"""Tests for the Architect system prompt content.

Verifies the prompt guides the LLM toward the correct tools and
does NOT reference deprecated tools or patterns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROMPT_PATH = Path("src/agents/prompts/architect_system.md")


@pytest.fixture
def prompt_text() -> str:
    return PROMPT_PATH.read_text()


class TestArchitectPromptReferences:
    """Verify the prompt mentions the right tools and omits deprecated ones."""

    def test_mentions_team_tool(self, prompt_text: str):
        assert "consult_data_science_team" in prompt_text

    def test_mentions_seek_approval(self, prompt_text: str):
        assert "seek_approval" in prompt_text

    def test_mentions_create_insight_schedule(self, prompt_text: str):
        assert "create_insight_schedule" in prompt_text

    def test_does_not_mention_old_ds_delegation(self, prompt_text: str):
        """Old single-DS delegation tools should not appear."""
        assert "diagnose_issue" not in prompt_text
        assert "analyze_energy" not in prompt_text
        assert "analyze_behavior" not in prompt_text

    def test_does_not_mention_run_custom_analysis(self, prompt_text: str):
        """run_custom_analysis is absorbed into team tool."""
        assert "run_custom_analysis" not in prompt_text

    def test_does_not_mention_individual_consult_tools(self, prompt_text: str):
        """Individual consult_* tools should not be referenced."""
        assert "consult_energy_analyst" not in prompt_text
        assert "consult_behavioral_analyst" not in prompt_text
        assert "consult_diagnostic_analyst" not in prompt_text

    def test_mentions_ds_team(self, prompt_text: str):
        """Prompt should describe the Data Science team."""
        text_lower = prompt_text.lower()
        assert "data science team" in text_lower or "ds team" in text_lower

    def test_mentions_specialist_roles(self, prompt_text: str):
        """Prompt should describe the three specialist roles."""
        text_lower = prompt_text.lower()
        assert "energy analyst" in text_lower
        assert "behavioral analyst" in text_lower
        assert "diagnostic analyst" in text_lower
