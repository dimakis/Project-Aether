# Feature 12: Climate Comfort Analysis

## Status: Proposed

## Summary

Enable the Data Scientist to analyze temperature, humidity, and HVAC data across rooms to produce per-room comfort scores, identify problem zones, and suggest climate automation improvements.

## Problem Statement

Users with multiple climate sensors often have no easy way to understand comfort patterns across their home. Rooms may be too hot in the afternoon, too humid after showers, or inefficiently heated/cooled. Home Assistant records the data but doesn't surface cross-room comfort analysis or actionable recommendations.

## User Experience

### Flow 1: "How comfortable is my home?"

```
You: "How's the temperature across my house?"

  → Architect delegates to Data Scientist (analysis_type: climate_comfort)
  → DS discovers all temperature/humidity sensors via entity catalog
  → DS fetches 48h of history for each sensor + weather entity
  → Sandbox: per-room statistical analysis, comfort scoring (PMV/PPD model)
  → Generates room-by-room comfort report with heatmap data

  "Here's your home comfort report for the last 48 hours:

   🌡️ **Living Room**: 22.5°C avg, 45% humidity — Comfortable ✅
   🌡️ **Bedroom**: 26.8°C between 3-6 PM — Too warm ⚠️
      → Afternoon sun heats the room. Consider closing blinds at 2 PM.
   🌡️ **Master Bath**: 78% humidity avg — Too humid ⚠️
      → Suggest: run extraction fan for 15 min after shower.
   🌡️ **Office**: 19.1°C avg — Slightly cool
      → Heating schedule ends at 5 PM but you're active until 7 PM."
```

### Flow 2: "Why is my bedroom so hot?"

```
You: "Why is the bedroom always hot in the afternoon?"

  → Architect delegates with specific entity_ids (bedroom sensors)
  → DS fetches bedroom temperature + weather + HVAC history
  → Sandbox: correlation analysis (indoor temp vs outdoor, solar angle, HVAC state)

  "Your bedroom temperature rises ~4°C between 1-5 PM. Strong correlation
   with outdoor temperature (r=0.87) and west-facing window solar gain.
   Your AC starts at 3 PM but takes 90 minutes to recover.
   
   💡 Suggestions:
   1. Pre-cool the bedroom starting at 12:30 PM
   2. Close blinds/shutters at 1 PM (automation suggestion)
   3. Consider window film to reduce solar heat gain"
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `CLIMATE_COMFORT` | "comfort", "temperature across", "how warm/cold" | Full home comfort audit |
| `HVAC_EFFICIENCY` | "heating efficiency", "AC performance", "HVAC" | HVAC runtime vs comfort achieved |
| `HUMIDITY_ANALYSIS` | "humidity", "moisture", "damp" | Humidity patterns, mold risk |

## Data Sources

### Required Entities

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `temperature` | Room temperature readings |
| `sensor` | `humidity` | Room humidity readings |
| `weather` | — | Outdoor conditions for correlation |

### Optional Entities (enrich analysis)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `climate` | — | HVAC state, setpoints, modes |
| `sensor` | `pressure` | Barometric pressure |
| `sensor` | `co2` | Air quality correlation |
| `sensor` | `pm25` / `pm10` | Air quality |
| `cover` | — | Blind/shutter state for solar gain analysis |
| `binary_sensor` | `window` | Open window detection |

### MCP Tools Used

- `list_entities` — discover climate-related sensors (filter by device_class)
- `get_history` — fetch historical data for analysis window
- `domain_summary_tool` — overview of sensor/climate domains
- `get_entity` — detailed attributes (unit_of_measurement, etc.)

## Comfort Scoring

Use the simplified PMV/PPD (Predicted Mean Vote / Predicted Percentage Dissatisfied) model adapted for residential settings:

| Score | Label | Temperature Range | Humidity Range |
|-------|-------|-------------------|----------------|
| 5 | Excellent | 21-23°C | 40-50% |
| 4 | Comfortable | 20-24°C | 35-55% |
| 3 | Acceptable | 18-26°C | 30-60% |
| 2 | Uncomfortable | 16-28°C | 25-70% |
| 1 | Poor | <16°C or >28°C | <25% or >70% |

Score parameters should be configurable via analysis options.

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `CLIMATE_COMFORT` | "Bedroom comfort score is 2/5 between 3-6 PM" |
| `HVAC_EFFICIENCY` | "Living room AC runs 4h to achieve 1°C cooling — check filter" |
| `HUMIDITY_RISK` | "Bathroom humidity exceeds 70% for 3+ hours daily — mold risk" |

## Automation Suggestions

The analysis may produce `AutomationSuggestion` objects for the Architect:

- Pre-cool/pre-heat rooms based on occupancy schedule
- Close blinds when solar gain predicted
- Run extraction fans after humidity spikes
- Adjust HVAC schedules based on actual comfort data vs wasted runtime

## Implementation Notes

### New AnalysisType Values

```python
CLIMATE_COMFORT = "climate_comfort"
HVAC_EFFICIENCY = "hvac_efficiency"
HUMIDITY_ANALYSIS = "humidity_analysis"
```

### New InsightType Values

```python
CLIMATE_COMFORT = "climate_comfort"
HVAC_EFFICIENCY = "hvac_efficiency"
HUMIDITY_RISK = "humidity_risk"
```

### Sandbox Script Approach

The generated script should:
1. Load all temperature/humidity time series from `/workspace/data.json`
2. Compute per-room statistics (mean, min, max, std, percentiles)
3. Score each room using the comfort model
4. Identify worst periods (time windows with lowest comfort)
5. Correlate with weather data if available
6. Output structured JSON with room scores, problem periods, and recommendations

### Entity Discovery Heuristic

```python
# Find climate-related sensors
climate_sensors = await entity_repo.find_by_device_class(
    domain="sensor", 
    device_classes=["temperature", "humidity"]
)
climate_entities = await entity_repo.find_by_domain("climate")
weather_entities = await entity_repo.find_by_domain("weather")
```

## Dependencies

- Existing: `get_history`, sandbox, Data Scientist pipeline
- New: Comfort scoring model (implemented in sandbox script, not a library dependency)

## Acceptance Criteria

1. **Given** temperature sensors in multiple rooms, **When** climate comfort analysis runs, **Then** each room gets a comfort score with supporting data
2. **Given** humidity sensors in bathrooms, **When** analysis detects sustained >70% humidity, **Then** a humidity risk insight is generated
3. **Given** HVAC entities and temperature sensors, **When** HVAC efficiency analysis runs, **Then** runtime-vs-comfort metrics are calculated
4. **Given** a room with poor comfort score and identifiable cause, **When** analysis completes, **Then** an automation suggestion is produced
5. **Given** weather entities available, **When** analysis runs, **Then** outdoor correlation is included in the report

## Out of Scope

- Real-time comfort monitoring (requires `subscribe_events`)
- HVAC control recommendations that modify setpoints (would need HITL)
- Integration with external weather forecast APIs
- Multi-building / multi-floor aggregation
