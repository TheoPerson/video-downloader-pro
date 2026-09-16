/**
 * URL validation utilities for the frontend.
 */

const YOUTUBE_PATTERNS = [
  /^https?:\/\/(www\.)?youtube\.com\/watch\?.*v=[a-zA-Z0-9_-]{11}/,
  /^https?:\/\/youtu\.be\/[a-zA-Z0-9_-]{11}/,
  /^https?:\/\/(www\.)?youtube\.com\/shorts\/[a-zA-Z0-9_-]{11}/,
  /^https?:\/\/(www\.)?youtube\.com\/embed\/[a-zA-Z0-9_-]{11}/,
  /^https?:\/\/(www\.)?youtube\.com\/live\/[a-zA-Z0-9_-]{11}/,
  /^https?:\/\/m\.youtube\.com\/watch\?.*v=[a-zA-Z0-9_-]{11}/,
];

/**
 * Check if a string looks like a supported video URL.
 */
export function isValidVideoUrl(url: string): boolean {
  const trimmed = url.trim();
  return YOUTUBE_PATTERNS.some((pattern) => pattern.test(trimmed));
}

/**
 * Check if a string looks like it could be any URL.
 */
export function looksLikeUrl(text: string): boolean {
  return /^https?:\/\/.+/.test(text.trim());
}
