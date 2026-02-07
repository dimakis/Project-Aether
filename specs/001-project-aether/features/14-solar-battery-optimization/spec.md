# Feature 14: Solar & Battery Optimization

## Status: Proposed

## Summary

Enable the Data Scientist to analyze solar production, battery state, grid import/export, and consumption data to optimize self-consumption, battery scheduling, and identify cost-saving opportunities for users with solar PV and/or battery storage systems.

## Problem Statement

Users with solar panels and batteries often don't know how efficiently they're using their solar production. Key questions go unanswered: How much solar am I exporting at low feed-in rates when I could self-consume? Should I charge my EV during the day instead of overnight? Is my battery cycling optimally? Home Assistant collects all this data but surfacing actionable optimization requires cross-entity analysis.

## User Experience

### Flow 1: "How's my solar doing?"

```
You: "Analyze my solar production this week"

  → DS discovers solar/battery/grid sensors
  → DS fetches 7 days of history
  → Sandbox: production curves, self-consumption ratio, export analysis

  "☀️ **Solar Report** (last 7 days)

   📊 Total production: 42.3 kWh
   🏠 Self-consumed: 25.1 kWh (59%)
   📤 Exported to grid: 17.2 kWh (41%) at ~$0.05/kWh = $0.86
   📥 Grid import: 31.4 kWh at ~$0.28/kWh = $8.79
   
   ⚡ Peak production: 6.8 kW (Tuesday, 12:15 PM)
   📈 Best day: Wednesday (8.2 kWh)
   📉 Worst day: Saturday (2.1 kWh — cloudy)

   💡 **Optimization opportunity**: You export 73% of production between
   10 AM-2 PM. Shifting EV charging to this window would self-consume
   an extra 12 kWh/week, saving ~$3.10/week ($161/year)."
```

### Flow 2: "Optimize my battery schedule"

```
You: "Is my battery being used efficiently?"

  → DS analyzes battery charge/discharge cycles vs solar + grid prices
  → Sandbox: cycle analysis, efficiency calculation, schedule optimization

  "🔋 **Battery Analysis** (last 7 days)

   Cycles: 6.8 full cycles (avg 0.97/day)
   Charge efficiency: 89% (10.2 kWh in → 9.1 kWh out)
   
   ⚠️ Issue: Battery charges from grid between 2-4 AM (off-peak) but
   solar production could charge it by 11 AM for free.
   
   💡 Suggestion: Disable grid charging, rely on solar charging.
   Estimated saving: $2.40/week.
   
   📊 Optimal discharge window: 5-9 PM (highest grid price + consumption)"
```

### Flow 3: "Self-consumption analysis"

