# Feature 15: Appliance Efficiency Tracking

## Status: Proposed

## Summary

Enable the Data Scientist to track individual appliance power consumption over time, detect efficiency degradation, compare similar appliances, and predict maintenance needs based on consumption trend analysis.

## Problem Statement

Smart plugs and energy monitors give per-appliance power data, but users rarely analyze trends over weeks or months. A refrigerator drawing 20% more power than last month may signal a failing compressor. A washing machine with increasing cycle energy could have a clogged filter. These degradation patterns are invisible without longitudinal analysis — but the data is already in Home Assistant.

## User Experience

### Flow 1: "Check my appliance health"

```
You: "Are any of my appliances using more energy than they should?"

  → DS discovers per-appliance energy sensors (smart plugs, energy monitors)
  → DS fetches 30-90 days of history
  → Sandbox: trend analysis, baseline comparison, anomaly detection

  "🔌 **Appliance Efficiency Report** (last 90 days)

   ❌ **Kitchen Fridge** (sensor.fridge_power)
      Current avg: 85W | 3-month baseline: 72W | Change: +18%
      ⚠️ Steady increase over 6 weeks. Common causes: dirty condenser
      coils, worn door seals, or failing compressor. Recommend cleaning
      condenser coils as first step.
   
   ✅ **Washing Machine** (sensor.washer_energy)
      Avg cycle: 1.2 kWh | Baseline: 1.15 kWh | Change: +4%
      Within normal variation.
   
   ✅ **Dryer** (sensor.dryer_energy)
      Avg cycle: 3.1 kWh | Baseline: 3.05 kWh | Change: +2%
      Within normal variation.
   
   🟡 **Dishwasher** (sensor.dishwasher_energy)
      Avg cycle: 1.8 kWh | Baseline: 1.5 kWh | Change: +20%
      ⚠️ Jump detected 3 weeks ago. Check heating element and filters."
```

### Flow 2: "Compare my AC units"

```
You: "Which of my AC units is least efficient?"

  → DS finds all climate/AC entities and associated power sensors
  → Sandbox: efficiency comparison (energy per degree of cooling)

  "🌡️ **AC Efficiency Comparison**

   | Unit | Avg Power | Cooling Rate | Efficiency |
   |------|-----------|-------------|------------|
   | Living Room AC | 1,200W | 2.1°C/hr | ⭐ Best |
   | Bedroom AC | 980W | 1.4°C/hr | 🟡 Average |
   | Office AC | 1,150W | 0.9°C/hr | ❌ Worst |

   The office AC uses similar power but cools 57% slower than the
   living room unit. Possible causes: dirty filters, refrigerant
   leak, or the room has higher heat gain (check insulation)."
```

### Flow 3: Proactive alert via scheduled insight

```
Scheduled insight (weekly):
  → DS checks all tracked appliances against their baselines
  → Flags any with >15% increase
  
  "⚠️ Weekly Appliance Alert: Your garage freezer power consumption
   increased 22% this week compared to its 90-day average. This is
   the 3rd consecutive week of increase. Strongly recommend inspection."
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `APPLIANCE_EFFICIENCY` | "appliance health", "appliance efficiency" | Full appliance audit |
| `APPLIANCE_COMPARISON` | "compare", "which is better", "least efficient" | Compare similar appliances |
| `APPLIANCE_TREND` | "appliance trends", "degradation", "maintenance" | Long-term trend analysis |

## Data Sources

### Required Entities

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `power` | Real-time power draw per appliance |
| `sensor` | `energy` | Cumulative energy per appliance |

### Discovery Strategy

Per-appliance sensors typically come from:
- **Smart plugs**: Shelly, Tasmota, TP-Link, Tuya — create `sensor.*_power` and `sensor.*_energy`
- **Whole-home monitors**: Emporia Vue, Sense — create per-circuit entities
- **Integration-specific**: Washing machine integrations (Samsung, LG SmartThinQ)

Discovery heuristic:
1. Find `sensor` entities with `device_class` in `[power, energy]`
2. Exclude whole-home / grid / solar sensors (by name patterns)
3. Group by device_id to pair power + energy sensors for the same appliance
4. Use entity friendly_name to identify appliance type

### MCP Tools Used

- `list_entities` — discover per-appliance power/energy sensors
- `get_history` — fetch 30-90 day history for trend analysis
- `get_entity` — attributes (device_class, unit, device_id)

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `APPLIANCE_DEGRADATION` | "Fridge power +18% over 6 weeks — maintenance recommended" |
| `APPLIANCE_ANOMALY` | "Dishwasher energy jumped 20% — sudden change 3 weeks ago" |
| `APPLIANCE_COMPARISON` | "Office AC 57% less efficient than living room unit" |
| `MAINTENANCE_PREDICTION` | "Based on trend, freezer will exceed 2x baseline in ~4 weeks" |

## Automation Suggestions

- Send alert when appliance power exceeds threshold for sustained period
- Track and log per-appliance daily energy for long-term trend visibility
- Power-off smart plug if appliance draws power in standby unexpectedly

## Implementation Notes

### New AnalysisType Values

```python
APPLIANCE_EFFICIENCY = "appliance_efficiency"
APPLIANCE_COMPARISON = "appliance_comparison"
APPLIANCE_TREND = "appliance_trend"
```

### New InsightType Values

```python
APPLIANCE_DEGRADATION = "appliance_degradation"
APPLIANCE_ANOMALY = "appliance_anomaly"
APPLIANCE_COMPARISON = "appliance_comparison"
```

### Baseline Calculation

```python
# In sandbox script:
# 1. Compute rolling 30-day average power as baseline
# 2. Compare recent 7-day average to baseline
# 3. Flag if deviation > 15% (configurable threshold)
# 4. For cyclic appliances (washer, dishwasher):
#    a. Detect cycles (power > threshold for > min_duration)
#    b. Calculate per-cycle energy
#    c. Compare recent cycles to historical average
```

### Cycle Detection

For appliances with discrete usage cycles (washer, dishwasher, dryer):

```python
# Detect cycles: power exceeds standby threshold for minimum duration
CYCLE_PARAMS = {
    "washer": {"threshold_w": 50, "min_duration_min": 15},
    "dishwasher": {"threshold_w": 30, "min_duration_min": 20},
    "dryer": {"threshold_w": 200, "min_duration_min": 15},
    "oven": {"threshold_w": 500, "min_duration_min": 10},
}
```

## Acceptance Criteria

1. **Given** per-appliance power sensors with 30+ days of data, **When** efficiency analysis runs, **Then** each appliance gets a baseline comparison with percentage change
2. **Given** an appliance with >15% power increase, **When** analysis completes, **Then** a degradation insight is generated with possible causes
3. **Given** multiple AC/heating units, **When** comparison analysis runs, **Then** efficiency metrics are calculated and units ranked
4. **Given** cyclic appliances, **When** trend analysis runs, **Then** per-cycle energy is tracked and compared to historical average
5. **Given** insufficient history (<7 days), **When** analysis runs, **Then** a clear message explains minimum data requirements

## Out of Scope

- Appliance identification from whole-home power data (NILM — too complex)
- Manufacturer-specific diagnostic codes
- Integration with warranty or service scheduling systems
- Real-time power monitoring alerts (requires `subscribe_events`)
