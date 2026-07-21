# CreditIQ AI — Loan Management & Credit Intelligence Platform

[![AI Engine CI](https://github.com/BidhanPandey550/CreditIQ-AI/actions/workflows/ai-engine-ci.yml/badge.svg)](https://github.com/BidhanPandey550/CreditIQ-AI/actions/workflows/ai-engine-ci.yml)
[![Platform CI](https://github.com/BidhanPandey550/CreditIQ-AI/actions/workflows/platform-ci.yml/badge.svg)](https://github.com/BidhanPandey550/CreditIQ-AI/actions/workflows/platform-ci.yml)
[![Security CI](https://github.com/BidhanPandey550/CreditIQ-AI/actions/workflows/security-ci.yml/badge.svg)](https://github.com/BidhanPandey550/CreditIQ-AI/actions/workflows/security-ci.yml)

Multi-tenant SaaS lending platform for banks, MFIs, cooperatives, and digital lenders in Nepal.
See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

The repository combines a lending SaaS foundation with a standalone, test-driven AI library for
data quality, financial feature engineering, credit-risk training, fraud detection, explainability,
integrity-verified model artifacts, model lifecycle management, and unified lending decisions.

## Current engineering status

- **238 AI-engine, 38 backend (including live PostgreSQL RLS), 3 ML-serving, and 3 frontend tests
  passing**, including cross-module and secure-session behavior tests.
- Ruff lint and formatting gates pass for `ai-engine/`.
- All 14 local smoke-test stages pass: data → features → credit/fraud → explanation → verified
  artifacts → unified decision → persistent registry → monitoring health.
- Model artifacts are SHA-256 verified before Joblib deserialization.
- Organization isolation is enforced by PostgreSQL RLS; branch-scoped staff access is enforced by
  a centralized authorization policy across operational queries and record creation.
- Applicant self-service uses a durable one-to-one ownership link in signed claims and database
  records; applicants can access only their own profile, applications, and status timeline.
- Compliance events inherit async-safe request IDs and client IP metadata; authentication, user and
  applicant creation, AI analysis, simulations, exports, and loan state changes are audited.
- Refresh sessions use rotating server-revocable tokens in HttpOnly SameSite cookies; the SPA keeps
  short-lived access tokens in memory rather than browser persistence.
- TOTP multi-factor authentication includes encrypted-at-rest secrets, short-lived signed login
  challenges, replay-resistant code verification, audited enrollment, and self-service controls.
- The frontend ships as an immutable Nginx static image with SPA routing, security headers, health
  checks, and same-origin API proxying; container builds are gated in CI.
- Portfolio reporting provides branch-authorized CSV and paginated confidential PDF exports; every
  export is recorded in the compliance audit trail.
- Locked frontend and installed Python dependencies are audited on every dependency change and on a
  weekly schedule; Dependabot tracks Python, npm, and GitHub Actions updates.
- This remains an **active-development foundation**, not a validated production lending model.
  Synthetic/demo predictions must not be used for real credit decisions.

> **MVP status.** This is the runnable foundation (Phase 0 → early Phase 1). External integrations
> (banks, eSewa/Khalti/IME Pay, credit bureaus) are **simulated adapters**, clearly flagged — no real
> financial connections. ML predictions are served by a thin `ml-engine` adapter over the canonical
> AI library. The backend fails closed if governed inference is unavailable; it never substitutes an
> unversioned heuristic for a lending assessment.

## Monorepo layout

```
Loan Banking/
├── ai-engine/        Standalone CreditIQ AI library (training, fraud, XAI, decisions, model ops)
├── backend/          FastAPI modular monolith (auth, tenancy, loans, applicants, ML gateway)
├── ml-engine/        Thin serving adapter over the canonical AI engine
├── frontend/         React 19 + TS + Vite SPA, built and served by Nginx
├── infrastructure/   Postgres init, ops
└── docs/             Architecture spec
```

## Quick start (Docker — recommended)

```bash
cd "Loan Banking"
cp .env.example .env
docker compose up --build
```

Then:

- Backend API + Swagger docs → http://localhost:5173/docs (proxied through the frontend edge)
- ML engine docs           → http://localhost:8001/docs
- Frontend (dev)           → http://localhost:5173

In development, the backend applies versioned Alembic migrations (including forced PostgreSQL RLS)
and seeds demo data on first boot. Production disables automatic migrations and refuses to start
unless the database is already at the repository's Alembic head.

> Existing local volumes created before the Alembic baseline should be recreated for development;
> do not stamp an unverified production schema. Back up any data before replacing a volume.

### Demo login (seeded)

| Role          | Email                        | Password      |
|---------------|------------------------------|---------------|
| Administrator | admin@himalayan-demo.com     | ChangeMe123!  |
| Loan Officer  | officer@himalayan-demo.com   | ChangeMe123!  |
| Risk Analyst  | analyst@himalayan-demo.com   | ChangeMe123!  |

> Two demo organizations are seeded so you can verify **tenant isolation** — a user from org A
> cannot see org B's applicants or loans.

## Run a service on its own (without Docker)

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload --port 8000     # needs a Postgres + Redis running

# ML engine
cd ml-engine
pip install -e ../ai-engine
pip install -e ".[dev]"
uvicorn src.serving.main:app --reload --port 8001

# Frontend
cd frontend
npm install
npm run dev
```

## Make targets

```bash
make up        # docker compose up --build
make down      # stop everything
make logs      # tail logs
make migrate   # apply versioned database migrations
make seed      # re-run backend seed
make test      # backend tests
```

## AI engine verification

```bash
cd ai-engine
poetry install
poetry run ruff check creditiq_ai tests
poetry run ruff format --check creditiq_ai tests
poetry run pytest
poetry run python -m creditiq_ai.smoke_test
```

Detailed implementation and audit material is available under
[`ai-engine/docs`](ai-engine/docs), including the integration matrix and technical-debt register.
