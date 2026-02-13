"""Unit tests for Proposal API routes.

Tests all proposal endpoints with mock repository -- no real database
or app lifespan needed.

The get_session() function is called directly (not a FastAPI dependency),
so it must be patched at the source: "src.api.routes.proposals.get_session".
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.storage.entities import ProposalStatus, ProposalType


def _make_test_app():
    """Create a minimal FastAPI app with the proposal router and mock DB."""
    from fastapi import FastAPI

    from src.api.rate_limit import limiter
    from src.api.routes.proposals import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Configure rate limiter for tests (required by @limiter.limit decorators)
    app.state.limiter = limiter

    return app


@pytest.fixture
def proposal_app():
    """Lightweight FastAPI app with proposal routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def proposal_client(proposal_app):
    """Async HTTP client wired to the proposal test app."""
    async with AsyncClient(
        transport=ASGITransport(app=proposal_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_get_session(mock_session):
    """Create a mock get_session async context manager."""

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    return _mock_get_session


@pytest.fixture
def mock_proposal():
    """Create a mock AutomationProposal object with all required attributes."""
    proposal = MagicMock()
    proposal.id = "prop-uuid-1"
    proposal.proposal_type = ProposalType.AUTOMATION.value
    proposal.conversation_id = None
    proposal.name = "Test Automation"
    proposal.description = "Test description"
    proposal.trigger = {"platform": "state", "entity_id": "light.test"}
    proposal.conditions = None
    proposal.actions = {"service": "light.turn_on", "entity_id": "light.test"}
    proposal.mode = "single"
    proposal.service_call = None
    proposal.status = ProposalStatus.PROPOSED
    proposal.ha_automation_id = None
    proposal.proposed_at = datetime(2026, 2, 9, 10, 0, 0, tzinfo=UTC)
    proposal.approved_at = None
    proposal.approved_by = None
    proposal.deployed_at = None
    proposal.rolled_back_at = None
    proposal.rejection_reason = None
    proposal.created_at = datetime(2026, 2, 9, 9, 0, 0, tzinfo=UTC)
    proposal.updated_at = datetime(2026, 2, 9, 9, 0, 0, tzinfo=UTC)
    # Review fields (Feature 28)
    proposal.original_yaml = None
    proposal.review_notes = None
    proposal.review_session_id = None
    proposal.parent_proposal_id = None
    proposal.to_ha_yaml_dict = MagicMock(
        return_value={
            "alias": "Test Automation",
            "trigger": {"platform": "state", "entity_id": "light.test"},
            "action": {"service": "light.turn_on", "entity_id": "light.test"},
        }
    )
    return proposal


@pytest.fixture
def mock_review_proposal():
    """Create a mock review proposal with original_yaml and review_notes set."""
    proposal = MagicMock()
    proposal.id = "prop-uuid-review"
    proposal.proposal_type = ProposalType.AUTOMATION.value
    proposal.conversation_id = None
    proposal.name = "Improved: Sunset Lights"
    proposal.description = "Optimised sunset automation with energy savings"
    proposal.trigger = {"platform": "sun", "event": "sunset", "offset": "-00:30:00"}
    proposal.conditions = None
    proposal.actions = {"service": "light.turn_on", "data": {"brightness": 180}}
    proposal.mode = "single"
    proposal.service_call = None
    proposal.status = ProposalStatus.PROPOSED
    proposal.ha_automation_id = None
    proposal.proposed_at = datetime(2026, 2, 10, 14, 0, 0, tzinfo=UTC)
    proposal.approved_at = None
    proposal.approved_by = None
    proposal.deployed_at = None
    proposal.rolled_back_at = None
    proposal.rejection_reason = None
    proposal.created_at = datetime(2026, 2, 10, 14, 0, 0, tzinfo=UTC)
    proposal.updated_at = datetime(2026, 2, 10, 14, 0, 0, tzinfo=UTC)
    # Review fields populated
    proposal.original_yaml = (
        "alias: Sunset Lights\ntrigger:\n  platform: sun\n  event: sunset\n"
        "action:\n  service: light.turn_on\n"
    )
    proposal.review_notes = [
        {"change": "Added offset", "rationale": "Pre-warm before sunset", "category": "behavioral"},
        {"change": "Reduced brightness", "rationale": "Energy saving", "category": "energy"},
    ]
    proposal.review_session_id = "review-session-abc"
    proposal.parent_proposal_id = None
    proposal.to_ha_yaml_dict = MagicMock(
        return_value={
            "alias": "Improved: Sunset Lights",
            "trigger": {"platform": "sun", "event": "sunset", "offset": "-00:30:00"},
            "action": {"service": "light.turn_on", "data": {"brightness": 180}},
        }
    )
    return proposal


@pytest.fixture
def mock_proposal_approved():
    """Create a mock approved AutomationProposal."""
    proposal = MagicMock()
    proposal.id = "prop-uuid-2"
    proposal.proposal_type = ProposalType.AUTOMATION.value
    proposal.conversation_id = "conv-uuid-1"
    proposal.name = "Approved Automation"
    proposal.description = "Approved description"
    proposal.trigger = {"platform": "state", "entity_id": "sensor.motion"}
    proposal.conditions = None
    proposal.actions = {"service": "light.turn_on", "entity_id": "light.hallway"}
    proposal.mode = "single"
    proposal.service_call = None
    proposal.status = ProposalStatus.APPROVED
    proposal.ha_automation_id = None
    proposal.proposed_at = datetime(2026, 2, 9, 10, 0, 0, tzinfo=UTC)
    proposal.approved_at = datetime(2026, 2, 9, 11, 0, 0, tzinfo=UTC)
    proposal.approved_by = "user1"
    proposal.deployed_at = None
    proposal.rolled_back_at = None
    proposal.rejection_reason = None
    proposal.created_at = datetime(2026, 2, 9, 9, 0, 0, tzinfo=UTC)
    proposal.updated_at = datetime(2026, 2, 9, 11, 0, 0, tzinfo=UTC)
    # Review fields (Feature 28)
    proposal.original_yaml = None
    proposal.review_notes = None
    proposal.review_session_id = None
    proposal.parent_proposal_id = None
    proposal.to_ha_yaml_dict = MagicMock(
        return_value={
            "alias": "Approved Automation",
            "trigger": {"platform": "state", "entity_id": "sensor.motion"},
            "action": {"service": "light.turn_on", "entity_id": "light.hallway"},
        }
    )
    return proposal


@pytest.fixture
def mock_proposal_deployed():
    """Create a mock deployed AutomationProposal."""
    proposal = MagicMock()
    proposal.id = "prop-uuid-3"
    proposal.proposal_type = ProposalType.AUTOMATION.value
    proposal.conversation_id = None
    proposal.name = "Deployed Automation"
    proposal.description = None
    proposal.trigger = {"platform": "time", "at": "08:00:00"}
    proposal.conditions = None
    proposal.actions = {"service": "light.turn_on"}
    proposal.mode = "single"
    proposal.service_call = None
    proposal.status = ProposalStatus.DEPLOYED
    proposal.ha_automation_id = "automation.deployed_automation"
    proposal.proposed_at = datetime(2026, 2, 9, 10, 0, 0, tzinfo=UTC)
    proposal.approved_at = datetime(2026, 2, 9, 11, 0, 0, tzinfo=UTC)
    proposal.approved_by = "user1"
    proposal.deployed_at = datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC)
    proposal.rolled_back_at = None
    proposal.rejection_reason = None
    proposal.created_at = datetime(2026, 2, 9, 9, 0, 0, tzinfo=UTC)
    proposal.updated_at = datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC)
    # Review fields (Feature 28)
    proposal.original_yaml = None
    proposal.review_notes = None
    proposal.review_session_id = None
    proposal.parent_proposal_id = None
    proposal.to_ha_yaml_dict = MagicMock(
        return_value={
            "alias": "Deployed Automation",
            "trigger": {"platform": "time", "at": "08:00:00"},
            "action": {"service": "light.turn_on"},
        }
    )
    return proposal


