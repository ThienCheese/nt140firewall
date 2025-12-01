import base64
import datetime
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List

from core.config import settings
from core.filtering import blacklist_manager
from core.forwarder import forward_query
from core.cache import dns_cache
from core.static_dns import static_dns_manager
from api.database import get_session, DNSLog, log_query_to_db
from api.models import Stats, LogEntry, APIConfig
from dnslib import DNSRecord

router = APIRouter()
security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Kiểm tra xác thực Basic Auth cho các endpoint quản trị."""
    is_user_ok = credentials.username == "admin"
    is_pass_ok = credentials.password == settings.ADMIN_PASSWORD
    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# === Endpoint DoH (DNS over HTTPS) ===
@router.api_route("/dns-query", methods=["GET", "POST"], tags=["DoH"])
async def handle_doh(request: Request):
    """
    Xử lý các yêu cầu DoH (RFC 8484).
    Tệp này  định nghĩa thư viện dnslib được sử dụng để phân tích cú pháp.
    """
    client_ip = request.client.host
    
    if request.method == "GET":
        dns_param = request.query_params.get("dns")
        if not dns_param:
            return Response("Missing 'dns' query parameter", status_code=400)
        try:
            # Base64URL decode
            request_bytes = base64.urlsafe_b64decode(dns_param + '==')
        except Exception:
            return Response("Invalid base64", status_code=400)
    else: # POST
        if request.headers.get("content-type")!= "application/dns-message":
            return Response("Invalid content-type", status_code=415)
        request_bytes = await request.body()
    
    try:
        record = DNSRecord.parse(request_bytes)
        qname = str(record.get_q().get_qname())
    except Exception:
        return Response(f"Invalid DNS packet", status_code=400)

    # 1. Check static DNS trước (để tránh circular dependency)
    response_bytes = static_dns_manager.get_static_response(record)
    if response_bytes:
        await log_query_to_db(client_ip, qname, "static")
        return Response(
            content=response_bytes,
            media_type="application/dns-message",
            headers={"Content-Length": str(len(response_bytes))}
        )
    
    # 2. Tái sử dụng logic lọc và chuyển tiếp
    if await blacklist_manager.is_blocked(qname):
        response_bytes = blacklist_manager.get_sinkhole_response(record)
        await log_query_to_db(client_ip, qname, "blocked")
    else:
        response_bytes = await forward_query(request_bytes, client_ip)
        await log_query_to_db(client_ip, qname, "allowed")

    if response_bytes:
        return Response(
            content=response_bytes,
            media_type="application/dns-message",
            headers={"Content-Length": str(len(response_bytes))}
        )
    return Response("DNS forwarding failed", status_code=502)

# === Endpoints API cho Dashboard ===

@router.get("/api/stats", response_model=Stats, tags=["Dashboard"])
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Lấy thống kê chung từ cơ sở dữ liệu."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    
    total_q = select(func.count(DNSLog.id)).where(DNSLog.timestamp >= cutoff)
    blocked_q = select(func.count(DNSLog.id)).where(
        DNSLog.status == 'blocked', 
        DNSLog.timestamp >= cutoff
    )
    
    total = (await session.execute(total_q)).scalar()
    blocked = (await session.execute(blocked_q)).scalar()
    
    return Stats(
        total_queries=total,
        blocked_queries=blocked,
        allowed_queries=total - blocked,
        blacklisted_domains=len(blacklist_manager.blocked_domains)
    )

@router.get("/api/logs", response_model=List[LogEntry], tags=["Dashboard"])
async def get_logs(limit: int = 100, session: AsyncSession = Depends(get_session)):
    """Lấy N truy vấn DNS cuối cùng."""
    query = select(DNSLog).order_by(DNSLog.timestamp.desc()).limit(limit)
    result = await session.execute(query)
    logs = result.scalars().all()
    return logs

@router.get("/api/config", response_model=APIConfig, tags=["Admin"], dependencies=[Depends(get_current_user)])
async def get_config():
    """Lấy cấu hình máy chủ hiện tại (yêu cầu xác thực)."""
    return APIConfig(
        sinkhole_ip=settings.SINKHOLE_IP,
        router_ip=settings.ROUTER_IP,
        upstream_dns=[settings.UPSTREAM_DNS_1, settings.UPSTREAM_DNS_2]
    )

@router.get("/api/cache/stats", tags=["Admin"], dependencies=[Depends(get_current_user)])
async def get_cache_stats():
    """Lấy cache statistics (yêu cầu xác thực)."""
    return await dns_cache.get_stats()

@router.post("/api/cache/clear", tags=["Admin"], dependencies=[Depends(get_current_user)])
async def clear_cache():
    """Xóa toàn bộ DNS cache (yêu cầu xác thực)."""
    await dns_cache.clear()
    return {"message": "Cache cleared successfully"}

@router.delete("/api/cache/{domain}", tags=["Admin"], dependencies=[Depends(get_current_user)])
async def invalidate_cache(domain: str):
    """Xóa cache entries cho một domain cụ thể (yêu cầu xác thực)."""
    await dns_cache.invalidate(domain)
    return {"message": f"Cache invalidated for {domain}"}