# Tasks: Calendar & Presence Integration

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**User Story**: US7

---

## MCP Client Extensions

- [ ] T401 [US7] Add calendar methods to src/mcp/client.py:
  - `list_calendars()` - GET /api/calendars
  - `get_calendar_events(entity_id, start, end)` - GET /api/calendars/{entity_id}
  - `is_event_active(entity_id, event_filter)` - Check if matching event is active now

- [ ] T402 [US7] Add zone methods to src/mcp/client.py:
  - `list_zones()` - GET /api/states (filter zone.*)
  - `get_zone_config(zone_id)` - GET /api/config/zone/config/{zone_id}
  - `create_zone(name, lat, lon, radius, icon)` - POST zone config
  - `update_zone(zone_id, ...)` - POST update
  - `delete_zone(zone_id)` - DELETE zone

- [ ] T403 [US7] Add presence methods to src/mcp/client.py:
  - `list_persons()` - GET /api/states (filter person.*)
  - `get_person_state(person_id)` - Get detailed person state
  - `list_device_trackers()` - GET /api/states (filter device_tracker.*)
  - `get_device_tracker_state(tracker_id)` - Get tracker details
  - `who_is_home()` - Convenience: list persons with state=home

## Data Models

- [ ] T404 [US7] Create src/mcp/calendar.py with:
  - CalendarEvent dataclass (summary, start, end, location, description, all_day)
  - CalendarClient class wrapping calendar API calls
  - parse_calendar_event() - Parse HA calendar response
  - filter_events(events, keywords) - Filter by title/description

- [ ] T405 [US7] Create src/mcp/presence.py with:
  - PersonState dataclass (entity_id, state, source, lat, lon, accuracy)
  - ZoneConfig dataclass (id, name, lat, lon, radius, icon, passive)
  - PresenceClient class wrapping presence API calls
  - is_anyone_home() - Check if any person is home
  - get_household_presence() - Summary of all person states

## Agent Tools

- [ ] T406 [P] [US7] Create src/tools/calendar_tools.py:
  - `get_upcoming_events(calendar_id, hours)` - List next N hours of events
  - `check_calendar_availability(calendar_id, start, end)` - Is time slot free?
  - `find_events_by_keyword(calendar_id, keyword)` - Search events
  - `is_meeting_now(calendar_id)` - Check if in a meeting

- [ ] T407 [P] [US7] Create src/tools/presence_tools.py:
  - `who_is_home()` - List persons currently home
  - `get_person_location(person_id)` - Get person's current zone/state
  - `is_home_empty()` - Check if no one is home
  - `get_arrival_history(person_id, days)` - Recent arrival/departure times

- [ ] T408 [P] [US7] Create src/tools/zone_tools.py:
  - `create_zone(name, lat, lon, radius)` - Create new zone
  - `delete_zone(zone_id)` - Remove zone
  - `list_zones()` - List all zones with occupancy
  - `get_zone_occupants(zone_id)` - Who's in this zone?

- [ ] T409 [US7] Register calendar/presence tools in src/tools/__init__.py

## Context Providers

- [ ] T410 [US7] Create src/context/calendar_context.py:
  - CalendarContextProvider class
  - get_schedule_context(hours_ahead) - Summary of upcoming events
  - get_busy_periods(date) - List busy time slots
  - Inject into agent system prompts when relevant

- [ ] T411 [US7] Create src/context/presence_context.py:
  - PresenceContextProvider class
  - get_presence_context() - Who's home, recent changes
  - get_typical_schedule(person_id) - Inferred daily patterns
  - Inject into agent system prompts

## Automation Helpers

- [ ] T412 [US7] Create src/automation/calendar_triggers.py:
  - build_calendar_trigger(entity_id, event_filter, offset) - Trigger before/after event
  - build_calendar_condition(entity_id, event_filter) - Condition: event active
  - Example: trigger 10 min before meeting, condition: has "WFH" in title

- [ ] T413 [US7] Create src/automation/presence_triggers.py:
  - build_zone_trigger(person_id, zone_id, event) - Trigger on zone enter/leave
  - build_presence_condition(persons, state) - Condition: persons home/away
  - build_occupancy_trigger(zone_id, min_occupants) - Trigger when N people in zone

- [ ] T414 [US7] Update src/mcp/automation_deploy.py to support:
  - Calendar triggers (platform: calendar)
  - Zone triggers (platform: zone)
  - Person state conditions

## Database Models

- [ ] T415 [US7] Create Alembic migration alembic/versions/008_presence.py:
  - Add Zone table (id, ha_zone_id, name, lat, lon, radius, icon, passive)
  - Add PersonOccupancy table (person_id, zone_id, entered_at, left_at) for history

- [ ] T416 [US7] Create src/storage/entities/zone.py with Zone model
- [ ] T417 [US7] Create src/storage/entities/person_occupancy.py with occupancy history

## API Endpoints

- [ ] T418 [P] [US7] Create src/api/schemas/presence.py:
  - PersonResponse, ZoneResponse, OccupancyResponse
  - ZoneCreate, ZoneUpdate
  - CalendarEventResponse

- [ ] T419 [US7] Create src/api/routes/presence.py:
  - GET /presence - Current household presence
  - GET /presence/persons - List all persons with states
  - GET /presence/persons/{id}/history - Arrival/departure history
  - GET /presence/zones - List zones with occupancy

- [ ] T420 [US7] Create src/api/routes/zones.py:
  - GET /zones - List zones
  - POST /zones - Create zone (requires HITL)
  - PATCH /zones/{id} - Update zone
  - DELETE /zones/{id} - Delete zone

- [ ] T421 [US7] Create src/api/routes/calendars.py:
  - GET /calendars - List calendars
  - GET /calendars/{id}/events - Get events
  - GET /calendars/{id}/availability - Check availability

## CLI Commands

- [ ] T422 [US7] Add `aether presence` commands to src/cli/main.py:
  - `aether presence status` - Who's home now
  - `aether presence history` - Recent arrivals/departures
  - `aether presence zones` - List zones with occupants

- [ ] T423 [US7] Add `aether calendar` commands:
  - `aether calendar list` - List calendars
  - `aether calendar events <id> --hours 24` - Show upcoming events
  - `aether calendar check <id>` - Is there a meeting now?

- [ ] T424 [US7] Add `aether zones` commands:
  - `aether zones list` - List zones
  - `aether zones create <name> <lat> <lon> <radius>` - Create zone
  - `aether zones delete <id>` - Delete zone

## Tests

**Unit Tests**:
- [ ] T425 [P] [US7] Create tests/unit/test_mcp_calendar.py
- [ ] T426 [P] [US7] Create tests/unit/test_mcp_presence.py
- [ ] T427 [P] [US7] Create tests/unit/test_calendar_tools.py
- [ ] T428 [P] [US7] Create tests/unit/test_presence_tools.py
- [ ] T429 [P] [US7] Create tests/unit/test_zone_tools.py

**Integration Tests**:
- [ ] T430 [US7] Create tests/integration/test_calendar_context.py
- [ ] T431 [US7] Create tests/integration/test_presence_tracking.py
- [ ] T432 [US7] Create tests/integration/test_zone_automations.py

**E2E Tests**:
- [ ] T433 [US7] Create tests/e2e/test_calendar_automation.py - Create meeting-aware automation
- [ ] T434 [US7] Create tests/e2e/test_arrival_automation.py - Create arrival-triggered automation
