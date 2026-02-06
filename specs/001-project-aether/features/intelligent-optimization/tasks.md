# Tasks: Intelligent Optimization & Multi-Agent Collaboration

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Migrated from**: `specs/001-project-aether/tasks.md` Phase 6b (US5)

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

- [ ] T221 [US5] Create src/agents/coordinator.py with AgentCoordinator:
  - register_agent(agent) - Register agents for coordination
  - request_analysis(from_agent, to_agent, query) - Inter-agent queries
  - handoff(from_agent, to_agent, context) - Transfer conversation context
  - broadcast_insight(insight) - Share insights across agents

- [ ] T222 [US5] Create AgentMessage model in src/graph/state.py:
  - from_agent: AgentRole
  - to_agent: AgentRole
  - message_type: "query" | "response" | "handoff" | "insight"
  - content: dict
  - context: dict (shared state)

- [ ] T223 [US5] Add inter-agent tools to src/tools/agent_tools.py:
  - request_data_analysis(query) - Architect asks DS for data
  - propose_automation(insight, suggestion) - DS proposes automation to Architect
  - query_entity_context(entity_ids) - Any agent queries Librarian
  - validate_automation(proposal) - Architect validates DS suggestions

## Data Scientist to Architect Integration

- [ ] T224 [US5] Create src/agents/ds_architect_bridge.py with:
  - AutomationSuggestion model (pattern, entities, proposed_trigger, proposed_action, confidence, evidence)
  - suggest_automation_from_pattern(pattern) - Convert insight to automation proposal
  - request_architect_review(suggestion) - Send to Architect for refinement
  - receive_architect_feedback(proposal_id, feedback) - Handle Architect response

- [ ] T225 [US5] Add "suggest automation" flow to DataScientistWorkflow:
  - When automation gap detected -> create AutomationSuggestion
  - Send to Architect via coordinator
  - Architect refines and creates full proposal
  - Return combined insight + proposal to user

- [ ] T226 [US5] Extend ArchitectAgent to handle DS suggestions:
  - receive_suggestion(suggestion) - Accept DS automation suggestions
  - refine_suggestion(suggestion) - Improve trigger/action design
  - create_proposal_from_suggestion(suggestion) - Generate full proposal

## Orchestrator Updates

- [ ] T227 [US5] Update src/graph/workflows.py with multi-agent orchestration:
  - Add optimization_workflow combining DS analysis -> Architect proposals
  - Add collaborative_analysis_workflow for complex queries
  - Implement interrupt points for user confirmation between agents

- [ ] T228 [US5] Create src/graph/nodes.py nodes for agent collaboration:
  - analyze_and_suggest - DS analyzes, suggests optimizations
  - architect_review - Architect reviews DS suggestions
  - combine_insights - Merge DS + Architect outputs
  - present_recommendations - Format final output for user

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
- [ ] T236 [P] [US5] Create tests/unit/test_agent_coordinator.py - Inter-agent messaging
- [ ] T237 [P] [US5] Create tests/unit/test_ds_architect_bridge.py - Suggestion flow

**Integration Tests**:
- [ ] T238 [US5] Create tests/integration/test_behavioral_workflow.py - Full behavioral analysis
- [ ] T239 [US5] Create tests/integration/test_agent_collaboration.py - DS -> Architect flow
- [ ] T240 [US5] Create tests/integration/test_optimization_api.py - Optimization endpoints

**E2E Tests**:
- [ ] T241 [US5] Create tests/e2e/test_optimization_flow.py - Full optimization: analyze -> suggest -> propose -> approve
- [ ] T242 [US5] Create tests/e2e/test_multi_agent_conversation.py - User query involving multiple agents
