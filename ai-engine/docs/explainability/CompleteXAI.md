# Complete Explainability Flow

CreditIQ AI now supports local additive explanations with SHAP fallback, model-agnostic global
permutation importance, repeated-perturbation stability, constrained counterfactual guidance,
structured decision summaries, and atomic JSON/Markdown audit reports.

Counterfactual changes are restricted to explicitly configured actionable features, direction,
step, and realistic bounds. The service reports only changes that improve predicted default risk;
it does not suggest altering protected or immutable identity attributes. Global importance measures
prediction sensitivity and must not be interpreted as causality.

Audit reports retain model version, feature version, method, timestamp, completeness status, and
validation issues. They are designed for future API, compliance, customer, and auditor-specific
presentation layers without embedding UI concerns in the AI engine.
