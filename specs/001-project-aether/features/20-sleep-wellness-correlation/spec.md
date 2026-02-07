# Feature 20: Sleep & Wellness Environment Correlation

## Status: Proposed

## Summary

Enable the Data Scientist to analyze bedroom environmental conditions (temperature, humidity, CO2, light, noise) and correlate them with sleep patterns inferred from motion sensors, bed occupancy sensors, or sleep tracker data to provide actionable recommendations for better sleep.

## Problem Statement

Sleep quality is heavily influenced by bedroom environment — temperature, humidity, air quality, light, and noise. Many smart home users have sensors for all of these but no way to correlate environmental conditions with their actual sleep patterns. They might not realize that their bedroom CO2 reaches 1500 ppm by 3 AM (closed room, no ventilation), or that street noise correlates with restless periods.

## User Experience

### Flow 1: "How's my sleep environment?"

```
You: "Analyze my bedroom environment for sleep quality"

  → DS discovers bedroom sensors (temperature, humidity, CO2, light)
  → DS fetches 14 nights of data
  → Sandbox: environmental scoring during sleep windows

  "🌙 **Sleep Environment Report** (last 14 nights)

   🌡️ **Temperature**: 22.8°C average during sleep
      Optimal: 18-20°C — ⚠️ Your bedroom is 3°C too warm
      Recommendation: Lower thermostat to 19°C at bedtime

   💨 **CO2**: Rises from 450 ppm at bedtime to 1,450 ppm by 4 AM
      Optimal: <1,000 ppm — ❌ Exceeds threshold for 5+ hours nightly
      Recommendation: Open window slightly, or run ventilation on timer

   💧 **Humidity**: 52% average — ✅ Within optimal range (40-60%)

   💡 **Light**: 0.2 lux average — ✅ Sufficiently dark
      ⚠️ Spikes to 15 lux at 5:30 AM (sunrise through curtains)
      Recommendation: Blackout curtains or smart blinds

   🔊 **Noise**: No noise sensor detected. Consider adding one.

   🏆 **Sleep Environment Score: 6/10**
   Main issues: temperature (too warm) and CO2 (poor ventilation)"
```

### Flow 2: "Why do I sleep badly on weeknights?"

```
You: "I feel like I sleep worse on weeknights"

  → DS compares weeknight vs weekend environmental conditions
  → DS correlates with motion patterns (restlessness proxy)

  "🔍 **Weeknight vs Weekend Sleep Analysis**

   📊 **Environmental differences**:
   | Factor | Weeknights | Weekends | Difference |
   |--------|-----------|----------|------------|
   | Bedtime temp | 23.5°C | 21.2°C | +2.3°C |
   | CO2 at 3 AM | 1,580 ppm | 1,120 ppm | +460 ppm |
   | Lights off | 11:15 PM | 12:30 AM | -75 min |
   | First motion | 6:15 AM | 8:45 AM | -150 min |
   
   📈 **Motion analysis** (restlessness proxy):
   Weeknight motion events (11 PM-6 AM): 12.3 avg
   Weekend motion events: 7.8 avg — 37% less restless
   
   💡 **Key finding**: Weeknight CO2 is 41% higher — likely because
   you close the window on weeknights (heating season). The combination
   of higher temp + CO2 correlates with more restlessness.
   
   Suggestion: Run bedroom ventilation on a timer (10 min every 2 hours)
   or crack the window with a reduced heating setpoint."
```

### Flow 3: Proactive scheduled insight

