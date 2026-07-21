# Security & Privacy Review

Last updated: 2026-07-22. This is an engineering review, not a penetration test or legal opinion.

## Verified controls

- Model and preprocessing artifacts are SHA-256 verified before the sole authoritative
  `joblib.load` path. Missing, mismatched, and tampered artifacts fail closed.
- PostgreSQL Row-Level Security is forced on every tenant-owned operational table. A live CI test
  uses a non-owner application role and proves cross-organization reads and writes are blocked.
- Branch authorization is centralized above database tenancy for branch-scoped staff.
- Production startup rejects the shipped development JWT secret, localhost/wildcard CORS, demo
  seeding, and automatic migrations.
- Refresh sessions rotate with reuse detection and are delivered to browsers in HttpOnly,
  SameSite=Strict cookies. Production forbids refresh-token exposure in JSON; the SPA stores its
  short-lived access token in memory only.
- TOTP MFA secrets are encrypted with an independent production-required Fernet key. Login uses
  short-lived signed challenge tokens and rejects reuse of an accepted TOTP time step.
- Audit records receive correlation IDs and client IP context without logging credentials or raw
  authentication tokens.
- The Nginx edge applies CSP and baseline browser security headers; only the edge is published by
  the production-oriented Compose topology.
- Python and npm dependencies are vulnerability-audited in CI and monitored by Dependabot.
- YAML uses safe loading. No application code uses `eval` or `exec`.

## Residual risk

- HMAC JWT signing is suitable for the current single issuer/verifier. Asymmetric signing and key
  rotation are required before independent services verify tokens directly.
- Local JSON registry and in-memory telemetry adapters are single-node implementations.
- External KYC, bureau, bank, and wallet integrations are simulations only.
- Institution-specific retention, consent, explainability, fairness, NRB, and incident-response
  controls require legal/compliance ownership before commercial deployment.

## Verdict

No known P0/P1 defect remains in the verified repository path. The platform is suitable for
continued controlled development, but is not authorized for real lending decisions until model,
security, operational, and regulatory validation are completed.
