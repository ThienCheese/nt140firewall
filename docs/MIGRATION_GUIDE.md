# So sánh: DuckDNS vs Cloudflare Tunnel

## Tổng quan thay đổi

| Khía cạnh | Cấu hình cũ (DuckDNS) | Cấu hình mới (Cloudflare) |
|-----------|----------------------|---------------------------|
| **Domain** | nt140firewall.duckdns.org | thiencheese.me (custom) |
| **TLS Management** | Caddy (Let's Encrypt DNS-01) | Cloudflare Edge |
| **Cert Renewal** | Tự động qua Caddy + DuckDNS API | Cloudflare tự động |
| **CGNAT Solution** | ❌ Không giải quyết được | ✅ Cloudflare Tunnel |
| **DoH Access** | ❌ LAN only | ✅ Global (via tunnel) |
| **DoT Access** | ⚠️ LAN only (với Layer4) | ⚠️ LAN only (no tunnel support) |
| **Dependencies** | Caddy + DuckDNS plugin | Caddy + cloudflared |
| **Static IP** | DHCP Reservation (router) | Netplan (server-side) |
| **Complexity** | Trung bình | Thấp hơn |
| **Cost** | Free | Free |

---

## Chi tiết thay đổi

### 1. Loại bỏ (Removed)

#### `Caddyfile`:
```diff
- # Plugin DuckDNS
- acme_dns duckdns {env.DUCKDNS_TOKEN}

- # Layer4 block với TLS termination
- layer4 {
-     :853 {
-         route {
-             tls
-             proxy {
-                 upstream dns_server:8053
-             }
-         }
-     }
- }

- # TLS block cho domain
- nt140firewall.duckdns.org {
-     tls {
-         dns duckdns {env.DUCKDNS_TOKEN}
-     }
- }
```

#### `.env`:
```diff
- DUCKDNS_TOKEN=6d73223e-b1d2-4f3e-b560-243b28b8172d
```

#### `docker-compose.yml`:
```diff
- ports:
-   - "80:80"      # Không cần expose nữa
-   - "443:443"    # Không cần expose nữa
-   - "443:443/udp"
-   - "853:853"    # Không cần expose nữa

- environment:
-   - DUCKDNS_TOKEN=${DUCKDNS_TOKEN}

- extra_hosts:
-   - "host.docker.internal:host-gateway"  # Không cần nữa
```

---

### 2. Thêm mới (Added)

#### `Caddyfile`:
```diff
+ # Khối toàn cục đơn giản
+ {
+     auto_https off  # Cloudflare xử lý TLS
+ }

+ # Listen trên 80 và 443 (nhận từ tunnel)
+ :80, :443 {
+     # ... handlers ...
+ }

+ # DoT endpoint đơn giản (không cần TLS)
+ :853 {
+     reverse_proxy dns_server:8053
+ }
```

#### `.env`:
```diff
+ YOUR_DOMAIN_NAME=dns.nt140-dns.me
+ CLOUDFLARE_TUNNEL_TOKEN=...
+ ADMIN_HASH_PASSWORD=...  # Dùng env variable thay vì hardcode
```

#### `docker-compose.yml`:
```diff
+ environment:
+   - ADMIN_HASH_PASSWORD=${ADMIN_HASH_PASSWORD}

+ healthcheck:
+   test: ["CMD", "wget", "..."]
+   interval: 30s

+ depends_on:
+   caddy:
+     condition: service_healthy  # Đợi Caddy sẵn sàng
```

---

### 3. Luồng dữ liệu thay đổi

#### **Trước (DuckDNS):**
```
Client WAN → ❌ CGNAT blocks → Cannot reach

Client LAN → Router → Docker Host:443
                           ↓
                      Caddy (TLS with DuckDNS cert)
                           ↓
                      dns_server
```

#### **Sau (Cloudflare Tunnel):**
```
Client WAN → Cloudflare Edge (TLS terminate)
                     ↓
          Cloudflare Tunnel (encrypted)
                     ↓
          Docker: cloudflared
                     ↓
          Docker: Caddy (HTTP only)
                     ↓
          Docker: dns_server

Client LAN → Router (với Static DNS)
                     ↓
             Direct to 192.168.1.100
                     ↓
             Docker: dns_server:53 (plain DNS)
```

---

## Lợi ích của cấu hình mới

### 1. **Đơn giản hơn**
- Không cần quản lý DuckDNS token
- Không cần cấu hình ACME DNS challenge
- Không cần Layer4 module phức tạp
- Caddy chỉ làm reverse proxy đơn giản

### 2. **Ổn định hơn**
- Cloudflare quản lý TLS (99.99% uptime)
- Không phụ thuộc vào DuckDNS API
- Auto-reconnect tunnel khi mất kết nối
- Static IP qua Netplan (không phụ thuộc DHCP router)

### 3. **Bảo mật tốt hơn**
- DDoS protection từ Cloudflare
- WAF (Web Application Firewall) sẵn có
- Rate limiting tự động
- Không expose ports ra Internet

### 4. **Linh hoạt hơn**
- Có thể thêm nhiều subdomain dễ dàng
- Có thể thêm nhiều services khác qua cùng tunnel
- Dashboard Cloudflare để monitor traffic

### 5. **Hiệu năng tốt hơn**
- Cloudflare CDN (200+ PoPs toàn cầu)
- HTTP/3 (QUIC) support
- Smart routing

---

## Migration Checklist

### Bước 1: Backup
```bash
# Backup cấu hình cũ
cp Caddyfile Caddyfile.duckdns.bak
cp docker-compose.yml docker-compose.yml.bak
cp .env .env.bak
```

### Bước 2: Update files
- [ ] Copy `.env.cloudflare` → `.env`
- [ ] Update `Caddyfile` với nội dung mới
- [ ] Update `docker-compose.yml`

### Bước 3: Setup Cloudflare
- [ ] Add domain to Cloudflare
- [ ] Create tunnel và lấy token
- [ ] Configure Public Hostnames (DoH & DoT)
- [ ] Test từ bên ngoài

### Bước 4: Deploy
```bash
# Stop containers cũ
docker compose down

# Rebuild và start
docker compose up --build -d

# Check logs
docker compose logs -f
```

### Bước 5: Verify
- [ ] Test DoH: `curl -H 'accept: application/dns-json' 'https://thiencheese.me/dns-query?name=google.com&type=A'`
- [ ] Test Dashboard: Browse to `https://thiencheese.me`
- [ ] Test Plain DNS (LAN): `dig @192.168.1.100 google.com`
- [ ] Test DoH from mobile (Intra app): Configure custom URL

### Bước 6: Update clients
- [ ] Router DHCP: Point DNS to `192.168.1.100`
- [ ] Mobile devices: Install Intra app → Custom DoH URL
- [ ] Test từ LAN và WAN (4G/5G)

---

## Rollback Plan

Nếu gặp vấn đề, có thể rollback về cấu hình DuckDNS:

```bash
# Restore files
cp Caddyfile.duckdns.bak Caddyfile
cp docker-compose.yml.bak docker-compose.yml
cp .env.bak .env

# Restart
docker compose down
docker compose up -d
```

**Lưu ý:** DuckDNS vẫn hoạt động song song với Cloudflare, không cần xóa.
