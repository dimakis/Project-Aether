"""Unit tests for review-related API schemas (Feature 28).

Tests ReviewNote, ProposalReviewResponse, and updated ProposalResponse
with review fields.
"""

from datetime import UTC, datetime

from src.api.schemas.proposals import (
    ProposalResponse,
    ProposalYAMLResponse,
    ReviewNote,
)


class TestReviewNote:
    """Tests for ReviewNote schema."""

    def test_valid_review_note(self):
        """ReviewNote accepts valid change, rationale, category."""
        note = ReviewNote(
            change="Added presence condition",
            rationale="Automation triggers even when nobody is home",
            category="behavioral",
        )
        assert note.change == "Added presence condition"
        assert note.rationale == "Automation triggers even when nobody is home"
        assert note.category == "behavioral"

    def test_all_categories(self):
        """ReviewNote accepts all expected category values."""
        for cat in ("energy", "behavioral", "efficiency", "security", "redundancy"):
            note = ReviewNote(change="test", rationale="test", category=cat)
            assert note.category == cat

    def test_serialization(self):
        """ReviewNote serializes to dict correctly."""
        note = ReviewNote(change="test change", rationale="reason", category="energy")
        data = note.model_dump()
        assert data == {"change": "test change", "rationale": "reason", "category": "energy"}


class TestProposalResponseReviewFields:
    """Tests for review fields on ProposalResponse."""

    def _base_kwargs(self) -> dict:
        """Base kwargs for a valid ProposalResponse."""
        now = datetime.now(UTC)
        return {
            "id": "test-id",
            "name": "Test Proposal",
            "status": "proposed",
            "trigger": {},
            "actions": {},
            "mode": "single",
            "conversation_id": None,
            "description": None,
            "conditions": None,
            "service_call": None,
            "ha_automation_id": None,
            "proposed_at": now,
            "approved_at": None,
            "approved_by": None,
            "deployed_at": None,
            "rolled_back_at": None,
            "rejection_reason": None,
            "created_at": now,
            "updated_at": now,
        }

    def test_review_fields_default_to_none(self):
        """Review fields are None by default on ProposalResponse."""
        resp = ProposalResponse(**self._base_kwargs())
        assert resp.original_yaml is None
        assert resp.review_notes is None
        assert resp.review_session_id is None
        assert resp.parent_proposal_id is None

    def test_review_fields_populated(self):
        """Review fields can be set on ProposalResponse."""
        kwargs = self._base_kwargs()
        kwargs.update(
            original_yaml="alias: Test\ntrigger:\n  platform: state",
            review_notes=[
                {"change": "Added condition", "rationale": "reason", "category": "behavioral"}
            ],
            review_session_id="550e8400-e29b-41d4-a716-446655440000",
            parent_proposal_id="660e8400-e29b-41d4-a716-446655440000",
        )
        resp = ProposalResponse(**kwargs)
        assert resp.original_yaml is not None
        assert "Test" in resp.original_yaml
        assert len(resp.review_notes) == 1
        assert resp.review_session_id == "550e8400-e29b-41d4-a716-446655440000"
        assert resp.parent_proposal_id == "660e8400-e29b-41d4-a716-446655440000"

    def test_yaml_response_inherits_review_fields(self):
        """ProposalYAMLResponse includes review fields from parent."""
        kwargs = self._base_kwargs()
        kwargs.update(
            yaml_content="generated: yaml",
            original_yaml="original: yaml",
            review_notes=[{"change": "test", "rationale": "r", "category": "energy"}],
            review_session_id="abc-123",
        )
        resp = ProposalYAMLResponse(**kwargs)
        assert resp.yaml_content == "generated: yaml"
        assert resp.original_yaml == "original: yaml"
        assert len(resp.review_notes) == 1

    def test_serialization_includes_review_fields(self):
        """Serialized response includes review fields when set."""
        kwargs = self._base_kwargs()
        kwargs.update(
            original_yaml="test yaml",
            review_notes=[{"change": "x", "rationale": "y", "category": "efficiency"}],
        )
        resp = ProposalResponse(**kwargs)
        data = resp.model_dump()
        assert "original_yaml" in data
        assert data["original_yaml"] == "test yaml"
        assert "review_notes" in data
        assert len(data["review_notes"]) == 1

    def test_serialization_excludes_none_review_fields(self):
        """Serialized response has None for review fields when not set."""
        resp = ProposalResponse(**self._base_kwargs())
        data = resp.model_dump()
        assert data["original_yaml"] is None
        assert data["review_notes"] is None
