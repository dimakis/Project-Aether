"""A2A remote client for calling agent services (Phase 3).

Implements the same ``invoke(state) -> dict`` interface as ``BaseAgent``
but calls a remote A2A service over HTTP.  Used when
``DEPLOYMENT_MODE=distributed`` to route to agents running as
separate Kubernetes services.

The ``stream()`` method adds real-time SSE streaming via the A2A
``SendStreamingMessage`` endpoint, translating A2A events into
``StreamEvent`` dicts consumed by the gateway SSE handler.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx
from httpx_sse import aconnect_sse

from src.agents.a2a_service import pack_state_to_data, unpack_data_to_state_updates
from src.agents.a2a_streaming import translate_a2a_event

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from src.agents.streaming.events import StreamEvent
    from src.graph.state import BaseState

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0
_STREAM_TIMEOUT = 900.0


class A2AClientError(Exception):
    """Raised when the remote A2A service returns an error."""


class A2ARemoteClient:
    """Calls a remote A2A agent service with the same interface as BaseAgent.

    Usage::

        client = A2ARemoteClient("http://data-science:8000")
        result = await client.invoke(state)  # same dict as agent.invoke()

        async for event in client.stream(state):
            print(event)  # StreamEvent dicts
    """

    _ALLOWED_SCHEMES = {"http", "https"}

    def __init__(
        self,
        base_url: str,
        timeout: float = _DEFAULT_TIMEOUT,
        stream_timeout: float = _STREAM_TIMEOUT,
    ) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if parsed.scheme not in self._ALLOWED_SCHEMES:
            msg = f"Invalid URL scheme '{parsed.scheme}'. Only {self._ALLOWED_SCHEMES} allowed."
            raise ValueError(msg)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.stream_timeout = stream_timeout

    async def invoke(self, state: BaseState, **kwargs: Any) -> dict[str, Any]:
        """Pack state, send to the remote A2A service, unpack response.

        Args:
            state: Current graph state (Pydantic model).

        Returns:
            State update dict (same format as BaseAgent.invoke()).

        Raises:
            A2AClientError: On permanent failure after retries.
        """
        data = pack_state_to_data(state)
        return await self._send_message(data)

    async def stream(self, state: BaseState) -> AsyncGenerator[StreamEvent, None]:
        """Stream events from the remote A2A service via SSE.

        Sends a ``message/sendStream`` JSON-RPC request and consumes
        the SSE response, translating each A2A event into a
        ``StreamEvent`` via ``translate_a2a_event()``.
        """
        data = pack_state_to_data(state)
        payload = {
            "jsonrpc": "2.0",
            "method": "message/stream",
            "id": "stream-1",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "data", "data": data}],
                    "messageId": "stream-0",
                },
            },
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.stream_timeout, connect=10.0),
            ) as client:
                async with aconnect_sse(
                    client,
                    "POST",
                    f"{self.base_url}/",
                    json=payload,
                ) as event_source:
                    async for sse in event_source.aiter_sse():
                        if sse.data == "[DONE]":
                            return

                        try:
                            parsed = json.loads(sse.data)
                        except json.JSONDecodeError:
                            logger.warning("Unparseable SSE data: %s", sse.data[:200])
                            continue

                        event = _reconstruct_a2a_event(parsed)
                        if event is None:
                            continue

                        translated = translate_a2a_event(event)
                        if translated is not None:
                            yield translated

        except httpx.HTTPStatusError as e:
            raise A2AClientError(f"HTTP {e.response.status_code}: {e}") from e
        except httpx.TimeoutException as e:
            raise A2AClientError(f"Stream timeout after {self.stream_timeout}s: {e}") from e
        except A2AClientError:
            raise
        except Exception as e:
            raise A2AClientError(f"Unexpected streaming error: {e}") from e

    async def _send_message(self, data: dict[str, Any]) -> dict[str, Any]:
        """Send an A2A-style message to the remote service.

        Uses the JSON-RPC endpoint at the service root. Extracts
        the result DataPart from the response.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "id": "1",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "data", "data": data}],
                    "messageId": "invoke-0",
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/",
                    json=payload,
                )
                resp.raise_for_status()

            try:
                body = resp.json()
            except Exception as e:
                raise A2AClientError(f"Invalid JSON response: {e}") from e

            if "error" in body:
                raise A2AClientError(f"A2A error: {body['error']}")

            result = body.get("result", {})
            artifacts = result.get("artifacts", [])
            if artifacts:
                parts = artifacts[0].get("parts", [])
                for part in parts:
                    if part.get("kind") == "data" and "data" in part:
                        return unpack_data_to_state_updates(part["data"])

            return unpack_data_to_state_updates(result)

        except httpx.HTTPStatusError as e:
            raise A2AClientError(f"HTTP {e.response.status_code}: {e}") from e
        except httpx.TimeoutException as e:
            raise A2AClientError(f"Timeout after {self.timeout}s: {e}") from e
        except A2AClientError:
            raise
        except Exception as e:
            raise A2AClientError(f"Unexpected error: {e}") from e


def _reconstruct_a2a_event(data: dict[str, Any]) -> Any:
    """Reconstruct a typed A2A event from parsed SSE JSON.

    The A2A SDK serializes events as JSON with a ``kind`` discriminator.
    We reconstruct the typed objects so ``translate_a2a_event()`` can
    use isinstance checks.
    """
    from a2a.types import (
        Artifact,
        DataPart,
        Part,
        TaskArtifactUpdateEvent,
        TaskState,
        TaskStatus,
        TaskStatusUpdateEvent,
        TextPart,
    )

    kind = data.get("kind")

    if kind == "status-update":
        status_data = data.get("status", {})
        state_str = status_data.get("state", "unknown")
        try:
            state = TaskState(state_str)
        except ValueError:
            state = TaskState.unknown
        return TaskStatusUpdateEvent(
            task_id=data.get("taskId", data.get("task_id", "")),
            context_id=data.get("contextId", data.get("context_id", "")),
            final=data.get("final", False),
            kind="status-update",
            status=TaskStatus(state=state),
        )

    if kind == "artifact-update":
        artifact_data = data.get("artifact", {})
        parts = []
        for p in artifact_data.get("parts", []):
            p_kind = p.get("kind", "")
            if p_kind == "text":
                parts.append(Part(root=TextPart(text=p.get("text", ""))))
            elif p_kind == "data":
                parts.append(Part(root=DataPart(data=p.get("data", {}))))
        artifact = Artifact(
            artifact_id=artifact_data.get("artifactId", artifact_data.get("artifact_id", "a-0")),
            parts=parts,
        )
        return TaskArtifactUpdateEvent(
            task_id=data.get("taskId", data.get("task_id", "")),
            context_id=data.get("contextId", data.get("context_id", "")),
            artifact=artifact,
            kind="artifact-update",
        )

    # JSON-RPC result wrapper (non-streaming final response)
    if "result" in data:
        return _reconstruct_a2a_event(data["result"])

    return None
