import asyncio
import httpx
from dnslib.dns import DNSRecord
from core.config import settings

# Tạo một HTTP client duy nhất, được chia sẻ để tái sử dụng kết nối
# Đây là trình chuyển tiếp DoH của chúng ta
doh_client = httpx.AsyncClient(
    headers={"Content-Type": "application/dns-message", "Accept": "application/dns-message"},
    http2=True,  # Sử dụng HTTP/2 cho hiệu suất DoH
    timeout=1.5,  # Giảm xuống 1.5s để tổng max = 3s
    follow_redirects=True,
    limits=httpx.Limits(
        max_connections=100,      # Tăng connection pool
        max_keepalive_connections=50,  # Keep-alive connections
        keepalive_expiry=30.0     # Keep connections open 30s
    )
)

class UDPForwarderProtocol(asyncio.DatagramProtocol):
    """Protocol tùy chỉnh để xử lý một lần chuyển tiếp UDP."""
    def __init__(self, request_bytes: bytes, response_future: asyncio.Future):
        self.request_bytes = request_bytes
        self.response_future = response_future
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        self.transport.sendto(self.request_bytes)

    def datagram_received(self, data, addr):
        if not self.response_future.done():
            self.response_future.set_result(data)
        self.transport.close()

    def error_received(self, exc):
        if not self.response_future.done():
            self.response_future.set_exception(exc)
        self.transport.close()

    def connection_lost(self, exc):
        if not self.response_future.done():
            self.response_future.set_exception(exc or ConnectionError("Connection lost"))

async def forward_udp(request_bytes: bytes, host: str, port: int) -> bytes | None:
    """Chuyển tiếp truy vấn DNS bằng UDP."""
    loop = asyncio.get_running_loop()
    response_future = loop.create_future()
    
    try:
        await loop.create_datagram_endpoint(
            lambda: UDPForwarderProtocol(request_bytes, response_future),
            remote_addr=(host, port)
        )
        return await asyncio.wait_for(response_future, timeout=1.5)  # Giảm xuống 1.5s
    except Exception as e:
        print(f"Lỗi khi chuyển tiếp UDP đến {host}:{port}: {e}")
        return None

async def forward_doh(request_bytes: bytes, host: str) -> bytes | None:
    """Chuyển tiếp truy vấn DNS bằng DoH."""
    try:
        response = await doh_client.post(f"https://{host}/dns-query", content=request_bytes)
        response.raise_for_status()
        return response.content
    except httpx.RequestError as e:
        print(f"Lỗi khi chuyển tiếp DoH đến {host}: {e}")
        return None

# Round-robin counter để load balance giữa upstreams
_upstream_counter = 0

# ==================================
async def forward_query(request_bytes: bytes, client_ip: str) -> bytes | None:
    """
    Round-robin giữa 1.1.1.1 và 1.0.0.1 thay vì parallel queries
    để tránh 2x request load lên upstream servers.
    
    - Sequential queries: Giảm load từ 656 req/s → 328 req/s
    - Tránh HTTP/2 connection exhaustion
    - Max latency = 1.5s (single timeout) thay vì 3s (parallel)
    """
    global _upstream_counter
    
    # Round-robin: lần chẵn dùng 1.1.1.1, lần lẻ dùng 1.0.0.1
    upstreams = [settings.UPSTREAM_DNS_1, settings.UPSTREAM_DNS_2]
    primary = upstreams[_upstream_counter % 2]
    fallback = upstreams[(_upstream_counter + 1) % 2]
    _upstream_counter += 1
    
    # Try primary first
    response = await forward_doh(request_bytes, primary)
    if response:
        return response
    
    # Try fallback if primary failed
    response = await forward_doh(request_bytes, fallback)
    if response:
        return response
    
    # Both failed
    print(f"⚠️ Both upstreams failed!")
    return None