# Sử dụng một image Python mỏng (slim) làm image cơ sở
FROM python:3.11-slim

# Đặt thư mục làm việc bên trong container là /app
WORKDIR /app

# Sao chép tệp requirements.txt vào thư mục làm việc
# Điều này được thực hiện riêng biệt để tận dụng bộ đệm (cache) của Docker
COPY requirements.txt .

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn của ứng dụng (từ thư mục 'server') vào thư mục /app
COPY .. .

# Thông báo cho Docker biết container sẽ lắng nghe trên các cổng này
EXPOSE 53/udp
EXPOSE 53/tcp
EXPOSE 8000
EXPOSE 8053
EXPOSE 8080

# Lệnh để chạy ứng dụng khi container khởi động
CMD ["python", "main.py"]