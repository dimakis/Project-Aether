"""Unit tests for HA gaps module.

Tests gap analysis and reporting functions.
"""

from src.ha.gaps import (
    MCP_GAPS,
    get_all_gaps,
    get_gap_by_tool,
    get_gaps_affecting_entity,
    get_gaps_by_priority,
    get_gaps_report,
    log_gap_encounter,
)


class TestGetAllGaps:
    """Tests for get_all_gaps."""

    def test_get_all_gaps_returns_list(self):
        """Test that get_all_gaps returns a list."""
        result = get_all_gaps()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_all_gaps_contains_expected_gaps(self):
        """Test that known gaps are present."""
        result = get_all_gaps()
        gap_tools = [gap["tool"] for gap in result]
        assert "list_devices" in gap_tools
        assert "list_areas" in gap_tools
        assert "create_automation" in gap_tools

    def test_gap_structure(self):
        """Test that gaps have expected structure."""
        result = get_all_gaps()
        for gap in result:
            assert "tool" in gap
            assert "priority" in gap
            assert "impact" in gap
            assert "workaround" in gap
            assert isinstance(gap["tool"], str)
            assert gap["priority"] in ["P1", "P2", "P3"]


class TestGetGapsByPriority:
    """Tests for get_gaps_by_priority."""

    def test_get_p1_gaps(self):
        """Test getting P1 priority gaps."""
        result = get_gaps_by_priority("P1")
        assert isinstance(result, list)
        for gap in result:
            assert gap["priority"] == "P1"

    def test_get_p2_gaps(self):
        """Test getting P2 priority gaps."""
        result = get_gaps_by_priority("P2")
        assert isinstance(result, list)
        for gap in result:
            assert gap["priority"] == "P2"

    def test_get_p3_gaps(self):
        """Test getting P3 priority gaps."""
        result = get_gaps_by_priority("P3")
        assert isinstance(result, list)
        for gap in result:
            assert gap["priority"] == "P3"

    def test_get_invalid_priority(self):
        """Test getting gaps with invalid priority."""
        result = get_gaps_by_priority("P4")
        assert isinstance(result, list)
        assert len(result) == 0


class TestGetGapByTool:
    """Tests for get_gap_by_tool."""

    def test_get_existing_gap(self):
        """Test getting an existing gap."""
        result = get_gap_by_tool("list_devices")
        assert result is not None
        assert result["tool"] == "list_devices"
        assert result["priority"] == "P1"

    def test_get_nonexistent_gap(self):
        """Test getting a non-existent gap."""
        result = get_gap_by_tool("nonexistent_tool")
        assert result is None

    def test_get_gap_with_all_fields(self):
        """Test that gap contains all expected fields."""
        result = get_gap_by_tool("list_devices")
        assert result is not None
        assert "tool" in result
        assert "priority" in result
        assert "impact" in result
        assert "workaround" in result
        assert "affects" in result
        assert "data_model_impact" in result


class TestGetGapsReport:
    """Tests for get_gaps_report."""

    def test_get_gaps_report_structure(self):
        """Test that report has expected structure."""
        result = get_gaps_report()
        assert isinstance(result, dict)
        assert "total_gaps" in result
        assert "priority_counts" in result
        assert "high_priority_tools" in result
        assert "medium_priority_tools" in result
        assert "low_priority_tools" in result

    def test_get_gaps_report_counts(self):
        """Test that report counts are correct."""
        result = get_gaps_report()
        assert result["total_gaps"] == len(MCP_GAPS)
        assert isinstance(result["priority_counts"], dict)
        assert "P1" in result["priority_counts"]
        assert "P2" in result["priority_counts"]
        assert "P3" in result["priority_counts"]

    def test_get_gaps_report_tool_lists(self):
        """Test that tool lists are populated."""
        result = get_gaps_report()
        assert isinstance(result["high_priority_tools"], list)
        assert isinstance(result["medium_priority_tools"], list)
        assert isinstance(result["low_priority_tools"], list)

        # Verify tools match their priorities
        all_p1 = get_gaps_by_priority("P1")
        assert len(result["high_priority_tools"]) == len(all_p1)

    def test_get_gaps_report_priority_counts_sum(self):
        """Test that priority counts sum to total."""
        result = get_gaps_report()
        total_from_counts = sum(result["priority_counts"].values())
        assert total_from_counts == result["total_gaps"]


