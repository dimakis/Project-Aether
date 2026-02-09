"""Integration tests for Chat API.

T098: Chat API with WebSocket tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from src.api.main import create_app

    app = create_app()
    return TestClient(app)


class TestChatAPIEndpoints:
    """Test chat API endpoints."""

    @pytest.mark.asyncio
    async def test_list_conversations_empty(self, client):
        """Test listing conversations when empty."""
        with patch("src.api.routes.chat.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock repository
            with patch("src.api.routes.chat.ConversationRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.list_by_user = AsyncMock(return_value=[])
                mock_repo.count = AsyncMock(return_value=0)

                response = client.get("/api/v1/conversations")

                assert response.status_code == 200
                data = response.json()
                assert data["items"] == []
                assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, client):
        """Test getting non-existent conversation."""
        with patch("src.api.routes.chat.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("src.api.routes.chat.ConversationRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_id = AsyncMock(return_value=None)

                response = client.get("/api/v1/conversations/non-existent")

                assert response.status_code == 404


class TestProposalAPIEndpoints:
    """Test proposal API endpoints."""

    @pytest.mark.asyncio
    async def test_list_proposals_empty(self, client):
        """Test listing proposals when empty."""
        with patch("src.api.routes.proposals.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("src.api.routes.proposals.ProposalRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.list_by_status = AsyncMock(return_value=[])
                mock_repo.count = AsyncMock(return_value=0)

                response = client.get("/api/v1/proposals")

                assert response.status_code == 200
                data = response.json()
                assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_pending_proposals(self, client):
        """Test listing pending proposals."""
        with patch("src.api.routes.proposals.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("src.api.routes.proposals.ProposalRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.list_pending_approval = AsyncMock(return_value=[])
                mock_repo.count = AsyncMock(return_value=0)

                response = client.get("/api/v1/proposals/pending")

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_proposal_not_found(self, client):
        """Test getting non-existent proposal."""
        with patch("src.api.routes.proposals.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("src.api.routes.proposals.ProposalRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_id = AsyncMock(return_value=None)

                response = client.get("/api/v1/proposals/non-existent")

                assert response.status_code == 404


class TestApprovalEndpoints:
    """Test approval/rejection endpoints."""

    @pytest.mark.asyncio
    async def test_approve_proposal_not_found(self, client):
        """Test approving non-existent proposal."""
        with patch("src.api.routes.proposals.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("src.api.routes.proposals.ProposalRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_id = AsyncMock(return_value=None)

                response = client.post(
                    "/api/v1/proposals/non-existent/approve",
                    json={"approved_by": "test_user"},
                )

                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_proposal_not_found(self, client):
        """Test rejecting non-existent proposal."""
        with patch("src.api.routes.proposals.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("src.api.routes.proposals.ProposalRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_id = AsyncMock(return_value=None)

                response = client.post(
                    "/api/v1/proposals/non-existent/reject",
                    json={"reason": "Test", "rejected_by": "user"},
                )

                assert response.status_code == 404
