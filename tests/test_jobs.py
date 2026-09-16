"""Tests for job lifecycle management."""

import asyncio
import time

import pytest
from backend.jobs import Job, JobManager, JobState


class TestJobState:
    """Test job state transitions."""

    def test_initial_state(self):
        job = Job(id="test1", url="https://www.youtube.com/watch?v=test")
        assert job.state == JobState.QUEUED

    def test_state_transition(self):
        job = Job(id="test1", url="https://www.youtube.com/watch?v=test")
        job.update_state(JobState.ANALYZING)
        assert job.state == JobState.ANALYZING

    def test_failure_state(self):
        job = Job(id="test1", url="https://www.youtube.com/watch?v=test")
        job.update_state(JobState.FAILED, "Download error")
        assert job.state == JobState.FAILED
        assert job.error == "Download error"

    def test_to_dict(self):
        job = Job(id="test1", url="https://www.youtube.com/watch?v=test")
        d = job.to_dict()
        assert d["id"] == "test1"
        assert d["state"] == "queued"
        assert d["progress"] == 0.0
        assert d["error"] is None

    def test_progress_tracking(self):
        job = Job(id="test1", url="https://www.youtube.com/watch?v=test")
        job.progress = 45.67
        d = job.to_dict()
        assert d["progress"] == 45.7


class TestJobManager:
    """Test job manager operations."""

    @pytest.fixture
    def manager(self):
        return JobManager()

    def test_create_job(self, manager):
        job = manager.create_job(
            "https://www.youtube.com/watch?v=test", "720p"
        )
        assert job.url == "https://www.youtube.com/watch?v=test"
        assert job.quality == "720p"
        assert job.state == JobState.QUEUED

    def test_get_job(self, manager):
        job = manager.create_job(
            "https://www.youtube.com/watch?v=test", "720p"
        )
        retrieved = manager.get_job(job.id)
        assert retrieved is job

    def test_get_nonexistent_job(self, manager):
        assert manager.get_job("nonexistent") is None

    def test_active_count(self, manager):
        assert manager.active_count == 0
        job = manager.create_job(
            "https://www.youtube.com/watch?v=test", "720p"
        )
        assert manager.active_count == 1
        job.update_state(JobState.READY)
        assert manager.active_count == 0

    def test_cancel_job(self, manager):
        job = manager.create_job(
            "https://www.youtube.com/watch?v=test", "720p"
        )
        assert manager.cancel_job(job.id)
        assert job.state == JobState.CANCELLED

    def test_cancel_completed_job(self, manager):
        job = manager.create_job(
            "https://www.youtube.com/watch?v=test", "720p"
        )
        job.update_state(JobState.READY)
        assert not manager.cancel_job(job.id)
