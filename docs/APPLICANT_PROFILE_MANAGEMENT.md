# Applicant Financial Profile Management

Authorized loan officers and administrators can maintain the complete underwriting profile after
onboarding. The profile contract covers personal and contact information, KYC identity reference,
employment or business details, income, expenses, assets, liabilities, and external loans.

## Update semantics

`PATCH /api/v1/applicants/{id}/profile` is a true partial update:

- omitted fields and collections remain unchanged;
- an explicitly supplied collection atomically replaces that section;
- an explicitly supplied `null` employment, business, or national ID clears that section;
- required identity fields cannot be explicitly cleared;
- negative financial values and unsupported frequencies are rejected by Pydantic validation;
- the applicant row is locked for the duration of the update.

The same tenant, applicant-ownership, and branch authorization policy used by loan origination is
applied to profile reads and writes. Applicant accounts are read-only for this endpoint; staff need
`applicant:manage` to modify underwriting data.

## Audit and privacy

Every successful update stores complete non-PII before/after financial evidence in the append-only
audit log. Full name, phone, email, address, and national ID are represented by keyed HMAC-SHA256
fingerprints in audit JSON, proving whether a value changed without duplicating raw identity data
or exposing low-entropy identifiers to offline dictionary attacks. The canonical values remain only
in their authorized domain tables.

Previously persisted AI analyses retain their original feature snapshots. Updating a profile does
not silently rewrite a historical lending prediction; a new governed analysis must be requested to
produce a new versioned decision.
