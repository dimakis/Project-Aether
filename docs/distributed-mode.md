# Distributed Mode Guide

Aether can run agents as separate containers communicating via the [A2A protocol](https://google.github.io/A2A/). This guide covers how to start, verify, and troubleshoot the distributed deployment locally.

## Architecture

```
User  -->  API Gateway (:8000)  -->  Architect (:8001)  -->  DS Orchestrator (:8002)  -->  DS Analysts (:8003)
               |                        |                        |                            |
               v                        v                        v                            v
           PostgreSQL              PostgreSQL              PostgreSQL                    gVisor Sandbox
           MLflow                  MLflow                  MLflow
```

**API Gateway** (monolith app) handles HTTP routing, auth, and SSE streaming. When `DEPLOYMENT_MODE=distributed`, it delegates to the Architect container via A2A instead of running the agent in-process.

**Architect** is the primary conversational agent. It handles user intent, generates proposals, and delegates analysis to the DS Orchestrator.

**DS Orchestrator** coordinates the Data Science team. It decides which analysts to run, manages confidence-based retry loops, and synthesizes findings.

**DS Analysts** contains Energy, Behavioral, and Diagnostic analysts in a single container. They share analysis state in-process and execute sequentially.

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

# Architect
curl http://localhost:8001/health

# DS Orchestrator
curl http://localhost:8002/health

# DS Analysts
curl http://localhost:8003/health
```

Check Agent Cards:

```bash
# Architect capabilities
curl http://localhost:8001/.well-known/agent-card.json | python -m json.tool

# DS Analysts capabilities
curl http://localhost:8003/.well-known/agent-card.json | python -m json.tool
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
- Port conflict (8001-8003 already in use)

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

## Comparison: Monolith vs Distributed

| Aspect | Monolith | Distributed |
|--------|----------|-------------|
| Containers | 1 (app) + infra | 4 (gateway + 3 agents) + infra |
| Latency | In-process calls | HTTP round-trips (~5-20ms/hop) |
| Scaling | Single process | Independent per agent |
| Debugging | Single log stream | Per-container logs |
| Resource isolation | Shared | Per-container limits |
| Development | Hot-reload friendly | Requires rebuild on code change |
| Command | `make run` | `make run-distributed` |
