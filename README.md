# NT140 DNS Firewall

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-compose-blue.svg)
![Platform](https://img.shields.io/badge/platform-linux-green.svg)

Một giải pháp DNS Firewall và Ad-Blocker toàn diện, hiệu suất cao, được containerized với Docker. Hệ thống sử dụng **Caddy** làm reverse proxy (cung cấp DoH, DoT, Dashboard) và backend **Python FastAPI** để thực hiện lọc DNS và ghi log.

## 🚀 Tính năng chính

### 🛡️ Bảo mật đa giao thức
- **DNS truyền thống**: Chặn quảng cáo/phần mềm độc hại qua DNS (UDP/TCP port 53)
- **DNS-over-HTTPS (DoH)**: Bảo mật DNS qua HTTPS (port 443)
- **DNS-over-TLS (DoT)**: Mã hóa DNS qua TLS (port 853)

### 📊 Giao diện quản trị
- **Web Dashboard**: Interface quản trị được bảo vệ mật khẩu
- **Real-time monitoring**: Thống kê và logs truy vấn theo thời gian thực
- **RESTful API**: Endpoint để tích hợp với các hệ thống khác

### 🌐 Hỗ trợ mạng LAN
- **Setup Guide**: Trang hướng dẫn kết nối cho client (port 8081)
- **Multi-platform**: Script kết nối cho Windows, macOS, Linux, iOS
- **Smart Sinkhole**: Chuyển hướng domain bị chặn đến trang thông báo

### ⚙️ Tự động hóa
- **Auto SSL/TLS**: Caddy tự động quản lý chứng chỉ qua Let's Encrypt
- **Auto Blacklist Update**: Python tự động cập nhật danh sách chặn từ nhiều nguồn
- **Health Monitoring**: Tự động kiểm tra và khôi phục service

## 🏗️ Kiến trúc hệ thống

### Container `caddy` (Reverse Proxy & Web Server)
```
┌─────────────────────────────────────────┐
│              Caddy Container            │
├─────────────────────────────────────────┤
│ Port 443  │ Dashboard + DoH             │
│ Port 853  │ DoT (caddy-l4 plugin)       │
│ Port 80   │ HTTP Redirect + Sinkhole    │
│ Port 8081 │ LAN Setup Guide             │
└─────────────────────────────────────────┘
```

**Chức năng chính:**
- Reverse proxy cho tất cả traffic HTTP/HTTPS
- Tự động quản lý SSL/TLS certificates via Let's Encrypt & DuckDNS
- Phục vụ dashboard, sinkhole page và setup guide
- Xử lý DoH và DoT connections

### Container `dns_server` (DNS Processing Engine)
```
┌─────────────────────────────────────────┐
│           Python FastAPI Server        │
├─────────────────────────────────────────┤
│ Port 53   │ Raw DNS Queries (UDP/TCP)   │
│ Internal  │ REST API for Dashboard      │
│ Internal  │ Database Logging            │
└─────────────────────────────────────────┘
```

**Chức năng chính:**
- Nhận và xử lý DNS queries từ port 53
- Lọc domains dựa trên blacklist
- Forward queries hợp lệ đến upstream DNS
- Ghi logs và thống kê vào database
- Cung cấp API cho dashboard
- Tự động cập nhật blacklist từ multiple sources

## 📋 Yêu cầu hệ thống

### ✅ Phần cứng tối thiểu
- **RAM**: 512MB trở lên 
- **Storage**: 2GB free space
- **CPU**: Single core (ARM/x86_64 supported)
- **Network**: Ethernet connection khuyến nghị

### 🖥️ Hệ điều hành được hỗ trợ
- Ubuntu 20.04 LTS trở lên (Đã test)
- Debian 11 trở lên  
- CentOS 8 / RHEL 8 trở lên
- Raspberry Pi OS
- Any Linux distro with systemd

### 🛠️ Software dependencies
- **Docker Engine**: 20.10+ 
- **Docker Compose**: v2.0+ (plugin version)
- **Docker Buildx**: Cho multi-platform builds
- **Git**: Để clone source code

### 🌐 Network requirements  
- **Static IP**: Máy chủ cần có static IP trong LAN (VD: `192.168.1.100`)
- **Hostname**: Hostname được set cho máy chủ
- **Domain**: DuckDNS domain miễn phí (VD: `your-domain.duckdns.org`)
- **DuckDNS Token**: API token từ tài khoản DuckDNS

### ⚠️ Lưu ý đặc biệt cho Router ZTE F670Y
- **Không cần Port Forwarding**: Router ZTE F670Y model này có cơ chế tự động forward
- Port 53, 80, 443, 853, 8081 sẽ tự động accessible từ WAN
- Chỉ cần đảm bảo static IP và hostname đã được set đúng

## 🚀 Hướng dẫn cài đặt (Tested trên Ubuntu)

### Bước 1: Cài đặt Docker Stack

#### 1.1 Cài đặt Docker Engine, Docker Compose v2, và Docker Buildx

```bash
# Cập nhật package list
sudo apt update && sudo apt upgrade -y

# Cài đặt dependencies
sudo apt install -y ca-certificates curl gnupg lsb-release git

# Thêm Docker GPG key và repository
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Cài đặt Docker Engine với Compose v2 và Buildx
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin

# Thêm user vào docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
docker buildx version
```

**Expected output:**
```
Docker version 24.0.x
Docker Compose version v2.x.x
docker-buildx github.com/docker/buildx v0.x.x
```

### Bước 2: Giải phóng Port 53

#### 2.1 Tắt systemd-resolved DNS Stub Listener

Hầu hết Ubuntu distributions chạy `systemd-resolved` trên port 53, gây conflict với DNS server container.

```bash
# Kiểm tra service đang sử dụng port 53
sudo netstat -tulpn | grep :53

# Edit systemd-resolved config
sudo nano /etc/systemd/resolved.conf
```

Tìm và chỉnh sửa dòng sau (uncomment và set = no):
```ini
[Resolve]
DNSStubListener=no
```

Restart service và verify:
```bash
# Restart systemd-resolved
sudo systemctl restart systemd-resolved

# Verify port 53 is free
sudo netstat -tulpn | grep :53
# Should return empty (no output)

# Check DNS still working
nslookup google.com
```

### Bước 3: Cấu hình Static IP và Hostname

#### 3.1 Set Static IP cho máy host

**Xác định interface name:**
```bash
# List network interfaces
ip link show
# Thường là: ens33, enp0s3, eth0, etc.
```

**Configure static IP với netplan:**
```bash
# Edit netplan config (thay ens33 với interface của bạn)
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    ens33:  # Thay bằng interface name của bạn (ví dụ: enp0s3, eth0)
      dhcp4: false
      addresses:
        - 192.168.1.100/24  # Static IP - thay đổi theo subnet của bạn
      gateway4: 192.168.1.1   # Router IP
      nameservers:
        addresses: [1.1.1.1, 1.0.0.1]  # Temporary DNS
```

Apply network changes:
```bash
# Test netplan config
sudo netplan try

# Apply permanently (sau khi confirm)
sudo netplan apply

# Verify new IP
ip addr show
ping 192.168.1.1  # Test gateway connectivity
```

#### 3.2 Set Hostname cho máy chủ

```bash
# Set hostname (thay 'dns-firewall' bằng tên bạn muốn)
sudo hostnamectl set-hostname dns-firewall

# Add hostname to /etc/hosts
echo "127.0.0.1 dns-firewall" | sudo tee -a /etc/hosts

# Verify hostname
hostnamectl status
hostname
```

### Bước 4: Clone và Cấu hình Project

#### 4.1 Clone source code

```bash
# Clone repository 
git clone <your-repository-url>
cd nt140-dns-firewall

# Verify project structure
ls -la
```

#### 4.2 Cấu hình DuckDNS (Optional for external access)

Nếu muốn truy cập từ bên ngoài mạng:

1. Truy cập [duckdns.org](https://www.duckdns.org) và đăng nhập
2. Tạo subdomain mới (VD: `mydns.duckdns.org`) 
3. Point subdomain đến **Public IP** của router
4. Copy **token** từ account page

#### 4.3 Environment Configuration  

```bash
# Copy và edit config
cp .env.example .env
nano .env
```

**Cấu hình `.env` file:**
```bash
# DuckDNS API Token (để empty nếu chỉ dùng local)
DUCKDNS_TOKEN=your_duckdns_token_here

# Static IP của server trong LAN
SINKHOLE_IP=192.168.1.100  

# Gateway/Router IP  
ROUTER_IP=192.168.1.1

# Upstream DNS servers
UPSTREAM_DNS_1=1.1.1.1
UPSTREAM_DNS_2=1.0.0.1

# Admin credentials
ADMIN_PASSWORD=strong_secret_password
ADMIN_HASH_PASSWORD=  # Sẽ generate sau
```

#### 4.4 Generate Dashboard Password

```bash
# Generate bcrypt hash for dashboard password
docker run --rm caddy:latest caddy hash-password --plaintext 'your_dashboard_password'
```

Copy output hash và paste vào `ADMIN_HASH_PASSWORD` trong `.env`.

### Bước 5: Deployment

#### 5.1 Build và khởi chạy containers

```bash
# Build và start all services (như bạn đã làm)
docker compose up --build -d

# Verify containers are running
docker compose ps

# Check logs
docker compose logs -f
```

**Expected output:**
```
NAME                   IMAGE                               STATUS
caddy_firewall         nt140-dns-firewall-caddy           Up 
dns_firewall_server    nt140-dns-firewall-dns_server      Up
```

#### 5.2 Verify Services hoạt động

**Test DNS Server:**
```bash
# Test local DNS resolution
dig @127.0.0.1 google.com
dig @192.168.1.100 google.com

# Test DNS filtering (nếu có domain bị block)
dig @127.0.0.1 doubleclick.net
```

**Test Web Services:**
```bash
# Test setup guide page
curl -I http://192.168.1.100:8081

# Test sinkhole page
curl -I http://192.168.1.100
```

## 📱 Sử dụng DNS Firewall

### Cấu hình Client Devices

#### Cho tất cả thiết bị trong LAN:

**Truy cập Setup Guide:**
```
http://192.168.1.100:8081
```

**Manual Configuration:**
- Primary DNS: `192.168.1.100`
- Secondary DNS: `1.1.1.1` (backup)

#### Android/iOS:
- WiFi Settings → Modify Network → Advanced → DNS
- Set DNS1: `192.168.1.100`

#### Windows:
- Control Panel → Network → Change Adapter Settings
- Properties → IPv4 → Use following DNS servers
- Preferred: `192.168.1.100`

#### Router-level (Recommended):
- Access router admin (usually `192.168.1.1`)
- Set Primary DNS: `192.168.1.100`
- Tất cả devices sẽ tự động sử dụng DNS firewall

### Truy cập Dashboard

**Local access:**
```
https://192.168.1.100:443
```

**Login credentials:**
- Username: `admin`
- Password: `<password_you_set>`

## 🛠️ Troubleshooting

### Lỗi thường gặp:

#### **Container không start được:**
```bash
# Check Docker service
sudo systemctl status docker

# Check port conflicts
sudo netstat -tulpn | grep -E ":(53|80|443|853|8081)"

# Restart containers
docker compose restart
```

#### **DNS không hoạt động:**
```bash
# Check DNS server logs
docker logs dns_firewall_server -f

# Test DNS directly
dig @127.0.0.1 google.com +short

# Check if port 53 is free
sudo netstat -tulpn | grep :53
```

#### **Dashboard không accessible:**
```bash
# Check Caddy logs
docker logs caddy_firewall -f

# Test HTTP connectivity
curl -I http://192.168.1.100:8081
```

## 🔧 Maintenance Commands

```bash
# View logs
docker compose logs -f

# Restart specific service
docker compose restart dns_server
docker compose restart caddy

# Update containers
docker compose pull
docker compose up -d

# Backup configuration
cp .env .env.backup
cp Caddyfile Caddyfile.backup

# Clean unused Docker resources
docker system prune -f
```

## 📊 Performance Notes

**Tested Environment:**
- OS: Ubuntu 22.04 LTS
- Hardware: 2GB RAM, 2 CPU cores
- Network: Gigabit Ethernet
- Router: ZTE F670Y (no port forwarding needed)

**Performance Metrics:**
- DNS Resolution: < 50ms average
- Concurrent connections: 100+ devices
- Memory usage: ~200MB total
- CPU usage: < 5% under normal load

## 🎯 Tính năng đặc biệt cho ZTE F670Y

Router ZTE F670Y có những đặc điểm sau:
- **Auto Port Forwarding**: Tự động mở ports cho services
- **UPnP Support**: Không cần manual port configuration
- **Built-in DNS Override**: Hỗ trợ NAT loopback tự động
- **IPv6 Ready**: Sẵn sàng cho IPv6 DNS filtering

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Test trên môi trường tương tự (Ubuntu + ZTE F670Y)
4. Submit pull request với documentation updates

## 📄 License

MIT License - see LICENSE file for details.

---

**✨ Đã test thành công trên:**
- Ubuntu 22.04 LTS
- Docker 24.0.x + Compose v2.x + Buildx
- ZTE F670Y Router (no port forwarding required)
- Static IP configuration với netplan
- systemd-resolved disabled (DNSStubListener=no)

**🚀 Deployment đơn giản:** Chỉ cần `docker compose up --build -d` sau khi complete setup!
