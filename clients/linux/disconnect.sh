#!/bin/bash
if [ "$EUID" -ne 0 ]; then
  echo "Vui long chay bang sudo"
  exit 1
fi

echo "--- Dang reset DNS ve DHCP (Tu dong) ---"

INTERFACES=$(ip link | awk -F: '$2 ~ / en| wl/ && $3 ~ /<.*,UP,.*>/ {print $2}' | cut -d'@' -f1 | tr -d ' ')

if [ -z "$INTERFACES" ]; then
    echo "Khong tim thay interface mang nao dang hoat dong."
    exit 1
fi

for IFACE in $INTERFACES; do
    echo "Reset interface: $IFACE"
    # Hoàn nguyên DNS về cài đặt tự động (DHCP)
    systemd-resolve --interface=$IFACE --revert-dns
done

systemctl restart systemd-resolved
echo "--- Hoan tat. DNS Firewall da duoc TAT. ---"