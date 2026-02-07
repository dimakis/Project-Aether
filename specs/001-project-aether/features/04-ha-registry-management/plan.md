# Plan: Home Assistant Registry Management

**Feature**: [spec.md](./spec.md) | **Tasks**: [tasks.md](./tasks.md)

## Implementation Phases

### Phase 1: MCP Client Extensions
Add REST API methods for all registry operations.

**Deliverable**: MCPClient can CRUD areas, floors, labels, devices, entities

### Phase 2: Agent Tools
Create LangChain tools that wrap registry operations.

**Deliverable**: Architect agent can manage registries via tool calls

### Phase 3: Organization Intelligence
Build smart naming and assignment suggestions.

**Deliverable**: Agent can suggest improvements to entity organization

### Phase 4: Database Sync
Extend sync service to maintain local registry state.

**Deliverable**: Local DB reflects HA registry state

### Phase 5: API & CLI
Expose registry management via API and CLI.

**Deliverable**: Full programmatic access to registry operations

## Dependencies

- US1 (Entity Discovery): Need entity sync working first
- US2 (Architect): Tools will be used by Architect agent

## Risks

| Risk | Mitigation |
|------|------------|
| HA version differences in registry API | Feature detection, graceful degradation |
| Bulk operations timeout | Batch processing with progress feedback |
| Accidental data loss | HITL approval, operation logging, undo capability |

## Estimated Effort

- MCP Client: 2-3 hours
- Agent Tools: 2-3 hours
- Organization Intelligence: 4-5 hours
- Database Sync: 3-4 hours
- API/CLI: 2-3 hours
- Tests: 3-4 hours

**Total**: ~18-22 hours
