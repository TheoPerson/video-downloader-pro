# Multi-stage build for the video downloader API
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Copy application code
COPY backend/ ./backend/
COPY tests/ ./tests/

# Create download directory with correct permissions
RUN mkdir -p /tmp/video-downloader && chown appuser:appuser /tmp/video-downloader

# Switch to non-root user
USER appuser

# Environment defaults
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV DOWNLOAD_DIR=/tmp/video-downloader
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Start the API server
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
