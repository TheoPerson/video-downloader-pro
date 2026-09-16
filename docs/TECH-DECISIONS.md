# TECH-DECISIONS.md - Technical Decisions Log

## Decision 1: `application/octet-stream` MIME Type for iOS Safari
- **Context**: iOS Safari intercepts `video/mp4` files and opens them in an inline QuickTime video player regardless of `Content-Disposition: attachment`.
- **Decision**: Override output headers for download responses to `Content-Type: application/octet-stream` accompanied by `X-Content-Type-Options: nosniff` and RFC 5987 filename parameters.
- **Outcome**: Safari triggers the native Download Manager dialog and saves the MP4 file directly into the iOS Files app.

## Decision 2: In-Memory Job Manager with TTL Cleanup
- **Context**: V1 is a lightweight personal utility that does not require persistent database overhead.
- **Decision**: Manage active downloads using an in-memory job store backed by `asyncio.Semaphore` for concurrency control and a background cleanup task that purges files older than 30 minutes.
- **Outcome**: Simple, fast, zero-database architecture with no risk of temporary storage exhaustion.

## Decision 3: URL Host Allowlist & Command Safety
- **Context**: Publicly accessible downloader endpoints are vulnerable to SSRF and command injection.
- **Decision**: Restrict accepted hostnames exclusively to YouTube domains and execute all yt-dlp/FFmpeg invocations safely via Python API structures without invoking shell commands.
- **Outcome**: Strong protection against SSRF, command injection, and proxy abuse.
