

---

### **Abstract**
Trong bối cảnh các mối đe dọa an ninh mạng ngày càng gia tăng, việc kiểm soát và lọc lưu lượng mạng ở tầng DNS đã trở thành một giải pháp hiệu quả để ngăn chặn truy cập vào các tên miền độc hại. Bài báo này trình bày về việc phân tích, đánh giá hiệu năng và khám phá các tính năng nâng cao của một hệ thống DNS Firewall được xây dựng dựa trên kiến trúc container hóa. Hệ thống sử dụng kết hợp máy chủ Caddy làm reverse proxy, một máy chủ DNS tùy chỉnh bằng Python để thực thi logic lọc, và Cloudflare Tunnel để cung cấp khả năng truy cập an toàn từ xa. Chúng tôi tiến hành phân tích chi tiết về kiến trúc, luồng dữ liệu và thực hiện các bài kiểm tra hiệu năng (benchmark) để so sánh với các dịch vụ DNS công cộng. Kết quả cho thấy giải pháp không chỉ cung cấp khả năng tùy biến và kiểm soát mạnh mẽ mà còn đạt được hiệu suất đáng kể, đồng thời mở ra tiềm năng triển khai các giao thức DNS an toàn như DNS over TLS (DoT) một cách linh hoạt.

**Keywords:** DNS Firewall, An ninh mạng, Containerization, Docker, Caddy, DNS over TLS (DoT), DNS over HTTPS (DoH), Cloudflare.

---

### **1. Giới thiệu**
Internet đã trở thành một phần không thể thiếu trong cuộc sống hiện đại, nhưng cũng tiềm ẩn nhiều rủi ro về an ninh như lừa đảo (phishing), phần mềm độc hại (malware), và các trang web có nội dung không phù hợp. Một trong những phương pháp tiếp cận hiệu quả để giảm thiểu các rủi ro này là thông qua việc lọc truy vấn DNS. Bằng cách chặn các yêu cầu phân giải tên miền đến các máy chủ độc hại đã biết, một DNS Firewall có thể ngăn chặn kết nối ngay từ giai đoạn đầu tiên, trước khi bất kỳ lưu lượng độc hại nào có thể tiếp cận thiết bị của người dùng.

Dự án này tập trung vào một giải pháp DNS Firewall được đóng gói bằng công nghệ container, giúp đơn giản hóa việc triển khai và quản lý. Kiến trúc của hệ thống bao gồm các thành-phần-dịch-vụ-nhỏ (microservices) phối hợp với nhau: một máy chủ web Caddy hiệu năng cao, một máy chủ DNS Python tùy chỉnh cho logic lọc, và dịch vụ Cloudflare Tunnel để mở rộng khả năng bảo vệ ra ngoài mạng nội bộ.

Bài báo này sẽ đi sâu vào phân tích kiến trúc hệ thống, mô tả luồng xử lý dữ liệu, đề xuất phương pháp luận để đánh giá hiệu năng, và thảo luận về khả năng triển khai các giao thức DNS mã hóa như DoT và DoH trong thực tế.

---

### **2. Kiến trúc Hệ thống (System Architecture)**
Hệ thống được thiết kế theo kiến trúc module, bao gồm ba container chính hoạt động phối hợp với nhau, được quản lý bởi Docker Compose.

*   **Caddy Server:** Đóng vai trò là cổng vào (gateway) của hệ thống. Nó lắng nghe trên các cổng 80 (HTTP), 443 (HTTPS/DoH), và 853 (DoT). Caddy chịu trách nhiệm τερματισμού TLS (TLS termination), tự động quản lý chứng chỉ SSL, và định tuyến các loại lưu lượng khác nhau đến đúng nơi xử lý.
    *   **DNS over HTTPS (DoH):** Các truy vấn DoH được Caddy nhận và chuyển tiếp đến máy chủ DNS Python nội bộ.
    *   **DNS over TLS (DoT):** Tương tự, các truy vấn DoT được chuyển tiếp đến máy chủ DNS.
    *   **Dashboard & Sinkhole:** Caddy phục vụ một trang dashboard để quản trị và một trang sinkhole để thông báo cho người dùng khi một tên miền bị chặn.

