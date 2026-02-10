# Aether UI

React frontend for Project Aether — the conversational interface for your smart home.

## Pages

| Page | Path | Description |
|------|------|-------------|
| **Dashboard** | `/` | System overview — entity counts, pending proposals, recent insights |
| **Chat** | `/chat` | Conversational interface with streaming, model selection, agent activity panel |
| **Proposals** | `/proposals` | View, approve, deploy, or rollback automation proposals |
| **Insights** | `/insights` | Browse analysis results — energy, behavioral, diagnostic |
| **Entities** | `/entities` | Browse and search discovered HA entities |
| **Registry** | `/registry` | HA registry — automations, scripts, scenes, services |
| **Agents** | `/agents` | Agent configuration — model, temperature, prompt versioning |
| **Schedules** | `/schedules` | Manage cron schedules and webhook triggers |
| **LLM Usage** | `/usage` | Token tracking, cost by model, daily trends |
| **Diagnostics** | `/diagnostics` | HA health, error log, integration status, recent traces |
| **Login** | `/login` | Passkey (Face ID / Touch ID), HA token, or password login |

## Tech Stack

- **React 19** with TypeScript
- **Vite** for build and HMR
- **TanStack Query** (React Query) for server state
- **Tailwind CSS** + **shadcn/ui** components
- **D3** for force-directed agent topology visualization

## Development

```bash
# From the project root (recommended)
make ui-dev          # Start dev server with HMR

# Or directly
cd ui
npm install
npm run dev          # http://localhost:3000
```

The dev server proxies `/api` requests to `http://localhost:8000` (the Aether API).

## Build

```bash
# From the project root
make ui-build

# Or directly
cd ui
npm run build        # Output to ui/dist/
```

## Running with the API

```bash
# Start everything (infrastructure + API + UI)
make run-ui

# Or start separately:
make run             # Infrastructure + API
make ui-dev          # UI dev server (separate terminal)
```

## Configuration

The Vite dev server is configured in `vite.config.ts`:

- **Port**: 3000
- **API proxy**: `/api` -> `http://localhost:8000`
- **WebSocket proxy**: `/api/v1/conversations/*/stream` -> `ws://localhost:8000`

No additional environment variables are required for development. The UI reads all configuration from the API.
