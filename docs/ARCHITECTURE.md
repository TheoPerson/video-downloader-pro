# ARCHITECTURE.md - Personal Video Downloader Architecture

```text
               +---------------------------------+
               |       iPhone Safari / Client    |
               +----------------+----------------+
                                |
                   HTTPS / JSON | HTTP File Attachment
                                v
               +----------------+----------------+
               |     Next.js Web Frontend        |
               |     (App Router / Tailwind)     |
               +----------------+----------------+
                                |
                    REST API    | CORS / Port 8000
                                v
               +----------------+----------------+
               |       FastAPI Download API      |
               |  - URL Normalizer & Validator   |
               |  - Rate Limiter & Concurrency   |
               |  - In-Memory Job State Machine  |
               +----------------+----------------+
                                |
             yt-dlp Python API  | FFmpeg remux
                                v
               +----------------+----------------+
               |    Isolated Subprocess Pipeline  |
               |    (/tmp/video-downloader)      |
               +----------------+----------------+
```

## System Components

1. **Frontend (Next.js 16 + React + Tailwind CSS)**
   - Mobile-first, single-screen responsive interface tailored for iOS Safari.
   - Handles paste detection, metadata preview, quality selection, and live polling.
   - Triggers native file downloads via location assignment (`window.location.href`).

2. **Backend API (FastAPI + Pydantic)**
   - Strict URL validation enforcing domain allowlist (`youtube.com`, `youtu.be`).
   - Rate limiting per IP to prevent service abuse.
   - Asynchronous job execution with in-memory state tracking (`QUEUED`, `ANALYZING`, `DOWNLOADING`, `MERGING`, `READY`).
   - Background worker task for automatic cleanup of temporary files after TTL expiration.

3. **Media Pipeline (yt-dlp + FFmpeg)**
   - Direct Python API integration with custom progress hooks.
   - Non-blocking executor threads for long-running extraction and remuxing.
   - Filename sanitization protecting against path traversal and control characters.
