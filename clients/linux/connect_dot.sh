#!/bin/bash
if [ "$EUID" -ne 0 ]; then
  echo "Vui long chay bang sudo"
  exit 1
fi

CONF_FILE="/etc/systemd/resolved.conf"
DNS_DOMAIN="nt140firewall.duckdns.org"

echo "--- Dang kich hoat DNS over TLS (DoT) cho $DNS_DOMAIN ---"

# Bước 1: Sao lưu tệp cấu hình hiện tại
if [ -f "$CONF_FILE.bak" ]; then
    echo "Da tim thay file backup. Bo qua buoc sao luu."
else
    cp $CONF_FILE "$CONF_FILE.bak"
    echo "Da sao luu cau hinh hien tai vao $CONF_FILE.bak"
fi

# Bước 2: Chỉnh sửa tệp cấu hình bằng sed
# Bỏ ghi chú (uncomment) và đặt DNS thành tên miền của bạn
sed -i -E "s/^[#]*DNS=.*/DNS=$DNS_DOMAIN/" $CONF_FILE
# Bỏ ghi chú và đặt DNSOverTLS=yes
sed -i -E "s/^[#]*DNSOverTLS=.*/DNSOverTLS=yes/" $CONF_FILE
# Bỏ ghi chú và đặt Domains=~. (sử dụng làm mặc định)
sed -i -E "s/^[#]*Domains=.*/Domains=~./" $CONF_FILE

# Bước 3: Khởi động lại dịch vụ
echo "Dang khoi dong lai systemd-resolved..."
systemctl restart systemd-resolved.service

echo "--- Hoan tat. DNS over TLS (DoT) da duoc BAT. ---"
echo "Chay 'resolvectl status' de kiem tra."