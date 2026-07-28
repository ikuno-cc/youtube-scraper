import yt_dlp
from app.config import get_settings

settings = get_settings()


def _get_opts(**extra) -> dict:
    """Build yt-dlp options, injecting cookies if the file exists."""
    opts = {
        "quiet": settings.yt_dlp_quiet,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "js_runtimes": {"node": {}},
        **extra,
    }
    cookies = settings.cookies_file_path
    if cookies:
        opts["cookiefile"] = str(cookies)
    return opts


def scrape_search(
    query: str,
    result_type: str = "video",
    limit: int = 20,
    language: str = "en",
    region: str = "US",
    sort_by: str = "relevance",
) -> dict:
    limit = min(limit, settings.max_results)

    # Map search prefix based on result type
    prefix = "ytsearch"
    if result_type == "channel":
        prefix = "ytsearch"  # flat search returns channels/videos
    elif result_type == "playlist":
        prefix = "ytsearch"

    search_query = f"{prefix}{limit}:{query}"
    opts = _get_opts(playlistend=limit)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(search_query, download=False)

    if not info:
        return {"results": [], "search": query, "type": result_type}

    entries = info.get("entries") or []

    results = []
    for e in entries:
        if not e or not e.get("id"):
            continue
        results.append({
            "videoId": e.get("id"),
            "title": e.get("title"),
            "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}",
            "channel": {
                "name": e.get("uploader") or e.get("channel"),
                "id": e.get("uploader_id") or e.get("channel_id"),
                "url": e.get("uploader_url") or e.get("channel_url"),
            },
            "duration": e.get("duration"),
            "viewCount": e.get("view_count"),
            "descriptionSnippet": e.get("description"),
            "thumbnails": e.get("thumbnails") or [],
        })

    return {"results": results, "search": query, "type": result_type}
