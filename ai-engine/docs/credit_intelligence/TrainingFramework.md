# Credit Intelligence Engine — Training Framework (Sprint 4, Module 1)

The extensible backbone every credit-risk algorithm plugs into. Built on four patterns:
**Template Method** (`BaseTrainer` fixes the workflow), **Registry** (`TrainingRegistry` maps
names → trainer classes), **Factory** (`TrainingFactory` builds trainers from config), and
**Dependency Injection** (`TrainingContext` carries the dataset + config into a run).

## Components

| Class | Responsibility |
|---|---|
| `CreditDataset` | Immutable features+target holder; content-hash `version` for provenance; stratified `split()` |
| `TrainingConfig` | One immutable run spec (algorithm, params, cv_folds, primary_metric, seed); validates the metric |
| `TrainingContext` | DI container = `dataset` + `config` for a single run |
| `BaseTrainer` | Template Method: `validate → cross-validate → fit → package → log`; `predict`/`predict_proba`/`save`/`load` |
| `TrainingResult` | Serialisable outcome (CV score, timing, provenance, warnings) — no estimator inside |
| `TrainingRegistry` | Name → trainer-class registry (`@register`) |
| `TrainingFactory` | Instantiates a trainer from a `TrainingConfig` |
| `TrainingPipeline` | Trains many algorithms, builds the leaderboard, selects the best |

## Training flow

```
CreditDataset ─┐
TrainingConfig ─┴─► TrainingContext ─► TrainingFactory.create() ─► BaseTrainer.train()
                                                                     │ validate labels
                                                                     │ StratifiedKFold CV (primary_metric)
                                                                     │ fit on full data
                                                                     │ capture warnings + timing
                                                                     ▼
                                                                TrainingResult
   TrainingPipeline.run([configs]) ─► [TrainingResult...] ─► leaderboard() ─► best()
```

## Design decisions

- **Template Method** keeps CV, metric handling, timing, warning-capture, and logging **identical
  across every model** — a new algorithm supplies only `_build_estimator(params)`. No duplicated
  training logic.
- **Config-driven, zero magic numbers.** `primary_metric` must be a valid scikit-learn scorer
  (`ALLOWED_METRICS`); `cv_folds`/`params`/`seed` all come from `TrainingConfig`, itself built from
  the unified `EngineConfig.models` (Sprint 3.5 single-config rule) via `training_configs_from_models`.
- **Leakage-safe & reproducible.** CV uses a seeded `StratifiedKFold`; the fitted estimator is
  retained on the trainer and persisted via `joblib`; `TrainingResult` records the `dataset_version`
  hash so a model is always traceable to the exact data it saw.
- **Forward-compatible pipeline.** Algorithms without a registered trainer are **skipped with a
  warning**, so the same 5-model config zoo runs today (Logistic Regression, Random Forest) and
  automatically includes XGBoost/LightGBM/CatBoost the moment their trainers are added — no config
  or pipeline change.
- **Ranking is automatic.** All allowed metrics follow scikit-learn's "higher-is-better" scorer
  convention, so `leaderboard()` sorts descending and `best()` returns the top trainer — no manual
  comparison.

## Training guide

```python
from creditiq_ai.config import load_config
from creditiq_ai.credit_intelligence import (
    CreditDataset, TrainingPipeline, training_configs_from_models,
)

dataset = CreditDataset(X=features_df, y=target_series, name="loans_2026Q3")
configs = training_configs_from_models(load_config().models)   # from config/base.yaml
pipeline = TrainingPipeline(configs)
pipeline.run(dataset)

for r in pipeline.leaderboard():
    print(r.algorithm, r.primary_score)
best_result, best_trainer = pipeline.best()
best_trainer.save("artifacts/best_model.joblib")
```

## Adding a new algorithm (Open/Closed)

1. Subclass `BaseTrainer`, set `algorithm`, implement `_build_estimator(params)`.
2. Decorate with `@register("my_algorithm")`.
3. Import it in `credit_intelligence/algorithms/__init__.py`.
4. Add a `{ type: my_algorithm, ... }` entry under `models.zoo` in `config/base.yaml`.

No change to `BaseTrainer`, the factory, or the pipeline.

## What's next (subsequent Sprint-4 modules)
XGBoost/LightGBM/CatBoost trainers · Optuna hyperparameter optimisation · full evaluation & metrics ·
probability calibration · credit-score engine · business-rule engine · confidence engine · model
registry · reports · visualization · validators · services.
