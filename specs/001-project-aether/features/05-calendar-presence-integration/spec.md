# Feature: Calendar & Presence Integration

**Status**: Not Started  
**Priority**: P3  
**User Story**: US7  
**Depends on**: US1 (Entity Discovery), US2 (Architect)

## Goal

Enable agents to access calendar events, track person locations, and manage zones to create context-aware automations based on schedules and presence.

## Description

Home Assistant integrates with calendars (Google, CalDAV, local) and tracks person presence via device trackers. This feature exposes these capabilities to agents, enabling:

- **Calendar Access**: Read upcoming events, check availability, create calendar-triggered automations
- **Person Tracking**: Know who's home, who's away, arrival/departure detection
- **Zone Management**: Create/manage zones (Work, Gym, School), track zone entry/exit
- **Schedule Awareness**: Agent understands household schedules and adapts automations

## Example Use Cases

### 1. Calendar-Aware Automations
**User**: "Don't turn on the coffee maker if I have a meeting before 8 AM"
**Agent**:
- Checks calendar for early meetings
- Creates automation with calendar condition
- Coffee maker only triggers if no meeting found

### 2. Smart Arrival Preparation
**User**: "When anyone comes home, turn on the porch light"
**Agent**:
- Identifies all person entities
- Creates zone-based trigger for "home" zone
- Sets up light automation with presence condition

### 3. Away Mode Based on Calendar
**User**: "Enable away mode when we're on vacation"
**Agent**:
- Checks calendar for events labeled "vacation" or "trip"
- Creates input_boolean for away_mode
- Links calendar events to away_mode toggle
- Creates automations that respect away_mode

### 4. Commute-Aware Heating
**User**: "Start heating 30 minutes before I usually get home"
**Agent**:
- Analyzes person entity history for arrival patterns
- Creates automation triggered by zone exit from "Work"
- Accounts for typical commute time
- Pre-heats home before arrival

### 5. Meeting Room Preparation
**User**: "Prepare the office when I have a work-from-home meeting"
**Agent**:
- Monitors calendar for events with "WFH" or "remote" keywords
- Creates automation: lights to meeting brightness, close blinds, AC to comfortable temp
- Activates 5 minutes before meeting start

### 6. Kid Schedule Tracking
**User**: "Remind me when the kids should be home from school"
**Agent**:
- Creates zone for "School"
- Tracks kids' phone device trackers
- Creates notification automation for expected arrival window
- Alerts if not home by expected time

## Independent Test

Agent can query calendar events, determine who's home, create a zone, and build an automation that triggers based on calendar + presence conditions.

## REST API Endpoints Required

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/calendars` | GET | List all calendar entities |
| `/api/calendars/{entity_id}` | GET | Get calendar events for date range |
| `/api/states/person.*` | GET | Get person states (home/away) |
| `/api/states/device_tracker.*` | GET | Get device tracker states |
| `/api/states/zone.*` | GET | Get zone states |
| `/api/config/zone/config` | GET | List zone configurations |
| `/api/config/zone/config/{zone_id}` | POST | Create/update zone |
| `/api/config/zone/config/{zone_id}` | DELETE | Delete zone |

## Data Structures

### Calendar Event
```python
CalendarEvent:
  summary: str          # Event title
  start: datetime       # Start time
  end: datetime         # End time
  location: str | None  # Location if set
  description: str | None
  all_day: bool
```

### Person State
```python
PersonState:
  entity_id: str        # person.john
  state: str            # home, away, zone_name
  source: str           # Device tracker providing state
  latitude: float
  longitude: float
  gps_accuracy: int
```

### Zone
```python
Zone:
  id: str
  name: str
  latitude: float
  longitude: float
  radius: float         # meters
  icon: str
  passive: bool         # Don't trigger automations
```

## Acceptance Criteria

1. **Given** a connected calendar, **When** agent queries events, **Then** it receives events for specified date range
2. **Given** person entities, **When** agent checks presence, **Then** it accurately reports who's home/away
3. **Given** user coordinates, **When** agent creates zone, **Then** zone appears in HA and triggers work
4. **Given** calendar event condition, **When** used in automation, **Then** automation respects calendar state
5. **Given** presence trigger, **When** person enters/leaves zone, **Then** automation fires correctly

## Privacy Considerations

- Calendar data may contain sensitive information
- Location tracking raises privacy concerns
- All presence data should be handled per Constitution privacy principles
- User must explicitly enable calendar/presence features

## HITL Requirements

- Creating zones requires approval (involves coordinates)
- Accessing calendar requires user consent
- Presence-based automations show which persons are tracked

## Related Features

- **US3 Energy Optimization**: Can optimize based on occupancy patterns
- **US5 Intelligent Optimization**: Correlates presence with usage patterns
- **Dashboard Generation**: Can show presence status on dashboards
