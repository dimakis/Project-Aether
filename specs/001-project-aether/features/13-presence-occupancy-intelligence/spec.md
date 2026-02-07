# Feature 13: Presence & Occupancy Intelligence

## Status: Proposed

## Summary

Enable the Data Scientist to analyze motion sensors, door sensors, and device trackers to map room occupancy patterns, identify energy waste in unoccupied rooms, and suggest presence-based automations.

## Problem Statement

Many smart homes have motion sensors, door contacts, and presence detection but don't leverage this data beyond simple motion-activated lights. Cross-referencing occupancy data with energy consumption reveals significant waste — lights, heating, and appliances running in empty rooms. Users lack visibility into their occupancy patterns and the energy cost of those patterns.

## User Experience

### Flow 1: "Where am I wasting energy?"

```
You: "Am I wasting energy in empty rooms?"

  → Architect delegates to Data Scientist (analysis_type: presence_energy_waste)
  → DS discovers motion sensors, maps them to rooms/areas
  → DS fetches motion history + light/climate states for each room
  → Sandbox: overlay occupancy windows with energy consumption per room

  "📊 **Occupancy vs Energy Waste Report** (last 7 days)

   🟡 **Guest Room**: Lights on 6.2 hrs/day, occupied 12 min/day — 98% waste
      → 4.3 kWh/week wasted. Suggestion: motion-based lighting.
   🟡 **Office**: Heater runs midnight-6 AM, zero motion after 7 PM — overnight waste
      → 8.1 kWh/week wasted. Suggestion: occupancy-based heating schedule.
   🟢 **Living Room**: Good correlation — energy use tracks occupancy well.
   🔴 **Hallway**: Light on 24/7, motion only detected 45 min/day
      → Suggestion: motion-activated with 5-min timeout."
```

### Flow 2: "When is each room usually occupied?"

```
You: "Show me my occupancy patterns"

  → DS builds occupancy heatmap per room per hour
  → Sandbox: generate hourly occupancy probability matrix

  "🏠 **Room Occupancy Patterns** (weekdays, last 30 days)

   | Room        | 6-8 AM | 8-12 PM | 12-2 PM | 2-6 PM | 6-10 PM | 10 PM+ |
   |-------------|--------|---------|---------|--------|---------|--------|
   | Kitchen     | 🟢 85% | 🟡 20% | 🟢 70% | 🟡 15% | 🟢 90%  | ⚪ 5%  |
   | Living Room | ⚪ 10% | 🟡 30% | 🟡 25% | 🟡 40% | 🟢 95%  | 🟡 30% |
   | Office      | ⚪ 5%  | 🟢 90% | 🟢 80% | 🟢 85% | 🟡 20%  | ⚪ 0%  |
   | Bedroom     | 🟡 40% | ⚪ 5%  | ⚪ 2%  | ⚪ 3%  | 🟡 30%  | 🟢 95% |

   Weekend patterns differ significantly — office drops to 15%, 
   living room peaks earlier at 10 AM."
```

### Flow 3: "Is anyone home?"

