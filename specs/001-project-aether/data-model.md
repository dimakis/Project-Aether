# Data Model: Project Aether

**Feature Branch**: `001-project-aether`  
**Date**: 2026-02-03

## Overview

This document defines the core entities, their relationships, and state transitions for Project Aether. The model mirrors Home Assistant's internal architecture to expose **all HA primitives** to the agents.

## Implementation Status

The following table maps spec entities to their implementation status:

| Entity | Status | ORM Model |
|--------|--------|-----------|
| **Floor** | Not implemented | Area has nullable `floor_id` only |
| **Area** | Implemented | `src/storage/entities/area.py` |
| **Label** | Not implemented | — |
| **Category** | Not implemented | — |
| **Device** | Implemented | `src/storage/entities/device.py` |
| **Entity (HAEntity)** | Implemented | `src/storage/entities/ha_entity.py` |
| **ConfigEntry** | Not implemented | — |
| **Integration** | Not implemented | — |
| **Helper** | Not implemented | — |
| **Scene** | Implemented (partial) | `src/storage/entities/ha_scene.py` (entity_states null until MCP supports) |
| **Script** | Implemented (partial) | `src/storage/entities/ha_script.py` (sequence null until MCP supports) |
| **Service** | Implemented | `src/storage/entities/ha_service.py` |
| **Event** | Not implemented | — |
| **HAAutomation** | Implemented | `src/storage/entities/ha_automation.py` |
| **DiscoverySession** | Implemented | `src/storage/entities/discovery_session.py` |
| **Agent** | Implemented (expanded) | `src/storage/entities/agent.py` — includes config/prompt versioning (Feature 23) |
| **Conversation** | Implemented | `src/storage/entities/conversation.py` |
| **Message** | Implemented | `src/storage/entities/message.py` |
| **AutomationProposal** | Implemented | `src/storage/entities/automation_proposal.py` |
| **Insight** | Implemented | `src/storage/entities/insight.py` |
| **Dashboard** | Not implemented | — |
| **Checkpoint** | Implemented | `src/storage/checkpoints.py` (LangGraph managed) |

**Additional entities in codebase (not in original spec):**

| Entity | ORM Model | Purpose |
|--------|-----------|---------|
| **UserProfile** | `src/storage/entities/user_profile.py` | User accounts (password, Google OAuth) |
| **PasskeyCredential** | `src/storage/entities/passkey_credential.py` | WebAuthn passkey storage |
| **SystemConfig** | `src/storage/entities/system_config.py` | HA URL/token (encrypted), setup state |
| **HAZone** | `src/storage/entities/ha_zone.py` | HA zone connection configs |
| **InsightSchedule** | `src/storage/entities/insight_schedule.py` | Cron/webhook insight triggers |
| **LLMUsage** | `src/storage/entities/llm_usage.py` | Token counts, costs, latency per LLM call |
| **FlowGrade** | `src/storage/entities/flow_grade.py` | Conversation quality grades |

---

