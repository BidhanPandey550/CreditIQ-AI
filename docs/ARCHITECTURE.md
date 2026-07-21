# CreditIQ AI — Enterprise System Architecture

**Loan Management & Credit Intelligence Platform**
**Target market:** Banks, Microfinance Institutions (MFIs), Cooperatives, and Digital Lenders in Nepal
**Document type:** Architecture & Design Specification (no application code — design only)
**Status:** v1.0 — Foundation architecture, awaiting implementation approval

> **Scope of this document.** This is a design blueprint only. It defines *how* the system is structured, not the running code. Integrations with banks, wallets (eSewa/Khalti/IME Pay), and credit bureaus are **designed as pluggable adapters but NOT implemented** — the MVP ships with clearly-labeled *simulated* adapters. Nothing here claims a live connection to any real financial institution.

---

## Table of Contents

1. [Executive Summary & Architectural Principles](#1-executive-summary--architectural-principles)
2. [Complete Enterprise System Architecture](#2-complete-enterprise-system-architecture)
3. [Multi-Tenant Architecture Design](#3-multi-tenant-architecture-design)
4. [Monorepo Folder Structure](#4-monorepo-folder-structure)
5. [PostgreSQL Database Schema & ERD Description](#5-postgresql-database-schema--erd-description)
6. [Backend Clean Architecture Design](#6-backend-clean-architecture-design)
7. [Frontend Architecture Design](#7-frontend-architecture-design)
8. [API Architecture Design](#8-api-architecture-design)
9. [Authentication & RBAC Architecture](#9-authentication--rbac-architecture)
10. [Machine Learning Service Architecture](#10-machine-learning-service-architecture)
11. [Integration Layer Architecture](#11-integration-layer-architecture)
12. [Docker & Infrastructure Architecture](#12-docker--infrastructure-architecture)
13. [Security & Compliance Architecture](#13-security--compliance-architecture)
14. [Development Roadmap (MVP → Production)](#14-development-roadmap-mvp--production)
15. [Recommended MVP Scope (University Project)](#15-recommended-mvp-scope-university-project)
16. [Recommended Production Scope (Real Fintech Startup)](#16-recommended-production-scope-real-fintech-startup)
17. [Appendix: Key Decision Records](#17-appendix-key-architecture-decision-records-adrs)

---

## 1. Executive Summary & Architectural Principles

CreditIQ AI is a **multi-tenant SaaS lending platform** that combines a loan-origination and servicing workflow with an AI-driven credit intelligence engine. The defining challenge is not any single feature but the *combination*: strong tenant isolation, auditable financial workflows, explainable ML decisions, and a regulatory posture aligned with Nepal Rastra Bank (NRB) expectations — all in a system that a small team can build, operate, and evolve.

### 1.1 Architectural style

- **Modular monolith first, service-extraction later.** The backend is one deployable FastAPI application internally divided into **bounded contexts** (modules) with hard boundaries. This gives a startup fast iteration and transactional simplicity, while keeping the *option* to extract any module into its own service. The **ML engine is the one genuinely separate service** from day one, because it has a different runtime profile (CPU/GPU, heavy libraries, independent scaling and deployment cadence).
- **Clean Architecture + Domain-Driven Design.** Dependencies always point inward: Domain ← Application ← Infrastructure/Presentation. Business rules never import a framework.
- **Ports & Adapters (Hexagonal).** Every external dependency (DB, ML, SMS, wallet, bureau) sits behind an interface (port) owned by the domain/application layer, with swappable adapters. This is what makes "integrations pluggable later" real rather than aspirational.
- **Event-oriented core.** Domain events (`LoanSubmitted`, `RiskScored`, `FraudFlagged`, `LoanDisbursed`) decouple workflow steps and feed the audit log, notifications, and analytics without tangling the modules.

### 1.2 Non-negotiable qualities

| Quality | How the architecture delivers it |
|---|---|
| **Tenant isolation** | `organization_id` on every tenant-scoped row + PostgreSQL Row-Level Security (RLS) enforced by DB policies, not just app code. Defense in depth. |
| **Auditability** | Append-only `audit_logs` fed by domain events; every state transition on a loan is recorded with actor, tenant, before/after, and correlation id. |
| **Explainability** | Every ML prediction persists its SHAP contributions and a human-readable rationale — no black-box decisions reach a loan officer. |
| **Security** | JWT access + rotating refresh tokens, RBAC with fine-grained permissions, argon2 hashing, rate limiting, encryption in transit and at rest, secrets isolated from code. |
| **Scalability** | Stateless API workers behind a load balancer; read replicas; Redis for cache/queues; ML served independently; async workers for heavy jobs. |
| **Maintainability** | Bounded contexts, dependency inversion, exhaustive typing (TypeScript + Pydantic v2 + SQLAlchemy typed models), and a test pyramid. |

### 1.3 The "no toy project" guarantees

1. **No hardcoded business logic** — decisioning thresholds, workflow stages, and scorecard weights live in configuration/DB tables (`policy_rules`, `workflow_definitions`), tenant-overridable.
2. **No fake integrations** — external connectors are interfaces with `Simulated*` adapters explicitly named and flagged (`is_simulated = true`), never masquerading as production links.
3. **Adapter-first** — adding a real eSewa or credit-bureau connector later means writing one adapter class and a config entry; **zero changes to core business logic**.

---

## 2. Complete Enterprise System Architecture

### 2.1 Layered / C4-style overview

```
                                   ┌────────────────────────────────────────────┐
                                   │                 CLIENTS                      │
                                   │  Web SPA (React 19) · Future mobile · 3rd-  │
                                   │  party API consumers (banks, partners)       │
                                   └───────────────────────┬──────────────────────┘
                                                           │ HTTPS / JSON (+ API keys)
                                   ┌───────────────────────▼──────────────────────┐
                                   │              EDGE / GATEWAY                   │
                                   │  TLS termination · WAF · Rate limiting ·      │
                                   │  CORS · Request ID · (Nginx / Traefik)        │
                                   └───────────────────────┬──────────────────────┘
                                                           │
        ┌──────────────────────────────────────────────────┼──────────────────────────────────────────────────┐
        │                                       API LAYER (FastAPI)                                             │
        │   Routers → Dependencies (auth, tenant ctx, RBAC) → Pydantic v2 schemas → Error handling middleware   │
        └──────────────────────────────────────────────────┼──────────────────────────────────────────────────┘
                                                           │  (in-process calls, DI)
        ┌──────────────────────────────────────────────────▼──────────────────────────────────────────────────┐
        │                              APPLICATION LAYER (Use Cases / Services)                                 │
        │   Orchestrates domain + infra · Unit of Work / transactions · Emits domain events · DTO mapping       │
        └───────┬───────────────────────┬────────────────────────┬────────────────────────┬────────────────────┘
                │                       │                        │                        │
     ┌──────────▼─────────┐  ┌──────────▼─────────┐   ┌──────────▼─────────┐   ┌──────────▼─────────┐
     │   DOMAIN LAYER      │  │  Ports (interfaces)│   │  Domain Events     │   │  Policy / Rules    │
     │ Entities · Value    │  │  Repos · ML · Bank │   │  (in-proc bus)     │   │  engine (config)   │
     │ Objects · Invariants│  │  Wallet · Bureau   │   │                    │   │                    │
     └─────────────────────┘  └─────────┬──────────┘   └─────────┬──────────┘   └────────────────────┘
                                        │ implemented by                    │ consumed by
        ┌───────────────────────────────▼───────────────────────────────────▼─────────────────────────┐
        │                              INFRASTRUCTURE LAYER (Adapters)                                  │
        │  SQLAlchemy repos · Alembic · Redis cache/queue · Object storage · Email/SMS · ML HTTP client │
        │  Integration adapters (Simulated* for MVP): Wallet · Bank · Bureau · Identity · Payment       │
        └───────┬───────────────────────────────────────────────┬───────────────────────┬──────────────┘
                │                                               │                       │
     ┌──────────▼──────────┐                        ┌───────────▼─────────┐   ┌─────────▼──────────────────┐
     │  PostgreSQL (RLS)    │                        │   Redis             │   │  ML ENGINE (separate svc)  │
     │  primary + replicas  │                        │  cache · queues ·   │   │  FastAPI · sklearn/XGB/    │
     │  tenant-isolated data │                        │  rate-limit buckets │   │  CatBoost/LightGBM · SHAP  │
     └──────────────────────┘                        └─────────────────────┘   │  model registry · monitor  │
                                                                                └────────────────────────────┘
     ┌───────────────────────────── ASYNC WORKERS (Celery/RQ/Arq on Redis) ────────────────────────────────┐
     │  Risk scoring jobs · Fraud batch · Report generation (PDF/CSV) · Notifications · Model drift checks   │
     └──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 The seven logical layers (as requested)

| # | Layer | Responsibility | Key components |
|---|---|---|---|
| 1 | **Presentation** | User interaction, visualization | React 19 SPA, role dashboards, charts, forms |
| 2 | **API** | Transport, validation, auth gating | FastAPI routers, Pydantic schemas, middleware |
| 3 | **Application** | Use cases, orchestration, transactions | Services, command/query handlers, UoW |
| 4 | **Domain** | Business entities & invariants | Entities, value objects, domain services, events |
| 5 | **Infrastructure** | Technical implementations | Repositories, DB, cache, external adapters |
| 6 | **Machine Learning** | Risk/fraud/scoring + explainability | ML engine service, model registry, monitoring |
| 7 | **Integration** | External connectors (future) | Ports + adapters for bank/wallet/bureau/identity |

### 2.3 Bounded contexts (backend modules)

Each maps to a directory module with its own domain/application/infra sub-structure and a **public interface** other modules call through (never reaching into another module's internals).

```
Identity & Access        Organization & Tenancy      Applicant & Financial Profile
Loan Origination         Loan Servicing              Credit Intelligence (ML gateway)
Fraud & Risk             Decisioning & Workflow      Portfolio Analytics
Reporting & Export       Notifications               Audit & Compliance
API & Integration Mgmt   Model Monitoring & Versioning
```

Inter-context communication: **synchronous** via published application interfaces for queries; **asynchronous** via domain events for side effects (audit, notifications, analytics projections).

---

## 3. Multi-Tenant Architecture Design

### 3.1 The tenant model

- **Tenant = Organization** (a bank / MFI / cooperative / digital lender).
- Below an organization: **Branches → Users**, and **Applicants → Loans → Financials**.
- A **Super Admin** (platform owner) sits *above* all tenants for platform operations; every other user belongs to exactly one organization.

### 3.2 Isolation strategy — decision

Three canonical options were evaluated:

| Strategy | Isolation | Ops cost | Cross-tenant analytics | Verdict |
|---|---|---|---|---|
| **A. Shared schema + `organization_id` + RLS** | Strong (DB-enforced) | Low | Easy | ✅ **Chosen for MVP & most tenants** |
| B. Schema-per-tenant | Stronger | Medium | Harder | Offered as premium tier for large banks |
| C. Database-per-tenant | Strongest | High | Hardest | Reserved for regulated data-residency clients |

**Decision:** Start with **Strategy A (shared schema + PostgreSQL Row-Level Security)**. It gives *database-enforced* isolation — not just application-level `WHERE org_id = ?` filters that a single missing clause could defeat — while remaining operationally simple for a small team. The design keeps a **clean upgrade path** to B/C: because all data access goes through the tenant-aware repository layer, moving a large enterprise client to a dedicated schema/DB is a routing change, not a rewrite.

### 3.3 How isolation is enforced (defense in depth)

**Layer 1 — Token:** the JWT carries `org_id` (and `branch_id`, `roles`). It is signed; the client cannot forge it.

**Layer 2 — Request context:** a FastAPI dependency resolves the tenant from the token and stores it in a request-scoped `TenantContext`. Every repository automatically injects `organization_id`.

**Layer 3 — Database RLS (the real guarantee):** each tenant-scoped table has RLS enabled. At the start of every DB transaction the app sets a session variable, and policies enforce it:

```sql
-- One-time per table
ALTER TABLE loans ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loans
  USING (organization_id = current_setting('app.current_org')::uuid);

-- Per request/transaction (set by middleware, never by client)
SET LOCAL app.current_org = '‹org-uuid-from-jwt›';
```

Even if an application bug omitted an `org_id` filter, the database returns **zero rows** for the wrong tenant. The Super Admin path uses a separate role that can bypass RLS *only* through explicitly audited platform-admin queries.

**Layer 4 — Branch-level scoping:** within a tenant, RBAC further restricts users to their branch(es) where required (a Loan Officer sees their branch's applications; a Branch Manager sees the branch; an Admin sees the org).

### 3.4 Tenant lifecycle

`Provisioning` → `Active` → `Suspended` (billing/compliance hold, read-only) → `Offboarding` (export + retention window) → `Purged`. Each transition is an audited event. Per-tenant configuration (branding, workflow definitions, decision policies, feature flags, future model bindings) lives in `organization_settings` and `workflow_definitions`, so tenants can diverge without code forks.

### 3.5 Per-tenant customization surface

- **Workflow:** stages/transitions configurable per org (`workflow_definitions`).
- **Decision policy:** thresholds, auto-approve/-reject bands, required reviewers (`policy_rules`).
- **Models (future-ready):** an org can be bound to a specific model version per task via `organization_model_bindings`, enabling champion/challenger per tenant.
- **Branding & locale:** logo, colors, language (English/Nepali), currency formatting (NPR).

---

## 4. Monorepo Folder Structure

A single repository with clearly separated deployables and shared contracts. Tooling: `pnpm` workspaces (JS), `uv`/`poetry` (Python), `turbo` (optional) for task orchestration.

```
creditiq-ai/
├── README.md
├── docker-compose.yml                 # local full-stack orchestration
├── docker-compose.prod.yml
├── .env.example                       # documents every env var (no secrets)
├── Makefile                           # dev shortcuts (up, migrate, seed, test, lint)
├── .github/workflows/                 # CI/CD pipelines
│   ├── ci-backend.yml
│   ├── ci-frontend.yml
│   ├── ci-ml.yml
│   └── security-scan.yml
│
├── frontend/                          # React 19 + TS + Vite SPA
│   ├── src/
│   │   ├── app/                       # providers, router, query client, theme
│   │   ├── pages/                     # route-level screens
│   │   ├── features/                  # feature-sliced modules (loans, applicants, fraud…)
│   │   │   └── loans/
│   │   │       ├── api/               # React Query hooks + fetchers
│   │   │       ├── components/
│   │   │       ├── hooks/
│   │   │       └── types.ts
│   │   ├── components/ui/             # shadcn/ui primitives
│   │   ├── components/charts/         # Recharts wrappers (gauges, cashflow…)
│   │   ├── lib/                       # api client, auth, rbac guards, utils
│   │   ├── stores/                    # lightweight client state (Zustand)
│   │   └── styles/
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/                           # FastAPI modular monolith (clean architecture)
│   ├── app/
│   │   ├── main.py                    # app factory, middleware wiring
│   │   ├── core/                      # config, security, logging, errors, DI container
│   │   ├── db/                        # engine, session, base, RLS helpers
│   │   ├── shared/                    # cross-context value objects, event bus, pagination
│   │   ├── modules/                   # ← bounded contexts
│   │   │   ├── identity/              #   auth, users, roles, permissions
│   │   │   │   ├── domain/            #     entities, value objects, events, ports
│   │   │   │   ├── application/       #     use cases, DTOs
│   │   │   │   ├── infrastructure/    #     SQLAlchemy models + repositories
│   │   │   │   └── api/               #     routers + schemas
│   │   │   ├── organization/
│   │   │   ├── applicant/
│   │   │   ├── loan/
│   │   │   ├── financial_profile/
│   │   │   ├── credit_intelligence/   #   ML gateway (calls ml-engine)
│   │   │   ├── fraud/
│   │   │   ├── decisioning/           #   workflow engine
│   │   │   ├── analytics/
│   │   │   ├── reporting/
│   │   │   ├── notifications/
│   │   │   ├── audit/
│   │   │   ├── integrations/          #   ports + Simulated* adapters
│   │   │   └── model_monitoring/
│   │   └── workers/                   # async tasks (Celery/Arq)
│   ├── alembic/                       # migrations
│   ├── tests/                         # unit / integration / e2e
│   ├── pyproject.toml
│   └── Dockerfile
│
├── ml-engine/                         # separate ML service
│   ├── src/
│   │   ├── serving/                   # FastAPI inference API
│   │   ├── features/                  # feature engineering + (light) feature store
│   │   ├── models/                    # risk, credit_score, default, fraud, behavior
│   │   ├── explainability/            # SHAP wrappers, rationale generation
│   │   ├── registry/                  # model versioning, artifact load/save
│   │   ├── monitoring/                # drift (PSI/KS), performance, distributions
│   │   ├── training/                  # training pipelines, evaluation, calibration
│   │   └── contracts/                 # request/response schemas (shared with backend)
│   ├── notebooks/                     # experimentation (not in serving path)
│   ├── artifacts/                     # serialized models (gitignored; object storage in prod)
│   ├── pyproject.toml
│   └── Dockerfile
│
├── shared/                            # cross-language contracts
│   ├── openapi/                       # generated OpenAPI spec (source of truth for FE types)
│   ├── ts-types/                      # generated TS types from OpenAPI
│   └── events/                        # domain event schema definitions
│
├── infrastructure/                    # IaC & ops
│   ├── docker/                        # per-service Dockerfiles / entrypoints
│   ├── nginx/                         # reverse proxy / TLS config
│   ├── terraform/                     # cloud provisioning (prod)
│   ├── k8s/                           # (future) manifests / helm charts
│   └── seed/                          # demo/seed data scripts
│
└── docs/
    ├── ARCHITECTURE.md                # ← this document
    ├── adr/                           # architecture decision records
    ├── api/                           # API reference
    ├── data-model/                    # ERD, schema docs
    └── runbooks/                      # ops runbooks
```

---

## 5. PostgreSQL Database Schema & ERD Description

### 5.1 Modeling conventions

- **Primary keys:** UUID v7 (time-ordered → good index locality) via `gen_random_uuid()`/app-generated.
- **Tenant key:** `organization_id UUID NOT NULL` on every tenant-scoped table, with RLS policy + composite indexes leading with `organization_id`.
- **Timestamps:** `created_at`, `updated_at` (UTC, `timestamptz`), plus `created_by`, `updated_by`.
- **Soft delete:** `deleted_at` where records must be retained for audit/compliance; hard delete is prohibited for financial/audit tables.
- **Money:** `NUMERIC(18,2)` in NPR — never floats. Currency code stored for future multi-currency.
- **Enums:** Postgres enums or lookup tables for controlled vocabularies (loan_status, risk_band…).
- **JSONB** for flexible/evolving attributes (KYC extra fields, feature snapshots, SHAP payloads) — indexed with GIN where queried.

### 5.2 ERD description (relationships)

```
organizations ──1:N── branches ──1:N── users
      │                                   │
      │ 1:N                               │ N:M (via user_roles)
      ▼                                   ▼
  applicants ──1:1── kyc_records       roles ──N:M── permissions (role_permissions)
      │  │  │  │
      │  │  │  └─1:N─ employment_records / business_records
      │  │  └────1:N─ income_records / expense_records
      │  └───────1:N─ asset_records / liability_records / existing_loans
      │
      ├─1:N─ transaction_records            (bank / wallet / utility — simulated)
      ├─1:N─ financial_documents
      └─1:N─ loan_applications
                  │
                  ├─1:N─ loan_workflow_events      (audited stage transitions)
                  ├─1:1─ loan_decisions
                  ├─1:N─ risk_scores               (versioned per model run)
                  ├─1:N─ credit_scores
                  ├─1:N─ default_predictions
                  ├─1:N─ fraud_alerts
                  ├─1:N─ ai_explanations           (SHAP + narrative)
                  └─1:N─ disbursements / repayments (servicing)

Platform / cross-cutting:
  model_versions ──1:N── model_metrics / drift_reports        (model_monitoring)
  api_keys, notifications, audit_logs, system_logs, financial_reports,
  workflow_definitions, policy_rules, organization_settings
```

### 5.3 Table catalog (grouped)

**Tenancy & identity**

| Table | Purpose | Notable columns |
|---|---|---|
| `organizations` | Tenant root | `type`(bank/mfi/coop/digital), `status`, `settings_id`, `nrb_license_no` |
| `organization_settings` | Per-tenant config | `branding` JSONB, `locale`, `feature_flags` JSONB |
| `branches` | Org sub-units | `organization_id`, `code`, `address`, `manager_user_id` |
| `users` | Accounts | `organization_id`, `branch_id`, `email`, `password_hash`(argon2), `mfa_enabled`, `status`, `last_login_at` |
| `roles` | Role catalog | `organization_id` (nullable = system role), `name`, `is_system` |
| `permissions` | Fine-grained perms | `code`(e.g. `loan:approve`), `description` |
| `user_roles` | N:M | `user_id`, `role_id`, `branch_scope` |
| `role_permissions` | N:M | `role_id`, `permission_id` |
| `refresh_tokens` | Rotating sessions | `user_id`, `token_hash`, `expires_at`, `revoked_at`, `device` |

**Applicant & financial profile**

| Table | Purpose |
|---|---|
| `applicants` | Personal info, org/branch scoped |
| `kyc_records` | Citizenship/passport IDs, verification status, `is_simulated_verification` |
| `employment_records` / `business_records` | Salaried vs self-employed details |
| `income_records` / `expense_records` | Cash-in / cash-out lines (source, amount, frequency) |
| `asset_records` / `liability_records` | Balance-sheet items |
| `existing_loans` | Prior/parallel obligations |
| `transaction_records` | Bank/wallet/utility transactions (**simulated** for MVP; `source_type`, `is_simulated`) |
| `financial_documents` | Uploaded docs (object-storage key, checksum, virus-scan status) |

**Loan lifecycle**

| Table | Purpose |
|---|---|
| `loan_products` | Product catalog per org (amount ranges, tenor, rate bands) |
| `loan_applications` | Core application, `status`, `product_id`, requested amount/tenor |
| `loan_workflow_events` | Every stage transition (from→to, actor, reason, timestamp) |
| `loan_decisions` | Final/interim decision, reviewer chain, conditions |
| `disbursements` / `repayments` | Servicing (active/closed/defaulted) |

**AI outputs (all versioned & explainable)**

| Table | Purpose |
|---|---|
| `risk_scores` | Risk band (low/med/high) + probability, `model_version_id`, `feature_snapshot` JSONB |
| `credit_scores` | 0–100 alternative score, subscores |
| `default_predictions` | Calibrated PD, horizon (e.g. 12m) |
| `fraud_alerts` | Alert type, severity, rule/model source, status (open/confirmed/dismissed) |
| `ai_explanations` | SHAP contributions JSONB + generated narrative, linked to the specific prediction |

**Platform, ops & compliance**

| Table | Purpose |
|---|---|
| `model_versions` | Registry: task, algorithm, version, metrics, artifact URI, stage(staging/prod/archived) |
| `model_metrics` / `drift_reports` | Monitoring over time (accuracy, AUC, PSI, feature importance) |
| `organization_model_bindings` | Which model version a tenant uses per task (champion/challenger) |
| `workflow_definitions` | Configurable stages/transitions per org |
| `policy_rules` | Decision thresholds & auto-decision bands per org |
| `api_keys` | Per-org keys for future integrations (hashed, scoped, rate-limited) |
| `notifications` | In-app/email/SMS notification records + delivery status |
| `financial_reports` | Generated report metadata + export artifact links |
| `audit_logs` | **Append-only** — actor, org, action, entity, before/after JSONB, ip, request_id |
| `system_logs` | Technical/application logs pointer (structured logging → aggregator in prod) |

### 5.4 Indexing & performance notes

- Composite indexes lead with `organization_id` (e.g. `(organization_id, status, created_at)` on `loan_applications`) to keep tenant-scoped queries fast and index-only where possible.
- GIN indexes on frequently-filtered JSONB (`feature_snapshot`, `kyc.extra`).
- Partial indexes for hot subsets (e.g. `WHERE status = 'under_review'`).
- Time-series-heavy tables (`transaction_records`, `audit_logs`, `model_metrics`) are **partition-ready** (monthly range partitioning) for production scale.
- Read replicas serve analytics/reporting to keep OLTP latency low; heavy analytics can later move to a star-schema mart.

---

## 6. Backend Clean Architecture Design

### 6.1 Dependency rule

```
        ┌──────────────────────── Presentation (FastAPI routers) ─────────────────────────┐
        │        depends on ▼                                                              │
        │  ┌──────────────── Application (use cases, DTOs, UoW, event publishing) ───────┐ │
        │  │        depends on ▼                                                          │ │
        │  │  ┌──────────── Domain (entities, value objects, invariants, ports) ───────┐ │ │
        │  │  │            (depends on NOTHING external — pure business logic)          │ │ │
        │  │  └────────────────────────────────────────────────────────────────────────┘ │ │
        │  └──────────────────────────────────────────────────────────────────────────────┘ │
        └──────────────────────────────────────────────────────────────────────────────────┘
              ▲ implemented by
        ┌─────┴──────────── Infrastructure (SQLAlchemy repos, Redis, HTTP clients, adapters) ┐
        │   Depends inward on Domain ports; injected at composition root (DI container)        │
        └──────────────────────────────────────────────────────────────────────────────────────┘
```

**Rule:** source code dependencies point only inward. The domain defines *interfaces* (ports); infrastructure provides *implementations* (adapters), wired together at startup in a composition root. Frameworks are details.

### 6.2 Layer responsibilities

- **Domain** — `LoanApplication`, `Applicant`, `RiskAssessment` entities; value objects (`Money`, `NationalId`, `RiskBand`, `CreditScore`); invariants (e.g. *"a loan cannot move to Disbursed without an Approved decision and a passed fraud screen"*); domain events; repository & service *ports*. No SQLAlchemy, no FastAPI, no Pydantic-as-persistence.
- **Application** — use cases (`SubmitLoanApplication`, `RunRiskAnalysis`, `ReviewLoan`, `DisburseLoan`). Each orchestrates domain objects + ports inside a **Unit of Work** (one transaction per use case), maps to/from DTOs, and publishes domain events. This is where authorization checks and tenant context are asserted.
- **Infrastructure** — SQLAlchemy models + repository implementations (translating between ORM rows and domain entities), Redis cache/queue, object storage, the **ML HTTP client**, and the **integration adapters** (`SimulatedWalletAdapter`, etc.). Alembic migrations live here.
- **Presentation** — thin FastAPI routers: parse/validate (Pydantic v2), resolve dependencies (current user, tenant, permissions), call one use case, serialize the result, map domain errors → HTTP problem details. **No business logic in routers.**

### 6.3 Example flow — "Submit loan application"

```
POST /api/v1/loans
  → router validates LoanCreateSchema, resolves TenantContext + requires permission `loan:create`
  → SubmitLoanApplicationUseCase(dto, ctx)
        opens UnitOfWork(transaction; SET LOCAL app.current_org)
        loads Applicant via ApplicantRepository (port)
        constructs LoanApplication entity → enforces invariants
        persists via LoanRepository (port)
        publishes LoanSubmitted event
        commits UoW
  → event handlers (async): AuditLog.record, Notifications.notifyOfficer,
        CreditIntelligence.enqueueRiskAnalysis (calls ml-engine)
  → router returns 201 + LoanResponseSchema
```

### 6.4 Cross-cutting concerns

Config (pydantic-settings, env-driven, 12-factor), structured logging with `request_id`/`org_id` correlation, centralized exception → RFC 7807 problem+json mapping, idempotency keys on mutating endpoints, and an in-process event bus (upgradeable to Redis/broker) for domain events.

### 6.5 Testing strategy

Unit tests on domain (pure, fast, no DB) → integration tests on repositories/use cases against a real Postgres (testcontainers) with RLS asserted → API contract tests → a thin e2e happy-path. **RLS isolation gets an explicit test**: a user from org A must receive 404/empty for org B's data.

---

## 7. Frontend Architecture Design

### 7.1 Stack & structure

React 19 + TypeScript + Vite, **feature-sliced** organization (`features/loans`, `features/applicants`, `features/fraud`, …), TailwindCSS + shadcn/ui for the component system, **React Query** for all server state (caching, background refetch, optimistic updates), React Router for routing, Recharts for visualization, and a light client-state store (Zustand) for UI-only state (theme, sidebar, org switcher selection).

### 7.2 Layered frontend

```
pages/            route screens (compose features)
features/<x>/     self-contained: api hooks · components · types · logic
components/ui/    shadcn/ui primitives (design system)
components/charts/ Recharts wrappers: RiskGauge, CreditScoreCard, CashFlowChart,
                  IncomeVsExpense, PortfolioExposure, LoanStatusTimeline…
lib/              apiClient (typed from OpenAPI), auth, rbacGuard, formatters (NPR, dates)
app/              providers (QueryClient, Theme, Router, AuthProvider), error boundary
```

### 7.3 Type safety across the wire

The backend's **OpenAPI spec is the source of truth**; TypeScript types are generated into `shared/ts-types` and consumed by the frontend. A change to an API schema surfaces as a compile error in the UI — no drift.

### 7.4 Role-aware UI

A single app renders **role-specific dashboards** gated by permissions delivered in the auth context:

| Role | Primary dashboard focus |
|---|---|
| Applicant | Own applications, status timeline, requested documents |
| Loan Officer | Branch queue, application review, KYC/docs, AI summary |
| Risk Analyst | Risk gauges, SHAP explanations, default probabilities, overrides |
| Branch Manager | Branch KPIs, officer performance, approval/rejection funnel |
| Administrator | Org users/roles, workflow & policy config, org analytics |
| Super Admin | Tenant management, platform health, model monitoring |

`RbacGuard` components and route guards hide/disable actions the user lacks permission for — **UI enforcement is convenience only; the API is the real authority.**

### 7.5 UX system

Minimal, professional fintech aesthetic; **light/dark mode** via CSS variables + Tailwind; fully responsive (mobile officers in the field); accessible (WCAG AA, keyboard nav, ARIA on charts); **organization switcher** in the top bar for multi-org users; advanced data tables (server-side pagination/sort/filter driven by React Query); forms with schema validation (react-hook-form + zod) mirroring backend Pydantic constraints; skeleton/loading and error states everywhere; NPR currency and Nepali/English localization.

---

## 8. API Architecture Design

### 8.1 Conventions

- **Versioned base:** `/api/v1`. Breaking changes → `/api/v2`.
- **REST + resource-oriented**, plural nouns, sub-resources for relationships.
- **Auth:** `Authorization: Bearer <access_jwt>` for users; `X-API-Key` for machine/integration clients.
- **Tenant:** derived from the token (never a client-supplied `org_id` in the body — prevents cross-tenant spoofing).
- **Pagination:** cursor-based for large/append-only sets, offset for small admin lists. Envelope: `{ data: [...], page: { next_cursor, total? } }`.
- **Filtering/Sorting:** `?status=under_review&sort=-created_at&created_from=...`.
- **Errors:** RFC 7807 `application/problem+json` with `type`, `title`, `status`, `detail`, `errors[]`, `request_id`.
- **Idempotency:** `Idempotency-Key` header on POST that creates money-moving or externally-visible effects.

### 8.2 Router map

| Prefix | Responsibility (selected endpoints) |
|---|---|
| `/auth` | `login`, `refresh`, `logout`, `mfa/verify`, `password/reset` |
| `/organizations` | tenant CRUD (super admin), `settings`, `branches`, `workflow-definitions`, `policy-rules` |
| `/users` | user CRUD, `roles`, `permissions`, invitations |
| `/applicants` | applicant CRUD, `kyc`, `employment`, `business`, `financials`, `documents`, `transactions` |
| `/loans` | applications CRUD, `submit`, `transition`, `decision`, `disburse`, `repayments`, `workflow-events` |
| `/risk` | `analyze` (trigger), `scores`, `assessments/{id}` |
| `/credit-score` | `compute`, `scores/{applicant_id}` |
| `/fraud` | `screen`, `alerts`, `alerts/{id}/resolve` |
| `/analytics` | approval/rejection rates, risk & PD distributions, portfolio exposure, branch/officer performance, delinquency, disbursement trends |
| `/reports` | generate (async), status, download (PDF/CSV) |
| `/notifications` | list, mark-read, preferences |
| `/admin` | platform ops (super admin): tenants, health, feature flags |
| `/integrations` | connector registry, api-keys, webhook config (adapters; simulated in MVP) |
| `/models` (monitoring) | versions, metrics, drift reports, bindings |

### 8.3 Request/response schema discipline

Every endpoint has explicit Pydantic v2 **request** and **response** models (separate from ORM models). Response models never leak internal fields (hashes, other tenants' ids). OpenAPI is auto-generated and drives client types and API docs.

### 8.4 Async & long-running work

Risk analysis, fraud batch screening, and report generation return `202 Accepted` with a job resource; the client polls `/jobs/{id}` or receives a notification/websocket event on completion. This keeps request latency predictable.

---

## 9. Authentication & RBAC Architecture

### 9.1 Authentication

- **Password hashing:** argon2id (bcrypt acceptable fallback), never plaintext, per-user salt (library-managed).
- **Tokens:** short-lived **access JWT** (~15 min) + long-lived **refresh token** (rotating, stored hashed in `refresh_tokens`).
- **Refresh rotation & reuse detection:** each refresh issues a new refresh token and revokes the old; presenting an already-used (revoked) token triggers **family revocation** (all sessions for that chain) — classic stolen-token defense.
- **JWT claims:** `sub` (user), `org_id`, `branch_id`, `roles`, `perms` (or a perms hash), `jti`, `exp`, `iat`. **Signed with HS256 (symmetric) in the current MVP** — a single backend both issues and verifies its own tokens, so a shared secret is sufficient. **RS256 (asymmetric) is the planned production upgrade** once independent services must verify tokens without holding the signing key. The backend refuses to boot in production with the default development secret.
- **MFA (design-ready):** `mfa_enabled` + TOTP flow scaffolded (`/auth/mfa/verify`), enforced per-role/policy when enabled.
- **Logout / revocation:** refresh tokens revoked in DB; short access-token TTL bounds exposure. Optional Redis denylist of `jti` for immediate access-token kill.

### 9.2 Authorization (RBAC)

- **Model:** Users → Roles (N:M) → Permissions (N:M). Permissions are fine-grained verbs on resources: `loan:create`, `loan:approve`, `risk:override`, `user:manage`, `org:configure`, `report:export`, `fraud:resolve`, `platform:admin`.
- **System roles** (seeded) map to the six required roles; orgs can create **custom roles** by composing permissions.

| Role | Representative permissions |
|---|---|
| Applicant | `loan:create(self)`, `loan:read(self)`, `document:upload(self)` |
| Loan Officer | `loan:read/review(branch)`, `applicant:manage(branch)`, `fraud:read` |
| Risk Analyst | `risk:read/override`, `credit-score:read`, `explanation:read`, `default:read` |
| Branch Manager | branch analytics, `loan:approve(branch, within policy)`, `officer:read` |
| Administrator | `user:manage`, `role:manage`, `org:configure`, org-wide analytics |
| Super Admin | `platform:admin`, tenant management, model monitoring (cross-tenant, audited) |

- **Enforcement point:** a FastAPI dependency `require(permission, scope)` runs in the router *before* the use case; scope (`self`/`branch`/`org`) is checked against `TenantContext`. Combined with RLS, this is **two independent gates**.
- **Policy-based decisions:** approval *limits* (amount thresholds requiring a Branch Manager or dual approval) live in `policy_rules`, not code — so lending authority is configurable per tenant.

### 9.3 Session & audit linkage

Every authenticated request carries a `request_id`; auth events (login success/failure, refresh, role change, permission-denied) are written to `audit_logs`. Repeated failures feed rate limiting and lockout.

---

## 10. Machine Learning Service Architecture

### 10.1 Why a separate service

The ML engine has different dependencies (XGBoost/CatBoost/LightGBM/SHAP), different scaling needs, and a different release cadence than the transactional backend. It runs as an **independent FastAPI service** the backend calls over HTTP (internal network), authenticated with a service token. The backend's `credit_intelligence` module is the **only** place that talks to it (a single anti-corruption layer / gateway).

### 10.2 Component view

```
                 ┌──────────────────────────── ML ENGINE ─────────────────────────────┐
 backend ──HTTP──►  serving/ (FastAPI)                                                  │
 (credit_        │     /predict/risk   /predict/credit-score   /predict/default        │
  intelligence)  │     /predict/fraud  /analyze/behavior       /explain                │
                 │        │                                                              │
                 │        ▼                                                              │
                 │   features/ ── feature engineering ── (light) feature store ─────────┤
                 │        │  income stability, savings ratio, cashflow volatility,       │
                 │        │  DTI, utility-payment regularity, txn anomalies…             │
                 │        ▼                                                              │
                 │   models/ ─ risk (clf) · credit_score (reg→0..100) · default (calib  │
                 │        │     PD) · fraud (rules + IsolationForest/GBM) · behavior     │
                 │        ▼                                                              │
                 │   explainability/ ─ SHAP values → human-readable rationale           │
                 │        ▼                                                              │
                 │   registry/ ─ model_versions (artifact URI, metrics, stage)          │
                 │   monitoring/ ─ drift (PSI/KS), performance, prediction distributions │
                 └────────────────────────────────────────────────────────────────────┘
   training/ (offline) ── data prep → train → evaluate → calibrate → register model version
```

### 10.3 The seven ML capabilities

1. **Credit Risk Prediction** — multiclass (low/medium/high) gradient-boosted classifier; returns band + class probabilities + confidence.
2. **Alternative Credit Score** — regression/scorecard mapping behavioral features to **0–100** with subscores (repayment behavior, cashflow, leverage, stability); monotonic constraints where sensible for fairness/interpretability.
3. **Default Probability (PD)** — calibrated binary classifier (Platt/isotonic) over a defined horizon (e.g. 12 months); outputs a probability, not just a label.
4. **Financial Behavior Analysis** — engineered features: income stability, spending patterns, savings ratio, cashflow volatility, DTI, utility-payment regularity; optional clustering for behavioral segments.
5. **Fraud Detection** — **hybrid**: deterministic rules (velocity, duplicate identity, impossible income, document mismatch) + anomaly/ML model (IsolationForest / gradient boosting) on transaction and application features. Produces `fraud_alerts` with severity and reasons.
6. **Explainable AI (SHAP)** — every prediction returns top positive/negative feature contributions, translated into plain language ("High debt-to-income ratio (52%) increased risk; 18 months of stable salary reduced it"). Stored in `ai_explanations`. **No decision surfaces without an explanation.**
7. **Model Monitoring** — tracks accuracy/AUC over labeled outcomes, **feature & prediction drift** (PSI/KS), feature-importance stability, and prediction distributions; raises alerts and feeds the monitoring dashboard.

### 10.4 Model lifecycle & governance

- **Registry & versioning:** every trained model is registered in `model_versions` (algorithm, hyperparameters, training-data snapshot ref, metrics, artifact URI, stage: `staging`/`production`/`archived`). Serving loads by stage/binding — **never** an ad-hoc pickle.
- **Reproducibility:** training pipelines are deterministic (seeded), versioned, and log data snapshots.
- **Champion/Challenger & per-tenant binding:** `organization_model_bindings` lets a tenant run a specific version; challengers can shadow-score for evaluation before promotion.
- **Fairness & compliance hooks:** monitoring includes subgroup performance checks; decisions retain the exact `feature_snapshot` + `model_version_id` so any decision is **reconstructible and defensible** to a regulator or auditor.
- **Human-in-the-loop:** ML outputs are **decision support**, not autonomous approval, unless policy explicitly enables auto-decision bands — and even then within configured limits with full audit.

### 10.5 Contracts

Request/response schemas live in `ml-engine/src/contracts` and mirror the backend DTOs so the wire contract is explicit and versioned. Predictions are **idempotent** per `(application_id, model_version)` and cached in Redis to avoid recompute.

---

## 11. Integration Layer Architecture

### 11.1 Principle — ports & adapters, config-driven

Every external system is expressed as a **port** (interface) owned by the application/domain, with interchangeable **adapters**. The core has *no* knowledge of eSewa, a specific bank, or a bureau — only of the interface. Which adapter is active is **configuration**, resolved by a registry/factory at runtime and selectable per tenant.

```
        application/domain ──depends on──►  PORTS (interfaces)
                                              WalletConnectorPort
                                              BankConnectorPort
                                              CreditBureauPort
                                              IdentityVerificationPort
                                              SmsGatewayPort · EmailPort · PaymentGatewayPort
                                                     ▲ implemented by
        infrastructure/integrations ── ADAPTERS (swappable)
            MVP:  SimulatedWalletAdapter · SimulatedBankAdapter · SimulatedBureauAdapter …
            Later: EsewaAdapter · KhaltiAdapter · ImePayAdapter · <Bank>Adapter · <Bureau>Adapter
                   (added WITHOUT touching core business logic)
```

### 11.2 Reliability & correctness patterns

- **Idempotency keys** on all outbound calls that cause effects.
- **Outbox pattern** for events that must reach an external system exactly once (write intent in the same DB transaction, dispatch asynchronously).
- **Circuit breaker + retry with backoff + timeouts** around every adapter; failures degrade gracefully and are audited.
- **Webhook ingress** (for callbacks) verified by signature + idempotency; mapped through an anti-corruption layer into domain events.
- **Secrets & keys** per integration stored in a secrets manager, never in code or DB plaintext; per-tenant API keys in `api_keys` (hashed, scoped, rate-limited).

### 11.3 MVP honesty

For the MVP, adapters are `Simulated*` implementations that generate plausible synthetic responses and are flagged `is_simulated = true` on any data they produce (e.g. `transaction_records.is_simulated`). They are **clearly not** representing real financial connections. Swapping to a real provider later is: (1) implement the adapter, (2) add credentials to secrets, (3) flip the tenant's config binding. No core change.

### 11.4 Planned connectors (design-only)

Commercial banks · Digital wallets (eSewa, Khalti, IME Pay) · Credit bureaus · Government identity verification · SMS gateways · Email services · Payment gateways. Each maps to one of the ports above.

---

## 12. Docker & Infrastructure Architecture

### 12.1 Services (containers)

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  frontend    │  │  backend     │  │  ml-engine   │  │  postgres    │  │  redis       │
│  Vite build →│  │  FastAPI     │  │  FastAPI     │  │  primary     │  │  cache /     │
│  Nginx static│  │  (Uvicorn/   │  │  (models)    │  │  (+replicas  │  │  queue /     │
│              │  │   Gunicorn)  │  │              │  │   in prod)   │  │  rate-limit  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │                 │
       └─────────────────┴──── docker network (internal) ────┴─────────────────┘
                                   │
                          ┌────────┴────────┐        ┌──────────────┐
                          │  reverse proxy   │        │  worker(s)   │
                          │  Nginx/Traefik   │        │  Celery/Arq  │
                          │  TLS · routing   │        │  async jobs  │
                          └──────────────────┘        └──────────────┘
```

- **frontend** — multi-stage build (Vite → static assets served by Nginx).
- **backend** — FastAPI under Gunicorn/Uvicorn workers; runs Alembic migrations on deploy.
- **ml-engine** — separate image with the ML dependency stack; scaled independently.
- **postgres** — primary (dev: single; prod: managed with replicas, PITR backups).
- **redis** — cache, rate-limit buckets, task queue broker (future-ready as requested).
- **worker** — async task runner sharing backend code (risk jobs, reports, notifications, drift).
- **reverse proxy** — TLS termination, routing, security headers.

### 12.2 Configuration strategy

Strict **12-factor**: all config via environment variables, documented in `.env.example`, never committed secrets. Separate compose files for dev (`docker-compose.yml`, hot-reload, seed data) and prod (`docker-compose.prod.yml`, built images, resource limits, healthchecks). Per-environment `.env` files sourced from a secrets manager in real deployments.

### 12.3 CI/CD readiness

- **CI:** lint + typecheck + unit/integration tests per package; container build; **security scanning** (dependency audit, SAST, image scan, secret scan).
- **Migrations:** Alembic gated in the pipeline; forward-only in prod.
- **CD:** build → push image → run migrations → rolling deploy → smoke tests → health-gated promotion. **The MVP structure is CI/CD-ready; full pipelines are wired as the team matures** (start with CI on every PR).
- **Path to Kubernetes:** `infrastructure/k8s` reserved; the stateless services and externalized state (Postgres/Redis/object storage) make the lift straightforward when scale demands it.

### 12.4 Observability (production)

Structured JSON logs → aggregator (Loki/ELK); metrics (Prometheus) + dashboards (Grafana); tracing (OpenTelemetry) with `request_id`/`org_id` propagation; ML-specific dashboards from `model_metrics`/`drift_reports`; alerting on SLOs, error rates, drift, and fraud spikes.

---

## 13. Security & Compliance Architecture

### 13.1 Security controls (by category)

**Identity & access:** argon2id password hashing; short-lived access JWT + rotating refresh with reuse detection; RBAC with fine-grained permissions; MFA design-ready; per-endpoint permission gates; account lockout on brute force.

**Tenant isolation:** `organization_id` everywhere + **PostgreSQL RLS** (DB-enforced), plus application-layer scoping — two independent barriers.

**Input & data safety:** Pydantic v2 validation on every request; **parameterized queries / ORM only** (no string-built SQL) → SQL-injection safe; output encoding on the frontend; file uploads scanned and stored out-of-band with checksums; strict CORS allowlist; security headers (HSTS, CSP, X-Frame-Options, etc.).

**Transport & storage encryption:** TLS 1.2+ everywhere in transit; encryption at rest at the disk/volume level; **column-level encryption for the most sensitive PII** (national IDs, KYC docs) via app-level or `pgcrypto`; object storage encrypted; secrets in a manager (not code/DB).

**Rate limiting & abuse:** Redis token-bucket limits per IP / per user / per API key; stricter limits on `/auth` and export endpoints.

**API keys:** per-tenant, hashed at rest, scoped to permissions, individually revocable and rate-limited.

**Auditability:** append-only `audit_logs` for every critical action (auth, decisions, role changes, config changes, exports, integration calls) with actor, tenant, before/after, IP, and `request_id`. Financial and audit tables are never hard-deleted.

**Secure SDLC:** dependency scanning, SAST, secret scanning, image scanning in CI; least-privilege service accounts; principle of least privilege across the DB roles (app role cannot bypass RLS; a separate, audited admin role can).

### 13.2 Compliance posture (Nepal / NRB)

The architecture is built to be **compliance-ready**, with the explicit caveat that **specific Nepal Rastra Bank directives and data-protection obligations must be confirmed with legal/compliance counsel** — this document does not assert exact regulatory text.

Design provisions that support a Nepali lending regulatory posture:

- **KYC/AML readiness:** structured KYC records, verification status, document retention, and audit trails; hooks for future government identity verification and AML/sanctions screening via the integration layer.
- **Auditability & reporting:** immutable audit logs and a reporting module capable of producing regulator-style reports (portfolio, delinquency, exposure) as PDF/CSV.
- **Explainability of credit decisions:** every AI-influenced decision retains its inputs, model version, SHAP explanation, and reviewer chain — supporting fair-lending scrutiny and adverse-action explanations.
- **Data residency & retention:** the multi-tenant strategy supports **in-country hosting** and per-tenant **schema/DB isolation** for institutions with residency requirements; retention windows are configurable and enforced.
- **Human accountability:** ML is decision *support*; approvals carry a responsible human actor within configured authority limits.

### 13.3 Data lifecycle

Classification (public / internal / PII / financial-sensitive) drives handling; retention and purge policies per class and per regulation; right-to-export on tenant offboarding; secure deletion honoring audit-retention obligations (soft-delete + scheduled purge after the mandated window).

---

## 14. Development Roadmap (MVP → Production)

```
Phase 0 ── Foundations (this document approved)
   Repo scaffolding · Docker compose · CI (lint/test) · DB base + RLS · auth skeleton

Phase 1 ── Core lending MVP  ────────────────────────────────────────────►  university-demoable
   Tenancy + RBAC · Applicant & financial profile · Loan application + workflow
   ML v1 (risk, credit score, default PD, fraud rules) · SHAP explanations
   Officer/Analyst/Manager dashboards · Simulated integrations · Audit logging

Phase 2 ── Intelligence & analytics depth
   Behavior analysis · fraud ML model · portfolio analytics · reporting (PDF/CSV)
   Model registry + monitoring dashboard · notifications · async workers

Phase 3 ── Hardening for production
   MFA · refresh-rotation reuse detection · rate limiting · column encryption
   Read replicas · partitioning · observability stack · full CI/CD · security review

Phase 4 ── Real integrations & scale
   First real adapters (wallet/bureau/identity) behind existing ports · SLAs
   Champion/challenger models · schema-per-tenant option · k8s (if scale demands)

Phase 5 ── Regulatory & enterprise
   NRB reporting packs · formal compliance review · pen-test · data-residency tiers
   Partner/API marketplace · advanced fraud graph analytics
```

---

## 15. Recommended MVP Scope (University Project)

**Goal:** a genuinely impressive, defensible capstone that demonstrates the full-stack + ML + multi-tenant story **without** drowning in production hardening. Build the *spine*, not every organ.

**Include:**

- **Multi-tenancy (real):** 2–3 seeded demo organizations with `organization_id` + RLS actually enforced. This is your differentiator — show cross-tenant isolation working.
- **Auth & RBAC:** JWT access + refresh, argon2 hashing, the six roles, permission-gated endpoints. (MFA *designed* but not wired.)
- **Applicant + financial profile:** core tables and forms (personal, KYC, income/expense, assets/liabilities, existing loans). **Transactions simulated** via `SimulatedWalletAdapter` — clearly labeled.
- **Loan workflow:** draft → submitted → under review → AI analysis → decision (approve/reject/needs-info) → disbursed. Configurable stages via `workflow_definitions` (even if you seed one default).
- **ML engine (separate service) with 3–4 models:** credit risk (classification), alternative credit score (0–100), default probability (calibrated), and **rule-based fraud** (add an anomaly model if time allows). Train on a **synthetic but realistic** dataset you generate.
- **Explainable AI (SHAP):** the "wow" feature — show top contributing factors in plain language for every prediction. Persist to `ai_explanations`.
- **Dashboards:** Loan Officer, Risk Analyst, and one Analytics view (approval rate, risk distribution, portfolio exposure) with Recharts gauges/cards/charts, light+dark mode.
- **Audit logging:** every decision and state transition recorded — great for the demo narrative.
- **Docker Compose:** frontend + backend + ml-engine + postgres + redis, one `docker compose up`.

**Explicitly defer (mention in your report as "future work"):** real integrations, MFA enforcement, refresh-reuse detection, column encryption, read replicas/partitioning, Kubernetes, model champion/challenger, full observability, formal compliance certification.

**Why this scope wins:** it proves architecture maturity (clean layers, RLS multi-tenancy, ports/adapters, explainable ML) — the things that separate a *platform* from a *credit-scoring script* — while staying buildable by a small team in a semester.

---

## 16. Recommended Production Scope (Real Fintech Startup)

**Goal:** everything in the MVP, **hardened and de-risked** for real money and real regulators. The MVP proves the design; production proves you can be trusted with financial data.

**Add on top of MVP:**

- **Security hardening:** enforce MFA (esp. Admin/Super Admin), refresh-token reuse detection with family revocation, per-key/per-user/per-IP rate limiting, column-level PII encryption, secrets manager, WAF, full security headers, dependency/SAST/image/secret scanning in CI, and an **external penetration test** before go-live.
- **Data resilience:** managed Postgres with read replicas, PITR backups + tested restores, partitioning of high-volume tables, and a documented DR plan (RPO/RTO).
- **Real integrations, one at a time:** implement adapters behind existing ports (identity verification and one wallet/bureau first), with circuit breakers, outbox, idempotency, and signed webhooks. Each guarded by SLAs and audited.
- **Model governance:** production model registry, **monitoring for accuracy/drift/fairness**, champion/challenger with shadow scoring, documented model cards, and reconstructable decisions for every loan.
- **Compliance program:** formal review against **NRB directives and applicable data-protection law with legal counsel**; KYC/AML workflows; regulator reporting packs; configurable retention/residency; per-tenant schema/DB isolation tier for large institutions.
- **Reliability & ops:** full observability (logs/metrics/traces), SLOs + alerting, on-call runbooks, blue-green/rolling deploys, and load testing to known capacity.
- **Scale path:** Kubernetes when traffic warrants; stateless services already make this a lift-not-rewrite.
- **Governance:** four-eyes approval on high-value loans (policy-driven), separation of duties, and immutable audit exports.

**Sequencing advice:** do **not** attempt all of this at once. Follow the roadmap — ship the MVP spine, harden security and data resilience next (Phase 3), then add *one* real integration and prove the adapter model before scaling the connector catalog. Bring compliance counsel in **before** onboarding the first real institution, not after.

---

## 17. Appendix: Key Architecture Decision Records (ADRs)

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | **Modular monolith** for backend, separate ML service | Startup velocity + transactional simplicity now; clean extraction path later. ML has distinct runtime → separate from day one. |
| ADR-002 | **Shared-schema + RLS** multi-tenancy (MVP) | DB-enforced isolation with low ops cost; upgrade path to schema/DB-per-tenant for enterprise/residency clients. |
| ADR-003 | **Clean Architecture + Ports/Adapters** | Business rules independent of frameworks; makes "pluggable integrations later" real, not aspirational. |
| ADR-004 | **HS256 JWT (MVP) + rotating refresh w/ reuse detection; RS256 as prod upgrade** | Single service signs+verifies → symmetric secret suffices now; asymmetric later for cross-service verification. Strong session-theft defense via refresh rotation. |
| ADR-005 | **SHAP-mandatory explainability** | No black-box decision reaches a human or a regulator; fair-lending & auditability. |
| ADR-006 | **Config-driven workflow & policy** (`workflow_definitions`, `policy_rules`) | No hardcoded business logic; per-tenant customization without code forks. |
| ADR-007 | **Simulated integration adapters, explicitly flagged** | Honesty about MVP capabilities; zero-core-change path to real connectors. |
| ADR-008 | **OpenAPI as the type source of truth** | Eliminates FE/BE contract drift via generated TypeScript types. |
| ADR-009 | **Money as `NUMERIC`, UTC `timestamptz`, UUIDv7 PKs** | Correctness for financial data; index-friendly ordered keys. |
| ADR-010 | **Append-only audit log via domain events** | Tamper-evident compliance trail decoupled from business modules. |

---

*End of architecture specification. No application code has been written. Awaiting your next instruction before implementation.*
