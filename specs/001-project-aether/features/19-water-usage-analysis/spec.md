# Feature 19: Water Usage Analysis

## Status: Proposed

## Summary

Enable the Data Scientist to analyze water consumption patterns, detect leaks (continuous flow at unusual hours), identify irrigation waste, and suggest water-saving automations for users with water flow/consumption sensors.

## Problem Statement

Water leaks can go undetected for days or weeks, causing damage and waste. Even without leaks, irrigation systems may run during rain, showers may run longer than necessary, and users have no visibility into their water consumption patterns. HA users with water meters or flow sensors have the data, but no automated analysis.

## User Experience

### Flow 1: "Analyze my water usage"

```
You: "How much water am I using?"

  → DS discovers water sensors (flow, consumption, moisture)
  → DS fetches 30 days of history
  → Sandbox: consumption breakdown, pattern analysis

  "💧 **Water Usage Report** (last 30 days)

   📊 Total: 12,450 liters (415 L/day average)
   📈 This month vs last: +8%

   ⏰ **Usage by time of day**:
   | Period | Daily Avg | % of Total |
   |--------|----------|------------|
   | 6-9 AM | 145 L | 35% — morning showers/breakfast |
   | 9 AM-5 PM | 85 L | 20% — irrigation + misc |
   | 5-9 PM | 125 L | 30% — cooking/evening |
   | 9 PM-6 AM | 60 L | 15% — ⚠️ higher than expected |

   ⚠️ **Night usage (60 L/day)** is higher than typical for an
   unoccupied period. Possible slow leak or running toilet.
   
   🌿 **Irrigation**: 35 L/day average. Ran on 3 rainy days this month."
```

### Flow 2: "Do I have a leak?"

```
You: "I think I might have a water leak"

  → DS analyzes minimum flow periods (2-5 AM baseline)
  → Sandbox: leak detection analysis

  "🔍 **Leak Detection Analysis**

   Analyzing minimum flow periods (2-5 AM, no expected usage):
   
   ❌ **Likely leak detected**
   Continuous flow of ~2.1 L/hour between 2-5 AM on 28 of 30 nights
   Estimated waste: 50 L/day = 1,500 L/month
   
   This pattern suggests:
   - Running toilet (most common — check flapper valve)
   - Slow drip in a faucet
   - Irrigation system weeping
   
   💰 Estimated cost: ~$4.50/month in water + sewage charges
   
   Recommendation: Check toilets first (add food coloring to tank,
   if bowl colors within 15 min, the flapper needs replacement)."
```

### Flow 3: "Is my irrigation efficient?"

```
You: "Is my garden irrigation wasting water?"

  → DS correlates irrigation runtime with weather/rain data
  → Sandbox: irrigation efficiency analysis

  "🌿 **Irrigation Analysis** (last 30 days)

   Total irrigation: 1,050 L (35 L/day)
   Runtime: 20 min/day at 6 AM
   
   ⚠️ **Waste detected**:
   - Irrigated on 3 rainy days (105 L wasted)
   - Irrigated day after 15mm+ rainfall on 2 occasions (70 L wasted)
   - Total waste: ~175 L (17% of irrigation water)
   
   💡 Suggestions:
   1. Add rain sensor check to irrigation automation
   2. Skip irrigation if >5mm rain in last 24 hours
   3. Reduce duration in cool/cloudy weather
   
   Shall I create a weather-aware irrigation automation?"
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `WATER_CONSUMPTION` | "water usage", "water consumption" | Consumption patterns and breakdown |
| `LEAK_DETECTION` | "leak", "water leak", "running water" | Minimum-flow analysis for leak detection |
| `IRRIGATION_EFFICIENCY` | "irrigation", "garden water", "sprinkler" | Irrigation vs weather correlation |

## Data Sources

### Required Entities (at least one)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `water` | Water consumption (liters/gallons) |

### Optional Entities

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `flow_rate` / `volume_flow_rate` | Real-time flow rate |
| `binary_sensor` | `moisture` | Soil moisture sensors |
| `switch` / `valve` | — | Irrigation valves |
| `weather` | — | Rain data for irrigation correlation |
| `sensor` | `precipitation` | Rain gauge |
| `sensor` | `monetary` | Water cost tracking |

### MCP Tools Used

- `list_entities` — discover water-related sensors
- `get_history` — fetch consumption timeseries
- `get_entity` — attributes (unit, device_class)

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `WATER_CONSUMPTION` | "Daily average: 415 L. 15% used during night hours" |
| `WATER_LEAK` | "Continuous 2.1 L/hour flow detected at night — likely leak" |
| `IRRIGATION_WASTE` | "Irrigated on 3 rainy days — 175 L wasted" |

## Automation Suggestions

- Alert when continuous flow detected during night hours (leak warning)
- Skip irrigation when rain detected in last 24 hours
- Adjust irrigation duration based on weather forecast
- Alert when daily consumption exceeds threshold

## Implementation Notes

### New AnalysisType Values

```python
WATER_CONSUMPTION = "water_consumption"
LEAK_DETECTION = "leak_detection"
IRRIGATION_EFFICIENCY = "irrigation_efficiency"
```

### New InsightType Values

```python
WATER_CONSUMPTION = "water_consumption"
WATER_LEAK = "water_leak"
IRRIGATION_WASTE = "irrigation_waste"
```

### Leak Detection Algorithm

```python
# In sandbox script:
# 1. Isolate 2-5 AM window (minimal expected usage)
# 2. Calculate flow rate during this window for each night
# 3. If consistent flow > threshold (e.g., 1 L/hour) on >50% of nights:
#    → Flag as likely leak
# 4. Estimate daily waste = avg_night_flow * 24
# 5. Classify:
#    - < 1 L/hr: possible slow drip
#    - 1-5 L/hr: running toilet or faucet
#    - > 5 L/hr: significant leak
LEAK_THRESHOLD_L_PER_HOUR = 1.0
LEAK_NIGHT_START = "02:00"
LEAK_NIGHT_END = "05:00"
LEAK_MIN_NIGHTS_PERCENT = 50
```

### Irrigation Correlation

```python
# Cross-reference irrigation events with weather:
# 1. Identify irrigation events (valve on, or flow > threshold during schedule)
# 2. For each event, check:
#    - Was it raining? (weather entity state)
#    - Did it rain in last 24 hours? (precipitation history)
#    - Soil moisture level? (if available)
# 3. Flag events where irrigation was unnecessary
```

## Acceptance Criteria

1. **Given** water consumption sensor, **When** water usage analysis runs, **Then** daily breakdown by time period is produced
2. **Given** consistent night-time flow detected, **When** leak detection runs, **Then** a leak insight is generated with estimated waste
3. **Given** irrigation + weather entities, **When** irrigation analysis runs, **Then** rain-day irrigation events are flagged as waste
4. **Given** leak detected, **When** analysis completes, **Then** an automation suggestion for leak alerts is produced
5. **Given** no water sensors found, **When** water analysis requested, **Then** a clear message explains which sensor types are needed

## Out of Scope

- Per-fixture water breakdown (requires per-fixture flow sensors)
- Water quality analysis (pH, hardness)
- Greywater/rainwater harvesting optimization
- Municipal water pressure monitoring
