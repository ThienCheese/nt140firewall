"""
Static DNS Overrides Module
Handles hard-coded DNS responses để tránh circular dependency.
"""
import socket
from typing import Optional, Dict
from dnslib import DNSRecord, RR, A, AAAA, QTYPE

from core.config import settings


class StaticDNSManager:
    """
    Quản lý static DNS entries để resolve một số domains mà không cần
    forward đến upstream DNS (tránh circular dependency).
    """
    
    def __init__(self):
        self.static_entries: Dict[str, str] = {}
        self._load_static_entries()
    
    def _load_static_entries(self):
        """Load static DNS entries từ config hoặc resolve một lần."""
        # Resolve thiencheese.me một lần để lấy Cloudflare IPs
        try:
            # Dùng system resolver (trước khi override DNS)
            domain = settings.DOMAIN_NAME if hasattr(settings, 'DOMAIN_NAME') else "thiencheese.me"
            
            # Resolve qua Cloudflare DNS trực tiếp để tránh circular
            # Chúng ta sẽ hard-code IPs của Cloudflare cho domain
            cloudflare_ips = [
                "104.21.90.197",   # Cloudflare proxy IP (example)
                "172.67.151.110",  # Cloudflare proxy IP (example)
            ]
            
            # Store với và không dấu chấm cuối
            for ip in cloudflare_ips:
                self.static_entries[f"{domain}"] = ip
                self.static_entries[f"{domain}."] = ip
                break  # Chỉ dùng IP đầu tiên
            
            print(f"✅ Static DNS: {domain} → {self.static_entries.get(domain, 'not set')}")
            
        except Exception as e:
            print(f"⚠️ Could not resolve static DNS entries: {e}")
            # Fallback: hard-code known Cloudflare IPs
            self.static_entries["thiencheese.me"] = "104.21.90.197"
            self.static_entries["thiencheese.me."] = "104.21.90.197"
    
    def get_static_response(self, record: DNSRecord) -> Optional[bytes]:
        """
        Tạo DNS response cho static entries.
        
        Args:
            record: DNS query record
            
        Returns:
            DNS response bytes hoặc None nếu không phải static entry
        """
        q = record.get_q()
        qname = str(q.qname).lower()
        qtype = q.qtype
        
        # Check nếu domain có trong static entries
        if qname not in self.static_entries:
            return None
        
        ip_address = self.static_entries[qname]
        reply = record.reply()
        
        # Chỉ handle A record (IPv4)
        if qtype == QTYPE.A:
            rdata = A(ip_address)
            reply.add_answer(RR(q.qname, QTYPE.A, rdata=rdata, ttl=300))
            return reply.pack()
        
        # AAAA (IPv6) - Return empty response
        elif qtype == QTYPE.AAAA:
            # Không có IPv6, return NOERROR với no answers
            return reply.pack()
        
        # Other types - return None để forward upstream
        return None
    
    def is_static_domain(self, domain: str) -> bool:
        """Check xem domain có phải static entry không."""
        return domain.lower() in self.static_entries
    
    def add_static_entry(self, domain: str, ip: str):
        """Thêm static entry manually."""
        self.static_entries[domain.lower()] = ip
        self.static_entries[f"{domain.lower()}."] = ip
    
    def remove_static_entry(self, domain: str):
        """Xóa static entry."""
        domain_lower = domain.lower()
        self.static_entries.pop(domain_lower, None)
        self.static_entries.pop(f"{domain_lower}.", None)
    
    def get_all_entries(self) -> Dict[str, str]:
        """Lấy tất cả static entries."""
        return self.static_entries.copy()


# Global instance
static_dns_manager = StaticDNSManager()
