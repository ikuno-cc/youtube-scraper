import yt_dlp
from app.config import get_settings

settings = get_settings()


def _get_opts(**extra) -> dict:
    """Build yt-dlp options, injecting cookies if the file exists."""
    opts = {
        "quiet": settings.yt_dlp_quiet,
        "no_warnings": True,
        "skip_download": True,
        "format": "all",
        **extra,
    }
    cookies = settings.cookies_file_path
    if cookies:
        opts["cookiefile"] = str(cookies)
    return opts


def _channel_url(channel_id: str) -> str:
    if channel_id.startswith("@"):
        return f"https://www.youtube.com/{channel_id}"
    if channel_id.startswith("UC"):
        return f"https://www.youtube.com/channel/{channel_id}"
    return f"https://www.youtube.com/@{channel_id}"


def scrape_channel(channel_id: str, max_videos: int = 20) -> dict:
    url = _channel_url(channel_id)
    max_videos = min(max_videos, settings.max_results)

    opts = _get_opts(
        extract_flat=True,
        playlistend=max_videos,
    )

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return {"channelId": channel_id, "videos": []}

    entries = info.get("entries") or []

    # entries may be nested (tabs) — flatten one level
    if entries and isinstance(entries[0], dict) and entries[0].get("_type") == "playlist":
        entries = entries[0].get("entries") or []

    videos = [
        {
            "videoId": e.get("id"),
            "title": e.get("title"),
            "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}",
            "duration": e.get("duration"),
            "viewCount": e.get("view_count"),
            "uploadDate": e.get("upload_date"),
            "thumbnails": e.get("thumbnails") or [],
        }
        for e in entries
        if e and e.get("id")
    ][:max_videos]

    return {
        "channelId": info.get("id") or channel_id,
        "title": info.get("channel") or info.get("title"),
        "description": info.get("description"),
        "url": info.get("webpage_url") or url,
        "thumbnails": info.get("thumbnails") or [],
        "followerCount": info.get("channel_follower_count"),
        "videoCount": info.get("playlist_count"),
        "videos": videos,
    }
