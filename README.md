<p align="center">
  <img src="assets/banner.svg" alt="Video Downloader Pro" width="100%">
</p>

<h1 align="center">Video Downloader Pro</h1>

<p align="center">
  <strong>A premium, self-hosted media utility optimized for iOS Safari.</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#installation">Installation</a> •
  <a href="#tech-stack">Tech Stack</a>
</p>

---

## 📱 The Mobile-First Download Experience

Most web-based video downloaders suffer on iOS: Safari intercepts `video/mp4` files and forces them into an inline player, making actual file saving a nightmare.

**Video Downloader Pro** solves this fundamentally. By proxying the media through a custom FastAPI backend, streams are re-encoded and served with `application/octet-stream` and `X-Content-Type-Options: nosniff`. 

The result? **A native "Do you want to download..." prompt on iOS Safari**, saving the video directly to your Files app, even over 5G.

## ✨ Features

- **Silky UX**: Rebuilt from the ground up with Framer Motion, glassmorphism, and Lucide icons.
- **Format Merging**: Extracts 1080p/4K video streams and seamlessly remuxes them with high-quality audio using local FFmpeg.
- **Job Engine**: Asynchronous, non-blocking Python backend with a strict in-memory state machine and automatic TTL cleanup.
- **Security Hardened**: URL domain allowlists, absolute path traversal defenses, and rate limiting out of the box.

## 🏗 Architecture

- **Frontend**: Next.js 16 (App Router), React, Tailwind CSS, Framer Motion.
- **Backend**: Python 3.12, FastAPI, yt-dlp, FFmpeg.
- **Data Flow**: `URL Paste` → `FastAPI Analysis` → `React Preview` → `yt-dlp Engine` → `FFmpeg Remux` → `Native OS Download`.

## 🚀 Installation & Deployment

### Local Development (Windows / macOS / Linux)

1. **Clone & Setup Backend**
```bash
uv venv
uv pip install -e ".[dev]"
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8001
```

2. **Setup Frontend**
```bash
cd frontend
npm install
npm run dev
```

3. **Visit** `http://localhost:3000`

### Docker (Production)

```bash
docker compose up -d --build
```

---
*Built for authorized personal use. Please respect content copyrights.*