## Home Assistant Registry Hierarchy

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          HOME ASSISTANT CORE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        ORGANIZATIONAL REGISTRIES                     │   │
│   │                                                                      │   │
│   │   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │   │
│   │   │  Floor   │───>│   Area   │    │  Label   │    │ Category │     │   │
│   │   └──────────┘    └────┬─────┘    └──────────┘    └──────────┘     │   │
│   │                        │               │  tags          │          │   │
│   └────────────────────────│───────────────│────────────────│──────────┘   │
│                            │               │                │              │
│   ┌────────────────────────▼───────────────▼────────────────▼──────────┐   │
│   │                        DEVICE REGISTRY                              │   │
│   │                                                                      │   │
│   │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │   │
│   │   │    Device    │    │    Device    │    │    Device    │  ...    │   │
│   │   │  (Hub/GW)    │    │ (Thermostat) │    │   (Sensor)   │         │   │
│   │   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘         │   │
│   │          │                   │                   │                  │   │
│   └──────────│───────────────────│───────────────────│──────────────────┘   │
│              │                   │                   │                      │
│   ┌──────────▼───────────────────▼───────────────────▼──────────────────┐   │
│   │                        ENTITY REGISTRY                              │   │
│   │                                                                      │   │
│   │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│   │
│   │   │ light. │ │switch. │ │sensor. │ │binary_ │ │climate.│ │ cover. ││   │
│   │   │        │ │        │ │        │ │sensor. │ │        │ │        ││   │
│   │   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘│   │
│   │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│   │
│   │   │ fan.   │ │ lock.  │ │ media_ │ │vacuum. │ │ camera.│ │ alarm_ ││   │
│   │   │        │ │        │ │ player.│ │        │ │        │ │control_││   │
│   │   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘│   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        HELPER ENTITIES                               │   │
│   │                                                                      │   │
│   │   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│   │   │input_      │ │input_      │ │input_      │ │input_      │       │   │
│   │   │boolean     │ │number      │ │text        │ │select      │       │   │
│   │   └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│   │   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│   │   │input_      │ │input_      │ │counter     │ │timer       │       │   │
│   │   │datetime    │ │button      │ │            │ │            │       │   │
│   │   └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│   │   ┌────────────┐ ┌────────────┐ ┌────────────┐                      │   │
│   │   │schedule    │ │group       │ │template    │                      │   │
│   │   │            │ │            │ │(sensor/etc)│                      │   │
│   │   └────────────┘ └────────────┘ └────────────┘                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        AUTOMATION ENGINE                             │   │
│   │                                                                      │   │
│   │   ┌────────────┐ ┌────────────┐ ┌────────────┐                      │   │
│   │   │ automation │ │  script    │ │   scene    │                      │   │
│   │   └────────────┘ └────────────┘ └────────────┘                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        CONFIG & INTEGRATIONS                         │   │
│   │                                                                      │   │
│   │   ┌────────────┐ ┌────────────┐ ┌────────────┐                      │   │
│   │   │config_entry│ │integration │ │  service   │                      │   │
│   │   └────────────┘ └────────────┘ └────────────┘                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        EVENT BUS                                     │   │
│   │                                                                      │   │
│   │   state_changed │ call_service │ automation_triggered │ custom      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Aether Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            HA REGISTRY MIRROR                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│   │  Floor   │────<│   Area   │     │  Label   │     │ Category │           │
│   └──────────┘     └────┬─────┘     └────┬─────┘     └──────────┘           │
│                         │                │                                   │
│   ┌──────────┐     ┌────┴─────┐     ┌────┴─────┐     ┌──────────┐           │
│   │ConfigEntry│───>│  Device  │<────│EntityLabel│<───│  Entity  │           │
│   └──────────┘     └──────────┘     └──────────┘     └────┬─────┘           │
│        │                                                  │                  │
│        │           ┌────────────────────────────┬─────────┘                  │
│        │           │            │               │                            │
│        ▼           ▼            ▼               ▼                            │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│   │Integration│ │  Helper  │ │  Scene   │ │  Script  │                       │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘                       │
│                                                                              │
│   ┌──────────┐ ┌──────────┐                                                 │
│   │  Service │ │  Event   │                                                 │
│   └──────────┘ └──────────┘                                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                            AETHER AGENT LAYER                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│   │  Agent   │────>│Conversation│──>│ Message  │     │ Insight  │           │
│   └──────────┘     └────┬─────┘     └──────────┘     └────┬─────┘           │
│                         │                                 │                  │
│                         ▼                                 ▼                  │
│                    ┌──────────┐                     ┌──────────┐             │
│                    │Automation│                     │ Dashboard│             │
│                    │ Proposal │                     │          │             │
│                    └──────────┘                     └──────────┘             │
│                                                                              │
│   ┌──────────┐     ┌──────────┐                                             │
│   │Discovery │     │Checkpoint│                                             │
│   │ Session  │     │(LangGraph)│                                            │
│   └──────────┘     └──────────┘                                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## HA Registry Entities

These entities mirror Home Assistant's internal registries to provide full access to all HA primitives.

---

### Floor

> **Status: Not Yet Implemented** — Area has a nullable `floor_id` column but no Floor table exists.

Represents a floor/level in the home (HA 2024.x+).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_floor_id | String | Home Assistant floor ID | Unique |
| name | String | Floor name | e.g., `Ground Floor`, `Basement` |
| level | Integer | Floor level number | 0 = ground, negative = below |
| icon | String | MDI icon | e.g., `mdi:home-floor-1` |
| aliases | String[] | Alternative names | For NLP matching |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Area

Represents a physical area/room in the home.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_area_id | String | Home Assistant area ID | Unique |
| name | String | Area name | e.g., `Living Room`, `Kitchen` |
| floor_id | UUID | FK to Floor | Nullable |
| icon | String | MDI icon | e.g., `mdi:sofa` |
| picture | String | Area picture URL | Nullable |
| aliases | String[] | Alternative names | For NLP matching |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Label

> **Status: Not Yet Implemented**

Custom tagging system for entities/devices/areas (HA 2024.x+).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_label_id | String | Home Assistant label ID | Unique |
| name | String | Label name | e.g., `Energy Monitor`, `Critical` |
| color | String | Hex color | e.g., `#FF5722` |
| icon | String | MDI icon | e.g., `mdi:tag` |
| description | String | Label purpose | Nullable |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Category

> **Status: Not Yet Implemented**

Domain-specific category for organization.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_category_id | String | Home Assistant category ID | Unique |
| domain | String | HA domain | `automation`, `script`, `scene`, `helper` |
| name | String | Category name | e.g., `Lighting`, `Security` |
| icon | String | MDI icon | Nullable |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Device

Represents a physical or logical device containing one or more entities.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_device_id | String | Home Assistant device ID | Unique |
| name | String | Device name | e.g., `Living Room Thermostat` |
| name_by_user | String | User-defined name | Nullable override |
| manufacturer | String | Device manufacturer | e.g., `Philips`, `Aqara` |
| model | String | Device model | e.g., `Hue White Ambiance` |
| model_id | String | Model identifier | Nullable |
| hw_version | String | Hardware version | Nullable |
| sw_version | String | Software/firmware version | Nullable |
| serial_number | String | Serial number | Nullable |
| area_id | UUID | FK to Area | Nullable |
| config_entry_id | UUID | FK to ConfigEntry | Required |
| via_device_id | UUID | FK to Device (parent) | For hubs/gateways |
| connections | JSONB | Network connections | MAC, IP, Zigbee addr, etc. |
| identifiers | JSONB | Unique identifiers | Integration-specific IDs |
| disabled_by | String | Disabled reason | `user`, `integration`, `config_entry` |
| entry_type | String | Device type | `service`, null for normal devices |
| labels | UUID[] | FK to Label | Many-to-many |
| created_at | Timestamp | First discovered | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

