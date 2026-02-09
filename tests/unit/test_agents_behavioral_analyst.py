"""Unit tests for src/agents/behavioral_analyst.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import AnalysisType


class TestBehavioralAnalystInit:
    def test_behavioral_types_defined(self):
        from src.agents.behavioral_analyst import BEHAVIORAL_TYPES

        assert AnalysisType.BEHAVIOR_ANALYSIS in BEHAVIORAL_TYPES
        assert AnalysisType.AUTOMATION_ANALYSIS in BEHAVIORAL_TYPES


class TestExtractFindings:
    @pytest.fixture
    def analyst(self):
        from src.agents.behavioral_analyst import BehavioralAnalyst

        with patch("src.agents.behavioral_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                return BehavioralAnalyst()

    def test_empty_on_failure(self, analyst):
        result = MagicMock()
        result.success = False
        result.stdout = ""
        state = MagicMock()
        findings = analyst.extract_findings(result, state)
        assert findings == []

    def test_empty_on_no_stdout(self, analyst):
        result = MagicMock()
        result.success = True
        result.stdout = ""
        state = MagicMock()
        findings = analyst.extract_findings(result, state)
        assert findings == []

    def test_parses_json_insights(self, analyst):
        output = json.dumps(
            {
                "insights": [
                    {
                        "title": "High manual usage",
                        "description": "Users manually toggle lights 20x/day",
                        "confidence": 0.8,
                        "entities": ["light.kitchen"],
                        "type": "insight",
                    }
                ]
            }
        )
        result = MagicMock()
        result.success = True
        result.stdout = output
        state = MagicMock()
        findings = analyst.extract_findings(result, state)
        assert len(findings) == 1
        assert findings[0].title == "High manual usage"
        assert findings[0].confidence == 0.8

    def test_invalid_json(self, analyst):
        result = MagicMock()
        result.success = True
        result.stdout = "not json at all"
        state = MagicMock()
        findings = analyst.extract_findings(result, state)
        assert findings == []

    def test_clamps_confidence(self, analyst):
        output = json.dumps(
            {
                "insights": [
                    {"title": "Test", "description": "D", "confidence": 2.0},
                    {"title": "Test2", "description": "D", "confidence": -1.0},
                ]
            }
        )
        result = MagicMock()
        result.success = True
        result.stdout = output
        state = MagicMock()
        findings = analyst.extract_findings(result, state)
        assert findings[0].confidence == 1.0
        assert findings[1].confidence == 0.0


class TestExtractCodeFromResponse:
    @pytest.fixture
    def analyst(self):
        from src.agents.behavioral_analyst import BehavioralAnalyst

        with patch("src.agents.behavioral_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                return BehavioralAnalyst()

    def test_python_code_block(self, analyst):
        response = "Here's the code:\n```python\nprint('hello')\n```\nDone"
        result = analyst._extract_code_from_response(response)
        assert result == "print('hello')"

    def test_generic_code_block(self, analyst):
        response = "Code:\n```\nprint('hello')\n```"
        result = analyst._extract_code_from_response(response)
        assert result == "print('hello')"

    def test_no_code_block(self, analyst):
        response = "print('hello')"
        result = analyst._extract_code_from_response(response)
        assert result == "print('hello')"


class TestBuildAnalysisPrompt:
    @pytest.fixture
    def analyst(self):
        from src.agents.behavioral_analyst import BehavioralAnalyst

        with patch("src.agents.behavioral_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                return BehavioralAnalyst()

    def test_basic_prompt(self, analyst):
        state = MagicMock()
        state.analysis_type = AnalysisType.BEHAVIOR_ANALYSIS
        state.time_range_hours = 24
        data = {"entity_count": 10}
        prompt = analyst._build_analysis_prompt(state, data)
        assert "10 entities" in prompt
        assert "24 hours" in prompt

    def test_with_prior_findings(self, analyst):
        state = MagicMock()
        state.analysis_type = AnalysisType.BEHAVIOR_ANALYSIS
        state.time_range_hours = 24
        data = {
            "entity_count": 5,
            "prior_specialist_findings": [
                {
                    "specialist": "energy",
                    "title": "High usage",
                    "description": "Kitchen uses too much power",
                }
            ],
        }
        prompt = analyst._build_analysis_prompt(state, data)
        assert "Prior findings" in prompt
        assert "energy" in prompt


class TestCollectScriptSceneUsage:
    async def test_collects_stats(self):
        from src.agents.behavioral_analyst import BehavioralAnalyst

        with patch("src.agents.behavioral_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                analyst = BehavioralAnalyst()

        mock_stats = MagicMock()
        mock_stats.by_domain = {"script": 10, "scene": 5}
        mock_stats.automation_triggers = 20
        mock_stats.manual_actions = 15

        mock_behavioral = MagicMock()
        mock_behavioral._logbook = MagicMock()
        mock_behavioral._logbook.get_stats = AsyncMock(return_value=mock_stats)

        result = await analyst._collect_script_scene_usage(mock_behavioral, 24)
        assert result["script_calls"] == 10
        assert result["scene_calls"] == 5

    async def test_handles_error(self):
        from src.agents.behavioral_analyst import BehavioralAnalyst

        with patch("src.agents.behavioral_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                analyst = BehavioralAnalyst()

        mock_behavioral = MagicMock()
        mock_behavioral._logbook = MagicMock()
        mock_behavioral._logbook.get_stats = AsyncMock(side_effect=Exception("fail"))

        result = await analyst._collect_script_scene_usage(mock_behavioral, 24)
        assert result == {}


class TestCollectTriggerSourceBreakdown:
    async def test_collects_breakdown(self):
        from src.agents.behavioral_analyst import BehavioralAnalyst

        with patch("src.agents.behavioral_analyst.load_prompt", return_value="prompt"):
            with patch("src.llm.get_llm", return_value=MagicMock()):
                analyst = BehavioralAnalyst()

        mock_stats = MagicMock()
        mock_stats.automation_triggers = 30
        mock_stats.manual_actions = 10

        mock_behavioral = MagicMock()
        mock_behavioral._logbook = MagicMock()
        mock_behavioral._logbook.get_stats = AsyncMock(return_value=mock_stats)

        result = await analyst._collect_trigger_source_breakdown(mock_behavioral, 24)
        assert result["automation_triggers"] == 30
        assert result["human_triggers"] == 10
        assert result["automation_ratio"] == 0.75
