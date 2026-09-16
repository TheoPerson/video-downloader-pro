"""Filename sanitization utilities."""

import re
import unicodedata


# Maximum filename length (conservative for cross-platform)
MAX_FILENAME_LENGTH = 200

# Characters unsafe for filenames across platforms
UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Multiple spaces/underscores/dashes
MULTI_SEPARATOR = re.compile(r"[-_\s]{2,}")


def sanitize_filename(name: str, extension: str = ".mp4") -> str:
    """
    Sanitize a string for use as a filename.

    - Strips control characters
    - Removes path traversal attempts
    - Removes unsafe characters
    - Normalizes unicode
    - Enforces length limit
    - Forces expected extension
    """
    if not name:
        name = "video"

    # Normalize unicode
    name = unicodedata.normalize("NFKC", name)

    # Remove any path components (prevent traversal)
    name = name.replace("/", " ").replace("\\", " ").replace("..", " ")

    # Remove unsafe characters
    name = UNSAFE_CHARS.sub(" ", name)

    # Collapse multiple separators
    name = MULTI_SEPARATOR.sub(" ", name)

    # Strip leading/trailing whitespace and dots
    name = name.strip(" .")

    # Remove any existing extension to force our own
    if "." in name:
        parts = name.rsplit(".", 1)
        known_extensions = {"mp4", "webm", "mkv", "avi", "mov", "m4a", "mp3", "wav"}
        if parts[-1].lower() in known_extensions:
            name = parts[0]

    # Enforce length limit (leaving room for extension)
    extension = extension if extension.startswith(".") else f".{extension}"
    max_name_length = MAX_FILENAME_LENGTH - len(extension)
    if len(name) > max_name_length:
        name = name[:max_name_length].rstrip(" .")

    # Final fallback
    if not name:
        name = "video"

    return f"{name}{extension}"


def make_safe_path_component(s: str) -> str:
    """Make a string safe for use as a single path component."""
    s = UNSAFE_CHARS.sub("_", s)
    s = s.replace("..", "_")
    s = s.strip("._")
    return s or "unknown"
