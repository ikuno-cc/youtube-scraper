from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # Cache
    cache_ttl_seconds: int = 300
    cache_max_size: int = 500

    # Rate limiting (requests per minute per IP)
    rate_limit_per_minute: int = 30

    # Scraping
    max_results: int = 20
    yt_dlp_quiet: bool = True

    # Cookies file path for yt-dlp authentication.
    # Mount this file as a volume in Docker/Coolify to avoid rebuilding on rotation.
    cookies_file: str = "/app/cookies/cookies.txt"

    # Server
    port: int = 8000
    docs_enabled: bool = True
    cors_origins: str = "*"

    @property
    def cookies_file_path(self) -> Path | None:
        """Return the cookies Path if the file exists, else None."""
        p = Path(self.cookies_file)
        return p if p.exists() and p.stat().st_size > 0 else None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
