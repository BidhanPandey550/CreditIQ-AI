"""Tests for Module 1 — data loading, dtype coercion, and validation."""

from pathlib import Path

import pandas as pd
import pytest

from creditiq_ai.config import load_config
from creditiq_ai.core.exceptions import DataLoadError
from creditiq_ai.data import coerce_dtypes, get_loader, load_dataset
from creditiq_ai.data.loaders import CsvLoader
from creditiq_ai.validation import DatasetValidator
from tests.fixtures.synthetic import make_credit_dataset

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def test_get_loader_by_extension():
    assert isinstance(get_loader("x.csv"), CsvLoader)


def test_unknown_extension_raises():
    with pytest.raises(DataLoadError):
        get_loader("x.unknown")


def test_csv_roundtrip(tmp_path):
    df = make_credit_dataset(50)
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)
    loaded = load_dataset(path)
    assert len(loaded) == 50
    assert "monthly_income" in loaded.columns


def test_missing_file_raises():
    with pytest.raises(DataLoadError):
        load_dataset("/nonexistent/file.csv")


def test_coerce_dtypes():
    cfg = load_config(CONFIG_DIR)
    df = pd.DataFrame({"applicant_id": [1, 2], "monthly_income": ["100", "bad"], "default": [0, 1]})
    coerced = coerce_dtypes(df, cfg.data.columns)
    assert coerced["monthly_income"].dtype.kind == "f"
    assert pd.isna(coerced["monthly_income"].iloc[1])  # 'bad' → NaN


def test_validation_passes_on_clean_data():
    cfg = load_config(CONFIG_DIR)
    df = make_credit_dataset(100)
    report = DatasetValidator(cfg.data).validate(df)
    assert report.passed
    assert report.n_rows == 100


def test_validation_flags_duplicate_ids():
    cfg = load_config(CONFIG_DIR)
    df = make_credit_dataset(10)
    df.loc[1, "applicant_id"] = df.loc[0, "applicant_id"]
    report = DatasetValidator(cfg.data).validate(df)
    assert not report.passed
    assert any(i.rule == "duplicate.ids" for i in report.errors)


def test_validation_flags_out_of_range():
    cfg = load_config(CONFIG_DIR)
    df = make_credit_dataset(10)
    df.loc[0, "monthly_income"] = -5  # below configured min 0
    report = DatasetValidator(cfg.data).validate(df)
    assert any(i.rule == "schema.below_min" for i in report.errors)
