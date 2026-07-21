"""Tests for Component 1 — the Data Cleaning Engine (cleaners, factory, engine, config)."""

import numpy as np
import pandas as pd
import pytest

from creditiq_ai.exceptions import PreprocessingError
from creditiq_ai.config import load_config
from creditiq_ai.preprocessing.cleaning import (
    CleanerFactory,
    CleaningConfig,
    CleanerStep,
    DataCleaningEngine,
)
from creditiq_ai.preprocessing.cleaning.cleaners import (
    BooleanNormalizer,
    CategoricalCleanup,
    ConsistencyChecker,
    CurrencyNormalizer,
    DatatypeCorrector,
    DuplicateRemover,
    InvalidValueDetector,
    MissingValueStandardizer,
    PercentageNormalizer,
    WhitespaceCleaner,
)


# --------------------------------------------------------------------------- individual cleaners
def test_whitespace_cleaner():
    df = pd.DataFrame({"name": ["  Sita  ", "Ram   Thapa"]})
    out, rep = WhitespaceCleaner({"collapse_internal": True}).clean(df)
    assert out["name"].tolist() == ["Sita", "Ram Thapa"]
    assert rep.cleaner == "WhitespaceCleaner"


def test_missing_value_standardizer():
    df = pd.DataFrame({"x": ["NA", "n/a", "5", ""]})
    out, rep = MissingValueStandardizer().clean(df)
    assert out["x"].isna().sum() == 3
    assert rep.changes["values_nulled"] == 3


def test_duplicate_remover():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    out, rep = DuplicateRemover().clean(df)
    assert len(out) == 2
    assert rep.changes["duplicates_removed"] == 1


def test_datatype_corrector_auto_numeric():
    df = pd.DataFrame({"income": ["100", "200", "300"], "name": ["a", "b", "c"]})
    out, rep = DatatypeCorrector({"auto": True}).clean(df)
    assert out["income"].dtype.kind in "if"
    assert rep.changes["columns_converted"]["income"] == "numeric"


def test_categorical_cleanup_with_mapping():
    df = pd.DataFrame({"emp": [" Self Emp ", "SALARIED"]})
    out, _ = CategoricalCleanup({"mapping": {"emp": {"self emp": "self_employed"}}}).clean(df)
    assert out["emp"].tolist() == ["self_employed", "salaried"]


def test_currency_normalizer():
    df = pd.DataFrame({"amt": ["Rs 1,200.50", "NPR 3,000", None]})
    out, _ = CurrencyNormalizer({"columns": ["amt"]}).clean(df)
    assert out["amt"].iloc[0] == 1200.5
    assert np.isnan(out["amt"].iloc[2])


def test_percentage_normalizer():
    df = pd.DataFrame({"rate": ["45%", "12.5%"]})
    out, _ = PercentageNormalizer({"columns": ["rate"], "as_fraction": True}).clean(df)
    assert out["rate"].iloc[0] == 0.45


def test_boolean_normalizer():
    df = pd.DataFrame({"flag": ["Yes", "no", "maybe"]})
    out, _ = BooleanNormalizer({"columns": ["flag"]}).clean(df)
    assert out["flag"].iloc[0] is True
    assert out["flag"].iloc[1] is False
    assert pd.isna(out["flag"].iloc[2])


def test_invalid_value_detector_set_nan():
    df = pd.DataFrame({"income": [100, -5, 200]})
    out, rep = InvalidValueDetector(
        {"rules": [{"column": "income", "min": 0, "action": "set_nan"}]}
    ).clean(df)
    assert pd.isna(out["income"].iloc[1])
    assert rep.changes["invalid_values"]["income"] == 1


def test_invalid_value_detector_drop():
    df = pd.DataFrame({"income": [100, -5, 200]})
    out, _ = InvalidValueDetector(
        {"rules": [{"column": "income", "min": 0, "action": "drop"}]}
    ).clean(df)
    assert len(out) == 2


def test_consistency_checker_flags():
    df = pd.DataFrame({"income": [100, 100], "expenses": [50, 150]})
    out, rep = ConsistencyChecker(
        {"rules": [{"left": "expenses", "op": "<=", "right": "income", "action": "flag"}]}
    ).clean(df)
    assert rep.changes["violations"]["expenses<=income"] == 1
    assert len(out) == 2  # flag does not drop


# --------------------------------------------------------------------------- factory
def test_factory_lists_all_cleaners():
    assert len(CleanerFactory.available()) == 11
    assert "currency" in CleanerFactory.available()


def test_factory_unknown_raises():
    with pytest.raises(PreprocessingError):
        CleanerFactory.create("does_not_exist")


# --------------------------------------------------------------------------- engine + config
def test_engine_runs_configured_steps():
    df = pd.DataFrame({"name": ["  A  ", "  A  ", "B"], "income": ["100", "100", "200"]})
    config = CleaningConfig(
        steps=[
            CleanerStep(name="whitespace"),
            CleanerStep(name="correct_dtypes", params={"auto": True}),
            CleanerStep(name="drop_duplicates"),
        ]
    )
    out, report = DataCleaningEngine(config).clean(df)
    assert len(out) == 2  # duplicates removed after trimming
    assert out["income"].dtype.kind in "if"
    assert report.rows_removed == 1
    assert len(report.steps) == 3


def test_cleaning_config_comes_from_unified_engine_config():
    cfg = load_config()  # single config surface, no independent YAML load
    names = {s.name for s in cfg.cleaning.steps}
    assert {"whitespace", "drop_duplicates", "correct_dtypes"} <= names


def test_disabled_steps_are_skipped():
    config = CleaningConfig(steps=[CleanerStep(name="drop_duplicates", enabled=False)])
    engine = DataCleaningEngine(config)
    df = pd.DataFrame({"a": [1, 1]})
    out, report = engine.clean(df)
    assert len(out) == 2  # dedup disabled → nothing removed
    assert report.steps == []
