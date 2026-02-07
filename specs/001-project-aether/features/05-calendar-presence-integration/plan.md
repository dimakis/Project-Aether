# Plan: Calendar & Presence Integration

**Feature**: [spec.md](./spec.md) | **Tasks**: [tasks.md](./tasks.md)

## Implementation Phases

### Phase 1: MCP Client Extensions
Add REST API methods for calendar, presence, and zone operations.

**Deliverable**: MCPClient can read calendars, track presence, manage zones

### Phase 2: Data Models & Parsing
Create dataclasses and parsing utilities for calendar/presence data.

**Deliverable**: Clean typed interfaces for calendar events and presence states

### Phase 3: Agent Tools
Create LangChain tools for presence and calendar queries.

**Deliverable**: Agents can check who's home, query calendars, manage zones

### Phase 4: Context Providers
Build context providers that inject schedule/presence awareness.

**Deliverable**: Agents have automatic awareness of household context

### Phase 5: Automation Helpers
Create builders for calendar and presence-based triggers/conditions.

**Deliverable**: Easy creation of presence-aware automations

### Phase 6: API & CLI
Expose presence features via API and CLI.

**Deliverable**: Full programmatic access to presence features

## Dependencies

- US1 (Entity Discovery): Need entity sync for person/zone entities
- US2 (Architect): Tools used by Architect for presence-aware automations

## Risks

| Risk | Mitigation |
|------|------------|
| Calendar API varies by integration | Abstract common interface, graceful degradation |
| Privacy concerns with location | Explicit user consent, data minimization |
| GPS accuracy issues | Use zone radius appropriately, hysteresis |
| Multiple device trackers per person | Let HA handle via person entity |

## Estimated Effort

- MCP Client: 2-3 hours
- Data Models: 1-2 hours
- Agent Tools: 3-4 hours
- Context Providers: 2-3 hours
- Automation Helpers: 2-3 hours
- Database/API: 3-4 hours
- Tests: 3-4 hours

**Total**: ~18-23 hours
