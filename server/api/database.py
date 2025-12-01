import datetime
import asyncio
from typing import Tuple
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func

from core.config import settings

# Sử dụng aiosqlite làm trình điều khiển (driver)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,  # Tăng connection pool
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Tắt SQL logging để tăng performance
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# === Async Queue cho Batch Logging ===
log_queue: asyncio.Queue = None
batch_size = 100  # Ghi 100 records một lần
batch_timeout = 2.0  # Hoặc sau 2 giây

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
    global log_queue
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Khởi tạo queue và background worker
    log_queue = asyncio.Queue(maxsize=10000)
    asyncio.create_task(batch_logger_worker())

async def get_session() -> AsyncSession:
    """Dependency của FastAPI để cung cấp một session DB."""
    async with AsyncSessionLocal() as session:
        yield session

# === Background Worker cho Batch Logging ===
async def batch_logger_worker():
    """Background task ghi logs theo batch để giảm I/O."""
    global log_queue
    batch = []
    last_flush = asyncio.get_event_loop().time()
    
    while True:
        try:
            # Đợi log entry hoặc timeout
            try:
                entry = await asyncio.wait_for(log_queue.get(), timeout=batch_timeout)
                batch.append(entry)
            except asyncio.TimeoutError:
                pass  # Timeout → flush batch hiện tại
            
            current_time = asyncio.get_event_loop().time()
            should_flush = (
                len(batch) >= batch_size or 
                (batch and current_time - last_flush >= batch_timeout)
            )
            
            if should_flush and batch:
                # Flush batch vào database
                try:
                    async with AsyncSessionLocal() as session:
                        session.add_all([
                            DNSLog(
                                client_ip=client_ip,
                                domain=domain,
                                status=status,
                                timestamp=timestamp
                            )
                            for client_ip, domain, status, timestamp in batch
                        ])
                        await session.commit()
                    batch = []
                    last_flush = current_time
                except Exception as e:
                    print(f"❌ Batch logging error: {e}")
                    batch = []  # Drop batch nếu lỗi để tránh memory leak
        
        except Exception as e:
            print(f"❌ Batch worker error: {e}")
            await asyncio.sleep(1)

# === Hàm Log (Non-blocking) ===
async def log_query_to_db(client_ip: str, domain: str, status: str):
    """
    Ghi một mục nhật ký vào queue (non-blocking).
    Background worker sẽ ghi batch vào DB.
    """
    global log_queue
    if log_queue is None:
        return  # Queue chưa khởi tạo
    
    try:
        # Put vào queue không đợi (non-blocking)
        timestamp = datetime.datetime.utcnow()
        log_queue.put_nowait((client_ip, domain, status, timestamp))
    except asyncio.QueueFull:
        # Queue đầy → drop log để không block DNS queries
        pass
    except Exception as e:
        # Không làm sập máy chủ DNS nếu việc log thất bại
        print(f"⚠️ Log queue error: {e}")