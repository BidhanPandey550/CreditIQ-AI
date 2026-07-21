"""Module 1 — Automatic datatype conversion.

Purpose:  Coerce a DataFrame's columns to the dtypes declared in the data schema config,
          tolerating messy upstream types without silently corrupting data.
Inputs:   DataFrame + list[ColumnSpec].
Outputs:  new DataFrame with coerced dtypes.
Deps:     pandas; config.models.ColumnSpec.
Extend:   add a branch to _coerce_series for a new dtype token.
"""

from __future__ import annotations

import pandas as pd

from creditiq_ai.config.models import ColumnSpec
from creditiq_ai.core.logging import get_logger

logger = get_logger("creditiq_ai.data.dtypes")


def _coerce_series(series: pd.Series, dtype: str) -> pd.Series:
    if dtype in {"float", "float64"}:
        return pd.to_numeric(series, errors="coerce").astype("float64")
    if dtype in {"int", "int64"}:
        # Nullable integer preserves NaNs from failed coercions.
        return pd.to_numeric(series, errors="coerce").astype("Int64")
    if dtype in {"str", "string", "object"}:
        return series.astype("string")
    if dtype in {"bool", "boolean"}:
        return series.astype("boolean")
    if dtype in {"datetime", "date"}:
        return pd.to_datetime(series, errors="coerce")
    logger.warning(f"Unknown dtype '{dtype}'; leaving column untouched")
    return series


def coerce_dtypes(df: pd.DataFrame, columns: list[ColumnSpec]) -> pd.DataFrame:
    """Return a copy of `df` with each declared column coerced to its configured dtype."""
    result = df.copy()
    for spec in columns:
        if spec.name in result.columns:
            result[spec.name] = _coerce_series(result[spec.name], spec.dtype)
    return result
