import yt_dlp
from app.config import get_settings

settings = get_settings()


def _get_opts(**extra) -> dict:
    """Build yt-dlp options, injecting cookies if the file exists."""
    opts = {
        "quiet": settings.yt_dlp_quiet,
        "no_warnings": True,
        "skip_download": True,
        "js_runtimes": {"node": {}},
        **extra,
    }
    cookies = settings.cookies_file_path
    if cookies:
        opts["cookiefile"] = str(cookies)
    return opts


def scrape_comments(video_id: str, max_comments: int = 50) -> dict:
    url = f"https://www.youtube.com/watch?v={video_id}"
    max_comments = min(max_comments, 200)

    opts = _get_opts(
        getcomments=True,
        extractor_args={
            "youtube": {
                "max_comments": [str(max_comments)],
                "comment_sort": ["top"],
            }
        },
    )

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return {"videoId": video_id, "comments": [], "count": 0}

    raw_comments = info.get("comments") or []
    comments = [
        {
            "commentId": c.get("id"),
            "text": c.get("text"),
            "author": c.get("author"),
            "authorId": c.get("author_id"),
            "likeCount": c.get("like_count"),
            "replyCount": c.get("reply_count"),
            "isLiked": c.get("is_favorited"),
            "isPinned": c.get("is_pinned"),
            "publishedTime": c.get("timestamp"),
            "parent": c.get("parent"),  # "root" if top-level
        }
        for c in raw_comments
    ]

    return {
        "videoId": video_id,
        "commentCount": info.get("comment_count"),
        "comments": comments[:max_comments],
    }
