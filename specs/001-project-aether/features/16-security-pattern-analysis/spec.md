# Feature 16: Security Pattern Analysis

## Status: Proposed

## Summary

Enable the Data Scientist to analyze door sensors, window sensors, lock states, and motion detectors to identify security gaps, routine vulnerabilities, and suggest security-hardening automations.

## Problem Statement

Smart home security hardware generates a wealth of data — door open/close events, lock/unlock states, motion patterns, window contacts — but most users only get real-time notifications. They lack insight into their security routines: Are doors consistently locked at night? Are windows left open when nobody's home? Is there a pattern of forgetting the back door? This analysis turns raw security data into actionable habits and automations.

## User Experience

### Flow 1: "Check my security patterns"

```
You: "Are there any security gaps in my routine?"

  → DS discovers door, window, lock, and motion entities
  → DS fetches 14 days of history
  → Sandbox: pattern analysis, gap detection, routine scoring

  "🔒 **Security Pattern Report** (last 14 days)

   ❌ **Back Door** (lock.back_door)
      Unlocked after 10 PM on 9 of 14 nights (64%)
      Average lock time when locked: 11:47 PM
      → Suggestion: Auto-lock at 10 PM

   ⚠️ **Side Window** (binary_sensor.side_window)
      Left open overnight on 3 occasions
      Left open while house was empty (away) on 2 occasions
      → Suggestion: Alert when open + no motion for 30 min

   ✅ **Front Door** (lock.front_door)
      Consistently locked by 9:30 PM (100% of nights)
      Average lock-to-unlock: 10.2 hours — good routine

   ✅ **Garage Door** (cover.garage_door)
      Closed by 8 PM every night. No gaps detected.

   🏠 **Overall Security Score: 7/10**
   Main gap: back door locking discipline"
```

### Flow 2: "What happens when I leave?"

```
You: "Is my house secure when I leave for work?"

  → DS correlates departure events with security entity states
  → Sandbox: departure-state analysis

  "🚪 **Departure Security Check** (last 14 departures)

   When you leave (detected via device_tracker):
   ✅ Front door: locked within 2 min on 14/14 departures
   ⚠️ Back door: unlocked on 4/14 departures (29%)
   ⚠️ Garage: left open on 2/14 departures (14%)
   ✅ All windows: closed on 13/14 departures

   💡 Suggestion: Create a 'leaving home' automation that:
   1. Locks all doors
   2. Closes garage
   3. Checks all windows (alert if open)
   4. Arms alarm system"
```

### Flow 3: "Unusual activity detection"

```
You: "Has there been any unusual activity?"

  → DS analyzes motion patterns against established baselines
  → Detects deviations from normal occupancy patterns

  "🔍 **Activity Anomalies** (last 7 days)

   ⚠️ Motion detected in garage at 3:12 AM on Tuesday
      (typical garage motion: 7 AM-9 PM only)
   
   ⚠️ Front door opened at 2:45 AM on Thursday
      (typical: no door events between 11 PM-6 AM)
   
   ✅ All other motion patterns within normal ranges.
   
   No action required if these were you — but consider a notification
   automation for off-hours door/motion events."
```

## Analysis Types

| Type | Trigger Phrases | What It Does |
|------|----------------|--------------|
| `SECURITY_PATTERNS` | "security", "security gaps", "locking habits" | Full security routine audit |
| `DEPARTURE_SECURITY` | "when I leave", "house secure", "away security" | Departure state analysis |
| `ACTIVITY_ANOMALIES` | "unusual activity", "strange motion", "night activity" | Off-baseline motion/door events |

## Data Sources

### Required Entities (at least some)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `binary_sensor` | `door` | Door open/close events |
| `lock` | — | Lock/unlock state |

### Optional Entities (enrich analysis)

| Domain | Device Class | Purpose |
|--------|-------------|---------|
| `binary_sensor` | `window` | Window open/close |
| `binary_sensor` | `motion` | Motion for occupancy context |
| `cover` | `garage_door` | Garage door state |
| `device_tracker` | — | Home/away for departure analysis |
| `person` | — | Presence detection |
| `alarm_control_panel` | — | Alarm arm/disarm state |
| `binary_sensor` | `vibration` | Vibration/tamper detection |

### MCP Tools Used

- `list_entities` — discover security-related entities
- `get_history` — fetch door/lock/window state histories
- `get_entity` — attributes (device_class, area_id)

## Insight Types Produced

| Insight Type | Example |
|-------------|---------|
| `SECURITY_GAP` | "Back door unlocked after 10 PM on 64% of nights" |
| `SECURITY_ROUTINE` | "Front door consistently locked by 9:30 PM — good routine" |
| `DEPARTURE_VULNERABILITY` | "Back door left unlocked on 29% of departures" |
| `ACTIVITY_ANOMALY` | "Off-hours motion in garage at 3:12 AM — unusual" |

## Automation Suggestions

- Auto-lock doors at a specific time (derived from the user's typical lock time)
- "Leaving home" routine: lock all doors, close garage, check windows
- "Bedtime" routine: lock doors, close garage, arm alarm
- Alert when door/window left open for extended period
- Alert for off-hours motion or door events
- Alert when a door is unlocked while house is in "away" mode

## Security Score Model

Score the home on a 1-10 scale based on:

| Factor | Weight | Scoring |
|--------|--------|---------|
| Night lock compliance | 30% | % of nights all doors locked by target time |
| Departure lock compliance | 25% | % of departures with all doors locked |
| Window management | 20% | % of away/night periods with all windows closed |
| Garage discipline | 15% | % of nights garage closed |
| Off-hours anomalies | 10% | Inverse of anomaly frequency |

## Implementation Notes

### New AnalysisType Values

```python
SECURITY_PATTERNS = "security_patterns"
DEPARTURE_SECURITY = "departure_security"
ACTIVITY_ANOMALIES = "activity_anomalies"
```

### New InsightType Values

```python
SECURITY_GAP = "security_gap"
SECURITY_ROUTINE = "security_routine"
DEPARTURE_VULNERABILITY = "departure_vulnerability"
ACTIVITY_ANOMALY = "activity_anomaly"
```

### Night Period Definition

```python
# Configurable via analysis options
NIGHT_START = "22:00"  # 10 PM
NIGHT_END = "06:00"    # 6 AM
```

### Departure Detection

```python
# Use person/device_tracker state changes:
# home → not_home = departure event
# Capture all security entity states at departure time ± 5 minutes
```

## Acceptance Criteria

1. **Given** door lock entities, **When** security pattern analysis runs, **Then** per-door nightly lock compliance percentage is reported
2. **Given** device_tracker + lock entities, **When** departure security runs, **Then** lock state at each departure is reported
3. **Given** motion sensor baselines, **When** activity anomaly analysis runs, **Then** off-baseline events are flagged with timestamps
4. **Given** security gaps detected, **When** analysis completes, **Then** specific automation suggestions are produced
5. **Given** all security factors scored, **When** analysis completes, **Then** an overall security score (1-10) is reported

## Out of Scope

- Camera feed analysis (video/image processing)
- Integration with professional security monitoring services
- Real-time intrusion detection (requires `subscribe_events`)
- Neighborhood crime data correlation
