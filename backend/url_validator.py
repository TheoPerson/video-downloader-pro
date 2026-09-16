"""URL validation and normalization for supported video hosts."""

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from .config import settings


class URLValidationError(Exception):
    """Raised when a URL fails validation."""

    def __init__(self, message: str = "This URL is not supported."):
        self.message = message
        super().__init__(self.message)


def validate_url(url: str) -> str:
    """
    Validate and normalize a video URL.

    Only allows explicitly supported hosts.
    Returns the normalized URL.
    Raises URLValidationError if invalid.
    """
    url = url.strip()

    if not url:
        raise URLValidationError("Please enter a URL.")

    # Basic URL format check
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise URLValidationError("URL must start with http:// or https://.")

    try:
        parsed = urlparse(url)
    except Exception:
        raise URLValidationError("This URL is not valid.")

    if not parsed.hostname:
        raise URLValidationError("This URL is not valid.")

    # Strip www. prefix for host comparison
    hostname = parsed.hostname.lower()

    # Check against allowed hosts
    if hostname not in settings.allowed_hosts:
        raise URLValidationError(
            "This URL is not supported. Only YouTube URLs are accepted."
        )

    # Normalize the URL
    return _normalize_youtube_url(parsed)


def _normalize_youtube_url(parsed) -> str:
    """Normalize YouTube URL to a canonical form."""
    hostname = parsed.hostname.lower()

    # Handle youtu.be short links
    if hostname in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.lstrip("/").split("/")[0]
        if not video_id or not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
            raise URLValidationError("Invalid YouTube video ID.")
        return f"https://www.youtube.com/watch?v={video_id}"

    # Handle youtube.com URLs
    path = parsed.path.lower()

    # YouTube Shorts
    shorts_match = re.match(r"^/shorts/([a-zA-Z0-9_-]{11})", parsed.path)
    if shorts_match:
        video_id = shorts_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # Standard watch URL
    if path.startswith("/watch"):
        params = parse_qs(parsed.query)
        video_id = params.get("v", [None])[0]
        if not video_id or not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
            raise URLValidationError("Invalid YouTube video ID.")
        return f"https://www.youtube.com/watch?v={video_id}"

    # Embed URL
    embed_match = re.match(r"^/embed/([a-zA-Z0-9_-]{11})", parsed.path)
    if embed_match:
        video_id = embed_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # Live URL
    live_match = re.match(r"^/live/([a-zA-Z0-9_-]{11})", parsed.path)
    if live_match:
        video_id = live_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    raise URLValidationError(
        "Could not find a valid video in this URL."
    )


def extract_video_id(url: str) -> str:
    """Extract the video ID from a normalized YouTube URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    video_id = params.get("v", [None])[0]
    if not video_id:
        raise URLValidationError("Could not extract video ID.")
    return video_id
