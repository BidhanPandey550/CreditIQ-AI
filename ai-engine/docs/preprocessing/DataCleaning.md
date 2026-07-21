# Data Cleaning Engine (Component 1)

Reusable, config-driven cleaning built on the **Strategy** (each cleaner) + **Factory**
(`CleanerFactory`) patterns, injected with a typed `CleaningConfig`. Every step emits a
structured Loguru log and a `CleaningStepReport`; the engine returns an aggregate `CleaningReport`.

```python
from creditiq_ai.config import load_config
from creditiq_ai.preprocessing.cleaning import DataCleaningEngine
cfg = load_config()                                        # unified, environment-aware config
cleaned_df, report = DataCleaningEngine(cfg.cleaning).clean(raw_df)
```

## Cleaners

| Cleaner (YAML name) | What it does | When to use | Advantages | Disadvantages |
|---|---|---|---|---|
| `whitespace` | Trim / collapse whitespace in text | Almost always, first | Cheap; fixes join/group bugs | None material |
| `standardize_missing` | Map `''/NA/null/-` → NaN | Raw exports with mixed null tokens | Makes downstream imputation reliable | Token list must fit the domain |
| `correct_dtypes` | Auto-cast object→numeric/datetime (+ explicit map) | After missing/whitespace cleanup | Removes silent "numbers as strings" bugs | Auto-inference can misclassify borderline columns → set explicit `mapping` |
| `categorical_cleanup` | strip/lowercase + synonym→canonical map | Free-text categoricals ("Self Emp" vs "self_employed") | Collapses duplicate categories | Mapping is manual |
| `currency` | `'Rs 1,200.50'` → `1200.5` | Monetary text fields | Locale-tolerant | No FX conversion (single base currency) |
| `percentage` | `'45%'` → `0.45` | Rate/ratio text | Consistent fractions | Assumes `%` semantics |
| `boolean` | yes/no/1/0 → bool | Mixed boolean encodings | Uniform booleans | Unknown tokens → NaN |
| `date` | Parse to datetime (optional reformat) | Date text columns | Standard temporal type | Ambiguous formats need care |
| `invalid_values` | Range/allowed-set rules → NaN or drop | Known valid domains (e.g. income ≥ 0) | Declarative, per-column | Rules are manual |
| `consistency` | Cross-field rules (e.g. expenses ≤ income) | Relational invariants | Catches logical errors | Only simple comparisons |
| `drop_duplicates` | Remove duplicate rows | After key columns are cleaned | Prevents leakage/double counting | Runs after normalisation so keys match |

## Ordering guidance
`whitespace → standardize_missing → (currency/percentage/boolean/date) → categorical_cleanup →
correct_dtypes → invalid_values → consistency → drop_duplicates`. Normalise values **before**
de-duplicating so logically-equal rows actually match.

## Configuration
Cleaning steps live under the `cleaning:` section of [`config/base.yaml`](../../config/base.yaml)
(with per-environment overrides). Steps are ordered, individually `enabled`, and parameterised —
the engine has **zero hardcoded cleaning logic**. Config is validated into `EngineConfig.cleaning`
by the single config loader and **injected** into the engine; the engine never reads YAML itself.

## Reports
- `CleaningStepReport`: `cleaner`, `rows_before`, `rows_after`, `changes` (per-cleaner detail).
- `CleaningReport`: `initial_rows`, `final_rows`, `rows_removed`, `steps[]`.

## Extension points
- **New cleaner:** subclass `BaseCleaner`, implement `_apply(df) -> (df, changes)`, then
  `register("my_cleaner")(MyCleaner)`. Add it to the YAML — no engine change (Open/Closed).
- **New parser:** add to `creditiq_ai/utils/parsing.py` and reference it from a cleaner (DRY).
- **Alternate config source:** swap the config loader for a DB/remote source; the engine
  only depends on the `CleaningConfig` type (Dependency Inversion).
