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
async def forward_query(request_bytes: bytes, client_ip: str) -> bytes | None:
    """
    Logic định tuyến đã được sửa lỗi (Fix):
    - Bất kể client là LAN hay WAN (DoH/DoT), TẤT CẢ các truy vấn
    - KHÔNG bị chặn (allowed) sẽ được chuyển tiếp (forward) đến
    - các máy chủ DNS ngược dòng (upstream) công cộng (ví dụ: 1.1.1.1).
    - Điều này đảm bảo một chính sách lọc nhất quán và
    - tránh bị ảnh hưởng bởi bộ lọc của ISP/Router (tránh Split-Policy).
    """
    
    # Bỏ qua client_ip, luôn sử dụng upstream công cộng
    # để đảm bảo một chính sách lọc (policy) nhất quán.
    response = await forward_doh(request_bytes, settings.UPSTREAM_DNS_1)
    
    if response is None:
        # Thử máy chủ dự phòng nếu máy chủ đầu tiên thất bại
        print(f"Upstream 1 ({settings.UPSTREAM_DNS_1}) failed, trying upstream 2...")
        response = await forward_doh(request_bytes, settings.UPSTREAM_DNS_2)
        
    return response