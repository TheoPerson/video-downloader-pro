"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Link2,
  ClipboardPaste,
  Download,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  RotateCcw,
  Sparkles,
} from "lucide-react";
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

  const handleAnalyze = useCallback(
    async (inputUrl?: string) => {
      const target = inputUrl ?? url;
      if (!target.trim()) return;
      setError("");
      setAppState("analyzing");
      try {
        const data = await analyzeVideo(target.trim());
        setMetadata(data);
        if (data.formats.length > 0) setSelectedQuality(data.formats[0].quality);
        setAppState("preview");
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not analyze this video. Check the URL and try again."
        );
        setAppState("error");
      }
    },
    [url]
  );

  const handleDownload = useCallback(async () => {
    if (!metadata || !selectedQuality) return;
    setError("");
    setAppState("downloading");
    const fmt = metadata.formats.find((f) => f.quality === selectedQuality);
    try {
      const { job_id } = await startDownload(
        url.trim(),
        selectedQuality,
        fmt?.container || "mp4"
      );
      const poll = setInterval(async () => {
        try {
          const status = await getJobStatus(job_id);
          setJobStatus(status);
          if (status.state === "ready") {
            clearInterval(poll);
            pollRef.current = null;
            setAppState("ready");
            window.location.href = getDownloadUrl(job_id);
          } else if (status.state === "failed") {
            clearInterval(poll);
            pollRef.current = null;
            setError(status.error || "Download failed.");
            setAppState("error");
          } else if (
            status.state === "cancelled" ||
            status.state === "cleaned"
          ) {
            clearInterval(poll);
            pollRef.current = null;
            setError("Download was cancelled.");
            setAppState("error");
          }
        } catch {
          /* transient */
        }
      }, 1500);
      pollRef.current = poll;
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not start download."
      );
      setAppState("error");
    }
  }, [metadata, selectedQuality, url]);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && looksLikeUrl(text)) {
        setUrl(text);
        if (isValidVideoUrl(text)) {
          resetState();
          setUrl(text);
          setTimeout(() => handleAnalyze(text), 80);
        }
      }
    } catch {
      inputRef.current?.focus();
    }
  }, [resetState, handleAnalyze]);

  const progressLabel = (): string => {
    if (appState === "ready") return "Complete";
    if (!jobStatus) return "Preparing…";
    if (jobStatus.state === "downloading")
      return jobStatus.progress > 0
        ? `${Math.round(jobStatus.progress)}%`
        : "0%";
    if (jobStatus.state === "merging") return "Merging…";
    return "Preparing…";
  };

  const busy = appState === "analyzing" || appState === "downloading";

  /* ─── Render ──────────────────────────────────────────── */
  return (
    <div className="min-h-[100dvh] bg-black text-white flex flex-col">
      {/* ── Background ── */}
      <div className="fixed inset-0 -z-10">
        {/* Subtle radial vignette — pure CSS, no blur artifacts */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(30,30,40,1) 0%, rgba(0,0,0,1) 100%)",
          }}
        />
        {/* Fine noise texture via SVG data-uri for premium feel */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
            backgroundRepeat: "repeat",
            backgroundSize: "128px 128px",
          }}
        />
      </div>

      {/* ── Header ── */}
      <header className="pt-safe-top shrink-0">
        <motion.div
          className="flex flex-col items-center pt-14 pb-8 px-6"
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/[0.08] flex items-center justify-center mb-5">
            <Download className="w-5 h-5 text-white/70" strokeWidth={1.8} />
          </div>
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-white/95">
            Video Downloader
          </h1>
          <p className="text-[13px] text-white/30 mt-1 tracking-wide font-medium">
            Private Media Utility
          </p>
        </motion.div>
      </header>

      {/* ── Main ── */}
      <main className="flex-1 flex flex-col items-center px-5 pb-safe-bottom">
        <motion.div
          className="w-full max-w-[480px] space-y-5"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* ── URL Input ── */}
          <div
            className={`
              relative rounded-2xl border transition-colors duration-300
              ${busy ? "border-white/[0.06] bg-white/[0.03]" : "border-white/[0.08] bg-white/[0.04] hover:border-white/[0.12]"}
              focus-within:border-white/[0.18] focus-within:bg-white/[0.05]
            `}
          >
            <div className="flex items-center px-4 gap-3">
              <Link2
                className="w-[18px] h-[18px] text-white/25 shrink-0"
                strokeWidth={1.8}
              />
              <input
                ref={inputRef}
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (appState === "error") resetState();
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !busy && url.trim())
                    handleAnalyze();
                }}
                placeholder="Paste YouTube URL"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                enterKeyHint="go"
                disabled={busy}
                className="flex-1 bg-transparent py-4 text-[15px] text-white/90 placeholder:text-white/25 focus:outline-none disabled:opacity-40"
              />
              <AnimatePresence mode="wait">
                {url && !busy ? (
                  <motion.button
                    key="clear"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.15 }}
                    onClick={() => {
                      setUrl("");
                      resetState();
                      inputRef.current?.focus();
                    }}
                    className="p-1.5 -mr-1 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-colors"
                    aria-label="Clear"
                  >
                    <X className="w-4 h-4" />
                  </motion.button>
                ) : !url && !busy ? (
                  <motion.button
                    key="paste"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.15 }}
                    onClick={handlePaste}
                    className="flex items-center gap-1.5 px-3 py-1.5 -mr-1 rounded-lg bg-white/[0.06] text-white/50 text-[12px] font-medium hover:bg-white/[0.1] hover:text-white/70 active:scale-95 transition-all touch-manipulation"
                  >
                    <ClipboardPaste className="w-3.5 h-3.5" />
                    Paste
                  </motion.button>
                ) : null}
              </AnimatePresence>
            </div>
          </div>

          {/* ── Analyze Button ── */}
          <AnimatePresence>
            {appState === "idle" && url.trim() && (
              <motion.button
                key="analyze"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8, transition: { duration: 0.15 } }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                onClick={() => handleAnalyze()}
                className="w-full py-3.5 rounded-2xl bg-white text-black text-[15px] font-semibold
                           hover:bg-white/90 active:scale-[0.98] transition-all touch-manipulation
                           flex items-center justify-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                Analyze Video
              </motion.button>
            )}
          </AnimatePresence>

          {/* ── Error ── */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6, transition: { duration: 0.15 } }}
                className="rounded-2xl border border-red-500/20 bg-red-500/[0.07] p-4 flex items-start gap-3"
              >
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] text-red-200/90 leading-relaxed">
                    {error}
                  </p>
                  <button
                    onClick={() => {
                      setError("");
                      setAppState(metadata ? "preview" : "idle");
                    }}
                    className="mt-2 text-[12px] font-medium text-red-400/80 hover:text-red-300 transition-colors"
                  >
                    Dismiss
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Loading ── */}
          <AnimatePresence>
            {appState === "analyzing" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center py-16 gap-4"
              >
                <div className="relative">
                  <Loader2 className="w-7 h-7 text-white/40 animate-spin" />
                </div>
                <p className="text-[13px] text-white/30 font-medium">
                  Extracting metadata…
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Video Card ── */}
          <AnimatePresence>
            {metadata &&
              (appState === "preview" ||
                appState === "downloading" ||
                appState === "ready") && (
                <motion.div
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    duration: 0.5,
                    ease: [0.22, 1, 0.36, 1],
                  }}
                  className="rounded-2xl border border-white/[0.08] bg-white/[0.03] overflow-hidden"
                >
                  {/* Thumbnail */}
                  <div className="relative aspect-video bg-white/[0.02]">
                    {metadata.thumbnail ? (
                      <img
                        src={metadata.thumbnail}
                        alt=""
                        className="w-full h-full object-cover"
                        loading="eager"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Download className="w-10 h-10 text-white/10" />
                      </div>
                    )}
                    {/* Bottom scrim */}
                    <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/70 to-transparent" />
                    {metadata.duration && (
                      <span className="absolute bottom-3 right-3 text-[11px] font-mono text-white/80 bg-black/50 backdrop-blur-sm px-2 py-0.5 rounded-md">
                        {formatDuration(metadata.duration)}
                      </span>
                    )}
                  </div>

                  {/* Info + Actions */}
                  <div className="px-5 pt-4 pb-5 space-y-5">
                    {/* Title & Channel */}
                    <div>
                      <h2 className="text-[15px] font-medium text-white/90 leading-snug line-clamp-2">
                        {metadata.title}
                      </h2>
                      {metadata.channel && (
                        <p className="text-[13px] text-white/35 mt-1">
                          {metadata.channel}
                        </p>
                      )}
                    </div>

                    {/* Quality + Download */}
                    {appState === "preview" && (
                      <div className="space-y-3">
                        {/* Quality select */}
                        <div className="relative">
                          <select
                            value={selectedQuality}
                            onChange={(e) =>
                              setSelectedQuality(e.target.value)
                            }
                            className="w-full appearance-none bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-3 pr-10 text-[14px] text-white/80 focus:outline-none focus:border-white/[0.18] cursor-pointer transition-colors"
                          >
                            {metadata.formats.map((f) => (
                              <option
                                key={f.quality}
                                value={f.quality}
                                className="bg-zinc-900 text-white"
                              >
                                {f.label}
                              </option>
                            ))}
                          </select>
                          <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
                        </div>

                        {/* Download button */}
                        <button
                          onClick={handleDownload}
                          className="w-full py-3.5 rounded-xl bg-white text-black text-[15px] font-semibold
                                     hover:bg-white/90 active:scale-[0.98] transition-all touch-manipulation
                                     flex items-center justify-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Download{" "}
                          {metadata.formats
                            .find((f) => f.quality === selectedQuality)
                            ?.container.toUpperCase() || "MP4"}
                        </button>
                      </div>
                    )}

                    {/* Progress */}
                    {(appState === "downloading" || appState === "ready") && (
                      <div className="space-y-4">
                        <div className="space-y-2.5">
                          <div className="flex items-center justify-between text-[13px]">
                            <span
                              className={
                                appState === "ready"
                                  ? "text-emerald-400 font-medium"
                                  : "text-white/50"
                              }
                            >
                              {appState === "ready"
                                ? "Download Complete"
                                : "Downloading…"}
                            </span>
                            <span className="text-white/30 font-mono tabular-nums">
                              {progressLabel()}
                            </span>
                          </div>
                          {/* Track */}
                          <div className="h-1 w-full rounded-full bg-white/[0.06] overflow-hidden">
                            <motion.div
                              className={`h-full rounded-full ${
                                appState === "ready"
                                  ? "bg-emerald-400"
                                  : "bg-white/60"
                              }`}
                              initial={{ width: 0 }}
                              animate={{
                                width: `${
                                  appState === "ready"
                                    ? 100
                                    : jobStatus?.progress ?? 0
                                }%`,
                              }}
                              transition={{
                                duration: 0.6,
                                ease: "easeOut",
                              }}
                            />
                          </div>
                          {appState === "ready" && jobStatus?.file_size && (
                            <p className="text-[12px] text-white/25 text-right">
                              {formatBytes(jobStatus.file_size)}
                            </p>
                          )}
                        </div>

                        {appState === "ready" && jobStatus && (
                          <motion.a
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.15 }}
                            href={getDownloadUrl(jobStatus.id)}
                            download={jobStatus.filename || "video.mp4"}
                            className="flex items-center justify-center gap-2 w-full py-3 rounded-xl
                                       border border-emerald-500/25 bg-emerald-500/[0.08] text-emerald-400
                                       text-[14px] font-medium hover:bg-emerald-500/[0.12] active:scale-[0.98]
                                       transition-all touch-manipulation"
                          >
                            <CheckCircle2 className="w-4.5 h-4.5" />
                            Save to Device
                          </motion.a>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
          </AnimatePresence>

          {/* ── Reset ── */}
          <AnimatePresence>
            {(appState === "ready" ||
              (appState === "error" && metadata)) && (
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => {
                  setUrl("");
                  resetState();
                  inputRef.current?.focus();
                }}
                className="w-full flex items-center justify-center gap-2 py-3 text-[13px] text-white/30 hover:text-white/50 transition-colors touch-manipulation"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                New Download
              </motion.button>
            )}
          </AnimatePresence>
        </motion.div>
      </main>

      {/* ── Footer ── */}
      <footer className="shrink-0 text-center py-6 pb-safe-bottom">
        <p className="text-[11px] text-white/15 font-medium tracking-[0.08em] uppercase">
          Authorized Personal Use
        </p>
      </footer>
    </div>
  );
}
