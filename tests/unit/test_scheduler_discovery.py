"""Tests for periodic discovery sync via SchedulerService.

Verifies that the scheduler registers a discovery sync job when
discovery_sync_enabled is True and respects the interval setting.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestSchedulerDiscoverySync:
    """Verify discovery sync job is scheduled correctly."""

    async def test_discovery_job_added_when_enabled(self):
        """When discovery_sync_enabled=True, a periodic job should be added."""
        mock_settings = MagicMock()
        mock_settings.scheduler_enabled = True
        mock_settings.scheduler_timezone = "UTC"
        mock_settings.aether_role = "all"
        mock_settings.discovery_sync_enabled = True
        mock_settings.discovery_sync_interval_minutes = 15

        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            from src.scheduler.service import SchedulerService

            service = SchedulerService()

            # Mock the underlying APScheduler
            service._scheduler = MagicMock()
            service._scheduler.get_jobs = MagicMock(return_value=[])

            # Mock sync_jobs to avoid DB call
            service.sync_jobs = AsyncMock()

            await service.start()

            # Should have called add_job for the discovery sync
            add_job_calls = service._scheduler.add_job.call_args_list
            discovery_calls = [
                c for c in add_job_calls
                if c.kwargs.get("id") == "discovery:periodic_sync"
                or (c.args and len(c.args) > 1 and "discovery" in str(c))
            ]
            assert len(discovery_calls) >= 1, (
                f"Expected discovery sync job, got calls: {add_job_calls}"
            )

    async def test_discovery_job_not_added_when_disabled(self):
        """When discovery_sync_enabled=False, no discovery job should be added."""
        mock_settings = MagicMock()
        mock_settings.scheduler_enabled = True
        mock_settings.scheduler_timezone = "UTC"
        mock_settings.aether_role = "all"
        mock_settings.discovery_sync_enabled = False
        mock_settings.discovery_sync_interval_minutes = 30

        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            from src.scheduler.service import SchedulerService

            service = SchedulerService()

            service._scheduler = MagicMock()
            service._scheduler.get_jobs = MagicMock(return_value=[])
            service.sync_jobs = AsyncMock()

            await service.start()

            # No discovery job should be added
            add_job_calls = service._scheduler.add_job.call_args_list
            discovery_calls = [
                c for c in add_job_calls
                if c.kwargs.get("id") == "discovery:periodic_sync"
            ]
            assert len(discovery_calls) == 0, (
                f"Expected no discovery sync job, got: {discovery_calls}"
            )