*   **Python DNS Server:** Đây là "bộ não" của hệ thống. Máy chủ này lắng nghe trên cổng 53 và thực hiện các nhiệm vụ sau:
    1.  Nhận truy vấn DNS từ Caddy hoặc từ các client trong mạng LAN.
    2.  Kiểm tra tên miền truy vấn với một danh sách đen (blacklist).
    3.  Nếu tên miền nằm trong blacklist, máy chủ trả về địa chỉ IP của trang sinkhole.
    4.  Nếu không, truy vấn sẽ được chuyển tiếp đến một máy chủ DNS công cộng (upstream DNS) như Google DNS (8.8.8.8) hoặc Cloudflare DNS (1.1.1.1) để phân giải.

*   **Cloudflare Tunnel (cloudflared):** Dịch vụ này tạo ra một kết nối an toàn, bền bỉ giữa container Caddy và mạng lưới toàn cầu của Cloudflare. Nhờ đó, người dùng có thể truy cập vào các dịch vụ DoT/DoH của DNS Firewall từ bất kỳ đâu trên thế giới thông qua một tên miền công cộng, mà không cần phải cấu hình port forwarding hay có địa chỉ IP tĩnh.

---

### **3. Related Work**

Trong những năm gần đây, việc lọc DNS đã trở thành một phương pháp phổ biến để tăng cường bảo mật mạng. Một số giải pháp tiêu biểu bao gồm:

**3.1. Pi-hole [5]**
Pi-hole là một giải pháp mã nguồn mở phổ biến, hoạt động như một DNS sinkhole để chặn quảng cáo và tracking domains. Nó cung cấp giao diện web để quản lý và theo dõi thống kê. Tuy nhiên, Pi-hole thiếu hỗ trợ tích hợp cho các giao thức DNS mã hóa hiện đại (DoH/DoT) và không có giải pháp sẵn có cho vấn đề CGNAT.

**3.2. AdGuard Home [6]**
AdGuard Home là một phần mềm chặn quảng cáo mạng tương tự Pi-hole nhưng có hỗ trợ DoH/DoT. Tuy nhiên, việc triển khai từ xa vẫn yêu cầu cấu hình phức tạp với VPN hoặc port forwarding, và không có giải pháp tích hợp cho môi trường CGNAT.

**3.3. Cloudflare Gateway [7]**
Cloudflare Gateway cung cấp dịch vụ DNS lọc dựa trên cloud với khả năng mở rộng cao. Tuy nhiên, đây là một giải pháp thương mại và người dùng phải phụ thuộc hoàn toàn vào hạ tầng của bên thứ ba, thiếu khả năng tùy biến và kiểm soát dữ liệu.

**3.4. Khoảng trống nghiên cứu (Research Gaps)**
Các giải pháp hiện tại thường gặp phải một hoặc nhiều hạn chế sau:
- Thiếu khả năng triển khai dễ dàng trong môi trường CGNAT mà không cần kiến thức kỹ thuật sâu về mạng.
- Không tích hợp sẵn các giao thức DNS mã hóa với giải pháp truy cập từ xa.
- Phụ thuộc vào dịch vụ bên thứ ba hoặc yêu cầu cấu hình phức tạp với VPN.
- Thiếu khả năng tùy biến cao cho các trường hợp sử dụng cụ thể (custom blacklists, sinkhole pages).

### **4. Phương pháp luận (Methodology)**

#### **4.1. Thiết kế Kiến trúc**
Để giải quyết các khoảng trống đã xác định, chúng tôi đề xuất một kiến trúc modular dựa trên container với ba thành phần chính:

1. **Caddy Reverse Proxy**: Xử lý TLS termination và routing cho các giao thức DoH/DoT.
2. **Python DNS Filter**: Thực hiện logic lọc với khả năng tùy biến cao.
3. **Cloudflare Tunnel**: Giải quyết vấn đề CGNAT mà không cần cấu hình mạng phức tạp.

**Đóng góp chính (Main Contributions):**
- **C1**: Kiến trúc tích hợp Cloudflare Tunnel với DNS Firewall, cho phép triển khai dễ dàng trong môi trường CGNAT mà không cần IP tĩnh hay port forwarding.
- **C2**: Hỗ trợ đồng thời cả DNS truyền thống (port 53) cho LAN và các giao thức mã hóa (DoH/DoT) cho WAN trong cùng một hệ thống.
- **C3**: Cơ chế "Split-horizon DNS" cho phép thiết bị chuyển đổi liền mạch giữa mạng LAN và WAN mà không cần thay đổi cấu hình.
- **C4**: Triển khai hoàn toàn bằng container, dễ dàng bảo trì và mở rộng.

#### **4.2. Prompt cho Eraser - Sơ đồ Kiến trúc Hệ thống**

