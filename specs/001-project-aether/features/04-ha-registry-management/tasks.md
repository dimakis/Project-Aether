# Tasks: Home Assistant Registry Management

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**User Story**: US6

---

## MCP Client Extensions

- [ ] T301 [US6] Add device registry methods to src/mcp/client.py:
  - `list_device_registry()` - GET /api/config/device_registry
  - `update_device(device_id, name, area_id, disabled)` - POST update
  - `get_device(device_id)` - Get single device details

- [ ] T302 [US6] Add entity registry methods to src/mcp/client.py:
  - `list_entity_registry()` - GET /api/config/entity_registry  
  - `update_entity_registry(entity_id, name, icon, disabled, area_id)` - POST update
  - `get_entity_registry_entry(entity_id)` - Get single entry

- [ ] T303 [US6] Add area registry methods to src/mcp/client.py:
  - `list_areas()` - GET /api/config/area_registry/list
  - `create_area(name, icon, floor_id)` - POST create
  - `update_area(area_id, name, icon, floor_id)` - POST update
  - `delete_area(area_id)` - POST delete

- [ ] T304 [US6] Add floor registry methods to src/mcp/client.py:
  - `list_floors()` - GET /api/config/floor_registry/list
  - `create_floor(name, level, icon)` - POST create
  - `update_floor(floor_id, name, level, icon)` - POST update  
  - `delete_floor(floor_id)` - POST delete

- [ ] T305 [US6] Add label registry methods to src/mcp/client.py:
  - `list_labels()` - GET /api/config/label_registry/list
  - `create_label(name, color, icon, description)` - POST create
  - `update_label(label_id, name, color, icon)` - POST update
  - `delete_label(label_id)` - POST delete

## Agent Tools

- [ ] T306 [P] [US6] Create src/tools/registry_tools.py with area tools:
  - `create_area(name, floor)` - Create new area
  - `rename_area(area_id, new_name)` - Rename area
  - `delete_area(area_id)` - Delete area (with entity check)
  - `list_areas()` - List all areas with entity counts

- [ ] T307 [P] [US6] Add floor tools to src/tools/registry_tools.py:
  - `create_floor(name, level)` - Create floor
  - `assign_area_to_floor(area_id, floor_id)` - Move area to floor
  - `list_floors()` - List floors with areas

- [ ] T308 [P] [US6] Add label tools to src/tools/registry_tools.py:
  - `create_label(name, color, description)` - Create label
  - `apply_label(entity_ids, label_id)` - Apply label to entities
  - `remove_label(entity_ids, label_id)` - Remove label
  - `list_labels()` - List labels with entity counts

- [ ] T309 [P] [US6] Add entity management tools to src/tools/registry_tools.py:
  - `rename_entity(entity_id, new_name)` - Update friendly name
  - `set_entity_icon(entity_id, icon)` - Update icon
  - `disable_entity(entity_id)` - Disable entity
  - `enable_entity(entity_id)` - Enable entity
  - `assign_entity_to_area(entity_id, area_id)` - Move entity to area

- [ ] T310 [P] [US6] Add device management tools to src/tools/registry_tools.py:
  - `rename_device(device_id, new_name)` - Update device name
  - `assign_device_to_area(device_id, area_id)` - Move device
  - `disable_device(device_id)` - Disable device
  - `list_devices(area_id)` - List devices, optionally by area

- [ ] T311 [US6] Register registry tools in src/tools/__init__.py get_all_tools()

## Organization Intelligence

- [ ] T312 [US6] Create src/agents/organizer.py with EntityOrganizer:
  - `analyze_naming_patterns()` - Detect naming conventions
  - `suggest_entity_names(entity_ids)` - Generate better names
  - `suggest_area_assignments(entity_ids)` - Infer areas from context
  - `detect_orphan_entities()` - Find entities without areas
  - `suggest_labels(entity_ids)` - Suggest label groupings

- [ ] T313 [US6] Create src/mcp/naming.py with naming utilities:
  - `parse_entity_name(entity_id)` - Extract components
  - `generate_friendly_name(entity_id, context)` - Create readable name
  - `normalize_name(name)` - Consistent formatting
  - `infer_room_from_name(name)` - Extract room hints

