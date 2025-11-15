# 🚀 QUICK START: Fix CGNAT với Cloudflare Tunnel

## Tại sao chọn Cloudflare Tunnel?

- ✅ **MIỄN PHÍ** - Không giới hạn bandwidth
- ✅ **DỄ SETUP** - Chỉ 15-30 phút
- ✅ **STABLE** - 99.99% uptime
- ✅ **SECURE** - TLS end-to-end + DDoS protection
- ✅ **KHÔNG CẦN VPS** - Không có chi phí phát sinh

---

## Các bước thực hiện (15-30 phút)

### BƯỚC 1: Đăng ký Cloudflare (5 phút)

1. Truy cập: https://dash.cloudflare.com/sign-up
2. Đăng ký tài khoản (free plan)
3. Xác nhận email

---

### BƯỚC 2: Tạo Cloudflare Tunnel (10 phút)

#### 2.1. Login vào Cloudflare Dashboard
```
https://one.dash.cloudflare.com/
```

#### 2.2. Tạo Tunnel
1. Click vào **Zero Trust** trong sidebar
2. Chọn **Access** → **Tunnels**
3. Click **Create a tunnel**
4. Chọn **Cloudflared**
5. Đặt tên tunnel: `nt140-firewall`
6. Click **Save tunnel**

#### 2.3. Lấy Tunnel Token
Sau khi tạo tunnel, bạn sẽ thấy một command như:
```bash
docker run cloudflare/cloudflared:latest tunnel run --token eyJh...
```

**Copy toàn bộ token** (phần sau `--token`)

---

### BƯỚC 3: Cập nhật docker-compose.yml (5 phút)

Mở file `docker-compose.yml` và thêm service `cloudflared`:

```yaml
services:
  # ... các service hiện tại (caddy, dns_server) ...

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared_tunnel
    restart: unless-stopped
    command: tunnel run
    networks:
      - nt140-net
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      - caddy
```

---

### BƯỚC 4: Cập nhật .env (2 phút)

Thêm vào file `.env`:

```bash
# Paste token từ bước 2.3
CLOUDFLARE_TUNNEL_TOKEN=eyJh...your_token_here...
```

---

### BƯỚC 5: Cấu hình Routes trong Cloudflare (5 phút)

Quay lại Cloudflare Dashboard → Tunnel → `nt140-firewall` → Tab **Public Hostname**

#### Route 1: DoH & Dashboard (HTTPS)
- **Subdomain:** `nt140firewall` (hoặc để trống nếu dùng root domain)
- **Domain:** `duckdns.org` (nếu dùng DuckDNS) HOẶC domain riêng của bạn
- **Path:** (để trống)
- **Type:** HTTPS
- **URL:** `https://caddy:443`
- **Additional settings:**
  - ✅ No TLS Verify (vì Caddy dùng self-signed cert internally)
  
Click **Save hostname**

#### Route 2: DoT (Optional - TCP)
- **Subdomain:** `dot`
- **Domain:** `nt140firewall.duckdns.org`
- **Path:** (để trống)
- **Type:** TCP
- **URL:** `tcp://caddy:853`

Click **Save hostname**

---

### BƯỚC 6: Khởi động Cloudflared (1 phút)

```bash
cd /home/cheese/Documents/Vault/Network_Secuity/Project/test
sudo docker compose up -d cloudflared
```

Kiểm tra logs:
```bash
docker logs cloudflared_tunnel -f
```

Bạn sẽ thấy:
```
INF Connection established connIndex=0
INF Registered tunnel connection
```

✅ **Nếu thấy "Connection established" = THÀNH CÔNG!**

---

### BƯỚC 7: Test từ thiết bị bên ngoài (3 phút)

#### Test DoH endpoint:

Từ smartphone (tắt WiFi, dùng 4G/5G):

```bash
# Android/iOS - Dùng app "DNS Lookup"
# Hoặc dùng browser:
https://nt140firewall.duckdns.org/dns-query

# Nên thấy error "Missing 'dns' parameter" = endpoint hoạt động!
```

Hoặc từ máy tính khác (không trong LAN):

```bash
curl "https://nt140firewall.duckdns.org/dns-query?dns=AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB"
```

#### Test Dashboard:

```bash
https://nt140firewall.duckdns.org/
```

Nhập:
- Username: `admin`
- Password: `admin` (từ file .env của bạn)

✅ **Nếu thấy dashboard = THÀNH CÔNG HOÀN TOÀN!**