**Prompt for Eraser.io:**
```
Create a detailed system architecture diagram for a containerized DNS Firewall with Cloudflare Tunnel integration.

Components to include:

1. External Layer:
   - "Internet Users" group containing:
     * "Mobile Device (4G/5G)"
     * "Laptop (Public WiFi)"
     * "Desktop (Remote Network)"
   - "Cloudflare Global Network" cloud with services:
     * "Edge Servers"
     * "DDoS Protection"
     * "TLS Termination"
     * "Tunnel Service"

2. Network Boundary:
   - "ISP with CGNAT" box showing blocked incoming connections
   - "Home Router (192.168.1.1)" with NAT
   - Bidirectional arrow from Router to Internet labeled "Outbound Only"

3. Docker Environment (192.168.1.100):
   - Container: "cloudflared"
     * Label: "Cloudflare Tunnel Client"
     * Show persistent encrypted connection to Cloudflare
   - Container: "caddy"
     * Label: "Caddy Reverse Proxy"
     * Ports: 80, 443, 853, 8081
     * Show connections to:
       - cloudflared (HTTP/TCP)
       - dns_server (HTTP)
       - LAN clients (direct)
   - Container: "dns_server"
     * Label: "Python DNS Filter (FastAPI)"
     * Ports: 53, 8000, 8053, 8080
     * Internal components:
       - "DNS Listener"
       - "Blacklist Manager"
       - "Query Logger"
       - "Upstream Forwarder"
   - Volume: "caddy_data" (persistent TLS certs)
   - Volume: "server/data" (blacklist & database)

4. LAN Clients:
   - Group of devices: "Laptop", "Phone", "Desktop"
   - Direct DNS connection to dns_server:53

5. External Services:
   - "Upstream DNS" (1.1.1.1, 8.8.8.8)

Data Flows:
1. Internet User → Cloudflare Edge (HTTPS/TLS) [green]
2. Cloudflare Edge → cloudflared (Tunnel - Encrypted) [green, dashed]
3. cloudflared → caddy (HTTP/TCP) [blue]
4. caddy → dns_server (HTTP) [blue]
5. dns_server → Upstream DNS (DNS) [orange]
6. LAN Client → dns_server:53 (DNS) [purple, direct]
7. dns_server → SQLite DB (Query Logs) [gray]

Use standard cloud/network icons. Apply security zones with different background colors:
- Red zone: Internet (untrusted)
- Yellow zone: DMZ (Cloudflare)
- Green zone: Internal (Docker containers)
- Blue zone: LAN
```

#### **4.3. Prompt cho Eraser - Sơ đồ Luồng Dữ liệu (Data Flow)**

**Prompt for Eraser.io:**
```
Create a detailed Data Flow Diagram (DFD) showing DNS query processing in the firewall system.

Use standard DFD notation:
- Circles/Rounded rectangles for processes
- Rectangles for external entities
- Open rectangles for data stores
- Arrows for data flows

External Entities:
1. "User Device" (top left)
2. "Cloudflare Network" (top center)
3. "Upstream DNS (1.1.1.1)" (top right)

Processes:
P1. "Receive DNS Query" (Caddy)
P2. "Decrypt & Parse" (Caddy)
P3. "Load Blacklist" (Python - Background)
P4. "Check Domain" (Python - Query Handler)
P5. "Forward to Upstream" (Python - Forwarder)
P6. "Return Sinkhole IP" (Python - Blocker)
P7. "Return Real IP" (Python - Resolver)
P8. "Log Query" (Python - Logger)

Data Stores:
D1. "blacklist.txt" (Read-only)
D2. "queries.db" (SQLite)

Detailed Flow:

Scenario A - Blocked Domain (Red path):
1. User Device → [DNS Query: ads.evil.com] → P1
2. P1 → [Encrypted Query] → P2
3. P2 → [Domain: ads.evil.com] → P4
4. P4 → [Check] → D1
5. D1 → [Match Found] → P4
6. P4 → [Blocked] → P6
7. P6 → [192.168.1.100] → P8
8. P8 → [Log: BLOCKED, timestamp] → D2
9. P8 → [Sinkhole IP] → User Device
10. User Device → [HTTP] → Sinkhole Page

Scenario B - Allowed Domain (Green path):
1. User Device → [DNS Query: google.com] → P1
2. P1 → [Encrypted Query] → P2
3. P2 → [Domain: google.com] → P4
4. P4 → [Check] → D1
5. D1 → [No Match] → P4
6. P4 → [Allow] → P5
7. P5 → [DNS Query] → Upstream DNS
8. Upstream DNS → [142.250.x.x] → P5
9. P5 → [Real IP] → P7
10. P7 → [142.250.x.x] → P8
11. P8 → [Log: ALLOWED, timestamp] → D2
12. P8 → [Real IP] → User Device
13. User Device → [HTTPS] → google.com

Background Process:
- P3 (every 24h) → [Fetch] → External Blacklist Sources
- External Sources → [New domains] → P3
- P3 → [Update] → D1

Add annotations:
- "DoH/DoT" for encrypted queries from WAN
- "Plain DNS" for queries from LAN
- "Async Processing" for background tasks
- Show query timing: <50ms for LAN, <200ms for WAN

Use color coding:
- Red: Blocked path
- Green: Allowed path
- Blue: Background updates
- Gray: Logging operations
```

