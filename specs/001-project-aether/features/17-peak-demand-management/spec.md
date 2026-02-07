# Feature 17: Peak Demand Management

## Status: Proposed

## Summary

Enable the Data Scientist to identify simultaneous high-power loads, analyze demand peaks, model time-of-use tariff impacts, and suggest load staggering strategies to reduce electricity costs and avoid demand charges.

## Problem Statement

Running the EV charger, dryer, oven, and heat pump simultaneously can create expensive demand peaks. Many electricity tariffs include demand charges (based on the highest kW draw in a billing period) or time-of-use rates. Users don't know when their peaks occur, which appliances contribute most, or how much they could save by staggering loads. Home Assistant has the data to answer all of this.

## User Experience

### Flow 1: "When are my power peaks?"

```
You: "Analyze my peak electricity demand"

  → DS fetches whole-home power + per-circuit/appliance sensors
  → Sandbox: peak detection, load stacking analysis

  "⚡ **Peak Demand Report** (last 30 days)

   📊 Maximum demand: 11.2 kW (Feb 3, 6:15 PM)
   📊 Average peak (daily): 7.8 kW
   📊 Average demand: 2.1 kW
   
   🔝 **Top 5 Peak Events** (>8 kW):
   | Date | Peak | Duration | Contributing Loads |
   |------|------|----------|-------------------|
   | Feb 3 | 11.2 kW | 45 min | EV charger + oven + heat pump |
   | Feb 1 | 9.8 kW | 30 min | EV charger + dryer + heat pump |
   | Jan 29 | 9.1 kW | 25 min | Oven + dryer + dishwasher |
   | Jan 28 | 8.7 kW | 55 min | EV charger + heat pump |
   | Jan 25 | 8.4 kW | 20 min | EV charger + oven |

   ⚡ **EV charger** is present in 4/5 top peaks.
   
   💡 If you stagger EV charging to after 10 PM (when oven/dryer are off),
   your peak drops from 11.2 kW to ~6.8 kW."
```

### Flow 2: "Model my tariff"

```
You: "How much would I save with a time-of-use tariff?"

  → DS takes your actual consumption profile
  → Sandbox: models flat-rate vs TOU vs demand-charge tariffs

  "💰 **Tariff Comparison** (based on your last 30 days of usage)

   | Tariff | Monthly Cost | vs Current |
   |--------|-------------|------------|
   | Flat rate ($0.28/kWh) | $142 | Current plan |
   | TOU (peak $0.35, off-peak $0.15) | $128 | Save $14/mo |
   | TOU + demand ($0.25/kWh + $8/kW) | $151 | Costs $9 more |
   
   With TOU: You'd save by shifting 23% of your peak-hour usage to
   off-peak. Main candidates: EV charging, dishwasher, laundry.
   
   ⚠️ Avoid demand-charge tariffs — your 11.2 kW peaks would cost
   $89/mo in demand charges alone."
```

### Flow 3: "Help me reduce demand"

