"""Synthetic-but-realistic training data for the MVP models.

Real deployments train on the institution's historical, labelled loan outcomes. Here we
generate a plausible dataset from a known latent risk process so the pipeline is end-to-end
runnable without any real customer data.
"""
from __future__ import annotations

import numpy as np

# Feature order is the contract shared with the backend (compute_financials()).
FEATURES = [
    "debt_to_income",
    "savings_ratio",
    "income_stability",
    "cashflow_volatility",
    "has_delinquency",
]


def generate(n: int = 6000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    dti = np.clip(rng.beta(2, 3, n) * 1.4, 0, 1.8)
    savings = np.clip(rng.beta(2, 4, n), 0, 1)
    stability = np.clip(rng.beta(3, 2, n), 0, 1)
    volatility = np.clip(rng.beta(2, 3, n), 0, 1)
    delinquency = rng.binomial(1, 0.15, n).astype(float)

    # Latent default propensity — the "true" data-generating process.
    logit = (-1.2
             + 2.4 * dti
             - 1.6 * savings
             - 1.1 * stability
             + 1.5 * volatility
             + 1.3 * delinquency
             + rng.normal(0, 0.4, n))
    prob = 1 / (1 + np.exp(-logit))
    y = rng.binomial(1, prob)

    X = np.column_stack([dti, savings, stability, volatility, delinquency])
    return X, y


def vectorize(features: dict) -> list[float]:
    """Map an incoming feature dict to the model's feature vector (missing → sane defaults)."""
    defaults = {"debt_to_income": 0.4, "savings_ratio": 0.1, "income_stability": 0.5,
                "cashflow_volatility": 0.5, "has_delinquency": 0.0}
    return [float(features.get(k, defaults[k])) for k in FEATURES]
