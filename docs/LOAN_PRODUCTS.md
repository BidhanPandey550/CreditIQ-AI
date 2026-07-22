# Loan Product Policy

Loan products are tenant-owned lending policies used consistently by origination and servicing.
Administrators configure a normalized unique code, display name, amount range, tenor range, annual
interest rate, and active/inactive lifecycle state.

When an application selects a product, the backend—not the browser—verifies that the product belongs
to the caller's organization, remains active, and permits the requested amount and tenor. An inactive
product remains attached to historical loans but cannot accept new applications. At disbursement,
the product rate is used unless an explicitly authorized disbursement override is supplied.

Every create or update operation records before/after evidence in the compliance audit log. Product
codes are uppercase-normalized and protected by a database unique constraint per organization.

## API

- `GET /api/v1/loan-products` — active products available to authorized loan users.
- `GET /api/v1/loan-products?include_inactive=true` — administrator inventory.
- `POST /api/v1/loan-products` — create a validated policy.
- `PATCH /api/v1/loan-products/{id}` — revise pricing/limits or lifecycle status.

Existing products are assigned deterministic `LEGACY-*` codes during migration. Product deletion is
intentionally unsupported because historical decisions and repayment schedules must remain
reconstructable.
