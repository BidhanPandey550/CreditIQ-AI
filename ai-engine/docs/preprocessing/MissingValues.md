# Missing Value Engine (Component 2)

Reproducible imputation via **Strategy + Factory + DI**. Statistics are learned at `fit()` and
reused verbatim at `transform()`, so **there is no train→test leakage** and the fitted engine is
joblib-serialisable for inference.

```python
from creditiq_ai.config import load_config
from creditiq_ai.preprocessing.imputation import MissingValueEngine
imputed_df, report = MissingValueEngine(load_config().imputation).fit_transform(df)
# inference:
imputed_test = MissingValueEngine(...).fit(train).transform(test)
```

## Strategies

| Strategy (YAML) | Type | When to use | Advantages | Disadvantages |
|---|---|---|---|---|
| `mean` | univariate, numeric | ~symmetric numeric distributions | Fast, simple | Distorted by skew/outliers; shrinks variance |
| `median` | univariate, numeric | skewed / outlier-prone numerics (income) | Robust to outliers | Ignores relationships between features |
| `mode` | univariate, any | categoricals & low-cardinality numerics | Works for text | Over-represents the majority category |
| `constant` | univariate, any | "missing" is meaningful (sentinel/`unknown`) | Explicit, auditable | Can bias models if overused |
| `ffill` | univariate | ordered / time-series data | Preserves last-known value | Needs meaningful row order |
| `bfill` | univariate | ordered data, back-looking | Fills leading gaps | Same ordering caveat |
| `knn` | multivariate, numeric | correlated numeric features | Uses feature relationships | O(n²) distance cost; scale-sensitive |
| `iterative` | multivariate, numeric | rich numeric feature interactions (MICE) | Most accurate when relationships exist | Slow; assumes modellable structure |

## How the engine resolves strategy per column
1. An explicit `columns:` override wins.
2. Otherwise numeric columns get `default_numeric`, non-numeric get `default_categorical`.
3. Univariate strategies are applied per column (only columns that actually contain NaN).
4. Multivariate strategies (`knn`/`iterative`) pool all their numeric columns into one fitted
   imputer so neighbours/regressions can use every feature.
5. A `numeric_only` strategy assigned to a non-numeric column raises `PreprocessingError`
   (fail-fast, no silent corruption).

## Configuration
Everything lives under the `imputation:` section of [`config/base.yaml`](../../config/base.yaml),
injected as `EngineConfig.imputation`:
`default_numeric`, `default_categorical`, per-strategy params, and per-column overrides. The
engine has **no hardcoded imputation logic**.

## Report
`ImputationReport.columns[]` gives `column`, `strategy`, `missing_before`, `missing_after`;
`report.total_imputed` is the total values filled.

## Extension points
- **New strategy:** subclass `BaseImputer` (set `supports_multivariate` / `numeric_only`),
  implement `fit`/`transform`, then `register("name")(MyImputer)`. Reference it from YAML.
- **Alternate config source:** inject a different `ImputationConfig` (Dependency Inversion).
- **Serialization:** the fitted engine is picklable (`joblib.dump`) — Component 11 will wrap this
  with metadata + version numbers.
