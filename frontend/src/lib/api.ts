/**
 * API client for the video downloader backend.
 */

const API_BASE = ""; // Empty to use relative paths (proxied via next.config.ts)

export interface VideoFormat {
  quality: string;
  label: string;
  container: string;
}

export interface VideoMetadata {
  id: string;
  title: string;
  thumbnail: string;
  channel: string;
  duration: number | null;
  formats: VideoFormat[];
}

export interface JobStatus {
  id: string;
  state: string;
  progress: number;
  error: string | null;
  title: string | null;
  filename: string | null;
  file_size: number | null;
  created_at: number;
}

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "An unexpected error occurred.";
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Response may not be JSON
    }
    throw new ApiError(response.status, message);
  }
  return response.json();
}

/**
 * Analyze a video URL and return metadata.
 */
export async function analyzeVideo(url: string): Promise<VideoMetadata> {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return handleResponse<VideoMetadata>(response);
}

/**
 * Start a download job.
 */
export async function startDownload(
  url: string,
  quality: string,
  format: string = "mp4",
): Promise<{ job_id: string; state: string }> {
  const response = await fetch(`${API_BASE}/api/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, quality, format }),
  });
  return handleResponse<{ job_id: string; state: string }>(response);
}

/**
 * Get the status of a download job.
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  return handleResponse<JobStatus>(response);
}

/**
 * Get the download URL for a completed job.
 */
export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/jobs/${jobId}/file`;
}

/**
 * Format duration in seconds to human-readable string.
 */
export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60);
    const remainMins = mins % 60;
    return `${hrs}:${remainMins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Format bytes to human-readable string.
 */
export function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}
