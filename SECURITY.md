# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Aether, **please do not open a public issue**. Instead, report it responsibly:

1. **Email**: Send a detailed report to the maintainers via the repository's Security Advisories feature on GitHub (Settings > Security > Advisories > New draft advisory).
2. **Include**: A description of the vulnerability, steps to reproduce, potential impact, and any suggested fixes.
3. **Response time**: We aim to acknowledge reports within 48 hours and provide a fix or mitigation within 7 days for critical issues.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | Yes (current)      |

## Security Model

Aether follows a defence-in-depth approach (see Constitution Principle VI):

- **Authentication**: JWT session tokens + WebAuthn passkeys + API key support. Auth required on all endpoints except health probes.
- **Encryption at rest**: HA tokens encrypted with Fernet (PBKDF2-derived keys). Passwords hashed with bcrypt (12+ rounds).
- **Input validation**: All inputs validated via Pydantic schemas with strict constraints.
- **SQL injection**: Prevented via SQLAlchemy ORM with parameterized queries only.
- **SSRF protection**: User-provided URLs validated against cloud metadata endpoints and dangerous addresses.
- **Sandbox isolation**: All generated scripts execute in gVisor (runsc) sandboxed containers with resource limits.
- **Rate limiting**: Global and per-endpoint rate limits to prevent abuse.
- **Security headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Permissions-Policy on all responses.
- **Human-in-the-loop**: Mutating Home Assistant operations require explicit user approval.

## Security Practices

- Dependencies are pinned and audited regularly.
- CVEs are patched within 72 hours of disclosure.
- Pre-commit hooks enforce linting and secret scanning.
- CI/CD includes security scanning (bandit, pip-audit).
- No secrets, API keys, or credentials are committed to the repository.

## Disclosure Policy

We follow coordinated disclosure. Once a fix is available, we will:

1. Release a patched version.
2. Publish a security advisory on GitHub.
3. Credit the reporter (unless they prefer anonymity).
