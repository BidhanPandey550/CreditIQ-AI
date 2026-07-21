# Sprint 8.5 — Quality Gate Results

Environment: `ai-engine/.venv` (Python 3.11 runtime; pyproject targets 3.12). Deps present:
pydantic, pandas, numpy, scikit-learn, loguru, pyyaml, ruff. Absent (declared in pyproject):
pytest-cov, mypy, black, xgboost, lightgbm, catboost, shap, optuna, mlflow.

| Gate | Command | Baseline | Final | Status |
|---|---|---|---|---|
| Unit + integration tests | `pytest -q` | 119 passed | **123 passed** (119 unit + 4 integration) | ✅ |
| Lint | `ruff check creditiq_ai tests` | All checks passed | All checks passed | ✅ |
| Format check | `ruff format --check creditiq_ai` | 74 would reformat | 74 would reformat | ⚠️ P3 |
| Compile | `python -m compileall creditiq_ai` | OK | OK | ✅ |
| Import root | `python -c "import creditiq_ai"` | OK | OK | ✅ |
| Circular imports | `pkgutil.walk_packages` import-all | NONE | NONE | ✅ |
| Config load | `load_config()` all envs | OK | OK | ✅ |
| Coverage | `pytest --cov` | n/a | **NOT RUN** (`pytest-cov` not installed) | ⚠️ P2 |
| Type check | `mypy` | n/a | **NOT RUN** (`mypy` not installed) | ⚠️ P2 |
| Package build | `python -m build` | n/a | **NOT RUN** (`build` not installed; Poetry package) | ⚠️ P3 |
| Security scan (manual) | `grep` yaml.load/pickle/eval/secrets | clean | clean | ✅ |
| Smoke test | `python -m creditiq_ai.smoke_test` | n/a | **PASS (exit 0)**, 9 steps ok, 5 not_implemented | ✅ |

## Notes
- Coverage, mypy, and build gates could not run because their tools are not installed in the
  verification venv. They are **declared** in `pyproject.toml` dev deps; running them requires
  `poetry install`. Not claimed as passing.
- `ruff format --check` failing is cosmetic (the formatter was never applied); code is lint-clean.
- No gate was weakened or skipped to force a pass.
