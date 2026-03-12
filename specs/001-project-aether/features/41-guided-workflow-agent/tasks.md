# Tasks: Guided Workflow Agent

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 — Wire the Automation Builder Agent

- [ ] T4101 Create `src/agents/automation_builder/__init__.py` and `agent.py` with `AutomationBuilderAgent` class that:
  - Compiles the existing `automation_builder` graph with PostgreSQL checkpointing
  - Provides `start_session(user_message, session_id)` and `continue_session(user_message, session_id)` methods
  - Streams node outputs as SSE-compatible messages
  - Emits `emit_job_start` / `emit_job_status` / `emit_job_complete` events at each step
  - Handles the HITL interrupt at preview (pauses and streams the YAML preview)

- [ ] T4102 Enhance `preview_node` in `src/graph/nodes/automation_builder.py` to:
  - Call `seek_approval()` from `src/tools/approval_tools.py` to create an actual `AutomationProposal`
  - Include the `proposal_id` from the created proposal in the state
  - Format a user-friendly preview message with YAML and a link to the proposals page

- [ ] T4103 [P] Unit tests for `AutomationBuilderAgent` — mock LLM, verify streaming, verify job events, verify checkpoint resume

**Checkpoint**: Agent compiles and can stream a simple automation flow end-to-end with mock LLM

---

## Phase 2 — Orchestrator Routing

- [ ] T4104 Add `"create_automation"` intent to `OrchestratorAgent.classify_intent()` in `src/agents/orchestrator.py`:
  - Add intent patterns: "create automation", "make automation", "set up automation", "automate", "when X then Y", "turn on/off ... at/when"
  - When classified, set `target_agent = "automation_builder"` in `TaskPlan`

- [ ] T4105 Update `src/api/routes/openai_compat/handlers.py` to handle `agent="automation_builder"`:
  - When `agent` is `"automation_builder"` (explicit) or orchestrator routes to it (auto), invoke `AutomationBuilderAgent` instead of `ArchitectWorkflow`
  - Reuse existing SSE streaming format

- [ ] T4106 [P] Unit tests for orchestrator routing — verify "create an automation" classifies as `create_automation`, verify handler invokes correct agent

**Checkpoint**: Saying "create an automation" in auto mode routes to the builder

---

## Phase 3 — Chat Preset and Activity Integration

- [ ] T4107 Add "Create Automation" preset in `src/api/routes/workflows.py`:
  - Name: "Create Automation"
  - Description: "Guided step-by-step automation creation with live validation"
  - Agents: `["automation_builder"]`
  - Default agent: `automation_builder`

- [ ] T4108 Add step status emissions to each node in `src/graph/nodes/automation_builder.py`:
  - `gather_intent_node`: "Extracting automation intent..."
  - `validate_entities_node`: "Validating {n} entities..."
  - `check_duplicates_node`: "Checking for duplicates..."
  - `generate_yaml_node`: "Generating YAML (attempt {n})..."
  - `validate_yaml_node`: "Validating YAML..."
  - `preview_node`: "Automation ready for review"

- [ ] T4109 [P] Verify the WorkflowPresetSelector picks up the new preset automatically (no frontend changes needed — it reads from API)

**Checkpoint**: "Create Automation" preset visible in chat, activity panel shows step progress

---

## Phase 4 — Multi-turn Clarification

- [ ] T4110 Enhance `AutomationBuilderAgent` to support multi-turn clarification:
  - When `needs_clarification=True`, stream the clarification question, then pause (checkpoint)
  - On next user message, resume from checkpoint with the new message appended
  - Same pattern for `entity_errors` — stream suggestions, wait for user correction

- [ ] T4111 Add conversation threading: `AutomationBuilderAgent` uses `thread_id` (session ID) for LangGraph checkpointing so the user can pick up where they left off

- [ ] T4112 [P] Integration test: multi-turn flow (user sends intent -> agent asks clarification -> user responds -> agent proceeds to YAML -> user approves)

**Checkpoint**: Multi-turn guided flow works end-to-end

---

## Phase 5 — Polish and Documentation

- [ ] T4113 Add help text to the "Create Automation" preset description explaining what users can do
- [ ] T4114 Ensure error handling: LLM failures, invalid state, timeout — all surface user-friendly messages
- [ ] T4115 Run `make ci-local` and fix any issues

**Checkpoint**: Feature complete, CI green

---

`[P]` = Can run in parallel (different files, no dependencies)
