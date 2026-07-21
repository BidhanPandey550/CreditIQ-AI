# CreditIQ AI — ML Engine

A standalone, production-grade **credit-intelligence ML engine** (`creditiq_ai`). Framework-free:
no API, no UI, no auth — just the AI. Serving tiers depend on this library, never the reverse.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design (structure, class diagram,
data flow, extension points).

## Capabilities

| Module | Package | Status |
|---|---|---|
| Data loading, validation, cleaning, imputation | `data`, `validation`, `preprocessing` | implemented |
| Financial feature engineering | `feature_engineering` | implemented |
| Credit training framework (LogReg, Random Forest) | `credit_intelligence` | implemented; model zoo incomplete |
| Credit score + unified credit/fraud decision | `decision` | implemented |
| Fraud detector ensemble + 0–1000 score | `fraud`, `fraud_intelligence` | implemented core; orchestration incomplete |
| Local explainability + graceful SHAP fallback | `explainability` | implemented core; global/counterfactual incomplete |
| Integrity-verified artifacts and lifecycle registry | `model_operations` | implemented local adapter |
| Operational decision monitoring | `model_operations.monitoring` | implemented baseline; drift/alerts incomplete |

See [`docs/audits/technical_debt_register.md`](docs/audits/technical_debt_register.md) for an honest
record of incomplete capabilities and production-readiness gaps.

## Install & test

```bash
cd ai-engine
poetry install
poetry run pytest
```

Optional model libraries are grouped so core development stays reproducible and lightweight:

```bash
poetry install -E modeling  # XGBoost, LightGBM, CatBoost, SHAP, Optuna
poetry install -E mlops     # MLflow
poetry install -E all       # complete AI toolchain
```

## Configuration

Everything is configured in [`config/*.yaml`](config/) — no hardcoded values. Override any key
via environment: `CREDITIQ_RUNTIME__LOG_LEVEL=DEBUG`, `CREDITIQ_MODELS__OPTUNA_TRIALS=50`.

```python
from creditiq_ai import load_config
cfg = load_config()          # merges config/*.yaml + env, validated into EngineConfig
print(cfg.scoring.min_score, cfg.scoring.max_score)   # 300 850
```

## Design guarantees

- Clean architecture: dependencies point inward to `core` (pure contracts).
- Open/closed: add a feature, model, detector, scorer, or registry backend by implementing a base
  class + a config entry — no edits to existing code.
- Reproducibility: each trained model records the exact `config_hash` it was trained under.
- Typed I/O everywhere (Pydantic), structured logging, custom exceptions, pytest per module.
