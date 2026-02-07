# Feature 18: Weather-Correlated Analysis

## Status: Proposed

## Summary

Enable the Data Scientist to cross-reference indoor sensor data and energy consumption with weather entities to explain anomalies, predict upcoming energy costs, and optimize HVAC pre-conditioning schedules.

## Problem Statement

"Why did my heating bill spike this week?" is a question that can only be answered by correlating indoor data with outdoor conditions. Users see energy spikes but can't easily attribute them to a cold snap, a heatwave, or a rainy period. Home Assistant's `weather.*` entities and outdoor temperature sensors provide the missing context, but no automated cross-referencing exists.

## User Experience

### Flow 1: "Why did my energy spike?"

```
You: "My energy usage was much higher this week. Why?"

  → Architect delegates to DS with energy + weather correlation
  → DS fetches energy history + weather history for the same period
  → Sandbox: regression analysis, weather impact quantification

  "📊 **Energy vs Weather Analysis** (this week vs last week)

   This week: 187 kWh consumed (+42% vs last week's 132 kWh)
   
   🌡️ **Weather impact explains ~85% of the increase:**
   - Average outdoor temp: 2°C (vs 9°C last week)
   - Heating degree days: 112 (vs 63 last week, +78%)
   - Your heating ran 14.2 hrs/day (vs 8.1 hrs/day)
   
   📈 Your home's heating coefficient: ~3.2 kWh per heating degree day
   This is within normal range for a home your size.
   
   ⚠️ Remaining 15% unexplained — possible causes:
   - Holiday period (more occupancy = more cooking/lighting)
   - Hot water usage increase"
```

### Flow 2: "Predict my energy costs"

```
You: "What will my energy cost be this week based on the forecast?"

  → DS uses historical consumption-vs-weather model
  → DS fetches weather forecast from weather entity
  → Sandbox: applies model to forecast

  "🔮 **Energy Cost Prediction** (next 7 days)

   Based on your consumption patterns and the weather forecast:
   
   | Day | Forecast | Predicted kWh | Est. Cost |
   |-----|----------|--------------|-----------|
   | Mon | 5°C, cloudy | 28 kWh | $7.84 |
   | Tue | 3°C, rain | 31 kWh | $8.68 |
   | Wed | -1°C, snow | 38 kWh | $10.64 |
   | Thu | 1°C, cloudy | 35 kWh | $9.80 |
   | Fri | 6°C, sunny | 26 kWh | $7.28 |
   | Sat | 8°C, sunny | 23 kWh | $6.44 |
   | Sun | 7°C, partly cloudy | 24 kWh | $6.72 |
   
   **Predicted weekly total: 205 kWh (~$57.40)**
   
   Wednesday will be the most expensive day. Consider pre-heating
   Tuesday evening during off-peak hours."
```

### Flow 3: "Optimize HVAC pre-conditioning"