@pytest.fixture
def mock_proposal_repo(mock_proposal, mock_proposal_approved, mock_proposal_deployed):
    """Create mock ProposalRepository."""
    repo = MagicMock()
    repo.list_by_status = AsyncMock(return_value=[mock_proposal])
    repo.list_pending_approval = AsyncMock(return_value=[mock_proposal])
    repo.get_by_id = AsyncMock(return_value=mock_proposal)
    repo.count = AsyncMock(return_value=1)
    repo.create = AsyncMock(return_value=mock_proposal)
    repo.propose = AsyncMock(return_value=mock_proposal)
    repo.approve = AsyncMock(return_value=mock_proposal_approved)
    repo.reject = AsyncMock(return_value=mock_proposal)
    repo.deploy = AsyncMock(return_value=mock_proposal_deployed)
    repo.rollback = AsyncMock(return_value=mock_proposal)
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.mark.asyncio
class TestListProposals:
    """Tests for GET /api/v1/proposals."""

    async def test_list_proposals_returns_paginated_results(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should return proposals with total count when filtering by status."""
        mock_proposal_repo.list_by_status = AsyncMock(return_value=[mock_proposal])
        mock_proposal_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals?status=proposed")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == "prop-uuid-1"
            assert data["items"][0]["name"] == "Test Automation"
            assert data["limit"] == 50
            assert data["offset"] == 0

    async def test_list_proposals_with_status_filter(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should filter proposals by status."""
        mock_proposal_repo.list_by_status = AsyncMock(return_value=[mock_proposal])
        mock_proposal_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals?status=proposed")

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            mock_proposal_repo.list_by_status.assert_called()
            # Check that it was called with ProposalStatus.PROPOSED
            call_args = mock_proposal_repo.list_by_status.call_args
            assert call_args[0][0] == ProposalStatus.PROPOSED

    async def test_list_proposals_with_invalid_status(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should ignore invalid status and return all proposals."""
        mock_proposal_repo.list_by_status = AsyncMock(return_value=[mock_proposal])
        mock_proposal_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals?status=invalid")

            assert response.status_code == 200
            # Should call list_by_status for all statuses
            assert mock_proposal_repo.list_by_status.call_count > 0

    async def test_list_proposals_with_limit_and_offset(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should respect limit and offset parameters."""
        mock_proposal_repo.list_by_status = AsyncMock(return_value=[mock_proposal])
        mock_proposal_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals?limit=10&offset=5")

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 5

    async def test_list_proposals_empty(self, proposal_client, mock_get_session):
        """Should return empty list when no proposals exist."""
        repo = MagicMock()
        repo.list_by_status = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=repo),
        ):
            response = await proposal_client.get("/api/v1/proposals")

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["total"] == 0


