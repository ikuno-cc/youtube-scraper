from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Cache
    cache_ttl_seconds: int = 300
    cache_max_size: int = 500

    # Rate limiting (requests per minute per IP)
    rate_limit_per_minute: int = 30

    # Scraping
    max_results: int = 20
    yt_dlp_quiet: bool = True

    # Server
    port: int = 8000
    docs_enabled: bool = True
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
