"""Analysis prompt building for Data Scientist agent."""

from typing import Any

from src.agents.prompts import load_depth_fragment, load_prompt
from src.graph.state import AnalysisState, AnalysisType


def build_analysis_prompt(
    state: AnalysisState,
    energy_data: dict[str, Any],
) -> str:
    """Build the analysis prompt based on type.

    Args:
        state: Analysis state
        energy_data: Energy data summary

    Returns:
        Prompt for script generation
    """
    entity_count = energy_data.get("entity_count", 0)
    total_kwh = energy_data.get("total_kwh", 0.0)
    hours = state.time_range_hours

    # Energy-specific context (only for energy/anomaly/usage/cost analysis)
    energy_context = f"""
I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh:.2f} kWh

Data structure (available in /workspace/data.json):
- entities: List of entity data with data_points, stats, etc.
- total_kwh: Total consumption
- hours: Analysis period
"""

    if state.analysis_type == AnalysisType.ENERGY_OPTIMIZATION:
        prompt = load_prompt(
            "data_scientist_energy",
            entity_count=str(entity_count),
            hours=str(hours),
            total_kwh=f"{total_kwh:.2f}",
        )

    elif state.analysis_type == AnalysisType.DIAGNOSTIC:
        instructions = state.custom_query or "Perform a general diagnostic analysis"
        diagnostic_ctx = state.diagnostic_context or "No additional diagnostic context provided."

        prompt = load_prompt(
            "data_scientist_diagnostic",
            entity_count=str(entity_count),
            hours=str(hours),
            total_kwh=f"{total_kwh:.2f}",
            diagnostic_context=diagnostic_ctx,
            instructions=instructions,
        )

    elif state.analysis_type == AnalysisType.ANOMALY_DETECTION:
        prompt = f"""
I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh:.2f} kWh

Data structure (available in /workspace/data.json):
- entities: List of entity data with data_points, stats, etc.
- total_kwh: Total consumption
- hours: Analysis period

Please analyze this energy data and generate a Python script that:
1. Establishes baseline consumption patterns
2. Detects anomalies using statistical methods (z-score, IQR)
3. Identifies unusual spikes or drops
4. Flags entities with abnormal behavior

Output insights as JSON to stdout with type="anomaly_detection".
"""

    elif state.analysis_type == AnalysisType.USAGE_PATTERNS:
        prompt = f"""
I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh:.2f} kWh

Data structure (available in /workspace/data.json):
- entities: List of entity data with data_points, stats, etc.
- total_kwh: Total consumption
- hours: Analysis period

Please analyze this energy data and generate a Python script that:
1. Identifies daily usage patterns (morning, afternoon, evening, night)
2. Compares weekday vs weekend consumption
3. Detects recurring patterns
4. Suggests optimal automation schedules

Output insights as JSON to stdout with type="usage_pattern".
"""

    elif state.analysis_type == AnalysisType.BEHAVIOR_ANALYSIS:
        prompt = f"""
I have behavioral data from {entity_count} entities over the past {hours} hours.

Data structure (available in /workspace/data.json):
- button_usage: List of entity button/switch press data with totals and hourly breakdown
- entities: Flattened entity list for iteration
- entity_count: Number of entities with data
- hours: Analysis period

Please analyze this behavioral data and generate a Python script that:
1. Identifies the most frequently manually controlled entities
2. Detects peak usage hours for manual interactions
3. Finds patterns in button/switch press timing
4. Suggests which manual actions could benefit from automation

Output insights as JSON to stdout with type="behavioral_pattern".
"""

    elif state.analysis_type == AnalysisType.AUTOMATION_ANALYSIS:
        prompt = f"""
I have automation effectiveness data for {entity_count} automations over the past {hours} hours.

Data structure (available in /workspace/data.json):
- automation_effectiveness: List of automation records with trigger_count, manual_overrides, efficiency_score
- entities: Flattened entity list for iteration
- entity_count: Number of automations analyzed
- hours: Analysis period

Please analyze this automation effectiveness data and generate a Python script that:
1. Ranks automations by effectiveness (trigger count vs manual overrides)
2. Identifies automations with high manual override rates
3. Suggests improvements for inefficient automations
4. Calculates overall automation coverage

Output insights as JSON to stdout with type="automation_inefficiency" for issues
and type="behavioral_pattern" for positive findings.
"""

    elif state.analysis_type == AnalysisType.AUTOMATION_GAP_DETECTION:
        prompt = f"""
I have automation gap data with {entity_count} detected patterns over the past {hours} hours.

Data structure (available in /workspace/data.json):
- automation_gaps: List of gap records with description, entities, occurrences, typical_time, confidence
- entities: Flattened entity list for iteration
- entity_count: Number of gaps detected
- hours: Analysis period

Please analyze this automation gap data and generate a Python script that:
1. Identifies the strongest repeating manual patterns
2. Ranks gaps by frequency and confidence
3. Generates specific automation trigger/action suggestions for each gap
4. Estimates effort saved if each gap were automated

Output insights as JSON to stdout with type="automation_gap".
Include proposed_trigger and proposed_action in the evidence for each insight.
"""

    elif state.analysis_type == AnalysisType.CORRELATION_DISCOVERY:
        prompt = f"""
I have entity correlation data with {entity_count} correlated pairs over the past {hours} hours.

Data structure (available in /workspace/data.json):
- correlations: List of correlation records with entity_a, entity_b, co_occurrences, avg_delta_seconds, confidence
- entities: Flattened entity list for iteration
- entity_count: Number of correlated pairs found
- hours: Analysis period

Please analyze this entity correlation data and generate a Python script that:
1. Identifies the strongest entity correlations (devices used together)
2. Visualizes correlation patterns (timing, frequency)
3. Suggests automation groups based on correlated entities
4. Detects unexpected correlations that may indicate issues

Output insights as JSON to stdout with type="correlation".
"""

    elif state.analysis_type == AnalysisType.DEVICE_HEALTH:
        prompt = f"""
I have device health data for {entity_count} devices over the past {hours} hours.

Data structure (available in /workspace/data.json):
- device_health: List of device records with entity_id, status, last_seen, issue, state_changes
- entities: Flattened entity list for iteration
- entity_count: Number of devices analyzed
- hours: Analysis period

Please analyze this device health data and generate a Python script that:
1. Identifies devices that appear unresponsive or degraded
2. Detects devices with unusual state change patterns
3. Flags devices with high unavailable/unknown state ratios
4. Provides health scores and recommended actions per device

Output insights as JSON to stdout with type="device_health".
"""

    elif state.analysis_type == AnalysisType.COST_OPTIMIZATION:
        prompt = (
            energy_context
            + """
Please analyze this data and generate a Python script that:
1. Identifies the highest energy consumers
2. Calculates cost projections based on usage patterns
3. Suggests schedule changes to reduce costs (off-peak shifting)
4. Estimates monthly savings for each recommendation

Output insights as JSON to stdout with type="cost_saving".
Include estimated_monthly_savings in the evidence for each insight.
"""
        )

    else:  # CUSTOM or other
        custom_query = state.custom_query or "Perform a general analysis"
        prompt = f"""
I have data for {entity_count} entities over the past {hours} hours.

Data structure (available in /workspace/data.json):
- entities: List of entity data
- entity_count: Number of entities
- hours: Analysis period

Custom analysis request: {custom_query}

Generate a Python script that addresses this request.
Output insights as JSON to stdout.
"""

    # Feature 33: append depth-specific EDA fragment
    fragment = load_depth_fragment(state.depth)
    if fragment:
        prompt = prompt + "\n\n" + fragment
    return prompt
