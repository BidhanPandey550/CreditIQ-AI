"""Tests for Sprint 5 Module 1 — the Fraud Detection Framework + unsupervised detectors."""

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from creditiq_ai.config import load_config
from creditiq_ai.exceptions import ArtifactIntegrityError, FraudDetectionError
from creditiq_ai.fraud import (
    FraudDetectionFactory,
    FraudDetectionPipeline,
    FraudDetectionResult,
    available_detectors,
)
from creditiq_ai.fraud.algorithms.sklearn_detectors import IsolationForestDetector
from tests.fixtures.synthetic import make_credit_dataset

CONTINUOUS = [
    "monthly_income",
    "monthly_expenses",
    "monthly_debt_payments",
    "total_assets",
    "total_liabilities",
    "savings_balance",
]


def _reference_and_outlier(n: int = 300):
    df = make_credit_dataset(n)[CONTINUOUS]
    scaler = StandardScaler().fit(df)
    ref = pd.DataFrame(scaler.transform(df), columns=CONTINUOUS)
    normal = ref.iloc[[0]].reset_index(drop=True)
    outlier = pd.DataFrame([np.full(len(CONTINUOUS), 8.0)], columns=CONTINUOUS)  # far outside
    return ref, normal, outlier


# --------------------------------------------------------------------------- registry / factory
def test_registry_lists_all_five_detectors():
    assert set(available_detectors()) == {
        "isolation_forest",
        "local_outlier_factor",
        "one_class_svm",
        "elliptic_envelope",
        "dbscan",
    }


def test_factory_unknown_detector_raises():
    with pytest.raises(FraudDetectionError):
        FraudDetectionFactory.create("does_not_exist")


# --------------------------------------------------------------------------- single detector
def test_detector_scores_are_normalized():
    ref, _, _ = _reference_and_outlier()
    det = IsolationForestDetector({"n_estimators": 100, "contamination": 0.05, "random_state": 42})
    det.fit(ref)
    scores = det.score(ref)
    assert ((scores >= 0) & (scores <= 1)).all()


def test_detector_flags_outlier_higher_than_normal():
    ref, normal, outlier = _reference_and_outlier()
    det = IsolationForestDetector({"n_estimators": 100, "contamination": 0.05, "random_state": 42})
    det.fit(ref)
    assert det.score(outlier)[0] > det.score(normal)[0]
    assert bool(det.predict(outlier)[0]) is True


def test_detector_save_load_roundtrip(tmp_path):
    ref, _, outlier = _reference_and_outlier()
    det = IsolationForestDetector({"n_estimators": 100, "contamination": 0.05, "random_state": 42})
    det.fit(ref)
    path = tmp_path / "detector.joblib"
    artifact = det.save(path)
    reloaded = IsolationForestDetector.load_artifact(artifact)
    np.testing.assert_allclose(det.score(outlier), reloaded.score(outlier))


def test_detector_load_without_checksum_fails_closed(tmp_path):
    ref, _, _ = _reference_and_outlier()
    detector = IsolationForestDetector(
        {"n_estimators": 50, "contamination": 0.05, "random_state": 42}
    ).fit(ref)
    path = tmp_path / "detector.joblib"
    detector.save(path)
    with pytest.raises(ArtifactIntegrityError):
        IsolationForestDetector.load(path)


def test_unfitted_detector_raises():
    det = IsolationForestDetector({})
    with pytest.raises(Exception):
        det.score(pd.DataFrame([[0.0] * len(CONTINUOUS)], columns=CONTINUOUS))


# --------------------------------------------------------------------------- pipeline / contract
def test_pipeline_fits_all_configured_detectors():
    ref, _, _ = _reference_and_outlier()
    pipeline = FraudDetectionPipeline(load_config().fraud).fit(ref)
    assert set(pipeline.detector_names) == set(available_detectors())


def test_pipeline_analyze_returns_contract():
    ref, normal, outlier = _reference_and_outlier()
    pipeline = FraudDetectionPipeline(load_config().fraud).fit(ref)
    results = pipeline.analyze(pd.concat([normal, outlier], ignore_index=True))
    assert len(results) == 2
    for r in results:
        assert isinstance(r, FraudDetectionResult)
        assert 0.0 <= r.fraud_probability <= 1.0
        assert len(r.detector_breakdown) == 5
        assert 0.0 <= r.detector_agreement <= 1.0
        # later-module fields default empty/None (contract stays backward compatible)
        assert r.fraud_score is None and r.risk_flags == []


def test_pipeline_flags_extreme_outlier():
    ref, normal, outlier = _reference_and_outlier()
    pipeline = FraudDetectionPipeline(load_config().fraud).fit(ref)
    normal_res, outlier_res = pipeline.analyze(pd.concat([normal, outlier], ignore_index=True))
    assert outlier_res.fraud_probability > normal_res.fraud_probability
    assert outlier_res.anomaly_detected is True


def test_pipeline_skips_unregistered_detector():
    cfg = load_config().fraud.model_copy(
        update={
            "detectors": list(load_config().fraud.detectors)
            + [type(load_config().fraud.detectors[0])(type="graph_based", enabled=True, params={})]
        }
    )
    ref, _, _ = _reference_and_outlier()
    pipeline = FraudDetectionPipeline(cfg).fit(ref)
    assert "graph_based" not in pipeline.detector_names  # skipped, not implemented yet


def test_unfitted_pipeline_raises():
    _, normal, _ = _reference_and_outlier()
    with pytest.raises(FraudDetectionError):
        FraudDetectionPipeline(load_config().fraud).analyze(normal)