```
You: "How can I reduce my peak demand?"

  → DS identifies staggerable loads and creates a schedule

  "📋 **Load Staggering Plan**

   Your current peak problem: 5-8 PM, EV + cooking + heating overlap.
   
   Proposed schedule:
   | Time | Load | Current | Proposed |
   |------|------|---------|----------|
   | 5-7 PM | Cooking (oven) | ✅ Keep | ✅ Keep (can't shift) |
   | 5-7 PM | Heat pump | ✅ Keep | ✅ Keep (comfort) |
   | 5-7 PM | EV charger | ❌ Shift | → 10 PM-6 AM |
   | 5-7 PM | Dryer | ❌ Shift | → 8 PM-10 PM |
   | 6-7 PM | Dishwasher | ❌ Shift | → 9 PM |
   
   Expected peak reduction: 11.2 kW → 5.8 kW (-48%)
   
   Shall I create automations for the EV charging and 
   dishwasher schedules?"
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `PEAK_DEMAND` | "peak demand", "power peaks", "demand charges" | Peak event detection and analysis |
| `TARIFF_MODELING` | "tariff", "time of use", "TOU", "electricity rate" | Compare tariff structures against actual usage |
| `LOAD_STAGGERING` | "stagger loads", "reduce peaks", "load schedule" | Identify shiftable loads, propose schedule |

## Data Sources

### Required Entities

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `power` | Whole-home instantaneous power (at minimum) |

### Optional Entities (enrich analysis)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `power` / `energy` | Per-circuit or per-appliance breakdown |
| `sensor` | `energy` | Cumulative energy for cost modeling |
| `climate` | — | HVAC load identification |
| `sensor` | — | EV charger sensors |

### MCP Tools Used

- `list_entities` — discover power/energy sensors
- `get_history` — fetch power timeseries (high resolution preferred)
- `get_entity` — attributes for load identification

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `PEAK_DEMAND` | "Max demand: 11.2 kW. EV charger contributes to 80% of peaks" |
| `TARIFF_RECOMMENDATION` | "TOU tariff would save $14/month with current usage pattern" |
| `LOAD_STAGGER` | "Shifting EV charging to off-peak reduces peak by 48%" |

## Automation Suggestions

- Schedule EV charging to off-peak hours
- Delay dishwasher/dryer start to avoid peak overlap
- Load shedding: pause EV charging when total power exceeds threshold
- Smart scheduling: start appliances sequentially instead of simultaneously

## Implementation Notes

### New AnalysisType Values

```python
PEAK_DEMAND = "peak_demand"
TARIFF_MODELING = "tariff_modeling"
LOAD_STAGGERING = "load_staggering"
```

### New InsightType Values

```python
PEAK_DEMAND = "peak_demand"
TARIFF_RECOMMENDATION = "tariff_recommendation"
LOAD_STAGGER = "load_stagger"
```

### Peak Detection Algorithm

```python
# In sandbox script:
# 1. Resample whole-home power to 1-minute intervals
# 2. Find peaks: local maxima above threshold (e.g., 5 kW)
# 3. For each peak:
#    a. Find contributing loads (per-circuit sensors active during peak)
#    b. Calculate peak duration (time above 80% of peak value)
#    c. Identify which loads could have been shifted
# 4. Rank peaks by magnitude and frequency
```

### Tariff Configuration

```json
{
  "tariff_options": [
    {
      "name": "Flat Rate",
      "type": "flat",
      "rate_per_kwh": 0.28
    },
    {
      "name": "Time of Use",
      "type": "tou",
      "peak_rate": 0.35,
      "peak_hours": "17-21",
      "off_peak_rate": 0.15,
      "off_peak_hours": "23-07",
      "standard_rate": 0.25
    },
    {
      "name": "Demand Charge",
      "type": "demand",
      "energy_rate": 0.25,
      "demand_rate_per_kw": 8.00
    }
  ]
}
```

## Acceptance Criteria

1. **Given** whole-home power sensor, **When** peak demand analysis runs, **Then** top peak events are identified with timestamps and magnitude
2. **Given** per-appliance sensors, **When** peak analysis runs, **Then** contributing loads are identified for each peak event
3. **Given** tariff options provided, **When** tariff modeling runs, **Then** monthly cost is calculated for each tariff and a recommendation is given
4. **Given** shiftable loads identified, **When** load staggering analysis runs, **Then** a proposed schedule with expected peak reduction is produced
5. **Given** only whole-home sensor (no per-appliance), **When** analysis runs, **Then** peak timing and magnitude are still reported (load attribution noted as unavailable)

## Out of Scope

- Real-time demand monitoring and alerts (requires `subscribe_events`)
- Direct appliance scheduling via smart plug timers
- Integration with utility APIs for actual tariff data
- Three-phase power analysis
- Power factor / reactive power analysis
