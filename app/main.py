import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.cache import make_key, get_cached, set_cached, cache_size
from app.scrapers.search import scrape_search
from app.scrapers.metadata import scrape_metadata
from app.scrapers.subtitles import scrape_subtitles
from app.scrapers.channel import scrape_channel
from app.scrapers.comments import scrape_comments
from app.scrapers.download import download_and_upload_to_r2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("youtube-scraper")

settings = get_settings()

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("YouTube Scraper API starting up…")
    yield
    logger.info("YouTube Scraper API shutting down…")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="YouTube Scraper API",
    description=(
        "Self-hosted YouTube scraper API. "
        "Scrape search results, video metadata, subtitles, channel info, and comments."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _cached_scrape(endpoint: str, params: dict, scraper_fn, *args, **kwargs):
    key = make_key(endpoint, params)
    cached = get_cached(key)
    if cached is not None:
        cached["_cached"] = True
        return cached
    result = scraper_fn(*args, **kwargs)
    result["_cached"] = False
    set_cached(key, result)
    return result


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "cache_entries": cache_size(),
        "timestamp": int(time.time()),
    }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
@app.get("/api/v1/youtube/search", tags=["YouTube"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def search(
    request: Request,
    search: str = Query(..., description="Search query"),
    type: Literal["video", "channel", "playlist"] = Query("video", description="Result type"),
    limit: int = Query(20, ge=1, le=50, description="Number of results"),
    language: str = Query("en", description="Language code (e.g. en, es, fr)"),
    region: str = Query("US", description="Region code (e.g. US, GB, DE)"),
    sort_by: Literal["relevance", "rating", "view_count", "upload_date"] = Query(
        "relevance", description="Sort order"
    ),
):
    """
    Search YouTube for videos, channels, or playlists.

    Supports filters: type, limit, language, region, sort_by.
    """
    params = {
        "search": search,
        "type": type,
        "limit": limit,
        "language": language,
        "region": region,
        "sort_by": sort_by,
    }
    try:
        return _cached_scrape(
            "search", params, scrape_search,
            query=search,
            result_type=type,
            limit=limit,
            language=language,
            region=region,
            sort_by=sort_by,
        )
    except Exception as e:
        logger.exception("Search error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
@app.get("/api/v1/youtube/metadata", tags=["YouTube"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def metadata(
    request: Request,
    video_id: str = Query(..., description="YouTube video ID (e.g. dQw4w9WgXcQ)"),
):
    """
    Fetch full metadata for a YouTube video including views, likes, duration,
    description, channel info, thumbnails, and available formats.
    """
    try:
        return _cached_scrape(
            "metadata", {"video_id": video_id},
            scrape_metadata, video_id=video_id
        )
    except Exception as e:
        logger.exception("Metadata error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Subtitles
# ---------------------------------------------------------------------------
@app.get("/api/v1/youtube/subtitles", tags=["YouTube"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def subtitles(
    request: Request,
    video_id: str = Query(..., description="YouTube video ID"),
    language: str = Query("en", description="Language code (e.g. en, es, fr)"),
    subtitle_origin: Literal["auto", "manual", "any"] = Query(
        "any", description="Prefer auto-generated or manual captions"
    ),
):
    """
    Retrieve subtitle/transcript information for a video.
    Returns the subtitle track URL and available languages.
    Use subtitle_origin=auto for auto-generated, manual for uploader captions.
    """
    try:
        return _cached_scrape(
            "subtitles",
            {"video_id": video_id, "language": language, "subtitle_origin": subtitle_origin},
            scrape_subtitles,
            video_id=video_id,
            language=language,
            subtitle_origin=subtitle_origin,
        )
    except Exception as e:
        logger.exception("Subtitles error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------
@app.get("/api/v1/youtube/channel", tags=["YouTube"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def channel(
    request: Request,
    channel_id: str = Query(
        ...,
        description="Channel ID (UC…), handle (@channelname), or username",
    ),
    max_videos: int = Query(20, ge=1, le=50, description="Max recent videos to return"),
):
    """
    Fetch channel metadata and a list of recent uploads.
    Accepts channel ID (UC…), handle (@name), or username.
    """
    try:
        return _cached_scrape(
            "channel",
            {"channel_id": channel_id, "max_videos": max_videos},
            scrape_channel,
            channel_id=channel_id,
            max_videos=max_videos,
        )
    except Exception as e:
        logger.exception("Channel error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
@app.get("/api/v1/youtube/comments", tags=["YouTube"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def comments(
    request: Request,
    video_id: str = Query(..., description="YouTube video ID"),
    max_comments: int = Query(50, ge=1, le=200, description="Max comments to return"),
):
    """
    Fetch comments for a YouTube video.
    Returns top-level comments sorted by top engagement.
    Note: This endpoint is slower than others as YouTube comment scraping
    requires additional page loads.
    """
    try:
        return _cached_scrape(
            "comments",
            {"video_id": video_id, "max_comments": max_comments},
            scrape_comments,
            video_id=video_id,
            max_comments=max_comments,
        )
    except Exception as e:
        logger.exception("Comments error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Download & Push to Cloudflare R2
# ---------------------------------------------------------------------------
@app.get("/api/v1/youtube/download", tags=["YouTube"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def download(
    request: Request,
    video_id: str = Query(..., description="YouTube video ID"),
    quality: Literal["best", "1080p", "720p", "480p", "audio_only"] = Query(
        "best", description="Target video/audio quality"
    ),
):
    """
    Download a YouTube video (or audio) and push it directly to Cloudflare R2 storage.
    Returns the permanent Cloudflare public CDN URL.
    """
    try:
        return _cached_scrape(
            "download",
            {"video_id": video_id, "quality": quality},
            download_and_upload_to_r2,
            video_id=video_id,
            quality=quality,
        )
    except Exception as e:
        logger.exception("Download/Upload error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
