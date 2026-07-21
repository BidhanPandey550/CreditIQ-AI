# CreditIQ AI — ML Engine Architecture

A standalone, production-grade credit-intelligence engine. It is a **library** (importable
package `creditiq_ai`), deliberately free of any web framework, API router, UI, or auth — those
live in the serving/application tier and *depend on* this engine, never the reverse.

> This document is the framework contract. It is written **before** any model code so that all
> twelve functional modules plug into a stable set of abstractions.

---

## 1. Folder structure

```
ai-engine/
├── pyproject.toml                 # Poetry project + tooling config
├── README.md
├── config/                        # externalised configuration (YAML) — no hardcoded values
│   ├── base.yaml                  # all sections: runtime/data/cleaning/imputation/features/models/scoring/fraud
│   └── environments/              # per-environment overrides
│       ├── development.yaml
│       ├── testing.yaml
│       └── production.yaml
├── docs/
│   └── ARCHITECTURE.md            # this document
├── artifacts/                     # local model/registry store (object storage in prod)
├── creditiq_ai/                   # THE PACKAGE
│   ├── core/                      # framework backbone (no ML libs beyond typing)
│   │   ├── base.py                #   abstract base classes (ports/interfaces)
│   │   ├── schemas.py             #   Pydantic domain models (I/O contracts)
│   │   ├── enums.py               #   controlled vocabularies
│   │   ├── exceptions.py          #   custom exception hierarchy
│   │   ├── logging.py             #   structured logging setup
│   │   └── types.py               #   shared type aliases
│   ├── config/                    # config loading + validation (Pydantic Settings)
│   │   ├── models.py              #   typed config schema
│   │   └── loader.py              #   YAML + env merge → EngineConfig
│   ├── data/            (M1)      # data loaders: CSV, Parquet, future DB connectors
│   ├── validation/     (M1)      # schema / missing / duplicate / dtype validation
│   ├── preprocessing/  (M2)      # imputation, outliers, encoding, scaling, dates, currency
│   ├── feature_engineering/ (M3) # modular feature generators + registry
│   ├── models/         (M4)      # estimator wrappers (LogReg/RF/XGB/LGBM/CatBoost) + tuning
│   ├── risk/           (M4/M6)   # credit-risk service + default-probability service
│   ├── scoring/        (M5)      # alternative credit score (300–850), pluggable strategy
│   ├── fraud/          (M7)      # anomaly detectors (IForest/LOF/OneClassSVM) + ensemble
│   ├── explainability/ (M8)      # SHAP explainers → machine-readable explanations
│   ├── evaluation/     (M9)      # metrics, calibration, comparison reports
│   ├── inference/      (M10)     # end-to-end InferenceEngine orchestrator
│   ├── monitoring/     (M11)     # metrics, latency, drift hooks, data-quality checks
│   ├── registry/       (M12)     # model registry (versions, metadata, load/save)
│   ├── training/                 # training orchestration (fit → tune → select → register)
│   ├── pipelines/                # composed end-to-end pipelines (training / inference)
│   └── utils/                    # io, timing, hashing, validation helpers
└── tests/
    ├── unit/                     # per-module unit tests
    ├── integration/              # cross-module pipeline tests
    └── fixtures/                 # synthetic datasets + factories
```

**Single-responsibility rule:** each package owns exactly one concern and exposes a small public
surface via its `__init__.py`. Cross-package calls go through the `core` abstractions, not through
concrete classes.

---

## 2. Module architecture & dependency direction

Dependencies point **inward** toward `core`. `core` depends on nothing in the package.

```
                         ┌───────────────────────────────────────────────┐
                         │                    core/                       │
                         │  base ABCs · schemas · enums · exceptions ·    │
                         │  logging · types    (depends on NOTHING)       │
                         └───────────────▲───────────────────────────────┘
                                         │ implemented / used by
     ┌───────────────┬──────────────┬────┴───────┬───────────────┬────────────────┐
     │               │              │            │               │                │
  data/          preprocessing/  feature_eng/  models/        fraud/        explainability/
  validation/                                   risk/ scoring/
     │               │              │            │               │                │
     └───────────────┴──────────────┴────────────┴───────────────┴────────────────┘
                                         │  composed by
                         ┌───────────────┴───────────────┐
                         │   training/   ·   pipelines/    │   ← orchestration
                         │   inference/                    │
                         └───────────────┬───────────────┘
                                         │ observed / persisted by
                         ┌───────────────┴───────────────┐
                         │  monitoring/    ·   registry/   │   ← infrastructure adapters
                         └───────────────────────────────┘
                                         │
                                     config/  (cross-cutting; injected everywhere)
                                     utils/   (cross-cutting; pure helpers)
```

