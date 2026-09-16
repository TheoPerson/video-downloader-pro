# RESEARCH.md - Video Downloader Research Summary

## 1. Engine & Extraction (yt-dlp)
- **Metadata Inspection**: `yt_dlp.YoutubeDL(opts).extract_info(url, download=False)` provides title, thumbnail, duration, channel, and stream formats without fetching media.
- **Format Merging**: High-definition video streams (1080p, 720p) are often separated into video-only and audio-only streams on platforms like YouTube. Format string `bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best` selects optimal streams and invokes FFmpeg for remuxing into a single MP4 container.

## 2. iOS Safari Direct Download Semantics
- **AVPlayer Hijacking**: iOS Safari hijacks responses with `Content-Type: video/mp4` into its native inline video player, ignoring `Content-Disposition: attachment`.
- **Download Enforcement**: Serving media with `Content-Type: application/octet-stream`, `X-Content-Type-Options: nosniff`, `Content-Disposition: attachment; filename="..."`, and RFC 5987 UTF-8 encoded filename guarantees Safari launches the native Download Manager prompt (*"Do you want to download 'filename'?"*) and saves the byte stream into the iOS **Files app**.
- **Resume Support**: `Accept-Ranges: bytes` allows Safari to resume interrupted mobile network downloads.

## 3. Open Source References
- **Cobalt**: Inspires URL-first minimalist interaction and frontend/API decoupling.
- **MeTube**: Inspires isolated job state transitions, input URL validation allowlists, and post-expansion filename sanitization.