```
You: "How can you tell if the house is empty?"

  → DS analyzes all presence indicators to build a "home/away" model
  → Identifies which sensors are most reliable for presence detection

  "Based on your sensor data, I can determine home/away status using:
   1. device_tracker.phone_john (primary — 98% reliable)
   2. binary_sensor.front_door (secondary — entry/exit events)
   3. Motion sensor activity aggregate (fallback)
   
   You're typically away Mon-Fri 8:30 AM - 5:45 PM.
   Suggestion: Create a home/away automation that adjusts heating,
   lights, and security based on this pattern."
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `PRESENCE_ENERGY_WASTE` | "wasting energy", "empty rooms", "occupancy waste" | Cross-reference occupancy with energy |
| `OCCUPANCY_PATTERNS` | "occupancy", "when are rooms used", "room usage" | Build occupancy heatmaps per room |
| `HOME_AWAY_DETECTION` | "anyone home", "away mode", "presence detection" | Model home/away state from sensors |

## Data Sources

### Required Entities

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `binary_sensor` | `motion` | Room-level occupancy detection |

### Optional Entities (enrich analysis)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `binary_sensor` | `door` | Entry/exit events |
| `binary_sensor` | `occupancy` | Dedicated occupancy sensors |
| `device_tracker` | — | Phone/person presence |
| `person` | — | Person entity (home/not_home) |
| `light` | — | Light state to cross-reference with occupancy |
| `climate` | — | HVAC state to cross-reference with occupancy |
| `sensor` | `power` / `energy` | Per-room energy to quantify waste |

### MCP Tools Used

- `list_entities` — discover motion, door, occupancy, device_tracker entities
- `get_history` — fetch state histories for occupancy correlation
- `get_entity` — get area_id to map sensors to rooms

## Room Mapping Strategy

Sensors must be mapped to rooms/areas for meaningful analysis:

1. **Primary**: Use `area_id` from entity attributes (most reliable)
2. **Fallback**: Parse entity_id naming convention (e.g., `binary_sensor.kitchen_motion`)
3. **Manual**: Allow user to specify room-sensor mapping via analysis options

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `OCCUPANCY_WASTE` | "Guest room: 6h lights, 12min occupancy — 98% energy waste" |
| `OCCUPANCY_PATTERN` | "Office occupied Mon-Fri 8 AM-6 PM, empty weekends" |
| `PRESENCE_DETECTION` | "Home/away detection possible with 95% accuracy using phone + door" |

## Automation Suggestions

- Motion-based lighting per room with optimized timeout values (derived from typical visit duration)
- Occupancy-based HVAC scheduling (heat only when room is typically occupied)
- Home/away mode automation (adjust heating, security, lights on departure/arrival)
- "Last person left" automation (all motion quiet for N minutes → away mode)

## Implementation Notes

### New AnalysisType Values

```python
PRESENCE_ENERGY_WASTE = "presence_energy_waste"
OCCUPANCY_PATTERNS = "occupancy_patterns"
HOME_AWAY_DETECTION = "home_away_detection"
```

### New InsightType Values

```python
OCCUPANCY_WASTE = "occupancy_waste"
OCCUPANCY_PATTERN = "occupancy_pattern"
PRESENCE_DETECTION = "presence_detection"
```

### Occupancy Inference from Motion Sensors

Motion sensors report `on` when motion detected, `off` after a timeout. To infer "room occupied":

```python
# In sandbox script:
# 1. Parse motion sensor state changes
# 2. Consider "occupied" = motion detected within last N minutes
# 3. Build occupancy windows: [(start, end), ...]
# 4. Aggregate into hourly probability matrix
OCCUPANCY_TIMEOUT_MINUTES = 10  # Configurable
```

### Energy Waste Quantification

```python
# For each room:
# 1. Get occupancy windows from motion data
# 2. Get energy-consuming entity states (lights, HVAC)
# 3. Calculate: waste = energy consumed while room unoccupied
# 4. Estimate monthly cost of waste
```

## Acceptance Criteria

1. **Given** motion sensors in multiple rooms, **When** occupancy pattern analysis runs, **Then** a per-room hourly occupancy matrix is produced
2. **Given** motion sensors and light entities in the same area, **When** presence energy waste analysis runs, **Then** waste hours and kWh are quantified per room
3. **Given** device_tracker and door sensors, **When** home/away analysis runs, **Then** a reliable presence model is identified
4. **Given** high-waste rooms detected, **When** analysis completes, **Then** automation suggestions with specific timeout values are produced
5. **Given** rooms without area_id mapping, **When** analysis runs, **Then** entity_id name parsing is used as fallback

## Out of Scope

- Real-time occupancy tracking / live dashboard
- Camera-based occupancy (privacy concerns)
- Multi-person room counting (motion sensors are binary)
- Geofencing setup (relies on existing device_tracker)