**Indexes**: `ha_device_id` (unique), `manufacturer`, `model`, `area_id`, `config_entry_id`

---

### Entity

Represents a Home Assistant entity (the controllable unit).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_entity_id | String | Home Assistant entity ID | Unique, e.g., `light.living_room` |
| unique_id | String | Integration unique ID | From integration |
| platform | String | Integration platform | e.g., `hue`, `zwave_js` |
| domain | String | HA domain | See Domain Reference below |
| friendly_name | String | Human-readable name | From HA attributes |
| original_name | String | Integration-provided name | Before user override |
| device_id | UUID | FK to Device | Nullable (not all have device) |
| area_id | UUID | FK to Area | Can override device's area |
| icon | String | MDI icon | User or integration-defined |
| entity_category | String | Entity category | `config`, `diagnostic`, or null |
| state | String | Current state | Domain-specific |
| attributes | JSONB | Full HA attributes | Brightness, temperature, etc. |
| capabilities | JSONB | Supported features | Domain-specific capabilities |
| supported_features | Integer | Feature bitmask | HA feature flags |
| device_class | String | Device class | `temperature`, `motion`, etc. |
| unit_of_measurement | String | Unit | `°C`, `kWh`, `%`, etc. |
| disabled_by | String | Disabled reason | `user`, `integration`, `config_entry` |
| hidden_by | String | Hidden reason | `user`, `integration` |
| labels | UUID[] | FK to Label | Many-to-many |
| last_reported | Timestamp | Last state report | From HA |
| last_changed | Timestamp | Last state change | From HA |
| last_updated | Timestamp | Last attribute update | From HA |
| created_at | Timestamp | First discovered | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

**Domain Reference**:
| Domain | Description | Example Entities |
|--------|-------------|------------------|
| `light` | Lighting control | Dimmable bulbs, LED strips |
| `switch` | Binary switch | Smart plugs, relays |
| `sensor` | Sensor readings | Temperature, humidity |
| `binary_sensor` | Binary state | Motion, door/window |
| `climate` | HVAC control | Thermostats, AC |
| `cover` | Covers/blinds | Curtains, garage doors |
| `fan` | Fan control | Ceiling fans, ventilation |
| `lock` | Lock control | Smart locks |
| `media_player` | Media devices | TVs, speakers |
| `vacuum` | Robot vacuums | Roomba, Roborock |
| `camera` | Camera feeds | IP cameras |
| `alarm_control_panel` | Security systems | Home alarm |
| `humidifier` | Humidity control | Humidifiers, dehumidifiers |
| `water_heater` | Water heating | Boilers |
| `button` | Trigger actions | Integration buttons |
| `number` | Numeric input | Volume, speed settings |
| `select` | Dropdown selection | Mode selection |
| `text` | Text input | Custom text fields |
| `siren` | Siren control | Alarms |
| `update` | Software updates | Firmware updates |
| `weather` | Weather data | Weather services |
| `person` | Person tracking | Presence detection |
| `zone` | Geographic zones | Home, Work |
| `sun` | Sun position | Sunrise/sunset |
| `device_tracker` | Device location | Phone, tracker |

**Indexes**: `ha_entity_id` (unique), `domain`, `device_id`, `area_id`, `friendly_name` (full-text)

---

### ConfigEntry

> **Status: Not Yet Implemented**

Represents an integration configuration (how integrations are set up).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_entry_id | String | Home Assistant config entry ID | Unique |
| domain | String | Integration domain | e.g., `hue`, `zwave_js` |
| title | String | User-friendly title | e.g., `Hue Bridge` |
| source | String | Entry source | `user`, `discovery`, `import`, etc. |
| state | String | Entry state | `loaded`, `setup_error`, `not_loaded` |
| disabled_by | String | Disabled reason | `user` or null |
| pref_disable_new_entities | Boolean | Auto-disable new entities | Default: false |
| pref_disable_polling | Boolean | Disable polling | Default: false |
| options | JSONB | Entry options | Integration-specific |
| version | Integer | Config version | For migrations |
| minor_version | Integer | Minor version | For migrations |
| created_at | Timestamp | Entry creation | From HA |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Integration

> **Status: Not Yet Implemented**

Represents an available HA integration (metadata).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| domain | String | Integration domain | Unique, e.g., `hue` |
| name | String | Integration name | e.g., `Philips Hue` |
| documentation | String | Docs URL | Link to HA docs |
| codeowners | String[] | Maintainers | GitHub usernames |
| config_flow | Boolean | Has config flow | UI configuration |
| iot_class | String | IoT class | `local_polling`, `cloud_push`, etc. |
| quality_scale | String | Quality rating | `platinum`, `gold`, `silver`, `bronze` |
| requirements | String[] | Python packages | Dependencies |
| version | String | Integration version | For HACS integrations |
| is_built_in | Boolean | Core integration | vs HACS |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Helper

