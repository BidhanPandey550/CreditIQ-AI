"""D1 regression tests — model artifacts are never deserialized without integrity verification."""

import pytest

from creditiq_ai.credit_intelligence import CreditDataset, TrainingConfig, TrainingContext
from creditiq_ai.credit_intelligence.algorithms.logistic_regression import (
    LogisticRegressionTrainer,
)
from creditiq_ai.exceptions import ArtifactIntegrityError
from creditiq_ai.model_operations import ArtifactStore
from creditiq_ai.model_operations.domain import ArtifactKind
from tests.fixtures.synthetic import make_credit_dataset


def test_save_returns_checksummed_artifact(tmp_path):
    store = ArtifactStore()
    artifact = store.save({"weights": [1, 2, 3]}, tmp_path / "m.joblib")
    assert artifact.checksum_sha256 and len(artifact.checksum_sha256) == 64
    assert artifact.serialization_format == "joblib"
    assert artifact.size_bytes > 0


def test_verified_load_roundtrip(tmp_path):
    store = ArtifactStore()
    artifact = store.save({"a": 1}, tmp_path / "m.joblib")
    assert store.load_artifact(artifact) == {"a": 1}


def test_missing_artifact_raises(tmp_path):
    with pytest.raises(ArtifactIntegrityError):
        ArtifactStore().load(tmp_path / "nope.joblib", "0" * 64)


def test_wrong_checksum_raises(tmp_path):
    store = ArtifactStore()
    store.save({"a": 1}, tmp_path / "m.joblib")
    with pytest.raises(ArtifactIntegrityError):
        store.load(tmp_path / "m.joblib", "deadbeef" * 8)


def test_tampered_artifact_is_blocked(tmp_path):
    """Corrupting the file after save must block the load (unsafe deserialization prevented)."""
    store = ArtifactStore()
    path = tmp_path / "m.joblib"
    artifact = store.save({"a": 1}, path)
    path.write_bytes(path.read_bytes() + b"tampered")  # corrupt the artifact
    with pytest.raises(ArtifactIntegrityError):
        store.load_artifact(artifact)


def test_unsupported_format_rejected(tmp_path):
    with pytest.raises(ArtifactIntegrityError):
        ArtifactStore().save({"a": 1}, tmp_path / "m.txt")


def test_missing_checksum_refuses_to_load(tmp_path):
    from creditiq_ai.model_operations.domain import ModelArtifact

    store = ArtifactStore()
    store.save({"a": 1}, tmp_path / "m.joblib")
    art = ModelArtifact(kind=ArtifactKind.MODEL, path=str(tmp_path / "m.joblib"))  # no checksum
    with pytest.raises(ArtifactIntegrityError):
        store.load_artifact(art)


def test_real_trained_model_integrity_load(tmp_path):
    df = make_credit_dataset(120)
    X, y = df.drop(columns=["applicant_id", "default"]), df["default"]
    cfg = TrainingConfig(algorithm="logistic_regression", params={"max_iter": 500}, cv_folds=2)
    trainer = LogisticRegressionTrainer(cfg)
    trainer.train(TrainingContext(dataset=CreditDataset(X, y), config=cfg))

    store = ArtifactStore()
    artifact = store.save(trainer, tmp_path / "credit.joblib")
    reloaded = store.load_artifact(artifact)  # verified load
    import numpy as np

    np.testing.assert_allclose(
        trainer.predict_proba(X.iloc[[0]]), reloaded.predict_proba(X.iloc[[0]])
    )
