# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="YouTube Scraper API"
LABEL org.opencontainers.image.description="Self-hosted YouTube scraper REST API"
LABEL org.opencontainers.image.source="https://github.com/your-repo/youtube-scraper-api"

# ffmpeg, curl, unzip, and deno (required for yt-dlp JS runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://deno.land/install.sh | sh \
    && cp /root/.deno/bin/deno /usr/local/bin/deno

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser \
    && mkdir -p /app/cookies \
    && chown -R appuser:appgroup /app

COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

# Health check — Coolify uses this automatically
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
