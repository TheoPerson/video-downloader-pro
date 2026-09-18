"""Video download service using yt-dlp."""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

import yt_dlp

from .config import settings
from .filename import sanitize_filename
from .jobs import Job, JobState

logger = logging.getLogger(__name__)


# Standard quality tiers we present to users
QUALITY_MAP = {
    "2160p": 2160,
    "1440p": 1440,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
    "audio": 0,
}


def _get_base_opts() -> dict:
    """Base yt-dlp options shared across operations."""
    return {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "geo_bypass": False,
        "nocheckcertificate": False,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
    }


async def analyze_video(url: str) -> dict:
    """
    Extract metadata and available formats for a video URL.

    Returns structured metadata suitable for the frontend.
    Does not download the video.
    """
    opts = _get_base_opts()
    opts.update(
        {
            "skip_download": True,
            "extract_flat": False,
        }
    )

    def _extract():
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    import concurrent.futures
    loop = asyncio.get_running_loop()
    try:
        # Use ProcessPoolExecutor for true isolation and hard-kill capability
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
            info = await asyncio.wait_for(
                loop.run_in_executor(pool, _extract),
                timeout=60,
            )
    except asyncio.TimeoutError:
        raise RuntimeError("Video analysis timed out. Please try again.")
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private video" in error_msg:
            raise RuntimeError("This video is private and cannot be accessed.")
        if "Video unavailable" in error_msg:
            raise RuntimeError("This video is unavailable.")
        if "Sign in" in error_msg:
            raise RuntimeError("This video requires authentication.")
        raise RuntimeError("Could not analyze this video. It may be unavailable.")
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise RuntimeError("Could not analyze this video.")

    if not info:
        raise RuntimeError("No video information found.")

    # Determine available qualities from format list
    available_qualities = _extract_qualities(info.get("formats", []))

    # Build clean response
    duration = info.get("duration")
    return {
        "id": info.get("id", ""),
        "title": info.get("title", "Unknown"),
        "thumbnail": info.get("thumbnail", ""),
        "channel": info.get("uploader") or info.get("channel", ""),
        "duration": duration if isinstance(duration, (int, float)) else None,
        "formats": available_qualities,
    }


def _extract_qualities(formats: list) -> list[dict]:
    """
    Determine available quality tiers from yt-dlp format list.

    Groups formats into standard tiers and reports what's actually available.
    """
    available_heights = set()
    has_audio_only = False

    for fmt in formats:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec", "none")
        acodec = fmt.get("acodec", "none")

        # Check for audio-only streams
        if (vcodec == "none" or not vcodec) and acodec and acodec != "none":
            has_audio_only = True

        # Track video heights
        if height and vcodec and vcodec != "none":
            available_heights.add(height)

    # Map to standard tiers
    result = []
    for label, target_height in QUALITY_MAP.items():
        if label == "audio":
            if has_audio_only:
                result.append(
                    {
                        "quality": "audio",
                        "label": "Audio Only (M4A)",
                        "container": "m4a",
                    }
                )
            continue

        # Find the closest available height at or below the target
        matching = [h for h in available_heights if h <= target_height]
        if matching or target_height in available_heights:
            # Check if this tier actually has a stream at roughly this height
            close_heights = [h for h in available_heights if abs(h - target_height) <= 40]
            if close_heights:
                result.append(
                    {
                        "quality": label,
                        "label": f"{label} MP4",
                        "container": "mp4",
                    }
                )

    # Always ensure at least one option
    if not result:
        result.append(
            {
                "quality": "best",
                "label": "Best Available",
                "container": "mp4",
            }
        )

    return result