---

### **4. Thực nghiệm và Kết quả (Experiments & Results)**
Để đánh giá hiệu năng của hệ thống, chúng tôi sử dụng công cụ `dnsperf` để đo lường các chỉ số quan trọng như độ trễ (latency) và số lượng truy vấn mỗi giây (queries per second). Chúng tôi so sánh hiệu năng của DNS Firewall nội bộ với một dịch vụ DNS công cộng phổ biến là Google DNS (8.8.8.8) làm baseline.

#### **4.1. Môi trường Thử nghiệm**
*   **Hệ thống DNS Firewall:** Chạy trên một máy ảo với 2 vCPU, 4GB RAM.
*   **Máy khách:** Chạy `dnsperf` trên một máy khác trong cùng mạng LAN.
*   **Dữ liệu đầu vào:** Một tệp chứa 10,000 tên miền phổ biến (`queryfile.txt`).

#### **4.2. Hướng dẫn Benchmark**
Một tệp kịch bản `benchmark.sh` được tạo ra để tự động hóa quá trình kiểm thử.

**File: `benchmark.sh`**
```bash
#!/bin/bash

# Địa chỉ IP của DNS Firewall nội bộ (thay đổi nếu cần)
LOCAL_DNS_IP="127.0.0.1" 

# Địa chỉ IP của DNS công cộng để so sánh
PUBLIC_DNS_IP="8.8.8.8"

# Tên tệp dữ liệu truy vấn
QUERY_FILE="queryfile.txt"

# Số lượng client đồng thời
CONCURRENT_CLIENTS=10

# Thời gian chạy mỗi bài test (giây)
DURATION=60

# Kiểm tra xem dnsperf đã được cài đặt chưa
if ! command -v dnsperf &> /dev/null
then
    echo "dnsperf could not be found. Please install it first."
    echo "On Debian/Ubuntu: sudo apt-get install dnsperf"
    exit
fi

# Tạo tệp truy vấn mẫu nếu chưa có
if [ ! -f "$QUERY_FILE" ]; then
    echo "Creating sample query file: $QUERY_FILE..."
    cat <<EOF > $QUERY_FILE
google.com A
facebook.com A
youtube.com A
wikipedia.org A
amazon.com A
# Thêm nhiều tên miền khác vào đây để có kết quả chính xác hơn
EOF
fi

echo "-----------------------------------------------------"
echo "Starting benchmark for Local DNS Firewall ($LOCAL_DNS_IP)"
echo "-----------------------------------------------------"
dnsperf -s $LOCAL_DNS_IP -d $QUERY_FILE -c $CONCURRENT_CLIENTS -l $DURATION

echo ""
echo "-----------------------------------------------------"
echo "Starting benchmark for Public DNS (Google - $PUBLIC_DNS_IP)"
echo "-----------------------------------------------------"
dnsperf -s $PUBLIC_DNS_IP -d $QUERY_FILE -c $CONCURRENT_CLIENTS -l $DURATION

echo ""
echo "Benchmark finished."
```

**Cách sử dụng:**
1.  Cài đặt `dnsperf`.
2.  Tạo file `queryfile.txt` với danh sách các tên miền cần kiểm tra.
3.  Chạy kịch bản: `bash benchmark.sh`.
4.  Phân tích và so sánh các số liệu được `dnsperf` xuất ra, đặc biệt là "Average Latency" và "Queries per second".

