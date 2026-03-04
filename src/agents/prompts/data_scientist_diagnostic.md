I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh} kWh

Data structure (available in /workspace/data.json):
- total_kwh: float — Total consumption across all sensors
- average_kwh: float — Average per sensor
- entity_count: int — Number of sensors
- hours: int — Analysis period
- entities: list of objects, each with:
    - entity_id: str (e.g. "sensor.washing_machine_energy")
    - friendly_name: str | null
    - device_class: str | null (e.g. "energy", "power")
    - unit: str (e.g. "kWh", "W")
    - data_points: list of {{"timestamp": "ISO-8601", "value": float, "unit": str}}
    - stats: {{"total": float, "average": float, "min": float, "max": float,
              "count": int, "unit": str, "peak_value": float,
              "peak_timestamp": "ISO-8601"|null,
              "daily_totals": {{"YYYY-MM-DD": float}},
              "hourly_averages": {{"0": float, ..., "23": float}}}}
    - start_time: "ISO-8601"
    - end_time: "ISO-8601"

**DIAGNOSTIC MODE** — The Architect has gathered evidence about a system issue
and needs your help analyzing it.

**Architect's Collected Evidence:**
{diagnostic_context}

**Investigation Instructions:**
{instructions}

Please generate a Python script that:
1. Analyzes the provided entity data for gaps, missing values, and anomalies
2. Checks for periods with no data (connectivity issues)
3. Identifies state transitions that suggest integration failures
4. Correlates any patterns with the diagnostic context above
5. Provides specific findings about root cause and affected time periods

Output insights as JSON to stdout with type="diagnostic".
Each insight should include:
- title: Short description of the finding
- description: Detailed explanation
- impact: "critical", "high", "medium", or "low"
- confidence: 0.0-1.0
- evidence: Supporting data points
- recommendation: What to do about it
