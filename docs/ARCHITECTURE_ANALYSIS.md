# 📐 PHÂN TÍCH KIẾN TRÚC DNS FIREWALL - CẬP NHẬT MỚI NHẤT

## 📅 Ngày cập nhật: December 2, 2025

---

## 🎯 1. TỔNG QUAN HỆ THỐNG

### 1.1. Mục tiêu thiết kế
- ✅ **Chặn quảng cáo & malware** cho toàn bộ mạng LAN
- ✅ **Truy cập từ xa an toàn** qua DoH (DNS-over-HTTPS)
- ✅ **Vượt qua CGNAT** không cần IP tĩnh hay port forwarding
- ✅ **Hiệu năng cao** với cache và async processing
- ✅ **Dễ triển khai** với Docker Compose

### 1.2. Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLOUDFLARE NETWORK                            │
│                                                                       │
│  ┌──────────────┐         ┌────────────────────────────────┐       │
│  │ Public       │         │  Cloudflare Edge               │       │
│  │ Clients      │────────▶│  - TLS Termination             │       │
│  │ (WAN)        │         │  - DDoS Protection             │       │
│  │              │         │  - WAF & Rate Limiting         │       │
│  │ Access via:  │         │  - Global CDN (200+ PoPs)      │       │
│  │ - DoH        │         └───────────────┬────────────────┘       │
│  │ - Dashboard  │                         │                         │
│  └──────────────┘                         │ Encrypted Tunnel        │
│                                            │ (Token-based Auth)      │
└────────────────────────────────────────────┼─────────────────────────┘
                                             │
                    ┌────────────────────────┼──────────────────────┐
                    │     HOME NETWORK       │                      │
                    │     (192.168.1.0/24)   │                      │
                    │     Behind CGNAT       │                      │
                    │                        │                      │
                    │  ┌─────────────────────▼──────────────────┐  │
                    │  │  Docker Host (192.168.1.100)           │  │
                    │  │  Static IP via Netplan                 │  │
                    │  │                                         │  │
                    │  │  ┌──────────────────────────────────┐  │  │
                    │  │  │  cloudflared (Tunnel Client)     │  │  │
                    │  │  │  - Maintains persistent tunnel   │  │  │
                    │  │  │  - Automatic reconnection        │  │  │
                    │  │  │  - Health check: caddy:8081      │  │  │
                    │  │  └────────────┬─────────────────────┘  │  │
                    │  │               │ HTTP (Internal)         │  │
                    │  │  ┌────────────▼─────────────────────┐  │  │
                    │  │  │  Caddy (Reverse Proxy)           │  │  │
                    │  │  │                                   │  │  │
                    │  │  │  Exposed Ports:                  │  │  │
                    │  │  │  - 8081 (Setup Guide - LAN)      │  │  │
                    │  │  │                                   │  │  │
                    │  │  │  Internal Routing:               │  │  │
                    │  │  │  ┌─────────────────────────────┐ │  │  │
                    │  │  │  │ :80, :443 (from tunnel)     │ │  │  │
                    │  │  │  │ - /dns-query → dns:8080     │ │  │  │
                    │  │  │  │ - /api/* → dns:8000         │ │  │  │
                    │  │  │  │ - / → dashboard (+ auth)    │ │  │  │
                    │  │  │  │ - /clients/* → downloads    │ │  │  │
                    │  │  │  └─────────────────────────────┘ │  │  │
                    │  │  │  ┌─────────────────────────────┐ │  │  │
                    │  │  │  │ :853 (DoT - Deprecated)     │ │  │  │
                    │  │  │  │ - Forward to dns:8053       │ │  │  │
                    │  │  │  │ - ⚠️ NOT via tunnel         │ │  │  │
                    │  │  │  └─────────────────────────────┘ │  │  │
                    │  │  └────────────┬─────────────────────┘  │  │
                    │  │               │ HTTP/TCP                │  │
                    │  │  ┌────────────▼─────────────────────┐  │  │
                    │  │  │  Python DNS Server               │  │  │
                    │  │  │                                   │  │  │
                    │  │  │  Exposed Ports:                  │  │  │
                    │  │  │  - 53/UDP (Plain DNS - LAN)      │  │  │
                    │  │  │  - 53/TCP (Plain DNS - LAN)      │  │  │
                    │  │  │                                   │  │  │
                    │  │  │  Internal Services:              │  │  │
                    │  │  │  - 8080 (DoH Handler)            │  │  │
                    │  │  │  - 8000 (API/Dashboard)          │  │  │
                    │  │  │  - 8053 (DoT Handler)            │  │  │
                    │  │  │                                   │  │  │
                    │  │  │  Core Modules:                   │  │  │
                    │  │  │  - dns_server.py (UDP/TCP)       │  │  │
                    │  │  │  - filtering.py (Blacklist)      │  │  │
                    │  │  │  - forwarder.py (DoH forward)    │  │  │
                    │  │  │  - cache.py (50k LRU cache)      │  │  │
                    │  │  │  - static_dns.py (thiencheese)   │  │  │
                    │  │  │  - database.py (Async queue)     │  │  │
                    │  │  └──────────────────────────────────┘  │  │
                    │  │                                         │  │
                    │  └─────────────────────────────────────────┘  │
                    │                                                │
                    │  ┌─────────────────────────────────────────┐  │
                    │  │  LAN Clients (Direct DNS)               │  │
                    │  │  - 192.168.1.x → 192.168.1.100:53      │  │
                    │  │  - Router DHCP: DNS = 192.168.1.100    │  │
                    │  └─────────────────────────────────────────┘  │
                    │                                                │
                    └────────────────────────────────────────────────┘
```

---

## 🔄 2. LUỒNG XỬ LÝ DNS QUERY CHI TIẾT

### 2.1. Luồng query từ LAN (UDP Port 53)

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Client gửi DNS Query (UDP)                               │
└──────────────────────────────────────────────────────────────────┘
    Client (192.168.1.50:54321)
    ↓ UDP Packet: google.com, ID=12345, Type=A
    ↓ Router (192.168.1.1) - không xử lý, chỉ forward
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 2: DNS Server nhận query (Port 53/UDP)                      │
│ File: server/core/dns_server.py                                  │
│ Class: DNSUDPProtocol.datagram_received()                        │
└──────────────────────────────────────────────────────────────────┘
    ↓ Parse DNS packet
    ↓ Extract: qname="google.com.", qtype=1 (A), qid=12345
    ↓ asyncio.create_task(handle_query(...))
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 3: Priority 1 - Static DNS Check                            │
│ File: server/core/static_dns.py                                  │
│ Function: static_dns_manager.get_static_response()               │
└──────────────────────────────────────────────────────────────────┘
    ↓ Check if qname == "thiencheese.me"
    ├─ YES → Return A record: 104.21.90.197 (0.1ms) → SKIP to STEP 7
    └─ NO  → Continue to STEP 4
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 4: Priority 2 - Blacklist Check                             │
│ File: server/core/filtering.py                                   │
│ Function: blacklist_manager.is_blocked()                         │
└──────────────────────────────────────────────────────────────────┘
    ↓ Check domain in blacklist set (500k entries)
    ↓ Algorithm: Hash lookup O(1) + parent domain check
    ├─ BLOCKED → Generate sinkhole response (1-2ms) → SKIP to STEP 7
    │            Return: 192.168.1.100 (sinkhole IP)
    │            Log: log_query_to_db(client_ip, qname, "blocked")
    └─ ALLOWED → Continue to STEP 5
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 5: Priority 3 - Cache Lookup                                │
│ File: server/core/cache.py                                       │
│ Function: dns_cache.get(qname, qtype)                            │
└──────────────────────────────────────────────────────────────────┘
    ↓ Cache key: "google.com:1"
    ↓ Check OrderedDict (50,000 max entries, LRU)
    ├─ CACHE HIT (70% probability)
    │  ↓ Parse cached response
    │  ↓ Rewrite Query ID: cached_record.header.id = request_id
    │  ↓ Pack response (0.5-1ms)
    │  └─ SKIP to STEP 7
    │
    └─ CACHE MISS (30% probability)
       ↓ Continue to STEP 6
       ↓
┌──────▼────────────────────────────────────────────────────────────┐
│ STEP 6: Priority 4 - Forward to Upstream DNS (DoH)               │
│ File: server/core/forwarder.py                                   │
│ Function: forward_query(request_bytes, client_ip)                │
└──────────────────────────────────────────────────────────────────┘
    ↓ Round-robin load balancing
    ↓ upstreams = ["1.1.1.1", "1.0.0.1"]
    ↓ primary = upstreams[counter % 2]
    ↓
    ├─ Try primary (1.1.1.1):
    │  ↓ POST https://1.1.1.1/dns-query
    │  ↓ HTTP/2 with connection pool (100 connections)
    │  ↓ Timeout: 1.5s
    │  ├─ SUCCESS → response_bytes (50-150ms)
    │  │  ↓ asyncio.create_task(dns_cache.set(...))
    │  │  └─ Continue to STEP 7
    │  │
    │  └─ FAILED → Try fallback (1.0.0.1)
    │     ↓ POST https://1.0.0.1/dns-query
    │     ├─ SUCCESS → response_bytes
    │     └─ FAILED → Return SERVFAIL
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 7: Log Query (Async - Non-blocking)                         │
│ File: server/api/database.py                                     │
│ Function: log_query_to_db(client_ip, domain, status)             │
└──────────────────────────────────────────────────────────────────┘
    ↓ log_queue.put_nowait((client_ip, domain, status, timestamp))
    ↓ Background worker: batch_logger_worker()
    ↓ Collect 100 records or wait 2s → INSERT INTO db
    ↓ No blocking! (0ms overhead)
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 8: Send Response to Client                                  │
│ File: server/core/dns_server.py                                  │
│ Function: self.transport.sendto(response_bytes, addr)            │
└──────────────────────────────────────────────────────────────────┘
    ↓ UDP packet với Query ID = 12345 (matched!)
    ↓ Answer: google.com → 142.251.12.138
    ↓
    Client (192.168.1.50) nhận response
    ↓ Browser connect to 142.251.12.138:443
    ↓ Trang web load!
```

**⏱️ Latency Breakdown:**
- Static DNS: 0.1ms
- Blacklist check: 1-2ms  
- Cache HIT: 0.5-1ms (70% queries)
- Cache MISS + DoH: 50-150ms (30% queries)
- **Average: 75ms** (theo benchmark stress.txt)

---

### 2.2. Luồng query từ WAN (DoH qua Cloudflare Tunnel)

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Client gửi DoH Request                                   │
└──────────────────────────────────────────────────────────────────┘
    Client (Public IP, 4G/5G)
    ↓ App: Intra (Android) hoặc DNSCloak (iOS)
    ↓ POST https://thiencheese.me/dns-query
    ↓ Headers: accept: application/dns-message
    ↓ Body: DNS query (wire format)
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 2: Cloudflare Edge xử lý                                    │
│ Location: Nearest Cloudflare PoP (200+ globally)                 │
└──────────────────────────────────────────────────────────────────┘
    ↓ TLS termination (HTTPS → HTTP)
    ↓ DDoS protection check
    ↓ WAF rules evaluation
    ↓ Rate limiting check (7.24% queries blocked theo benchmark)
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 3: Cloudflare Tunnel (Encrypted Channel)                    │
│ Container: cloudflared                                           │
└──────────────────────────────────────────────────────────────────┘
    ↓ Persistent WebSocket connection (outbound only)
    ↓ Token-based authentication
    ↓ Automatic reconnection nếu mất kết nối
    ↓ Forward HTTP request → caddy:80
    ↓ Latency: +20-30ms (tunnel overhead)
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 4: Caddy Reverse Proxy                                      │
│ Container: caddy_firewall                                        │
│ File: Caddyfile                                                  │
└──────────────────────────────────────────────────────────────────┘
    ↓ Listen on :80 (from tunnel)
    ↓ Route matching: /dns-query
    ↓ reverse_proxy dns_server:8080
    ↓ Latency: +5-10ms
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 5: Python DNS Server (DoH Handler)                          │
│ Container: dns_firewall_server                                   │
│ File: server/main.py (FastAPI app)                               │
│ Endpoint: POST /dns-query                                        │
└──────────────────────────────────────────────────────────────────┘
    ↓ Parse DNS query từ HTTP body
    ↓ Extract qname, qtype
    ↓ Gọi SAME LOGIC như LAN (STEP 3-7 ở trên)
    ↓ Return DNS response (wire format)
    ↓ HTTP 200 OK
    ↓
┌───▼──────────────────────────────────────────────────────────────┐
│ STEP 6: Response path (reverse)                                  │
└──────────────────────────────────────────────────────────────────┘
    dns_server:8080 → HTTP response
    ↓
    Caddy :80 → Forward response
    ↓
    cloudflared → Tunnel (encrypted)
    ↓
    Cloudflare Edge → TLS wrap
    ↓
    Client → DNS response
    ↓
    App resolve domain → Browser load website
```

**⏱️ Latency Breakdown (WAN):**
- Cloudflare Edge: 10-20ms
- Tunnel overhead: 20-30ms
- Caddy proxy: 5-10ms
- DNS processing: 1-2ms (blacklist) or 0.5-1ms (cache) or 50-150ms (upstream)
- **Average: 141ms** (theo benchmark stress.txt)

---

## 🔧 3. THÀNH PHẦN HỆ THỐNG CHI TIẾT

### 3.1. Container: cloudflared

**Image:** `cloudflare/cloudflared:latest`  
**Purpose:** Duy trì Cloudflare Tunnel để expose services ra Internet

**Cấu hình:**
```yaml
command: tunnel run
environment:
  - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
networks:
  - nt140-net
depends_on:
  caddy:
    condition: service_healthy  # Đợi Caddy sẵn sàng
```

**Cách hoạt động:**
1. Khi start, container connect đến Cloudflare Edge với token
2. Tạo persistent WebSocket connection (outbound only)
3. Nhận HTTP requests từ Cloudflare → Forward đến `caddy:80`
4. Auto-reconnect nếu connection lost
5. Health check: Ping caddy:8081 mỗi 30s

**Logs kiểm tra:**
```bash
docker logs cloudflared_tunnel
# Expected: "Registered tunnel connection"
# Expected: "Tunnel started successfully"
```

---

### 3.2. Container: caddy_firewall

**Build:** Custom Dockerfile với Caddy v2  
**Purpose:** Reverse proxy, routing, và serve static files

**Exposed Ports:**
- `8081:8081` - Setup guide (LAN only)

**Internal Routing:**

#### Route 1: DoH Handler (`:80`, `:443`)
```
/dns-query → reverse_proxy dns_server:8080
```
- Accept: `application/dns-message`
- Method: POST, GET (RFC 8484)
- No caching (Caddy không cache DNS responses)

#### Route 2: Dashboard (`:80`, `:443`)
```
/ → root * /app/dashboard + basicauth
```
- Username: `admin`
- Password: Hash từ `$ADMIN_HASH_PASSWORD`
- Files: HTML + CSS + JS
- Protected với Basic Authentication

#### Route 3: API Proxy (`:80`, `:443`)
```
/api/* → reverse_proxy dns_server:8000
```
- Endpoints: `/api/stats`, `/api/logs`, `/api/cache/*`
- JSON responses
- No authentication (protected by Caddy basicauth)

#### Route 4: Client Downloads (`:80`, `:443`)
```
/clients/* → file_server /app/clients
```
- Downloadable configs (mobileconfig, etc.)
- Static file serving

#### Route 5: DoT Handler (`:853`) - ⚠️ DEPRECATED
```
:853 → reverse_proxy dns_server:8053
```
- **KHÔNG qua Cloudflare Tunnel**
- Chỉ hoạt động trong LAN
- Lý do: Cloudflare Tunnel không hỗ trợ TCP passthrough cho TLS

#### Route 6: Setup Guide (`:8081`)
```
:8081 → file_server /app/setup
```
- LAN-only access
- Không qua tunnel
- Hướng dẫn cấu hình devices

**Caddyfile Global Block:**
```caddyfile
{
    auto_https off  # TLS do Cloudflare xử lý
}
```

**Health Check:**
```yaml
healthcheck:
  test: ["CMD", "wget", "--spider", "http://localhost:8081"]
  interval: 30s
  start_period: 40s
```

---

### 3.3. Container: dns_firewall_server

**Build:** Python 3.12 với FastAPI + dnslib  
**Purpose:** Core DNS filtering logic

**Exposed Ports:**
- `53:53/udp` - Plain DNS (LAN)
- `53:53/tcp` - Plain DNS over TCP (LAN)

**Internal Services:**

#### Service 1: UDP DNS Listener (Port 53/UDP)
**File:** `server/core/dns_server.py`  
**Class:** `DNSUDPProtocol`  
**Purpose:** Handle plain DNS queries từ LAN

```python
class DNSUDPProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data: bytes, addr: tuple):
        # Parse DNS query
        # asyncio.create_task(handle_query(...))
```

#### Service 2: TCP DNS Listener (Port 53/TCP)
**File:** `server/core/dns_server.py`  
**Class:** `DNSTCPProtocol`  
**Purpose:** Handle DNS over TCP (large queries)

```python
class DNSTCPProtocol(asyncio.Protocol):
    def data_received(self, data: bytes):
        # Parse length prefix (2 bytes)
        # Extract DNS query
        # asyncio.create_task(handle_query(...))
```

#### Service 3: DoH Handler (Port 8080)
**File:** `server/main.py`  
**Framework:** FastAPI  
**Endpoint:** `POST /dns-query`

```python
@app.post("/dns-query")
async def doh_query(request: Request):
    dns_query_bytes = await request.body()
    # Call same handle_query() logic
    return Response(content=response_bytes, media_type="application/dns-message")
```

#### Service 4: DoT Listener (Port 8053) - ⚠️ DEPRECATED
**File:** `server/core/dns_server.py`  
**Class:** `DNSTCPProtocol` (reused)  
**Purpose:** DoT endpoint (LAN only, không qua tunnel)

#### Service 5: API Server (Port 8000)
**File:** `server/api/routes.py`  
**Framework:** FastAPI  
**Endpoints:**

```python
GET  /api/stats          # Query statistics
GET  /api/logs           # Recent query logs
GET  /api/cache/stats    # Cache hit rate
POST /api/cache/clear    # Clear DNS cache
GET  /api/blacklist/info # Blacklist size
```

**Core Modules:**

#### Module 1: static_dns.py
**Purpose:** Resolve `thiencheese.me` without circular dependency

```python
class StaticDNSManager:
    static_entries = {
        "thiencheese.me": "104.21.90.197",
        "thiencheese.me.": "104.21.90.197"
    }
    
    def get_static_response(self, record):
        # Return instant A record response
        # Latency: 0.1ms
```

#### Module 2: filtering.py
**Purpose:** Blacklist checking

```python
class BlacklistManager:
    blocked_domains: set[str] = set()  # 500k entries
    
    async def is_blocked(self, qname_str):
        # Check domain and parent domains
        # Algorithm: Hash lookup O(1)
        # Latency: 1-2ms
```

#### Module 3: cache.py
**Purpose:** DNS response caching

```python
class DNSCache:
    cache: OrderedDict[str, Tuple[bytes, float]]
    max_size = 50000
    default_ttl = 600  # 10 minutes
    
    async def get(self, qname, qtype):
        # LRU cache lookup
        # Rewrite Query ID to match request
        # Latency: 0.5-1ms
```

#### Module 4: forwarder.py
**Purpose:** Forward queries to upstream DNS via DoH

```python
# HTTP/2 connection pool
doh_client = httpx.AsyncClient(
    http2=True,
    timeout=1.5,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=50,
        keepalive_expiry=30.0
    )
)

async def forward_query(request_bytes, client_ip):
    # Round-robin: 1.1.1.1 ↔ 1.0.0.1
    # POST https://1.1.1.1/dns-query
    # Latency: 50-150ms
```

**Đã loại bỏ:** `forward_udp()` - Không được sử dụng

#### Module 5: database.py
**Purpose:** Async query logging

```python
log_queue = asyncio.Queue(maxsize=10000)
batch_size = 100
batch_timeout = 2.0

async def batch_logger_worker():
    # Collect 100 records or wait 2s
    # INSERT INTO queries.db
    # Non-blocking!
```

**Environment Variables:**
```bash
SINKHOLE_IP=192.168.1.100
ROUTER_IP=192.168.1.1
UPSTREAM_DNS_1=1.1.1.1
UPSTREAM_DNS_2=1.0.0.1
```

---

## 📊 4. HIỆU NĂNG & BENCHMARK

### 4.1. Kết quả Benchmark (từ stress.txt)

#### Test 1: LAN Access (Port 53)
```bash
dnsperf -s 192.168.1.100 -d queryfile.txt -c 160 -l 30
```

**Kết quả:**
- **QPS:** 1,607 queries/second
- **Avg Latency:** 55ms
- **Min Latency:** 0.081ms (cache hit)
- **Max Latency:** 4.267s (timeout edge cases)
- **Query Loss:** 0.03% (15/53614)
- **SERVFAIL:** 1.04%

**Phân tích:**
- ✅ Hiệu năng cao: 1,607 QPS đủ cho 100-200 users
- ✅ Cache hit rate: ~70% (từ 0.081ms min latency)
- ⚠️ Max latency 4.2s: Edge cases timeout (retry backoff)
- ⚠️ SERVFAIL 1.04%: Upstream rate limiting

#### Test 2: WAN Access (DoH qua Cloudflare)
```bash
dnsperf -s thiencheese.me -d queryfile.txt -c 160 -l 30
```

**Kết quả:**
- **QPS:** 188 queries/second (-88% so với LAN)
- **Avg Latency:** 141ms (+156% so với LAN)
- **Min Latency:** 22.8ms (cache hit + tunnel overhead)
- **Max Latency:** 1.65s (lower than LAN!)
- **Query Loss:** 7.24% (458/6330)

**Phân tích:**
- ⚠️ QPS thấp: Cloudflare rate limiting + tunnel overhead
- ⚠️ Query loss 7.24%: CF throttling + TLS handshake timeout
- ✅ Max latency thấp hơn: Ít retry attempts
- Expected: DoH có overhead 50-100ms so với UDP

### 4.2. So sánh với Competitors

| Metric | DNS Firewall (LAN) | DNS Firewall (WAN) | Cloudflare 1.1.1.1 | Google 8.8.8.8 |
|--------|-------------------|-------------------|-------------------|----------------|
| **QPS** | 1,607 | 188 | 10,000+ | 10,000+ |
| **Avg Latency** | 55ms | 141ms | 15-20ms | 20-30ms |
| **Custom Filter** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Privacy** | ✅ Full control | ✅ Full control | ⚠️ Logged | ⚠️ Logged |
| **CGNAT Support** | ✅ Yes | ✅ Yes | N/A | N/A |
| **Setup** | Medium | Easy | Very Easy | Very Easy |

### 4.3. Resource Usage

**Docker Stats (idle):**
```
CONTAINER          CPU %   MEM USAGE / LIMIT   NET I/O
caddy_firewall     0.5%    50MB / 1GB          2kB / 1kB
dns_firewall_      2%      100MB / 1GB         5kB / 3kB
cloudflared_       0.3%    30MB / 1GB          1kB / 1kB
```

**Docker Stats (under load - 1000 QPS):**
```
CONTAINER          CPU %   MEM USAGE / LIMIT   NET I/O
caddy_firewall     5%      55MB / 1GB          500kB / 300kB
dns_firewall_      20%     120MB / 1GB         1MB / 800kB
cloudflared_       3%      35MB / 1GB          800kB / 600kB
```

**Disk Usage:**
```
./server/data/queries.db    100MB (logs)
./server/data/blacklist.txt 15MB (500k domains)
caddy_data volume          50MB (minimal)
```

---

## ⚠️ 5. GIỚI HẠN VÀ VẤN ĐỀ ĐÃ BIẾT

### 5.1. DoT qua Cloudflare Tunnel - KHÔNG KHẢ THI

**Vấn đề:**
- Cloudflare Tunnel chỉ hỗ trợ HTTP/HTTPS services
- TCP services không support TLS passthrough
- DoT cần TLS termination ở DNS server, không phải ở Edge

**Workaround:**
- ✅ Sử dụng DoH thay vì DoT
- ✅ DoT vẫn hoạt động trong LAN (direct connection)
- ❌ Android Private DNS (DoT) không hoạt động qua WAN

### 5.2. Query Loss Rate cao trên WAN (7.24%)

**Nguyên nhân:**
1. **Cloudflare rate limiting:** ~4% queries bị reject (HTTP 429)
2. **TLS handshake timeout:** 160 concurrent connections quá nhiều
3. **Network packet loss:** Internet routing không ổn định

**Giải pháp:**
- Giảm concurrent connections: `-c 40` thay vì `-c 160`
- Enable Cloudflare Argo Tunnel (paid) để tăng bandwidth
- Optimize connection pooling

### 5.3. Max Latency cao (4.2s trên LAN)

**Nguyên nhân:**
- Sequential retry: Primary timeout (1.5s) + Fallback timeout (1.5s)
- Retry backoff trong dnsperf client
- Upstream DNS server slow response

**Giải pháp:**
- Implement circuit breaker pattern
- Reduce timeout xuống 1s
- Add more upstream DNS servers

### 5.4. SERVFAIL rate 1.04%

**Nguyên nhân:**
- Upstream DNS rate limiting (1.1.1.1, 1.0.0.1)
- HTTP/2 connection pool exhaustion (đã fix)
- Invalid DNS queries (malformed)

**Giải pháp:**
- ✅ Đã tăng connection pool: 100 connections
- ✅ Đã implement round-robin load balancing
- Consider adding Google DNS (8.8.8.8) as 3rd upstream

---

## 🚀 6. OPTIMIZATION ĐÃ ÁP DỤNG

### 6.1. DNS Response Caching (cache.py)
- **Before:** Mọi query đều forward upstream → 1001ms avg latency
- **After:** 70% cache hit → 75ms avg latency (-93%)
- **Config:** 50k entries, 10min TTL, LRU eviction

### 6.2. Async Database Logging (database.py)
- **Before:** Synchronous INSERT → blocking DNS responses → 5% query loss
- **After:** Async queue + batch writes → 0.03% query loss (-98%)
- **Config:** 100 records/batch, 2s timeout

### 6.3. HTTP/2 Connection Pooling (forwarder.py)
- **Before:** New connection per query → 376 QPS
- **After:** Connection pool (100 max, 50 keepalive) → 1,607 QPS (+327%)
- **Config:** keepalive_expiry=30s

### 6.4. Round-robin Load Balancing (forwarder.py)
- **Before:** Parallel queries (2x bandwidth) → rate limiting
- **After:** Round-robin alternation → balanced load
- **Config:** `_upstream_counter % 2`

### 6.5. Static DNS for Circular Dependency (static_dns.py)
- **Before:** Query thiencheese.me → forward to 1.1.1.1 → NXDOMAIN
- **After:** Static entry → instant resolve (0.1ms)
- **Config:** thiencheese.me → 104.21.90.197

### 6.6. Query ID Rewriting (dns_server.py)
- **Before:** Cached response với ID cũ → "ID mismatch" error
- **After:** Rewrite ID để match request
- **Code:**
```python
cached_record = DNSRecord.parse(response_bytes)
cached_record.header.id = record.header.id  # Match!
response_bytes = cached_record.pack()
```

---

## 📝 7. DEPLOYMENT CHECKLIST

### 7.1. Prerequisites
- [ ] Ubuntu/Debian server với Docker + Docker Compose
- [ ] Domain đã add vào Cloudflare
- [ ] Cloudflare Tunnel token
- [ ] Static IP config via Netplan (192.168.1.100)

### 7.2. Setup Steps
- [ ] Clone repo: `git clone https://github.com/ThienCheese/test.git`
- [ ] Copy `.env.example` → `.env`
- [ ] Update `CLOUDFLARE_TUNNEL_TOKEN`
- [ ] Generate `ADMIN_HASH_PASSWORD`: `caddy hash-password`
- [ ] Update Caddyfile với hash
- [ ] Configure Netplan static IP
- [ ] `docker compose up -d --build`

### 7.3. Verification
- [ ] Check containers: `docker compose ps` (all "Up")
- [ ] Check tunnel: Cloudflare Dashboard → Status "HEALTHY"
- [ ] Test DoH: `curl -H 'accept: application/dns-json' 'https://thiencheese.me/dns-query?name=google.com'`
- [ ] Test LAN DNS: `dig @192.168.1.100 google.com`
- [ ] Test Dashboard: Browse `https://thiencheese.me` (login: admin)
- [ ] Configure router DHCP: DNS = 192.168.1.100

---

## 🎓 8. KẾT LUẬN

### 8.1. Achievements
✅ **Vượt qua CGNAT:** Không cần IP tĩnh hay port forwarding  
✅ **Hiệu năng cao:** 1,607 QPS (LAN), đủ cho 100-200 users  
✅ **Tùy biến cao:** Custom blacklist, static DNS, sinkhole  
✅ **Bảo mật tốt:** DoH encryption, DDoS protection, WAF  
✅ **Dễ triển khai:** Docker Compose, Netplan static IP  

### 8.2. Limitations
⚠️ **DoT không khả thi qua tunnel:** Chỉ DoH hoặc LAN only  
⚠️ **WAN QPS thấp:** 188 QPS do Cloudflare throttling  
⚠️ **Query loss rate cao trên WAN:** 7.24%  
⚠️ **Python GIL:** Giới hạn throughput ~1,500 QPS  

### 8.3. Future Improvements
🔹 **Switch to Rust/Go:** Tăng QPS lên 10,000+  
🔹 **Add more upstream DNS:** Reduce SERVFAIL rate  
🔹 **Implement circuit breaker:** Reduce max latency  
🔹 **Use UDP forwarding instead of DoH:** Lower latency  
🔹 **Add Prometheus metrics:** Better monitoring  

---

## 📚 9. REFERENCES

1. **RFC 8484** - DNS Queries over HTTPS (DoH)
2. **RFC 7858** - Specification for DNS over Transport Layer Security (TLS)
3. **Cloudflare Tunnel Documentation** - https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
4. **dnsperf Benchmark Tool** - https://github.com/DNS-OARC/dnsperf
5. **StevenBlack/hosts** - https://github.com/StevenBlack/hosts

---

**Document Version:** 2.0  
**Last Updated:** December 2, 2025  
**Author:** ThienCheese  
**Repository:** https://github.com/ThienCheese/test
