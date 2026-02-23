"""A2A remote client for calling agent services (Phase 3).

Implements the same ``invoke(state) -> dict`` interface as ``BaseAgent``
but calls a remote A2A service over HTTP.  Used when
``DEPLOYMENT_MODE=distributed`` to route to agents running as
separate Kubernetes services.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from src.agents.a2a_service import pack_state_to_data, unpack_data_to_state_updates

if TYPE_CHECKING:
    from src.graph.state import BaseState

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0


class A2AClientError(Exception):
    """Raised when the remote A2A service returns an error."""


class A2ARemoteClient:
    """Calls a remote A2A agent service with the same interface as BaseAgent.

    Usage::

        client = A2ARemoteClient("http://data-science:8000")
        result = await client.invoke(state)  # same dict as agent.invoke()
    """

    _ALLOWED_SCHEMES = {"http", "https"}

    def __init__(
        self,
        base_url: str,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if parsed.scheme not in self._ALLOWED_SCHEMES:
            msg = f"Invalid URL scheme '{parsed.scheme}'. Only {self._ALLOWED_SCHEMES} allowed."
            raise ValueError(msg)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

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
