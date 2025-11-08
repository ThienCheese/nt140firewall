# Yêu cầu quyền Quản trị viên
if (-Not (::GetCurrent()).IsInRole(::Administrator)) {
    Start-Process PowerShell -Verb RunAs "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$DnsDomain = "nt140firewall.duckdns.org"
$DohTemplate = "https://nt140firewall.duckdns.org/dns-query"

Write-Host "--- Dang kich hoat DNS over HTTPS (DoH) cho $DnsDomain ---" -ForegroundColor Green

# Bước 1: Phân giải IP công cộng hiện tại của máy chủ
try {
    $serverIp = (Resolve-DnsName -Name $DnsDomain).IPAddress
    Write-Host "Da phan giai IP may chu: $serverIp"
} catch {
    Write-Warning "LOI: Khong the phan giai $DnsDomain. Kiem tra xem DDNS co hoat dong khong."
    Read-Host "Nhan Enter de thoat."
    exit
}

# Bước 2: Thêm máy chủ vào danh sách "Known Servers" (Máy chủ đã biết) của Windows [7, 5]
# Tham số -AllowFallbackToUdp $False rất quan trọng để đảm bảo an toàn [8]
Write-Host "Dang them may chu vao danh sach DoH..."
Add-DnsClientDohServerAddress -ServerAddress $serverIp -DohTemplate $DohTemplate -AllowFallbackToUdp $False -AutoUpgrade $True [8, 9, 10]

# Bước 3: Áp dụng cài đặt DNS cho tất cả các adapter đang hoạt động
$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.Name -notlike 'Loopback*' }
foreach ($adapter in $adapters) {
    Write-Host "Dang cau hinh cho: $($adapter.Name)"
    try {
        # Đặt IP máy chủ làm DNS duy nhất [11]
        Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses $serverIp
        Write-Host "   -> Thanh cong!" -ForegroundColor Cyan
    } catch {
        Write-Warning "   -> Loi khi cau hinh $($adapter.Name): $_"
    }
}

# Bước 4: Xóa bộ đệm DNS
ipconfig /flushdns

Write-Host "--- Hoan tat. DNS over HTTPS (DoH) da duoc BAT. ---" -ForegroundColor Green
Read-Host "Nhan Enter de thoat."