**Clean-architecture layers**

| Layer | Packages | Rule |
|---|---|---|
| Domain / contracts | `core` | Pure Python + Pydantic; no ML libs |
| ML capability | `data`, `validation`, `preprocessing`, `feature_engineering`, `models`, `risk`, `scoring`, `fraud`, `explainability`, `evaluation` | Implement `core` ABCs |
| Orchestration | `training`, `inference`, `pipelines` | Compose capabilities; own no business rules of their own |
| Infrastructure | `registry`, `monitoring` | Adapters for persistence & observability behind `core` ports |
| Cross-cutting | `config`, `utils` | Injected; never import upward |

---

## 3. Class diagram (text form)

Abstract base classes (in `core/base.py`) and their concrete implementations:

```
BaseComponent (ABC)                         # name, config, logger; common lifecycle
│
├── BaseDataLoader (ABC)
│     + load(source: str|Path) -> DataFrame
│     ├── CsvLoader
│     ├── ParquetLoader
│     └── DatabaseLoader           (future; interface only)
│
├── BaseValidator (ABC)
│     + validate(df: DataFrame) -> ValidationReport
│     ├── SchemaValidator
│     ├── MissingValueValidator
│     ├── DuplicateValidator
│     └── DTypeValidator
│
├── BaseTransformer (ABC)          # sklearn-compatible: fit / transform / fit_transform
│     + fit(X, y=None) -> self
│     + transform(X) -> X'
│     ├── MissingValueImputer
│     ├── OutlierHandler
│     ├── CategoricalEncoder
│     ├── NumericScaler
│     ├── DateFeaturizer
│     └── CurrencyNormalizer
│
├── BaseFeatureGenerator (ABC)     # ONE feature (or feature group); registered, not wired-in
│     + name: str ; + dependencies: list[str]
│     + generate(df: DataFrame) -> DataFrame
│     ├── IncomeStabilityFeature ├── SavingsRatioFeature ├── DebtToIncomeFeature
│     ├── ExpenseRatioFeature     ├── CashFlowStabilityFeature ├── AvgMonthlyIncomeFeature
│     ├── PaymentConsistencyFeature ├── TransactionFrequencyFeature
│     ├── IncomeGrowthFeature     └── FinancialBehaviourIndexFeature
│           ▲ registered in FeatureRegistry → FeatureEngineeringPipeline
│
├── BaseModel (ABC)               # uniform wrapper over any estimator
│     + fit(X, y) -> self  + predict(X)  + predict_proba(X)
│     + feature_names  + get_params()  + save(path)  + load(path)
│     ├── LogisticRegressionModel ├── RandomForestModel ├── XGBoostModel
│     ├── LightGBMModel           └── CatBoostModel
│
├── BaseAnomalyDetector (ABC)
│     + fit(X) -> self  + score(X) -> float[]  + predict(X) -> {-1,1}[]
│     ├── IsolationForestDetector ├── LocalOutlierFactorDetector └── OneClassSVMDetector
│           ▲ combined by FraudEnsemble
│
├── BaseExplainer (ABC)
│     + explain_local(model, x) -> Explanation
│     + explain_global(model, X) -> GlobalImportance
│     └── ShapExplainer
│
├── BaseScorer (ABC)              # Strategy pattern for the 300–850 score
│     + score(probability|features) -> CreditScoreResult
│     ├── ProbabilityToScoreScorer   (log-odds → points; config-driven)
│     └── WeightedFeatureScorer      (scorecard; config-driven weights)
│
├── BaseEvaluator (ABC)
│     + evaluate(y_true, y_pred, y_proba) -> EvaluationReport
│     └── ClassificationEvaluator
│
└── BaseRegistry (ABC)
      + save(model, metadata) -> version  + load(name, version) -> BaseModel
      + list_versions(name) -> list[ModelMetadata]
      └── LocalFileRegistry   (joblib + JSON;  MLflow adapter is a drop-in)

Services (application layer, compose the above):
  CreditRiskService  → uses models/, training/, evaluation/, registry/
  DefaultProbabilityService → uses a calibrated BaseModel
  CreditScoringService → uses BaseScorer
  FraudDetectionService → uses FraudEnsemble
  InferenceEngine    → orchestrates preprocessing→features→risk→score→default→fraud→explain
  ModelTrainer       → orchestrates load→validate→preprocess→features→tune→select→register
  MonitoringService  → records PredictionEvent, latency, drift hooks
```

