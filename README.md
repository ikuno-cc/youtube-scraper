# YouTube Scraper API 🎬

A self-hosted REST API that scrapes YouTube for search results, video metadata, subtitles/transcripts, channel info, and comments — no third-party scraping service required.

Built with **FastAPI** + **yt-dlp** + **youtube-search-python**, ready for one-click **Coolify** deployment.

---

## Features

- 🔍 **Search** — videos, channels, playlists with filters (sort, language, region)
- 📄 **Metadata** — full video info (views, likes, duration, formats, thumbnails)
- 📝 **Subtitles** — timestamped captions (manual or auto-generated)
- 📺 **Channel** — channel info + recent uploads
- 💬 **Comments** — top comments for any video
- ⚡ **Caching** — in-memory TTL cache to avoid redundant scrapes
- 🛡️ **Rate Limiting** — per-IP request limiting via slowapi
- 🐳 **Docker-ready** — multi-stage Dockerfile + docker-compose
- 🚀 **Coolify-ready** — health check endpoint + env-var driven config

---

## Quick Start (Local)

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd youtube-scraper-api

# 2. Copy and edit env vars (all have sensible defaults)
cp .env.example .env

# 3. Build and run with Docker Compose
docker compose up --build
```

The API will be available at **http://localhost:8000**
Swagger docs at **http://localhost:8000/docs**

---

## API Endpoints

### `GET /health`
Health check. Returns server status and cache stats.

```json
{"status": "ok", "cache_entries": 12, "timestamp": 1234567890}
```

---

### `GET /api/v1/youtube/search`
Search YouTube.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search` | string | **required** | Search query |
| `type` | `video\|channel\|playlist` | `video` | Result type |
| `limit` | int (1–50) | `20` | Number of results |
| `language` | string | `en` | Language code |
| `region` | string | `US` | Region code |
| `sort_by` | `relevance\|rating\|view_count\|upload_date` | `relevance` | Sort order |

```bash
curl "http://localhost:8000/api/v1/youtube/search?search=python+tutorial&type=video&limit=10"
```

---

### `GET /api/v1/youtube/metadata`
Get full metadata for a video.

| Parameter | Type | Description |
|-----------|------|-------------|
| `video_id` | string | YouTube video ID (e.g. `dQw4w9WgXcQ`) |

```bash
curl "http://localhost:8000/api/v1/youtube/metadata?video_id=dQw4w9WgXcQ"
```

**Response includes:** title, description, views, likes, duration, upload date, channel info, tags, categories, thumbnails, available formats.

---

### `GET /api/v1/youtube/subtitles`
Get subtitle/transcript info for a video.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_id` | string | **required** | YouTube video ID |
| `language` | string | `en` | Language code |
| `subtitle_origin` | `auto\|manual\|any` | `any` | Caption source preference |

```bash
curl "http://localhost:8000/api/v1/youtube/subtitles?video_id=dQw4w9WgXcQ&language=en&subtitle_origin=any"
```

**Response includes:** subtitle URL, format, source type, all available languages.

---

### `GET /api/v1/youtube/channel`
Get channel info and recent videos.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `channel_id` | string | **required** | Channel ID (`UC…`), handle (`@name`), or username |
| `max_videos` | int (1–50) | `20` | Max recent videos to return |

```bash
curl "http://localhost:8000/api/v1/youtube/channel?channel_id=@mkbhd&max_videos=10"
```

---

### `GET /api/v1/youtube/comments`
Get top comments for a video.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_id` | string | **required** | YouTube video ID |
| `max_comments` | int (1–200) | `50` | Max comments to return |

```bash
curl "http://localhost:8000/api/v1/youtube/comments?video_id=dQw4w9WgXcQ&max_comments=25"
```

> ⚠️ **Note:** Comments scraping is significantly slower than other endpoints as it requires additional page loads by yt-dlp.

---

## Configuration

All settings are driven by environment variables. Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL_SECONDS` | `300` | Cache expiry in seconds |
| `CACHE_MAX_SIZE` | `500` | Max cached entries |
| `RATE_LIMIT_PER_MINUTE` | `30` | Max requests/min per IP |
| `MAX_RESULTS` | `20` | Max results cap |
| `YT_DLP_QUIET` | `true` | Suppress yt-dlp logs |
| `PORT` | `8000` | Listening port |
| `DOCS_ENABLED` | `true` | Enable /docs and /redoc |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

---

## Coolify Deployment

### Method 1: Docker Compose (Recommended)

1. In Coolify: **New Resource → Docker Compose**
2. Paste the contents of `docker-compose.yml`
3. Set environment variables in the Coolify dashboard (see table above)
4. Deploy — Coolify detects the `/health` endpoint automatically

### Method 2: Dockerfile (single service)

1. In Coolify: **New Resource → Application → GitHub/GitLab repo**
2. Set build pack to **Dockerfile**
3. Set port to `8000`
4. Add environment variables
5. Enable health check path: `/health`

### Method 3: Build image locally and push

```bash
docker build -t your-registry/youtube-scraper-api:latest .
docker push your-registry/youtube-scraper-api:latest
```
Then deploy via **Docker Image** in Coolify.

---

## Project Structure

```
youtube-scraper-api/
├── app/
│   ├── main.py              # FastAPI app + all routes
│   ├── config.py            # Settings (env vars via pydantic-settings)
│   ├── cache.py             # In-memory TTL cache
│   └── scrapers/
│       ├── search.py        # youtube-search-python wrapper
│       ├── metadata.py      # yt-dlp video metadata extractor
│       ├── subtitles.py     # yt-dlp subtitles/transcripts
│       ├── channel.py       # yt-dlp channel info
│       └── comments.py      # yt-dlp comments
├── Dockerfile               # Multi-stage, slim production image
├── docker-compose.yml       # Compose file for local + Coolify
├── .env.example             # Environment variable template
├── .dockerignore
├── requirements.txt
└── README.md
```

---

## Notes

- YouTube may occasionally block or throttle scraping. The in-memory cache helps reduce request frequency.
- `yt-dlp` is updated frequently — if scraping breaks, update it: `pip install -U yt-dlp`
- The comments endpoint can be slow (5–30 seconds) for popular videos with many comments.
- For higher availability, consider adding a Redis cache and running multiple API instances behind a load balancer.

---

## License

MIT
