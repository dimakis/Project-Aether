# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enterprise security hardening for production deployment
  - HSTS, CSP, and Permissions-Policy security headers
  - `/api/v1/ready` readiness probe endpoint for Kubernetes
  - `AETHER_ROLE` setting for multi-replica K8s deployment (api/scheduler/all)
  - Production guard blocking unsandboxed script execution
- Open-source readiness files (LICENSE, CONTRIBUTING.md, SECURITY.md, CHANGELOG.md)

### Changed
- Upgraded Fernet key derivation from SHA-256 to PBKDF2-HMAC-SHA256 (480k iterations)
- Rate limiter now uses X-Forwarded-For for real client IP behind reverse proxies
- `/metrics` endpoint now requires authentication (removed from auth-exempt routes)
- Status endpoint error messages sanitized in production (no internal details)
- Containerfile updated with proxy headers, graceful shutdown, and K8s-ready defaults

### Security
- Fixed rate limiting bypass when behind reverse proxy (all clients shared same IP)
- Prevented information leakage in health check error messages
- Added HSTS to enforce HTTPS in production/staging environments
- Added CSP to restrict resource loading on API responses
- Blocked unsandboxed script execution in production environment

## [0.1.0] - 2025-01-01

### Added
- Initial release of Project Aether
- Multi-agent system with Architect, Librarian, Data Scientist, and Developer agents
- LangGraph-based workflow orchestration with human-in-the-loop approval
- Home Assistant integration via MCP (Model Context Protocol)
- FastAPI REST API with JWT + WebAuthn authentication
- React dashboard UI with chat, proposals, insights, entities, and trace views
- PostgreSQL storage with Alembic migrations
- MLflow observability and trace visualization
- gVisor-sandboxed script execution for data analysis
- APScheduler-based scheduled and event-driven insights
- OpenAI-compatible API endpoint for third-party integrations
