# Feature 21: Carbon Footprint Estimation

## Status: Proposed

## Summary

Enable the Data Scientist to estimate household carbon emissions from energy consumption data using grid carbon intensity factors, track trends over time, and suggest reduction strategies. Optionally integrate with solar production to show net carbon impact.

## Problem Statement

Many environmentally conscious smart home users want to understand their carbon footprint but have no way to translate their kWh consumption into CO2 emissions. The calculation requires knowing the carbon intensity of the local electricity grid, which varies by region and time of day. Home Assistant has the energy data; this feature adds the carbon context.

## User Experience

### Flow 1: "What's my carbon footprint?"

```
You: "What's my household carbon footprint?"

  → DS collects energy consumption data
  → DS applies grid carbon intensity factors
  → Sandbox: emissions calculation, breakdown, trend analysis

  "🌍 **Carbon Footprint Report** (last 30 days)

   📊 Total electricity consumption: 520 kWh
   🏭 Estimated CO2 emissions: 234 kg CO2e
   📏 Daily average: 7.8 kg CO2e/day
   
   ☀️ Solar offset: -189 kWh self-consumed
      → Avoided emissions: 85 kg CO2e
   
   🌱 **Net carbon footprint: 149 kg CO2e**

   📊 **Breakdown by usage category**:
   | Category | kWh | CO2 (kg) | % of Total |
   |----------|-----|----------|------------|
   | Heating/cooling | 245 | 110 | 47% |
   | EV charging | 120 | 54 | 23% |
   | Appliances | 95 | 43 | 18% |
   | Lighting | 35 | 16 | 7% |
   | Other | 25 | 11 | 5% |

   📈 **Trend**: Down 12% vs last month (milder weather + solar increase)
   
   💡 Your biggest reduction opportunity: Shift EV charging to midday
   (solar hours) to avoid 54 kg CO2e/month from grid charging."
```

### Flow 2: "Track my carbon trend"

```
You: "How has my carbon footprint changed over the past 6 months?"

  → DS fetches monthly energy totals
  → Sandbox: monthly emissions calculation, trend line

  "📈 **6-Month Carbon Trend**

   | Month | kWh | CO2 (kg) | Trend |
   |-------|-----|----------|-------|
   | Sep | 380 | 171 | — |
   | Oct | 420 | 189 | 📈 +11% |
   | Nov | 510 | 230 | 📈 +22% (heating season) |
   | Dec | 580 | 261 | 📈 +13% |
   | Jan | 550 | 248 | 📉 -5% |
   | Feb (proj.) | 520 | 234 | 📉 -6% |

   📊 6-month total: 2,960 kWh → 1,333 kg CO2e
   🌱 Annualized: ~2,666 kg CO2e/year
   
   For context, the average European household emits ~2,500 kg CO2e/year
   from electricity. You're slightly above average, mainly due to
   EV charging (which replaces petrol — net positive!)."
```

### Flow 3: "What if I change my energy mix?"