> **Status: Not Yet Implemented**

Represents a user-created helper entity.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| entity_id | UUID | FK to Entity | Required |
| helper_type | String | Helper type | See Helper Types below |
| config | JSONB | Helper configuration | Type-specific |
| editable | Boolean | User-editable | Usually true |
| category_id | UUID | FK to Category | Optional |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

**Helper Types**:
| Type | Domain | Purpose | Config Fields |
|------|--------|---------|---------------|
| `input_boolean` | `input_boolean` | Toggle state | `initial`, `icon` |
| `input_number` | `input_number` | Numeric value | `min`, `max`, `step`, `mode`, `unit_of_measurement` |
| `input_text` | `input_text` | Text value | `min`, `max`, `pattern`, `mode` |
| `input_select` | `input_select` | Dropdown | `options`, `initial` |
| `input_datetime` | `input_datetime` | Date/time | `has_date`, `has_time`, `initial` |
| `input_button` | `input_button` | Press trigger | `icon` |
| `counter` | `counter` | Increment/decrement | `initial`, `minimum`, `maximum`, `step`, `restore` |
| `timer` | `timer` | Countdown timer | `duration`, `restore` |
| `schedule` | `schedule` | Weekly schedule | Complex schedule blocks |
| `group` | `group` | Entity grouping | `entities`, `all` (require all on) |
| `template` | `sensor`/`binary_sensor`/etc. | Template-based | `value_template`, `attribute_templates` |

---

### Scene

Represents a Home Assistant scene (snapshot of entity states).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_scene_id | String | Home Assistant scene ID | Unique |
| entity_id | UUID | FK to Entity | `scene.*` entity |
| name | String | Scene name | e.g., `Movie Night` |
| icon | String | MDI icon | Nullable |
| entity_states | JSONB | Target states | `{entity_id: {state, attributes}}` |
| category_id | UUID | FK to Category | Optional |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Script

Represents a Home Assistant script (reusable action sequence).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_script_id | String | Home Assistant script ID | Unique, e.g., `script.notify_all` |
| entity_id | UUID | FK to Entity | `script.*` entity |
| alias | String | Script name | Human-readable |
| description | String | Script description | Nullable |
| icon | String | MDI icon | Nullable |
| mode | String | Execution mode | `single`, `restart`, `queued`, `parallel` |
| max | Integer | Max parallel runs | For `queued`/`parallel` modes |
| max_exceeded | String | Overflow action | `silent`, `warning`, `error` |
| sequence | JSONB | Action sequence | List of HA actions |
| fields | JSONB | Input fields | Script parameters |
| variables | JSONB | Script variables | Template variables |
| category_id | UUID | FK to Category | Optional |
| trace_enabled | Boolean | Enable tracing | Default: true |
| last_triggered | Timestamp | Last execution | From HA |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

---

### Service

Represents an available HA service (callable actions).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| domain | String | Service domain | e.g., `light`, `homeassistant` |
| service | String | Service name | e.g., `turn_on`, `reload` |
| name | String | Human-readable name | e.g., `Turn on` |
| description | String | Service description | What it does |
| fields | JSONB | Service parameters | Schema for each field |
| target | JSONB | Target specification | Entity/device/area selectors |
| response | JSONB | Response schema | For services with responses |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

**Common Service Patterns**:
| Domain | Services | Description |
|--------|----------|-------------|
| `homeassistant` | `turn_on`, `turn_off`, `toggle`, `reload` | Generic entity control |
| `light` | `turn_on`, `turn_off`, `toggle` | Light control with brightness/color |
| `switch` | `turn_on`, `turn_off`, `toggle` | Switch control |
| `climate` | `set_temperature`, `set_hvac_mode`, `set_preset_mode` | HVAC control |
| `cover` | `open_cover`, `close_cover`, `set_cover_position` | Cover control |
| `media_player` | `play_media`, `volume_set`, `media_pause` | Media control |
| `notify` | `*` | Notification services |
| `automation` | `trigger`, `turn_on`, `turn_off`, `reload` | Automation control |
| `script` | `*`, `turn_on`, `turn_off`, `reload` | Script execution |
| `scene` | `apply`, `turn_on`, `reload` | Scene activation |
| `input_*` | `set_value`, `increment`, `decrement` | Helper control |

**Indexes**: `(domain, service)` (unique)

---

### Event

> **Status: Not Yet Implemented**

Represents HA event types for agent awareness.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| event_type | String | Event type | e.g., `state_changed`, `call_service` |
| description | String | Event description | What triggers it |
| data_schema | JSONB | Event data schema | Expected fields |
| is_internal | Boolean | Internal event | Core vs integration |
| created_at | Timestamp | Record creation | Immutable |

**Key Event Types**:
| Event Type | Description | Data Fields |
|------------|-------------|-------------|
| `state_changed` | Entity state change | `entity_id`, `old_state`, `new_state` |
| `call_service` | Service called | `domain`, `service`, `service_data` |
| `automation_triggered` | Automation fired | `name`, `entity_id`, `source` |
| `script_started` | Script began | `name`, `entity_id` |
| `homeassistant_start` | HA startup | — |
| `homeassistant_stop` | HA shutdown | — |
| `component_loaded` | Integration loaded | `component` |
| `service_registered` | New service | `domain`, `service` |
| `device_registry_updated` | Device change | `action`, `device_id` |
| `entity_registry_updated` | Entity change | `action`, `entity_id` |
| `area_registry_updated` | Area change | `action`, `area_id` |
| `floor_registry_updated` | Floor change | `action`, `floor_id` |
| `label_registry_updated` | Label change | `action`, `label_id` |

