"""Shared fixtures for streaming module tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage


@pytest.fixture()
def mock_agent():
    """Create a mock ArchitectAgent with standard defaults."""
    agent = MagicMock()
    agent.name = "Architect"
    agent.role = MagicMock()
    agent.role.value = "architect"
    agent.llm = MagicMock()
    agent._get_ha_tools.return_value = []
    agent._build_messages.return_value = [HumanMessage(content="test")]
    agent._is_mutating_tool.return_value = False
    agent._get_entity_context = AsyncMock(return_value=None)
    agent._extract_proposals.return_value = []
    return agent


def make_tool_call_chunk(name: str, args_str: str, call_id: str, index: int = 0) -> AIMessageChunk:
    """Create a mock AIMessageChunk with a tool call chunk."""
    chunk = AIMessageChunk(content="")
    chunk.tool_call_chunks = [{"name": name, "args": args_str, "id": call_id, "index": index}]
    return chunk


async def async_iter(items):
    """Convert a list to an async iterator."""
    for item in items:
        yield item
