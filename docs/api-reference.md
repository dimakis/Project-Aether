# API Reference

All endpoints are under `/api/v1`. Authentication is required via JWT token (cookie or Bearer header), API key (`X-API-Key` header or `api_key` query parameter), or passkey unless noted as public.

Interactive API docs: `http://localhost:8000/api/docs` (when running in debug mode).
Full OpenAPI spec: [`specs/001-project-aether/contracts/api.yaml`](../specs/001-project-aether/contracts/api.yaml)

---

## OpenAI-Compatible Endpoints

These endpoints allow any OpenAI-compatible client to work with Aether:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/models` | List available agents as "models" |
| `POST` | `/api/v1/chat/completions` | Chat with agents (supports `stream: true`) |
| `POST` | `/api/v1/feedback` | Submit feedback on responses |

---

## System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/health` | Public | Liveness probe |
| `GET` | `/api/v1/ready` | Public | Readiness probe (Kubernetes) |
| `GET` | `/api/v1/status` | Public | System status with component health |
| `GET` | `/api/v1/metrics` | Required | Operational metrics (request rates, latency, errors) |

---

## Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/auth/setup-status` | Public | Check if first-time setup is complete |
| `POST` | `/api/v1/auth/setup` | Public | First-time setup: validate HA, store config, return JWT (one-shot) |
| `POST` | `/api/v1/auth/login` | Public | Password login (checks DB hash, then env var fallback) |
| `POST` | `/api/v1/auth/login/ha-token` | Public | HA token login (validates against stored HA URL) |
| `POST` | `/api/v1/auth/logout` | Required | Clear session cookie |
| `GET` | `/api/v1/auth/me` | Required | Check session status |
| `GET` | `/api/v1/auth/google/url` | Required | Google OAuth URL |
| `POST` | `/api/v1/auth/google/callback` | Required | Google OAuth callback |

### Passkeys (WebAuthn)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/passkey/register/options` | Required | Start passkey registration |
| `POST` | `/api/v1/auth/passkey/register/verify` | Required | Complete passkey registration |
| `POST` | `/api/v1/auth/passkey/authenticate/options` | Public | Start passkey login |
| `POST` | `/api/v1/auth/passkey/authenticate/verify` | Public | Complete passkey login (returns JWT) |
| `GET` | `/api/v1/auth/passkeys` | Required | List registered passkeys |
| `DELETE` | `/api/v1/auth/passkeys/{id}` | Required | Delete a passkey |

---

## Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/conversations` | Start new conversation |
| `GET` | `/api/v1/conversations` | List conversations |
| `GET` | `/api/v1/conversations/{id}` | Get conversation with messages |
| `POST` | `/api/v1/conversations/{id}/messages` | Send a message |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation |

---

## Entities

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/entities` | List entities (with filtering) |
| `GET` | `/api/v1/entities/{id}` | Get entity details |
| `POST` | `/api/v1/entities/query` | Natural language entity query |
| `POST` | `/api/v1/entities/sync` | Trigger entity sync from HA |
| `GET` | `/api/v1/entities/domains/summary` | Domain counts |

---

## Devices & Areas

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/devices` | List devices |
| `GET` | `/api/v1/devices/{id}` | Get device details |
| `GET` | `/api/v1/areas` | List areas |
| `GET` | `/api/v1/areas/{id}` | Get area details |

---