Key Pydantic contracts (in `core/schemas.py`): `ApplicantRecord`, `FinancialProfile`,
`FeatureVector`, `RiskAssessment`, `CreditScoreResult`, `DefaultProbabilityResult`,
`FraudResult`, `FeatureContribution`, `Explanation`, `PredictionResult`, `ModelMetadata`,
`EvaluationReport`, `ValidationReport`, `PredictionEvent`.

---

## 4. Data flow

**Training flow**

```
raw file/DB
  → data.BaseDataLoader.load()                → DataFrame
  → validation.*Validator.validate()          → ValidationReport (fail-fast on errors)
  → preprocessing.PreprocessingPipeline.fit_transform()   → clean matrix (+ fitted, serialisable)
  → feature_engineering.FeatureEngineeringPipeline.transform()  → FeatureVector matrix
  → training.ModelTrainer:
        for model in models.yaml:
            optuna tune → cross_validate → fit
        evaluation.ClassificationEvaluator.evaluate() on each
        select best by configured primary metric
  → registry.BaseRegistry.save(best_model, ModelMetadata)   → version id
```

**Inference flow**

```
ApplicantRecord (Pydantic)
  → InferenceEngine.predict():
      preprocessing.transform()      (fitted artifacts loaded from registry)
      feature_engineering.transform()
      risk.CreditRiskService         → RiskAssessment
      scoring.CreditScoringService   → CreditScoreResult (300–850)
      risk.DefaultProbabilityService → DefaultProbabilityResult (prob, category, confidence)
      fraud.FraudDetectionService    → FraudResult
      explainability.ShapExplainer   → Explanation (top/positive/negative contributors)
      monitoring.MonitoringService.record(PredictionEvent)
  → PredictionResult (single structured object)
```

Every stage consumes and emits **typed contracts** from `core/schemas.py`, so stages are
independently testable and replaceable.

---

## 5. Configuration system (unified & environment-aware)

- All tunables live in `config/base.yaml` + `config/environments/{development,testing,production}.yaml`.
  **No magic numbers in code, and no per-component YAML files.**
- `creditiq_ai/config/loader.py` is the **single** loader. Flow: detect environment (`CREDITIQ_ENV`)
  → `base.yaml` ← `environments/<env>.yaml` ← `CREDITIQ_*` env vars → validate into a typed,
  immutable `EngineConfig` (Pydantic) that records the effective `environment`.
- Every component (cleaning, imputation, features, …) receives its **slice** of `EngineConfig` by
  dependency injection (e.g. `DataCleaningEngine(cfg.cleaning)`). **No component reads YAML.**
- Config is immutable and hashable (`config_hash`), so a model version can record the exact config
  it was trained under (reproducibility).

---

## 6. Extension points (Open/Closed)

| To add… | Do this | Without touching |
|---|---|---|
| A new data source | Implement `BaseDataLoader`; register in loader factory | any consumer |
| A new feature | Implement `BaseFeatureGenerator`; add to `features.yaml` | existing features / pipeline |
| A new model | Implement `BaseModel`; add to `models.yaml` zoo | trainer / selection logic |
| A new anomaly detector | Implement `BaseAnomalyDetector`; add to `fraud.yaml` | ensemble / service |
| A new scoring method | Implement `BaseScorer`; select in `scoring.yaml` | inference engine |
| A new explainer | Implement `BaseExplainer` | inference engine |
| A new registry backend (MLflow/S3) | Implement `BaseRegistry` | training / inference |

---

## 7. Cross-cutting standards

Type hints everywhere · Google-style docstrings · Pydantic for all I/O contracts ·
`logging` (never `print`) via `core.logging` · custom exceptions from `core.exceptions` ·
deterministic seeds from config · `joblib` for artifact serialisation · pytest for every module.

---

## 8. Implementation order (modules)

1. **core + config** (this foundation) → 2. Data Loader (M1) → 3. Validation (M1) →
4. Preprocessing (M2) → 5. Feature Engineering (M3) → 6. Models + tuning (M4) →
7. Evaluation (M9) → 8. Training orchestration → 9. Default Probability (M6) →
10. Alternative Credit Score (M5) → 11. Fraud (M7) → 12. Explainability (M8) →
13. Registry (M12) → 14. Monitoring (M11) → 15. Inference Engine (M10) → 16. Pipelines.

Evaluation and training come early because models are meaningless without measurement and a
repeatable fit/select loop.
```
