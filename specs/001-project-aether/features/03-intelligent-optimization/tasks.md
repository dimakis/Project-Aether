# Tasks: Intelligent Optimization & Multi-Agent Collaboration

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Migrated from**: `specs/001-project-aether/tasks.md` Phase 6b (US5)

---

## Reconciliation with Feature 08-C (Model Routing & Multi-Agent)

**Date**: 2026-02-07 | **Reference**: `features/08-C-model-routing-multi-agent/`

Feature 08-C implemented a simpler tool-delegation pattern for multi-agent communication,
which supersedes several tasks originally planned here. The decisions are:

- **AgentCoordinator class** (T221): **Cancelled**. Tool-delegation via `agent_tools.py` + model context propagation handles coordination without a dedicated class. (per 08-C T173)
- **AgentMessage model** (T222): **Cancelled**. Single-user system uses structured tool returns (e.g., `AnalysisState.automation_suggestion`) instead of async message queues. (per 08-C T176)
- **Inter-agent tools** (T223): **Adapted**. `analyze_energy`/`diagnose_issue` tools already exist. Simplified to adding a `propose_automation` tool in `agent_tools.py`. (per 08-C T174)
- **DS-Architect bridge module** (T224): **Simplified**. `AutomationSuggestion` Pydantic model added to `src/graph/state.py` instead of a separate `ds_architect_bridge.py` module. Existing `automation_suggestion` reverse-communication pattern on `AnalysisState` is reused. (per 08-C T174)
- **T225-T228**: **Implemented with simplified approach** — no coordinator, no message queue; uses tool-delegation and structured state.

---

## New MCP Capabilities

- [ ] T211 [US5] Add `get_logbook()` method to src/mcp/client.py - fetch logbook entries from `/api/logbook/{timestamp}` endpoint
- [ ] T212 [US5] Create src/mcp/logbook.py with LogbookHistoryClient:
  - Parse logbook entries (entity_id, state, context, timestamp, user)
  - Filter by domain, entity, time range
  - Aggregate by action type (button_press, automation_triggered, script_run, state_change)
- [ ] T213 [P] [US5] Add logbook parsers to src/mcp/parsers.py (parse_logbook_entry, parse_logbook_list)

## New Analysis Types

- [ ] T214 [US5] Extend AnalysisType enum in src/graph/state.py with:
  - BEHAVIOR_ANALYSIS - Usage patterns from logbook
  - AUTOMATION_ANALYSIS - Automation effectiveness scoring
  - AUTOMATION_GAP_DETECTION - Find manual patterns to automate
  - CORRELATION_DISCOVERY - Find entity relationships
  - DEVICE_HEALTH - Detect anomalies and potential issues
  - COST_OPTIMIZATION - Energy cost projections with savings recommendations

## Data Scientist Agent Extensions

- [ ] T215 [US5] Create src/mcp/behavioral.py with BehavioralAnalysisClient:
  - get_button_usage(hours) - Button/switch press frequency and timing
  - get_automation_effectiveness() - Trigger counts, manual overrides, efficiency scores
  - find_correlations(entity_ids) - Discover entity relationships from timing patterns
  - detect_automation_gaps() - Find repeating manual patterns that could be automated
  - get_device_health_report() - Identify devices with unusual/missing activity

- [ ] T216 [US5] Extend DataScientistAgent._build_analysis_prompt() with prompts for new analysis types
- [ ] T217 [US5] Add DATA_SCIENTIST_BEHAVIORAL_PROMPT in src/agents/data_scientist.py for behavioral insights
- [ ] T218 [US5] Create _collect_behavioral_data() method in DataScientistAgent for logbook aggregation

## Insight Types Extension

- [ ] T219 [US5] Extend InsightType enum in src/storage/entities/insight.py with:
  - AUTOMATION_GAP - "You do X manually, suggest automation"
  - AUTOMATION_INEFFICIENCY - "Automation Y could be improved"
  - CORRELATION - "Entity A and B are often used together"
  - DEVICE_HEALTH - "Device may need attention"
  - COST_SAVING - "This change would save $X/month"
  - BEHAVIORAL_PATTERN - "Usage pattern detected"

- [ ] T220 [US5] Create Alembic migration for InsightType enum extension in alembic/versions/006_insight_types.py

## Agent-to-Agent Communication Framework

- [x] T221 [US5] ~~Create src/agents/coordinator.py with AgentCoordinator~~ — **Cancelled**: Tool-delegation pattern via agent_tools.py handles coordination (per 08-C T173)

- [x] T222 [US5] ~~Create AgentMessage model in src/graph/state.py~~ — **Cancelled**: Structured tool returns suffice for single-user system (per 08-C T176)

