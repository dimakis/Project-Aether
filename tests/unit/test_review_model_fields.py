"""Unit tests for Smart Config Review model extensions (Feature 28).

Tests the new review-related fields on AutomationProposal:
- original_yaml: Text field for storing the original config before review
- review_notes: JSONB field for structured change annotations
- review_session_id: UUID for grouping batch reviews
- parent_proposal_id: UUID FK for split proposal tracking
"""

from src.storage.entities.automation_proposal import (
    AutomationProposal,
    ProposalStatus,
)


class TestReviewFields:
    """Tests for review-related fields on AutomationProposal."""

    def _make_proposal(self, **kwargs) -> AutomationProposal:
        """Create a proposal with defaults for required fields."""
        defaults = {
            "id": "test-review-id",
            "name": "Test Review Proposal",
            "trigger": {"platform": "state", "entity_id": "light.kitchen"},
            "actions": {"service": "light.turn_off", "entity_id": "light.kitchen"},
            "mode": "single",
            "status": ProposalStatus.DRAFT,
            "proposal_type": "automation",
        }
        defaults.update(kwargs)
        return AutomationProposal(**defaults)

    def test_original_yaml_defaults_to_none(self):
        """original_yaml is None when not set (new proposals)."""
        p = self._make_proposal()
        assert p.original_yaml is None

    def test_original_yaml_stores_yaml_string(self):
        """original_yaml stores the original config YAML as a string."""
        yaml_content = """automation:
  alias: Kitchen Lights
  trigger:
    platform: state
    entity_id: light.kitchen
  action:
    service: light.turn_off
"""
        p = self._make_proposal(original_yaml=yaml_content)
        assert p.original_yaml == yaml_content
        assert "Kitchen Lights" in p.original_yaml

    def test_review_notes_defaults_to_none(self):
        """review_notes is None when not set."""
        p = self._make_proposal()
        assert p.review_notes is None

    def test_review_notes_stores_structured_list(self):
        """review_notes stores a list of change annotations."""
        notes = [
            {
                "change": "Added presence condition",
                "rationale": "Automation triggers even when nobody is home",
                "category": "behavioral",
            },
            {
                "change": "Reduced brightness during peak hours",
                "rationale": "Peak energy usage between 5-8 PM",
                "category": "energy",
            },
        ]
        p = self._make_proposal(review_notes=notes)
        assert p.review_notes == notes
        assert len(p.review_notes) == 2
        assert p.review_notes[0]["category"] == "behavioral"
        assert p.review_notes[1]["category"] == "energy"

    def test_review_session_id_defaults_to_none(self):
        """review_session_id is None for non-batch reviews."""
        p = self._make_proposal()
        assert p.review_session_id is None

    def test_review_session_id_stores_uuid_string(self):
        """review_session_id stores a UUID for batch grouping."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        p = self._make_proposal(review_session_id=session_id)
        assert p.review_session_id == session_id

    def test_parent_proposal_id_defaults_to_none(self):
        """parent_proposal_id is None for non-split proposals."""
        p = self._make_proposal()
        assert p.parent_proposal_id is None

    def test_parent_proposal_id_stores_uuid_string(self):
        """parent_proposal_id links split proposals to their parent."""
        parent_id = "660e8400-e29b-41d4-a716-446655440000"
        p = self._make_proposal(parent_proposal_id=parent_id)
        assert p.parent_proposal_id == parent_id

    def test_is_review_property(self):
        """is_review returns True when original_yaml is present."""
        # Non-review proposal
        p = self._make_proposal()
        assert p.is_review is False

        # Review proposal
        p_review = self._make_proposal(original_yaml="some: yaml")
        assert p_review.is_review is True

    def test_review_fields_coexist_with_existing_fields(self):
        """Review fields work alongside all existing proposal fields."""
        p = self._make_proposal(
            original_yaml="original: yaml",
            review_notes=[{"change": "test", "rationale": "reason", "category": "efficiency"}],
            review_session_id="550e8400-e29b-41d4-a716-446655440000",
            parent_proposal_id="660e8400-e29b-41d4-a716-446655440000",
            description="A review of kitchen automation",
            proposal_type="automation",
        )
        # Existing fields still work
        assert p.name == "Test Review Proposal"
        assert p.status == ProposalStatus.DRAFT
        assert p.proposal_type == "automation"
        assert p.description == "A review of kitchen automation"
        # Review fields present
        assert p.original_yaml == "original: yaml"
        assert len(p.review_notes) == 1
        assert p.review_session_id is not None
        assert p.parent_proposal_id is not None
