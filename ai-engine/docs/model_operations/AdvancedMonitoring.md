# Advanced Model Operations

CreditIQ AI now treats model operations as an independent control plane around inference. The
registry remains the source of truth, while monitoring services consume privacy-safe aggregates.

## Implemented controls

- Population Stability Index (PSI) drift analysis uses reference quantile bins and reports each
  numeric feature independently. Minimum sample size and warning/critical levels are configured.
- Delayed-outcome performance monitoring compares production ROC AUC with its approved baseline.
- Model health combines inference reliability, drift and delayed performance using worst-state
  semantics, so a healthy latency signal cannot hide critical drift.
- Alerts are deduplicated while open and can be acknowledged. Delivery is deliberately an adapter
  extension point; no fake email or banking integration exists.
- Lineage validates parent references and cycles, and exposes ancestry and child traversal.
- Promotion requires a champion, configurable metric floors and bounded regression versus the
  incumbent. Rollback uses the registry's atomic version switch.

All thresholds live under `monitoring` in the unified YAML/Pydantic configuration. Raw applicant
features and identity values are not retained by operational monitoring or alerts.
