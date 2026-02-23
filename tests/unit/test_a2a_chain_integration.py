"""End-to-end integration test for the full A2A chain (Phase 4).

Verifies state propagates correctly through:
API -> Architect -> DS Orchestrator -> DS Analysts

Uses mocked HTTP responses (no real containers needed).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.a2a_client import A2ARemoteClient
from src.agents.a2a_service import pack_state_to_data, unpack_data_to_state_updates
from src.graph.state import AnalysisState, ConversationState


class TestFullChainStateRoundTrip:
    """State survives the full A2A chain."""

    def test_conversation_state_survives_pack_unpack(self):
        state = ConversationState(
            conversation_id="conv-chain-1",
            channel="api",
            active_agent="architect",
            messages=[
                HumanMessage(content="analyze my energy usage"),
                AIMessage(content="I'll run the DS team analysis"),
            ],
        )

        packed = pack_state_to_data(state)
        unpacked = unpack_data_to_state_updates(packed)

        assert unpacked["conversation_id"] == "conv-chain-1"
        assert unpacked["active_agent"] == "architect"

    def test_analysis_state_survives_pack_unpack(self):
        state = AnalysisState(run_id="run-chain-1")

        packed = pack_state_to_data(state)
        unpacked = unpack_data_to_state_updates(packed)

        assert unpacked["run_id"] == "run-chain-1"

    @pytest.mark.asyncio()
    async def test_remote_client_sends_packed_state(self):
        client = A2ARemoteClient(base_url="http://architect:8000")
        state = ConversationState(
            conversation_id="conv-e2e",
            messages=[HumanMessage(content="test")],
        )

        captured = {}

        async def mock_send(data):
            captured.update(data)
            return {"active_agent": "architect"}

        with patch.object(client, "_send_message", side_effect=mock_send):
            result = await client.invoke(state)

        assert captured["conversation_id"] == "conv-e2e"
        assert "_lc_messages" in captured
        assert result["active_agent"] == "architect"


class TestStreamingEventTranslation:
    """A2A events translate correctly to StreamEvents."""

    def test_full_event_sequence(self):
        from a2a.types import (
            Artifact,
            Part,
            TaskArtifactUpdateEvent,
            TaskState,
            TaskStatus,
            TaskStatusUpdateEvent,
            TextPart,
        )

        from src.agents.a2a_streaming import translate_a2a_event

        events = [
            TaskStatusUpdateEvent(
                task_id="t1",
                context_id="c1",
                final=False,
                status=TaskStatus(state=TaskState.working),
            ),
            TaskArtifactUpdateEvent(
                task_id="t1",
                context_id="c1",
                artifact=Artifact(
                    artifact_id="a1",
                    parts=[Part(root=TextPart(text="Analyzing..."))],
                ),
            ),
            TaskStatusUpdateEvent(
                task_id="t1",
                context_id="c1",
                final=True,
                status=TaskStatus(state=TaskState.completed),
            ),
        ]

        results = [translate_a2a_event(e) for e in events]

        assert results[0]["type"] == "status"
        assert results[1]["type"] == "token"
        assert results[1]["content"] == "Analyzing..."
        assert results[2]["type"] == "state"


class TestDualModeChainResolution:
    """resolve_agent_invoker maps the full chain correctly."""

    def test_architect_resolves_to_architect_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            mock_s.return_value.architect_service_url = "http://architect:8000"
            invoker = resolve_agent_invoker("architect")

        assert invoker.mode == "remote"
        assert invoker.service_url == "http://architect:8000"

    def test_data_scientist_resolves_to_orchestrator_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            mock_s.return_value.ds_orchestrator_url = "http://ds-orchestrator:8000"
            invoker = resolve_agent_invoker("data_scientist")

        assert invoker.mode == "remote"
        assert invoker.service_url == "http://ds-orchestrator:8000"

    def test_energy_analyst_resolves_to_analysts_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            mock_s.return_value.ds_analysts_url = "http://ds-analysts:8000"
            invoker = resolve_agent_invoker("energy_analyst")

        assert invoker.mode == "remote"
        assert invoker.service_url == "http://ds-analysts:8000"

    def test_developer_resolves_to_developer_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            mock_s.return_value.developer_service_url = "http://developer:8000"
            invoker = resolve_agent_invoker("developer")

        assert invoker.mode == "remote"
        assert invoker.service_url == "http://developer:8000"

    def test_librarian_resolves_to_librarian_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            mock_s.return_value.librarian_service_url = "http://librarian:8000"
            invoker = resolve_agent_invoker("librarian")

        assert invoker.mode == "remote"
        assert invoker.service_url == "http://librarian:8000"

    def test_dashboard_designer_resolves_to_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            mock_s.return_value.dashboard_designer_service_url = "http://dashboard-designer:8000"
            invoker = resolve_agent_invoker("dashboard_designer")

        assert invoker.mode == "remote"
        assert invoker.service_url == "http://dashboard-designer:8000"

    def test_orchestrator_resolves_to_orchestrator_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "distributed"
            mock_s.return_value.orchestrator_service_url = "http://orchestrator-agent:8000"
            invoker = resolve_agent_invoker("orchestrator")

        assert invoker.mode == "remote"
        assert invoker.service_url == "http://orchestrator-agent:8000"

    def test_monolith_mode_all_local(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_s:
            mock_s.return_value.deployment_mode = "monolith"

            all_agents = [
                "architect",
                "developer",
                "librarian",
                "dashboard_designer",
                "orchestrator",
                "data_scientist",
                "energy_analyst",
            ]
            for name in all_agents:
                invoker = resolve_agent_invoker(name)
                assert invoker.mode == "local", f"{name} should be local in monolith"
