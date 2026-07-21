# Sprint 8.5 — Security & Privacy Review

Scope: the `creditiq_ai` library (the separate `backend/`, `ml-engine/`, `frontend/` apps are out
of scope for this library audit).

## Static scans (actual results)

| Check | Command | Result |
|---|---|---|
| Unsafe YAML | `grep "yaml.load("` | **none** — only `yaml.safe_load` is used (`config/loader.py`) |
| Pickle / eval / exec | `grep "pickle.load\|eval(\|exec("` | **none** |
| Hardcoded secrets | `grep -iE "(password|secret|api_key|token)\s*=\s*['\"]"` | **none in library** |
| Model deserialization | `grep "joblib.load"` | one authoritative site inside `ArtifactStore`, after mandatory SHA-256 verification |

## Findings

- **F2 (P1) — model artifacts are deserialized without integrity verification.**
  Trainer and detector persistence now delegates to `ArtifactStore`; public loads without a trusted
  checksum fail closed before deserialization.
  directly. `joblib` uses `pickle`, so loading a corrupted or tampered artifact is unsafe, and the
  Sprint-8 requirement ("never silently load a model whose integrity validation fails") is **unmet**
  because the registry's SHA-256 checksum layer is not yet implemented. **Recommendation:** load all
  artifacts through a registry method that verifies a stored SHA-256 checksum first and raises
  `ArtifactIntegrityError` on mismatch. (Implemented and covered by tampering and public-loader tests.)
  feature work, out of scope for an audit sprint.)

- **Privacy (PASS for built code).** The explanation narrative does **not** leak the applicant
  identifier (asserted in `test_platform_integration`). Fraud/monitoring redaction utilities and
  identifier hashing are **NOT BUILT** (required by Sprint 8) — a gap, not a leak, because there is
  no monitoring pipeline persisting records yet.

- **Logging.** Loguru logs contain aggregate stats (row counts, scores), not raw applicant PII, in
  the built modules. No citizenship/national-ID/token/secret logging found.

## Verdict
No P0 data-leakage or code-execution vulnerabilities in the library. **One P1 (F2)**: unsafe model
loading is possible until artifact integrity verification is implemented — this alone blocks a
"READY" release decision.