async def download_video(job: Job) -> Path:
    """
    Download a video at the requested quality.

    Handles format selection, downloading, and merging.
    Returns the path to the completed file.
    """
    quality = job.quality
    target_format = job.format

    # Determine yt-dlp format string
    if quality == "audio":
        format_str = "bestaudio[ext=m4a]/bestaudio/best"
        ext = "m4a"
    else:
        height = QUALITY_MAP.get(quality, 720)
        # Prefer mp4 video + m4a audio for iOS compatibility
        format_str = (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/"
            f"best"
        )
        ext = "mp4"

    if quality == "best":
        format_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        ext = "mp4"

    # Setup output path
    download_dir = settings.download_path
    output_template = str(download_dir / f"{job.id}.%(ext)s")

    # Progress hook
    def _progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total and total > 0:
                job.progress = min(95.0, (downloaded / total) * 90.0)

                # Check size limit
                if total > settings.max_output_bytes:
                    raise RuntimeError("File exceeds maximum allowed size.")
            job.updated_at = __import__("time").time()
        elif d["status"] == "finished":
            job.progress = 90.0

    opts = _get_base_opts()
    
    # Check for local ffmpeg in project directory
    ffmpeg_dir = Path(__file__).parent.parent
    
    opts.update(
        {
            "format": format_str,
            "outtmpl": output_template,
            "merge_output_format": ext,
            "progress_hooks": [_progress_hook],
            "postprocessors": [],
            "max_filesize": settings.max_output_bytes,
            "socket_timeout": 30,
            "ffmpeg_location": str(ffmpeg_dir) if (ffmpeg_dir / "ffmpeg.exe").exists() else None,
            "prefer_ffmpeg": True,
        }
    )

    # If MP4, add remux postprocessor for consistency
    if ext == "mp4":
        opts["postprocessors"].append(
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4",
            }
        )

    job.update_state(JobState.DOWNLOADING)

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job.url, download=True)
            return info

    loop = asyncio.get_event_loop()
    try:
        info = await asyncio.wait_for(
            loop.run_in_executor(None, _download),
            timeout=settings.max_download_seconds,
        )
    except asyncio.TimeoutError:
        job.update_state(JobState.FAILED, "Download timed out.")
        raise RuntimeError("Download timed out.")
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"Download error for job {job.id[:8]}: {error_msg}")
        job.update_state(JobState.FAILED, "The video could not be downloaded right now.")
        raise RuntimeError("The video could not be downloaded right now.")
    except Exception as e:
        logger.error(f"Download error for job {job.id[:8]}: {e}")
        job.update_state(JobState.FAILED, "Download failed unexpectedly.")
        raise RuntimeError("Download failed unexpectedly.")

    # Find the output file
    job.update_state(JobState.MERGING)
    job.progress = 95.0

    output_file = _find_output_file(download_dir, job.id, ext)
    if not output_file:
        job.update_state(JobState.FAILED, "Output file not found after download.")
        raise RuntimeError("Download completed but output file was not found.")

    # Validate file
    file_size = output_file.stat().st_size
    if file_size == 0:
        output_file.unlink()
        job.update_state(JobState.FAILED, "Downloaded file is empty.")
        raise RuntimeError("Downloaded file is empty.")

    if file_size > settings.max_output_bytes:
        output_file.unlink()
        job.update_state(JobState.FAILED, "File exceeds the allowed size.")
        raise RuntimeError("The file exceeded the allowed size.")

    # Generate clean filename
    title = info.get("title", "video") if info else "video"
    job.title = title
    safe_name = sanitize_filename(title, f".{ext}")
    job.filename = safe_name

    # Rename to final filename
    final_path = download_dir / f"{job.id}_{safe_name}"
    output_file.rename(final_path)

    job.file_path = final_path
    job.file_size = file_size
    job.progress = 100.0
    job.update_state(JobState.READY)

    logger.info(
        f"Job {job.id[:8]} ready: {safe_name} ({file_size / 1048576:.1f} MB)"
    )

    return final_path


def _find_output_file(download_dir: Path, job_id: str, expected_ext: str) -> Optional[Path]:
    """Find the output file created by yt-dlp."""
    # yt-dlp may create files with various extensions during processing
    for file_path in download_dir.iterdir():
        if file_path.name.startswith(job_id) and file_path.is_file():
            return file_path
    return None
