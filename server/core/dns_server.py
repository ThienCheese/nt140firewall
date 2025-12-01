import asyncio
from dnslib import DNSRecord
from core.config import settings
from core.filtering import BlacklistManager
from core.forwarder import forward_query
from core.static_dns import static_dns_manager  # Import static DNS
from api.database import log_query_to_db # Import hàm log
from core.cache import dns_cache # Import DNS cache

class DNSUDPProtocol(asyncio.DatagramProtocol):
    """Xử lý các truy vấn UDP trên cổng 53."""
    def __init__(self, manager: BlacklistManager):
        self.manager = manager
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        client_ip = addr[0]
        try:
            record = DNSRecord.parse(data)
            qname = str(record.get_q().get_qname())
            
            # Chạy logic xử lý trong một tác vụ mới để không chặn
            # vòng lặp nhận (receive loop)
            asyncio.create_task(self.handle_query(data, addr, qname, client_ip, record))
        except Exception:
            # Gói tin DNS không hợp lệ
            pass 

    async def handle_query(self, data: bytes, addr: tuple, qname: str, client_ip: str, record):
        qtype = record.get_q().qtype
        
        # 1. Check static DNS trước (để tránh circular dependency)
        response_bytes = static_dns_manager.get_static_response(record)
        if response_bytes:
            # Static domain (VD: thiencheese.me) → return ngay
            await log_query_to_db(client_ip, qname, "static")
            self.transport.sendto(response_bytes, addr)
            return
        
        # 2. Check blacklist
        if await self.manager.is_blocked(qname):
            response_bytes = self.manager.get_sinkhole_response(record)
            await log_query_to_db(client_ip, qname, "blocked")
        else:
            # 3. Check cache
            response_bytes = await dns_cache.get(qname, qtype)
            
            if response_bytes is None:
                # 4. Cache miss → forward query
                response_bytes = await forward_query(data, client_ip)
                
                # 5. Cache response nếu hợp lệ
                if response_bytes:
                    asyncio.create_task(dns_cache.set(qname, qtype, response_bytes))
            
            await log_query_to_db(client_ip, qname, "allowed")

        if response_bytes:
            self.transport.sendto(response_bytes, addr)

class DNSTCPProtocol(asyncio.Protocol):
    """
    Xử lý các kết nối DNS over TCP (cả Cổng 53 và 8053 cho DoT).
    DNS over TCP sử dụng tiền tố độ dài 2-byte.
    """
    def __init__(self, manager: BlacklistManager):
        self.manager = manager
        self.transport = None
        self.client_ip = None
        self._buffer = b''

    def connection_made(self, transport):
        self.transport = transport
        self.client_ip = transport.get_extra_info('peername')[0]

    def data_received(self, data: bytes):
        self._buffer += data
        
        while len(self._buffer) > 2:
            try:
                # Đọc tiền tố độ dài 2-byte
                length = int.from_bytes(self._buffer[:2], 'big')
                
                # Kiểm tra xem đã nhận đủ gói tin chưa
                if len(self._buffer) >= (length + 2):
                    query_data = self._buffer[2:length+2]
                    # Cắt gói tin đã xử lý khỏi buffer
                    self._buffer = self._buffer[length+2:]
                    
                    record = DNSRecord.parse(query_data)
                    qname = str(record.get_q().get_qname())
                    
                    asyncio.create_task(self.handle_query(query_data, qname, self.client_ip, record))
                else:
                    # Gói tin chưa đầy đủ, chờ thêm dữ liệu
                    break
            except Exception:
                # Dữ liệu không hợp lệ, đóng kết nối
                self.transport.close()
                break

    async def handle_query(self, data: bytes, qname: str, client_ip: str, record):
        qtype = record.get_q().qtype
        
        # 1. Check static DNS trước (để tránh circular dependency)
        response_bytes = static_dns_manager.get_static_response(record)
        if response_bytes:
            # Static domain (VD: thiencheese.me) → return ngay
            await log_query_to_db(client_ip, qname, "static")
            len_prefix = len(response_bytes).to_bytes(2, 'big')
            self.transport.write(len_prefix + response_bytes)
            return
        
        # 2. Check blacklist
        if await self.manager.is_blocked(qname):
            response_bytes = self.manager.get_sinkhole_response(record)
            await log_query_to_db(client_ip, qname, "blocked")
        else:
            # 3. Check cache
            response_bytes = await dns_cache.get(qname, qtype)
            
            if response_bytes is None:
                # 4. Cache miss → forward query
                response_bytes = await forward_query(data, client_ip)
                
                # 5. Cache response nếu hợp lệ
                if response_bytes:
                    asyncio.create_task(dns_cache.set(qname, qtype, response_bytes))
            
            await log_query_to_db(client_ip, qname, "allowed")

        if response_bytes:
            len_prefix = len(response_bytes).to_bytes(2, 'big')
            self.transport.write(len_prefix + response_bytes)

async def start_dns_listeners(manager: BlacklistManager):
    """Khởi chạy tất cả các trình lắng nghe DNS (UDP, TCP, DoT)."""
    loop = asyncio.get_running_loop()
    
    # 1. Trình lắng nghe UDP (Cổng 53)
    await loop.create_datagram_endpoint(
        lambda: DNSUDPProtocol(manager),
        local_addr=('0.0.0.0', settings.DNS_PORT_UDP)
    )
    
    # 2. Trình lắng nghe TCP (Cổng 53, cho các truy vấn LAN lớn)
    await loop.create_server(
        lambda: DNSTCPProtocol(manager),
        host='0.0.0.0',
        port=settings.DNS_PORT_TCP
    )
    
    # 3. Trình lắng nghe TCP cho DoT (Cổng 8053, cho Caddy proxy)
    # Tái sử dụng cùng một protocol vì DoT chỉ là DNS-over-TCP được bọc TLS
    await loop.create_server(
        lambda: DNSTCPProtocol(manager),
        host='0.0.0.0',
        port=settings.DOT_PROXY_PORT
    )