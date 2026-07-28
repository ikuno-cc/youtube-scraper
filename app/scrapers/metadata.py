import yt_dlp
from app.config import get_settings

settings = get_settings()


def _get_opts(**extra) -> dict:
    """Build yt-dlp options, injecting cookies if the file exists."""
    opts = {
        "quiet": settings.yt_dlp_quiet,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "format": "all",
        **extra,
    }
    cookies = settings.cookies_file_path
    if cookies:
        opts["cookiefile"] = str(cookies)
    return opts


def scrape_metadata(video_id: str) -> dict:
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = _get_opts()

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return {}

    # Build clean thumbnails list
    thumbnails = [
        {"url": t.get("url"), "width": t.get("width"), "height": t.get("height")}
        for t in (info.get("thumbnails") or [])
        if t.get("url")
    ]

    # Build formats summary
    formats = []
    for f in (info.get("formats") or []):
        if isinstance(f, dict):
            formats.append({
                "formatId": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution"),
                "fps": f.get("fps"),
                "filesize": f.get("filesize"),
                "tbr": f.get("tbr"),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec"),
            })

    return {
        "videoId": info.get("id"),
        "title": info.get("title"),
        "description": info.get("description"),
        "uploadDate": info.get("upload_date"),
        "duration": info.get("duration"),
        "durationString": info.get("duration_string"),
        "viewCount": info.get("view_count"),
        "likeCount": info.get("like_count"),
        "commentCount": info.get("comment_count"),
        "channel": {
            "name": info.get("channel"),
            "id": info.get("channel_id"),
            "url": info.get("channel_url"),
            "followerCount": info.get("channel_follower_count"),
        },
        "tags": info.get("tags") or [],
        "categories": info.get("categories") or [],
        "ageLimit": info.get("age_limit"),
        "availability": info.get("availability"),
        "isLive": info.get("is_live"),
        "wasLive": info.get("was_live"),
        "thumbnails": thumbnails,
        "webpage_url": info.get("webpage_url"),
        "formats": formats,
    }
