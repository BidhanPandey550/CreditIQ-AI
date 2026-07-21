"""Numeric helper functions shared across feature engineering and scoring.

Purpose:  Small, pure, well-tested numeric utilities (no magic numbers inline).
Deps:     numpy, pandas.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd


def safe_div(
    numerator: pd.Series | float, denominator: pd.Series | float, default: float = 0.0
) -> pd.Series | float:
    """Element-wise division returning `default` where the denominator is 0 / NaN.

    Handles scalar/Series mixes by broadcasting (not index alignment), so a scalar numerator
    against a Series denominator fills the whole column rather than only index 0.
    """
    num_is_series = isinstance(numerator, pd.Series)
    den_is_series = isinstance(denominator, pd.Series)

    if not num_is_series and not den_is_series:  # scalar / scalar
        if denominator in (0, None) or (isinstance(denominator, float) and denominator == 0.0):
            return float(default)
        value = float(numerator) / float(denominator)
        return value if np.isfinite(value) else float(default)

    index = cast(pd.Series, numerator if num_is_series else denominator).index
    num_arr = (
        cast(pd.Series, numerator).to_numpy(dtype=float)
        if num_is_series
        else np.asarray(numerator, dtype=float)
    )
    den_arr = (
        cast(pd.Series, denominator).to_numpy(dtype=float)
        if den_is_series
        else np.asarray(denominator, dtype=float)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.divide(num_arr, den_arr)
    result = np.where((den_arr == 0) | ~np.isfinite(result), default, result)
    return pd.Series(result, index=index)


def clip01(series: pd.Series | float) -> pd.Series | float:
    """Clip values to the [0, 1] interval."""
    if isinstance(series, pd.Series):
        return series.clip(0.0, 1.0)
    return float(min(1.0, max(0.0, series)))
