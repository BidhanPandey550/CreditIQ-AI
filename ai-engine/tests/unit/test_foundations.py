"""Foundation tests: config system, schemas, enums, exceptions.

These validate the framework contracts before any module is built on top of them.
"""

from pathlib import Path

import pytest

from creditiq_ai.config import (
    EngineConfig,
    Environment,
    config_hash,
    detect_environment,
    load_config,
)
from creditiq_ai.core.enums import RiskCategory, ScoringStrategy
from creditiq_ai.core.exceptions import CreditIQError, ModelNotFittedError
from creditiq_ai.core.schemas import (
    ApplicantRecord,
    CreditScoreResult,
    ValidationReport,
)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def test_config_loads_from_yaml():
    cfg = load_config(CONFIG_DIR)
    assert isinstance(cfg, EngineConfig)
    assert cfg.scoring.min_score == 300
    assert cfg.scoring.max_score == 850
    assert cfg.scoring.strategy == ScoringStrategy.PROBABILITY_TO_SCORE


def test_config_has_full_model_zoo():
    cfg = load_config(CONFIG_DIR)
    enabled = {m.type.value for m in cfg.models.zoo if m.enabled}
    assert {"logistic_regression", "random_forest", "xgboost", "lightgbm", "catboost"} <= enabled


def test_config_hash_is_deterministic():
    cfg = load_config(CONFIG_DIR)
    assert config_hash(cfg) == config_hash(cfg)
    assert len(config_hash(cfg)) == 16


def test_env_override_beats_yaml(monkeypatch):
    # Development YAML sets DEBUG; an env override must win over it.
    monkeypatch.setenv("CREDITIQ_RUNTIME__LOG_LEVEL", "ERROR")
    cfg = load_config(CONFIG_DIR)
    assert cfg.runtime.log_level == "ERROR"


def test_environment_detection(monkeypatch):
    monkeypatch.setenv("CREDITIQ_ENV", "production")
    assert detect_environment() == Environment.PRODUCTION


def test_unknown_environment_raises(monkeypatch):
    monkeypatch.setenv("CREDITIQ_ENV", "staging")  # not a valid environment
    with pytest.raises(Exception):
        detect_environment()


def test_environment_specific_overrides():
    dev = load_config(CONFIG_DIR, environment=Environment.DEVELOPMENT)
    testing = load_config(CONFIG_DIR, environment=Environment.TESTING)
    prod = load_config(CONFIG_DIR, environment=Environment.PRODUCTION)
    assert dev.runtime.log_level == "DEBUG"
    assert testing.models.tuning_enabled is False  # testing disables tuning
    assert prod.runtime.log_json is True  # production emits JSON logs
    assert dev.environment == Environment.DEVELOPMENT


def test_config_is_immutable():
    cfg = load_config(CONFIG_DIR)
    with pytest.raises(Exception):
        cfg.runtime.log_level = "ERROR"  # frozen model


def test_applicant_record_accepts_partial_data():
    rec = ApplicantRecord(applicant_id="A1", monthly_income=50000)
    assert rec.applicant_id == "A1"
    assert rec.monthly_expenses is None


def test_credit_score_bounds_enforced():
    with pytest.raises(Exception):
        CreditScoreResult(score=900, band=RiskCategory.LOW, strategy="x")  # > 850


def test_validation_report_errors_property():
    report = ValidationReport(passed=True, n_rows=10, n_columns=3)
    assert report.errors == []


def test_exception_context():
    err = CreditIQError("boom", context={"k": "v"})
    assert "context" in str(err)
    assert issubclass(ModelNotFittedError, CreditIQError)
