"""Job lifecycle management for video downloads."""

import asyncio
import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import settings

logger = logging.getLogger(__name__)


class JobState(str, enum.Enum):
    """Job state machine states."""

    QUEUED = "queued"
    ANALYZING = "analyzing"
    DOWNLOADING = "downloading"
    MERGING = "merging"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CLEANED = "cleaned"


@dataclass
class Job:
    """Represents a video download job."""

    id: str
    url: str
    quality: str = "720p"
    format: str = "mp4"
    codec: str = "h264"
    enhance: bool = False
    state: JobState = JobState.QUEUED
    progress: float = 0.0
    error: Optional[str] = None
    title: Optional[str] = None
    filename: Optional[str] = None
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def update_state(self, state: JobState, error: Optional[str] = None):
        """Transition to a new state."""
        self.state = state
        self.updated_at = time.time()
        if error:
            self.error = error
        logger.info(f"Job {self.id[:8]}: {state.value}" + (f" - {error}" if error else ""))

    def to_dict(self) -> dict:
        """Serialize job for API response."""
        return {
            "id": self.id,
            "state": self.state.value,
            "progress": round(self.progress, 1),
            "error": self.error,
            "title": self.title,
            "filename": self.filename,
            "file_size": self.file_size,
            "created_at": self.created_at,
        }


class JobManager:
    """
    Manages video download jobs with bounded concurrency.

    In-memory job store with automatic cleanup.
    No database needed for V1.
    """

    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the cleanup background task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Job manager started")

    async def stop(self):
        """Stop the cleanup background task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        # Clean up all remaining files
        for job in self._jobs.values():
            self._cleanup_file(job)
        logger.info("Job manager stopped")

    def create_job(self, url: str, quality: str, format: str = "mp4", codec: str = "h264", enhance: bool = False) -> Job:
        """Create a new download job."""
        job_id = uuid.uuid4().hex[:16]
        job = Job(id=job_id, url=url, quality=quality, format=format, codec=codec, enhance=enhance)
        self._jobs[job_id] = job
        logger.info(f"Job created: {job_id[:8]} for quality={quality}")
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    @property
    def active_count(self) -> int:
        """Count currently active (non-terminal) jobs."""
        active_states = {
            JobState.QUEUED,
            JobState.ANALYZING,
            JobState.DOWNLOADING,
            JobState.MERGING,
        }
        return sum(1 for j in self._jobs.values() if j.state in active_states)

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Get the concurrency semaphore."""
        return self._semaphore

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job if it's still active."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        active_states = {
            JobState.QUEUED,
            JobState.ANALYZING,
            JobState.DOWNLOADING,
            JobState.MERGING,
        }
        if job.state in active_states:
            job.update_state(JobState.CANCELLED)
            self._cleanup_file(job)
            return True
        return False

    def _cleanup_file(self, job: Job):
        """Remove temporary file for a job."""
        if job.file_path and job.file_path.exists():
            try:
                job.file_path.unlink()
                logger.info(f"Cleaned up file for job {job.id[:8]}")
            except OSError as e:
                logger.warning(f"Failed to clean up {job.file_path}: {e}")
            job.file_path = None

    async def _cleanup_loop(self):
        """Periodically clean up expired jobs."""
        while True:
            try:
                await asyncio.sleep(settings.cleanup_interval_seconds)
                await self._run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _run_cleanup(self):
        """Remove expired jobs and their files."""
        now = time.time()
        expired = []

        for job_id, job in self._jobs.items():
            age = now - job.created_at
            if age > settings.job_ttl_seconds:
                self._cleanup_file(job)
                job.update_state(JobState.CLEANED)
                expired.append(job_id)
            elif job.state in (JobState.FAILED, JobState.CANCELLED) and age > 300:
                # Clean failed/cancelled jobs after 5 minutes
                self._cleanup_file(job)
                expired.append(job_id)

        for job_id in expired:
            del self._jobs[job_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired jobs")

        # Also clean orphaned files in download directory
        await self._clean_orphaned_files()

    async def _clean_orphaned_files(self):
        """Remove files not associated with any active job."""
        download_dir = settings.download_path
        if not download_dir.exists():
            return

        active_paths = {
            job.file_path for job in self._jobs.values() if job.file_path
        }

        now = time.time()
        for file_path in download_dir.iterdir():
            if file_path.is_file() and file_path not in active_paths:
                # Only clean files older than 10 minutes
                try:
                    file_age = now - file_path.stat().st_mtime
                    if file_age > 600:
                        file_path.unlink()
                        logger.info(f"Cleaned orphaned file: {file_path.name}")
                except OSError:
                    pass
