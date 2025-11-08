#!/bin/bash
if [ "$EUID" -ne 0 ]; then
  echo "Vui long chay bang sudo"
  exit 1
fi

CONF_FILE="/etc/systemd/resolved.conf"

echo "--- Dang VO HIEU HOA DNS over TLS (DoT) ---"

# Bước 1: Kiểm tra và khôi phục tệp sao lưu
if [ -f "$CONF_FILE.bak" ]; then
    mv "$CONF_FILE.bak" $CONF_FILE
    echo "Da khoi phuc cau hinh goc tu $CONF_FILE.bak"
else
    echo "Khong tim thay file backup '$CONF_FILE.bak'."
    echo "Ban co the phai chinh sua $CONF_FILE thu cong de hoan nguyen."
    exit 1
fi

# Bước 2: Khởi động lại dịch vụ
echo "Dang khoi dong lai systemd-resolved..."
systemctl restart systemd-resolved.service

echo "--- Hoan tat. DNS over TLS (DoT) da duoc TAT. ---"