# 🔄 LUỒNG XỬ LÝ HỆ THỐNG - DNS FIREWALL

## 📋 MỤC LỤC
1. [Luồng Query từ LAN (UDP)](#1-luồng-query-từ-lan-udp)
2. [Luồng Query từ WAN (DoH)](#2-luồng-query-từ-wan-doh)
3. [Sequence Diagrams](#3-sequence-diagrams)
4. [Performance Metrics](#4-performance-metrics)

---

## 1. LUỒNG QUERY TỪ LAN (UDP)

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Client gửi DNS Query                                     │
│ Location: Client device (192.168.1.50)                           │
│ Protocol: UDP                                                     │
└─────────────────────────────────────────────────────────────────┘
    │
    │ UDP Packet:
    │ - Source: 192.168.1.50:54321
    │ - Dest: 192.168.1.100:53
    │ - Query: google.com, Type=A, ID=12345
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Router Forward (Không xử lý)                             │
│ Device: Router (192.168.1.1)                                     │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Router chỉ forward packet theo routing table
    │ Không có DNS interception
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: DNS Server nhận query                                    │
│ Container: dns_firewall_server                                   │
│ File: server/core/dns_server.py                                  │
│ Class: DNSUDPProtocol                                            │
│ Method: datagram_received(data, addr)                            │
└─────────────────────────────────────────────────────────────────┘
    │
    │ try:
    │     record = DNSRecord.parse(data)
    │     qname = str(record.get_q().get_qname())  # "google.com."
    │     asyncio.create_task(handle_query(...))
    │ except:
    │     pass  # Invalid DNS packet, ignore
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Handle Query - Priority 1 (Static DNS)                   │
│ File: server/core/static_dns.py                                  │
│ Function: static_dns_manager.get_static_response(record)         │
│ Latency: 0.1ms                                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    │ if qname == "thiencheese.me":
    │     return A record: 104.21.90.197
    │     └─> JUMP to Step 9 (Send Response)
    │ else:
    │     continue to Step 5
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Handle Query - Priority 2 (Blacklist Check)              │
│ File: server/core/filtering.py                                   │
│ Function: blacklist_manager.is_blocked(qname)                    │
│ Latency: 1-2ms                                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Algorithm:
    │   domain_parts = qname.split(".")  # ["google", "com"]
    │   for i in range(len(domain_parts)):
    │       subdomain = ".".join(domain_parts[i:])
    │       if subdomain in blocked_domains:  # Hash lookup O(1)
    │           return True
    │
    │ if is_blocked(qname):
    │     response_bytes = manager.get_sinkhole_response(record)
    │     # Return: 192.168.1.100 (sinkhole IP)
    │     await log_query_to_db(client_ip, qname, "blocked")
    │     └─> JUMP to Step 9 (Send Response)
    │ else:
    │     continue to Step 6
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: Handle Query - Priority 3 (Cache Lookup)                 │
│ File: server/core/cache.py                                       │
│ Function: dns_cache.get(qname, qtype)                            │
│ Latency: 0.5-1ms                                                  │
│ Hit Rate: ~70%                                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Cache structure:
    │   OrderedDict[str, Tuple[bytes, float]]
    │   Key: "google.com:1"
    │   Value: (response_bytes, expire_time)
    │   Max size: 50,000 entries (LRU eviction)
    │
    │ async with self.lock:
    │     if key in self.cache:
    │         response_bytes, expire_time = self.cache[key]
    │         if not expired:
    │             # ⚠️ CRITICAL: Rewrite Query ID
    │             cached_record = DNSRecord.parse(response_bytes)
    │             cached_record.header.id = record.header.id
    │             response_bytes = cached_record.pack()
    │             self.hits += 1
    │             └─> JUMP to Step 8 (Log & Send)
    │
    │ # Cache MISS
    │ self.misses += 1
    │ continue to Step 7
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: Forward Query to Upstream DNS (DoH)                      │
│ File: server/core/forwarder.py                                   │
│ Function: forward_query(request_bytes, client_ip)                │
│ Latency: 50-150ms                                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    │ # Round-robin load balancing
    │ global _upstream_counter
    │ upstreams = ["1.1.1.1", "1.0.0.1"]
    │ primary = upstreams[_upstream_counter % 2]
    │ fallback = upstreams[(_upstream_counter + 1) % 2]
    │ _upstream_counter += 1
    │
    │ # HTTP/2 Connection Pool
    │ doh_client = httpx.AsyncClient(
    │     http2=True,
    │     timeout=1.5,
    │     limits=httpx.Limits(
    │         max_connections=100,
    │         max_keepalive_connections=50,
    │         keepalive_expiry=30.0
    │     )
    │ )
    │
    │ # Try primary upstream
    │ response = await doh_client.post(
    │     f"https://{primary}/dns-query",
    │     content=request_bytes
    │ )
    │ if response.status_code == 200:
    │     response_bytes = response.content
    │     # Async cache store (non-blocking)
    │     asyncio.create_task(dns_cache.set(qname, qtype, response_bytes))
    │     continue to Step 8
    │ else:
    │     # Try fallback upstream
    │     response = await forward_doh(request_bytes, fallback)
    │     if response:
    │         continue to Step 8
    │     else:
    │         # Both failed → SERVFAIL
    │         return SERVFAIL response
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 8: Log Query to Database (Async, Non-blocking)              │
│ File: server/api/database.py                                     │
│ Function: log_query_to_db(client_ip, domain, status)             │
│ Latency: 0ms (non-blocking)                                      │
└─────────────────────────────────────────────────────────────────┘
    │
    │ global log_queue
    │ timestamp = datetime.utcnow()
    │ log_queue.put_nowait((client_ip, domain, status, timestamp))
    │
    │ # Background worker: batch_logger_worker()
    │ # Runs in separate task:
    │ while True:
    │     batch = []
    │     # Collect 100 records or wait 2s
    │     while len(batch) < 100 and time < batch_timeout:
    │         batch.append(await log_queue.get())
    │     
    │     # Batch insert
    │     async with AsyncSessionLocal() as session:
    │         session.add_all([DNSLog(...) for entry in batch])
    │         await session.commit()
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 9: Send Response to Client                                  │
│ File: server/core/dns_server.py                                  │
│ Method: self.transport.sendto(response_bytes, addr)              │
└─────────────────────────────────────────────────────────────────┘
    │
    │ UDP Packet:
    │ - Source: 192.168.1.100:53
    │ - Dest: 192.168.1.50:54321
    │ - Response: google.com → 142.251.12.138
    │ - Query ID: 12345 (matched!)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 10: Client nhận response                                    │
│ Application: Browser / App                                       │
└─────────────────────────────────────────────────────────────────┘
    │
    │ if status == BLOCKED:
    │     Browser connect to 192.168.1.100 (sinkhole page)
    │     Display: "Domain blocked by DNS Firewall"
    │ else:
    │     Browser connect to 142.251.12.138:443
    │     Load website content
```

---

## 2. LUỒNG QUERY TỪ WAN (DoH)

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Client gửi DoH Request                                   │
│ Location: Anywhere (Public Internet)                             │
│ Protocol: HTTPS (DoH)                                            │
└─────────────────────────────────────────────────────────────────┘
    │
    │ HTTPS POST Request:
    │ - URL: https://thiencheese.me/dns-query
    │ - Header: accept: application/dns-message
    │ - Body: DNS query (wire format, binary)
    │ - Query: google.com, Type=A
    │
    │ Client apps:
    │ - Android: Intra app (by Google Jigsaw)
    │ - iOS: DNSCloak app
    │ - Browser: curl -H "accept: application/dns-message"
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Cloudflare Edge Processing                               │
│ Location: Nearest Cloudflare PoP (200+ locations globally)       │
│ Latency: +10-20ms (Internet routing)                             │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Security checks:
    │ 1. TLS termination (HTTPS → HTTP)
    │ 2. DDoS protection (HTTP flood, SYN flood)
    │ 3. WAF rules (malicious payloads)
    │ 4. Rate limiting (prevent abuse)
    │    └─> 7.24% queries blocked theo benchmark
    │ 5. Bot detection (challenge pages)
    │
    │ if passed:
    │     Forward to Cloudflare Tunnel
    │ else:
    │     Return HTTP 429 (Too Many Requests)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Cloudflare Tunnel (Encrypted Channel)                    │
│ Container: cloudflared                                           │
│ Latency: +20-30ms (tunnel overhead)                              │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Tunnel mechanism:
    │ - Persistent WebSocket connection (outbound only)
    │ - Token-based authentication
    │ - End-to-end encryption (Cloudflare Edge ↔ cloudflared)
    │ - Auto-reconnect nếu connection lost
    │
    │ cloudflared receives HTTP request from Cloudflare Edge
    │ Forward to: http://caddy:80/dns-query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Caddy Reverse Proxy                                      │
│ Container: caddy_firewall                                        │
│ Latency: +5-10ms (proxy overhead)                                │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Caddyfile routing:
    │ :80, :443 {
    │     handle /dns-query {
    │         reverse_proxy dns_server:8080
    │     }
    │ }
    │
    │ Forward HTTP POST to dns_server:8080
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Python DNS Server (DoH Handler)                          │
│ Container: dns_firewall_server                                   │
│ File: server/main.py                                             │
│ Endpoint: POST /dns-query                                        │
└─────────────────────────────────────────────────────────────────┘
    │
    │ FastAPI endpoint:
    │ @app.post("/dns-query")
    │ async def doh_query(request: Request):
    │     dns_query_bytes = await request.body()
    │     record = DNSRecord.parse(dns_query_bytes)
    │     
    │     # SAME LOGIC như LAN (Step 4-8 ở trên)
    │     # 1. Static DNS check
    │     # 2. Blacklist check
    │     # 3. Cache lookup
    │     # 4. Forward to upstream DoH
    │     # 5. Async logging
    │     
    │     return Response(
    │         content=response_bytes,
    │         media_type="application/dns-message"
    │     )
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6-10: Response Path (Reverse Direction)                     │
└─────────────────────────────────────────────────────────────────┘
    │
    │ dns_server:8080 → HTTP 200 OK (application/dns-message)
    │     ↓
    │ Caddy :80 → Forward response
    │     ↓
    │ cloudflared → Send via WebSocket tunnel
    │     ↓
    │ Cloudflare Edge → Wrap với TLS
    │     ↓
    │ Client → HTTPS 200 OK
    │     ↓
    │ Client app parse DNS response
    │     ↓
    │ Browser/App connect to resolved IP
```

### WAN vs LAN Comparison

| Step | LAN (UDP) | WAN (DoH) | Additional Latency |
|------|-----------|-----------|-------------------|
| 1. Client send | UDP packet | HTTPS POST | +0ms (same) |
| 2. Routing | Router forward | CF Edge security | +10-20ms |
| 3. Tunnel | N/A | Cloudflare Tunnel | +20-30ms |
| 4. Proxy | N/A | Caddy reverse proxy | +5-10ms |
| 5. DNS process | Same logic | Same logic | +0ms |
| **Total** | **55ms avg** | **141ms avg** | **+86ms (+156%)** |

---

## 3. SEQUENCE DIAGRAMS

### 3.1. Cache HIT Scenario (Fast Path)

```
Client          DNS Server     Static DNS     Cache
  │                 │              │            │
  │──DNS Query─────▶│              │            │
  │                 │──Check──────▶│            │
  │                 │◀─Not static──│            │
  │                 │                           │
  │                 │──Lookup──────────────────▶│
  │                 │◀─HIT (0.5ms)──────────────│
  │                 │                           │
  │                 │ (Rewrite Query ID)        │
  │◀─DNS Response───│                           │
  │                 │                           │
 0ms             0.6ms                      Total: 0.6ms
```

### 3.2. Cache MISS + Upstream Forward (Slow Path)

```
Client     DNS Server    Blacklist    Cache    Forwarder   Upstream DNS
  │            │             │          │          │            │
  │──Query────▶│             │          │          │            │
  │            │──Check─────▶│          │          │            │
  │            │◀─Allowed────│          │          │            │
  │            │──Lookup─────────────▶ │          │            │
  │            │◀─MISS───────────────── │          │            │
  │            │──Forward──────────────────────▶  │            │
  │            │             │          │          │            │
  │            │             │          │          │──DoH POST─▶│
  │            │             │          │          │ (1.1.1.1)  │
  │            │             │          │          │            │
  │            │             │          │          │◀─Response──│
  │            │             │          │◀─Store───│            │
  │◀─Response──│             │          │          │            │
  │            │             │          │          │            │
0ms          2ms          3ms        55ms      150ms      Total: 150ms
```

### 3.3. Blocked Domain Scenario

```
Client     DNS Server    Static DNS    Blacklist    Database
  │            │              │             │            │
  │──Query────▶│              │             │            │
  │ (ads.evil) │              │             │            │
  │            │──Check──────▶│             │            │
  │            │◀─Not static──│             │            │
  │            │──Check──────────────────▶  │            │
  │            │◀─BLOCKED─────────────────  │            │
  │            │ (Sinkhole response)        │            │
  │            │──Log─────────────────────────────────▶ │
  │            │  (async, non-blocking)     │            │
  │◀─Sinkhole──│              │             │            │
  │   0.0.0.0  │              │             │            │
  │            │              │             │            │
0ms          2ms                                    Total: 2ms
```

---

## 4. PERFORMANCE METRICS

### 4.1. Latency Breakdown by Path

#### Cache HIT (70% of queries)
```
Total: 0.5-1ms

Breakdown:
- UDP receive & parse:    0.05ms
- Static DNS check:       0.1ms
- Blacklist check:        0.0ms (skipped if static)
- Cache lookup:           0.3ms
- Query ID rewrite:       0.05ms
- UDP send:               0.1ms
```

#### Cache MISS + Upstream Forward (30% of queries)
```
Total: 50-150ms (avg 75ms)

Breakdown:
- UDP receive & parse:    0.05ms
- Static DNS check:       0.1ms
- Blacklist check:        1ms
- Cache lookup (miss):    0.3ms
- Round-robin select:     0.01ms
- DoH HTTP/2 connection:  5-10ms (reuse from pool)
- Upstream DNS resolve:   30-120ms
  ├─ Network RTT:         10-30ms
  ├─ Cloudflare process:  10-50ms
  └─ DNS recursion:       10-40ms
- Response parse:         0.1ms
- Cache store (async):    0ms (non-blocking)
- UDP send:               0.1ms
```

#### Blocked Domain (5-10% of queries)
```
Total: 1-2ms

Breakdown:
- UDP receive & parse:    0.05ms
- Static DNS check:       0.1ms
- Blacklist check (hit):  1-2ms
  ├─ Hash lookup:         0.5ms
  ├─ Parent check:        0.5ms
  └─ Sinkhole response:   0.5ms
- Async logging:          0ms (non-blocking)
- UDP send:               0.1ms
```

### 4.2. Query Distribution (estimated from benchmark)

```
┌─────────────────────────────────────────────────┐
│ Query Type Distribution                          │
├─────────────────────────────────────────────────┤
│ ██████████████████████████████████████ (70%)    │ Cache HIT
│ █████████████ (20%)                              │ Cache MISS (allowed)
│ ████ (7%)                                        │ Blocked domains
│ █ (2%)                                           │ NXDOMAIN
│ █ (1%)                                           │ SERVFAIL
└─────────────────────────────────────────────────┘
```

### 4.3. Throughput Limits

#### Theoretical Maximum (LAN, all cache hits)
```
Cache lookup latency: 0.5ms
Max QPS = 1000ms / 0.5ms = 2,000 QPS per core

With Python GIL:
- Effective: ~1,500 QPS per core
- Benchmark: 1,607 QPS (close to theoretical)
```

#### Actual Performance (LAN, 70% cache hit)
```
Avg latency: 55ms (includes 30% upstream forwards)
Concurrent queries: 160
Actual QPS: 1,607

Efficiency: 1607 / ((160 / 0.055) * 1000) = 55%
```

#### WAN Performance (via Cloudflare Tunnel)
```
Avg latency: 141ms
Concurrent queries: 160
Actual QPS: 188

Bottlenecks:
1. Cloudflare rate limiting (7.24% queries blocked)
2. TLS handshake timeout (160 concurrent too many)
3. Tunnel overhead (+30ms per query)
```

---

## 📚 REFERENCES

- **DNS Protocol:** RFC 1035
- **DNS over HTTPS:** RFC 8484
- **HTTP/2:** RFC 7540
- **Python asyncio:** https://docs.python.org/3/library/asyncio.html
- **dnslib:** https://github.com/paulc/dnslib
- **httpx:** https://www.python-httpx.org/
- **Cloudflare Tunnel:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

---

**Document Version:** 1.0  
**Last Updated:** December 2, 2025  
**Author:** ThienCheese
