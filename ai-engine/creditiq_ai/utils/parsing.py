"""Value-parsing helpers shared by cleaning strategies.

Purpose:  Pure, reusable parsers for currency / percentage / boolean tokens so no cleaner
          re-implements this logic (DRY).
Inputs:   scalar values (possibly messy strings).
Outputs:  floats / bools / NaN.
Deps:     numpy.
Extend:   add a parser here and reference it from a cleaner.
"""

from __future__ import annotations

import re
from typing import Final

import numpy as np

_NON_NUMERIC: Final = re.compile(r"[^0-9.\-]")

DEFAULT_TRUE_TOKENS: Final[frozenset[str]] = frozenset({"true", "t", "yes", "y", "1"})
DEFAULT_FALSE_TOKENS: Final[frozenset[str]] = frozenset({"false", "f", "no", "n", "0"})
DEFAULT_MISSING_TOKENS: Final[frozenset[str]] = frozenset(
    {"", "na", "n/a", "null", "none", "nan", "-", "--", "?"}
)


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and np.isnan(value))


def parse_currency(value: object) -> float:
    """'Rs 1,200.50' → 1200.5 ; unparseable / missing → NaN."""
    if _is_missing(value):
        return np.nan
    cleaned = _NON_NUMERIC.sub("", str(value))
    if cleaned in {"", "-", ".", "-."}:
        return np.nan
    try:
        return float(cleaned)
    except ValueError:
        return np.nan


def parse_percentage(value: object, as_fraction: bool = True) -> float:
    """'45%' → 0.45 (as_fraction) or 45.0. Bare numbers pass through."""
    if _is_missing(value):
        return np.nan
    number = parse_currency(value)
    if np.isnan(number):
        return np.nan
    return number / 100.0 if as_fraction else number


def parse_boolean(
    value: object,
    true_tokens: frozenset[str] = DEFAULT_TRUE_TOKENS,
    false_tokens: frozenset[str] = DEFAULT_FALSE_TOKENS,
) -> bool | float:
    """Map truthy/falsy tokens to bool; unknown / missing → NaN."""
    if _is_missing(value):
        return np.nan
    token = str(value).strip().lower()
    if token in true_tokens:
        return True
    if token in false_tokens:
        return False
    return np.nan
