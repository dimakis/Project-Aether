"""Tests for distributed mode dispatch in the streaming handler (Phase 5).

When DEPLOYMENT_MODE=distributed, the handler should delegate to
the remote Architect service via A2ARemoteClient instead of creating
an in-process ArchitectWorkflow.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestShouldUseDistributedDispatch:
    """_should_use_distributed() checks deployment mode."""

    def test_returns_false_in_monolith_mode(self):
        from src.api.routes.openai_compat.handlers import _should_use_distributed

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "monolith"
            assert _should_use_distributed() is False

    def test_returns_true_in_distributed_mode(self):
        from src.api.routes.openai_compat.handlers import _should_use_distributed

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            assert _should_use_distributed() is True


class TestDistributedArchitectCall:
    """In distributed mode, the handler calls the Architect via A2A."""

    @pytest.mark.asyncio()
    async def test_creates_a2a_client_with_architect_url(self):
        from src.api.routes.openai_compat.handlers import _create_distributed_client

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.architect_service_url = "http://architect:8000"
            client = _create_distributed_client()

        assert client.base_url == "http://architect:8000"