---

## Aether Agent Entities

These entities are specific to Project Aether's agent orchestration layer.

---

### DiscoverySession

Tracks entity discovery runs by the Librarian agent.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| started_at | Timestamp | Session start | Immutable |
| completed_at | Timestamp | Session end | Nullable until complete |
| entities_found | Integer | Count of entities discovered | >= 0 |
| entities_added | Integer | New entities | >= 0 |
| entities_removed | Integer | Removed entities | >= 0 |
| entities_updated | Integer | Changed entities | >= 0 |
| devices_found | Integer | Count of devices discovered | >= 0 |
| devices_added | Integer | New devices | >= 0 |
| areas_found | Integer | Count of areas discovered | >= 0 |
| floors_found | Integer | Count of floors discovered | >= 0 |
| labels_found | Integer | Count of labels discovered | >= 0 |
| integrations_found | Integer | Count of integrations | >= 0 |
| services_found | Integer | Count of services discovered | >= 0 |
| status | Enum | Session status | `running`, `completed`, `failed` |
| error_message | String | Error details if failed | Nullable |
| mlflow_run_id | String | MLflow tracking ID | For observability |

---

### Agent

Represents an agent in the system (for tracing purposes).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| name | String | Agent identifier | `librarian`, `categorizer`, `architect`, `developer`, `data_scientist` |
| description | String | Agent purpose | Human-readable |
| version | String | Agent version | SemVer |
| prompt_template | Text | System prompt | Versioned in MLflow |
| created_at | Timestamp | Record creation | Immutable |

---

### Conversation

A dialogue session between user and an agent (primarily Architect).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| agent_id | UUID | FK to Agent | Required |
| user_id | String | User identifier | Default: `default_user` |
| title | String | Conversation summary | Auto-generated |
| status | Enum | Conversation state | `active`, `completed`, `archived` |
| context | JSONB | Conversation context | Entities involved, preferences |
| created_at | Timestamp | Started | Immutable |
| updated_at | Timestamp | Last activity | Auto-updated |

---

### Message

Individual messages within a conversation.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| conversation_id | UUID | FK to Conversation | Required |
| role | Enum | Message author | `user`, `assistant`, `system` |
| content | Text | Message content | Required |
| tool_calls | JSONB | Function calls made | Nullable |
| tool_results | JSONB | Function call results | Nullable |
| tokens_used | Integer | Token count | For cost tracking |
| latency_ms | Integer | Response time | For performance tracking |
| mlflow_span_id | String | Trace span ID | For observability |
| created_at | Timestamp | Message time | Immutable |

---

### HAAutomation

Represents an existing Home Assistant automation (synced from HA).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| ha_automation_id | String | Home Assistant automation ID | Unique |
| entity_id | UUID | FK to Entity | `automation.*` entity |
| alias | String | Automation name | Human-readable |
| description | String | Automation description | Nullable |
| mode | String | Execution mode | `single`, `restart`, `queued`, `parallel` |
| max | Integer | Max parallel runs | For `queued`/`parallel` modes |
| max_exceeded | String | Overflow action | `silent`, `warning`, `error` |
| trigger | JSONB | HA trigger config | Trigger definitions |
| condition | JSONB | HA conditions | Condition definitions |
| action | JSONB | HA actions | Action sequence |
| variables | JSONB | Automation variables | Template variables |
| trace_enabled | Boolean | Enable tracing | Default: true |
| stored_traces | Integer | Traces to keep | Default: 5 |
| is_enabled | Boolean | Automation enabled | From entity state |
| last_triggered | Timestamp | Last execution | From HA |
| category_id | UUID | FK to Category | Optional |
| created_at | Timestamp | Record creation | Immutable |
| updated_at | Timestamp | Last sync | Auto-updated |

**Trigger Types**:
| Type | Description | Key Fields |
|------|-------------|------------|
| `state` | State change | `entity_id`, `from`, `to`, `for` |
| `numeric_state` | Numeric threshold | `entity_id`, `above`, `below` |
| `time` | Time of day | `at` |
| `time_pattern` | Recurring time | `hours`, `minutes`, `seconds` |
| `sun` | Sunrise/sunset | `event`, `offset` |
| `zone` | Zone enter/exit | `entity_id`, `zone`, `event` |
| `device` | Device trigger | `device_id`, device-specific |
| `mqtt` | MQTT message | `topic`, `payload` |
| `webhook` | HTTP webhook | `webhook_id` |
| `event` | HA event | `event_type`, `event_data` |
| `homeassistant` | HA lifecycle | `event` (start/shutdown) |
| `tag` | NFC/RFID tag | `tag_id`, `device_id` |
| `calendar` | Calendar event | `entity_id`, `event` |
| `template` | Template true | `value_template` |
| `persistent_notification` | Notification | `notification_id` |
| `conversation` | Voice command | `command` |

