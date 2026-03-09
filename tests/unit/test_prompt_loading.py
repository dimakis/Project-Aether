"""Unit tests for src/agents/prompts/__init__.py — load_prompt_for_agent."""

import pytest

from src.agents.prompts import load_prompt_for_agent


class TestLoadPromptForAgent:
    def test_db_prompt_takes_priority(self):
        result = load_prompt_for_agent("architect", db_prompt="Use this DB prompt.")
        assert result == "Use this DB prompt."

    def test_db_prompt_with_kwargs_formatting(self):
        result = load_prompt_for_agent(
            "architect",
            db_prompt="Hello {name}, you are {role}.",
            name="Aether",
            role="architect",
        )
        assert result == "Hello Aether, you are architect."

    def test_raises_when_no_prompt_found(self):
        with pytest.raises(FileNotFoundError, match="No prompt template found"):
            load_prompt_for_agent("nonexistent_agent_xyz_99")
