# Distributed Mode Guide

Aether can run agents as separate containers communicating via the [A2A protocol](https://google.github.io/A2A/). This guide covers how to start, verify, and troubleshoot the distributed deployment locally.

## Architecture

```
User  -->  API Gateway (:8000)  -->  Orchestrator (:8007)  -->  Architect (:8001)
                                                                     |
                                         +---------------------------+---------------------------+
                                         |                           |                           |
                                   DS Orchestrator (:8002)    Developer (:8004)        Dashboard Designer (:8006)
                                         |
                                   DS Analysts (:8003)           Librarian (:8005)
                                         |
                                    gVisor Sandbox
```

**7 agent service containers** + API Gateway + infrastructure:

| Container | Port | Agent(s) | Pattern |
|-----------|------|----------|---------|
| API Gateway | 8000 | None (routing) | Gateway |
| Architect | 8001 | ArchitectAgent | Single-agent |
| DS Orchestrator | 8002 | DataScientistAgent | Single-agent |
| DS Analysts | 8003 | Energy + Behavioral + Diagnostic | Multi-agent |
| Developer | 8004 | DeveloperAgent | Single-agent |
| Librarian | 8005 | LibrarianAgent | Single-agent |
| Dashboard Designer | 8006 | DashboardDesignerAgent | Single-agent |
| Orchestrator | 8007 | OrchestratorAgent | Single-agent |

## Prerequisites

- Podman or Docker with Compose
- A configured `.env` file (see [Configuration](configuration.md))
- The base infrastructure running (Postgres, MLflow)

## Quick Start

```bash
# Build all service images
make build-services

# Start distributed mode
make run-distributed
```

This starts:
- PostgreSQL and MLflow (infrastructure)
- Aether API gateway (monolith with DEPLOYMENT_MODE=distributed)
- Architect service
- DS Orchestrator service
- DS Analysts service

## Verify Services

Check that all containers are healthy:

```bash
# Gateway
curl http://localhost:8000/api/v1/health

# All agent services
for port in 8001 8002 8003 8004 8005 8006 8007; do
  echo "Port $port: $(curl -s http://localhost:$port/health)"
done
```

Check Agent Cards:

```bash
# Any agent service
curl http://localhost:8001/.well-known/agent-card.json | python -m json.tool
```

## Send a Test Request

```bash
# Send a chat message through the full chain
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Analyze my energy usage"}],
    "stream": true,
    "agent": "auto"
  }'
```

With `agent: "auto"`, the request flows: Gateway -> Orchestrator -> Architect -> DS Orchestrator -> DS Analysts.

With `agent: "architect"`, it goes directly to the Architect service.

## Switch Back to Monolith

```bash
# Stop distributed mode
podman-compose -f infrastructure/podman/compose.yaml \
  -f infrastructure/podman/compose.distributed.yaml \
  --profile full down

# Start monolith mode
make run
```

Or simply use `make run` / `make run-prod` which use the base compose file without the distributed override.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOYMENT_MODE` | `monolith` | `monolith` (all in-process) or `distributed` (A2A services) |
| `ARCHITECT_SERVICE_URL` | `http://architect:8000` | Architect A2A service endpoint |
| `DS_ORCHESTRATOR_URL` | `http://ds-orchestrator:8000` | DS Orchestrator A2A service endpoint |
| `DS_ANALYSTS_URL` | `http://ds-analysts:8000` | DS Analysts A2A service endpoint |

These are set automatically by `compose.distributed.yaml`. You only need to configure them manually when running services on the host.

## Container Images

All agent services use a single parameterized Containerfile:

```bash
# Build individually
podman build --build-arg AETHER_SERVICE=architect \
  -t aether-architect:latest \
  -f infrastructure/podman/Containerfile.service .

podman build --build-arg AETHER_SERVICE=ds_orchestrator \
  -t aether-ds-orchestrator:latest \
  -f infrastructure/podman/Containerfile.service .

podman build --build-arg AETHER_SERVICE=ds_analysts \
  -t aether-ds-analysts:latest \
  -f infrastructure/podman/Containerfile.service .

# Or build all at once
make build-services
```

## Troubleshooting

### Service not healthy

```bash
# Check container logs
podman logs aether-architect
podman logs aether-ds-orchestrator
podman logs aether-ds-analysts
```

Common causes:
- Database not ready (check Postgres health first)
- Missing `.env` file (LLM API key needed for agent initialization)
- Port conflict (8001-8007 already in use)

### Connection refused between services

Containers communicate via the `aether-network` Docker network. If one service can't reach another:

```bash
# Verify all containers are on the same network
podman network inspect aether-network
```

### Requests not reaching agent services

Check that `DEPLOYMENT_MODE=distributed` is set on the gateway:

```bash
podman exec aether-app env | grep DEPLOYMENT_MODE
```

If it shows `monolith`, the gateway runs agents in-process and ignores the service containers.

## Observability Stack

Add Prometheus, Grafana, and Loki for metrics, dashboards, and centralized logs:

```bash
make run-observed    # distributed + observability
make down-observed   # stop everything
```

| Service | URL | Purpose |
|---------|-----|---------|
| Prometheus | http://localhost:9090 | Metrics scraping (every 15s from all containers) |
| Grafana | http://localhost:3001 | Dashboards (login: admin/admin) |
| Loki | http://localhost:3100 | Log aggregation (queried via Grafana) |

Grafana comes pre-provisioned with:
- Prometheus and Loki data sources
- **Agent Health** dashboard: request rate, p95 latency, error rate, active requests

To view logs in Grafana: go to Explore, select Loki data source, and query by container label.

## Comparison: Deployment Modes

| Aspect | Monolith | Distributed | Observed |
|--------|----------|-------------|----------|
| Containers | 1 (app) + infra | 8 (gateway + 7 agents) + infra | 8 agents + 4 observability + infra |
| Latency | In-process calls | HTTP round-trips (~5-20ms/hop) | Same as distributed |
| Scaling | Single process | Independent per agent | Same + metrics visibility |
| Debugging | Single log stream | Per-container logs | Centralized in Grafana |
| Metrics | MLflow traces only | MLflow + /metrics endpoints | Full Prometheus + Grafana |
| Command | `make run` | `make run-distributed` | `make run-observed` |
