"""Tests for the FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app import app


@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoint:
    """Test health check."""

    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "active_jobs" in data


class TestAnalyzeEndpoint:
    """Test analyze endpoint validation."""

    @pytest.mark.asyncio
    async def test_empty_url(self, client):
        response = await client.post("/api/analyze", json={"url": ""})
        assert response.status_code == 422  # Pydantic validation

    @pytest.mark.asyncio
    async def test_unsupported_url(self, client):
        response = await client.post(
            "/api/analyze", json={"url": "https://evil.com/video"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_url(self, client):
        response = await client.post("/api/analyze", json={})
        assert response.status_code == 422


class TestDownloadEndpoint:
    """Test download endpoint validation."""

    @pytest.mark.asyncio
    async def test_unsupported_url(self, client):
        response = await client.post(
            "/api/download",
            json={"url": "https://evil.com/video", "quality": "720p"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_quality(self, client):
        response = await client.post(
            "/api/download",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "quality": "99999p",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_format(self, client):
        response = await client.post(
            "/api/download",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "quality": "720p",
                "format": "avi",
            },
        )
        assert response.status_code == 422


class TestJobEndpoint:
    """Test job status endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_job_id(self, client):
        response = await client.get("/api/jobs/invalid!job!id")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_nonexistent_job(self, client):
        response = await client.get("/api/jobs/abcdef1234567890")
        assert response.status_code == 404
