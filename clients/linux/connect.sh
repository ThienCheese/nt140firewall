#!/bin/bash
if; then
  echo "Vui long chay bang sudo"
  exit
fi

SERVER_IP="192.168.1.100"
echo "--- Dang cau hinh DNS Firewall ($SERVER_IP) ---"

# Phát hiện các interface đang hoạt động
INTERFACES=$(ip link | awk -F: '$2 ~ / en| wl/ && $3 ~ /<.*,UP,.*>/ {print $2}' | cut -d'@' -f1 | tr -d ' ')

if; then
    echo "Khong tim thay interface mang nao dang hoat dong."
    exit 1
fi

for IFACE in $INTERFACES; do
    echo "Cau hinh cho interface: $IFACE"
    # Sử dụng systemd-resolve để đặt DNS cho mỗi interface
    systemd-resolve --interface=$IFACE --set-dns=$SERVER_IP
    # Đảm bảo DNSSEC bị tắt để máy chủ của chúng ta hoạt động
    systemd-resolve --interface=$IFACE --set-dnssec=no
done

systemctl restart systemd-resolved
echo "--- Hoan tat. DNS Firewall da duoc BAT. ---"