"""Video Downloader API - Configuration."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    debug: bool = False

    # Download limits
    max_concurrent_jobs: int = 2
    max_download_seconds: int = 1800
    max_output_bytes: int = 2_147_483_648  # 2 GB
    job_ttl_seconds: int = 1800
    cleanup_interval_seconds: int = 300

    # Temporary storage
    download_dir: str = "/tmp/video-downloader"

    # Rate limiting
    rate_limit_rpm: int = 30

    # Allowed hosts (YouTube only for V1)
    allowed_hosts: list[str] = [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtu.be",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    ]

    @property
    def download_path(self) -> Path:
        """Get the download directory as a Path, creating it if needed."""
        path = Path(self.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
