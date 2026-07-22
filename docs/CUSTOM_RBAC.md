# Tenant Custom Roles and Live Authorization

CreditIQ AI provides six immutable platform system roles and allows each institution to compose
additional tenant-owned roles from the canonical permission catalog.

## Security invariants

- A tenant administrator can grant only permissions currently held by that administrator.
- `platform:admin` and the Super Admin role cannot be delegated by tenant administrators.
- System roles cannot be renamed or edited through tenant APIs.
- Role names are normalized and case-insensitively unique inside an organization.
- Every create/update operation records permission-level before/after audit evidence.
- User creation fails if even one requested role is missing; partial role assignment is forbidden.
- Applicant accounts remain restricted to the single Applicant system role.

JWT claims are not treated as the ongoing authorization source. Every protected request verifies the
account and resolves current branch, applicant ownership, roles, and permissions from PostgreSQL.
Disabling an account or reducing a role therefore takes effect immediately, even if the caller still
holds an otherwise valid short-lived access token.

## API

- `GET /api/v1/roles` — system and tenant role catalog visible to the caller.
- `POST /api/v1/roles` — create a tenant custom role.
- `PATCH /api/v1/roles/{id}` — rename or recompose a custom role.
- `GET /api/v1/users/permissions` — canonical permission descriptions.
- `GET /api/v1/users/roles` — roles safely assignable by the current administrator.

Role deletion is intentionally unsupported. Removing a role that is still assigned can orphan user
access expectations and destroy historical meaning; a future retirement workflow should include
assignment migration and explicit audit approval.
