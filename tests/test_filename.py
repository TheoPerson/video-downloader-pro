"""Tests for filename sanitization."""

import pytest
from backend.filename import sanitize_filename, make_safe_path_component


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_normal_title(self):
        result = sanitize_filename("My Cool Video")
        assert result == "My Cool Video.mp4"

    def test_with_extension(self):
        result = sanitize_filename("video", ".m4a")
        assert result == "video.m4a"

    def test_removes_path_separators(self):
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result
        assert ".." not in result

    def test_removes_unsafe_chars(self):
        result = sanitize_filename('video: "the best?" <wow>')
        assert ":" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result
        assert "?" not in result

    def test_removes_control_chars(self):
        result = sanitize_filename("video\x00\x01\x1f")
        assert "\x00" not in result
        assert "\x01" not in result

    def test_empty_name(self):
        result = sanitize_filename("")
        assert result == "video.mp4"

    def test_strips_existing_video_extension(self):
        result = sanitize_filename("video.webm", ".mp4")
        assert result == "video.mp4"

    def test_preserves_non_video_dots(self):
        result = sanitize_filename("Dr. Jones explains v2.0")
        assert result == "Dr. Jones explains v2.0.mp4"

    def test_long_title_truncated(self):
        long_name = "A" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_unicode_preserved(self):
        result = sanitize_filename("日本語タイトル")
        assert "日本語タイトル" in result

    def test_collapses_multiple_spaces(self):
        result = sanitize_filename("video   with    spaces")
        assert "   " not in result

    def test_forces_extension(self):
        result = sanitize_filename("no-ext")
        assert result.endswith(".mp4")

    def test_extension_without_dot(self):
        result = sanitize_filename("video", "mp4")
        assert result == "video.mp4"


class TestMakeSafePathComponent:
    """Test path component sanitization."""

    def test_normal_string(self):
        assert make_safe_path_component("hello") == "hello"

    def test_removes_unsafe(self):
        result = make_safe_path_component("../../../etc")
        assert ".." not in result

    def test_empty_string(self):
        assert make_safe_path_component("") == "unknown"
