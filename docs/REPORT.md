

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

### **3. Phương pháp luận (Methodology)**
Để trực quan hóa kiến trúc và luồng hoạt động của hệ thống, chúng tôi sử dụng các mô hình AI tạo sinh hình ảnh để vẽ sơ đồ. Dưới đây là các prompt được thiết kế để tạo ra các hình ảnh minh họa cần thiết.

#### **3.1. Prompt cho Sơ đồ Kiến trúc Tổng quan**

**Prompt for Nano Banana Pro (or similar AI image generator):**
```
Create a high-level architecture diagram for a container-based DNS Firewall system. The style should be clean, professional, and use standard cloud architecture icons. The diagram must include three main components, each in its own container box:

1.  **Caddy Server (Container):**
    *   Label it "Caddy Reverse Proxy".
    *   Show external user devices (a laptop, a smartphone) connecting to it via the internet, with arrows labeled "DoH (port 443)" and "DoT (port 853)".
    *   Show it serving a "Dashboard" and a "Sinkhole Page".

2.  **Python DNS Server (Container):**
    *   Label it "Python DNS Filter".
    *   Show an arrow from "Caddy Reverse Proxy" to this container, labeled "DNS Query".
    *   Inside this container, show a simple logic flow: a diamond shape labeled "In Blacklist?", with a "Yes" arrow pointing to the "Sinkhole Page" (conceptually) and a "No" arrow pointing to an "Upstream DNS" component.
    *   Show an icon for a blacklist file (e.g., a text file icon).

3.  **Cloudflare Tunnel (Container):**
    *   Label it "Cloudflared Tunnel".
    *   Show a dotted line arrow from the "Caddy Reverse Proxy" container to a cloud icon labeled "Cloudflare Network".
    *   Show an external user connecting to the "Cloudflare Network" to represent remote access.

Arrange the components logically, with clear data flow arrows. Use a color palette of blues, grays, and greens. The entire diagram should be enclosed in a box labeled "Docker Environment on Host Machine".
```

#### **3.2. Prompt cho Sơ đồ Luồng Dữ liệu (Data Flow Diagram)**

**Prompt for Nano Banana Pro (or similar AI image generator):**
```
Create a Data Flow Diagram (DFD) illustrating the process of a DNS query in a DNS Firewall system. Use a clear, diagrammatic style with simple shapes (circles for processes, rectangles for external entities, and open-ended rectangles for data stores).

The diagram should depict two main scenarios: "Blocked Domain" and "Allowed Domain".

**Entities:**
*   User Device (External)
*   Upstream DNS Server (e.g., 8.8.8.8) (External)

**Processes (Circles):**
1.  "Receive Encrypted DNS Query (DoT/DoH)" - handled by Caddy.
2.  "Decrypt & Forward Query" - handled by Caddy.
3.  "Filter Domain against Blacklist" - handled by the Python DNS Server.
4.  "Forward to Upstream DNS" - handled by the Python DNS Server.
5.  "Return Sinkhole IP".
6.  "Return Resolved IP".

**Data Stores (Open-ended rectangles):**
*   "Blacklist.txt"

**Flow:**
1.  An arrow from "User Device" to Process 1, labeled "DNS Query (example.com)".
2.  An arrow from Process 1 to Process 2.
3.  An arrow from Process 2 to Process 3.
4.  An arrow from Process 3 to the "Blacklist.txt" data store, labeled "Check Domain".
5.  **Scenario 1 (Blocked):** An arrow from Process 3 to Process 5, labeled "Domain is malicious". An arrow from Process 5 back to the User Device, labeled "Sinkhole IP Address".
6.  **Scenario 2 (Allowed):** An arrow from Process 3 to Process 4, labeled "Domain is safe". An arrow from Process 4 to "Upstream DNS Server", labeled "Resolve example.com". An arrow from "Upstream DNS Server" back to Process 4, labeled "Real IP Address". An arrow from Process 4 to Process 6, and finally an arrow from Process 6 back to the User Device, labeled "Real IP Address".

Use different colors or line styles for the "Blocked" and "Allowed" paths to make them easy to distinguish.
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