---

### AutomationProposal

A proposed automation rule (from agents, requiring HITL approval).

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| conversation_id | UUID | FK to Conversation | Source conversation |
| name | String | Automation name | Human-readable |
| description | Text | What it does | User-facing |
| trigger | JSONB | HA trigger config | Time, state, event, etc. |
| conditions | JSONB | HA conditions | Optional |
| actions | JSONB | HA actions | Required |
| mode | String | Execution mode | Default: `single` |
| status | Enum | Proposal state | See state machine below |
| ha_automation_id | String | HA automation ID | Set after deployment |
| proposed_at | Timestamp | When proposed | Immutable |
| approved_at | Timestamp | When approved | Nullable |
| approved_by | String | Approver | Nullable |
| deployed_at | Timestamp | When deployed to HA | Nullable |
| rolled_back_at | Timestamp | When rolled back | Nullable |
| rejection_reason | String | Why rejected | Nullable |
| mlflow_run_id | String | Tracking ID | For observability |

**State Machine**:
```
                 ┌──────────┐
                 │  draft   │
                 └────┬─────┘
                      │ propose()
                      ▼
                 ┌──────────┐
        ┌───────>│ proposed │<──────┐
        │        └────┬─────┘       │
        │             │             │
        │   approve() │   reject()  │
        │             ▼             │
        │        ┌──────────┐       │
        │        │ approved │       │
        │        └────┬─────┘       │
        │             │             │
        │    deploy() │             │
        │             ▼             │
        │        ┌──────────┐       │
        │        │ deployed │───────┤
        │        └────┬─────┘       │
        │             │             │
        │  rollback() │             │
        │             ▼             │
        │        ┌──────────┐       │
        └────────│rolled_back│──────┘
                 └──────────┘
                      │
              expire()/archive()
                      ▼
                 ┌──────────┐
                 │ archived │
                 └──────────┘
```

---

### Insight

Data-driven observation from the Data Scientist agent.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| type | Enum | Insight category | `energy_optimization`, `anomaly_detection`, `usage_pattern`, `cost_saving`, `maintenance_prediction` |
| title | String | Brief summary | Human-readable |
| description | Text | Detailed explanation | Markdown supported |
| evidence | JSONB | Supporting data | Charts, statistics, queries |
| confidence | Float | Confidence score | 0.0 - 1.0 |
| impact | String | Potential impact | `low`, `medium`, `high`, `critical` |
| entities | UUID[] | Related entities | FK to Entity |
| script_path | String | Generated analysis script | Path in MLflow artifacts |
| script_output | JSONB | Script execution results | Stdout, figures, metrics |
| status | Enum | Insight state | `pending`, `reviewed`, `actioned`, `dismissed` |
| mlflow_run_id | String | Tracking ID | For observability |
| created_at | Timestamp | Generated | Immutable |
| reviewed_at | Timestamp | When reviewed | Nullable |
| actioned_at | Timestamp | When actioned | Nullable |

---

### Dashboard

> **Status: Not Yet Implemented** — Dashboard generation exists in agents but no persistent Dashboard table.

Generated Home Assistant dashboard configuration.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | Generated |
| conversation_id | UUID | FK to Conversation | Source conversation |
| name | String | Dashboard name | Human-readable |
| description | Text | Purpose | User-facing |
| theme | String | Visual theme | `auto`, `light`, `dark` |
| layout | JSONB | HA dashboard YAML | Lovelace configuration |
| entities | UUID[] | Included entities | FK to Entity |
| status | Enum | Dashboard state | `draft`, `approved`, `deployed`, `archived` |
| ha_dashboard_id | String | HA dashboard ID | Set after deployment |
| deployed_at | Timestamp | When deployed | Nullable |
| created_at | Timestamp | Generated | Immutable |
| updated_at | Timestamp | Last modified | Auto-updated |

---

### Checkpoint (LangGraph Managed)

LangGraph manages this table for workflow state persistence.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| thread_id | String | Workflow thread | Primary key part |
| checkpoint_id | String | Checkpoint version | Primary key part |
| parent_id | String | Parent checkpoint | For branching |
| checkpoint | JSONB | Serialized state | LangGraph format |
| metadata | JSONB | Additional metadata | Custom fields |
| created_at | Timestamp | Checkpoint time | Immutable |

---

## Validation Rules

### HA Registry Entities

#### Floor
- `ha_floor_id` must be unique
- `level` should be unique per floor (no duplicate levels)

#### Area
- `ha_area_id` must be unique
- `floor_id` must reference existing Floor if provided

#### Label
- `ha_label_id` must be unique
- `color` must be valid hex color format

#### Device
- `ha_device_id` must be unique
- `config_entry_id` must reference existing ConfigEntry
- `via_device_id` must reference existing Device if provided (no circular refs)
- `area_id` must reference existing Area if provided

#### Entity
- `ha_entity_id` must match pattern: `{domain}.{object_id}`
- `domain` must be valid HA domain
- `device_id` must reference existing Device if provided
- `area_id` must reference existing Area if provided
- `entity_category` must be `config`, `diagnostic`, or null

