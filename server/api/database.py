import datetime
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func

from core.config import settings

# Sử dụng aiosqlite làm trình điều khiển (driver)
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# === Mô hình Bảng (Table Model) ===
class DNSLog(Base):
    """Mô hình cho nhật ký truy vấn DNS."""
    __tablename__ = "dns_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    client_ip = Column(String)
    domain = Column(String, index=True)
    status = Column(String) # 'allowed' hoặc 'blocked'

async def init_db():
    """Tạo các bảng trong DB."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    """Dependency của FastAPI để cung cấp một session DB."""
    async with AsyncSessionLocal() as session:
        yield session

# === Hàm Log ===
async def log_query_to_db(client_ip: str, domain: str, status: str):
    """
    Ghi một mục nhật ký vào DB một cách bất đồng bộ.
    Được gọi từ các trình xử lý DNS (UDP/TCP/DoH).
    """
    try:
        async with AsyncSessionLocal() as session:
            log_entry = DNSLog(client_ip=client_ip, domain=domain, status=status)
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        # Không làm sập máy chủ DNS nếu việc log thất bại
        print(f"Lỗi khi log vào DB: {e}")