from youtubesearchpython import VideosSearch, ChannelsSearch, PlaylistsSearch, CustomSearch, VideoSortOrder
from app.config import get_settings

settings = get_settings()

_SORT_MAP = {
    "relevance": VideoSortOrder.relevance,
    "rating": VideoSortOrder.rating,
    "view_count": VideoSortOrder.viewCount,
    "upload_date": VideoSortOrder.uploadDate,
}


def _clean_video(item: dict) -> dict:
    return {
        "videoId": item.get("id"),
        "title": item.get("title"),
        "link": item.get("link"),
        "channel": {
            "name": item.get("channel", {}).get("name"),
            "id": item.get("channel", {}).get("id"),
            "link": item.get("channel", {}).get("link"),
        },
        "duration": item.get("duration"),
        "viewCount": item.get("viewCount", {}).get("text") if item.get("viewCount") else None,
        "publishedTime": item.get("publishedTime"),
        "thumbnails": item.get("thumbnails", []),
        "descriptionSnippet": (
            "".join(s.get("text", "") for s in item.get("descriptionSnippet", []))
            if item.get("descriptionSnippet")
            else None
        ),
    }


def _clean_channel(item: dict) -> dict:
    return {
        "channelId": item.get("id"),
        "title": item.get("title"),
        "link": item.get("link"),
        "thumbnails": item.get("thumbnails", []),
        "subscribers": item.get("subscribers", {}).get("simpleText") if item.get("subscribers") else None,
        "descriptionSnippet": (
            "".join(s.get("text", "") for s in item.get("descriptionSnippet", []))
            if item.get("descriptionSnippet")
            else None
        ),
    }


def _clean_playlist(item: dict) -> dict:
    return {
        "playlistId": item.get("id"),
        "title": item.get("title"),
        "link": item.get("link"),
        "channel": {
            "name": item.get("channel", {}).get("name"),
            "id": item.get("channel", {}).get("id"),
        },
        "videoCount": item.get("videoCount"),
        "thumbnails": item.get("thumbnails", []),
    }


def scrape_search(
    query: str,
    result_type: str = "video",
    limit: int = 20,
    language: str = "en",
    region: str = "US",
    sort_by: str = "relevance",
) -> dict:
    sort_order = _SORT_MAP.get(sort_by, VideoSortOrder.relevance)
    limit = min(limit, settings.max_results)

    if result_type == "channel":
        search = ChannelsSearch(query, limit=limit, language=language, region=region)
        results = search.result()
        items = [_clean_channel(i) for i in (results.get("result") or [])]
        return {"results": items, "search": query, "type": "channel"}

    if result_type == "playlist":
        search = PlaylistsSearch(query, limit=limit, language=language, region=region)
        results = search.result()
        items = [_clean_playlist(i) for i in (results.get("result") or [])]
        return {"results": items, "search": query, "type": "playlist"}

    # Default: video
    search = VideosSearch(query, limit=limit, language=language, region=region)
    results = search.result()
    items = [_clean_video(i) for i in (results.get("result") or [])]
    return {"results": items, "search": query, "type": "video"}
