# Explainable AI Engine — Local Explanations (Sprint 6, Module 1)

Explains individual lending decisions for loan officers, risk analysts, compliance, customers, and
auditors. Built on **Strategy** (interchangeable explainers), **Factory + Registry** (best-supported
explainer selection), and **Dependency Injection** (`ExplanationContext`). Reuses the frozen Sprint-1
contracts (`core.schemas.Explanation` / `FeatureContribution`) — no duplication.

## Components

| Component | Responsibility |
|---|---|
| `ExplanationContext` | DI container: `predict_proba`, `feature_names`, `background`, raw model, `model_kind` |
| `BaseLocalExplainer` | Strategy interface: `supports(ctx)` + `explain(ctx, row) → RawContributions` |
| `ShapExplainer` | Preferred (priority 100); TreeExplainer/LinearExplainer; **declines when SHAP absent** |
| `MarginalContributionExplainer` | Model-agnostic fallback (priority 10); ablate-to-baseline; always available |
| `ExplainerFactory` | Selects the highest-priority explainer whose `supports(ctx)` is True |
| `NarrativeRenderer` | Config-driven plain-language text (**no hardcoded strings**) |
| `CompletenessValidator` | Every feature attributed · prediction ∈ [0,1] · direction consistent |
| `LocalExplanationService` | Orchestrates select → explain → rank → render → validate → assemble |
| `LocalExplanation` | Audit-ready result: `Explanation` + method + confidence + versions + completeness |

## Explanation flow

```
trainer + background ─► build_context() ─► ExplanationContext
row ─► LocalExplanationService.explain():
        ExplainerFactory.select(ctx)         # SHAP if installed & compatible, else Marginal
        explainer.explain(ctx, row)          # RawContributions (signed: + increases default risk)
          └─ on runtime error ─► graceful fallback to MarginalContributionExplainer
        rank by |contribution| → top positive / negative (top_k from config)
        NarrativeRenderer.render()           # plain language from config templates
        CompletenessValidator.validate()     # completeness + consistency
     ─► LocalExplanation  (embeds core Explanation + method + confidence + metadata)
```

## SHAP integration & graceful fallback

`ShapExplainer.supports(ctx)` is True only when (a) SHAP is importable and (b) the model is a
tree/linear family with a raw estimator available. Otherwise the factory automatically picks the
**model-agnostic marginal explainer**, so an explanation is *always* produced. If SHAP is selected
but errors at runtime, the service falls back too. (In this environment SHAP is not installed, so
the marginal explainer runs; installing `shap` activates the SHAP path with no code change.)

## Design decisions

- **Reuse over duplication** — the contribution-level result IS the frozen `core.schemas.Explanation`;
  `LocalExplanation` only *wraps* it with XAI metadata, so Sprint 1 is untouched.
- **No hardcoded explanation text** — every sentence and human label comes from
  `explainability.templates` / `feature_labels` in `config/base.yaml`.
- **No hardcoded thresholds** — `top_k` and `consistency_tolerance` are config.
- **Model-agnostic guarantee** — the marginal explainer needs only `predict_proba` + a background
  sample, so any model (any sprint, any library) is explainable.
- **Auditability** — the result records `method`, `model_version`, `feature_version`, completeness
  flag, and issues, ready for the audit-report module.

## Adding a new explainer (Open/Closed)

1. Subclass `BaseLocalExplainer`; implement `supports(ctx)` and `explain(ctx, row) → RawContributions`.
2. `@register("name", priority=N)` (higher = preferred).
3. Import it in `explainability/__init__.py`.

No change to the factory, service, renderer, or validators.

## What's next (Sprint-6 modules)
Global explanations & feature importance · counterfactual guidance · decision summaries · audit
reports (JSON/Markdown) · visualization · services/pipelines.