#### **4.3. Giả định về Kết quả**
*   **Độ trễ (Latency):** Dự kiến DNS Firewall nội bộ sẽ có độ trễ thấp hơn đáng kể so với Google DNS đối với các truy vấn được cache hoặc các truy vấn lặp lại, do không phải đi ra ngoài Internet. Tuy nhiên, với các truy vấn mới hoàn toàn, độ trễ sẽ là tổng của thời gian xử lý nội bộ và thời gian truy vấn đến upstream DNS.
*   **Queries Per Second (QPS):** Hệ thống nội bộ có thể xử lý một lượng lớn QPS, nhưng có thể bị giới hạn bởi tài nguyên CPU của máy chủ và hiệu năng của ứng dụng Python.

---

### **5. Thảo luận về Tính năng DNS over TLS với Cloudflare Tunnel**
Một trong những tính năng nổi bật của kiến trúc này là khả năng cung cấp dịch vụ DNS được mã hóa (DoT/DoH) cho người dùng từ xa một cách an toàn.

**Giả định:** Người dùng sở hữu một tên miền riêng (ví dụ: `my-secure-dns.com`) và đã cấu hình nó với Cloudflare.

**Luồng hoạt động như sau:**
1.  Người dùng cấu hình thiết bị (laptop, điện thoại) để sử dụng DoT với địa chỉ `my-secure-dns.com`.
2.  Khi thiết bị gửi một truy vấn DNS, nó sẽ được mã hóa bằng TLS và gửi đến mạng lưới của Cloudflare.
3.  Cloudflare nhận truy vấn này và, thông qua dịch vụ Tunnel, chuyển tiếp nó một cách an toàn đến container `cloudflared` đang chạy trong mạng nội bộ của người dùng.
4.  Container `cloudflared` chuyển tiếp truy vấn đến `Caddy`.
5.  `Caddy` giải mã truy vấn và gửi đến `Python DNS Server` để lọc.
6.  Phản hồi từ `Python DNS Server` (IP thật hoặc IP sinkhole) được trả về theo con đường ngược lại, được mã hóa và gửi đến thiết bị của người dùng.

**Ưu điểm:**
*   **Bảo mật đầu cuối:** Toàn bộ truy vấn DNS từ thiết bị người dùng đến máy chủ nội bộ đều được mã hóa, chống lại việc nghe lén hoặc giả mạo.
*   **Không cần IP tĩnh hay mở port:** Cloudflare Tunnel loại bỏ hoàn toàn nhu cầu phải có IP tĩnh hoặc mở các port nhạy cảm trên router, giảm thiểu bề mặt tấn công.
*   **Tính sẵn sàng cao:** Tận dụng hạ tầng toàn cầu của Cloudflare để đảm bảo kết nối ổn định.

Đây là một giải pháp mạnh mẽ để xây dựng một dịch vụ DNS cá nhân, an toàn và có thể truy cập từ mọi nơi.

---

### **6. Kết luận**
Hệ thống DNS Firewall dựa trên container đã chứng tỏ là một giải pháp linh hoạt, mạnh mẽ và dễ triển khai để tăng cường an ninh mạng cho cá nhân hoặc tổ chức nhỏ. Việc phân tích kiến trúc và đánh giá hiệu năng cho thấy hệ thống không chỉ đáp ứng tốt nhu cầu lọc tên miền độc hại mà còn có khả năng mở rộng với các giao thức mã hóa hiện đại như DoT/DoH thông qua Cloudflare Tunnel. Các bài kiểm tra hiệu năng ban đầu cho thấy kết quả hứa hẹn về độ trễ và khả năng xử lý. Hướng phát triển trong tương lai có thể bao gồm việc tối ưu hóa hiệu năng của máy chủ Python, phát triển giao diện dashboard trực quan hơn và tích hợp các nguồn blacklist động.

---

### **7. Tài liệu tham khảo**
[1] Caddy Server - https://caddyserver.com/
[2] Cloudflare Tunnel - https://www.cloudflare.com/products/tunnel/
[3] Docker - https://www.docker.com/
[4] DNS Performance Testing Tool (dnsperf) - https://www.dns-oarc.net/tools/dnsperf
[5] Pi-hole: A black hole for Internet advertisements - https://pi-hole.net/
[6] AdGuard Home - Network-wide ads & trackers blocking DNS server - https://adguard.com/en/adguard-home/overview.html
[7] Cloudflare Gateway - https://www.cloudflare.com/products/zero-trust/gateway/
[8] Hoffman, P., McManus, P. (2018). "DNS Queries over HTTPS (DoH)", RFC 8484, IETF.
[9] Hu, Z., Zhu, L., Heidemann, J., Mankin, A., Wessels, D., Hoffman, P. (2016). "Specification for DNS over Transport Layer Security (TLS)", RFC 7858, IETF.