## Insights

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/insights` | List insights |
| `GET` | `/api/v1/insights/pending` | List pending insights |
| `GET` | `/api/v1/insights/summary` | Insights summary |
| `GET` | `/api/v1/insights/{id}` | Get insight details |
| `POST` | `/api/v1/insights` | Create insight |
| `POST` | `/api/v1/insights/{id}/review` | Mark insight reviewed |
| `POST` | `/api/v1/insights/{id}/action` | Mark insight actioned |
| `POST` | `/api/v1/insights/{id}/dismiss` | Dismiss insight |
| `DELETE` | `/api/v1/insights/{id}` | Delete insight |
| `POST` | `/api/v1/insights/analyze` | Trigger analysis |

---

## Insight Schedules

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/insight-schedules` | List schedules |
| `POST` | `/api/v1/insight-schedules` | Create schedule |
| `GET` | `/api/v1/insight-schedules/{id}` | Get schedule |
| `PUT` | `/api/v1/insight-schedules/{id}` | Update schedule |
| `DELETE` | `/api/v1/insight-schedules/{id}` | Delete schedule |
| `POST` | `/api/v1/insight-schedules/{id}/run` | Manual trigger |

---

## Proposals

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/proposals` | List automation proposals (filterable by status) |
| `GET` | `/api/v1/proposals/pending` | List proposals awaiting approval |
| `GET` | `/api/v1/proposals/{id}` | Get proposal details with YAML |
| `POST` | `/api/v1/proposals` | Create a new proposal directly |
| `POST` | `/api/v1/proposals/{id}/approve` | Approve proposal |
| `POST` | `/api/v1/proposals/{id}/reject` | Reject proposal |
| `POST` | `/api/v1/proposals/{id}/deploy` | Deploy approved proposal to HA |
| `POST` | `/api/v1/proposals/{id}/rollback` | Rollback deployed proposal |
| `DELETE` | `/api/v1/proposals/{id}` | Delete proposal |

---

## Optimization

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/optimize` | Run optimization analysis |
| `GET` | `/api/v1/optimize/{job_id}` | Get optimization status |
| `GET` | `/api/v1/optimize/suggestions/list` | List automation suggestions |
| `POST` | `/api/v1/optimize/suggestions/{id}/accept` | Accept suggestion |
| `POST` | `/api/v1/optimize/suggestions/{id}/reject` | Reject suggestion |

---

## HA Registry

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/registry/sync` | Sync automations/scripts/scenes from HA |
| `GET` | `/api/v1/registry/automations` | List HA automations |
| `GET` | `/api/v1/registry/automations/{id}` | Get automation details |
| `GET` | `/api/v1/registry/automations/{id}/config` | Get automation YAML config |
| `GET` | `/api/v1/registry/scripts` | List HA scripts |
| `GET` | `/api/v1/registry/scripts/{id}` | Get script details |
| `GET` | `/api/v1/registry/scenes` | List HA scenes |
| `GET` | `/api/v1/registry/scenes/{id}` | Get scene details |
| `GET` | `/api/v1/registry/services` | List known services |
| `GET` | `/api/v1/registry/services/{id}` | Get service details |
| `POST` | `/api/v1/registry/services/call` | Call an HA service |
| `POST` | `/api/v1/registry/services/seed` | Seed common services |
| `GET` | `/api/v1/registry/helpers` | List HA helpers (input_boolean, etc.) |
| `POST` | `/api/v1/registry/helpers` | Create a helper entity |
| `DELETE` | `/api/v1/registry/helpers/{domain}/{input_id}` | Delete a helper entity |
| `GET` | `/api/v1/registry/summary` | Registry summary |

---

## Dashboards

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboards` | List Lovelace dashboards |
| `GET` | `/api/v1/dashboards/{url_path}/config` | Get dashboard configuration |

---

## Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/reports` | List analysis reports |
| `GET` | `/api/v1/reports/{id}` | Get report details |
| `GET` | `/api/v1/reports/{id}/communication` | Get report communication log |
| `GET` | `/api/v1/reports/{id}/artifacts/{filename}` | Serve report artifact (chart, data file) |

---

## Diagnostics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/diagnostics/ha-health` | HA health (unavailable entities, unhealthy integrations) |
| `GET` | `/api/v1/diagnostics/error-log` | Parsed HA error log with pattern matching |
| `GET` | `/api/v1/diagnostics/config-check` | HA config validation |
| `GET` | `/api/v1/diagnostics/traces/recent` | Recent agent traces from MLflow |