---

### BƯỚC 8: Cập nhật Client Configs (5 phút)

Thiết bị giờ có thể dùng DoH endpoint từ bất kỳ đâu!

#### iOS/macOS:
1. Download file `apple_ios_mac/nt140_firewall_DoH.mobileconfig`
2. Cài đặt profile (nó đã trỏ đúng domain rồi)

#### Android:
```
Settings → Network & Internet → Private DNS
→ nt140firewall.duckdns.org
```

#### Windows:
Chạy `clients/windows/connect_firewall_DoH.ps1`

#### Test:
1. Mở browser
2. Truy cập: http://ads.example.com
3. Nên bị chuyển đến sinkhole (IP 192.168.1.100)

---

## ✅ HOÀN THÀNH!

Giờ đây:
- ✅ DoH hoạt động từ WAN (anywhere in the world)
- ✅ Dashboard truy cập được từ WAN
- ✅ DNS filtering hoạt động cả trong & ngoài LAN
- ✅ TLS/HTTPS automatic
- ✅ DDoS protection miễn phí

---

## 🔧 Troubleshooting

### Vấn đề: Cloudflared không connect
```bash
# Check logs
docker logs cloudflared_tunnel

# Common issues:
# 1. Token sai → Copy lại token từ Cloudflare
# 2. Network issue → Check internet connection
# 3. Firewall block → Allow outbound 443
```

### Vấn đề: 502 Bad Gateway
```bash
# Check Caddy đang chạy
docker ps | grep caddy

# Check Caddy logs
docker logs caddy_firewall

# Thường do Caddy chưa ready → Đợi 30s và thử lại
```

### Vấn đề: Dashboard yêu cầu password nhưng không nhận
```bash
# Check ADMIN_PASSWORD trong .env
cat .env | grep ADMIN_PASSWORD

# Restart Caddy
docker compose restart caddy
```

### Vấn đề: DNS query không hoạt động
```bash
# Check DNS server
docker logs dns_firewall_server

# Test local DNS first
dig @127.0.0.1 google.com

# Nếu local OK nhưng WAN fail → Check Cloudflare routes
```

---

## 📊 Monitoring

### Check tunnel status:
```bash
docker logs cloudflared_tunnel -f
```

### Check DNS queries:
```bash
docker logs dns_firewall_server -f
```

### Check blocked queries:
Truy cập Dashboard: https://nt140firewall.duckdns.org/

---

## 🔐 Security Recommendations

### 1. Đổi mật khẩu mặc định
```bash
# Edit .env
ADMIN_PASSWORD=your_strong_password_here

# Restart
docker compose restart
```

### 2. Enable Cloudflare Access (Optional)
Thêm layer bảo vệ cho Dashboard:
1. Cloudflare Dashboard → Zero Trust → Access → Applications
2. Create Application → Self-hosted
3. Chọn domain: `nt140firewall.duckdns.org`
4. Add policy: Emails = your_email@example.com
5. Save

Giờ chỉ email của bạn mới truy cập được dashboard!

### 3. Rate Limiting
Cloudflare tự động có rate limiting, nhưng có thể tùy chỉnh:
1. Dashboard → Security → WAF
2. Rate Limiting Rules
3. Add rule: Max 100 requests/minute per IP

---

## 📈 Next Steps

Sau khi setup xong:

1. ✅ Test từ nhiều locations khác nhau
2. ✅ Cập nhật tất cả client devices
3. ✅ Monitor performance trong 1 tuần
4. ✅ Theo dõi query logs để tune blacklist
5. ✅ Xem xét Phase 2-6 trong roadmap (Performance, Security, etc.)

---

## 💡 Tips

- **Backup tunnel token**: Lưu token vào password manager
- **Monitor usage**: Xem Cloudflare Analytics để biết traffic pattern
- **Update regularly**: `docker compose pull && docker compose up -d`
- **Check logs daily**: Đặt cronjob để alert nếu có errors

---

## 🆘 Support

Nếu gặp vấn đề:
1. Check logs: `docker logs <container_name>`
2. Check Cloudflare Tunnel status: https://one.dash.cloudflare.com/
3. Read `docs/TROUBLESHOOTING.md` (if exists)
4. Check Cloudflare Community: https://community.cloudflare.com/

---

## 🎉 Chúc mừng!

Bạn đã bypass CGNAT thành công! DNS Firewall giờ hoạt động globally! 🌍🚀
