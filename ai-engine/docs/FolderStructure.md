# CreditIQ AI Engine — Folder Structure

Sprint 1 delivers the **foundation** only (no ML models). Every folder below has a single,
clear responsibility so future ML modules plug in without touching existing code.

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
    ├── models/                 # (future) estimator wrappers — Sprint 2+
    ├── training/               # (future) training orchestration — Sprint 2+
    ├── inference/              # (future) inference engine — Sprint 2+
    ├── evaluation/             # (future) metrics & reports — Sprint 2+
    ├── explainability/         # (future) SHAP explainers — Sprint 2+
    ├── fraud/                  # (future) anomaly detectors — Sprint 2+
    ├── registry/               # (future) model registry — Sprint 2+
    ├── monitoring/             # (future) drift / metrics / logging hooks — Sprint 2+
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
| `preprocessing` | Transformer components + pipeline | ✅ (foundation) |
| `feature_engineering` | Feature generators + registry | ✅ (foundation) |
| `pipelines` | Compose stages into runnable pipelines | ✅ (framework) |
| `services` | High-level orchestration entry points | ✅ (framework) |
| `utils` | Cross-cutting pure helpers | ✅ |
| `models`,`training`,`inference`,`evaluation`,`explainability`,`fraud`,`registry`,`monitoring` | ML capabilities | ⏳ Sprint 2+ |

> `tests/` and `docs/` live at the project root (`ai-engine/`) rather than inside the package —
> the standard Python packaging convention. This is the deliberate "improvement" over the
> example layout.
```
