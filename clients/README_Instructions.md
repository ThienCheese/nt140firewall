# Hướng dẫn Kết nối Client

Sử dụng các tệp trong thư mục này (có thể tải về từ Dashboard) để kết nối hoặc ngắt kết nối khỏi nt140-firewall.

## 1. Thiết bị Di động (Cài đặt một lần)

Phương pháp này được khuyến nghị cho điện thoại và máy tính xách tay. Nó sẽ bảo vệ thiết bị của bạn mọi lúc, mọi nơi (cả ở nhà và bên ngoài).

*   **iOS & macOS:** Tải tệp `apple_ios_macos/nt140_firewall_DoH.mobileconfig`. Mở tệp và làm theo hướng dẫn trên màn hình để "Cài đặt" (Install) hồ sơ.
    *   *Ngắt kết nối:* Vào Cài đặt > Cài đặt chung > VPN & Quản lý thiết bị > Xóa hồ sơ "nt140-firewall".
*   **Android (9+):** Vào Cài đặt > Mạng & Internet > DNS cá nhân (Private DNS). Chọn "Tên máy chủ của nhà cung cấp DNS cá nhân" và nhập `nt140firewall.duckdns.org`.
    *   *Ngắt kết nối:* Chọn "Tắt" hoặc "Tự động" trong cài đặt DNS cá nhân.
*   **Windows (Di động/DoH):** Tải về và chạy `connect_firewall_DoH.ps1` (Nhấp chuột phải -> Run with PowerShell).
    *   *Ngắt kết nối:* Chạy `disconnect_firewall_DoH.ps1`.
*   **Linux (Di động/DoT):** Chạy `sudo./connect_firewall_DoT.sh`.
    *   *Ngắt kết nối:* Chạy `sudo./disconnect_firewall_DoT.sh` (khôi phục tệp cấu hình cũ).

## 2. Thiết bị Cố định (Chỉ dùng trong nhà)

Phương pháp này dành cho máy tính để bàn hoặc các thiết bị không bao giờ rời khỏi mạng LAN.

*   **Windows (Chỉ LAN):** Nhấp chuột phải vào `connect_firewall_LAN.ps1` và chọn "Run with PowerShell".
    *   *Ngắt kết nối:* Nhấp chuột phải vào `disconnect_firewall_LAN.ps1`.
*   **Linux (Chỉ LAN):** Chạy `sudo./connect_firewall_LAN.sh`.
    *   *Ngắt kết nối:* Chạy `sudo./disconnect_firewall_LAN.sh`.