---
name: security-review
description: Audit code against the 8-point security posture from the Aether constitution (Principle VI). Use when reviewing code, PRs, security changes, adding new endpoints, handling credentials, or when the user asks for a security audit or review.
---

# Security Review

Systematically audit code against Principle VI of `.specify/memory/constitution.md`.

## Instructions

When triggered, run the following 8-point checklist against the target file(s) or diff. For each point, report **PASS**, **FAIL**, or **N/A** with specific line references.

### Checklist

1. **Defence in Depth**
   - Are there multiple independent security layers (auth, authz, validation, encryption, network)?
   - Does failure of one layer still protect the system?
   - Check: no single-point-of-failure security controls.

2. **Secrets & Credentials**
   - No secrets in source code, logs, error messages, or client responses.
   - Credentials at rest: encrypted (Fernet/AES-256) or hashed (bcrypt, work factor >= 12).
   - JWT keys >= 256 bits with bounded expiry.
   - Auth cookies: `httpOnly`, `Secure` (prod), `SameSite=Lax` or stricter.

3. **Input Validation & Injection Prevention**
   - All external input validated via Pydantic schemas or strict typing.
   - Database queries use parameterised access only (SQLAlchemy ORM/Core).
   - No raw string interpolation in SQL.
   - Output contextually escaped to prevent XSS.

4. **Transport & Headers**
   - Production traffic over TLS.
   - Security headers present: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Strict-Transport-Security`.
   - CORS origins explicitly allowlisted — no wildcard `*` in production.

5. **Dependency Hygiene**
   - Dependencies pinned to exact versions in lock file.
   - No known CVEs in current dependencies (check advisories if possible).
   - New dependencies evaluated for maintenance status and supply-chain risk.

6. **No Security Shortcuts**
   - No `# nosec`, `# type: ignore[security]`, or suppressed security warnings without written justification.
   - No simpler implementation chosen at the cost of security.
   - No "we'll fix it later" security debt.

7. **Least Privilege & Attack Surface**
   - New endpoints require auth by default; any exempt route is explicitly listed in `EXEMPT_ROUTES`.
   - DB connections use minimal-permission roles.
   - No debug endpoints, unused routes, or dev scaffolding left in production code.
   - Containers run as non-root with read-only filesystem where possible.

8. **Audit & Accountability**
   - Auth events (login, logout, failures, passkey registration) logged with timestamps and client metadata.
   - System config changes logged.
   - Logs do not contain secrets, tokens, or unnecessary PII.

### Output Format

```
## Security Review: <filename or scope>

| # | Check                          | Status | Notes              |
|---|--------------------------------|--------|--------------------|
| 1 | Defence in Depth               | PASS   |                    |
| 2 | Secrets & Credentials          | FAIL   | Line 42: plaintext |
| 3 | Input Validation               | PASS   |                    |
| 4 | Transport & Headers            | N/A    | Not an endpoint    |
| 5 | Dependency Hygiene             | PASS   |                    |
| 6 | No Security Shortcuts          | PASS   |                    |
| 7 | Least Privilege                | FAIL   | No auth on /debug  |
| 8 | Audit & Accountability         | PASS   |                    |

**Summary**: X/8 passed, Y issues found.
**Action items**: [list of specific fixes needed]
```

### Prohibited Patterns to Flag

- Plaintext passwords or tokens in DB
- `eval()`, `exec()` outside gVisor sandbox
- Auth disabled "for convenience"
- Stack traces, internal paths, or dependency versions in API error responses
- MD5 or SHA-1 for security-critical hashing
- Hard-coded secrets (even "temporary")
- Simpler implementation chosen despite known security weakness
