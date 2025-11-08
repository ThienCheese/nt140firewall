from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # Tải biến từ tệp.env (docker-compose sẽ đọc và truyền vào)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    # Cài đặt Mạng
    SINKHOLE_IP: str = "192.168.1.100"
    ROUTER_IP: str = "192.168.1.1"
    UPSTREAM_DNS_1: str = "1.1.1.1"
    UPSTREAM_DNS_2: str = "1.0.0.1"

    # Cài đặt Cổng (Nội bộ)
    DNS_PORT_UDP: int = 53
    DNS_PORT_TCP: int = 53
    DOT_PROXY_PORT: int = 8053  # Cổng nội bộ Caddy proxy DoT đến
    DOH_PORT: int = 8080      # Cổng nội bộ Caddy proxy DoH đến
    API_PORT: int = 8000      # Cổng nội bộ cho API/Dashboard

    # Cài đặt Blacklist (Tệp  và các nguồn của nó)
    BLACKLIST_PATH: str = "data/blacklist.txt"
    BLACKLIST_SOURCES: List[str] = [
        # Các nguồn được đề cập trong 
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "https://openphish.com/feed.txt",
        "https://urlhaus.abuse.ch/downloads/hostfile/"
    ]
    BLACKLIST_REFRESH_INTERVAL: int = 86400 # 24 giờ

    # Cài đặt API & DB
    DATABASE_URL: str = "sqlite+aiosqlite:///data/queries.db"
    ADMIN_PASSWORD: str = "password"

# Tạo một thực thể (instance) cài đặt duy nhất để import
settings = Settings()