# Applicant Transaction Evidence

CreditIQ AI stores bank, wallet, and utility transaction records behind the applicant authorization
boundary. The current MVP generates wallet evidence through `SimulatedWalletAdapter`; it does not
connect to eSewa, Khalti, a bank, or any other financial provider.

## API and isolation

`GET /api/v1/applicants/{applicant_id}/transactions` requires `applicant:read` and reuses the same
tenant, branch, and applicant-ownership checks as the rest of the applicant profile. Results are
paginated, newest first, and may be filtered by the controlled source types `bank`, `wallet`, and
`utility`. Aggregate credits, debits, net cash flow, and simulated-record count are computed in SQL
over the authorized filter rather than over only the displayed page.

The database uses a composite `(organization_id, applicant_id, txn_date)` index for the dominant
access path. PostgreSQL row-level security remains the final tenant isolation boundary.

## Simulation safety

Synthetic records always carry `is_simulated=true` and the UI displays a visible warning. Stable
SHA-256-derived seeding makes the generated evidence reproducible within a calendar day and avoids
Python process hash randomization. Regeneration deletes only the applicant's previous simulated
wallet batch before inserting its replacement; imported or future connector-sourced records are
never deleted. The replacement count and new record count are audited.

## Financial behaviour view

The applicant detail page shows total inflows, total outflows, net cash flow, a six-month chart, and
the latest transaction evidence. These records feed the existing income-stability and cash-flow
volatility features. The view never labels simulated evidence as a real financial connection.

Future connectors must implement the existing integration port, preserve provider provenance and
idempotency keys, and pass a separate security/compliance review before they may write non-simulated
records.
