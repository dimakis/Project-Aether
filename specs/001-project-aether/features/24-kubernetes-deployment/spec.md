# Feature 24: Kubernetes Deployment

## Summary

Create production-grade Kubernetes manifests and Helm chart for deploying Aether on K8s clusters. This includes proper separation of API and scheduler workloads, database migration strategy, ingress configuration, secret management, network policies, and horizontal pod autoscaling.

## Prerequisites

The following Phase 1 changes are already implemented:

- `AETHER_ROLE` setting for process role separation (api/scheduler/all)
- Scheduler guard that prevents duplicate job execution across replicas
- `/api/v1/ready` readiness probe endpoint (checks DB connectivity)
- Rate limiter using `X-Forwarded-For` for real client IP behind ingress
- Containerfile with `--proxy-headers`, `--forwarded-allow-ips`, and `--timeout-graceful-shutdown`
- Security headers (HSTS, CSP, Permissions-Policy)

## Architecture

```
                    ┌─────────────────┐
                    │  Ingress (nginx) │
                    │  TLS termination │
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
         ┌──────┴──────┐ ┌──┴───┐ ┌──────┴──────┐
         │ API Pods (N) │ │ UI   │ │ Scheduler   │
         │ AETHER_ROLE  │ │ Pods │ │ Pod (1)     │
         │ = api        │ │ (N)  │ │ AETHER_ROLE │
         │ HPA: 2-8     │ │      │ │ = scheduler │
         └──────┬──────┘ └──────┘ └──────┬──────┘
                │                         │
         ┌──────┴─────────────────────────┴──────┐
         │         PostgreSQL (StatefulSet)        │
         │         + PVC for persistent storage    │
         └─────────────────┬──────────────────────┘
                           │
         ┌─────────────────┴──────────────────────┐
         │         MLflow (Deployment, optional)    │
         └────────────────────────────────────────┘
```

## Deliverables

### K8s Manifests (`infrastructure/k8s/`)

| File | Description |
|------|-------------|
| `namespace.yaml` | `aether` namespace with resource quotas |
| `configmap.yaml` | Non-secret configuration (environment, log level, HA URL) |
| `secrets.yaml` | Template for K8s Secrets (JWT_SECRET, LLM_API_KEY, HA_TOKEN, DB password) |
| `api-deployment.yaml` | API Deployment with HPA, probes, security context |
| `scheduler-deployment.yaml` | Single-replica scheduler Deployment |
| `ui-deployment.yaml` | UI nginx Deployment |
| `postgres-statefulset.yaml` | PostgreSQL StatefulSet with PVC |
| `mlflow-deployment.yaml` | MLflow tracking server Deployment |
| `services.yaml` | ClusterIP Services for all components |
| `ingress.yaml` | Ingress with TLS, path-based routing |
| `network-policies.yaml` | Pod-to-pod communication restrictions |
| `hpa.yaml` | HorizontalPodAutoscaler for API tier |
| `migration-job.yaml` | One-shot Job for `alembic upgrade head` |
| `kustomization.yaml` | Kustomize base with environment overlays |

### Deployment Targets

#### API Deployment
- 2+ replicas, HPA (CPU/memory autoscaling, 2-8 pods)
- Liveness probe: `GET /api/v1/health` (lightweight, no deps)
- Readiness probe: `GET /api/v1/ready` (checks DB)
- Startup probe: 30s initial delay for migration time
- Resource requests: 256Mi RAM, 250m CPU
- Resource limits: 1Gi RAM, 1000m CPU
- Security context: `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`
- Pod anti-affinity for high availability
- Environment: `AETHER_ROLE=api`

#### Scheduler Deployment
- **Single replica** (critical -- prevents duplicate job execution)
- PodDisruptionBudget: `minAvailable: 0` (allow rolling updates)
- Same probes and security context as API
- Environment: `AETHER_ROLE=scheduler`

#### UI Deployment
- 2+ replicas, simple HTTP health probes
- Nginx serving static React build
- API proxy via ingress path routing (not nginx upstream)

#### Database Migration Strategy
- Run as a Kubernetes Job (pre-deployment)
- Uses `alembic upgrade head` with PostgreSQL advisory lock to prevent concurrent migrations
- Can be wired as a Helm pre-install/pre-upgrade hook or Argo pre-sync hook

### Network Policies
- API pods: Allow ingress from ingress controller, egress to PostgreSQL, MLflow, HA, LLM APIs
- Scheduler pods: Allow egress to PostgreSQL, HA, LLM APIs only
- UI pods: Allow ingress from ingress controller only
- PostgreSQL: Allow ingress from API and scheduler pods only
- Default deny all other traffic

### Secret Management
- Use K8s Secrets (or external-secrets-operator for production)
- Required secrets: `JWT_SECRET`, `LLM_API_KEY`, `DATABASE_URL`, `HA_TOKEN`
- Optional: `GOOGLE_API_KEY`, `WEBHOOK_SECRET`, `API_KEY`

## Tasks

- [ ] Create base K8s manifests in `infrastructure/k8s/`
- [ ] Create Kustomize overlays for dev/staging/production
- [ ] Add migration Job with advisory lock support in `alembic/env.py`
- [ ] Create `docs/deployment-k8s.md` deployment guide
- [ ] Add connection pool sizing documentation (replicas * pool_size < max_connections)
- [ ] Consider Helm chart as a follow-up (Kustomize first for simplicity)
- [ ] Add Prometheus metrics export (optional, for K8s monitoring stack)

## Out of Scope

- Helm chart (follow-up after Kustomize manifests are validated)
- Multi-tenant isolation (separate feature)
- Redis for distributed locking (evaluate after initial deployment)
- Managed database services (RDS, Cloud SQL) -- use StatefulSet first
- GitOps (ArgoCD/Flux) setup -- deployment-tool agnostic manifests

## References

- Phase 1 security commit: `feat(security): enterprise security hardening`
- Constitution Principle IV (State): PostgreSQL for durable checkpointing
- Constitution Principle II (Isolation): gVisor sandbox in K8s
- Existing compose.yaml: `infrastructure/podman/compose.yaml` (migration path comments)
