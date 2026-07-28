import os
import tempfile
import time
import logging
import yt_dlp
import boto3
from botocore.config import Config
from app.config import get_settings

logger = logging.getLogger("youtube-scraper")
settings = get_settings()


def _get_opts(**extra) -> dict:
    opts = {
        "quiet": settings.yt_dlp_quiet,
        "no_warnings": True,
        "format": "all",
    }
    cookies = settings.cookies_file_path
    if cookies:
        opts["cookiefile"] = str(cookies)
    opts.update(extra)
    return opts


def _get_s3_client():
    if not settings.r2_account_id or not settings.r2_access_key_id or not settings.r2_secret_access_key:
        raise ValueError(
            "Cloudflare R2 credentials missing. Please set R2_ACCOUNT_ID, "
            "R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY in environment variables."
        )

    endpoint_url = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        service_name="s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def download_and_upload_to_r2(
    video_id: str,
    quality: str = "best",
) -> dict:
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Determine format specifier for yt-dlp
    if quality == "audio_only":
        format_spec = "bestaudio/best"
        ext = "mp3"
    elif quality == "1080p":
        format_spec = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        ext = "mp4"
    elif quality == "720p":
        format_spec = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        ext = "mp4"
    elif quality == "480p":
        format_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        ext = "mp4"
    else:  # "best"
        format_spec = "bestvideo+bestaudio/best"
        ext = "mp4"

    temp_dir = tempfile.mkdtemp(prefix="yt_download_")
    output_template = os.path.join(temp_dir, f"{video_id}.%(ext)s")

    opts = _get_opts(
        format=format_spec,
        outtmpl=output_template,
        merge_output_format="mp4" if quality != "audio_only" else None,
        postprocessors=[
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ] if quality == "audio_only" else [],
    )

    downloaded_file = None
    title = None
    duration = None

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title")
            duration = info.get("duration")

        # Locate downloaded file in temp_dir
        files = os.listdir(temp_dir)
        if not files:
            raise FileNotFoundError("Video download failed, output file not found.")

        downloaded_file = os.path.join(temp_dir, files[0])
        filesize = os.path.getsize(downloaded_file)
        actual_ext = os.path.splitext(downloaded_file)[1].lstrip(".")

        # Upload to Cloudflare R2
        s3 = _get_s3_client()
        bucket = settings.r2_bucket_name or "youtube-videos"
        object_key = f"videos/{video_id}.{actual_ext}"

        content_type = "audio/mpeg" if actual_ext == "mp3" else "video/mp4"

        logger.info(f"Uploading {downloaded_file} to R2 bucket '{bucket}' as '{object_key}'...")
        s3.upload_file(
            downloaded_file,
            bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

        # Build public URL
        if settings.r2_public_domain:
            public_domain = settings.r2_public_domain.rstrip("/")
            public_url = f"{public_domain}/{object_key}"
        else:
            public_url = f"https://{bucket}.{settings.r2_account_id}.r2.cloudflarestorage.com/{object_key}"

        return {
            "videoId": video_id,
            "title": title,
            "duration": duration,
            "quality": quality,
            "format": actual_ext,
            "filesizeBytes": filesize,
            "cloudflareUrl": public_url,
            "bucket": bucket,
            "objectKey": object_key,
            "uploadedAt": int(time.time()),
        }

    finally:
        # Clean up temporary download directory
        if temp_dir and os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, f))
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass
