"""Tests for URL validation and normalization."""

import pytest
from backend.url_validator import validate_url, URLValidationError, extract_video_id


class TestValidateUrl:
    """Test URL validation and normalization."""

    def test_standard_youtube_url(self):
        result = validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_short_youtube_url(self):
        result = validate_url("https://youtu.be/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_shorts_url(self):
        result = validate_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_embed_url(self):
        result = validate_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_live_url(self):
        result = validate_url("https://www.youtube.com/live/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_mobile_youtube_url(self):
        result = validate_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        result = validate_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        )
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_url_with_whitespace(self):
        result = validate_url("  https://www.youtube.com/watch?v=dQw4w9WgXcQ  ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_empty_url(self):
        with pytest.raises(URLValidationError, match="Please enter a URL"):
            validate_url("")

    def test_blank_url(self):
        with pytest.raises(URLValidationError, match="Please enter a URL"):
            validate_url("   ")

    def test_no_protocol(self):
        with pytest.raises(URLValidationError, match="must start with"):
            validate_url("www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_unsupported_host(self):
        with pytest.raises(URLValidationError, match="not supported"):
            validate_url("https://www.vimeo.com/12345")

    def test_arbitrary_url_rejected(self):
        with pytest.raises(URLValidationError, match="not supported"):
            validate_url("https://evil.com/malicious")

    def test_private_ip_rejected(self):
        with pytest.raises(URLValidationError, match="not supported"):
            validate_url("http://192.168.1.1/admin")

    def test_localhost_rejected(self):
        with pytest.raises(URLValidationError, match="not supported"):
            validate_url("http://localhost:8080/api")

    def test_invalid_video_id(self):
        with pytest.raises(URLValidationError):
            validate_url("https://www.youtube.com/watch?v=short")

    def test_no_video_id(self):
        with pytest.raises(URLValidationError):
            validate_url("https://www.youtube.com/watch")

    def test_youtube_channel_rejected(self):
        with pytest.raises(URLValidationError):
            validate_url("https://www.youtube.com/@username")

    def test_http_youtube_url(self):
        result = validate_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class TestExtractVideoId:
    """Test video ID extraction."""

    def test_extract_from_normalized(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_no_id(self):
        with pytest.raises(URLValidationError):
            extract_video_id("https://www.youtube.com/watch")
