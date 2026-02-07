I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh} kWh

Data structure (available in /workspace/data.json):
- entities: List of entity data with data_points, stats, etc.
- total_kwh: Total consumption
- hours: Analysis period

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
