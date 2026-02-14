# Getting Started

This guide covers authentication, deployment modes, and remote access for Project Aether. For prerequisites and initial setup, see the [Quick Start](../README.md#quick-start) in the README.

## Authentication

Aether uses HA-verified first-time setup and supports four authentication methods.

### First-Time Setup

On first launch, the UI shows a setup wizard:

1. **Enter HA URL + token** — Aether validates the connection by calling the HA API
2. **Set fallback password** (optional) — stored as a bcrypt hash in the database
3. **Register a passkey** — Face ID / Touch ID for quick biometric login

The HA URL and token are stored in the database (encrypted with Fernet, key derived from `JWT_SECRET`). Setup can only be run once; to re-run, delete the `system_config` DB row.

### 1. Passkey / Biometric Login (WebAuthn) — Primary

The recommended login method. After registering a passkey during setup, use Face ID, Touch ID, or Windows Hello to sign in instantly.

Configure for your domain:

```bash
WEBAUTHN_RP_ID=home.example.com     # your domain (must match URL)
WEBAUTHN_RP_NAME=Aether             # display name
WEBAUTHN_ORIGIN=https://home.example.com  # full origin URL
```

> **Note**: WebAuthn requires HTTPS in production. Use Cloudflare Tunnel or Tailscale for secure remote access.

### 2. HA Token Login — Alternative

Log in using any valid Home Assistant long-lived access token. Aether validates the token against the stored HA URL (from setup) or env var fallback.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ha-token \
  -H "Content-Type: application/json" \
  -d '{"ha_token": "your-long-lived-access-token"}'
```

### 3. Password Login (JWT) — Fallback

If you set a password during setup, use it to log in. Aether checks the DB hash first, then falls back to the `AUTH_PASSWORD` env var.

```bash
# Optional env var fallback (DB password from setup takes priority)
AUTH_USERNAME=admin
AUTH_PASSWORD=your-secret
JWT_SECRET=a-long-random-string  # optional, auto-derived if empty
JWT_EXPIRY_HOURS=72
```

Login via the UI or API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-secret"}'
```

The JWT is returned in the response body **and** as an httpOnly cookie (`aether_session`).

### 4. API Key (Programmatic Access)

For scripts, CLI tools, or external integrations:

```bash
API_KEY=your-api-key
```

Pass via header or query parameter:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/entities
```

### Auth Disabled (Development)

When no setup has been completed and neither `AUTH_PASSWORD` nor `API_KEY` is set, authentication is completely disabled for development convenience.

---

## Deployment Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Development** | `make run` | Infrastructure in containers, API on host with hot-reload |
| **Dev + UI** | `make run-ui` | Above + React UI dev server with HMR |
| **Production** | `make run-prod` | Everything containerized (Podman Compose) |
| **Stop** | `make down` | Stop all services and containers |

### Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Chat UI | `3000` | React frontend |
| Aether API | `8000` | FastAPI backend (OpenAI-compatible + native API) |
| MLflow | `5002` | Trace viewer for agent observability |
| PostgreSQL | `5432` | State, conversations, entities, insights |

---

## Remote Access

### Cloudflare Tunnel (Recommended)

1. Install cloudflared: `brew install cloudflared`
2. Create a tunnel: `cloudflared tunnel create aether`
3. Configure to route to `http://localhost:3000`
4. Update your `.env`:

```bash
WEBAUTHN_RP_ID=aether.your-domain.com
WEBAUTHN_ORIGIN=https://aether.your-domain.com
ALLOWED_ORIGINS=https://aether.your-domain.com
```

Benefits: no port forwarding, automatic HTTPS, DDoS protection.

### Alternative: Tailscale (VPN)

1. Install Tailscale on your HA machine and phone
2. Access via Tailscale IP: `http://100.x.y.z:3000`

Benefits: zero-config VPN, no public exposure, works with HTTP (no HTTPS needed for WebAuthn on Tailscale).

### Security Checklist

- [ ] Set `AUTH_PASSWORD` to a strong password
- [ ] Set `JWT_SECRET` to a random 32+ character string
- [ ] Configure `ALLOWED_ORIGINS` for your domain
- [ ] Register a passkey for passwordless login
- [ ] Use HTTPS (required for WebAuthn on public domains)

---

## Next Steps

- [Configuration](configuration.md) — LLM providers, per-agent model overrides, usage tracking
- [User Flows](user-flows.md) — step-by-step interaction sequences
- [Architecture](architecture.md) — system design and agent roles
