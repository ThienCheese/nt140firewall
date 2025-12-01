# 🛡️ DNS Firewall - Hướng dẫn Triển khai Hoàn chỉnh

Hệ thống DNS Firewall tự host tại nhà, giúp chặn quảng cáo, mã độc, và các trang web theo dõi cho **toàn bộ mạng gia đình** của bạn. Hỗ trợ truy cập an toàn từ mọi nơi với giao thức mã hóa DNS-over-HTTPS (DoH) và DNS-over-TLS (DoT).

## 📋 Mục lục
- [Tổng quan hệ thống](#-tổng-quan-hệ-thống)
- [Yêu cầu phần cứng & phần mềm](#-yêu-cầu-phần-cứng--phần-mềm)
- [Bước 1: Chuẩn bị Domain & Cloudflare](#-bước-1-chuẩn-bị-domain--cloudflare)
- [Bước 2: Cài đặt máy chủ (VM/Máy vật lý)](#-bước-2-cài-đặt-máy-chủ-vmmáy-vật-lý)
- [Bước 3: Cấu hình Cloudflare Tunnel](#-bước-3-cấu-hình-cloudflare-tunnel)
- [Bước 4: Cấu hình Router (LAN DNS)](#-bước-4-cấu-hình-router-lan-dns)
- [Bước 5: Kiểm tra & Xác minh](#-bước-5-kiểm-tra--xác-minh)
- [Khắc phục sự cố](#-khắc-phục-sự-cố)
- [Nâng cao](#-nâng-cao)

---

## 🎯 Tổng quan hệ thống

### Tính năng chính
- ✅ **Chặn quảng cáo toàn mạng**: Mọi thiết bị trong nhà được bảo vệ tự động
- ✅ **DNS mã hóa (DoH)**: Bảo vệ quyền riêng tư, chống nghe lén
- ✅ **Dashboard quản lý**: Xem thống kê, logs truy vấn DNS theo thời gian thực
- ✅ **Truy cập từ xa**: Dùng DNS Firewall ngay cả khi không ở nhà (qua 4G/5G)
- ✅ **Tự động cập nhật blacklist**: 24 giờ cập nhật một lần từ nguồn uy tín
- ✅ **Hoạt động với CGNAT**: Không cần IP tĩnh, không mở port router
- ✅ **Setup đơn giản**: Cấu hình static IP qua Netplan, không cần config router

### Sơ đồ kiến trúc
```
Internet (WAN)                    Home Network (LAN)
     │                                  │
     │  ┌─────────────────────┐         │
     └─▶│  CLOUDFLARE EDGE    │         │
        │  - DoH: port 443    │         │
        │  - DoT: port 853    │         │
        │  - TLS Termination  │         │
        └──────────┬──────────┘         │
                   │ Encrypted Tunnel   │
                   │ (Outbound only)    │
                   ▼                    │
        ┌──────────────────────┐        │
        │   HOME SERVER/VM     │        │
        │  192.168.x.x         │        │
        │ ┌──────────────────┐ │        │
        │ │ Docker Compose   │ │        │
        │ │ ┌──────────────┐ │ │        │
        │ │ │ Cloudflared  │ │ │   Client devices
        │ │ └──────┬───────┘ │ │   (Phones, PCs...)
        │ │ ┌──────▼───────┐ │ │        │
        │ │ │    Caddy     │◀┼─┼────────┘
        │ │ │ Reverse Proxy│ │ │   Port 53 (DNS)
        │ │ └──────┬───────┘ │ │
        │ │ ┌──────▼───────┐ │ │
        │ │ │  DNS Server  │ │ │
        │ │ │   (Python)   │ │ │
        │ │ │  + Blacklist │ │ │
        │ │ └──────────────┘ │ │
        │ └──────────────────┘ │
        └──────────────────────┘
            Router: 192.168.x.1
```

**📊 Cách hoạt động:**
- **Từ LAN (Trong nhà)**: Thiết bị → Router → Server port 53 → Lọc DNS
- **Từ WAN (Ngoài nhà)**: Điện thoại → Cloudflare → Tunnel → Server → Lọc DNS

---

## 💻 Yêu cầu phần cứng & phần mềm

### Phần cứng (chọn 1)
- **Máy ảo (VM)**: VMware/VirtualBox/Proxmox
  - RAM: Tối thiểu 512MB (khuyến nghị 1GB)
  - CPU: 1 core
  - Disk: 10GB
- **Máy vật lý**: Raspberry Pi, Mini PC, máy tính cũ bất kỳ


### Phần mềm
- **Hệ điều hành**: Ubuntu 22.04/24.04 hoặc Debian 11/12
- **Docker & Docker Compose**: Sẽ hướng dẫn cài đặt
- **Kết nối Internet**: Băng thông tối thiểu 10Mbps

### Tài khoản cần có
- ✅ Tài khoản Cloudflare (miễn phí): https://dash.cloudflare.com/sign-up
- ✅ Một tên miền (domain): Mua từ Namecheap, GoDaddy, hoặc bất kỳ nhà cung cấp nào

---

## 📝 Bước 1: Chuẩn bị Domain & Cloudflare

### 1.1. Mua và thêm domain vào Cloudflare

1. **Mua domain** từ nhà cung cấp (ví dụ: Namecheap, GoDaddy, Porkbun...)
   - Khuyến nghị: `.com`, `.net`, `.me` (dễ nhớ)
   - Ví dụ: `mydnsfirewall.com`

2. **Thêm domain vào Cloudflare**:
   - Đăng nhập https://dash.cloudflare.com
   - Click **"Add a Site"** → Nhập domain của bạn
   - Chọn gói **Free** (đủ dùng)
   - Cloudflare sẽ quét DNS records hiện tại

3. **Đổi Nameserver**:
   - Cloudflare sẽ cung cấp 2 nameserver (ví dụ: `adam.ns.cloudflare.com`)
   - Vào trang quản lý domain của bạn (Namecheap/GoDaddy...)
   - Đổi **Nameservers** sang nameserver của Cloudflare
   - **Chờ 5-30 phút** để DNS lan truyền (có thể đến 24h)

4. **Xác minh**:
   - Quay lại Cloudflare Dashboard
   - Đợi thông báo **"Great news! Cloudflare is now protecting your site"**

### 1.2. Tạo Cloudflare Tunnel

1. Vào **Cloudflare Zero Trust Dashboard**:
   - https://one.dash.cloudflare.com
   - Lần đầu sẽ yêu cầu đặt tên team (tùy ý, ví dụ: `myteam`)

2. Tạo Tunnel:
   - Sidebar: **Networks** → **Tunnels**
   - Click **"Create a tunnel"**
   - Chọn **Cloudflared**
   - Đặt tên tunnel (ví dụ: `dns-firewall-home`)
   - Click **Save tunnel**

3. **Lưu Token**:
   - Màn hình tiếp theo hiển thị lệnh Docker chứa token
   - Sao chép phần `--token eyJh...` (chuỗi rất dài)
   - **LƯU CẨN THẬN**, sẽ dùng ở bước sau
   - Ví dụ: `eyJhIjoiYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY...`

4. **Cấu hình Public Hostname** (bước quan trọng):
   
   **Hostname cho DoH và Dashboard:**
   - Click **"Add a public hostname"**
   - **Subdomain**: Để trống (dùng root domain) hoặc `dns`
   - **Domain**: Chọn domain của bạn
   - **Service Type**: `HTTP`
   - **URL**: `caddy:80`
   - Click **Save hostname**

**✅ Kết quả**: Bạn có endpoint:
- `https://yourdomain.com` hoặc `https://dns.yourdomain.com` (DoH + Dashboard)

**⚠️ Lưu ý về DoT (DNS-over-TLS):**
- DoT qua Cloudflare Tunnel **KHÔNG khả thi** do giới hạn kỹ thuật
- DoT chỉ hoạt động trong mạng LAN (direct connection)
- Khuyến nghị: Dùng **DoH** cho mọi thiết bị (hỗ trợ tốt hơn, hoạt động mọi nơi)

---

## 🖥️ Bước 2: Cài đặt máy chủ (VM/Máy vật lý)

### 2.1. Cài đặt Ubuntu Server

**Nếu dùng máy ảo (VMware/VirtualBox):**
1. Tải Ubuntu Server 24.04 LTS ISO: https://ubuntu.com/download/server
2. Tạo VM mới:
   - RAM: 1GB
   - CPU: 1 core
   - Disk: 10GB
   - Network: **Bridge** (để có IP trên cùng mạng LAN)
3. Cài đặt Ubuntu (chọn OpenSSH server khi được hỏi)
4. **Cấu hình Static IP qua Netplan** (quan trọng):

```bash
# Kiểm tra interface name
ip addr show

# Tìm interface (thường là eth0, ens33, enp0s3...)
# Ví dụ: inet 192.168.1.xxx/24 brd 192.168.1.255 scope global dynamic enp0s3

# Mở file cấu hình Netplan
sudo nano /etc/netplan/00-installer-config.yaml
```

Thay thế nội dung bằng (chỉnh sửa cho phù hợp với mạng của bạn):

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:  # Thay bằng interface name của bạn
      dhcp4: no
      addresses:
        - 192.168.1.100/24  # IP tĩnh bạn muốn đặt
      routes:
        - to: default
          via: 192.168.1.1  # IP router/gateway
      nameservers:
        addresses:
          - 1.1.1.1  # DNS tạm thời (sau này sẽ dùng chính server này)
          - 8.8.8.8
```

Áp dụng cấu hình:

```bash
# Kiểm tra cú pháp
sudo netplan try

# Nếu OK (kết nối SSH không bị mất), apply
sudo netplan apply

# Kiểm tra lại IP
ip addr show
```

**✅ Kết quả**: Server có IP tĩnh `192.168.1.100`, không cần cấu hình DHCP reservation trên router.

**Nếu dùng Raspberry Pi / máy vật lý:**
- Cài Ubuntu Server theo hướng dẫn chính thức
- Kết nối qua SSH từ máy tính chính
- Làm tương tự để cấu hình static IP

### 2.2. Cài đặt Docker & Docker Compose

SSH vào máy chủ và chạy các lệnh sau:

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Cho phép user hiện tại dùng Docker (không cần sudo)
sudo usermod -aG docker $USER

# Cài đặt Docker Compose
sudo apt install docker-compose-v2 

# Khởi động lại session để áp dụng quyền
newgrp docker

# Kiểm tra cài đặt
docker --version
docker compose version
```

**Kết quả mong đợi:**
```
Docker version 24.x.x
Docker Compose version v2.x.x
```

### 2.3. Clone project và cấu hình

```bash
# Clone repository
git clone https://github.com/ThienCheese/test.git
cd test

# Tạo file cấu hình từ template
cp .env.cloudflare .env

# Mở file .env để chỉnh sửa
nano .env
```

**Chỉnh sửa file `.env`:**
```env
# Thay YOUR_DOMAIN_NAME bằng domain của bạn
YOUR_DOMAIN_NAME=yourdomain.com

# Paste token từ Cloudflare Tunnel (bước 1.2)
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY...

# Đặt mật khẩu cho Dashboard (thay đổi mật khẩu mạnh)
ADMIN_PASSWORD=YourStrongPassword123!

# IP của server trong LAN (lấy ở bước 2.1)
ROUTER_IP=192.168.1.1

# IP sinkhole (trang chặn) - KHÔNG SỬA
SINKHOLE_IP=127.0.0.1

# DNS Upstream (KHÔNG SỬA nếu không rõ)
UPSTREAM_DNS_1=1.1.1.1
UPSTREAM_DNS_2=1.0.0.1
```

**Lưu file**: `Ctrl+O` → `Enter` → `Ctrl+X`

### 2.4. Tạo hash mật khẩu cho Caddy

```bash
# Thay 'YourStrongPassword123!' bằng mật khẩu bạn đã đặt ở trên
docker run --rm caddy:latest caddy hash-password --plaintext 'YourStrongPassword123!'
```

**Sao chép** chuỗi hash kết quả (bắt đầu bằng `$2a$14$...`)

**Chỉnh sửa Caddyfile:**
```bash
nano Caddyfile
```

Tìm dòng `{$ADMIN_HASH_PASSWORD}` và thay bằng hash vừa tạo:
```
basicauth {
    admin $2a$14$abcdefghijklmnopqrstuvwxyz...
}
```

**Lưu file**: `Ctrl+O` → `Enter` → `Ctrl+X`

### 2.5. Khởi động hệ thống

```bash
# Build và chạy tất cả containers
sudo docker compose up -d --build

# Kiểm tra trạng thái
docker compose ps

# Xem logs nếu có lỗi
docker compose logs -f
```

**Kết quả mong đợi:**
```
NAME                    STATUS
test-caddy-1           Up (healthy)
test-cloudflared-1     Up
test-dns_server-1      Up
```

**✅ Kiểm tra nhanh từ LAN:**
```bash
# Từ máy tính khác trong mạng LAN
nslookup google.com 192.168.1.100
```
(Thay `192.168.1.100` bằng IP server của bạn)

Nếu trả về IP → DNS server đang hoạt động! ✨

---

## 🌐 Bước 3: Cấu hình Cloudflare Tunnel

### 3.1. Kiểm tra Tunnel đã kết nối

1. Quay lại **Cloudflare Zero Trust Dashboard**
2. **Networks** → **Tunnels**
3. Tunnel của bạn phải có trạng thái **HEALTHY** (màu xanh)

Nếu **DISCONNECTED** (màu đỏ):
```bash
# Xem logs của cloudflared
docker compose logs cloudflared

# Khởi động lại nếu cần
docker compose restart cloudflared
```

### 3.2. Xác minh Public Hostname

Trong tab **Public Hostname** của tunnel, phải có:

| Hostname | Service Type | URL |
|----------|--------------|-----|
| `yourdomain.com` (hoặc `dns.yourdomain.com`) | HTTP | `caddy:80` |

### 3.3. Test từ Internet

**Test DoH:**
```bash
# Từ máy tính BẤT KỲ có Internet (không cần trong LAN)
curl -H "accept: application/dns-json" \
  "https://dns.yourdomain.com/dns-query?name=google.com&type=A"
```

**Kết quả mong đợi:** JSON response với IP của google.com

**Test Dashboard:**
- Mở trình duyệt: `https://yourdomain.com`
- Đăng nhập: username `admin`, mật khẩu là `ADMIN_PASSWORD` đã đặt
- Xem dashboard thống kê DNS

**Test DoH từ command line:**
```bash
# Test với kdig (khuyến nghị)
sudo apt install knot-dnsutils
kdig @yourdomain.com +https google.com

# Hoặc với curl (JSON format)
curl -H 'accept: application/dns-json' \
  'https://yourdomain.com/dns-query?name=google.com&type=A'
```

---

## 🔧 Bước 4: Cấu hình Router (LAN DNS)

### 4.1. Cấu hình DNS trên Router (Đơn giản)

1. **Đăng nhập vào router** (thường là `192.168.1.1` hoặc `192.168.0.1`)
2. Tìm phần **DHCP Settings** hoặc **LAN Settings**
3. Tìm mục **Primary DNS Server**
4. Đổi thành IP của DNS Firewall: `192.168.1.100`
5. **Secondary DNS**: `1.1.1.1` (backup khi server offline)
6. **Save** và **Apply** (router sẽ tự reboot)

**✅ Kết quả**: Tất cả thiết bị kết nối vào WiFi/LAN sẽ tự động dùng DNS Firewall.

### 4.2. Cấu hình cho từng thiết bị (Tùy chọn)

Nếu không muốn thay đổi router, có thể cấu hình trên từng thiết bị:

**Windows:**
1. Control Panel → Network → Change adapter settings
2. Right-click WiFi/Ethernet → Properties
3. Internet Protocol Version 4 → Properties
4. "Use the following DNS server":
   - Preferred: `192.168.1.100`
   - Alternate: `1.1.1.1`

**macOS:**
1. System Settings → Network
2. Chọn WiFi/Ethernet → Details
3. DNS → Thêm `192.168.1.100`

**Linux:**
```bash
# Sửa file resolv.conf
sudo nano /etc/resolv.conf

# Thêm dòng
nameserver 192.168.1.100
nameserver 1.1.1.1
```

### 4.3. Không cần cấu hình thêm!

✅ **Server đã có static IP** (cấu hình qua Netplan ở Bước 2.1)  
✅ **Router chỉ cần trỏ DNS** → Xong!  
✅ **Không cần DHCP reservation** hay port forwarding  
✅ **Không cần Split-Horizon DNS** (Cloudflare Tunnel tự động xử lý)

---

## ✅ Bước 5: Kiểm tra & Xác minh

### 5.1. Test từ thiết bị trong LAN

**Trên Windows:**
```cmd
nslookup google.com
```
→ Phải thấy server là `192.168.1.100`

**Trên Linux/Mac:**
```bash
dig google.com
```
→ Xem dòng `SERVER: 192.168.1.100#53`

**Test chặn quảng cáo:**
```bash
nslookup ads.google.com
```
→ Phải trả về `127.0.0.1` (bị chặn)

### 5.2. Test từ thiết bị di động

**Android (DoH qua Intra app - Khuyến nghị):**
1. Tải app **Intra** từ Google Play Store (by Google Jigsaw - miễn phí)
2. Mở Intra → **Settings** → **Select DNS-over-HTTPS Server**
3. Chọn **Custom Server URL**
4. Nhập: `https://yourdomain.com/dns-query`
5. Quay lại → Bật **ON**

**iOS (DoH qua DNSCloak):**
1. Tải app **DNSCloak** từ App Store
2. Mở app → **DNS Servers** → Thêm server mới
3. URL: `https://yourdomain.com/dns-query`
4. Protocol: **DNS-over-HTTPS**
5. Save và Enable

**Trong mạng LAN (không cần app):**
- Thiết bị tự động dùng DNS server `192.168.1.100` (qua DHCP router)
- Không cần cấu hình gì thêm!

**Test:** Mở trình duyệt, vào các trang web có nhiều quảng cáo (ví dụ: vnexpress.net) → Quảng cáo sẽ biến mất!

### 5.3. Xem thống kê trên Dashboard

1. Mở trình duyệt: `https://yourdomain.com` hoặc `http://192.168.1.100:8081` (từ LAN)
2. Đăng nhập với `admin` / mật khẩu đã đặt
3. Xem:
   - **Total Queries**: Tổng số truy vấn DNS
   - **Blocked**: Số domain bị chặn
   - **Query Logs**: Lịch sử truy vấn real-time

**📊 Các chỉ số quan trọng:**
- Queries per minute
- Block rate (% bị chặn)
- Top blocked domains
- Top queried domains

---

## 🔍 Khắc phục sự cố

### ❌ Lỗi "Container exited"

```bash
# Xem logs chi tiết
docker compose logs caddy
docker compose logs dns_server
docker compose logs cloudflared

# Khởi động lại
docker compose down
docker compose up -d --build
```

### ❌ Không kết nối được DoH từ Internet

**Kiểm tra:**
1. Cloudflare Tunnel status phải là **HEALTHY**
   ```bash
   docker compose logs cloudflared | grep "Registered tunnel"
   ```
2. Public Hostname đã cấu hình đúng (HTTP → `caddy:80`)
3. Domain đã được add vào Cloudflare và nameserver đã đổi

```bash
# Test DNS resolve
dig @1.1.1.1 yourdomain.com

# Phải trả về IP Cloudflare (104.x.x.x hoặc 172.x.x.x)

# Test DoH endpoint
curl -H 'accept: application/dns-json' \
  'https://yourdomain.com/dns-query?name=google.com&type=A'
```

### ❌ Thiết bị trong LAN không dùng DNS Firewall

1. Khởi động lại router sau khi đổi DNS
2. Khởi động lại thiết bị client hoặc chạy `ipconfig /release` → `ipconfig /renew` (Windows)
3. Kiểm tra DNS server hiện tại:
   ```bash
   # Windows
   ipconfig /all
   
   # Linux/Mac
   cat /etc/resolv.conf
   ```

### ❌ Port 53 bị chiếm

Nếu server đã chạy `systemd-resolved`:
```bash
# Kiểm tra
sudo lsof -i :53

# Tắt systemd-resolved
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved

# Chỉnh sửa DNS thủ công
sudo nano /etc/resolv.conf
```
Thêm dòng: `nameserver 1.1.1.1`

### ❌ Tunnel DISCONNECTED

```bash
# Xem logs
docker compose logs cloudflared

# Kiểm tra token
cat .env | grep CLOUDFLARE_TUNNEL_TOKEN

# Tạo tunnel mới nếu token sai
# (Quay lại Cloudflare Dashboard tạo tunnel mới)
```

---

## 🚀 Nâng cao

### Tùy chỉnh Blacklist

```bash
# Thêm domain vào blacklist thủ công
echo "ads.example.com" >> server/data/blacklist.txt

# Hoặc chỉnh sửa nguồn blacklist
nano server/data/blacklist_sources.txt
```

Hệ thống tự động cập nhật blacklist mỗi 24 giờ từ các nguồn:
- StevenBlack/hosts
- OISD
- Hagezi

### Cấu hình nâng cao cho Router

**OpenWRT/pfSense**: Dùng Dnsmasq để cấu hình chi tiết hơn
**Asus Router**: Cài Merlin firmware để có nhiều tùy chọn DNS hơn

### Benchmark hiệu năng

```bash
# Cài dnsperf
sudo apt install dnsperf

# Chạy benchmark
./benchmark.sh
```

### Sao lưu và Phục hồi

```bash
# Sao lưu cấu hình
tar -czf dns-firewall-backup.tar.gz .env Caddyfile docker-compose.yml server/data/

# Phục hồi
tar -xzf dns-firewall-backup.tar.gz
docker compose up -d
```

---

## 📚 Tài liệu tham khảo

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Caddy Documentation](https://caddyserver.com/docs/)
- [DNS-over-HTTPS RFC 8484](https://www.rfc-editor.org/rfc/rfc8484.html)
- [DNS-over-TLS RFC 7858](https://www.rfc-editor.org/rfc/rfc7858.html)

---

## 🤝 Hỗ trợ

Nếu gặp vấn đề, hãy:
1. Kiểm tra phần [Khắc phục sự cố](#-khắc-phục-sự-cố)
2. Xem logs: `docker compose logs -f`
3. Mở Issue trên GitHub: https://github.com/ThienCheese/test/issues

---

## 📄 License

MIT License - Xem file [LICENSE](LICENSE) để biết chi tiết

## 🚀 Bắt đầu

### Yêu cầu
- Một máy chủ chạy Linux (khuyến nghị Ubuntu/Debian) có cài đặt Docker và Docker Compose.
- Một tài khoản Cloudflare (miễn phí).
- Một tên miền đã được thêm vào tài khoản Cloudflare của bạn.

### Cài đặt
1.  **Clone repository:**
    ```sh
    git clone https://github.com/ThienCheese/test.git
    cd test
    ```

2.  **Cấu hình Cloudflare Tunnel:**
    - Đăng nhập vào [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
    - Đi đến `Access` -> `Tunnels`.
    - Tạo một tunnel mới và làm theo hướng dẫn để lấy `TUNNEL_TOKEN`.

3.  **Cấu hình môi trường:**
    - Sao chép tệp cấu hình mẫu:
      ```sh
      cp .env.example .env
      ```
    - Mở tệp `.env` và điền các thông tin cần thiết:
      ```env
      # Tên miền bạn đã cấu hình trên Cloudflare
      YOUR_DOMAIN_NAME=your-domain.com

      # Token từ Cloudflare Tunnel
      CLOUDFLARE_TUNNEL_TOKEN=...

      # Mật khẩu cho Dashboard (thay đổi mật khẩu này)
      ADMIN_PASSWORD=YourStrongPassword

      # (Tùy chọn) Cấu hình Upstream DNS và IP cho Sinkhole
      UPSTREAM_DNS_1=1.1.1.1
      UPSTREAM_DNS_2=1.0.0.1
      SINKHOLE_IP=127.0.0.1 
      ```

4.  **Tạo hash cho mật khẩu:**
    - Chạy lệnh sau để tạo hash cho mật khẩu quản trị của bạn. Thay `YourStrongPassword` bằng mật khẩu bạn đã chọn.
    ```sh
    docker run --rm caddy:latest caddy hash-password --plaintext 'YourStrongPassword'
    ```
    - Sao chép chuỗi hash kết quả và dán vào tệp `Caddyfile`, thay thế `{$ADMIN_HASH}`.

5.  **Khởi chạy hệ thống:**
    ```sh
    sudo docker compose up --build -d
    ```

### Cấu hình Public Hostname cho Tunnel
Sau khi tunnel hoạt động, bạn cần trỏ tên miền của mình đến nó:
1.  Trong Cloudflare Zero Trust Dashboard, vào tunnel của bạn và chọn tab `Public Hostname`.
2.  Thêm các `Public Hostname` như sau:
    - **DoH/Dashboard:**
      - **Subdomain:** `@` (hoặc `dns` nếu bạn muốn dùng `dns.your-domain.com`)
      - **Service:** `HTTP` -> `http://caddy:80`
    - **DoT:**
      - **Subdomain:** `dot` (hoặc tên khác)
      - **Service:** `TCP` -> `caddy:853`

### Sử dụng

- **Dashboard**: Truy cập `https://your-domain.com` và đăng nhập với mật khẩu bạn đã tạo.
- **DoH Endpoint**: `https://your-domain.com/dns-query`
- **Plain DNS (LAN only)**: `192.168.1.100:53`

#### Cấu hình cho Client

Có hai cách chính để cấu hình các thiết bị của bạn sử dụng DNS Firewall:

**1. Cấu hình Router (Khuyến nghị cho mạng LAN):**
- Đơn giản nhất: Trỏ DNS trong DHCP settings router đến `192.168.1.100`
- **Ưu điểm:** Mọi thiết bị kết nối WiFi/LAN tự động được bảo vệ
- **Nhược điểm:** Chỉ hoạt động trong mạng nhà

**2. Cấu hình app DoH (Khuyến nghị cho di động):**
- **Android**: Cài app **Intra** → Custom URL: `https://your-domain.com/dns-query`
- **iOS**: Cài app **DNSCloak** → Custom DoH server
- **Ưu điểm:** Bảo vệ mọi nơi (4G/5G, WiFi công cộng)
- **Nhược điểm:** Cần cài app riêng

#### Tóm tắt Setup

**✅ Đã hoàn thành:**
1. **Server có static IP** `192.168.1.100` (qua Netplan)
2. **Router DHCP** trỏ DNS đến `192.168.1.100`
3. **Cloudflare Tunnel** cho phép truy cập từ xa qua DoH
4. **Dashboard** bảo vệ bằng Basic Authentication

**🎯 Cách sử dụng:**

| Vị trí | Cấu hình | Giao thức |
|--------|----------|-----------|
| **Trong nhà (LAN)** | Tự động (qua DHCP router) | Plain DNS (port 53) |
| **Ra ngoài (4G/5G)** | App Intra/DNSCloak | DoH (HTTPS) |
| **Quản trị** | `https://yourdomain.com` | HTTPS + Auth |

**💡 Không cần:**
- ❌ Cấu hình DHCP reservation trên router
- ❌ Cấu hình Split-Horizon DNS
- ❌ Mở port forwarding
- ❌ IP công khai tĩnh

## 🔧 Tùy chỉnh

- **Danh sách đen (Blacklists)**: Thêm hoặc xóa các URL nguồn trong `server/data/blacklist_sources.txt`. Hệ thống sẽ tự động cập nhật 24 giờ một lần.
- **Trang Sinkhole**: Chỉnh sửa các tệp trong thư mục `sinkhole/` để thay đổi giao diện trang thông báo chặn.
- **Giao diện Dashboard**: Các tệp tĩnh của dashboard nằm trong `dashboard/`.

## 📈 Hiệu năng

Sử dụng `dnsperf` để đánh giá hiệu năng. Xem chi tiết trong tệp `benchmark.sh`.

## 🤝 Đóng góp
Mọi đóng góp đều được chào đón! Vui lòng tạo Pull Request hoặc mở Issue để thảo luận về các thay đổi.

## 📄 Giấy phép
Dự án này được cấp phép theo [MIT License](LICENSE).