```
You: "How much carbon would I save if I added a battery?"

  → DS models scenarios based on current consumption + solar
  → Sandbox: scenario comparison

  "🔋 **Battery Impact Scenario**

   Current situation:
   - Grid import: 331 kWh/month at peak carbon intensity
   - CO2: 149 kg/month (net of solar)
   
   With 10 kWh battery:
   - Store solar surplus → use in evening instead of grid
   - Estimated grid import reduction: -45% (182 kWh saved)
   - New CO2: 67 kg/month (net)
   
   🌱 **Annual carbon saving: ~984 kg CO2e**
   
   Payback period at current energy prices: ~6.5 years
   Carbon payback (battery manufacturing): ~2.1 years"
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `CARBON_FOOTPRINT` | "carbon footprint", "CO2 emissions", "carbon" | Current emissions estimate with breakdown |
| `CARBON_TREND` | "carbon trend", "emissions over time" | Monthly emissions trend |
| `CARBON_SCENARIOS` | "reduce carbon", "what if", "battery impact" | Model emission reduction scenarios |

## Data Sources

### Required Entities

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `energy` | Total energy consumption |

### Optional Entities (enrich analysis)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `energy` (per-appliance) | Category breakdown |
| `sensor` | `energy` (solar) | Solar production offset |
| `sensor` | `energy` (grid import/export) | Net grid usage |
| `sensor` | `gas` | Gas consumption for combined footprint |

### Carbon Intensity Data

Grid carbon intensity varies by country, region, and time of day. Configuration approach:

#### Option A: Static Configuration (MVP)

```json
{
  "grid_carbon_intensity_gco2_per_kwh": 450,
  "country": "US",
  "region": "California"
}
```

Default values by country (2024 averages):

| Country | g CO2e/kWh | Source |
|---------|-----------|--------|
| Norway | 29 | IEA |
| France | 56 | IEA |
| UK | 207 | IEA |
| Germany | 350 | IEA |
| US (avg) | 390 | EPA |
| US (CA) | 210 | EPA |
| Australia | 560 | IEA |
| Poland | 640 | IEA |

#### Option B: Time-Varying (future enhancement)

Integrate with APIs like [Electricity Maps](https://www.electricitymaps.com/), [Carbon Intensity UK](https://carbonintensity.org.uk/), or [WattTime](https://www.watttime.org/) for real-time grid carbon intensity. This would enable carbon-aware scheduling (run high-load appliances when the grid is cleanest).

### MCP Tools Used

- `list_entities` — discover energy sensors
- `get_history` — fetch consumption timeseries
- `get_entity` — attributes (device_class, unit)

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `CARBON_FOOTPRINT` | "Monthly emissions: 234 kg CO2e. Heating is 47% of total" |
| `CARBON_TREND` | "Emissions down 12% vs last month" |
| `CARBON_REDUCTION` | "Shifting EV charging to solar hours saves 54 kg CO2e/month" |
| `CARBON_BENCHMARK` | "Your household is slightly above the national average" |

## Automation Suggestions

- Carbon-aware EV charging (charge when grid carbon intensity is lowest)
- Shift flexible loads to low-carbon time windows
- Alert when daily/weekly emissions exceed target
- Solar surplus notifications (use solar now to avoid grid carbon)

## Implementation Notes

### New AnalysisType Values

```python
CARBON_FOOTPRINT = "carbon_footprint"
CARBON_TREND = "carbon_trend"
CARBON_SCENARIOS = "carbon_scenarios"
```

### New InsightType Values

```python
CARBON_FOOTPRINT = "carbon_footprint"
CARBON_TREND = "carbon_trend"
CARBON_REDUCTION = "carbon_reduction"
CARBON_BENCHMARK = "carbon_benchmark"
```

### Carbon Calculation

```python
# Basic calculation:
# CO2 (kg) = energy_kwh * grid_intensity_gco2_per_kwh / 1000
#
# With solar:
# net_grid_kwh = total_consumption - solar_self_consumed
# CO2 (kg) = net_grid_kwh * grid_intensity / 1000
#
# With gas:
# gas_CO2 (kg) = gas_m3 * 2.0  # ~2.0 kg CO2 per m³ natural gas
# total_CO2 = electricity_CO2 + gas_CO2
```

### Configuration in Settings

```python
# Added to src/settings.py
carbon_intensity_gco2_per_kwh: float = Field(
    default=390.0,
    description="Grid carbon intensity in gCO2e/kWh (default: US average)",
)
carbon_gas_factor_kgco2_per_m3: float = Field(
    default=2.0,
    description="Carbon factor for natural gas in kg CO2 per m³",
)
```

### Benchmarking Data

Embed simple benchmarks for context:

```python
HOUSEHOLD_BENCHMARKS_KG_CO2E_PER_YEAR = {
    "very_low": 500,    # "Excellent — minimal grid dependence"
    "low": 1500,        # "Good — efficient home"
    "average": 2500,    # "Average household"
    "high": 4000,       # "Above average — improvement opportunities"
    "very_high": 6000,  # "High — significant reduction potential"
}
```

## Acceptance Criteria

1. **Given** energy consumption sensors + configured carbon intensity, **When** footprint analysis runs, **Then** total CO2e with category breakdown is produced
2. **Given** solar production sensors, **When** analysis runs, **Then** solar offset is subtracted and net emissions reported
3. **Given** 3+ months of data, **When** trend analysis runs, **Then** monthly emissions are charted with trend direction
4. **Given** benchmark data, **When** analysis completes, **Then** the household is compared to regional/national average
5. **Given** no carbon intensity configured, **When** analysis runs, **Then** US average is used as default with a note to configure for accuracy

## Out of Scope

- Scope 2/3 emissions (transport, food, goods)
- Real-time carbon intensity API integration (future enhancement)
- Carbon offset purchasing integration
- Life cycle assessment of home appliances
- Gas consumption analysis without gas sensors