class TestLogGapEncounter:
    """Tests for log_gap_encounter."""

    def test_log_existing_gap(self):
        """Test logging an existing gap."""
        result = log_gap_encounter("list_devices", "Testing device listing")
        assert result is not None
        assert "gap" in result
        assert "context" in result
        assert "workaround_applied" in result
        assert result["gap"]["tool"] == "list_devices"
        assert result["context"] == "Testing device listing"
        assert result["workaround_applied"] is not None

    def test_log_nonexistent_gap(self):
        """Test logging a non-existent gap."""
        result = log_gap_encounter("nonexistent_tool", "Testing")
        assert result is None

    def test_log_gap_without_context(self):
        """Test logging a gap without context."""
        result = log_gap_encounter("list_areas")
        assert result is not None
        assert result["context"] is None

    def test_log_gap_structure(self):
        """Test that logged gap has expected structure."""
        result = log_gap_encounter("list_devices", "Test context")
        assert result is not None
        assert isinstance(result["gap"], dict)
        assert "tool" in result["gap"]
        assert "priority" in result["gap"]
        assert "workaround" in result["gap"]


class TestGetGapsAffectingEntity:
    """Tests for get_gaps_affecting_entity."""

    def test_get_gaps_affecting_device(self):
        """Test getting gaps affecting Device entity."""
        result = get_gaps_affecting_entity("Device")
        assert isinstance(result, list)
        # Should find gaps that mention Device in data_model_impact
        device_mentioned = any(
            "Device" in str(gap.get("data_model_impact", [])) for gap in MCP_GAPS
        )
        if device_mentioned:
            assert len(result) > 0

    def test_get_gaps_affecting_area(self):
        """Test getting gaps affecting Area entity."""
        result = get_gaps_affecting_entity("Area")
        assert isinstance(result, list)
        # Should find gaps that mention Area in data_model_impact
        area_mentioned = any("Area" in str(gap.get("data_model_impact", [])) for gap in MCP_GAPS)
        if area_mentioned:
            assert len(result) > 0

    def test_get_gaps_affecting_nonexistent_entity(self):
        """Test getting gaps for non-existent entity."""
        result = get_gaps_affecting_entity("NonExistentEntity")
        assert isinstance(result, list)
        # May or may not have results depending on data_model_impact

    def test_get_gaps_affecting_case_insensitive(self):
        """Test that entity matching is case-insensitive."""
        result_lower = get_gaps_affecting_entity("device")
        result_upper = get_gaps_affecting_entity("Device")
        # Should return same results (case-insensitive matching)
        assert len(result_lower) == len(result_upper)

    def test_get_gaps_affecting_entity_structure(self):
        """Test that returned gaps have expected structure."""
        result = get_gaps_affecting_entity("Device")
        for gap in result:
            assert "tool" in gap
            assert "priority" in gap
            assert "data_model_impact" in gap


class TestMCPGapsConstant:
    """Tests for MCP_GAPS constant."""

    def test_mcp_gaps_is_list(self):
        """Test that MCP_GAPS is a list."""
        assert isinstance(MCP_GAPS, list)

    def test_mcp_gaps_not_empty(self):
        """Test that MCP_GAPS is not empty."""
        assert len(MCP_GAPS) > 0

    def test_mcp_gaps_immutability(self):
        """Test that MCP_GAPS structure is consistent."""
        # Verify all gaps have required fields
        for gap in MCP_GAPS:
            assert isinstance(gap, dict)
            assert "tool" in gap
            assert "priority" in gap
            assert isinstance(gap["tool"], str)
            assert gap["priority"] in ["P1", "P2", "P3"]

    def test_mcp_gaps_unique_tools(self):
        """Test that tool names are unique."""
        tools = [gap["tool"] for gap in MCP_GAPS]
        assert len(tools) == len(set(tools)), "Duplicate tool names found in MCP_GAPS"
