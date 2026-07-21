"""Synthetic dataset factory for tests (no real customer data)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_credit_dataset(n: int = 200, seed: int = 0, with_series: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    income = rng.uniform(20_000, 150_000, n).round(2)
    expenses = (income * rng.uniform(0.3, 0.9, n)).round(2)
    debt = (income * rng.uniform(0.0, 0.5, n)).round(2)
    data = {
        "applicant_id": [f"A{i:05d}" for i in range(n)],
        "monthly_income": income,
        "monthly_expenses": expenses,
        "monthly_debt_payments": debt,
        "total_assets": rng.uniform(0, 2_000_000, n).round(2),
        "total_liabilities": rng.uniform(0, 1_000_000, n).round(2),
        "savings_balance": rng.uniform(0, 500_000, n).round(2),
        "employment_months": rng.integers(0, 120, n),
        "num_existing_loans": rng.integers(0, 5, n),
        "has_delinquency": rng.binomial(1, 0.15, n),
    }
    dti = debt / income
    prob_default = 1 / (1 + np.exp(-(-1.0 + 3.0 * dti + 0.8 * data["has_delinquency"])))
    data["default"] = rng.binomial(1, prob_default)

    if with_series:
        for m in range(1, 7):
            data[f"income_month_{m}"] = (income * rng.uniform(0.8, 1.2, n)).round(2)
            data[f"txn_month_{m}"] = rng.integers(5, 60, n)

    return pd.DataFrame(data)
