"""Module 3 — Feature registry.

Purpose:  Name → generator-class lookup so features are added by registration, never by editing
          a central pipeline (open/closed).
Inputs:   registration calls.
Outputs:  generator classes / instances by name.
Deps:     core.base, generators.
Extend:   call register("my_feature")(MyFeatureClass) from any module at import time.
"""

from __future__ import annotations

from typing import Callable

from creditiq_ai.core.base import BaseFeatureGenerator
from creditiq_ai.core.exceptions import FeatureEngineeringError
from creditiq_ai.feature_engineering import generators as g

_REGISTRY: dict[str, type[BaseFeatureGenerator]] = {}


def register(
    name: str,
) -> Callable[[type[BaseFeatureGenerator]], type[BaseFeatureGenerator]]:
    """Decorator/registrar for a feature generator class."""

    def _wrap(cls: type[BaseFeatureGenerator]) -> type[BaseFeatureGenerator]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_generator_class(name: str) -> type[BaseFeatureGenerator]:
    if name not in _REGISTRY:
        raise FeatureEngineeringError(
            f"Unknown feature '{name}'", context={"available": sorted(_REGISTRY)}
        )
    return _REGISTRY[name]


def available_features() -> list[str]:
    return sorted(_REGISTRY)


# Register the built-in generators.
register("income_stability")(g.IncomeStabilityFeature)
register("savings_ratio")(g.SavingsRatioFeature)
register("debt_to_income")(g.DebtToIncomeFeature)
register("expense_ratio")(g.ExpenseRatioFeature)
register("cash_flow_stability")(g.CashFlowStabilityFeature)
register("avg_monthly_income")(g.AvgMonthlyIncomeFeature)
register("payment_consistency")(g.PaymentConsistencyFeature)
register("transaction_frequency")(g.TransactionFrequencyFeature)
register("income_growth")(g.IncomeGrowthFeature)
register("financial_behaviour_index")(g.FinancialBehaviourIndexFeature)
