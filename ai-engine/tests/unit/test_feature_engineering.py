"""Tests for Module 3 — feature generators, registry, and pipeline."""

from pathlib import Path

import pandas as pd

from creditiq_ai.config import load_config
from creditiq_ai.feature_engineering import (
    FeatureEngineeringPipeline,
    available_features,
    register,
)
from creditiq_ai.feature_engineering.generators import (
    DebtToIncomeFeature,
    SavingsRatioFeature,
)
from creditiq_ai.core.base import BaseFeatureGenerator
from tests.fixtures.synthetic import make_credit_dataset

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def test_debt_to_income():
    df = pd.DataFrame({"monthly_income": [100.0], "monthly_debt_payments": [40.0]})
    out = DebtToIncomeFeature().generate(df)
    assert out["debt_to_income"].iloc[0] == 0.4


def test_savings_ratio():
    df = pd.DataFrame(
        {"monthly_income": [100.0], "monthly_expenses": [60.0], "monthly_debt_payments": [10.0]}
    )
    out = SavingsRatioFeature().generate(df)
    assert abs(out["savings_ratio"].iloc[0] - 0.3) < 1e-9


def test_registry_lists_all_ten():
    assert len(available_features()) >= 10
    assert "financial_behaviour_index" in available_features()


def test_pipeline_generates_all_configured_features():
    cfg = load_config(CONFIG_DIR)
    df = make_credit_dataset(50)
    pipe = FeatureEngineeringPipeline(cfg.features)
    out = pipe.transform(df)
    for feat in [
        "debt_to_income",
        "savings_ratio",
        "expense_ratio",
        "income_stability",
        "cash_flow_stability",
        "avg_monthly_income",
        "payment_consistency",
        "transaction_frequency",
        "income_growth",
        "financial_behaviour_index",
    ]:
        assert feat in out.columns


def test_composite_feature_resolves_after_dependencies():
    cfg = load_config(CONFIG_DIR)
    df = make_credit_dataset(20)
    out = FeatureEngineeringPipeline(cfg.features).transform(df)
    fbi = out["financial_behaviour_index"]
    assert fbi.between(0.0, 1.0).all()  # composite is bounded


def test_series_features_use_wide_columns():
    cfg = load_config(CONFIG_DIR)
    df = make_credit_dataset(20, with_series=True)
    out = FeatureEngineeringPipeline(cfg.features).transform(df)
    # income_growth should vary when a real income series is present
    assert out["income_growth"].std() > 0


def test_new_feature_added_by_registration_only():
    @register("dummy_constant")
    class DummyFeature(BaseFeatureGenerator):
        feature_names = ["dummy_constant"]
        dependencies = []

        def generate(self, df):
            out = df.copy()
            out["dummy_constant"] = 1.0
            return out

    assert "dummy_constant" in available_features()
