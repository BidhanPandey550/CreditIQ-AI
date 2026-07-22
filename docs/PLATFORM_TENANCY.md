# Platform Tenant Administration

CreditIQ AI distinguishes the platform administrator's home organization from the single effective
organization selected for a request. This supports platform operations without weakening PostgreSQL
row-level security.

## Control plane

Super Admins can list organization identities, onboard a tenant with its Head Office and first
Administrator, suspend/reactivate a tenant with a mandatory reason, and open an active tenant from
the Tenant Management screen. Organization and user identity tables are control-plane tables. The
application's `admin_session` is unscoped only for those tables; it uses the same non-superuser role
and cannot bypass RLS on tenant-owned tables.

Onboarding and lifecycle mutations write audit evidence in the affected tenant by setting an
explicit transaction-local tenant context before inserting the audit event.

## Switched access tokens

`POST /api/v1/auth/switch-organization` issues a normal short-lived access token containing:

- `home_org_id`: the organization that owns the Super Admin account.
- `org_id`: the one effective organization for data access.

Every protected request reloads the user, roles, and permissions from the home organization. If
`platform:admin` has been revoked, a switched token stops working immediately. The effective
organization must still exist and be active. A switched identity receives no inherited branch or
applicant scope, and `tenant_session(org_id)` pins every operational query to the effective tenant.

Refresh-token rotation intentionally issues a home-scoped access token. Switching is therefore a
temporary explicit action rather than a persistent impersonation. MFA and other identity-security
changes always execute and audit in the home organization.

## Frontend isolation

The organization switcher is rendered only for `platform:admin`. On switch and logout, the complete
React Query cache is cleared before new tenant data is fetched, preventing stale records from a
previous tenant from remaining visible. The API remains the authorization authority; hiding controls
in the UI is not treated as a security boundary.

A platform administrator must switch away from the current organization before suspending it. Once
suspended, all existing tokens targeting that organization are rejected by live organization-status
validation.
