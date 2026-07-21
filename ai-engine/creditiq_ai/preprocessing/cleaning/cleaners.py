"""Independent cleaning strategies.

Purpose:  One class per cleaning concern (SRP). Each is usable standalone and composed by the
          DataCleaningEngine via the factory. None mutate their input in place.
Inputs:   DataFrame + params (from YAML).
Outputs:  (cleaned DataFrame, changes summary).
Deps:     pandas, numpy; utils.parsing.
Extend:   add a class here + register it in factory.py.
"""

from __future__ import annotations

import operator
import warnings
from typing import Any, Callable

import numpy as np
import pandas as pd

from creditiq_ai.preprocessing.cleaning.base import BaseCleaner
from creditiq_ai.utils.parsing import (
    DEFAULT_FALSE_TOKENS,
    DEFAULT_MISSING_TOKENS,
    DEFAULT_TRUE_TOKENS,
    parse_boolean,
    parse_currency,
    parse_percentage,
)

_OPS: dict[str, Callable[[Any, Any], Any]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


class WhitespaceCleaner(BaseCleaner):
    """Trim leading/trailing whitespace (optionally collapse internal runs) on text columns."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        collapse = self.params.get("collapse_internal", False)
        touched = []
        for col in self._string_columns(out):
            stripped = out[col].astype("string").str.strip()
            if collapse:
                stripped = stripped.str.replace(r"\s+", " ", regex=True)
            if not stripped.equals(out[col].astype("string")):
                touched.append(col)
            out[col] = stripped
        return out, {"columns_trimmed": touched}


class MissingValueStandardizer(BaseCleaner):
    """Replace textual missing tokens ('', 'NA', 'null', ...) with a real NaN."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        tokens = {t.lower() for t in self.params.get("tokens", DEFAULT_MISSING_TOKENS)}
        replaced = 0
        for col in self._string_columns(out):
            lowered = out[col].astype("string").str.strip().str.lower()
            mask = lowered.isin(tokens)
            replaced += int(mask.sum())
            out.loc[mask, col] = np.nan
        return out, {"values_nulled": replaced}


class DuplicateRemover(BaseCleaner):
    """Drop duplicate rows (optionally on a subset of key columns)."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        subset = self.params.get("subset")
        keep = self.params.get("keep", "first")
        before = len(df)
        out = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
        return out, {"duplicates_removed": before - len(out)}


class DatatypeCorrector(BaseCleaner):
    """Auto-correct object columns to numeric/datetime; explicit mapping overrides auto."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        mapping: dict[str, str] = self.params.get("mapping", {})
        threshold = float(self.params.get("auto_threshold", 0.9))
        auto = self.params.get("auto", True)
        converted: dict[str, str] = {}

        for col, dtype in mapping.items():
            if col in out.columns:
                out[col] = self._coerce(out[col], dtype)
                converted[col] = dtype

        if auto:
            for col in out.columns:
                if col in mapping or out[col].dtype not in ("object", "string"):
                    continue
                non_null = out[col].notna().sum()
                if non_null == 0:
                    continue
                as_num = pd.to_numeric(out[col], errors="coerce")
                if as_num.notna().sum() / non_null >= threshold:
                    out[col] = as_num
                    converted[col] = "numeric"
                    continue
                with warnings.catch_warnings():
                    # Auto-probing non-date text is expected; suppress the inference notice.
                    warnings.simplefilter("ignore", UserWarning)
                    as_dt = pd.to_datetime(out[col], errors="coerce")
                if as_dt.notna().sum() / non_null >= threshold:
                    out[col] = as_dt
                    converted[col] = "datetime"
        return out, {"columns_converted": converted}

    @staticmethod
    def _coerce(series: pd.Series, dtype: str) -> pd.Series:
        if dtype in {"int", "float", "numeric"}:
            return pd.to_numeric(series, errors="coerce")
        if dtype in {"datetime", "date"}:
            return pd.to_datetime(series, errors="coerce")
        if dtype in {"str", "string"}:
            return series.astype("string")
        return series


class CategoricalCleanup(BaseCleaner):
    """Normalise categorical text: strip, lowercase, and apply a synonym→canonical mapping."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        lowercase = self.params.get("lowercase", True)
        strip = self.params.get("strip", True)
        mapping: dict[str, dict[str, str]] = self.params.get("mapping", {})
        for col in self._string_columns(out):
            series = out[col].astype("string")
            if strip:
                series = series.str.strip()
            if lowercase:
                series = series.str.lower()
            if col in mapping:
                series = series.replace(mapping[col])
            out[col] = series
        return out, {"columns_normalised": self._string_columns(out)}


class CurrencyNormalizer(BaseCleaner):
    """Parse currency-formatted text columns into floats."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        columns = self.params.get("columns", [])
        for col in columns:
            if col in out.columns:
                out[col] = out[col].map(parse_currency)
        return out, {"columns_parsed": [c for c in columns if c in out.columns]}


class PercentageNormalizer(BaseCleaner):
    """Parse percentage strings ('45%' → 0.45 or 45.0)."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        columns = self.params.get("columns", [])
        as_fraction = self.params.get("as_fraction", True)
        for col in columns:
            if col in out.columns:
                out[col] = out[col].map(lambda v: parse_percentage(v, as_fraction))
        return out, {"columns_parsed": [c for c in columns if c in out.columns]}


class BooleanNormalizer(BaseCleaner):
    """Map truthy/falsy tokens to booleans."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        columns = self.params.get("columns", [])
        true_tokens = frozenset(self.params.get("true_tokens", DEFAULT_TRUE_TOKENS))
        false_tokens = frozenset(self.params.get("false_tokens", DEFAULT_FALSE_TOKENS))
        for col in columns:
            if col in out.columns:
                out[col] = out[col].map(lambda v: parse_boolean(v, true_tokens, false_tokens))
        return out, {"columns_parsed": [c for c in columns if c in out.columns]}


class DateNormalizer(BaseCleaner):
    """Parse configured columns to datetime (optionally reformat to a string pattern)."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        columns = self.params.get("columns", [])
        output_format = self.params.get("output_format")
        for col in columns:
            if col in out.columns:
                parsed = pd.to_datetime(out[col], errors="coerce")
                out[col] = parsed.dt.strftime(output_format) if output_format else parsed
        return out, {"columns_parsed": [c for c in columns if c in out.columns]}


class InvalidValueDetector(BaseCleaner):
    """Flag values outside allowed ranges / sets; set them to NaN or drop the rows."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        rules: list[dict[str, Any]] = self.params.get("rules", [])
        invalid_counts: dict[str, int] = {}
        drop_mask = pd.Series(False, index=out.index)

        for rule in rules:
            col = rule["column"]
            if col not in out.columns:
                continue
            series = out[col]
            invalid = pd.Series(False, index=out.index)
            if "min" in rule:
                invalid |= pd.to_numeric(series, errors="coerce") < rule["min"]
            if "max" in rule:
                invalid |= pd.to_numeric(series, errors="coerce") > rule["max"]
            if "allowed" in rule:
                invalid |= ~series.isin(rule["allowed"]) & series.notna()
            invalid = invalid.fillna(False)
            invalid_counts[col] = int(invalid.sum())
            if rule.get("action", "set_nan") == "drop":
                drop_mask |= invalid
            else:
                out.loc[invalid, col] = np.nan

        if drop_mask.any():
            out = out[~drop_mask].reset_index(drop=True)
        return out, {"invalid_values": invalid_counts}


class ConsistencyChecker(BaseCleaner):
    """Cross-field consistency rules (e.g. expenses <= income). Flag / null / drop violations."""

    def _apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        out = df  # caller owns the copy (see BaseCleaner.clean(copy=...))
        rules: list[dict[str, Any]] = self.params.get("rules", [])
        violations: dict[str, int] = {}
        drop_mask = pd.Series(False, index=out.index)

        for rule in rules:
            left, op, right = rule["left"], rule["op"], rule["right"]
            if left not in out.columns or op not in _OPS:
                continue
            right_series = out[right] if isinstance(right, str) and right in out.columns else right
            satisfied = _OPS[op](out[left], right_series)
            violated = ~satisfied.fillna(True) if hasattr(satisfied, "fillna") else ~satisfied
            key = f"{left}{op}{right}"
            violations[key] = int(violated.sum())
            action = rule.get("action", "flag")
            if action == "drop":
                drop_mask |= violated
            elif action == "set_nan":
                out.loc[violated, left] = np.nan

        if drop_mask.any():
            out = out[~drop_mask].reset_index(drop=True)
        return out, {"violations": violations}
