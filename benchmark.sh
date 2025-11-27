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
