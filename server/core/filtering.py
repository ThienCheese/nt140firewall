import asyncio
from pathlib import Path
from dnslib.dns import QTYPE, RR, A, DNSRecord

from core.config import settings

class BlacklistManager:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.blocked_domains: set[str] = set()
        # Lock cần thiết để ngăn chặn race condition khi tải lại danh sách
        self._lock = asyncio.Lock()

    async def reload_blacklist(self):
        """
        Tải (hoặc tải lại) danh sách đen từ tệp  vào bộ nhớ.
        """
        if not self.filepath.exists():
            print(f"[Cảnh báo] Tệp danh sách đen {self.filepath} không tìm thấy.")
            self.blocked_domains = set()
            return

        new_blacklist = set()
        
        # Việc đọc tệp là đồng bộ, nhưng nó chỉ chạy
        # định kỳ nên chấp nhận được.
        try:
            with open(self.filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Xử lý định dạng hosts (ví dụ: 0.0.0.0 domain.com)
                        parts = line.split()
                        if len(parts) >= 2:
                            domain = parts[-1]
                            new_blacklist.add(domain)
                        # Xử lý định dạng chỉ có domain (như trong )
                        elif len(parts) == 1:
                            new_blacklist.add(parts[0])
            
            async with self._lock:
                self.blocked_domains = new_blacklist
            
            print(f"Đã tải lại danh sách đen. Tổng cộng {len(self.blocked_domains)} tên miền bị chặn.")
        except Exception as e:
            print(f"Lỗi khi tải danh sách đen: {e}")

    async def is_blocked(self, qname_str: str) -> bool:
        """
        Kiểm tra xem một tên miền (và các tên miền cha) có trong danh sách đen hay không.
        Đây là logic cốt lõi của tường lửa.
        """
        # qname_str thường kết thúc bằng dấu '.', hãy chuẩn hóa nó
        domain_parts = qname_str.strip('.').split('.')
        
        # Kiểm tra `ads.example.com`, sau đó `example.com`
        async with self._lock:
            for i in range(len(domain_parts)):
                subdomain = ".".join(domain_parts[i:])
                if subdomain in self.blocked_domains:
                    return True
        return False

    def get_sinkhole_response(self, record: DNSRecord) -> bytes:
        """
        Tạo một gói tin DNS trả lời trỏ đến SINKHOLE_IP.
        """
        q = record.get_q()
        reply = record.reply()
        
        # Chỉ trả về bản ghi A cho Sinkhole
        if q.qtype == QTYPE.A:
            rdata = A(settings.SINKHOLE_IP)
            reply.add_answer(RR(q.qname, q.qtype, rdata=rdata, ttl=60))
        
        # Đối với AAAA (IPv6) hoặc các loại khác, chỉ cần trả về
        # một phản hồi NOERROR (RCODE 0) không có câu trả lời.
        # Điều này ngăn ngừa lỗi trình duyệt nhưng không trỏ đến sinkhole.
        
        return reply.pack()

# Thực thể (instance) duy nhất được chia sẻ
blacklist_manager = BlacklistManager(settings.BLACKLIST_PATH)