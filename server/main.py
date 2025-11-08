import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.dns_server import start_dns_listeners
from core.blacklist_updater import start_blacklist_updater
from core.filtering import blacklist_manager
from core.config import settings
from api.routes import router as api_router
from api.database import init_db

# asynccontextmanager 'lifespan' quản lý các tác vụ nền
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Logic khởi động
    print("Bắt đầu khởi chạy dịch vụ...")
    # 1. Khởi tạo cơ sở dữ liệu
    await init_db()
    
    # 2. Tải danh sách đen lần đầu
    await blacklist_manager.reload_blacklist()
    
    # 3. Khởi chạy các tác vụ nền
    loop = asyncio.get_running_loop()
    dns_task = loop.create_task(start_dns_listeners(blacklist_manager))
    updater_task = loop.create_task(start_blacklist_updater(blacklist_manager))
    
    print(f"--- Máy chủ DNS đang lắng nghe trên cổng {settings.DNS_PORT_UDP} (UDP/TCP) ---")
    print(f"--- Trình lắng nghe DoT proxy đang lắng nghe trên cổng {settings.DOT_PROXY_PORT} ---")
    print(f"--- Trình cập nhật Blacklist đã khởi động ---")
    
    yield # Ứng dụng FastAPI chạy trong khi các tác vụ này chạy nền
    
    # Logic tắt máy
    print("Bắt đầu quá trình tắt máy...")
    dns_task.cancel()
    updater_task.cancel()
    await asyncio.gather(dns_task, updater_task, return_exceptions=True)
    print("Tắt máy hoàn tất.")

# Khởi tạo ứng dụng FastAPI chính
app = FastAPI(title="nt140-dns-firewall API", lifespan=lifespan)
app.include_router(api_router)

# Máy chủ DoH (chạy trên cổng 8080)
# Chúng ta tạo một ứng dụng FastAPI thứ hai (nhưng riêng biệt)
# để xử lý lưu lượng DoH, vì nó sử dụng một cổng khác
# và một logic định tuyến đơn giản hơn (chỉ /dns-query)
doh_app = FastAPI(title="DoH Handler")
doh_app.include_router(api_router, prefix="/api") # Đảm bảo nó có thể xử lý /api/doh-query

async def run_servers():
    """
    Chạy cả hai máy chủ Uvicorn (API/Dashboard và DoH) đồng thời.
    """
    config_main = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=settings.API_PORT, # 8000
        log_level="info"
    )
    server_main = uvicorn.Server(config_main)

    config_doh = uvicorn.Config(
        app, # Tái sử dụng cùng một ứng dụng FastAPI chính
        host="0.0.0.0", 
        port=settings.DOH_PORT, # 8080
        log_level="info"
    )
    server_doh = uvicorn.Server(config_doh)

    print(f"--- API/Dashboard đang khởi chạy trên cổng {settings.API_PORT} ---")
    print(f"--- Trình xử lý DoH đang khởi chạy trên cổng {settings.DOH_PORT} ---")

    await asyncio.gather(
        server_main.serve(),
        server_doh.serve()
    )

if __name__ == "__main__":
    # Lưu ý: 'main.py' không khởi chạy trực tiếp các trình lắng nghe DNS.
    # Trình lắng nghe DNS được khởi chạy bởi 'lifespan' của FastAPI.
    # Điều này đảm bảo mọi thứ chạy trong cùng một vòng lặp asyncio.
    try:
        asyncio.run(run_servers())
    except KeyboardInterrupt:
        print("Phát hiện KeyboardInterrupt, đang tắt...")