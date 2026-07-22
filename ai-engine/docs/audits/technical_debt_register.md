# Technical Debt Register (as of Sprint 8.5 audit)

| ID | Sev | Area | Description | Disposition |
|---|---|---|---|---|
| D1 | ~~P1~~ | Model ops / security | Model artifacts (`joblib.load`) deserialized with no integrity check | **RESOLVED AND VERIFIED** — every trainer/detector public loader delegates to `ArtifactStore`; missing or mismatched SHA-256 fails closed before deserialization |
| D2 | ~~P1~~ | Platform | No unified credit+fraud Decision Engine | **RESOLVED** — `creditiq_ai.decision.DecisionEngine` (config-driven policy, integrity blocks, fraud failure degrades); 10 tests (scenarios A–G) |
| D3 | ~~P2~~ | Model ops | Registry persistence/production selection was missing | **RESOLVED (local/single-node)** — atomic JSON registry, lifecycle enforcement, checksum-required artifacts, unique production selection, rollback, and audit history |
| D4 | ~~P2~~ | Monitoring | Operational and model monitoring was incomplete | **RESOLVED (local adapter)** — inference telemetry, PSI drift, delayed-label performance, aggregate health, deduplicated alerts, and failure policy are tested |
| D5 | ~~P2~~ | Credit | Credit score, rules, confidence, and calibration were missing | **RESOLVED** |
| D6 | ~~P2~~ | Credit | Model zoo and Optuna were missing | **RESOLVED** — five trainers, optional dependency guards, configurable Optuna optimization |
| D7 | ~~P2~~ | Fraud | Fraud orchestration was incomplete | **RESOLVED** — behaviour, identity hooks, rules, anomaly ensemble, confidence, explanation, reporting, pipeline |
| D8 | ~~P2~~ | Tooling | Reproducible Python 3.12 quality environment was absent | **RESOLVED** — Poetry Python 3.12; lint, format, mypy, tests/coverage, smoke and build gates |
| D9 | ~~P2~~ | Platform | The `creditiq_ai` library was not integrated with the running applications | **RESOLVED** — `ml-engine` is a thin serving adapter over the canonical library; the backend calls it through a governed client and fails closed if unavailable |
| D10 | ~~P3~~ | Style | Formatting was not enforced | **RESOLVED** — repository-wide `ruff format --check` is a CI gate |
| D11 | P3 | Structure | Some frozen scaffold packages remain empty | Open — compatibility namespaces; remove only in a future breaking release |
| D12 | ~~P3~~ | Docs | Enterprise inference claims did not match code | **RESOLVED** — API-neutral inference application contract and integration tests added |
| D14 | P2 | Deployment | Local JSON registry and experiment tracking remain single-node adapters | **PARTIAL** — production inference telemetry now uses a bounded, TTL-controlled Redis adapter shared across replicas; transactional registry and object-storage adapters remain open |
| D15 | P2 | Governance | Nepal deployment still requires institution-specific legal, privacy, retention, fairness, and NRB compliance sign-off | Open — organizational/legal control, not solvable by library code alone |
| D13 | P3 | Naming | Two fraud packages (`fraud/` detection framework, `fraud_intelligence/` orchestration) — intentional split but overlapping names | Documented |

## Not debt (verified healthy)
- **One** configuration loader (`config/loader.py`), **one** logging system (Loguru), **one**
  exception hierarchy, **one** canonical preprocessing path (Sprint 3.5 removed the duplicate).
- No duplicate model registry inside the library (`model_operations` is authoritative; the
  trainer/detector/feature/cleaner/explainer registries are distinct *component* registries, not
  competing model registries).
- No circular imports.