---

## Evaluations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/evaluations/summary` | Latest trace evaluation summary |
| `POST` | `/api/v1/evaluations/run` | Trigger on-demand trace evaluation |
| `GET` | `/api/v1/evaluations/scorers` | List available scorers |

---

## Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents` | List all agents with active config |
| `GET` | `/api/v1/agents/{name}` | Get agent by name |
| `PATCH` | `/api/v1/agents/{name}` | Update agent status |
| `POST` | `/api/v1/agents/{name}/clone` | Clone agent |
| `PATCH` | `/api/v1/agents/{name}/model` | Quick model switch |

### Agent Config Versions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents/{name}/config/versions` | List config versions |
| `POST` | `/api/v1/agents/{name}/config/versions` | Create config draft |
| `PATCH` | `/api/v1/agents/{name}/config/versions/{id}` | Update config draft |
| `DELETE` | `/api/v1/agents/{name}/config/versions/{id}` | Delete config version |
| `POST` | `/api/v1/agents/{name}/config/versions/{id}/promote` | Promote config |
| `POST` | `/api/v1/agents/{name}/config/rollback` | Rollback config |

### Agent Prompt Versions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents/{name}/prompt/versions` | List prompt versions |
| `POST` | `/api/v1/agents/{name}/prompt/versions` | Create prompt draft |
| `PATCH` | `/api/v1/agents/{name}/prompt/versions/{id}` | Update prompt draft |
| `DELETE` | `/api/v1/agents/{name}/prompt/versions/{id}` | Delete prompt version |
| `POST` | `/api/v1/agents/{name}/prompt/versions/{id}/promote` | Promote prompt |
| `POST` | `/api/v1/agents/{name}/prompt/rollback` | Rollback prompt |

### Agent Bulk Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/agents/{name}/promote-all` | Promote config + prompt drafts |
| `POST` | `/api/v1/agents/{name}/prompt/generate` | AI-generate system prompt |
| `POST` | `/api/v1/agents/seed` | Seed default agents |

---

## Activity

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/activity/stream` | SSE stream for real-time agent activity |

---

## Flow Grades

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/flow-grades` | Submit flow grade |
| `GET` | `/api/v1/flow-grades/{conversation_id}` | Get grades for conversation |
| `DELETE` | `/api/v1/flow-grades/{grade_id}` | Delete grade |

---

## HA Zones

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/zones` | List HA zones |
| `POST` | `/api/v1/zones` | Create zone |
| `PATCH` | `/api/v1/zones/{id}` | Update zone |
| `DELETE` | `/api/v1/zones/{id}` | Delete zone |
| `POST` | `/api/v1/zones/{id}/set-default` | Set default zone |
| `POST` | `/api/v1/zones/{id}/test` | Test zone connectivity |

---

## Model Ratings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/models/ratings` | List model ratings |
| `POST` | `/api/v1/models/ratings` | Create model rating |
| `GET` | `/api/v1/models/summary` | Model summaries |
| `GET` | `/api/v1/models/performance` | Model performance metrics |

---

## Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/webhooks/ha` | Receive HA webhook events (including `ios.notification_action_fired` for push notification HITL approval/rejection) |

---

## Traces

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/traces/{trace_id}/spans` | Get trace span tree for visualization |

---

## Workflows

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/workflows/presets` | List workflow presets for chat UI |

---

## LLM Usage

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/usage/summary` | Usage summary with cost (`?days=30`) |
| `GET` | `/api/v1/usage/daily` | Daily usage breakdown |
| `GET` | `/api/v1/usage/models` | Per-model usage breakdown |
| `GET` | `/api/v1/usage/conversation/{id}` | Conversation cost breakdown |

---

## See Also

- [CLI Reference](cli-reference.md) — terminal commands
- [Architecture](architecture.md) — system design and middleware pipeline
- [Getting Started](getting-started.md) — authentication setup
