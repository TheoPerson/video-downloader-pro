"""FastAPI application for the video downloader."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, field_validator
from starlette.background import BackgroundTask

from .config import settings
from .downloader import analyze_video, download_video
from .filename import sanitize_filename
from .jobs import Job, JobManager, JobState
from .url_validator import validate_url, URLValidationError

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Job manager singleton
job_manager = JobManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start/stop job manager."""
    await job_manager.start()
    logger.info(f"Video Downloader API started. Download dir: {settings.download_dir}")
    yield
    await job_manager.stop()
    logger.info("Video Downloader API stopped.")


app = FastAPI(
    title="Video Downloader API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Rate limiting (simple in-memory)
_request_times: dict[str, list[float]] = {}
_rate_lock = asyncio.Lock()


async def check_rate_limit(request: Request):
    """Simple per-IP rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0  # 1 minute window

    async with _rate_lock:
        times = _request_times.get(client_ip, [])
        # Remove old entries
        times = [t for t in times if now - t < window]
        if len(times) >= settings.rate_limit_rpm:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment.",
            )
        times.append(now)
        _request_times[client_ip] = times


# --- Request/Response Models ---


class AnalyzeRequest(BaseModel):
    """Request to analyze a video URL."""

    url: str

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("URL is required.")
        if len(v) > 2048:
            raise ValueError("URL is too long.")
        return v.strip()


class DownloadRequest(BaseModel):
    """Request to download a video."""

    url: str
    quality: str = "720p"
    format: str = "mp4" # mp4, mkv, audio
    codec: str = "h264" # h264, hevc
    enhance: bool = False

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("URL is required.")
        if len(v) > 2048:
            raise ValueError("URL is too long.")
        return v.strip()

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: str) -> str:
        allowed = {"2160p", "1440p", "1080p", "720p", "480p", "360p", "audio", "best"}
        if v not in allowed:
            raise ValueError(f"Quality must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        allowed = {"mp4", "mkv", "audio"}
        if v not in allowed:
            raise ValueError(f"Format must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("codec")
    @classmethod
    def validate_codec(cls, v: str) -> str:
        allowed = {"h264", "hevc"}
        if v not in allowed:
            raise ValueError(f"Codec must be one of: {', '.join(sorted(allowed))}")
        return v


# --- API Routes ---


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "active_jobs": job_manager.active_count,
    }


@app.post("/api/analyze")
async def analyze(request: Request, body: AnalyzeRequest):
    """Analyze a video URL and return metadata."""
    await check_rate_limit(request)

    # Validate and normalize URL
    try:
        normalized_url = validate_url(body.url)
    except URLValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Extract metadata
    try:
        metadata = await analyze_video(normalized_url)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not analyze this video.",
        )

    return metadata


@app.post("/api/download")
async def start_download(request: Request, body: DownloadRequest):
    """Start a video download job."""
    await check_rate_limit(request)

    # Validate and normalize URL
    try:
        normalized_url = validate_url(body.url)
    except URLValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Check concurrent job limit
    if job_manager.active_count >= settings.max_concurrent_jobs:
        raise HTTPException(
            status_code=429,
            detail="Too many active downloads. Please wait.",
        )

    # Create job
    fmt = "m4a" if body.quality == "audio" else body.format
    job = job_manager.create_job(normalized_url, body.quality, fmt, body.codec, body.enhance)

    # Start download in background
    asyncio.create_task(_run_download(job))

    return {"job_id": job.id, "state": job.state.value}


async def _run_download(job: Job):
    """Execute a download job with concurrency control."""
    async with job_manager.semaphore:
        try:
            await download_video(job)
        except Exception as e:
            if job.state != JobState.FAILED:
                job.update_state(JobState.FAILED, str(e))
            logger.error(f"Job {job.id[:8]} failed: {e}")


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a download job."""
    # Sanitize job_id
    if not job_id or len(job_id) > 32 or not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID.")

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return job.to_dict()


@app.get("/api/jobs/{job_id}/file")
async def download_file(job_id: str):
    """Download the completed file for a job."""
    # Sanitize job_id
    if not job_id or len(job_id) > 32 or not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID.")

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.state != JobState.READY:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not ready. Current state: {job.state.value}",
        )

    if not job.file_path or not job.file_path.exists():
        raise HTTPException(status_code=410, detail="File is no longer available.")

    # Verify file is within allowed directory
    download_dir = settings.download_path.resolve()
    file_path = job.file_path.resolve()
    if not str(file_path).startswith(str(download_dir)):
        logger.error(f"Path traversal attempt: {file_path}")
        raise HTTPException(status_code=403, detail="Access denied.")

    filename = job.filename or f"video{file_path.suffix}"

    # Use application/octet-stream to prevent iOS Safari from hijacking
    # the response into its inline media player. Safari ignores
    # Content-Disposition: attachment for video/mp4 and plays inline instead.
    # With octet-stream + nosniff, Safari reliably triggers a file download.
    from urllib.parse import quote

    # RFC 5987 encoded filename for unicode support
    filename_encoded = quote(filename)

    return FileResponse(
        path=str(file_path),
        media_type="application/octet-stream",
        filename=filename,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{filename_encoded}"
            ),
            "Cache-Control": "private, no-transform",
            "X-Content-Type-Options": "nosniff",
            "Accept-Ranges": "bytes",
        },
    )


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a download job."""
    if not job_id or len(job_id) > 32 or not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID.")

    if job_manager.cancel_job(job_id):
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Job not found or already completed.")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler to prevent stack trace leakage."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )
