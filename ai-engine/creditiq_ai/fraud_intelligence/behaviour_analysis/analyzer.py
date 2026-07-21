"""Vectorized financial behaviour risk analysis."""

from __future__ import annotations

import numpy as np

from creditiq_ai.config.models import FraudBehaviourConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.exceptions import ConfigurationError
from creditiq_ai.fraud_intelligence.behaviour_analysis.models import (
    BehaviourInput,
    BehaviourRiskProfile,
)


class BehaviourAnalyzer(BaseComponent):
    INDICATORS = frozenset(
        {
            "spending_volatility",
            "income_instability",
            "savings_inconsistency",
            "debt_burden",
            "transaction_frequency",
            "cash_flow_irregularity",
            "lifestyle_instability",
        }
    )

    def __init__(self, config: FraudBehaviourConfig) -> None:
        super().__init__()
        self.behaviour_config = config
        if set(config.weights) != self.INDICATORS or any(
            weight < 0.0 for weight in config.weights.values()
        ):
            raise ConfigurationError("Fraud behaviour weights must define every indicator")
        if sum(config.weights.values()) <= 0.0:
            raise ConfigurationError("Fraud behaviour weights must have a positive sum")

    def analyze(self, data: BehaviourInput) -> BehaviourRiskProfile:
        income = np.asarray(data.monthly_income, dtype=float)
        expenses = np.asarray(data.monthly_expenses, dtype=float)
        savings = np.asarray(data.monthly_savings, dtype=float)
        debt = np.asarray(data.monthly_debt_payments, dtype=float)
        transactions = np.asarray(data.transaction_counts, dtype=float)
        warnings: list[str] = []
        series = [income, expenses, savings, debt, transactions]
        completeness = sum(array.size > 0 for array in series) / len(series)
        if completeness < 1.0:
            warnings.append("incomplete_behaviour_history")

        income_mean = self._mean(income)
        expense_mean = self._mean(expenses)
        indicators = {
            "spending_volatility": self._cv(expenses),
            "income_instability": self._cv(income),
            "savings_inconsistency": self._cv(savings),
            "debt_burden": self._ratio(self._mean(debt), income_mean),
            "transaction_frequency": min(
                1.0, self._mean(transactions) / self.behaviour_config.transaction_frequency_cap
            ),
            "cash_flow_irregularity": self._cv(self._aligned_difference(income, expenses)),
            "lifestyle_instability": self._ratio(expense_mean, income_mean),
        }
        weights = self.behaviour_config.weights
        score = sum(indicators[name] * weights[name] for name in self.INDICATORS) / sum(
            weights.values()
        )
        return BehaviourRiskProfile(
            risk_score=round(min(1.0, max(0.0, score)), 4),
            indicators={name: round(value, 4) for name, value in indicators.items()},
            data_completeness=round(completeness, 4),
            warnings=warnings,
        )

    def _cv(self, values: np.ndarray) -> float:
        if values.size < 2 or self._mean(values) == 0.0:
            return 0.0
        return min(
            1.0,
            float(np.std(values)) / abs(self._mean(values)) / self.behaviour_config.volatility_cap,
        )

    @staticmethod
    def _mean(values: np.ndarray) -> float:
        return float(np.mean(values)) if values.size else 0.0

    @staticmethod
    def _ratio(numerator: float, denominator: float) -> float:
        return (
            min(1.0, max(0.0, numerator / denominator))
            if denominator > 0.0
            else float(numerator > 0.0)
        )

    @staticmethod
    def _aligned_difference(left: np.ndarray, right: np.ndarray) -> np.ndarray:
        size = min(left.size, right.size)
        return left[-size:] - right[-size:] if size else np.asarray([], dtype=float)
