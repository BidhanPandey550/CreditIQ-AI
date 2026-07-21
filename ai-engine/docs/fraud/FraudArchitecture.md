# Fraud Intelligence Engine — Detection Framework (Sprint 5, Module 1)

The extensible anomaly-detection backbone. Built on the same four patterns as the training
framework: **Template Method** (`BaseFraudDetector`), **Registry** (`FraudDetectionRegistry`),
**Factory** (`FraudDetectionFactory`), **Dependency Injection** (config from `EngineConfig.fraud`).

## Components

| Class | Responsibility |
|---|---|
| `BaseFraudDetector` | Template Method: fit reference → calibrate a **[0,1] anomaly scale** → `score`/`predict`/`save`/`load` |
| `FraudDetectionConfig` | Alias of the unified `EngineConfig.fraud` (single config surface — no duplicate config) |
| `FraudDetectionRegistry` | Name → detector-class registry (`@register`) |
| `FraudDetectionFactory` | Builds a detector from name + params |
| `FraudDetectionPipeline` | Fits the ensemble; aggregates per-row into `FraudDetectionResult` |
| `FraudDetectionResult` | The **stable integration contract** consumed by the Credit Intelligence Engine + APIs |

## Detectors (unsupervised)

| Detector (config `type`) | Method | Notes |
|---|---|---|
| `isolation_forest` | random-partition isolation | fast, robust default |
| `local_outlier_factor` | local density (novelty=True) | catches local anomalies |
| `one_class_svm` | kernel boundary | scale-sensitive |
| `elliptic_envelope` | Gaussian covariance / Mahalanobis | assumes elliptical data |
| `dbscan` | density novelty (distance-to-core > `eps`) | custom, since DBSCAN has no native predict |

All expose the **same normalized interface**: `score()` ∈ [0,1] (higher = more anomalous) and
`predict()` → bool. Each detector flips scikit-learn's "higher = more normal" signal and calibrates
its [0,1] scale from the reference distribution at `fit()` — so heterogeneous detectors are directly
comparable and ensemble-able.

## Detection flow

```
reference X ─► FraudDetectionPipeline.fit()   (each detector fits + calibrates its 0–1 scale)
new X       ─► FraudDetectionPipeline.analyze()
                 per detector: score() ∈ [0,1], predict() → bool
                 per row: detector_breakdown={name: score}, votes=Σ flags,
                          anomaly_detected = votes ≥ vote_threshold (config),
                          fraud_probability = mean(scores)   [provisional]
              ─► list[FraudDetectionResult]
```

## Integration contract (`FraudDetectionResult`)

Populated **progressively** across Sprint-5 modules; later-module fields default to `None`/`[]` so
the schema stays backward-compatible:

| Field | Filled by |
|---|---|
| `fraud_probability`, `anomaly_detected`, `detector_breakdown`, `detector_agreement` | **Module 1 (this)** |
| `fraud_score`, `fraud_level`, `recommended_action` | scoring engine |
| `confidence_score`, `confidence_level` | confidence engine |
| `risk_flags` | rule engine |
| `explanations` | explanation engine |

## Design decisions

- **Template Method** unifies fit/calibrate/score/persist so a new detector supplies only
  `_fit_model` / `_raw_scores` / `_raw_predict`. No duplicated normalization or persistence logic.
- **No hardcoded thresholds.** Detector hyperparameters, `contamination`, `random_state`, and the
  ensemble `vote_threshold` all come from `config/base.yaml` (`fraud:` section). The [0,1] scale is
  learned from data, not fixed.
- **Comparable, ensemble-ready scores.** Per-detector min–max calibration on the reference makes
  scores combinable despite different underlying scales.
- **Forward-compatible.** Unregistered detectors (e.g. a future `graph_based`) are skipped with a
  warning, so the config can list detectors before their code exists.
- **Independent from the credit feature engine** (per requirement): fraud features (next module)
  live under `fraud/features/`, separate from `feature_engineering/`.

## Adding a new detector (Open/Closed)

1. Subclass `BaseFraudDetector`, set `detector_name`, implement `_fit_model` / `_raw_scores`
   (higher = more anomalous) / `_raw_predict` (True = anomaly).
2. `@register("my_detector")`.
3. Import it in `fraud/algorithms/__init__.py`.
4. Add `{ type: my_detector, enabled: true, params: {...} }` under `fraud.detectors` in `base.yaml`.

No change to the base class, factory, or pipeline.

## What's next (Sprint-5 modules)
Fraud feature engineering (`fraud/features/`) · rule-based engine (`fraud/rules/`) · fraud scoring
engine (probability→score/level/action) · confidence engine · explanation engine · evaluation ·
visualization · registry integration · services.

> Note: Module 1 fills only the detector-level contract fields; the provisional
> `fraud_probability` (ensemble mean) and `vote_threshold` flag will be superseded by the calibrated
> scoring engine. On raw/unscaled features the ensemble should be preceded by the preprocessing
> scaler (as in the tests) for the distance-based detectors to behave.
