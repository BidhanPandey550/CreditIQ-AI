"""Module 3 — Feature generators.

Purpose:  Each class produces ONE financial feature from the applicant DataFrame. Generators are
          self-contained and registered (not hard-wired), so new features are added without
          touching existing ones (open/closed).
Inputs:   DataFrame with scalar columns (and optionally wide monthly-series columns).
Outputs:  DataFrame with the new feature column(s) appended.
Deps:     pandas, numpy; core.base.BaseFeatureGenerator; utils.mathx.
Extend:   subclass BaseFeatureGenerator, set feature_names/dependencies, register in registry.py.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from creditiq_ai.core.base import BaseFeatureGenerator
from creditiq_ai.core.exceptions import FeatureEngineeringError
from creditiq_ai.utils.mathx import clip01, safe_div


def _vectorized_cv(block: pd.DataFrame) -> pd.Series:
    """Row-wise coefficient of variation, fully vectorized (no per-row Python apply)."""
    mean = block.mean(axis=1)
    std = block.std(axis=1, ddof=0)
    cv = std / mean.abs()
    return cv.replace([float("inf"), float("-inf")], 0.0).fillna(0.0)


# Canonical input column names (align with the data schema / ApplicantRecord).
INCOME = "monthly_income"
EXPENSES = "monthly_expenses"
DEBT = "monthly_debt_payments"
EMPLOYMENT = "employment_months"
DELINQUENCY = "has_delinquency"
INCOME_SERIES_PREFIX = "income_month_"
TXN_SERIES_PREFIX = "txn_month_"


class _FeatureBase(BaseFeatureGenerator):
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.params = params or {}

    def _require(self, df: pd.DataFrame) -> None:
        missing = [c for c in self.dependencies if c not in df.columns]
        if missing:
            raise FeatureEngineeringError(
                f"{self.name} missing required columns", context={"missing": missing}
            )

    @staticmethod
    def _wide(df: pd.DataFrame, prefix: str) -> list[str]:
        pattern = re.compile(rf"^{re.escape(prefix)}\d+$")
        return sorted(
            [c for c in df.columns if pattern.match(c)], key=lambda c: int(c.rsplit("_", 1)[1])
        )


class DebtToIncomeFeature(_FeatureBase):
    feature_names = ["debt_to_income"]
    dependencies = [INCOME]

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        self._require(df)
        out = df.copy()
        debt = out[DEBT] if DEBT in out.columns else 0.0
        out["debt_to_income"] = safe_div(debt, out[INCOME], default=1.0)
        return out


class SavingsRatioFeature(_FeatureBase):
    feature_names = ["savings_ratio"]
    dependencies = [INCOME, EXPENSES]

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        self._require(df)
        out = df.copy()
        debt = out[DEBT] if DEBT in out.columns else 0.0
        out["savings_ratio"] = safe_div(out[INCOME] - out[EXPENSES] - debt, out[INCOME])
        return out


class ExpenseRatioFeature(_FeatureBase):
    feature_names = ["expense_ratio"]
    dependencies = [INCOME, EXPENSES]

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        self._require(df)
        out = df.copy()
        out["expense_ratio"] = safe_div(out[EXPENSES], out[INCOME], default=1.0)
        return out


class AvgMonthlyIncomeFeature(_FeatureBase):
    feature_names = ["avg_monthly_income"]
    dependencies = []

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        wide = self._wide(out, INCOME_SERIES_PREFIX)
        if wide:
            out["avg_monthly_income"] = out[wide].mean(axis=1)
        elif INCOME in out.columns:
            out["avg_monthly_income"] = out[INCOME]
        else:
            out["avg_monthly_income"] = 0.0
        return out


class IncomeStabilityFeature(_FeatureBase):
    """1/(1+CV) of the monthly income series; falls back to an employment-tenure proxy."""

    feature_names = ["income_stability"]
    dependencies = []

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        wide = self._wide(out, INCOME_SERIES_PREFIX)
        if wide:
            out["income_stability"] = 1.0 / (1.0 + _vectorized_cv(out[wide]))
        elif EMPLOYMENT in out.columns:
            months_full = float(self.params.get("months_for_full_stability", 24))
            out["income_stability"] = clip01(out[EMPLOYMENT].fillna(0) / months_full)
        else:
            out["income_stability"] = 0.5
        return out


class CashFlowStabilityFeature(_FeatureBase):
    """Stability of net monthly cash flow; falls back to a single-period net-margin proxy."""

    feature_names = ["cash_flow_stability"]
    dependencies = []

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        inc_wide = self._wide(out, INCOME_SERIES_PREFIX)
        if inc_wide:
            out["cash_flow_stability"] = 1.0 / (1.0 + _vectorized_cv(out[inc_wide]))
        elif INCOME in out.columns and EXPENSES in out.columns:
            out["cash_flow_stability"] = clip01(safe_div(out[INCOME] - out[EXPENSES], out[INCOME]))
        else:
            out["cash_flow_stability"] = 0.5
        return out


class PaymentConsistencyFeature(_FeatureBase):
    """Proxy for on-time repayment behaviour (1 = consistent)."""

    feature_names = ["payment_consistency"]
    dependencies = []

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if DELINQUENCY in out.columns:
            penalty = float(self.params.get("delinquency_penalty", 1.0))
            out["payment_consistency"] = clip01(1.0 - out[DELINQUENCY].fillna(0) * penalty)
        else:
            out["payment_consistency"] = 1.0
        return out


class TransactionFrequencyFeature(_FeatureBase):
    """Average monthly transaction count from the transaction series (0 if unavailable)."""

    feature_names = ["transaction_frequency"]
    dependencies = []

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        wide = self._wide(out, TXN_SERIES_PREFIX)
        if wide:
            out["transaction_frequency"] = out[wide].mean(axis=1)
        elif "transaction_count" in out.columns:
            out["transaction_frequency"] = out["transaction_count"].fillna(0)
        else:
            out["transaction_frequency"] = 0.0
        return out


class IncomeGrowthFeature(_FeatureBase):
    """Relative growth between the first and last month of the income series (0 if unavailable)."""

    feature_names = ["income_growth"]
    dependencies = []

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        wide = self._wide(out, INCOME_SERIES_PREFIX)
        if len(wide) >= 2:
            first, last = out[wide[0]], out[wide[-1]]
            out["income_growth"] = safe_div(last - first, first)
        else:
            out["income_growth"] = 0.0
        return out


class FinancialBehaviourIndexFeature(_FeatureBase):
    """Composite 0–1 index blending the core behavioural features (weights from config)."""

    feature_names = ["financial_behaviour_index"]
    dependencies = [
        "income_stability",
        "savings_ratio",
        "debt_to_income",
        "cash_flow_stability",
        "payment_consistency",
    ]

    _DEFAULT_WEIGHTS = {
        "income_stability": 0.25,
        "savings_ratio": 0.20,
        "debt_to_income": 0.25,
        "cash_flow_stability": 0.15,
        "payment_consistency": 0.15,
    }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        self._require(df)
        out = df.copy()
        weights = {**self._DEFAULT_WEIGHTS, **self.params.get("weights", {})}
        total = sum(weights.values()) or 1.0
        components = {
            "income_stability": clip01(out["income_stability"]),
            "savings_ratio": clip01(out["savings_ratio"]),
            "debt_to_income": clip01(1.0 - out["debt_to_income"]),  # lower DTI is better
            "cash_flow_stability": clip01(out["cash_flow_stability"]),
            "payment_consistency": clip01(out["payment_consistency"]),
        }
        index = sum(components[name] * weight for name, weight in weights.items()) / total
        out["financial_behaviour_index"] = clip01(index)
        return out
