"""
DNS Response Caching Module
Caches DNS responses để giảm latency và upstream queries.
"""
import asyncio
import time
from typing import Optional, Dict, Tuple
from collections import OrderedDict
from dnslib import DNSRecord


class DNSCache:
    """
    Thread-safe in-memory DNS cache với TTL support.
    Sử dụng LRU eviction policy.
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        """
        Args:
            max_size: Số lượng records tối đa trong cache
            default_ttl: TTL mặc định (giây) nếu response không có TTL
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Tuple[bytes, float]] = OrderedDict()
        self.lock = asyncio.Lock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _make_key(self, qname: str, qtype: int) -> str:
        """Tạo cache key từ query name và type."""
        return f"{qname.lower().rstrip('.')}:{qtype}"
    
    def _is_expired(self, expire_time: float) -> bool:
        """Check xem cache entry đã hết hạn chưa."""
        return time.time() > expire_time
    
    async def get(self, qname: str, qtype: int) -> Optional[bytes]:
        """
        Lấy cached response nếu có và chưa expire.
        
        Args:
            qname: Domain name
            qtype: Query type (A=1, AAAA=28, etc.)
            
        Returns:
            Cached DNS response bytes hoặc None
        """
        key = self._make_key(qname, qtype)
        
        async with self.lock:
            if key in self.cache:
                response_bytes, expire_time = self.cache[key]
                
                if self._is_expired(expire_time):
                    # Expired → xóa khỏi cache
                    del self.cache[key]
                    self.misses += 1
                    return None
                
                # Move to end (LRU)
                self.cache.move_to_end(key)
                self.hits += 1
                return response_bytes
            
            self.misses += 1
            return None
    
    async def set(self, qname: str, qtype: int, response_bytes: bytes, ttl: Optional[int] = None):
        """
        Lưu DNS response vào cache.
        
        Args:
            qname: Domain name
            qtype: Query type
            response_bytes: DNS response để cache
            ttl: Time-to-live (giây), None = sử dụng default_ttl
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # Parse TTL từ response nếu có thể
        try:
            record = DNSRecord.parse(response_bytes)
            if record.rr:  # Nếu có resource records
                # Lấy TTL nhỏ nhất từ các RRs
                min_ttl = min(rr.ttl for rr in record.rr)
                ttl = min(ttl, min_ttl) if min_ttl > 0 else ttl
        except:
            pass  # Nếu parse lỗi, dùng default TTL
        
        key = self._make_key(qname, qtype)
        expire_time = time.time() + ttl
        
        async with self.lock:
            # LRU eviction nếu cache đầy
            if len(self.cache) >= self.max_size and key not in self.cache:
                self.cache.popitem(last=False)  # Remove oldest
                self.evictions += 1
            
            self.cache[key] = (response_bytes, expire_time)
            self.cache.move_to_end(key)
    
    async def invalidate(self, qname: str, qtype: Optional[int] = None):
        """
        Xóa cache entries cho domain.
        
        Args:
            qname: Domain name
            qtype: Query type (None = xóa tất cả types)
        """
        async with self.lock:
            if qtype is not None:
                key = self._make_key(qname, qtype)
                self.cache.pop(key, None)
            else:
                # Xóa tất cả entries cho domain này
                keys_to_delete = [
                    k for k in self.cache.keys() 
                    if k.startswith(f"{qname.lower().rstrip('.')}:")
                ]
                for key in keys_to_delete:
                    del self.cache[key]
    
    async def clear(self):
        """Xóa toàn bộ cache."""
        async with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    async def get_stats(self) -> Dict:
        """Lấy cache statistics."""
        async with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": round(hit_rate, 2),
                "total_queries": total
            }
    
    async def cleanup_expired(self):
        """Background task để xóa expired entries."""
        async with self.lock:
            current_time = time.time()
            keys_to_delete = [
                k for k, (_, expire_time) in self.cache.items()
                if current_time > expire_time
            ]
            for key in keys_to_delete:
                del self.cache[key]
            
            return len(keys_to_delete)


# Global cache instance
dns_cache = DNSCache(max_size=10000, default_ttl=300)


async def start_cache_cleanup_worker():
    """Background task để cleanup expired cache entries mỗi 60 giây."""
    while True:
        await asyncio.sleep(60)
        try:
            deleted = await dns_cache.cleanup_expired()
            if deleted > 0:
                print(f"🧹 Cache cleanup: Removed {deleted} expired entries")
        except Exception as e:
            print(f"❌ Cache cleanup error: {e}")
