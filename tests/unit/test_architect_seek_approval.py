"""Unit tests for architect's seek_approval integration.

Verifies the architect system prompt instructs use of seek_approval
for all mutating actions, and that the tool is available.
"""

import pytest


class TestArchitectSeekApprovalPrompt:
    """Tests that the architect system prompt directs seek_approval usage."""

    def test_system_prompt_mentions_seek_approval(self):
        """The system prompt instructs the architect to use seek_approval."""
        from src.agents.architect import ARCHITECT_SYSTEM_PROMPT

        assert "seek_approval" in ARCHITECT_SYSTEM_PROMPT

    def test_system_prompt_forbids_control_entity(self):
        """The system prompt tells the architect NOT to use control_entity directly."""
        from src.agents.architect import ARCHITECT_SYSTEM_PROMPT

        assert "NEVER call `control_entity`" in ARCHITECT_SYSTEM_PROMPT

    def test_system_prompt_forbids_deploy_automation(self):
        """The system prompt tells the architect NOT to use deploy_automation directly."""
        from src.agents.architect import ARCHITECT_SYSTEM_PROMPT

        assert "NEVER call" in ARCHITECT_SYSTEM_PROMPT
        assert "deploy_automation" in ARCHITECT_SYSTEM_PROMPT

    def test_system_prompt_covers_all_action_types(self):
        """The system prompt documents all four action types."""
        from src.agents.architect import ARCHITECT_SYSTEM_PROMPT

        assert "entity_command" in ARCHITECT_SYSTEM_PROMPT
        assert "automation" in ARCHITECT_SYSTEM_PROMPT
        assert '"script"' in ARCHITECT_SYSTEM_PROMPT or "Scripts" in ARCHITECT_SYSTEM_PROMPT
        assert '"scene"' in ARCHITECT_SYSTEM_PROMPT or "Scenes" in ARCHITECT_SYSTEM_PROMPT

    def test_seek_approval_in_tool_registry(self):
        """seek_approval is registered in get_all_tools()."""
        from src.tools import get_all_tools

        tools = get_all_tools()
        tool_names = [t.name for t in tools]
        assert "seek_approval" in tool_names

    def test_control_entity_still_available_but_deprioritized(self):
        """control_entity is still in the tool registry (backward compat)."""
        from src.tools import get_all_tools

        tools = get_all_tools()
        tool_names = [t.name for t in tools]
        # control_entity remains available but prompt directs to seek_approval
        assert "control_entity" in tool_names

    def test_system_prompt_mentions_proposals_page(self):
        """The system prompt tells the architect to direct users to Proposals page."""
        from src.agents.architect import ARCHITECT_SYSTEM_PROMPT

        assert "Proposals" in ARCHITECT_SYSTEM_PROMPT
        assert "review" in ARCHITECT_SYSTEM_PROMPT.lower()
        assert "approve" in ARCHITECT_SYSTEM_PROMPT.lower()
