"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  analyzeVideo,
  startDownload,
  getJobStatus,
  getDownloadUrl,
  formatDuration,
  formatBytes,
  type VideoMetadata,
  type JobStatus,
  ApiError,
} from "@/lib/api";
import { isValidVideoUrl, looksLikeUrl } from "@/lib/url-utils";

type AppState =
  | "idle"
  | "analyzing"
  | "preview"
  | "downloading"
  | "ready"
  | "error";

export default function VideoDownloader() {
  const [url, setUrl] = useState("");
  const [appState, setAppState] = useState<AppState>("idle");
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [selectedQuality, setSelectedQuality] = useState<string>("");
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string>("");
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const resetState = useCallback(() => {
    setAppState("idle");
    setMetadata(null);
    setSelectedQuality("");
    setJobStatus(null);
    setError("");
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!url.trim()) return;

    setError("");
    setAppState("analyzing");

    try {
      const data = await analyzeVideo(url.trim());
      setMetadata(data);
      // Auto-select best quality
      if (data.formats.length > 0) {
        setSelectedQuality(data.formats[0].quality);
      }
      setAppState("preview");
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not analyze this video. Please check the URL and try again.";
      setError(message);
      setAppState("error");
    }
  }, [url]);

  const handleDownload = useCallback(async () => {
    if (!metadata || !selectedQuality) return;

    setError("");
    setAppState("downloading");

    const selectedFormat = metadata.formats.find(
      (f) => f.quality === selectedQuality,
    );
    const format = selectedFormat?.container || "mp4";

    try {
      const { job_id } = await startDownload(url.trim(), selectedQuality, format);

      // Start polling for job status
      const poll = setInterval(async () => {
        try {
          const status = await getJobStatus(job_id);
          setJobStatus(status);

          if (status.state === "ready") {
            clearInterval(poll);
            pollRef.current = null;
            setAppState("ready");

            // Trigger download via direct navigation (best for iOS Safari)
            window.location.href = getDownloadUrl(job_id);
          } else if (status.state === "failed") {
            clearInterval(poll);
            pollRef.current = null;
            setError(status.error || "Download failed.");
            setAppState("error");
          } else if (status.state === "cancelled" || status.state === "cleaned") {
            clearInterval(poll);
            pollRef.current = null;
            setError("Download was cancelled.");
            setAppState("error");
          }
        } catch {
          // Continue polling on transient errors
        }
      }, 1500);

      pollRef.current = poll;
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not start the download.";
      setError(message);
      setAppState("error");
    }
  }, [metadata, selectedQuality, url]);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && looksLikeUrl(text)) {
        setUrl(text);
        // Auto-analyze if valid
        if (isValidVideoUrl(text)) {
          resetState();
          setUrl(text);
          // Trigger analysis after state update
          setTimeout(async () => {
            setAppState("analyzing");
            try {
              const data = await analyzeVideo(text.trim());
              setMetadata(data);
              if (data.formats.length > 0) {
                setSelectedQuality(data.formats[0].quality);
              }
              setAppState("preview");
            } catch (err) {
              const message =
                err instanceof ApiError
                  ? err.message
                  : "Could not analyze this video.";
              setError(message);
              setAppState("error");
            }
          }, 100);
        }
      }
    } catch {
      // Clipboard API not available or denied
      inputRef.current?.focus();
    }
  }, [resetState]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && appState === "idle") {
      handleAnalyze();
    }
  };

  const getButtonLabel = (): string => {
    switch (appState) {
      case "analyzing":
        return "Analyzing…";
      case "downloading":
        if (jobStatus) {
          if (jobStatus.state === "downloading") {
            return jobStatus.progress > 0
              ? `Downloading… ${Math.round(jobStatus.progress)}%`
              : "Downloading…";
          }
          if (jobStatus.state === "merging") return "Preparing MP4…";
        }
        return "Starting download…";
      case "ready":
        return "Download complete ✓";
      default:
        return "";
    }
  };

  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-100 flex flex-col">
      {/* Header */}
      <header className="pt-safe-top px-4 pt-12 pb-4 text-center">
        <h1 className="text-xl font-semibold tracking-tight text-zinc-100">
          Video Downloader
        </h1>
        <p className="text-sm text-zinc-500 mt-1">Private utility</p>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col items-center px-4 pb-safe-bottom">
        <div className="w-full max-w-lg space-y-6 mt-4">
          {/* URL Input */}
          <div className="space-y-3">
            <div className="relative">
              <input
                ref={inputRef}
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (appState === "error") resetState();
                }}
                onKeyDown={handleKeyDown}
                placeholder="Paste video URL"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck="false"
                enterKeyHint="go"
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-4 
                           text-base text-zinc-100 placeholder:text-zinc-600
                           focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50
                           transition-colors"
                aria-label="Video URL"
                disabled={appState === "analyzing" || appState === "downloading"}
              />
              {url && appState === "idle" && (
                <button
                  onClick={() => {
                    setUrl("");
                    resetState();
                    inputRef.current?.focus();
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 
                             hover:text-zinc-300 p-1 rounded-lg transition-colors"
                  aria-label="Clear URL"
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={handlePaste}
                className="flex-1 bg-zinc-900 border border-zinc-800 text-zinc-300 
                           rounded-xl py-3 text-sm font-medium
                           hover:bg-zinc-800 active:bg-zinc-700 
                           transition-colors touch-manipulation"
                disabled={appState === "analyzing" || appState === "downloading"}
              >
                📋 Paste
              </button>
              <button
                onClick={handleAnalyze}
                disabled={
                  !url.trim() ||
                  appState === "analyzing" ||
                  appState === "downloading"
                }
                className="flex-[2] bg-blue-600 text-white rounded-xl py-3 text-sm font-semibold
                           hover:bg-blue-500 active:bg-blue-700 
                           disabled:opacity-40 disabled:cursor-not-allowed
                           transition-colors touch-manipulation"
              >
                {appState === "analyzing" ? (
                  <span className="flex items-center justify-center gap-2">
                    <Spinner /> Analyzing…
                  </span>
                ) : (
                  "Get Video"
                )}
              </button>
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div
              className="bg-red-950/50 border border-red-900/50 rounded-xl px-4 py-3 text-sm text-red-300"
              role="alert"
              aria-live="polite"
            >
              {error}
              <button
                onClick={() => {
                  setError("");
                  if (appState === "error") setAppState(metadata ? "preview" : "idle");
                }}
                className="block mt-2 text-red-400 hover:text-red-300 text-xs underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Video Preview */}
          {metadata && (appState === "preview" || appState === "downloading" || appState === "ready") && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
              {/* Thumbnail */}
              {metadata.thumbnail && (
                <div className="relative aspect-video bg-zinc-800">
                  <img
                    src={metadata.thumbnail}
                    alt={metadata.title}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  {metadata.duration && (
                    <span className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-1.5 py-0.5 rounded font-mono">
                      {formatDuration(metadata.duration)}
                    </span>
                  )}
                </div>
              )}

              {/* Info */}
              <div className="p-4 space-y-3">
                <div>
                  <h2 className="text-sm font-medium text-zinc-100 leading-snug line-clamp-2">
                    {metadata.title}
                  </h2>
                  {metadata.channel && (
                    <p className="text-xs text-zinc-500 mt-1">
                      {metadata.channel}
                      {metadata.duration
                        ? ` · ${formatDuration(metadata.duration)}`
                        : ""}
                    </p>
                  )}
                </div>

                {/* Quality selector */}
                {appState === "preview" && (
                  <>
                    <div>
                      <label
                        htmlFor="quality-select"
                        className="block text-xs text-zinc-500 mb-1.5"
                      >
                        Quality
                      </label>
                      <select
                        id="quality-select"
                        value={selectedQuality}
                        onChange={(e) => setSelectedQuality(e.target.value)}
                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 
                                   text-sm text-zinc-100 
                                   focus:outline-none focus:ring-2 focus:ring-blue-500/50
                                   appearance-none cursor-pointer"
                      >
                        {metadata.formats.map((f) => (
                          <option key={f.quality} value={f.quality}>
                            {f.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      onClick={handleDownload}
                      className="w-full bg-emerald-600 text-white rounded-xl py-3.5 text-sm font-semibold
                                 hover:bg-emerald-500 active:bg-emerald-700
                                 transition-colors touch-manipulation"
                    >
                      Download{" "}
                      {metadata.formats.find((f) => f.quality === selectedQuality)
                        ?.container.toUpperCase() || "MP4"}
                    </button>
                  </>
                )}

                {/* Download progress */}
                {(appState === "downloading" || appState === "ready") && (
                  <div className="space-y-2">
                    {/* Progress bar */}
                    <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ease-out ${
                          appState === "ready"
                            ? "bg-emerald-500"
                            : "bg-blue-500"
                        }`}
                        style={{
                          width: `${jobStatus?.progress ?? 0}%`,
                        }}
                        role="progressbar"
                        aria-valuenow={jobStatus?.progress ?? 0}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label="Download progress"
                      />
                    </div>

                    {/* Status text */}
                    <p
                      className="text-xs text-zinc-400 text-center"
                      aria-live="polite"
                    >
                      {getButtonLabel()}
                    </p>

                    {/* File info when ready */}
                    {appState === "ready" && jobStatus?.file_size && (
                      <p className="text-xs text-zinc-500 text-center">
                        {formatBytes(jobStatus.file_size)}
                      </p>
                    )}

                    {/* Manual download link when ready */}
                    {appState === "ready" && jobStatus && (
                      <a
                        href={getDownloadUrl(jobStatus.id)}
                        download={jobStatus.filename || "video.mp4"}
                        className="block w-full text-center bg-emerald-600 text-white 
                                   rounded-xl py-3 text-sm font-semibold
                                   hover:bg-emerald-500 active:bg-emerald-700
                                   transition-colors touch-manipulation mt-2"
                      >
                        Save File ↓
                      </a>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* New download button */}
          {(appState === "ready" || appState === "error") && (
            <button
              onClick={() => {
                setUrl("");
                resetState();
                inputRef.current?.focus();
              }}
              className="w-full bg-zinc-900 border border-zinc-800 text-zinc-400 
                         rounded-xl py-3 text-sm font-medium
                         hover:bg-zinc-800 active:bg-zinc-700
                         transition-colors touch-manipulation"
            >
              New Download
            </button>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="px-4 py-4 text-center pb-safe-bottom">
        <p className="text-xs text-zinc-700">
          For personal use · Content you own or are authorized to download
        </p>
      </footer>
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
