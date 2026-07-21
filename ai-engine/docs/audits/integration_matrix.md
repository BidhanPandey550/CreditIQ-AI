# Sprint 8.5 — Integration Matrix

Statuses: **PASS** (verified by test), **PARTIAL** (works but incomplete/indirect), **NOT BUILT**
(subsystem not implemented), **N/A**.

| Integration link | Status | Evidence / reason |
|---|---|---|
| Data engineering → feature engineering | **PASS** | `test_platform_integration` clean→impute→features |
| Feature engineering → credit training | **PASS** | engineered features train LogisticRegression, valid CV |
| Feature engineering → fraud analysis | **PARTIAL** | fraud detectors consume numeric features, but the dedicated `fraud/features` engine is NOT built; detection runs on caller-scaled features |
| Training → registry | **PARTIAL** | trainers produce checksum-bearing artifacts and durable registration exists; automatic post-training registration remains |
| Registry → lifecycle | **PASS** | persistent registry enforces the lifecycle state machine and records audit events |
| Registry → inference | **PASS** | production-version selection returns checksum-linked artifacts for verified loading |
| Credit inference → decision | **PASS** | `DecisionEngine` composes credit PD → score → decision (D2 fixed; `test_decision_engine`) |
| Fraud inference → decision | **PASS** | `DecisionEngine` composes fraud score into the decision, fraud can only make it more conservative |
| Decision → explainability | **PARTIAL** | explainability integrates directly with a trained model, not yet wired through the decision engine |
| Decision → monitoring | **PASS** | injected privacy-safe monitoring sink records decisions; backend failure degrades observability without blocking a safe decision |
| Outcomes → performance monitoring | **NOT BUILT** | not implemented |
| Drift → model health | **NOT BUILT** | not implemented |
| Health → alerts | **NOT BUILT** | not implemented |
| Promotion → audit | **NOT BUILT** | promotion + audit storage not implemented |
| Rollback → audit | **NOT BUILT** | rollback + audit storage not implemented |

## Summary
- **Verified-integrated core:** Data → Features → Credit training → PD → Explanation, and Fraud
  detection ensemble → Fraud score (0–1000). These span Sprints 1–4, 6, 7 and genuinely work
  together (deterministic, tested).
- **Remaining integration surface:** automatic training registration, decision-to-explanation,
  outcome/performance monitoring, drift, alert delivery, and promotion/rollback audit export.