#### ConfigEntry
- `ha_entry_id` must be unique
- `state` must be `loaded`, `setup_error`, `setup_retry`, `not_loaded`, or `failed_unload`

#### Helper
- `entity_id` must reference existing Entity
- `helper_type` must be valid helper type
- `config` must match schema for `helper_type`

#### Scene
- `ha_scene_id` must be unique
- `entity_id` must reference Entity with domain `scene`
- `entity_states` must contain valid entity_id keys

#### Script
- `ha_script_id` must be unique
- `entity_id` must reference Entity with domain `script`
- `mode` must be `single`, `restart`, `queued`, or `parallel`
- `max` required if mode is `queued` or `parallel`

#### Service
- `(domain, service)` combination must be unique
- `fields` must be valid JSON schema

#### HAAutomation
- `ha_automation_id` must be unique
- `entity_id` must reference Entity with domain `automation`
- `mode` must be `single`, `restart`, `queued`, or `parallel`

### Aether Agent Entities

#### AutomationProposal
- Cannot transition from `archived` to any other state
- `approved_by` required when status is `approved`
- `ha_automation_id` required when status is `deployed`
- HITL: status cannot change from `proposed` to `deployed` without going through `approved`

#### Insight
- `confidence` must be between 0.0 and 1.0
- `script_path` required for `energy_optimization` type
- `evidence` must contain at least one data point

#### Dashboard
- `layout` must be valid HA Lovelace YAML structure
- `entities` must reference existing Entity records

---

## Indexes

```sql
-- ===========================================
-- HA REGISTRY INDEXES
-- ===========================================

-- Floor lookups
CREATE UNIQUE INDEX idx_floor_ha_id ON floors(ha_floor_id);
CREATE UNIQUE INDEX idx_floor_level ON floors(level);

-- Area lookups
CREATE UNIQUE INDEX idx_area_ha_id ON areas(ha_area_id);
CREATE INDEX idx_area_floor ON areas(floor_id);
CREATE INDEX idx_area_name ON areas(name);

-- Label lookups
CREATE UNIQUE INDEX idx_label_ha_id ON labels(ha_label_id);

-- Category lookups
CREATE UNIQUE INDEX idx_category_ha_id ON categories(ha_category_id);
CREATE INDEX idx_category_domain ON categories(domain);

-- Device lookups
CREATE UNIQUE INDEX idx_device_ha_id ON devices(ha_device_id);
CREATE INDEX idx_device_manufacturer ON devices(manufacturer);
CREATE INDEX idx_device_model ON devices(model);
CREATE INDEX idx_device_area ON devices(area_id);
CREATE INDEX idx_device_config_entry ON devices(config_entry_id);
CREATE INDEX idx_device_via ON devices(via_device_id);

-- Entity lookups
CREATE UNIQUE INDEX idx_entity_ha_id ON entities(ha_entity_id);
CREATE INDEX idx_entity_domain ON entities(domain);
CREATE INDEX idx_entity_device ON entities(device_id);
CREATE INDEX idx_entity_area ON entities(area_id);
CREATE INDEX idx_entity_platform ON entities(platform);
CREATE INDEX idx_entity_device_class ON entities(device_class);
CREATE INDEX idx_entity_friendly_name ON entities USING gin(to_tsvector('english', friendly_name));

-- ConfigEntry lookups
CREATE UNIQUE INDEX idx_config_entry_ha_id ON config_entries(ha_entry_id);
CREATE INDEX idx_config_entry_domain ON config_entries(domain);
CREATE INDEX idx_config_entry_state ON config_entries(state);

-- Integration lookups
CREATE UNIQUE INDEX idx_integration_domain ON integrations(domain);

-- Helper lookups
CREATE INDEX idx_helper_type ON helpers(helper_type);
CREATE INDEX idx_helper_entity ON helpers(entity_id);

-- Scene lookups
CREATE UNIQUE INDEX idx_scene_ha_id ON scenes(ha_scene_id);
CREATE INDEX idx_scene_entity ON scenes(entity_id);

-- Script lookups
CREATE UNIQUE INDEX idx_script_ha_id ON scripts(ha_script_id);
CREATE INDEX idx_script_entity ON scripts(entity_id);

-- Service lookups
CREATE UNIQUE INDEX idx_service_domain_service ON services(domain, service);

-- HA Automation lookups
CREATE UNIQUE INDEX idx_ha_automation_ha_id ON ha_automations(ha_automation_id);
CREATE INDEX idx_ha_automation_entity ON ha_automations(entity_id);

-- Event lookups
CREATE UNIQUE INDEX idx_event_type ON events(event_type);

-- Label relationships (many-to-many)
CREATE INDEX idx_entity_labels ON entity_labels(entity_id);
CREATE INDEX idx_device_labels ON device_labels(device_id);

-- ===========================================
-- AETHER AGENT INDEXES
-- ===========================================

-- Conversation queries
CREATE INDEX idx_conversation_user ON conversations(user_id);
CREATE INDEX idx_conversation_status ON conversations(status);
CREATE INDEX idx_message_conversation ON messages(conversation_id);

-- Automation proposal workflow
CREATE INDEX idx_proposal_status ON automation_proposals(status);
CREATE INDEX idx_proposal_conversation ON automation_proposals(conversation_id);

-- Insight discovery
CREATE INDEX idx_insight_type ON insights(type);
CREATE INDEX idx_insight_status ON insights(status);

-- Discovery sessions
CREATE INDEX idx_discovery_started ON discovery_sessions(started_at);

-- ===========================================
-- TEMPORAL INDEXES
-- ===========================================

CREATE INDEX idx_entity_last_changed ON entities(last_changed);
CREATE INDEX idx_entity_last_updated ON entities(last_updated);
CREATE INDEX idx_device_updated ON devices(updated_at);
CREATE INDEX idx_ha_automation_triggered ON ha_automations(last_triggered);
CREATE INDEX idx_script_triggered ON scripts(last_triggered);
```