@pytest.mark.asyncio
class TestListPendingProposals:
    """Tests for GET /api/v1/proposals/pending."""

    async def test_list_pending_proposals(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should return only pending proposals."""
        mock_proposal_repo.list_pending_approval = AsyncMock(return_value=[mock_proposal])
        mock_proposal_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals/pending")

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["status"] == "proposed"
            mock_proposal_repo.list_pending_approval.assert_called_once()

    async def test_list_pending_proposals_with_limit(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should respect limit parameter."""
        mock_proposal_repo.list_pending_approval = AsyncMock(return_value=[mock_proposal])
        mock_proposal_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals/pending?limit=20")

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 20
            mock_proposal_repo.list_pending_approval.assert_called_once_with(limit=20)


@pytest.mark.asyncio
class TestGetProposal:
    """Tests for GET /api/v1/proposals/{proposal_id}."""

    async def test_get_proposal_by_id(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should return proposal with YAML content."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals/prop-uuid-1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "prop-uuid-1"
            assert data["name"] == "Test Automation"
            assert "yaml_content" in data
            assert "Proposal ID: prop-uuid-1" in data["yaml_content"]
            mock_proposal_repo.get_by_id.assert_called_once_with("prop-uuid-1")

    async def test_get_proposal_not_found(
        self, proposal_client, mock_proposal_repo, mock_get_session
    ):
        """Should return 404 when proposal not found."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    async def test_get_review_proposal_includes_original_yaml(
        self, proposal_client, mock_proposal_repo, mock_review_proposal, mock_get_session
    ):
        """Review proposals should include original_yaml for diff rendering."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_review_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals/prop-uuid-review")

            assert response.status_code == 200
            data = response.json()
            assert data["original_yaml"] is not None
            assert "Sunset Lights" in data["original_yaml"]
            assert data["yaml_content"] is not None  # suggested YAML also present

    async def test_get_review_proposal_includes_review_notes(
        self, proposal_client, mock_proposal_repo, mock_review_proposal, mock_get_session
    ):
        """Review proposals should include structured review_notes."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_review_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals/prop-uuid-review")

            assert response.status_code == 200
            data = response.json()
            assert data["review_notes"] is not None
            assert len(data["review_notes"]) == 2
            assert data["review_notes"][0]["category"] == "behavioral"
            assert data["review_session_id"] == "review-session-abc"

    async def test_get_non_review_proposal_has_null_review_fields(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Non-review proposals should have null review fields."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals/prop-uuid-1")

            assert response.status_code == 200
            data = response.json()
            assert data["original_yaml"] is None
            assert data["review_notes"] is None
            assert data["review_session_id"] is None

    async def test_list_proposals_includes_review_fields(
        self, proposal_client, mock_proposal_repo, mock_review_proposal, mock_get_session
    ):
        """List endpoint should include review fields on review proposals."""
        mock_proposal_repo.list_by_status = AsyncMock(return_value=[mock_review_proposal])
        mock_proposal_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.get("/api/v1/proposals?status=proposed")

            assert response.status_code == 200
            data = response.json()
            item = data["items"][0]
            assert item["original_yaml"] is not None
            assert item["review_notes"] is not None
            assert item["review_session_id"] == "review-session-abc"


@pytest.mark.asyncio
class TestCreateProposal:
    """Tests for POST /api/v1/proposals."""

    async def test_create_proposal_success(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session, mock_session
    ):
        """Should create and propose a new proposal."""
        mock_proposal_repo.create = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.propose = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals",
                json={
                    "name": "Test Automation",
                    "trigger": {"platform": "state", "entity_id": "light.test"},
                    "actions": {"service": "light.turn_on", "entity_id": "light.test"},
                    "description": "Test description",
                    "mode": "single",
                    "proposal_type": "automation",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "prop-uuid-1"
            assert data["name"] == "Test Automation"
            mock_proposal_repo.create.assert_called_once()
            mock_proposal_repo.propose.assert_called_once_with(mock_proposal.id)
            mock_session.commit.assert_called_once()

    async def test_create_proposal_with_entity_command_type(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session, mock_session
    ):
        """Should create an entity_command type proposal."""
        mock_proposal.proposal_type = ProposalType.ENTITY_COMMAND.value
        mock_proposal_repo.create = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.propose = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals",
                json={
                    "name": "Turn on light",
                    "trigger": [],
                    "actions": [],
                    "proposal_type": "entity_command",
                    "service_call": {
                        "domain": "light",
                        "service": "turn_on",
                        "entity_id": "light.living_room",
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["proposal_type"] == ProposalType.ENTITY_COMMAND.value

    async def test_create_proposal_not_found_after_create(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session, mock_session
    ):
        """Should return 404 if proposal not found after creation."""
        mock_proposal_repo.create = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.propose = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals",
                json={
                    "name": "Test Automation",
                    "trigger": {"platform": "state"},
                    "actions": {"service": "light.turn_on"},
                },
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestApproveProposal:
    """Tests for POST /api/v1/proposals/{proposal_id}/approve."""

    async def test_approve_proposal_success(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal,
        mock_proposal_approved,
        mock_get_session,
        mock_session,
    ):
        """Should approve a pending proposal."""
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal_repo.get_by_id = AsyncMock(
            side_effect=[mock_proposal, mock_proposal_approved]
        )
        mock_proposal_repo.approve = AsyncMock(return_value=mock_proposal_approved)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.api.routes.proposals._log_proposal_assessment") as mock_log,
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-1/approve",
                json={"approved_by": "user1", "comment": "Looks good"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "approved"
            mock_proposal_repo.approve.assert_called_once_with("prop-uuid-1", "user1")
            mock_session.commit.assert_called_once()
            # Route always calls _log_proposal_assessment (even without trace_id)
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["outcome"] == "approved"
            assert call_kwargs["trace_id"] is None

    async def test_approve_proposal_with_trace_id(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal,
        mock_proposal_approved,
        mock_get_session,
        mock_session,
    ):
        """Should log assessment when trace_id is provided."""
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal_repo.get_by_id = AsyncMock(
            side_effect=[mock_proposal, mock_proposal_approved]
        )
        mock_proposal_repo.approve = AsyncMock(return_value=mock_proposal_approved)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.api.routes.proposals._log_proposal_assessment") as mock_log,
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-1/approve",
                json={
                    "approved_by": "user1",
                    "comment": "Looks good",
                    "trace_id": "trace-123",
                },
            )

            assert response.status_code == 200
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["trace_id"] == "trace-123"
            assert call_kwargs["outcome"] == "approved"

    async def test_approve_proposal_not_found(
        self, proposal_client, mock_proposal_repo, mock_get_session
    ):
        """Should return 404 when proposal not found."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/nonexistent/approve",
                json={"approved_by": "user1"},
            )

            assert response.status_code == 404

    async def test_approve_proposal_wrong_status(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should return 400 when proposal is not in PROPOSED status."""
        mock_proposal.status = ProposalStatus.APPROVED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-1/approve",
                json={"approved_by": "user1"},
            )

            assert response.status_code == 400
            assert "cannot approve" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestRejectProposal:
    """Tests for POST /api/v1/proposals/{proposal_id}/reject."""

    async def test_reject_proposal_success(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session, mock_session
    ):
        """Should reject a pending proposal."""
        mock_proposal.status = ProposalStatus.PROPOSED
        rejected_proposal = MagicMock()
        rejected_proposal.id = mock_proposal.id
        rejected_proposal.proposal_type = mock_proposal.proposal_type
        rejected_proposal.conversation_id = mock_proposal.conversation_id
        rejected_proposal.name = mock_proposal.name
        rejected_proposal.description = mock_proposal.description
        rejected_proposal.trigger = mock_proposal.trigger
        rejected_proposal.conditions = mock_proposal.conditions
        rejected_proposal.actions = mock_proposal.actions
        rejected_proposal.mode = mock_proposal.mode
        rejected_proposal.service_call = mock_proposal.service_call
        rejected_proposal.status = ProposalStatus.REJECTED
        rejected_proposal.ha_automation_id = mock_proposal.ha_automation_id
        rejected_proposal.proposed_at = mock_proposal.proposed_at
        rejected_proposal.approved_at = None
        rejected_proposal.approved_by = None
        rejected_proposal.deployed_at = None
        rejected_proposal.rolled_back_at = None
        rejected_proposal.rejection_reason = "Not needed"
        rejected_proposal.created_at = mock_proposal.created_at
        rejected_proposal.updated_at = datetime(2026, 2, 9, 11, 30, 0, tzinfo=UTC)
        rejected_proposal.original_yaml = None
        rejected_proposal.review_notes = None
        rejected_proposal.review_session_id = None
        rejected_proposal.parent_proposal_id = None
        rejected_proposal.to_ha_yaml_dict = mock_proposal.to_ha_yaml_dict
        mock_proposal_repo.get_by_id = AsyncMock(side_effect=[mock_proposal, rejected_proposal])
        mock_proposal_repo.reject = AsyncMock(return_value=rejected_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.api.routes.proposals._log_proposal_assessment") as mock_log,
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-1/reject",
                json={"reason": "Not needed", "rejected_by": "user1"},
            )

            assert response.status_code == 200
            mock_proposal_repo.reject.assert_called_once_with("prop-uuid-1", "Not needed")
            mock_session.commit.assert_called_once()
            # Route always calls _log_proposal_assessment (even without trace_id)
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["outcome"] == "rejected"
            assert call_kwargs["trace_id"] is None

    async def test_reject_proposal_with_trace_id(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session, mock_session
    ):
        """Should log assessment when trace_id is provided."""
        mock_proposal.status = ProposalStatus.PROPOSED
        rejected_proposal = MagicMock()
        rejected_proposal.id = mock_proposal.id
        rejected_proposal.proposal_type = mock_proposal.proposal_type
        rejected_proposal.conversation_id = mock_proposal.conversation_id
        rejected_proposal.name = mock_proposal.name
        rejected_proposal.description = mock_proposal.description
        rejected_proposal.trigger = mock_proposal.trigger
        rejected_proposal.conditions = mock_proposal.conditions
        rejected_proposal.actions = mock_proposal.actions
        rejected_proposal.mode = mock_proposal.mode
        rejected_proposal.service_call = mock_proposal.service_call
        rejected_proposal.status = ProposalStatus.REJECTED
        rejected_proposal.ha_automation_id = mock_proposal.ha_automation_id
        rejected_proposal.proposed_at = mock_proposal.proposed_at
        rejected_proposal.approved_at = None
        rejected_proposal.approved_by = None
        rejected_proposal.deployed_at = None
        rejected_proposal.rolled_back_at = None
        rejected_proposal.rejection_reason = "Not needed"
        rejected_proposal.created_at = mock_proposal.created_at
        rejected_proposal.updated_at = datetime(2026, 2, 9, 11, 30, 0, tzinfo=UTC)
        rejected_proposal.original_yaml = None
        rejected_proposal.review_notes = None
        rejected_proposal.review_session_id = None
        rejected_proposal.parent_proposal_id = None
        rejected_proposal.to_ha_yaml_dict = mock_proposal.to_ha_yaml_dict
        mock_proposal_repo.get_by_id = AsyncMock(side_effect=[mock_proposal, rejected_proposal])
        mock_proposal_repo.reject = AsyncMock(return_value=rejected_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.api.routes.proposals._log_proposal_assessment") as mock_log,
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-1/reject",
                json={
                    "reason": "Not needed",
                    "rejected_by": "user1",
                    "trace_id": "trace-123",
                },
            )

            assert response.status_code == 200
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["trace_id"] == "trace-123"
            assert call_kwargs["outcome"] == "rejected"

    async def test_reject_proposal_not_found(
        self, proposal_client, mock_proposal_repo, mock_get_session
    ):
        """Should return 404 when proposal not found."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/nonexistent/reject",
                json={"reason": "Not needed"},
            )

            assert response.status_code == 404

    async def test_reject_proposal_wrong_status(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should return 400 when proposal cannot be rejected."""
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-1/reject",
                json={"reason": "Not needed"},
            )

            assert response.status_code == 400
            assert "cannot reject" in response.json()["detail"].lower()

    async def test_reject_approved_proposal(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal_approved,
        mock_get_session,
        mock_session,
    ):
        """Should allow rejecting an approved proposal."""
        mock_proposal_approved.status = ProposalStatus.APPROVED
        rejected_proposal = MagicMock()
        rejected_proposal.id = mock_proposal_approved.id
        rejected_proposal.proposal_type = mock_proposal_approved.proposal_type
        rejected_proposal.conversation_id = mock_proposal_approved.conversation_id
        rejected_proposal.name = mock_proposal_approved.name
        rejected_proposal.description = mock_proposal_approved.description
        rejected_proposal.trigger = mock_proposal_approved.trigger
        rejected_proposal.conditions = mock_proposal_approved.conditions
        rejected_proposal.actions = mock_proposal_approved.actions
        rejected_proposal.mode = mock_proposal_approved.mode
        rejected_proposal.service_call = mock_proposal_approved.service_call
        rejected_proposal.status = ProposalStatus.REJECTED
        rejected_proposal.ha_automation_id = mock_proposal_approved.ha_automation_id
        rejected_proposal.proposed_at = mock_proposal_approved.proposed_at
        rejected_proposal.approved_at = mock_proposal_approved.approved_at
        rejected_proposal.approved_by = mock_proposal_approved.approved_by
        rejected_proposal.deployed_at = None
        rejected_proposal.rolled_back_at = None
        rejected_proposal.rejection_reason = "Changed mind"
        rejected_proposal.created_at = mock_proposal_approved.created_at
        rejected_proposal.updated_at = datetime(2026, 2, 9, 11, 30, 0, tzinfo=UTC)
        rejected_proposal.original_yaml = None
        rejected_proposal.review_notes = None
        rejected_proposal.review_session_id = None
        rejected_proposal.parent_proposal_id = None
        rejected_proposal.to_ha_yaml_dict = mock_proposal_approved.to_ha_yaml_dict
        mock_proposal_repo.get_by_id = AsyncMock(
            side_effect=[mock_proposal_approved, rejected_proposal]
        )
        mock_proposal_repo.reject = AsyncMock(return_value=rejected_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-2/reject",
                json={"reason": "Changed mind"},
            )

            assert response.status_code == 200


@pytest.mark.asyncio
class TestDeployProposal:
    """Tests for POST /api/v1/proposals/{proposal_id}/deploy."""

    async def test_deploy_proposal_success(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal_approved,
        mock_proposal_deployed,
        mock_get_session,
        mock_session,
    ):
        """Should deploy an approved proposal."""
        mock_proposal_approved.status = ProposalStatus.APPROVED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_approved)
        mock_proposal_repo.deploy = AsyncMock(return_value=mock_proposal_deployed)

        mock_workflow = MagicMock()
        mock_workflow.deploy = AsyncMock(
            return_value={
                "ha_automation_id": "automation.deployed_automation",
                "deployment_method": "developer_workflow",
                "yaml_content": "alias: Deployed Automation\n",
                "instructions": None,
            }
        )

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.agents.DeveloperWorkflow", return_value=mock_workflow),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-2/deploy")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["proposal_id"] == "prop-uuid-2"
            assert data["ha_automation_id"] == "automation.deployed_automation"
            assert data["method"] == "developer_workflow"
            assert "yaml_content" in data
            mock_session.commit.assert_called_once()

    async def test_deploy_entity_command_proposal(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal_approved,
        mock_get_session,
        mock_session,
    ):
        """Should deploy an entity_command proposal via MCP."""
        entity_proposal = MagicMock()
        entity_proposal.id = "prop-uuid-entity"
        entity_proposal.proposal_type = ProposalType.ENTITY_COMMAND.value
        entity_proposal.conversation_id = None
        entity_proposal.name = "Entity Command"
        entity_proposal.description = None
        entity_proposal.trigger = {}
        entity_proposal.conditions = None
        entity_proposal.actions = {}
        entity_proposal.mode = "single"
        entity_proposal.status = ProposalStatus.APPROVED
        entity_proposal.ha_automation_id = None
        entity_proposal.proposed_at = datetime(2026, 2, 9, 10, 0, 0, tzinfo=UTC)
        entity_proposal.approved_at = datetime(2026, 2, 9, 11, 0, 0, tzinfo=UTC)
        entity_proposal.approved_by = "user1"
        entity_proposal.deployed_at = None
        entity_proposal.rolled_back_at = None
        entity_proposal.rejection_reason = None
        entity_proposal.created_at = datetime(2026, 2, 9, 9, 0, 0, tzinfo=UTC)
        entity_proposal.updated_at = datetime(2026, 2, 9, 11, 0, 0, tzinfo=UTC)
        entity_proposal.service_call = {
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.living_room",
            "data": {},
        }
        entity_proposal.to_ha_yaml_dict = MagicMock(return_value={"alias": "Entity Command"})

        mock_proposal_repo.get_by_id = AsyncMock(return_value=entity_proposal)
        mock_proposal_repo.deploy = AsyncMock(return_value=entity_proposal)

        mock_ha_client = MagicMock()
        mock_ha_client.call_service = AsyncMock()

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.api.routes.proposals.get_ha_client", return_value=mock_ha_client),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-entity/deploy")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["method"] == "mcp_service_call"
            mock_ha_client.call_service.assert_called_once_with(
                domain="light", service="turn_on", data={"entity_id": "light.living_room"}
            )
            mock_session.commit.assert_called_once()

    async def test_deploy_proposal_not_found(
        self, proposal_client, mock_proposal_repo, mock_get_session
    ):
        """Should return 404 when proposal not found."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post("/api/v1/proposals/nonexistent/deploy")

            assert response.status_code == 404

    async def test_deploy_proposal_wrong_status(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should return 400 when proposal is not approved."""
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-1/deploy")

            assert response.status_code == 400
            assert "cannot deploy" in response.json()["detail"].lower()

    async def test_deploy_already_deployed_without_force(
        self, proposal_client, mock_proposal_repo, mock_proposal_deployed, mock_get_session
    ):
        """Should return 400 when deploying already deployed proposal without force."""
        mock_proposal_deployed.status = ProposalStatus.DEPLOYED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_deployed)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-3/deploy")

            assert response.status_code == 400
            assert "already deployed" in response.json()["detail"].lower()

    async def test_deploy_already_deployed_with_force(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal_deployed,
        mock_get_session,
        mock_session,
    ):
        """Should allow redeploying with force=true."""
        mock_proposal_deployed.status = ProposalStatus.DEPLOYED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_deployed)

        mock_workflow = MagicMock()
        mock_workflow.deploy = AsyncMock(
            return_value={
                "ha_automation_id": "automation.deployed_automation",
                "deployment_method": "developer_workflow",
                "yaml_content": "alias: Deployed Automation\n",
            }
        )

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.agents.DeveloperWorkflow", return_value=mock_workflow),
        ):
            response = await proposal_client.post(
                "/api/v1/proposals/prop-uuid-3/deploy", json={"force": True}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    async def test_deploy_proposal_with_error(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal_approved,
        mock_get_session,
        mock_session,
    ):
        """Should handle deployment errors gracefully."""
        mock_proposal_approved.status = ProposalStatus.APPROVED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_approved)

        mock_workflow = MagicMock()
        mock_workflow.deploy = AsyncMock(side_effect=Exception("Deployment failed"))

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.agents.DeveloperWorkflow", return_value=mock_workflow),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-2/deploy")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


@pytest.mark.asyncio
class TestRollbackProposal:
    """Tests for POST /api/v1/proposals/{proposal_id}/rollback."""

    async def test_rollback_proposal_success(
        self,
        proposal_client,
        mock_proposal_repo,
        mock_proposal_deployed,
        mock_get_session,
        mock_session,
    ):
        """Should rollback a deployed proposal."""
        mock_proposal_deployed.status = ProposalStatus.DEPLOYED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_deployed)

        mock_workflow = MagicMock()
        mock_workflow.rollback = AsyncMock(
            return_value={
                "rolled_back": True,
                "ha_automation_id": "automation.deployed_automation",
                "ha_disabled": True,
                "ha_error": None,
                "note": "Rolled back successfully",
            }
        )

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.agents.DeveloperWorkflow", return_value=mock_workflow),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-3/rollback")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["proposal_id"] == "prop-uuid-3"
            assert data["ha_automation_id"] == "automation.deployed_automation"
            assert data["ha_disabled"] is True
            assert "rolled_back_at" in data
            mock_session.commit.assert_called_once()

    async def test_rollback_proposal_not_found(
        self, proposal_client, mock_proposal_repo, mock_get_session
    ):
        """Should return 404 when proposal not found."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post("/api/v1/proposals/nonexistent/rollback")

            assert response.status_code == 404

    async def test_rollback_proposal_wrong_status(
        self, proposal_client, mock_proposal_repo, mock_proposal_approved, mock_get_session
    ):
        """Should return 400 when proposal is not deployed."""
        mock_proposal_approved.status = ProposalStatus.APPROVED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_approved)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-2/rollback")

            assert response.status_code == 400
            assert "cannot rollback" in response.json()["detail"].lower()

    async def test_rollback_proposal_with_error(
        self, proposal_client, mock_proposal_repo, mock_proposal_deployed, mock_get_session
    ):
        """Should handle rollback errors."""
        mock_proposal_deployed.status = ProposalStatus.DEPLOYED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_deployed)

        mock_workflow = MagicMock()
        mock_workflow.rollback = AsyncMock(side_effect=Exception("Rollback failed"))

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
            patch("src.agents.DeveloperWorkflow", return_value=mock_workflow),
        ):
            response = await proposal_client.post("/api/v1/proposals/prop-uuid-3/rollback")

            assert response.status_code == 500
            assert "rollback" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestDeleteProposal:
    """Tests for DELETE /api/v1/proposals/{proposal_id}."""

    async def test_delete_proposal_success(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session, mock_session
    ):
        """Should delete a non-deployed proposal."""
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.delete = AsyncMock(return_value=True)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.delete("/api/v1/proposals/prop-uuid-1")

            assert response.status_code == 204
            mock_proposal_repo.delete.assert_called_once_with("prop-uuid-1")
            mock_session.commit.assert_called_once()

    async def test_delete_proposal_not_found(
        self, proposal_client, mock_proposal_repo, mock_get_session
    ):
        """Should return 404 when proposal not found."""
        mock_proposal_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.delete("/api/v1/proposals/nonexistent")

            assert response.status_code == 404

    async def test_delete_deployed_proposal(
        self, proposal_client, mock_proposal_repo, mock_proposal_deployed, mock_get_session
    ):
        """Should return 400 when trying to delete a deployed proposal."""
        mock_proposal_deployed.status = ProposalStatus.DEPLOYED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal_deployed)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.delete("/api/v1/proposals/prop-uuid-3")

            assert response.status_code == 400
            assert "cannot delete" in response.json()["detail"].lower()
            assert "rollback" in response.json()["detail"].lower()

    async def test_delete_proposal_delete_fails(
        self, proposal_client, mock_proposal_repo, mock_proposal, mock_get_session
    ):
        """Should return 404 when delete returns False."""
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_proposal_repo.delete = AsyncMock(return_value=False)

        with (
            patch("src.api.routes.proposals.get_session", mock_get_session),
            patch("src.api.routes.proposals.ProposalRepository", return_value=mock_proposal_repo),
        ):
            response = await proposal_client.delete("/api/v1/proposals/prop-uuid-1")

            assert response.status_code == 404
