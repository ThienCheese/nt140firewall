import asyncio
import httpx
from dnslib.dns import DNSRecord

from core.config import settings

# Tạo một HTTP client duy nhất, được chia sẻ để tái sử dụng kết nối
# Đây là trình chuyển tiếp DoH của chúng ta
doh_client = httpx.AsyncClient(
    headers={"Content-Type": "application/dns-message", "Accept": "application/dns-message"},
    http2=True, # Sử dụng HTTP/2 cho hiệu suất DoH
    timeout=5.0,
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
        return await asyncio.wait_for(response_future, timeout=5.0)
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

async def forward_query(request_bytes: bytes, client_ip: str) -> bytes | None:
    """
    Logic định tuyến thông minh:
    - Máy khách LAN -> Chuyển tiếp đến Router (để phân giải DNS nội bộ).
    - Máy khách WAN (DoH/DoT) -> Chuyển tiếp đến Upstream (để tránh vòng lặp).
    """
    is_lan_client = client_ip.startswith("192.168.") or client_ip == "127.0.0.1"
    
    if is_lan_client:
        # Chuyển tiếp đến Router qua UDP
        return await forward_udp(request_bytes, settings.ROUTER_IP, 53)
    else:
        # Máy khách từ xa (DoH/DoT). Chuyển tiếp đến Upstream DoH công cộng
        response = await forward_doh(request_bytes, settings.UPSTREAM_DNS_1)
        if response is None:
            # Thử máy chủ dự phòng
            response = await forward_doh(request_bytes, settings.UPSTREAM_DNS_2)
        return response