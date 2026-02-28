"""Unit tests for HITL push notifications.

Tests the notification action handler and send functions with
mocked HA client, DB session, and ProposalRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.hitl.push_notification import (
    handle_notification_action,
    send_approval_notification,
    send_test_notification,
)


@pytest.mark.asyncio
class TestHandleNotificationAction:
    """Tests for handle_notification_action()."""

    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.approve = AsyncMock(return_value=True)
        repo.reject = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    async def test_approve_prefix_calls_repo_approve(
        self, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        proposal_id = "abc12345-dead-beef-cafe-123456789abc"

        with (
            patch("src.storage.get_session") as mock_gs,
            patch("src.dal.ProposalRepository", return_value=mock_repo),
        ):
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await handle_notification_action(f"APPROVE_{proposal_id}")

        assert result["status"] == "success"
        assert result["action"] == "approve"
        assert result["proposal_id"] == proposal_id
        mock_repo.approve.assert_awaited_once_with(proposal_id, approved_by="push_notification")
        mock_session.commit.assert_awaited_once()

    async def test_reject_prefix_calls_repo_reject(
        self, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        proposal_id = "abc12345-dead-beef-cafe-123456789abc"

        with (
            patch("src.storage.get_session") as mock_gs,
            patch("src.dal.ProposalRepository", return_value=mock_repo),
        ):
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await handle_notification_action(f"REJECT_{proposal_id}")

        assert result["status"] == "success"
        assert result["action"] == "reject"
        mock_repo.reject.assert_awaited_once_with(
            proposal_id, reason="Rejected via push notification"
        )

    async def test_unknown_prefix_returns_ignored(self) -> None:
        result = await handle_notification_action("SNOOZE_some-id")

        assert result["status"] == "ignored"
        assert result["action_id"] == "SNOOZE_some-id"


@pytest.mark.asyncio
class TestSendApprovalNotification:
    """Tests for send_approval_notification()."""

    async def test_ui_only_channel_returns_skipped(self) -> None:
        with patch(
            "src.hitl.push_notification._get_hitl_settings",
            return_value=("notify.mobile_app_iphone", "ui_only"),
        ):
            result = await send_approval_notification(
                proposal_id="test-id",
                title="Test",
                description="Test action",
            )

        assert result["success"] is False
        assert result["skipped"] is True
        assert result["reason"] == "ui_only channel"


@pytest.mark.asyncio
class TestSendTestNotification:
    """Tests for send_test_notification()."""

    async def test_calls_ha_service_correctly(self) -> None:
        mock_ha = MagicMock()
        mock_ha.call_service = AsyncMock(return_value={"result": "ok"})

        with patch(
            "src.ha.get_ha_client_async",
            new_callable=AsyncMock,
            return_value=mock_ha,
        ):
            result = await send_test_notification("notify.mobile_app_iphone")

        assert result["success"] is True
        mock_ha.call_service.assert_awaited_once_with(
            "notify",
            "mobile_app_iphone",
            {"message": "This is a test notification from Aether.", "title": "Aether Test"},
        )
