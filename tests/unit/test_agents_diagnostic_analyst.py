"""Unit tests for src/agents/diagnostic_analyst.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestDiagnosticAnalystExtractFindings:
    @pytest.fixture
    def analyst(self):
        from src.agents.diagnostic_analyst import DiagnosticAnalyst

        with patch("src.agents.diagnostic_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                return DiagnosticAnalyst()

    def test_empty_on_failure(self, analyst):
        result = MagicMock()
        result.success = False
        state = MagicMock()
        assert analyst.extract_findings(result, state) == []

    def test_empty_on_no_stdout(self, analyst):
        result = MagicMock()
        result.success = True
        result.stdout = ""
        state = MagicMock()
        assert analyst.extract_findings(result, state) == []

    def test_parses_findings(self, analyst):
        output = json.dumps(
            {
                "insights": [
                    {
                        "title": "Sensor offline",
                        "description": "Temperature sensor has been unavailable",
                        "confidence": 0.9,
                        "entities": ["sensor.temp"],
                        "type": "concern",
                    }
                ]
            }
        )
        result = MagicMock()
        result.success = True
        result.stdout = output
        state = MagicMock()
        state.entity_ids = ["sensor.temp"]
        findings = analyst.extract_findings(result, state)
        assert len(findings) == 1
        assert findings[0].specialist == "diagnostic_analyst"

    def test_invalid_json(self, analyst):
        result = MagicMock()
        result.success = True
        result.stdout = "not json"
        state = MagicMock()
        assert analyst.extract_findings(result, state) == []


class TestDiagnosticAnalystExtractCode:
    @pytest.fixture
    def analyst(self):
        from src.agents.diagnostic_analyst import DiagnosticAnalyst

        with patch("src.agents.diagnostic_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                return DiagnosticAnalyst()

    def test_python_block(self, analyst):
        r = analyst._extract_code_from_response("```python\ncode\n```")
        assert r == "code"

    def test_generic_block(self, analyst):
        r = analyst._extract_code_from_response("```\ncode\n```")
        assert r == "code"

    def test_no_block(self, analyst):
        r = analyst._extract_code_from_response("just code")
        assert r == "just code"


class TestDiagnosticAnalystBuildPrompt:
    @pytest.fixture
    def analyst(self):
        from src.agents.diagnostic_analyst import DiagnosticAnalyst

        with patch("src.agents.diagnostic_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                return DiagnosticAnalyst()

    def test_basic_prompt(self, analyst):
        from src.graph.state import AnalysisType

        state = MagicMock()
        state.analysis_type = AnalysisType.DIAGNOSTIC
        state.time_range_hours = 48
        state.diagnostic_context = None
        data = {"unavailable_entities": ["sensor.a"], "unhealthy_integrations": []}
        prompt = analyst._build_analysis_prompt(state, data)
        assert "48 hours" in prompt
        assert "Unavailable entities: 1" in prompt

    def test_with_diagnostic_context(self, analyst):
        from src.graph.state import AnalysisType

        state = MagicMock()
        state.analysis_type = AnalysisType.DIAGNOSTIC
        state.time_range_hours = 24
        state.diagnostic_context = "Check zigbee network"
        data = {}
        prompt = analyst._build_analysis_prompt(state, data)
        assert "zigbee network" in prompt

    def test_with_prior_findings(self, analyst):
        from src.graph.state import AnalysisType

        state = MagicMock()
        state.analysis_type = AnalysisType.DIAGNOSTIC
        state.time_range_hours = 24
        state.diagnostic_context = None
        data = {
            "prior_specialist_findings": [
                {"specialist": "energy", "title": "High usage", "description": "Details"}
            ]
        }
        prompt = analyst._build_analysis_prompt(state, data)
        assert "Prior findings" in prompt
