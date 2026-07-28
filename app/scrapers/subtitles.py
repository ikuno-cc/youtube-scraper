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


def scrape_subtitles(
    video_id: str,
    language: str = "en",
    subtitle_origin: str = "any",  # "auto", "manual", "any"
) -> dict:
    url = f"https://www.youtube.com/watch?v={video_id}"

    opts = _get_opts(
        writesubtitles=False,
        writeautomaticsub=False,
    )

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return {"videoId": video_id, "language": language, "subtitles": [], "source": None}

    manual_subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    def _pick_sub(subs: dict) -> list | None:
        """Find best matching subtitle track for the given language."""
        if language in subs:
            return subs[language]
        # Try base language (e.g. "en" from "en-US")
        base = language.split("-")[0]
        for key in subs:
            if key.startswith(base):
                return subs[key]
        return None

    chosen = None
    source = None

    if subtitle_origin == "manual":
        chosen = _pick_sub(manual_subs)
        source = "manual" if chosen else None
    elif subtitle_origin == "auto":
        chosen = _pick_sub(auto_subs)
        source = "auto" if chosen else None
    else:  # "any" — prefer manual, fall back to auto
        chosen = _pick_sub(manual_subs)
        source = "manual" if chosen else None
        if not chosen:
            chosen = _pick_sub(auto_subs)
            source = "auto" if chosen else None

    if not chosen:
        return {
            "videoId": video_id,
            "language": language,
            "subtitles": [],
            "source": None,
            "availableLanguages": {
                "manual": list(manual_subs.keys()),
                "auto": list(auto_subs.keys()),
            },
        }

    # Prefer json3 format for rich timestamped data, fallback to srv1/ttml/vtt
    FORMAT_PRIORITY = ["json3", "srv3", "srv2", "srv1", "ttml", "vtt"]
    best_fmt = next(
        (f for pref in FORMAT_PRIORITY for f in chosen if f.get("ext") == pref),
        chosen[0] if chosen else None,
    )

    return {
        "videoId": video_id,
        "language": language,
        "source": source,
        "format": best_fmt.get("ext") if best_fmt else None,
        "url": best_fmt.get("url") if best_fmt else None,
        "availableLanguages": {
            "manual": list(manual_subs.keys()),
            "auto": list(auto_subs.keys()),
        },
        # All available formats for this language
        "formats": [
            {"ext": f.get("ext"), "url": f.get("url")} for f in chosen
        ],
    }