## Database Models

- [ ] T314 [US6] Create Alembic migration alembic/versions/007_registries.py:
  - Add Floor table (id, ha_floor_id, name, level, icon)
  - Add Label table (id, ha_label_id, name, color, icon, description)
  - Add entity_labels junction table
  - Update Area table with floor_id FK

- [ ] T315 [US6] Create src/storage/entities/floor.py with Floor model
- [ ] T316 [US6] Create src/storage/entities/label.py with Label model
- [ ] T317 [US6] Update src/storage/entities/area.py with floor relationship
- [ ] T318 [US6] Update src/storage/entities/entity.py with labels relationship

## DAL Extensions

- [ ] T319 [US6] Create src/dal/floor_repository.py with FloorRepository
- [ ] T320 [US6] Create src/dal/label_repository.py with LabelRepository
- [ ] T321 [US6] Update src/dal/area_repository.py with floor operations
- [ ] T322 [US6] Update src/dal/entity_repository.py with label operations

## Sync Service Extensions

- [ ] T323 [US6] Extend src/sync/entity_sync.py to sync:
  - Floor registry (new)
  - Label registry (new)
  - Entity registry entries (icons, disabled status)
  - Device registry assignments

## API Endpoints

- [ ] T324 [P] [US6] Create src/api/schemas/registry.py:
  - AreaCreate, AreaUpdate, AreaResponse
  - FloorCreate, FloorUpdate, FloorResponse
  - LabelCreate, LabelUpdate, LabelResponse
  - EntityRenameRequest, DeviceAssignRequest

- [ ] T325 [US6] Create src/api/routes/areas.py:
  - GET /areas - List areas
  - POST /areas - Create area
  - PATCH /areas/{id} - Update area
  - DELETE /areas/{id} - Delete area
  - GET /areas/{id}/entities - List entities in area

- [ ] T326 [US6] Create src/api/routes/floors.py:
  - GET /floors - List floors
  - POST /floors - Create floor
  - PATCH /floors/{id} - Update floor
  - DELETE /floors/{id} - Delete floor

- [ ] T327 [US6] Create src/api/routes/labels.py:
  - GET /labels - List labels
  - POST /labels - Create label
  - PATCH /labels/{id} - Update label
  - DELETE /labels/{id} - Delete label
  - POST /labels/{id}/apply - Apply to entities
  - POST /labels/{id}/remove - Remove from entities

- [ ] T328 [US6] Extend src/api/routes/entities.py:
  - PATCH /entities/{id}/name - Rename entity
  - PATCH /entities/{id}/area - Change area
  - PATCH /entities/{id}/icon - Change icon
  - POST /entities/{id}/disable - Disable
  - POST /entities/{id}/enable - Enable

## CLI Commands

- [ ] T329 [US6] Add `aether areas` commands to src/cli/main.py:
  - `aether areas list` - List all areas
  - `aether areas create <name>` - Create area
  - `aether areas delete <id>` - Delete area
  - `aether areas assign <entity_id> <area_id>` - Assign entity

- [ ] T330 [US6] Add `aether organize` commands:
  - `aether organize suggest` - Suggest organization improvements
  - `aether organize rename --domain sensor` - Suggest renames
  - `aether organize apply <suggestion_id>` - Apply suggestion

## Tests

**Unit Tests**:
- [ ] T331 [P] [US6] Create tests/unit/test_mcp_registries.py
- [ ] T332 [P] [US6] Create tests/unit/test_registry_tools.py
- [ ] T333 [P] [US6] Create tests/unit/test_entity_organizer.py
- [ ] T334 [P] [US6] Create tests/unit/test_naming_utils.py

**Integration Tests**:
- [ ] T335 [US6] Create tests/integration/test_area_management.py
- [ ] T336 [US6] Create tests/integration/test_label_operations.py
- [ ] T337 [US6] Create tests/integration/test_entity_registry_sync.py

**E2E Tests**:
- [ ] T338 [US6] Create tests/e2e/test_organize_flow.py - Full organize: analyze -> suggest -> approve -> apply
