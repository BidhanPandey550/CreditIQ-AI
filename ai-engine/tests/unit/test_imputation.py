"""Tests for Component 2 — the Missing Value (Imputation) Engine."""

import numpy as np
import pandas as pd
import pytest

from creditiq_ai.exceptions import PreprocessingError
from creditiq_ai.config import load_config
from creditiq_ai.preprocessing.imputation import (
    ColumnStrategy,
    ImputationConfig,
    ImputerFactory,
    MissingValueEngine,
)
from creditiq_ai.preprocessing.imputation.imputers import (
    BackwardFillImputer,
    ConstantImputer,
    ForwardFillImputer,
    MeanImputer,
    MedianImputer,
    ModeImputer,
)


# --------------------------------------------------------------------------- strategies
def test_mean_imputer():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, np.nan]})
    out = MeanImputer().fit_transform(df)
    assert out["x"].iloc[3] == 2.0


def test_median_imputer():
    df = pd.DataFrame({"x": [1.0, 2.0, 100.0, np.nan]})
    out = MedianImputer().fit_transform(df)
    assert out["x"].iloc[3] == 2.0


def test_mode_imputer_categorical():
    df = pd.DataFrame({"c": ["a", "a", "b", None]})
    out = ModeImputer().fit_transform(df)
    assert out["c"].iloc[3] == "a"


def test_constant_imputer():
    df = pd.DataFrame({"x": [1.0, np.nan]})
    out = ConstantImputer({"fill_value": -1}).fit_transform(df)
    assert out["x"].iloc[1] == -1


def test_forward_and_backward_fill():
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
    assert ForwardFillImputer().fit_transform(df)["x"].tolist() == [1.0, 1.0, 3.0]
    assert BackwardFillImputer().fit_transform(df)["x"].tolist() == [1.0, 3.0, 3.0]


# --------------------------------------------------------------------------- factory
def test_factory_lists_all_strategies():
    assert set(ImputerFactory.available()) == {
        "mean",
        "median",
        "mode",
        "constant",
        "ffill",
        "bfill",
        "knn",
        "iterative",
    }


def test_factory_unknown_raises():
    with pytest.raises(PreprocessingError):
        ImputerFactory.create("nope")


# --------------------------------------------------------------------------- engine
def test_engine_defaults_by_dtype():
    df = pd.DataFrame({"num": [1.0, 2.0, np.nan], "cat": ["a", None, "a"]})
    out, report = MissingValueEngine(ImputationConfig()).fit_transform(df)
    assert out.isna().sum().sum() == 0
    strategies = {c.column: c.strategy for c in report.columns}
    assert strategies["num"] == "median"
    assert strategies["cat"] == "mode"


def test_engine_multivariate_knn():
    df = pd.DataFrame(
        {
            "a": [1.0, 2.0, 3.0, np.nan, 5.0],
            "b": [2.0, 4.0, np.nan, 8.0, 10.0],
        }
    )
    out, _ = MissingValueEngine(ImputationConfig(default_numeric="knn")).fit_transform(df)
    assert out.isna().sum().sum() == 0


def test_engine_iterative():
    df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0], "b": [2.0, np.nan, 6.0, 8.0]})
    out, _ = MissingValueEngine(ImputationConfig(default_numeric="iterative")).fit_transform(df)
    assert out.isna().sum().sum() == 0


def test_engine_per_column_override():
    df = pd.DataFrame({"x": [10.0, 20.0, np.nan], "y": [1.0, np.nan, 3.0]})
    config = ImputationConfig(
        columns={"x": ColumnStrategy(strategy="constant", params={"fill_value": -999})}
    )
    out, report = MissingValueEngine(config).fit_transform(df)
    assert out["x"].iloc[2] == -999
    strategies = {c.column: c.strategy for c in report.columns}
    assert strategies["x"] == "constant"


def test_numeric_only_strategy_on_categorical_raises():
    df = pd.DataFrame({"cat": ["a", None, "b"]})
    config = ImputationConfig(columns={"cat": ColumnStrategy(strategy="mean")})
    with pytest.raises(PreprocessingError):
        MissingValueEngine(config).fit(df)


def test_train_statistics_reused_at_inference():
    train = pd.DataFrame({"x": [2.0, 4.0, 6.0, np.nan]})  # median of [2,4,6] = 4
    engine = MissingValueEngine(ImputationConfig()).fit(train)
    test = pd.DataFrame({"x": [np.nan, np.nan]})
    out = engine.transform(test)
    assert out["x"].tolist() == [4.0, 4.0]  # uses TRAIN median, no leakage


def test_report_totals():
    df = pd.DataFrame({"x": [1.0, np.nan, np.nan]})
    _, report = MissingValueEngine(ImputationConfig()).fit_transform(df)
    assert report.total_imputed == 2


def test_imputation_config_comes_from_unified_engine_config():
    cfg = load_config()  # single config surface, no independent YAML load
    assert cfg.imputation.default_numeric in ImputerFactory.available()
