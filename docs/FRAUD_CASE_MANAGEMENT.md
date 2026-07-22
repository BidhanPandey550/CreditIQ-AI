# Fraud Case Management

CreditIQ AI converts non-low fraud screening outcomes into tenant-isolated investigation records.
The alert center is an operational control around the model output; it does not claim that an
anomaly is proven fraud.

## Workflow

1. Governed loan analysis creates an `open` alert with severity and machine-readable reasons.
2. Users with `fraud:read` may list alerts only for their organization and authorized branch.
3. Users with `fraud:resolve` investigate an alert and record one terminal disposition:
   `confirmed` or `dismissed`.
4. A non-empty rationale of 10–2000 characters, investigator identity, and UTC timestamp are stored.
5. The mutation writes before/after evidence to the append-only compliance audit log.

Resolved alerts cannot be overwritten. The service obtains a row lock before disposition so two
analysts cannot race to produce conflicting outcomes.

## Decision safety

Loan approval is blocked while an alert at a configured blocking severity remains `open` or
`confirmed`. Only an analyst's explicit `dismissed` disposition clears that guard. The severity set
is configured with `FRAUD_APPROVAL_BLOCKING_SEVERITIES` and defaults to `high,critical`.

## API

- `GET /api/v1/fraud/alerts` — status/severity filtering plus bounded offset pagination.
- `GET /api/v1/fraud/alerts/{id}` — authorized case detail.
- `POST /api/v1/fraud/alerts/{id}/resolve` — terminal disposition and rationale.

PostgreSQL row-level security enforces organization isolation. Application-layer branch predicates
provide additional intra-tenant isolation. The React alert center is a convenience client; API
authorization remains authoritative.

## Extension points

Case assignment, evidence attachments, four-eyes approval, suspicious-activity reporting, external
case-management connectors, and institution-specific escalation SLAs should be added as explicit
workflows. They must not be inferred from anomaly scores alone.
