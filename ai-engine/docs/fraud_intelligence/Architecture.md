# Fraud Intelligence Engine (Sprint 7)

An **independent** fraud assessment engine that runs alongside the Credit Intelligence Engine; its
output is later combined into a unified lending decision (credit + fraud). Financial-fraud focused
(lending fraud, applicant anomalies, suspicious financial behaviour) — not cybersecurity.

## Package layout (`creditiq_ai/fraud_intelligence/`)

```
algorithms/           # (reserved) fraud-specific ML models
anomaly_detection/    # REUSES creditiq_ai.fraud (Isolation Forest / LOF / One-Class SVM / …) + adds Z-Score
behaviour_analysis/   # behavioural indicators → BehaviourRiskProfile
identity_validation/  # extensible identity-consistency framework (design-only externals)
rule_engine/          # configurable fraud rules (priority / severity / explanation)
scoring/              # Fraud Scoring Engine (0–1000)                         ← Module 1 ✅
confidence/           # fraud confidence estimation
explainability/       # fraud reasoning + human-readable explanation
reporting/            # JSON / Markdown fraud reports
pipelines/            # FraudDetectionPipeline (validate→behaviour→…→report)
services/             # orchestration + Decision Engine integration
validators/           # input validation
models/               # Pydantic contracts (FraudSignals, FraudScore, …)      ← Module 1 ✅
config/               # (config lives in the unified EngineConfig.fraud_intelligence)
```

> **No duplication.** Anomaly detection **reuses** the Sprint-5 `creditiq_ai.fraud` detection
> framework (registry/factory/ensemble). The only new detector is **Z-Score**, added to the
> existing fraud registry via its open/closed `@register` hook — not a reimplementation.

## Module 1 — Fraud Scoring Engine (0–1000)

`FraudScoringEngine.score(FraudSignals) -> FraudScore`. Signals are normalized [0,1] values
produced by the pipeline stages and **injected** (Dependency Inversion), so scoring is testable in
isolation:

```
FraudSignals(anomaly_probability, rule_penalty, behaviour_risk)
   │  weighted sum (config weights) / Σweights  →  fraud_probability ∈ [0,1]
   ▼
fraud_score = score_min + probability · (score_max − score_min)     # 0–1000
fraud_risk_level = band(fraud_score)                                # Very Low … Critical
recommended_action = actions[level]                                 # approve / review / reject
```

### Bands (config)

| Score | Level |
|---|---|
| 0–200 | Very Low |
| 201–400 | Low |
| 401–600 | Moderate |
| 601–800 | High |
| 801–1000 | Critical |

### Everything is configuration
Weights, the 0–1000 range, band thresholds, and per-level actions all live under
`fraud_intelligence.scoring` in [`config/base.yaml`](../../config/base.yaml). **No magic numbers,
no hardcoded thresholds.** Change the weighting or bands without touching code.

## Design decisions

- **Signal decoupling** — `FraudSignals` is the seam between "how a signal is computed" (later
  modules) and "how signals become a score" (this module). Each side evolves independently.
- **Config-driven bands & actions** — resolving a score to a level/action is pure config lookup.
- **Consistent with the platform** — reuses `BaseComponent` (logging), the unified config surface
  (Sprint 3.5 rule), and the established Strategy/Factory/DI/Registry conventions.

## Planned decision-engine integration (later module)
The pipeline will assemble a `FraudAssessment` and the Decision Engine service will merge it with
the credit result **without breaking backward compatibility**:

```json
{ "credit_score": 782, "fraud_score": 148, "probability_of_default": 0.07,
  "fraud_probability": 0.03, "credit_risk": "Low", "fraud_risk": "Very Low",
  "recommendation": "Approve", "confidence": 0.96 }
```

## What's next (Sprint-7 modules)
Anomaly-detection adapter (+ Z-Score detector) · behaviour analysis · identity validation · rule
engine · confidence · fraud explainability · reporting · pipeline · decision-engine integration.
