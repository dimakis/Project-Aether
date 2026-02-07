**Completed**: 2026-02-07

# Tasks: Model Routing & Multi-Agent Communication

**Input**: [spec.md](./spec.md), [plan.md](./plan.md)
**Status**: ✅ Complete (2026-02-07)

## Phase 1: Model Context Infrastructure

- [x] T-MR01 Create src/agents/model_context.py with ModelContext dataclass and contextvars
- [x] T-MR02 Add per-agent model settings to src/settings.py (data_scientist_model, data_scientist_temperature)

## Phase 2: Propagation Integration

- [x] T-MR03 Wrap openai_compat.py workflow calls in model_context()
- [x] T-MR04 Wrap chat.py workflow calls in model_context()
- [x] T-MR05 Update DataScientistAgent.llm to resolve model from context > agent setting > default
- [x] T-MR06 Wrap agent_tools.py delegation calls (analyze_energy, diagnose_issue) in model_context()

## Phase 3: Insight Automation Suggestions

- [x] T-MR07 Add automation_suggestion field to AnalysisState in src/graph/state.py
- [x] T-MR08 Update Data Scientist _generate_automation_suggestion for high-confidence insights
- [x] T-MR09 Update agent_tools.py formatters to append automation suggestion prompt when present

## Phase 4: Inter-Agent Trace Propagation

- [x] T-MR10 Add parent_span_id to ModelContext
- [x] T-MR11 Propagate parent_span_id in Data Scientist trace_span for parent-child MLflow linking

## Phase 5: Tests

- [x] T-MR12 [P] Create tests/unit/test_model_context.py - context manager, resolution order (15 tests)
- [x] T-MR13 [P] Create tests/unit/test_model_propagation.py - DS model selection with/without context (6 tests)
- [x] T-MR14 [P] Create tests/unit/test_insight_suggestions.py - automation suggestion formatting (12 tests)

## Phase 6: Task Tracking Updates

- [x] T-MR15 Update specs/001-project-aether/tasks.md T173-T177 with scope decisions
