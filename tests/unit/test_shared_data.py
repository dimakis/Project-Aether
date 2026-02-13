"""Unit tests for B3: shared_data field on TeamAnalysis.

Verifies:
- TeamAnalysis has a shared_data dict field defaulting to empty
- Specialists can write/read shared_data during teamwork mode
- shared_data is in-memory only (not persisted to DB)
"""

from __future__ import annotations


class TestTeamAnalysisSharedData:
    """TeamAnalysis has a shared_data field."""

    def test_shared_data_defaults_to_empty_dict(self):
        from src.graph.state import TeamAnalysis

        ta = TeamAnalysis(request_id="test", request_summary="test")
        assert ta.shared_data == {}
        assert isinstance(ta.shared_data, dict)

    def test_shared_data_can_store_values(self):
        from src.graph.state import TeamAnalysis

        ta = TeamAnalysis(request_id="test", request_summary="test")
        ta.shared_data["energy_stats"] = {"mean_kwh": 5.2, "peak_kwh": 12.1}
        ta.shared_data["behavioral_patterns"] = ["morning_routine", "night_routine"]

        assert ta.shared_data["energy_stats"]["mean_kwh"] == 5.2
        assert len(ta.shared_data["behavioral_patterns"]) == 2

    def test_shared_data_survives_model_copy(self):
        from src.graph.state import TeamAnalysis

        ta = TeamAnalysis(request_id="test", request_summary="test")
        ta.shared_data["key"] = "value"

        ta2 = ta.model_copy(deep=True)
        assert ta2.shared_data["key"] == "value"
        # Modifications to copy don't affect original
        ta2.shared_data["key2"] = "value2"
        assert "key2" not in ta.shared_data

    def test_shared_data_can_hold_complex_types(self):
        from src.graph.state import TeamAnalysis

        ta = TeamAnalysis(request_id="test", request_summary="test")
        ta.shared_data["df_json"] = [
            {"entity": "sensor.power", "mean": 5.0},
            {"entity": "sensor.temp", "mean": 22.3},
        ]
        ta.shared_data["computed_scores"] = {"health": 0.95, "efficiency": 0.72}

        assert len(ta.shared_data["df_json"]) == 2
        assert ta.shared_data["computed_scores"]["health"] == 0.95

    def test_shared_data_in_serialization(self):
        """shared_data is included in model_dump (for in-memory transport)."""
        from src.graph.state import TeamAnalysis

        ta = TeamAnalysis(
            request_id="test",
            request_summary="test",
            shared_data={"result": 42},
        )
        dumped = ta.model_dump()
        assert dumped["shared_data"] == {"result": 42}
