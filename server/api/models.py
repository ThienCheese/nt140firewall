from pydantic import BaseModel
from datetime import datetime
from typing import List

# Dùng cho /api/logs
class LogEntry(BaseModel):
    timestamp: datetime
    client_ip: str
    domain: str
    status: str

    class Config:
        orm_mode = True # Cho phép Pydantic đọc từ đối tượng SQLAlchemy

# Dùng cho /api/stats
class Stats(BaseModel):
    total_queries: int
    blocked_queries: int
    allowed_queries: int
    blacklisted_domains: int

# Dùng cho /api/config
class APIConfig(BaseModel):
    sinkhole_ip: str
    router_ip: str
    upstream_dns: List[str]