```
You: "How can I use more of my solar?"

  → DS identifies loads that could shift to solar hours
  → Sandbox: load profile analysis, shiftable load identification

  "Your self-consumption ratio is 59%. Here's how to improve it:

   1. 🚗 EV Charging (currently 11 PM-6 AM → shift to 10 AM-3 PM): +12 kWh/week
   2. 🧺 Washing machine (currently 7 PM → shift to midday): +1.5 kWh/week  
   3. 🍽️ Dishwasher (currently 9 PM → shift to 1 PM): +1.2 kWh/week
   
   With these shifts: Self-consumption would rise from 59% → 84%
   Annual saving estimate: ~$520"
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `SOLAR_PRODUCTION` | "solar", "production", "panels" | Production trends, peak analysis |
| `BATTERY_OPTIMIZATION` | "battery", "powerwall", "storage" | Cycle analysis, schedule optimization |
| `SELF_CONSUMPTION` | "self-consumption", "use my solar", "export" | Maximize solar self-use |
| `SOLAR_SAVINGS` | "solar savings", "ROI", "payback" | Financial analysis of solar system |

## Data Sources

### Required Entities (at least some)

| Domain | Device Class | Common Names | Purpose |
|--------|-------------|-------------|---------|
| `sensor` | `power` | `*solar*power*`, `*pv*power*` | Instantaneous solar production |
| `sensor` | `energy` | `*solar*energy*`, `*pv*energy*` | Cumulative solar production |

### Optional Entities (enrich analysis)

| Domain | Device Class | Common Names | Purpose |
|--------|-------------|-------------|---------|
| `sensor` | `energy` / `power` | `*grid*`, `*import*`, `*export*` | Grid exchange |
| `sensor` | `battery` | `*battery*soc*`, `*battery*level*` | Battery state of charge |
| `sensor` | `power` | `*battery*power*` | Battery charge/discharge rate |
| `sensor` | `energy` | `*consumption*`, `*total*energy*` | Total home consumption |
| `sensor` | `power` | `*ev*charger*`, `*car*charger*` | EV charging load |
| `sensor` | `monetary` | `*energy*cost*` | Energy cost tracking |
| `weather` | — | — | Cloud cover correlation |

### Entity Discovery Heuristic

Solar entities are named inconsistently across integrations (SolarEdge, Enphase, Fronius, Huawei, etc.). Discovery should:

1. Search by `device_class` in `[power, energy, battery]`
2. Filter by name patterns: `solar`, `pv`, `panel`, `inverter`, `grid`, `export`, `import`, `feed_in`, `battery`, `powerwall`
3. Check `unit_of_measurement` for `W`, `kW`, `Wh`, `kWh`
4. Group by integration/device to find complete solar systems

### MCP Tools Used

- `list_entities` — discover solar/battery/grid sensors
- `get_history` — fetch production/consumption timeseries
- `get_entity` — detailed attributes (device_class, unit)
- `domain_summary_tool` — sensor domain overview

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `SOLAR_PRODUCTION` | "Weekly production: 42 kWh, 15% above seasonal average" |
| `SELF_CONSUMPTION` | "Self-consumption ratio: 59%. Could reach 84% with load shifting" |
| `BATTERY_EFFICIENCY` | "Battery round-trip efficiency: 89%. 2 AM grid charging is suboptimal" |
| `SOLAR_SAVINGS` | "Solar offset $45 of grid costs this month" |

## Automation Suggestions

- Shift EV charging to peak solar hours
- Start high-consumption appliances (washer, dishwasher) during solar surplus
- Battery: disable grid charging when solar is sufficient
- Battery: force discharge during peak grid rate hours
- Send notification when daily solar production is unusually low (panel issue?)

## Implementation Notes

### New AnalysisType Values

```python
SOLAR_PRODUCTION = "solar_production"
BATTERY_OPTIMIZATION = "battery_optimization"
SELF_CONSUMPTION = "self_consumption"
SOLAR_SAVINGS = "solar_savings"
```

### New InsightType Values

```python
SOLAR_PRODUCTION = "solar_production"
SELF_CONSUMPTION = "self_consumption"
BATTERY_EFFICIENCY = "battery_efficiency"
SOLAR_SAVINGS = "solar_savings"
```

### Sandbox Script Approach

```python
# 1. Load solar production, grid import/export, battery SoC, consumption
# 2. Align all timeseries to common interval (5-min or 15-min)
# 3. Calculate:
#    - Total production, consumption, import, export
#    - Self-consumption ratio = (production - export) / production
#    - Peak production time and power
#    - Battery cycle count and efficiency
# 4. Identify shiftable loads (high consumption during export periods)
# 5. Model savings from load shifting
# 6. Output JSON with metrics, charts, recommendations
```

### Tariff Configuration

Energy prices should be configurable via analysis options:

```json
{
  "grid_import_rate": 0.28,
  "grid_export_rate": 0.05,
  "currency": "USD",
  "time_of_use": {
    "peak": {"rate": 0.35, "hours": "17-21"},
    "off_peak": {"rate": 0.15, "hours": "23-07"},
    "standard": {"rate": 0.28}
  }
}
```

If not provided, the script should note that cost estimates are unavailable and focus on kWh analysis.

## Acceptance Criteria

1. **Given** solar production sensors, **When** solar analysis runs, **Then** production totals, peak times, and daily breakdown are reported
2. **Given** solar + grid sensors, **When** self-consumption analysis runs, **Then** the self-consumption ratio is calculated with export/import breakdown
3. **Given** battery sensors, **When** battery analysis runs, **Then** cycle count, efficiency, and charge/discharge patterns are reported
4. **Given** shiftable loads identified, **When** analysis completes, **Then** specific load-shifting recommendations with estimated savings are produced
5. **Given** no solar sensors found, **When** solar analysis is requested, **Then** a clear message explains which sensor types are needed

## Out of Scope

- Weather forecast integration for production prediction
- Direct battery/inverter control via MCP
- Real-time solar monitoring dashboard
- Multi-string / micro-inverter level analysis
- Grid tariff API integration (manual config only)