---

## Migration Strategy

### Phase 1: Core HA Registries
1. Create `floors` table
2. Create `areas` table with FK to floors
3. Create `labels` table
4. Create `categories` table
5. Create `config_entries` table
6. Create `integrations` table

### Phase 2: Devices & Entities
1. Create `devices` table with FKs to areas, config_entries
2. Create `entities` table with FKs to devices, areas
3. Create `entity_labels` junction table
4. Create `device_labels` junction table

### Phase 3: HA Automation Primitives
1. Create `helpers` table with FK to entities
2. Create `scenes` table with FK to entities
3. Create `scripts` table with FK to entities
4. Create `ha_automations` table with FK to entities
5. Create `services` table
6. Create `events` table

### Phase 4: Aether Agent Layer
1. Create `agents` table with seed data
2. Create `conversations` table
3. Create `messages` table
4. Create `automation_proposals` table
5. Create `insights` table
6. Create `dashboards` table
7. Create `discovery_sessions` table
8. Let LangGraph create its `checkpoints` table

### Phase 5: Initial Sync
1. Run Librarian discovery to sync all HA registries
2. Populate floors, areas, labels, devices, entities
3. Sync scenes, scripts, automations
4. Index all services and events

---

## MCP Tool Mapping

The following table maps HA MCP tools to entities they populate:

| MCP Tool | Target Entity | Notes |
|----------|---------------|-------|
| `system_overview` | All registries | Initial discovery |
| `list_entities` | Entity | Core entity sync |
| `get_entity` | Entity | Single entity detail |
| `domain_summary_tool` | Entity | Domain statistics |
| `search_entities_tool` | Entity | Search-based discovery |
| `list_automations` | HAAutomation | Automation sync |
| `get_history` | (temporal analysis) | For insights |
| `call_service_tool` | Service | Service registry |

### Missing MCP Capabilities (Require Extension)

To fully populate the data model, the MCP server needs these additional tools:

| Needed Tool | Purpose | HA WebSocket API |
|-------------|---------|------------------|
| `list_devices` | Device registry | `config/device_registry/list` |
| `list_areas` | Area registry | `config/area_registry/list` |
| `list_floors` | Floor registry | `config/floor_registry/list` |
| `list_labels` | Label registry | `config/label_registry/list` |
| `list_categories` | Category registry | `config/category_registry/list` |
| `list_config_entries` | Config entries | `config_entries/get` |
| `list_integrations` | Integration manifest | `manifest/list` |
| `list_services` | Service registry | `get_services` |
| `list_scripts` | Script registry | `script/list` |
| `list_scenes` | Scene registry | `scene/list` |
| `list_helpers` | Helper entities | Filter by `input_*`, `counter`, `timer`, etc. |
| `subscribe_events` | Event stream | `subscribe_events` |

---

## WebSocket API Reference

For extending the MCP server, here are the key HA WebSocket commands:

```javascript
// Device Registry
{ "type": "config/device_registry/list" }
{ "type": "config/device_registry/update", "device_id": "...", "area_id": "...", "labels": [...] }

// Entity Registry
{ "type": "config/entity_registry/list" }
{ "type": "config/entity_registry/get", "entity_id": "light.living_room" }
{ "type": "config/entity_registry/update", "entity_id": "...", "area_id": "...", "labels": [...] }

// Area Registry
{ "type": "config/area_registry/list" }
{ "type": "config/area_registry/create", "name": "...", "floor_id": "..." }
{ "type": "config/area_registry/update", "area_id": "...", "name": "...", "labels": [...] }

// Floor Registry
{ "type": "config/floor_registry/list" }
{ "type": "config/floor_registry/create", "name": "...", "level": 0 }

// Label Registry
{ "type": "config/label_registry/list" }
{ "type": "config/label_registry/create", "name": "...", "color": "#FF5722" }

// Category Registry  
{ "type": "config/category_registry/list", "scope": "automation" }

// Config Entries
{ "type": "config_entries/get" }
{ "type": "config_entries/flow", "handler": "hue" }

// Services
{ "type": "get_services" }

// Automations, Scripts, Scenes
{ "type": "automation/config", "entity_id": "automation.example" }
{ "type": "script/config", "entity_id": "script.example" }
{ "type": "scene/config", "entity_id": "scene.example" }

// Events
{ "type": "subscribe_events", "event_type": "state_changed" }
{ "type": "fire_event", "event_type": "custom_event", "event_data": {...} }

// State
{ "type": "get_states" }
{ "type": "call_service", "domain": "light", "service": "turn_on", "service_data": {...} }
```
