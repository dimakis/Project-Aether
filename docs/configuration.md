# Configuration

LLM providers, per-agent model overrides, failover, usage tracking, and all environment variables.

---

## LLM Providers

Project Aether supports multiple LLM backends. Configure in your `.env`:

### OpenRouter (Recommended — access to 100+ models)

```bash
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=anthropic/claude-sonnet-4
```

### OpenAI Direct

```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4o
```

### Google Gemini

```bash
LLM_PROVIDER=google
GOOGLE_API_KEY=your-google-key
LLM_MODEL=gemini-2.0-flash
```

### Local Ollama (Free, private)

```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral:latest
# No API key needed
```

### Other OpenAI-Compatible APIs

```bash
LLM_PROVIDER=together  # or groq, custom
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.together.xyz/v1
LLM_MODEL=meta-llama/Llama-3-70b-chat-hf
```

---

## Per-Agent Model Overrides

Optimize cost by using cheaper models for specific agents:

```bash
# Global (used by Architect)
LLM_MODEL=anthropic/claude-sonnet-4

# DS Team specialists use a cheaper model for script generation
DATA_SCIENTIST_MODEL=gpt-4o-mini
DATA_SCIENTIST_TEMPERATURE=0.3
```

Resolution order: **UI model selection > per-agent `.env` setting > global default**.

---

## LLM Failover

Configure a fallback provider for resilience:

```bash
# Primary provider
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=anthropic/claude-sonnet-4

# Fallback provider (used when primary fails after retries)
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_MODEL=gpt-4o
```

The circuit breaker opens after 5 consecutive failures and retries after a 60-second cooldown.

---

## LLM Usage Tracking

Every LLM call is automatically tracked with token counts and estimated costs.

### Dashboard

Navigate to **LLM Usage** in the sidebar to see:
- **Summary cards**: total calls, tokens, estimated cost, models used
- **Daily trends**: chart of token usage and cost over time
- **Per-model breakdown**: usage and cost per model
- **Conversation costs**: cost breakdown per conversation

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/usage/summary?days=30` | Usage summary with cost |
| `GET` | `/api/v1/usage/daily` | Daily usage breakdown |
| `GET` | `/api/v1/usage/models` | Per-model usage |
| `GET` | `/api/v1/usage/conversation/{id}` | Conversation cost |

### Custom Pricing

Pricing data covers OpenAI, Anthropic, Google, Meta, DeepSeek, and Mistral models. The pricing table is in `src/llm/usage.py` (previously `src/llm_pricing.py`).

---

## Environment Variables

Complete reference of all environment variables from `src/settings.py`:

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (`development`, `staging`, `production`, `testing`) |
| `DEBUG` | `false` | Enable debug mode |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | `5` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Max overflow connections |
| `DATABASE_POOL_TIMEOUT` | `30` | Pool timeout (seconds) |

### Home Assistant

| Variable | Default | Description |
|----------|---------|-------------|
| `HA_URL` | — | Home Assistant URL |
| `HA_URL_REMOTE` | — | Remote HA URL (for external access) |
| `HA_TOKEN` | — | Home Assistant long-lived access token |

### LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openrouter` | LLM provider (`openrouter`, `openai`, `google`, `ollama`, `together`, `groq`) |
| `LLM_API_KEY` | — | LLM API key |
| `LLM_MODEL` | `anthropic/claude-sonnet-4` | Default LLM model |
| `LLM_TEMPERATURE` | `0.7` | Default temperature |
| `LLM_BASE_URL` | — | Custom base URL for OpenAI-compatible APIs |
| `DATA_SCIENTIST_MODEL` | — | Override model for DS Team specialists |
| `DATA_SCIENTIST_TEMPERATURE` | — | Override temperature for DS Team |
| `LLM_FALLBACK_PROVIDER` | — | Fallback LLM provider |
| `LLM_FALLBACK_MODEL` | — | Fallback LLM model |
| `GOOGLE_API_KEY` | — | Google Gemini API key |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `http://localhost:5002` | MLflow server URL |
| `MLFLOW_EXPERIMENT_NAME` | `aether` | MLflow experiment name |

### API

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `API_WORKERS` | `1` | Uvicorn worker count |
| `PUBLIC_URL` | — | Public URL for external access |
| `API_KEY` | — | API authentication key (empty = auth disabled in dev) |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_USERNAME` | `admin` | Username for password login |
| `AUTH_PASSWORD` | — | Password for login (DB password from setup takes priority) |
| `JWT_SECRET` | — | JWT signing secret (auto-derived if empty) |
| `JWT_EXPIRY_HOURS` | `72` | JWT token expiry |
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | — | Google OAuth client secret |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated allowed CORS origins |

### WebAuthn

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBAUTHN_RP_ID` | `localhost` | Relying party ID (your domain) |
| `WEBAUTHN_RP_NAME` | `Aether` | Display name |
| `WEBAUTHN_ORIGIN` | `http://localhost:3000` | Full origin URL |

### Process Roles

| Variable | Default | Description |
|----------|---------|-------------|
| `AETHER_ROLE` | `all` | Process role (`all`, `api`, `scheduler`) |

### Scheduler

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULER_ENABLED` | `true` | Enable APScheduler |
| `SCHEDULER_TIMEZONE` | `UTC` | Scheduler timezone |
| `WEBHOOK_SECRET` | — | Secret for HA webhook validation |

### Trace Evaluation

| Variable | Default | Description |
|----------|---------|-------------|
| `TRACE_EVAL_ENABLED` | `false` | Enable automatic trace evaluation |
| `TRACE_EVAL_CRON` | `0 3 * * *` | Cron schedule for trace evaluation |
| `TRACE_EVAL_MAX_TRACES` | `100` | Max traces to evaluate per run |

### Discovery

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCOVERY_SYNC_ENABLED` | `false` | Enable periodic entity sync |
| `DISCOVERY_SYNC_INTERVAL_MINUTES` | `60` | Sync interval |

### Timeouts

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOL_TIMEOUT_SECONDS` | `30` | Default tool execution timeout |
| `ANALYSIS_TOOL_TIMEOUT_SECONDS` | `120` | Analysis tool timeout |

### Sandbox

| Variable | Default | Description |
|----------|---------|-------------|
| `SANDBOX_ENABLED` | `true` | Enable gVisor sandbox |
| `SANDBOX_TIMEOUT_SECONDS` | `30` | Default sandbox timeout |
| `SANDBOX_ARTIFACTS_ENABLED` | `true` | Enable artifact collection from sandbox |
| `SANDBOX_TIMEOUT_QUICK` | `15` | Quick analysis timeout |
| `SANDBOX_TIMEOUT_STANDARD` | `30` | Standard analysis timeout |
| `SANDBOX_TIMEOUT_DEEP` | `60` | Deep analysis timeout |
| `SANDBOX_MEMORY_QUICK` | `256m` | Quick analysis memory limit |
| `SANDBOX_MEMORY_STANDARD` | `512m` | Standard analysis memory limit |
| `SANDBOX_MEMORY_DEEP` | `1g` | Deep analysis memory limit |

---

## See Also

- [Getting Started](getting-started.md) — authentication and deployment
- [Architecture](architecture.md) — system design, LLM factory, circuit breaker details
- [Development](development.md) — dev setup and project structure
