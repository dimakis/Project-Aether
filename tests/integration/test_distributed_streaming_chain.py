"""Integration test for distributed streaming through the A2A chain.

This verifies token-by-token SSE behavior across:
OpenAI handler -> A2ARemoteClient.stream() -> A2A service executor.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import HumanMessage
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter
from src.api.routes.openai_compat import router
from src.graph.state import ConversationState


def _make_openai_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    return app


class _StreamingArchitectAgent:
    """Minimal streaming agent for the A2A integration path."""

    async def stream_conversation(self, *, state: Any, user_message: str) -> Any:
        # Yield separate token events to validate incremental streaming.
        yield {"type": "token", "content": "Hello "}
        yield {"type": "tool_start", "tool": "get_entities", "agent": "architect"}
        yield {"type": "status", "content": "Querying entities..."}
        yield {
            "type": "tool_end",
            "tool": "get_entities",
            "agent": "architect",
            "result": "Found 2 lights",
        }
        yield {"type": "token", "content": "world"}
        yield {
            "type": "state",
            "state": ConversationState(
                conversation_id=state.conversation_id,
                messages=[HumanMessage(content=user_message)],
            ),
        }

    async def invoke(self, state: Any) -> dict[str, Any]:
        return {"ok": True}


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_distributed_streaming_tokens_flow_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Any,
) -> None:
    from src.agents.a2a_service import create_a2a_service

    openai_app = _make_openai_test_app()
    remote_a2a_app = create_a2a_service(
        agent_name="architect",
        agent_description="test architect",
        agent_skills=[],
        agent=cast("Any", _StreamingArchitectAgent()),
    )

    distributed_settings = test_settings.model_copy(
        update={
            "deployment_mode": "distributed",
            "architect_service_url": "http://architect.test",
        }
    )
    monkeypatch.setattr("src.settings.get_settings", lambda: distributed_settings)

    @asynccontextmanager
    async def _mock_get_session() -> Any:
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    monkeypatch.setattr(
        "src.api.routes.openai_compat.handlers.get_session",
        lambda: _mock_get_session(),
    )

    class _A2AAsyncClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["transport"] = ASGITransport(app=remote_a2a_app)
            kwargs["base_url"] = "http://architect.test"
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("src.agents.a2a_client.httpx.AsyncClient", _A2AAsyncClient)

    async with AsyncClient(
        transport=ASGITransport(app=openai_app),
        base_url="http://test",
    ) as client:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "architect",
                "messages": [{"role": "user", "content": "Say hello"}],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200

            token_contents: list[str] = []
            status_contents: list[str] = []
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                payload = line.removeprefix("data: ")
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                if obj.get("object") == "chat.completion.chunk":
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        token_contents.append(content)
                elif obj.get("type") == "status":
                    content = obj.get("content")
                    if isinstance(content, str):
                        status_contents.append(content)

            assert token_contents == ["Hello ", "world"]
            assert "Running get_entities..." in status_contents
            assert "Querying entities..." in status_contents