- [ ] T223 [US5] Add `propose_automation` tool to src/tools/agent_tools.py — **Adapted** from original scope (per 08-C T174):
  - propose_automation(suggestion) - DS proposes automation to Architect via tool delegation
  - ~~request_data_analysis, query_entity_context, validate_automation~~ — already covered by existing analyze_energy/diagnose_issue/discover_entities tools

## Data Scientist to Architect Integration

- [ ] T224 [US5] Add AutomationSuggestion model to src/graph/state.py — **Simplified** from original ds_architect_bridge.py (per 08-C T174):
  - AutomationSuggestion Pydantic model (pattern, entities, proposed_trigger, proposed_action, confidence, evidence, source_insight_type)
  - Replaces plain `str | None` automation_suggestion field on AnalysisState
  - ~~src/agents/ds_architect_bridge.py~~ — not needed; model lives in state.py, tool logic in agent_tools.py

- [ ] T225 [US5] Add "suggest automation" flow to DataScientistWorkflow:
  - When automation gap detected -> create AutomationSuggestion (structured model, not plain string)
  - Architect receives suggestion via `propose_automation` tool delegation (no coordinator)
  - Architect refines and creates full proposal
  - Return combined insight + proposal to user

- [ ] T226 [US5] Extend ArchitectAgent to handle DS suggestions:
  - receive_suggestion(suggestion) - Accept AutomationSuggestion and generate proposal
  - Uses existing LLM + proposal creation infrastructure

## Orchestrator Updates

- [ ] T227 [US5] Update src/graph/workflows.py with optimization workflow:
  - Add build_optimization_graph() combining DS analysis -> Architect proposals
  - Add run_optimization_workflow() execution function
  - Register in WORKFLOW_REGISTRY

- [ ] T228 [US5] Create src/graph/nodes.py optimization nodes:
  - collect_behavioral_data_node - Collect logbook/behavioral data
  - analyze_and_suggest_node - DS analyzes, produces insights + suggestions
  - architect_review_node - Architect reviews DS suggestions via tool delegation
  - present_recommendations_node - Format final output for user

## API Endpoints

- [ ] T229 [P] [US5] Create optimization schemas in src/api/schemas/optimization.py:
  - OptimizationRequest (analysis_types, time_range, focus_areas)
  - OptimizationResult (insights, suggestions, proposals)
  - AutomationSuggestion (pattern, confidence, proposed_automation)

- [ ] T230 [US5] Create src/api/routes/optimization.py:
  - POST /optimize - Run full optimization analysis
  - GET /optimize/suggestions - List pending automation suggestions
  - POST /optimize/suggestions/{id}/accept - Accept and create proposal
  - POST /optimize/suggestions/{id}/reject - Reject suggestion

## CLI Commands

- [ ] T231 [US5] Add `aether optimize` command in src/cli/main.py:
  - `aether optimize --type energy|behavior|all` - Run optimization analysis
  - `aether optimize suggestions` - List automation suggestions
  - `aether optimize accept <id>` - Accept suggestion, create proposal

- [ ] T232 [US5] Add `aether analyze behavior` command:
  - `aether analyze behavior --days 7` - Behavioral analysis
  - `aether analyze automations` - Automation effectiveness report
  - `aether analyze correlations` - Entity correlation discovery

## Tests (Constitution: Reliability & Quality)

**Unit Tests**:
- [ ] T233 [P] [US5] Create tests/unit/test_mcp_logbook.py - Logbook client and parsing
- [ ] T234 [P] [US5] Create tests/unit/test_behavioral_analysis.py - Pattern detection
- [ ] T235 [P] [US5] Create tests/unit/test_automation_gap_detection.py - Gap detection logic
- [x] T236 [P] [US5] ~~Create tests/unit/test_agent_coordinator.py~~ — **Cancelled**: No AgentCoordinator class (per 08-C)
- [ ] T237 [P] [US5] Create tests/unit/test_optimization_flow.py - Suggest-to-proposal tool flow (replaces ds_architect_bridge tests)

**Integration Tests**:
- [ ] T238 [US5] Create tests/integration/test_behavioral_workflow.py - Full behavioral analysis
- [ ] T239 [US5] Create tests/integration/test_agent_collaboration.py - DS -> Architect flow
- [ ] T240 [US5] Create tests/integration/test_optimization_api.py - Optimization endpoints

**E2E Tests**:
- [ ] T241 [US5] Create tests/e2e/test_optimization_flow.py - Full optimization: analyze -> suggest -> propose -> approve
- [ ] T242 [US5] Create tests/e2e/test_multi_agent_conversation.py - User query involving multiple agents
