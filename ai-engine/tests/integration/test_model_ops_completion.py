from __future__ import annotations

import json

from creditiq_ai.config import config_hash, load_config
from creditiq_ai.core.enums import ModelType
from creditiq_ai.credit_intelligence.trainers.result import CrossValidationScore, TrainingResult
from creditiq_ai.model_operations import (
    ArtifactKind,
    AuditReportGenerator,
    FileModelRegistry,
    LocalExperimentTracker,
    ModelArtifact,
    TrainingRegistrationService,
)


def test_experiment_training_registration_and_audit_export(tmp_path):
    tracker = LocalExperimentTracker(tmp_path / "experiments.json")
    run = tracker.start("credit-training", parameters={"folds": 5}, tags={"tenant": "demo"})
    completed = tracker.finish(run.run_id, metrics={"roc_auc": 0.82})
    assert completed.status == "completed"
    assert tracker.list_runs() == [completed]

    registry = FileModelRegistry(tmp_path / "registry.json")
    result = TrainingResult(
        algorithm="logistic_regression",
        params={"C": 1.0},
        primary_metric="roc_auc",
        primary_score=0.82,
        cv=CrossValidationScore(metric="roc_auc", mean=0.82, std=0.02, folds=[0.8, 0.84]),
        n_train=100,
        n_features=2,
        dataset_version="dataset@1",
        duration_seconds=1.2,
        feature_names=["income", "debt"],
    )
    artifact = ModelArtifact(
        kind=ArtifactKind.MODEL,
        path="credit.joblib",
        checksum_sha256="a" * 64,
    )
    registered = TrainingRegistrationService(registry).register(
        result,
        artifact,
        name="credit-risk",
        version="1.0.0",
        environment="production",
        config_hash=config_hash(load_config()),
        feature_schema_version="features@1",
    )
    assert registered.metadata.model_type is ModelType.LOGISTIC_REGRESSION
    assert registered.lineage.dataset_version == "dataset@1"

    paths = AuditReportGenerator().generate(registry.audit_events(), tmp_path / "audit")
    assert {path.suffix for path in paths} == {".json", ".md"}
    assert json.loads(paths[0].read_text())[0]["event_type"] == "model_registered"
