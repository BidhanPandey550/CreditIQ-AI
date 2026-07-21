# Technical Debt Register (as of Sprint 8.5 audit)

| ID | Sev | Area | Description | Disposition |
|---|---|---|---|---|
| D1 | ~~P1~~ | Model ops / security | Model artifacts (`joblib.load`) deserialized with no integrity check | **RESOLVED AND VERIFIED** — every trainer/detector public loader delegates to `ArtifactStore`; missing or mismatched SHA-256 fails closed before deserialization |
| D2 | ~~P1~~ | Platform | No unified credit+fraud Decision Engine | **RESOLVED** — `creditiq_ai.decision.DecisionEngine` (config-driven policy, integrity blocks, fraud failure degrades); 10 tests (scenarios A–G) |
| D3 | ~~P2~~ | Model ops | Registry persistence/production selection was missing | **RESOLVED (local/single-node)** — atomic JSON registry, lifecycle enforcement, checksum-required artifacts, unique production selection, rollback, and audit history |
| D4 | P2 | Monitoring | Operational monitoring baseline was missing | **PARTIAL** — privacy-safe bounded inference events, latency/failure health, and non-blocking Decision Engine policy implemented; durable telemetry, drift, outcomes, and alert delivery remain |
| D5 | P2 | Credit | No credit **score engine (300–850)**, business rules, confidence, or calibration despite config existing | Open |
| D6 | P2 | Credit | Only LogReg + RandomForest trainers; **XGBoost/LightGBM/CatBoost/Optuna** not implemented (declared deps uninstalled) | Open |
| D7 | P2 | Fraud | `fraud_intelligence` has only scoring; behaviour/identity/rules/anomaly-adapter/confidence/explanation/pipeline **not built** | Open |
| D8 | P2 | Tooling | Environment is Python 3.11 while project requires 3.12; `pytest-cov`, `mypy`, `build`, and Poetry are not installed | Open — rebuild a reproducible Python 3.12 environment |
| D9 | P2 | Platform | The `creditiq_ai` library is **not integrated** with the running `backend/`+`ml-engine/` apps (two parallel ML codebases) | Pre-existing, known |
| D10 | P3 | Style | `ruff format` has not been applied — 96 files currently require formatting | Open — mechanical formatting pass before public release |
| D11 | P3 | Structure | Empty scaffold packages (`registry/`, `monitoring/`, `credit_intelligence/registry/`, `evaluation/`, many `fraud_intelligence/*`, `model_operations/*`) exist as placeholders | Intentional (await their phases) |
| D12 | P3 | Docs | Some docs/memory refer to "Sprint 5 = Enterprise Inference & Decision Engine" which is not in code | Open — doc/reality drift |
| D13 | P3 | Naming | Two fraud packages (`fraud/` detection framework, `fraud_intelligence/` orchestration) — intentional split but overlapping names | Documented |

## Not debt (verified healthy)
- **One** configuration loader (`config/loader.py`), **one** logging system (Loguru), **one**
  exception hierarchy, **one** canonical preprocessing path (Sprint 3.5 removed the duplicate).
- No duplicate model registry inside the library (`model_operations` is authoritative; the
  trainer/detector/feature/cleaner/explainer registries are distinct *component* registries, not
  competing model registries).
- No circular imports.