```
Weekly scheduled insight (Monday 8 AM):

  "🌙 **Weekly Sleep Environment Summary**

   Average sleep environment score: 7/10 (up from 6/10 last week)
   ✅ Temperature improved after you lowered the thermostat
   ⚠️ CO2 still exceeds 1,000 ppm on 5 of 7 nights
   
   Best night: Saturday (score 9/10 — window open, cool temp, low CO2)
   Worst night: Wednesday (score 4/10 — 24°C, 1,650 ppm CO2)"
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `SLEEP_ENVIRONMENT` | "sleep quality", "bedroom environment", "sleep" | Full sleep environment audit |
| `SLEEP_COMPARISON` | "weeknight vs weekend", "sleep differences" | Compare sleep across periods |
| `SLEEP_TREND` | "sleep trend", "sleep getting worse/better" | Track environment score over time |

## Data Sources

### Required Entities (at least temperature + motion in bedroom)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `temperature` | Bedroom temperature (in bedroom area) |
| `binary_sensor` | `motion` | Bedroom motion (restlessness proxy) |

### Optional Entities (enrich analysis)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `sensor` | `humidity` | Bedroom humidity |
| `sensor` | `co2` / `carbon_dioxide` | Air quality |
| `sensor` | `pm25` / `pm10` | Particulate matter |
| `sensor` | `voc` / `volatile_organic_compounds` | VOC levels |
| `sensor` | `illuminance` | Light levels |
| `sensor` | `noise` / `sound_level` | Noise levels |
| `binary_sensor` | `occupancy` | Bed occupancy sensor |
| `sensor` | — | Sleep tracker data (Withings, etc.) |
| `climate` | — | Bedroom HVAC for temperature control |
| `cover` | — | Blinds/curtains for light control |
| `fan` | — | Ventilation for air quality |

### Room Identification

The analysis must identify "bedroom" sensors. Strategy:
1. Filter by `area_id` matching bedroom areas (primary)
2. Filter by entity_id containing `bedroom`, `bed_room`, `master`
3. Allow user to specify bedroom entity_ids via analysis options

### MCP Tools Used

- `list_entities` — discover bedroom environmental sensors
- `get_history` — fetch overnight sensor data
- `get_entity` — attributes (area_id, device_class)

## Sleep Window Detection

Determine when the user is sleeping (without a dedicated sleep sensor):

```python
# Heuristic from motion sensor:
# 1. Sleep start = last motion event before a gap > 30 min (after 9 PM)
# 2. Sleep end = first motion event after a gap > 30 min (before noon)
# 3. Restlessness = count of motion events during sleep window
#
# If bed occupancy sensor exists:
# 1. Sleep start = bed sensor → occupied
# 2. Sleep end = bed sensor → not occupied
```

## Sleep Environment Scoring

| Factor | Optimal Range | Weight | Source |
|--------|---------------|--------|--------|
| Temperature | 18-20°C | 25% | Sleep research consensus |
| CO2 | <1,000 ppm | 25% | WHO indoor air quality guidelines |
| Humidity | 40-60% | 15% | ASHRAE standards |
| Light | <1 lux | 15% | Sleep medicine research |
| Noise | <30 dB | 10% | WHO night noise guidelines |
| Air quality (PM/VOC) | PM2.5 <15 µg/m³ | 10% | WHO air quality guidelines |

Score = weighted average of per-factor scores (0-10 scale).

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `SLEEP_ENVIRONMENT` | "Sleep environment score: 6/10. CO2 and temperature are key issues" |
| `SLEEP_CO2_ALERT` | "Bedroom CO2 exceeds 1,000 ppm for 5+ hours nightly" |
| `SLEEP_TEMPERATURE` | "Bedroom is 3°C above optimal sleep temperature" |
| `SLEEP_COMPARISON` | "Weekend sleep environments score 30% better than weeknights" |

## Automation Suggestions

- Lower thermostat to 19°C at bedtime, raise at wake time
- Run ventilation on a timer during sleep hours (every 2 hours for 10 min)
- Close smart blinds at sunset, open at wake time
- Turn on fan/ventilation when CO2 exceeds threshold
- Gradually dim lights in the hour before typical bedtime

## Implementation Notes

### New AnalysisType Values

```python
SLEEP_ENVIRONMENT = "sleep_environment"
SLEEP_COMPARISON = "sleep_comparison"
SLEEP_TREND = "sleep_trend"
```

### New InsightType Values

```python
SLEEP_ENVIRONMENT = "sleep_environment"
SLEEP_CO2_ALERT = "sleep_co2_alert"
SLEEP_TEMPERATURE = "sleep_temperature"
SLEEP_COMPARISON = "sleep_comparison"
```

## Acceptance Criteria

1. **Given** bedroom temperature + motion sensors, **When** sleep environment analysis runs, **Then** a per-night environment score is produced
2. **Given** CO2 sensor in bedroom, **When** analysis detects >1,000 ppm for >2 hours, **Then** a CO2 alert insight is generated
3. **Given** 14+ nights of data, **When** weeknight vs weekend comparison runs, **Then** environmental differences are quantified
4. **Given** actionable issues found, **When** analysis completes, **Then** specific automation suggestions are produced
5. **Given** only temperature + motion sensors, **When** analysis runs, **Then** partial scoring works with available factors only

## Out of Scope

- Medical sleep quality assessment (not a medical device)
- Integration with clinical sleep studies
- Circadian rhythm optimization (complex biology)
- Smart mattress / sleep tracker data import (varies by vendor)
- Real-time alerts during sleep (requires `subscribe_events`)
