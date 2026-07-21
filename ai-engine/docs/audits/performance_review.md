# Sprint 8.5 — Performance & Resource Review

Local, deterministic (seed 42), 300-row synthetic dataset, `ai-engine/.venv`. Timings are
indicative single-run measurements (no brittle assertions added).

| Stage | Time | Notes |
|---|---|---|
| `load_config()` | ~11 ms | re-reads base.yaml + env YAML each call; `get_config()` is cached |
| Feature engineering (300 rows) | ~12 ms | vectorized (Sprint 3.5 removed row-wise apply) |
| Credit training (LogReg, 3-fold CV) | ~164 ms | dominated by cross-validation |
| Credit inference (1 row) | ~0.4 ms | fast |
| Explanation (1 row, marginal) | ~6.6 ms | O(n_features) predict calls — acceptable |
| Fraud ensemble fit (5 detectors) | ~209 ms | one-time per reference population |
| Fraud analyze (1 row) | ~9 ms | 5 detectors scored |
| Full smoke test | ~0.49 s | end-to-end built path |

## Observations
- **No material inefficiencies confirmed.** No import-time heavy work (import-all is instant and
  side-effect-free). No duplicate model loading in the built path.
- **Minor (P3):** `load_config()` re-parses YAML on every explicit call (~10 ms). Immaterial at
  current usage; a future decision-engine hot path should reuse a single injected `EngineConfig`
  rather than calling `load_config()` per request.
- **Minor (P3):** the marginal explainer does `n_features + 1` predictions per explanation; fine for
  ~10 features, but a SHAP/vectorized path would scale better for wide models (SHAP already wired,
  activates when installed).

No premature optimization performed. No performance regressions introduced.
