# Plan: Model Routing & Multi-Agent Communication

**Feature**: [spec.md](./spec.md) | **Tasks**: [tasks.md](./tasks.md)

## Implementation Phases

### Phase 1: Model Context Infrastructure
Create `ModelContext` using Python `contextvars` (same pattern as `src/tracing/context.py`).

**Deliverable**: Context manager that carries model_name, temperature, parent_span_id

### Phase 2: Per-Agent Settings
Add optional per-agent model overrides to Settings with resolution chain.

**Deliverable**: DATA_SCIENTIST_MODEL / DATA_SCIENTIST_TEMPERATURE env vars

### Phase 3: Propagation Integration
Wire model_context into openai_compat.py, chat.py, and agent_tools.py delegation calls.

**Deliverable**: User's model selection flows through to Data Scientist

### Phase 4: Insight Automation Suggestions
Add automation_suggestion field to AnalysisState; format in agent_tools.py.

**Deliverable**: Data Scientist can suggest automations via tool response

### Phase 5: Trace Propagation
Use parent_span_id from model context for MLflow parent-child linking.

**Deliverable**: Delegated agent traces appear as children of caller's trace

## Dependencies

- US2 (Architect): Agent tool delegation already works
- US3 (Data Scientist): Agent and workflow already functional
- src/tracing/context.py: Pattern for contextvars

## Risks

| Risk | Mitigation |
|------|------------|
| Context not propagated across async boundaries | contextvars works natively with asyncio |
| Per-agent settings conflict with user selection | Clear resolution order documented |
| Automation suggestion noise | Only attach for high-confidence, high-impact insights |

## Estimated Effort

- Model Context + Settings: 1-2 hours
- Propagation Integration: 1-2 hours
- Insight Suggestions: 1 hour
- Trace Propagation: 1 hour
- Tests: 1-2 hours

**Total**: ~6-8 hours
