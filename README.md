# NT140-DNS-FIREWALL

Dự án này cung cấp một giải pháp DNS Firewall mạnh mẽ, có khả năng tùy chỉnh cao, được đóng gói bằng Docker. Nó cho phép bạn chặn quảng cáo, mã độc, và các trang web theo dõi trên toàn bộ mạng của mình, đồng thời hỗ trợ các giao thức DNS mã hóa hiện đại như DNS-over-HTTPS (DoH) và DNS-over-TLS (DoT).

Nhờ tích hợp với **Cloudflare Tunnel**, hệ thống có thể được truy cập an toàn từ bất kỳ đâu trên thế giới, vượt qua các rào cản như CGNAT mà không cần IP tĩnh hay mở cổng trên router.

## ✨ Tính năng chính

- **Lọc DNS toàn diện**: Chặn các tên miền độc hại dựa trên các danh sách đen (blacklist) được cộng đồng cập nhật.
- **Hỗ trợ giao thức mã hóa**: Bảo vệ quyền riêng tư của bạn với DoH và DoT.
- **Dashboard quản trị**: Giao diện web trực quan để theo dõi thống kê, xem nhật ký truy vấn và quản lý hệ thống.
- **Giải pháp cho CGNAT**: Tích hợp sẵn Cloudflare Tunnel để truy cập từ xa một cách an toàn và dễ dàng.
- **Triển khai đơn giản**: Toàn bộ hệ thống được đóng gói trong các container Docker, dễ dàng cài đặt và quản lý với Docker Compose.
- **Hiệu năng cao**: Xây dựng trên nền tảng Caddy và Python (FastAPI), đảm bảo hiệu suất và khả năng mở rộng.
- **Tùy biến linh hoạt**: Dễ dàng thêm/bớt các nguồn blacklist, tùy chỉnh trang chặn (sinkhole), và cấu hình các tham số hệ thống.

## 🏗️ Kiến trúc sau khi tích hợp Cloudflare Tunnel

Kiến trúc mới tận dụng Cloudflare Tunnel để tạo một kết nối an toàn và bền bỉ từ mạng nội bộ ra mạng lưới toàn cầu của Cloudflare.

```
                        ┌─────────────────────────────────┐
                        │        CLOUDFLARE NETWORK       │
                        │ (your-domain.com)               │
┌───────────────┐       │                                 │
│ Client (WAN)  │──────▶│  DoH/DoT Endpoint (Port 443/853)│
└───────────────┘       │  - TLS Termination              │
                        │  - DDoS Protection              │
                        └──────────┬──────────────────────┘
                                   │ Cloudflare Tunnel (Encrypted)
                                   │ (Outbound-only connection)
                        ┌──────────▼──────────────────────┐
                        │          HOME NETWORK           │
                        │         (Behind CGNAT)          │
                        │                                 │
                        │ ┌─────────────────────────────┐ │
                        │ │      Docker Environment     │ │
                        │ │ ┌───────────────┐           │ │
                        │ │ │  Cloudflared  │           │ │
                        │ │ │   Container   │           │ │
                        │ │ └───────┬───────┘           │ │
                        │ │         │ (HTTP/TCP)        │ │
                        │ │ ┌───────▼───────┐           │ │
                        │ │ │     Caddy     │◀──────────┼─┐ ┌──────────────┐
                        │ │ │  (Container)  │           │ │ │ Client (LAN) │
                        │ │ └───────┬───────┘           │ │ └──────┬───────┘
                        │ │         │ (HTTP)            │ │        │ (Port 53)
                        │ │ ┌───────▼───────┐           │ │        │
                        │ │ │ Python DNS    │───────────┘ │
                        │ │ │    Server     │             │
                        │ │ │  (Container)  │             │
                        │ │ └───────────────┘             │
                        │ └─────────────────────────────┘ │
                        └─────────────────────────────────┘
```

**Luồng hoạt động:**
1.  **Client từ WAN**: Gửi truy vấn DoH/DoT đến tên miền của bạn (`your-domain.com`).
2.  **Cloudflare Edge**: Nhận truy vấn, xử lý TLS và chuyển tiếp nó qua Tunnel.
3.  **Cloudflared Container**: Nhận lưu lượng từ Tunnel và gửi đến Caddy.
4.  **Caddy Container**: Đóng vai trò reverse proxy, chuyển tiếp truy vấn đến Python DNS Server.
5.  **Python DNS Server**: Lọc tên miền, trả về IP thật hoặc IP của trang sinkhole.
6.  **Client từ LAN**: Vẫn có thể truy vấn trực tiếp qua cổng 53 như bình thường.

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
- **DoT Endpoint**: `dot.your-domain.com` (hoặc tên miền phụ bạn đã cấu hình)

#### Cấu hình cho Client

Có hai cách chính để cấu hình các thiết bị của bạn sử dụng DNS Firewall:

**1. Cấu hình trên từng thiết bị (Khuyên dùng cho thiết bị di động):**
- Sử dụng các endpoint DoH/DoT ở trên để cấu hình trong cài đặt mạng của điện thoại, laptop...
- **Ưu điểm:** Thiết bị của bạn sẽ được bảo vệ dù đang ở bất kỳ đâu (mạng nhà, 4G, Wi-Fi công cộng).

**2. Cấu hình trên Router (Khuyên dùng cho mạng LAN):**
- **Cách đơn giản:** Trong cài đặt DHCP của router, trỏ DNS server chính đến địa chỉ IP nội bộ của máy chủ Docker.
- **Ưu điểm:** Mọi thiết bị kết nối vào mạng LAN sẽ tự động được bảo vệ mà không cần cấu hình riêng lẻ.
- **Nhược điểm:** Chỉ hoạt động khi thiết bị đang ở trong mạng LAN.

#### Cấu hình nâng cao: Sử dụng tên miền thống nhất cho LAN và WAN

Để các thiết bị (đặc biệt là di động) có thể sử dụng **cùng một tên miền** mã hóa (ví dụ: `your-domain.com`) một cách liền mạch dù ở trong hay ngoài mạng LAN, bạn nên cấu hình router để thực hiện "Split-horizon DNS".

**Mục tiêu:** Khi thiết bị ở trong mạng LAN, router sẽ phân giải `your-domain.com` thành địa chỉ IP nội bộ (`192.168.1.100`), thay vì địa chỉ IP công cộng.

**Cách thực hiện trên router của bạn (ví dụ):**

1.  **Đặt IP tĩnh cho máy chủ:** Trong cài đặt DHCP của router, hãy đặt một địa chỉ IP tĩnh (DHCP Reservation) cho máy chủ đang chạy Docker (ví dụ: `192.168.1.100`).
2.  **Thêm bản ghi DNS tĩnh:** Tìm đến mục "DNS Hostname", "Static DNS", hoặc một mục tương tự trên router và thêm một bản ghi mới:
    *   **Hostname:** `your-domain.com` (và `dot.your-domain.com` nếu có)
    *   **IP Address:** `192.168.1.100`

**Lợi ích:**
- Một thiết bị di động có thể dùng cấu hình DoT `dot.your-domain.com` duy nhất.
- Khi ở nhà, router sẽ trả về IP nội bộ, kết nối sẽ nhanh và không đi ra ngoài Internet.
- Khi ra ngoài, DNS công cộng sẽ trả về IP của Cloudflare, và kết nối sẽ đi qua Tunnel. Trải nghiệm hoàn toàn liền mạch!

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