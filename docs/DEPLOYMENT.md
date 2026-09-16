# DEPLOYMENT.md - Deployment Guide

## Overview

The application consists of a Next.js frontend and a FastAPI backend powered by `yt-dlp` and `FFmpeg`.

## Option 1: Docker Compose (Recommended)

Run both the frontend and downloader API together in production mode:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start services
docker compose up -d --build
```

The frontend will be available at `http://localhost:3000` and the API at `http://localhost:8000`.

## Option 2: Dockerized API + Edge Frontend (Vercel / Netlify)

Because long-running downloads and FFmpeg process execution require persistent container execution, deploy the API on a VPS using Docker, and host the Next.js frontend on Vercel/Netlify.

### 1. Backend (VPS)
```bash
docker build -t video-downloader-api .
docker run -d \
  -p 8000:8000 \
  --name downloader-api \
  --restart unless-stopped \
  -e FRONTEND_URL="https://your-frontend-domain.com" \
  video-downloader-api
```

### 2. Frontend (Vercel/Netlify)
Set environment variable:
```env
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

## Security & Resource Limits Configuration

Adjust settings in `.env`:
```env
MAX_CONCURRENT_JOBS=2
MAX_DOWNLOAD_SECONDS=1800
MAX_OUTPUT_BYTES=2147483648
JOB_TTL_SECONDS=1800
CLEANUP_INTERVAL_SECONDS=300
RATE_LIMIT_RPM=30
```
