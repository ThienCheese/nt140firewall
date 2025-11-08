# Yêu cầu quyền Quản trị viên
if (-Not (::GetCurrent()).IsInRole(::Administrator)) {
    Start-Process PowerShell -Verb RunAs "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

Write-Host "--- Dang reset DNS ve DHCP (Tu dong) ---" -ForegroundColor Yellow

$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.Name -notlike 'Loopback*' }

foreach ($adapter in $adapters) {
    Write-Host "Dang reset: $($adapter.Name)"
    try {
        # Đặt lại DNS về mặc định (DHCP)
        Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ResetServerAddresses
        Write-Host "   -> Thanh cong!" -ForegroundColor Cyan
    } catch {
        Write-Warning "   -> Loi khi reset $($adapter.Name): $_"
    }
}

Write-Host "--- Hoan tat. DNS Firewall da duoc TAT. ---" -ForegroundColor Yellow
Read-Host "Nhan Enter de thoat."