# Yêu cầu quyền Quản trị viên
if (-Not (::GetCurrent()).IsInRole(::Administrator)) {
    Start-Process PowerShell -Verb RunAs "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$DnsDomain = "nt140firewall.duckdns.org"
Write-Host "--- Dang VO HIEU HOA DNS over HTTPS (DoH) ---" -ForegroundColor Yellow

# Bước 1: Đặt lại tất cả các adapter về DHCP
$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.Name -notlike 'Loopback*' }
foreach ($adapter in $adapters) {
    Write-Host "Dang reset adapter: $($adapter.Name)"
    try {
        # Đặt lại DNS về mặc định (DHCP)
        Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ResetServerAddresses
        Write-Host "   -> Thanh cong!" -ForegroundColor Cyan
    } catch {
        Write-Warning "   -> Loi khi reset $($adapter.Name): $_"
    }
}

# Bước 2: Xóa máy chủ khỏi danh sách "Known Servers" của Windows
Write-Host "Dang xoa may chu $DnsDomain khoi danh sach DoH..."
try {
    # Tìm tất cả các máy chủ sử dụng mẫu (template) của chúng ta
    $servers = Get-DnsClientDohServerAddress | Where-Object { $_.DohTemplate -like "*$DnsDomain*" }
    
    if ($servers) {
        foreach ($server in $servers) {
            Write-Host "   Dang xoa IP: $($server.ServerAddress)"
            Remove-DnsClientDohServerAddress -ServerAddress $server.ServerAddress
        }
    } else {
        Write-Host "   Khong tim thay may chu DoH nao da cau hinh."
    }
} catch {
    Write-Warning "   -> Loi khi xoa may chu DoH: $_"
}

# Bước 3: Xóa bộ đệm DNS
ipconfig /flushdns

Write-Host "--- Hoan tat. DNS Firewall (DoH) da duoc TAT. ---" -ForegroundColor Yellow
Read-Host "Nhan Enter de thoat."