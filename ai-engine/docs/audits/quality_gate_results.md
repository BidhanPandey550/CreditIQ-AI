# Current Quality Gate Results

Last verified: 2026-07-22. Authoritative automation lives in
`.github/workflows/ai-engine-ci.yml`, `.github/workflows/platform-ci.yml`, and
`.github/workflows/security-ci.yml`.

| Gate | Current evidence | Status |
|---|---|---|
| AI unit/integration tests | `poetry run pytest`: **238 passed**, 92.23% coverage | PASS |
| AI lint and format | Ruff check and format-check across library and tests | PASS |
| AI static typing | `poetry run mypy creditiq_ai` | PASS |
| AI package build | `poetry build`; wheel includes environment YAML configuration | PASS |
| AI smoke path | 14/14 stages: data through governed decision, registry, and monitoring | PASS |
| Backend tests | **87 local tests passed**; 2 PostgreSQL-only tests skipped locally | PASS |
| PostgreSQL isolation | Live PostgreSQL 17 test proves cross-tenant reads/writes are blocked | PASS |
| Backend migrations | Single Alembic head; offline SQL compilation and live upgrade | PASS |
| ML serving adapter | 3 adapter contract tests | PASS |
| Frontend | TypeScript typecheck, 3 secure-session tests, and production Vite build | PASS |
| Containers | Backend, frontend/Nginx, and canonical ML serving images build in CI | PASS |
| Dependency audit | `pip-audit` for three Python services; `npm audit` at high severity | AUTOMATED |

The historical Sprint 8.5 baseline was 119 tests with several unavailable tools. It is retained in
Git history, not presented here as current state. Passing engineering gates does not constitute
credit-model validation, regulatory approval, penetration testing, or production authorization.
