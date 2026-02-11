"""Tests for BaseAnalyst.analyze_config and ArchitectAgent.synthesize_review.

These methods power the config review workflow (Feature 28).
TDD: Red phase first — tests define the contract.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.architect import ArchitectAgent
from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst

SAMPLE_CONFIG = {
    "automation.kitchen_lights": (
        "trigger:\n"
        "  - platform: sun\n"
        "    event: sunset\n"
        "action:\n"
        "  - service: light.turn_on\n"
        "    entity_id: light.kitchen\n"
    ),
}

SAMPLE_CONTEXT = {"areas": {"kitchen": {"entities": ["light.kitchen"]}}}

SAMPLE_FINDINGS = [
    {
        "title": "Energy waste",
        "description": "Lights stay on indefinitely after sunset",
        "specialist": "energy",
        "confidence": 0.85,
        "entities": ["automation.kitchen_lights"],
    },
    {
        "title": "No off condition",
        "description": "Missing time-based turn-off",
        "specialist": "behavioral",
        "confidence": 0.7,
        "entities": ["automation.kitchen_lights"],
    },
]


class TestAnalyzeConfig:
    """Test BaseAnalyst.analyze_config method."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_findings_key(self):
        """analyze_config must return a dict containing 'findings'."""
        analyst = EnergyAnalyst(ha_client=MagicMock())
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='[{"title": "test", "description": "desc", "specialist": "energy", "confidence": 0.8}]'
        )
        with patch.object(
            type(analyst), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            result = await analyst.analyze_config(
                configs=SAMPLE_CONFIG,
                entity_context=SAMPLE_CONTEXT,
            )
        assert "findings" in result
        assert isinstance(result["findings"], list)

    @pytest.mark.asyncio
    async def test_findings_are_dicts(self):
        """Each finding should be a dict with at least title and description."""
        analyst = BehavioralAnalyst(ha_client=MagicMock())
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='[{"title": "Pattern found", "description": "Automation runs too often", "specialist": "behavioral", "confidence": 0.7}]'
        )
        with patch.object(
            type(analyst), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            result = await analyst.analyze_config(
                configs=SAMPLE_CONFIG,
                entity_context=SAMPLE_CONTEXT,
            )
        assert len(result["findings"]) >= 1
        finding = result["findings"][0]
        assert "title" in finding
        assert "description" in finding

    @pytest.mark.asyncio
    async def test_includes_specialist_name(self):
        """Findings should include the specialist name."""
        analyst = DiagnosticAnalyst(ha_client=MagicMock())
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='[{"title": "Issue", "description": "Potential error", "specialist": "diagnostic", "confidence": 0.9}]'
        )
        with patch.object(
            type(analyst), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            result = await analyst.analyze_config(
                configs=SAMPLE_CONFIG,
                entity_context=SAMPLE_CONTEXT,
            )
        finding = result["findings"][0]
        assert "specialist" in finding

    @pytest.mark.asyncio
    async def test_returns_empty_findings_on_llm_error(self):
        """If the LLM returns unparseable content, return empty findings."""
        analyst = EnergyAnalyst(ha_client=MagicMock())
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="not valid json")
        with patch.object(
            type(analyst), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            result = await analyst.analyze_config(
                configs=SAMPLE_CONFIG,
                entity_context=SAMPLE_CONTEXT,
            )
        assert result["findings"] == []

    @pytest.mark.asyncio
    async def test_llm_receives_config_yaml(self):
        """The LLM prompt must include the config YAML."""
        analyst = EnergyAnalyst(ha_client=MagicMock())
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="[]")
        with patch.object(
            type(analyst), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            await analyst.analyze_config(
                configs=SAMPLE_CONFIG,
                entity_context=SAMPLE_CONTEXT,
            )
        # Check the LLM was called and the config YAML was in the prompt
        mock_llm.ainvoke.assert_called_once()
        messages = mock_llm.ainvoke.call_args[0][0]
        prompt_text = " ".join(str(m.content) for m in messages)
        assert "automation.kitchen_lights" in prompt_text
        assert "light.turn_on" in prompt_text


class TestSynthesizeReview:
    """Test ArchitectAgent.synthesize_review method."""

    @pytest.mark.asyncio
    async def test_returns_list_of_suggestions(self):
        """synthesize_review must return a list of suggestion dicts."""
        architect = ArchitectAgent()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='[{"entity_id": "automation.kitchen_lights", "suggested_yaml": "trigger: []", "review_notes": "Simplified"}]'
        )
        with patch.object(
            type(architect), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            result = await architect.synthesize_review(
                configs=SAMPLE_CONFIG,
                ds_findings=SAMPLE_FINDINGS,
                entity_context=SAMPLE_CONTEXT,
            )
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_suggestion_has_required_fields(self):
        """Each suggestion must have entity_id, suggested_yaml, and review_notes."""
        architect = ArchitectAgent()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='[{"entity_id": "automation.kitchen_lights", "suggested_yaml": "trigger: []", "review_notes": "Added timeout"}]'
        )
        with patch.object(
            type(architect), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            result = await architect.synthesize_review(
                configs=SAMPLE_CONFIG,
                ds_findings=SAMPLE_FINDINGS,
                entity_context=SAMPLE_CONTEXT,
            )
        suggestion = result[0]
        assert "entity_id" in suggestion
        assert "suggested_yaml" in suggestion
        assert "review_notes" in suggestion

    @pytest.mark.asyncio
    async def test_returns_empty_on_llm_error(self):
        """If the LLM returns bad content, return empty list."""
        architect = ArchitectAgent()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="not json")
        with patch.object(
            type(architect), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            result = await architect.synthesize_review(
                configs=SAMPLE_CONFIG,
                ds_findings=SAMPLE_FINDINGS,
                entity_context=SAMPLE_CONTEXT,
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_prompt_includes_findings_and_configs(self):
        """The LLM prompt must include both configs and DS findings."""
        architect = ArchitectAgent()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="[]")
        with patch.object(
            type(architect), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            await architect.synthesize_review(
                configs=SAMPLE_CONFIG,
                ds_findings=SAMPLE_FINDINGS,
                entity_context=SAMPLE_CONTEXT,
            )
        mock_llm.ainvoke.assert_called_once()
        messages = mock_llm.ainvoke.call_args[0][0]
        prompt_text = " ".join(str(m.content) for m in messages)
        assert "automation.kitchen_lights" in prompt_text
        assert "Energy waste" in prompt_text

    @pytest.mark.asyncio
    async def test_respects_focus_parameter(self):
        """When focus is provided, it should be mentioned in the prompt."""
        architect = ArchitectAgent()
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="[]")
        with patch.object(
            type(architect), "llm", new_callable=lambda: property(lambda self: mock_llm)
        ):
            await architect.synthesize_review(
                configs=SAMPLE_CONFIG,
                ds_findings=SAMPLE_FINDINGS,
                entity_context=SAMPLE_CONTEXT,
                focus="energy",
            )
        messages = mock_llm.ainvoke.call_args[0][0]
        prompt_text = " ".join(str(m.content) for m in messages)
        assert "energy" in prompt_text.lower()
