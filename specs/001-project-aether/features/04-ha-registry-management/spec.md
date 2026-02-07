**Completed**: 2026-02-07

# Feature: Home Assistant Registry Management

**Status**: Complete  
**Priority**: P3  
**User Story**: US6  
**Depends on**: US1 (Entity Discovery), US2 (Architect)

## Goal

Enable agents to manage Home Assistant registries (devices, entities, areas, floors, labels) via REST API, allowing dynamic organization and configuration of the smart home.

## Description

Home Assistant maintains several registries that organize entities into logical groups. Currently, Project Aether can only read entities but cannot modify their organization. This feature adds full CRUD capabilities for:

- **Device Registry**: Manage device names, areas, disabled status
- **Entity Registry**: Rename entities, change icons, disable/enable, assign to areas
- **Area Registry**: Create/rename/delete areas (rooms)
- **Floor Registry**: Create floors and assign areas to them
- **Label Registry**: Create labels for cross-cutting entity grouping

This enables powerful use cases like the agent automatically organizing new devices, renaming poorly-named entities, and creating logical groupings based on user preferences.

## Example Use Cases

### 1. Automatic Device Organization
**User**: "I just added some new Zigbee devices. Can you organize them?"
**Agent**: 
- Discovers new devices without area assignments
- Analyzes device names/types to infer room placement
- Creates areas if needed ("Guest Bedroom")
- Assigns devices to appropriate areas
- Renames entities with consistent naming convention

### 2. Entity Cleanup
**User**: "Rename all my sensors to be more descriptive"
**Agent**:
- Lists all sensors with generic names
- Generates descriptive names based on device/area context
- Updates entity registry with new names
- Reports changes for user approval

### 3. Floor-Based Organization
**User**: "Set up floor organization - I have 3 floors"
**Agent**:
- Creates Floor 1, Floor 2, Floor 3 in registry
- Groups existing areas by floor
- Creates automations that work per-floor ("turn off all lights on Floor 2")

### 4. Label-Based Grouping
**User**: "Group all my security-related devices"
**Agent**:
- Creates "Security" label
- Identifies relevant entities (motion sensors, door sensors, cameras, locks)
- Applies label to all security entities
- Creates automation: "arm all security devices"

### 5. Bulk Disable/Enable
**User**: "Disable all the entities I never use"
**Agent**:
- Analyzes entity usage history
- Identifies entities with no state changes in 30+ days
- Presents list for approval
- Disables selected entities via registry

## Independent Test

Agent can create an area, assign entities to it, rename entities, and create labels - all via REST API without manual HA configuration.

## MCP Tools Used

None currently - this feature uses REST API directly.

## REST API Endpoints Required

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/config/device_registry` | GET | List all devices |
| `/api/config/device_registry/{device_id}` | POST | Update device |
| `/api/config/entity_registry` | GET | List all entity registry entries |
| `/api/config/entity_registry/{entity_id}` | POST | Update entity |
| `/api/config/area_registry/list` | GET | List all areas |
| `/api/config/area_registry/create` | POST | Create area |
| `/api/config/area_registry/update` | POST | Update area |
| `/api/config/area_registry/delete` | POST | Delete area |
| `/api/config/floor_registry/list` | GET | List all floors |
| `/api/config/floor_registry/create` | POST | Create floor |
| `/api/config/floor_registry/update` | POST | Update floor |
| `/api/config/floor_registry/delete` | POST | Delete floor |
| `/api/config/label_registry/list` | GET | List all labels |
| `/api/config/label_registry/create` | POST | Create label |
| `/api/config/label_registry/update` | POST | Update label |
| `/api/config/label_registry/delete` | POST | Delete label |

## Acceptance Criteria

1. **Given** entities without areas, **When** agent analyzes device context, **Then** it suggests area assignments with 80% accuracy
2. **Given** user approval, **When** agent creates/updates areas, **Then** changes appear in HA within 5 seconds
3. **Given** poorly-named entities, **When** agent renames them, **Then** automations using old names still work (HA handles this)
4. **Given** entities across multiple rooms, **When** agent creates labels, **Then** labeled entities can be controlled as a group
5. **Given** any registry modification, **When** executed, **Then** it's logged in MLflow and can be rolled back

## HITL Requirements

All registry modifications require explicit user approval:
- Area creation/deletion
- Entity renaming (batch operations shown as list)
- Device reassignment
- Label application

## Related Features

- **US1 Entity Discovery**: Registry management extends discovery capabilities
- **US2 Architect**: Uses registries when designing automations ("all lights in Kitchen")
- **Dashboard Generation**: Uses areas/floors for dashboard organization
