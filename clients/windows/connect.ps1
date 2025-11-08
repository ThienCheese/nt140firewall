# Yêu cầu quyền Quản trị viên
if (-Not (::GetCurrent()).IsInRole(::Administrator)) {
    Start-Process PowerShell -Verb RunAs "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

Write-Host "--- Dang cau hinh DNS Firewall (192.168.1.100) ---" -ForegroundColor Green

# Lấy tất cả các adapter mạng đang 'Up' (Thường là Wi-Fi hoặc Ethernet)
$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.Name -notlike 'Loopback*' }

foreach ($adapter in $adapters) {
    Write-Host "Dang cau hinh cho: $($adapter.Name)"
    try {
        # Đặt DNS chính thành máy chủ firewall, không đặt DNS phụ
        Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses "192.168.1.100"
        Write-Host "   -> Thanh cong!" -ForegroundColor Cyan
    } catch {
        Write-Warning "   -> Loi khi cau hinh $($adapter.Name): $_"
    }
}

Write-Host "--- Hoan tat. DNS Firewall da duoc BAT. ---" -ForegroundColor Green
Write-Host "Luu y: Khi ban roi khoi mang gia dinh, ban co the can chay 'disconnect_firewall.ps1'."
Read-Host "Nhan Enter de thoat."