```
You: "Should I pre-heat my house before peak hours?"

  → DS analyzes thermal inertia (how fast the house cools/heats)
  → DS models pre-heating strategy against weather forecast

  "🏠 **Thermal Analysis**

   Your home's thermal time constant: ~4.2 hours
   (loses 1°C every 4.2 hours with heating off at 5°C outdoor temp)
   
   💡 **Pre-heating strategy for tomorrow** (forecast: 2°C, peak 5-9 PM):
   - Heat to 23°C by 4:30 PM (30 min before peak)
   - Turn off heating during peak rate (5-9 PM)
   - Temperature will drop to ~21°C by 9 PM (still comfortable)
   - Resume heating at 9 PM at off-peak rate
   
   Estimated saving: $1.20/day vs continuous peak-rate heating"
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `WEATHER_ENERGY_CORRELATION` | "why energy spike", "weather impact", "heating vs cold" | Attribute energy changes to weather |
| `ENERGY_PREDICTION` | "predict energy", "forecast cost", "next week" | Model-based consumption prediction |
| `THERMAL_ANALYSIS` | "pre-heat", "thermal", "insulation", "heat loss" | Building thermal performance |

## Data Sources

### Required Entities

| Domain | Purpose |
|--------|---------|
| `weather` | Outdoor temperature, humidity, condition, forecast |
| `sensor` (energy/power) | Energy consumption data |

### Optional Entities

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `temperature` (outdoor) | More accurate outdoor readings than weather entity |
| `sensor` | `temperature` (indoor) | Room temperatures for thermal analysis |
| `climate` | — | HVAC runtime, mode, setpoint |
| `sensor` | `humidity` (outdoor) | Wind chill / heat index calculation |
| `sensor` | `illuminance` (outdoor) | Solar radiation correlation |

### MCP Tools Used

- `list_entities` — discover weather and outdoor sensor entities
- `get_history` — fetch weather + energy timeseries
- `get_entity` — weather forecast attributes (forecast array)

### Weather Entity Attributes

HA `weather.*` entities provide:
- `temperature` — current outdoor temp
- `humidity` — current outdoor humidity
- `wind_speed` — wind speed
- `forecast` — array of future conditions (daily/hourly depending on integration)

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `WEATHER_CORRELATION` | "85% of your energy increase correlates with the 7°C temperature drop" |
| `ENERGY_PREDICTION` | "Predicted: 205 kWh next week based on weather forecast" |
| `THERMAL_PERFORMANCE` | "Thermal time constant: 4.2 hours. Pre-heating saves $1.20/day" |
| `HEATING_COEFFICIENT` | "Your home uses 3.2 kWh per heating degree day" |

## Automation Suggestions

- Pre-heat/pre-cool based on weather forecast (start HVAC before peak rate)
- Adjust thermostat setpoint based on outdoor temperature (weather-compensated)
- Alert when weather conditions will cause energy spike
- Close blinds when outdoor temperature exceeds threshold (summer)

## Implementation Notes

### New AnalysisType Values

```python
WEATHER_ENERGY_CORRELATION = "weather_energy_correlation"
ENERGY_PREDICTION = "energy_prediction"
THERMAL_ANALYSIS = "thermal_analysis"
```

### New InsightType Values

```python
WEATHER_CORRELATION = "weather_correlation"
ENERGY_PREDICTION = "energy_prediction"
THERMAL_PERFORMANCE = "thermal_performance"
HEATING_COEFFICIENT = "heating_coefficient"
```

### Heating/Cooling Degree Days

```python
# Standard metric for weather-energy correlation
# Heating Degree Days (HDD) = max(0, base_temp - outdoor_temp) per day
# Cooling Degree Days (CDD) = max(0, outdoor_temp - base_temp) per day
BASE_TEMP_HEATING = 18.0  # °C (configurable)
BASE_TEMP_COOLING = 24.0  # °C (configurable)
```

### Thermal Time Constant Estimation

```python
# When HVAC turns off:
# 1. Find periods where HVAC is off and no windows/doors open
# 2. Fit exponential decay: T(t) = T_outdoor + (T_start - T_outdoor) * exp(-t/tau)
# 3. tau = thermal time constant (hours)
# Higher tau = better insulation
```

### Weather Forecast Access

```python
# Get forecast from weather entity attributes
weather = await mcp_client.get_entity_state("weather.home")
forecast = weather.get("attributes", {}).get("forecast", [])
# forecast = [{"datetime": "...", "temperature": 5, "condition": "cloudy"}, ...]
```

## Acceptance Criteria

1. **Given** energy sensors and weather entity, **When** correlation analysis runs, **Then** the percentage of energy variance explained by weather is calculated
2. **Given** 30+ days of energy + weather history, **When** prediction runs, **Then** next-week daily consumption is predicted with confidence intervals
3. **Given** indoor temperature sensors + HVAC + outdoor temp, **When** thermal analysis runs, **Then** the building's thermal time constant is estimated
4. **Given** pre-heating opportunity identified, **When** analysis completes, **Then** a specific schedule with cost saving estimate is produced
5. **Given** no weather entity configured, **When** weather analysis is requested, **Then** a clear message explains the requirement

## Out of Scope

- Integration with external weather APIs (relies on HA weather entities)
- Long-range (>7 day) weather predictions
- Building energy modeling (EnergyPlus / detailed simulation)
- Heating system sizing recommendations
