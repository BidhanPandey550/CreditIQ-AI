"""Tests for drift, performance, health, alerts, lineage and lifecycle services."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.core.enums import ModelType
from creditiq_ai.core.schemas import ModelMetadata
from creditiq_ai.exceptions import (
    AlertError,
    DriftDetectionError,
    LineageError,
    PromotionRejectedError,
)
from creditiq_ai.model_operations import (
    AlertManager,
    ArtifactKind,
    FileModelRegistry,
    InferenceEvent,
    InMemoryDecisionMonitor,
    LifecycleStage,
    LineageGraph,
    ModelArtifact,
    ModelFamily,
    ModelHealthService,
    ModelIdentity,
    ModelLineage,
    ModelVersion,
    PerformanceMonitor,
    PopulationStabilityDetector,
    PromotionPolicy,
    PromotionService,
)


def _config(**updates) -> MonitoringConfig:
    base = MonitoringConfig(
        minimum_drift_samples=20,
        minimum_performance_samples=20,
        promotion_required_metrics={"roc_auc": 0.7},
        promotion_max_metric_drop={"roc_auc": 0.02},
    )
    return base.model_copy(update=updates)


def _model(version: str, auc: float, parent: str | None = None) -> ModelVersion:
    return ModelVersion(
        identity=ModelIdentity(name="credit", family=ModelFamily.CREDIT),
        version=version,
        metadata=ModelMetadata(
            name="credit",
            version=version,
            model_type=ModelType.LOGISTIC_REGRESSION,
            metrics={"roc_auc": auc},
        ),
        artifacts=[
            ModelArtifact(
                kind=ArtifactKind.MODEL,
                path=f"credit-{version}.joblib",
                checksum_sha256="a" * 64,
            )
        ],
        lineage=ModelLineage(parent_version=parent),
    )


def _to_champion(registry: FileModelRegistry, model: ModelVersion) -> ModelVersion:
    result = registry.register(model)
    for stage in (
        LifecycleStage.VALIDATED,
        LifecycleStage.STAGING,
        LifecycleStage.CHALLENGER,
        LifecycleStage.CHAMPION,
    ):
        result = registry.transition(result.ref, stage)
    return result


def test_population_stability_detects_shift_and_stable_feature():
    rng = np.random.default_rng(42)
    reference = pd.DataFrame({"stable": rng.normal(0, 1, 500), "shifted": rng.normal(0, 1, 500)})
    current = pd.DataFrame({"stable": rng.normal(0, 1, 500), "shifted": rng.normal(4, 1, 500)})
    report = PopulationStabilityDetector(_config()).analyze(reference, current)
    assert report.status == "critical"
    assert "shifted" in report.drifted_features
    assert next(item for item in report.features if item.feature == "stable").status == "stable"


def test_population_stability_rejects_insufficient_or_non_numeric_data():
    detector = PopulationStabilityDetector(_config())
    with pytest.raises(DriftDetectionError):
        detector.analyze(pd.DataFrame({"x": [1]}), pd.DataFrame({"x": [1]}))
    with pytest.raises(DriftDetectionError):
        detector.analyze(pd.DataFrame({"x": ["a"] * 20}), pd.DataFrame({"x": ["b"] * 20}))


def test_performance_monitor_and_health_alert_lifecycle():
    config = _config()
    probabilities = np.array([0.05, 0.1, 0.2, 0.3, 0.6, 0.7, 0.8, 0.9] * 3)
    labels = np.array([0, 0, 0, 1, 0, 1, 1, 1] * 3)
    performance = PerformanceMonitor(config).evaluate(labels, probabilities, baseline=1.0)
    monitor = InMemoryDecisionMonitor(config)
    monitor.record(InferenceEvent(correlation_id="c1", success=True, duration_ms=10))
    health = ModelHealthService().evaluate(monitor.snapshot(), performance=performance)
    assert health.status in {"warning", "critical"}

    manager = AlertManager()
    alert = manager.from_health("credit@1", health)
    assert alert is not None
    assert manager.from_health("credit@1", health) == alert
    assert manager.acknowledge(alert.alert_id).status == "acknowledged"
    assert manager.list(status="open") == []
    with pytest.raises(AlertError):
        manager.acknowledge("missing")


def test_lineage_graph_traverses_and_rejects_invalid_parent():
    graph = LineageGraph([_model("1", 0.8), _model("2", 0.81, "1"), _model("3", 0.82, "2")])
    assert [item.version for item in graph.ancestors("3")] == ["2", "1"]
    assert [item.version for item in graph.children("1")] == ["2"]
    with pytest.raises(LineageError):
        LineageGraph([_model("2", 0.8, "missing")])


def test_promotion_policy_promotes_and_blocks_weak_candidate(tmp_path):
    registry = FileModelRegistry(tmp_path / "registry.json")
    service = PromotionService(registry, PromotionPolicy(_config()))
    champion = _to_champion(registry, _model("1", 0.82))
    production, decision = service.promote(champion.ref, reason="validated release")
    assert decision.approved
    assert production.stage is LifecycleStage.PRODUCTION

    weak = _to_champion(registry, _model("2", 0.6, "1"))
    with pytest.raises(PromotionRejectedError):
        service.promote(weak.ref)


def test_promotion_replaces_incumbent_in_one_registry_operation(tmp_path):
    registry = FileModelRegistry(tmp_path / "registry.json")
    service = PromotionService(registry, PromotionPolicy(_config()))
    first = _to_champion(registry, _model("1", 0.8))
    service.promote(first.ref)
    second = _to_champion(registry, _model("2", 0.81, "1"))

    production, _ = service.promote(second.ref)

    assert production.version == "2"
    assert registry.get(first.ref).stage is LifecycleStage.CHAMPION
    assert registry.audit_events()[-1].event_type == "model_promoted"
