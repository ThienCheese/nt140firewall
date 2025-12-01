import asyncio
import httpx
from dnslib.dns import DNSRecord
from core.config import settings

# Tạo một HTTP client duy nhất, được chia sẻ để tái sử dụng kết nối
# Đây là trình chuyển tiếp DoH của chúng ta
doh_client = httpx.AsyncClient(
    headers={"Content-Type": "application/dns-message", "Accept": "application/dns-message"},
    http2=True, # Sử dụng HTTP/2 cho hiệu suất DoH
    timeout=2.0,  # Giảm từ 5s → 2s để fail fast
    follow_redirects=True
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
        return await asyncio.wait_for(response_future, timeout=2.0)  # Giảm từ 5s → 2s
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

# ==================================
# == PHẦN ĐÃ SỬA LỖI
# ==================================
async def forward_query(request_bytes: bytes, client_ip: str) -> bytes | None:
    """
    Logic định tuyến với performance optimization:
    - Query cả 2 upstream servers ĐỒNG THỜI (parallel)
    - Lấy kết quả nhanh nhất (race condition)
    - Sử dụng UDP cho tốc độ (5-20ms vs DoH 50-100ms)
    - Fallback to DoH nếu UDP fail
    """
    
    # Parallel query to both upstreams (race condition - lấy cái nhanh nhất)
    tasks = [
        forward_udp(request_bytes, settings.UPSTREAM_DNS_1, 53),
        forward_udp(request_bytes, settings.UPSTREAM_DNS_2, 53)
    ]
    
    # Wait for first successful response
    for coro in asyncio.as_completed(tasks):
        try:
            response = await coro
            if response is not None:
                return response  # Return first successful response!
        except Exception:
            continue
    
    # If all UDP failed, fallback to DoH
    print(f"⚠️ All UDP failed, falling back to DoH...")
    response = await forward_doh(request_bytes, settings.UPSTREAM_DNS_1)
    
    if response is None:
        response = await forward_doh(request_bytes, settings.UPSTREAM_DNS_2)
    
    return response