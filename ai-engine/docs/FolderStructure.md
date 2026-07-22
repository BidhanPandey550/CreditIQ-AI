# CreditIQ AI Engine — Folder Structure

This document began as the Sprint 1 foundation map. It now describes the implemented engine after
the credit, fraud, explainability, decision, inference, and model-operations sprints. Every package
retains a single responsibility and extension occurs through registries and injected strategies.

```
ai-engine/
├── pyproject.toml              # Poetry project + tooling (black/ruff/mypy/pytest)
├── config/                     # environment YAML files: development / testing / production
├── docs/                       # README, Architecture, FolderStructure, DeveloperGuide
├── tests/                      # pytest suite (unit / integration / fixtures)
└── creditiq_ai/                # THE PACKAGE
    │
    ├── constants/              # immutable, non-configurable constants (enums, tokens, names)
    ├── exceptions/             # custom exception hierarchy with structured messages
    ├── logging/                # Loguru-based enterprise logging (console/file/rotating/domain)
    ├── config/                 # settings.py, loader, env detection, typed Pydantic config
    ├── core/                   # abstract base classes (ports) every module inherits from
    │
    ├── data/                   # data access
    │   ├── loaders/            #   BaseLoader, CSV/Parquet/Excel loaders, LoaderFactory
    │   ├── validators/         #   schema / missing / duplicate / dtype / outlier validators
    │   └── schemas/            #   dataset schema definitions (Pydantic / column specs)
    │
    ├── preprocessing/          # cleaning, imputation, scaling, encoding (foundation now)
    ├── feature_engineering/    # modular feature generators + registry
    ├── credit_intelligence/    # trainers, calibration, evaluation, rules, confidence, reports
    ├── decision/               # unified credit + fraud policy and output contract
    ├── inference/              # API-neutral governed inference application service
    ├── explainability/         # SHAP/fallback, importance, counterfactuals, audit reports
    ├── fraud/                  # pluggable anomaly detectors and ensemble pipeline
    ├── fraud_intelligence/     # behaviour, identity, rules, scoring, confidence, explanations
    ├── model_operations/       # artifacts, registry, lifecycle, promotion, monitoring, rollback
    ├── models/                 # compatibility namespace reserved by the frozen architecture
    ├── registry/               # compatibility namespace; model_operations is authoritative
    ├── monitoring/             # compatibility namespace; model_operations is authoritative
    ├── pipelines/              # extensible pipeline framework (stages pluggable)
    ├── services/               # application services that compose modules
    └── utils/                  # pure helpers: dates, files, serialization, seeds, paths, ...
```

## Responsibility summary

| Folder | Responsibility | Sprint 1? |
|---|---|---|
| `constants` | Fixed values referenced everywhere (no magic strings/numbers) | ✅ |
| `exceptions` | Typed, structured error classes | ✅ |
| `logging` | Loguru sinks: console, rotating file, error, training, inference, pipeline | ✅ |
| `config` | Environment-aware, validated, typed configuration | ✅ |
| `core` | Abstract base classes (BaseLoader/Validator/Pipeline/Model/…) | ✅ |
| `data/loaders` | Standardised DataFrame loading + factory | ✅ |
| `data/validators` | Structured validation reports | ✅ |
| `data/schemas` | Declarative dataset schemas | ✅ |
| `preprocessing` | Cleaning, imputation, encoding, scaling, selection, serialization | ✅ |
| `feature_engineering` | Financial feature generators + registry | ✅ |
| `credit_intelligence` | Training, optimization, calibration, evaluation, rules, confidence | ✅ |
| `decision`,`inference` | Governed unified lending decision and application contract | ✅ |
| `explainability` | SHAP/fallback explanations, importance, counterfactuals, audit reports | ✅ |
| `fraud`,`fraud_intelligence` | Detection strategies and business-facing orchestration | ✅ |
| `model_operations` | Integrity, registry, lifecycle, monitoring, alerts, promotion, rollback | ✅ (local adapters) |
| `pipelines` | Compose stages into runnable pipelines | ✅ (framework) |
| `services` | High-level orchestration entry points | ✅ (framework) |
| `utils` | Cross-cutting pure helpers | ✅ |
| `models`,`training`,`evaluation`,`registry`,`monitoring` | Frozen compatibility namespaces | Reserved |

> `tests/` and `docs/` live at the project root (`ai-engine/`) rather than inside the package —
> the standard Python packaging convention. This is the deliberate "improvement" over the
> example layout.
