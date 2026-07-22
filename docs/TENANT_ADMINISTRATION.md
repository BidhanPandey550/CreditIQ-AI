# Tenant and Branch Administration

The organization settings surface is restricted by `org:configure`. It allows an administrator to
maintain institutional name, NRB license reference, ISO-style currency code, IANA timezone, and
fiscal-year start month through a typed contract. Arbitrary JSON settings are not accepted by the
API. Every change stores a before/after snapshot in the compliance audit log.

Branches have tenant-unique normalized codes and an explicit active/inactive lifecycle. Historical
records retain their branch references; branches are never hard-deleted. Inactive branches cannot
receive new applicants, loans, or staff assignments, while existing records remain reviewable.
Branch creation and state changes are tenant-checked in the application service and audited.

## Isolation boundary

Business data is protected by forced PostgreSQL RLS. Identity and tenant-control tables such as
`organizations`, `branches`, and `users` currently use mandatory application-layer organization
predicates because platform onboarding still shares the application database connection. A real
production deployment must introduce a separate, tightly controlled platform-administration
connection/role before extending RLS to these control-plane tables. The project does not claim that
this remaining control-plane separation is already implemented.
