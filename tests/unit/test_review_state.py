"""Unit tests for ReviewState model (Feature 28).

Tests the LangGraph state model used by the config review workflow.
"""

from src.graph.state import ReviewState


class TestReviewState:
    """Tests for ReviewState model."""

    def test_default_construction(self):
        """ReviewState can be created with all defaults."""
        state = ReviewState()
        assert state.targets == []
        assert state.configs == {}
        assert state.entity_context == {}
        assert state.ds_findings == []
        assert state.suggestions == []
        assert state.review_session_id is None
        assert state.split_requested is False
        assert state.error is None
        assert state.focus is None

    def test_with_single_target(self):
        """ReviewState accepts a single automation target."""
        state = ReviewState(targets=["automation.kitchen_lights"])
        assert state.targets == ["automation.kitchen_lights"]
        assert len(state.targets) == 1

    def test_with_multiple_targets(self):
        """ReviewState accepts multiple targets for batch review."""
        targets = [
            "automation.kitchen_lights",
            "automation.bedroom_fan",
            "automation.garage_door",
        ]
        state = ReviewState(targets=targets)
        assert len(state.targets) == 3
        assert state.targets == targets

    def test_configs_store_entity_to_yaml_mapping(self):
        """configs maps entity_id to original YAML string."""
        state = ReviewState(
            configs={
                "automation.kitchen_lights": "alias: Kitchen Lights\ntrigger:\n  platform: state",
                "automation.bedroom_fan": "alias: Bedroom Fan\ntrigger:\n  platform: time",
            }
        )
        assert len(state.configs) == 2
        assert "Kitchen Lights" in state.configs["automation.kitchen_lights"]

    def test_ds_findings_stores_structured_findings(self):
        """ds_findings stores analysis results from DS team."""
        findings = [
            {
                "analyst": "energy",
                "finding": "Peak usage correlates with this automation",
                "confidence": 0.85,
            },
            {
                "analyst": "behavioral",
                "finding": "Never triggered when nobody is home",
                "confidence": 0.92,
            },
        ]
        state = ReviewState(ds_findings=findings)
        assert len(state.ds_findings) == 2
        assert state.ds_findings[0]["analyst"] == "energy"

    def test_suggestions_stores_per_target_suggestions(self):
        """suggestions stores architect's suggested changes per target."""
        suggestions = [
            {
                "entity_id": "automation.kitchen_lights",
                "suggested_yaml": "alias: Kitchen Lights\ntrigger:\n  platform: state",
                "review_notes": [
                    {
                        "change": "Added presence condition",
                        "rationale": "test",
                        "category": "behavioral",
                    }
                ],
            }
        ]
        state = ReviewState(suggestions=suggestions)
        assert len(state.suggestions) == 1
        assert state.suggestions[0]["entity_id"] == "automation.kitchen_lights"

    def test_review_session_id_for_batch_grouping(self):
        """review_session_id groups batch review results."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        state = ReviewState(review_session_id=session_id)
        assert state.review_session_id == session_id

    def test_split_requested_flag(self):
        """split_requested controls whether to create individual proposals."""
        state = ReviewState(split_requested=True)
        assert state.split_requested is True

    def test_focus_area(self):
        """focus narrows DS team analysis to a specific area."""
        state = ReviewState(focus="energy")
        assert state.focus == "energy"

    def test_error_captures_workflow_failures(self):
        """error stores failure messages from workflow nodes."""
        state = ReviewState(error="Failed to fetch automation config")
        assert state.error == "Failed to fetch automation config"

    def test_inherits_base_state_fields(self):
        """ReviewState has run_id and started_at from BaseState."""
        state = ReviewState()
        assert state.run_id is not None
        assert state.started_at is not None

    def test_has_message_history(self):
        """ReviewState supports message history from MessageState."""
        state = ReviewState()
        assert hasattr(state, "messages")
        assert state.messages == []
