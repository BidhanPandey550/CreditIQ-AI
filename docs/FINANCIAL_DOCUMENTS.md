# Financial Document Security

Financial documents are private applicant resources; they are never placed in the frontend bundle
or exposed through a static directory. The current storage implementation is a single-node adapter
behind generated tenant/applicant keys. It can later be replaced by encrypted object storage
without changing applicant authorization or API contracts.

## Upload flow

1. JWT permission and tenant context are validated.
2. Applicant ownership or staff branch scope is enforced through the canonical applicant service.
3. The upload rate limit and configured byte limit are applied.
4. Declared MIME type is checked against the allowlist and verified against PDF/JPEG/PNG magic
   bytes. Client filenames never determine a storage path.
5. The ClamAV INSTREAM adapter scans the bytes. Production refuses to start unless scanning is
   required and a scanner host is configured. Development may explicitly record
   `scan_unavailable`; that state is blocked whenever required scanning is enabled.
6. Content is atomically written under a UUID key with private directory/file permissions. Only
   metadata and a SHA-256 checksum are stored in PostgreSQL.
7. The upload is recorded in the correlated compliance audit log without file contents.

## Download flow

Every request re-evaluates applicant ownership/branch authorization, reads from the private storage
adapter, and verifies SHA-256 before returning bytes with `Content-Disposition: attachment` and
`X-Content-Type-Options: nosniff`. Integrity mismatch, unsafe scan state, missing content, and
cross-applicant access fail closed. Downloads are audited.

## Deployment boundary

The development Compose stack includes ClamAV and persistent private volumes. A distributed
production deployment should replace the local adapter with versioned encrypted object storage,
retention/legal-hold controls, backup/restore testing, and an orphan-reconciliation job. This
module does not perform government KYC verification; it stores evidence for a future verified
identity connector.
