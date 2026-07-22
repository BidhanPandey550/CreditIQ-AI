"""Contract tests for the canonical ML serving adapter."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from creditiq_ai.core.enums import ModelType
from creditiq_ai.core.schemas import ModelMetadata
from creditiq_ai.exceptions import ArtifactIntegrityError, ModelNotFoundError
from creditiq_ai.model_operations import (
    ArtifactStore,
    FileModelRegistry,
    LifecycleStage,
    ModelFamily,
    ModelIdentity,
    ModelLineage,
    ModelVersion,
)

from src.serving.main import app
from src.serving.bundle import ServingBundle
from src.serving.runtime import CanonicalRuntime
from src.serving.settings import ServingSettings


@pytest.fixture(scope="module")
def runtime() -> CanonicalRuntime:
    """Train the deterministic development runtime once for this module."""
    return CanonicalRuntime.train()


def test_runtime_prediction_uses_enterprise_contract(runtime: CanonicalRuntime) -> None:
    before = runtime.monitoring_snapshot()
    result = runtime.predict(
        {
            "debt_to_income": 0.3,
            "savings_ratio": 0.2,
            "income_stability": 0.8,
            "cashflow_volatility": 0.2,
            "has_delinquency": False,
            "monthly_income": 100000,
            "monthly_expenses": 40000,
        }
    )

    assert 300 <= result["credit_score"]["score"] <= 850
    assert 0.0 <= result["default"]["probability"] <= 1.0
    assert 0 <= result["fraud"]["score"] <= 1000
    assert result["fraud"]["severity"] in {
        "very_low",
        "low",
        "moderate",
        "high",
        "critical",
    }
    assert result["model_version"].startswith("logistic-")
    assert result["explanation"]["contributions"]
    assert result["explanation"]["narrative"]
    assert result["decision"]["recommendation"] in {
        "approve",
        "review",
        "manual_review",
        "reject",
    }
    assert result["decision"]["correlation_id"]
    assert 0.0 <= result["decision"]["confidence"] <= 1.0
    after = runtime.monitoring_snapshot()
    assert after.prediction_count == before.prediction_count + 1
    assert after.failure_count == before.failure_count


def test_http_contract_and_model_disclosure(runtime: CanonicalRuntime, monkeypatch) -> None:
    monkeypatch.setattr("src.serving.main.runtime", runtime)
    with TestClient(app) as client:
        health = client.get("/health")
        models = client.get("/models")
        prediction = client.post(
            "/predict",
            headers={"X-Request-ID": "trace-123"},
            json={
                "features": {
                    "debt_to_income": 0.4,
                    "savings_ratio": 0.1,
                    "income_stability": 0.6,
                    "cashflow_volatility": 0.3,
                    "has_delinquency": False,
                    "monthly_income": 100000,
                    "monthly_expenses": 40000,
                }
            },
        )
        monitoring = client.get("/monitoring")

    assert health.status_code == 200
    assert models.status_code == 200
    assert models.json()["stage"] == "development"
    assert models.json()["data_source"] == "synthetic"
    assert prediction.status_code == 200
    assert prediction.headers["X-Request-ID"] == "trace-123"
    assert 300 <= prediction.json()["credit_score"]["score"] <= 850
    assert monitoring.status_code == 200
    assert monitoring.json()["prediction_count"] >= 1
    assert "monitoring" in health.json()


def test_predict_rejects_empty_and_unknown_request_fields(runtime, monkeypatch) -> None:
    monkeypatch.setattr("src.serving.main.runtime", runtime)
    with TestClient(app) as client:
        assert client.post("/predict", json={"features": {}}).status_code == 422
        assert (
            client.post(
                "/predict",
                json={"features": {"debt_to_income": 0.4}, "unexpected": True},
            ).status_code
            == 422
        )


def _register_production_bundle(tmp_path, runtime: CanonicalRuntime) -> ServingSettings:
    artifact = ArtifactStore().save(
        ServingBundle(
            trainer=runtime.trainer,
            fraud=runtime.fraud,
            reference=runtime.reference,
            feature_version=runtime.feature_version,
            metrics=runtime.metrics,
        ),
        tmp_path / "credit-risk-v1.joblib",
    )
    registry = FileModelRegistry(tmp_path / "registry.json")
    model = registry.register(
        ModelVersion(
            identity=ModelIdentity(
                name="credit-risk", family=ModelFamily.CREDIT, environment="production"
            ),
            version="1.0.0",
            metadata=ModelMetadata(
                name="credit-risk",
                version="1.0.0",
                model_type=ModelType.LOGISTIC_REGRESSION,
                features=list(runtime.reference.columns),
                metrics={"roc_auc": float(runtime.metrics["roc_auc_cv"])},
            ),
            artifacts=[artifact],
            lineage=ModelLineage(
                dataset_version="repayment-outcomes-2026-07",
                feature_schema_version=runtime.feature_version,
            ),
        )
    )
    for stage in (
        LifecycleStage.VALIDATED,
        LifecycleStage.STAGING,
        LifecycleStage.CHALLENGER,
        LifecycleStage.CHAMPION,
        LifecycleStage.PRODUCTION,
    ):
        model = registry.transition(model.ref, stage)
    return ServingSettings(
        environment="production",
        registry_path=tmp_path / "registry.json",
        model_name="credit-risk",
        model_environment="production",
        monitoring_backend="redis",
        redis_url="redis://monitoring.invalid/1",
    )


def test_production_settings_require_registry() -> None:
    with pytest.raises(ValidationError, match="ML_SERVING_REGISTRY_PATH"):
        ServingSettings(environment="production")


def test_production_settings_require_shared_monitoring(tmp_path) -> None:
    with pytest.raises(ValidationError, match="MONITORING_BACKEND=redis"):
        ServingSettings(environment="production", registry_path=tmp_path / "registry.json")


def test_production_runtime_loads_only_promoted_verified_bundle(
    tmp_path, runtime, monkeypatch
) -> None:
    settings = _register_production_bundle(tmp_path, runtime)
    monkeypatch.setattr(
        "src.serving.runtime.create_redis_monitor", lambda *args, **kwargs: runtime.monitor
    )

    loaded = CanonicalRuntime.create(settings)

    assert loaded.version == "1.0.0"
    assert loaded.stage == "production"
    assert loaded.data_source == "repayment-outcomes-2026-07"
    assert loaded.feature_version == "serving-features-v1"


def test_production_runtime_rejects_missing_promotion(tmp_path) -> None:
    settings = ServingSettings(
        environment="production",
        registry_path=tmp_path / "missing-registry.json",
        monitoring_backend="redis",
        redis_url="redis://monitoring.invalid/1",
    )
    with pytest.raises(ModelNotFoundError):
        CanonicalRuntime.create(settings)


def test_production_runtime_blocks_tampered_artifact(tmp_path, runtime) -> None:
    settings = _register_production_bundle(tmp_path, runtime)
    artifact_path = tmp_path / "credit-risk-v1.joblib"
    artifact_path.write_bytes(artifact_path.read_bytes() + b"tampered")

    with pytest.raises(ArtifactIntegrityError, match="checksum mismatch"):
        CanonicalRuntime.create(settings)


def test_failed_inference_is_recorded_without_features(runtime) -> None:
    before = runtime.monitoring_snapshot()

    with pytest.raises(ValueError):
        runtime.predict({"debt_to_income": "not-a-number"}, correlation_id="failure-123")

    after = runtime.monitoring_snapshot()
    assert after.prediction_count == before.prediction_count + 1
    assert after.failure_count == before.failure_count + 1
    assert not hasattr(after, "features")


def test_monitoring_failure_does_not_block_valid_inference(runtime, monkeypatch) -> None:
    def unavailable(event) -> None:
        raise RuntimeError("telemetry unavailable")

    monkeypatch.setattr(runtime.monitor, "record", unavailable)

    result = runtime.predict({"debt_to_income": 0.3})

    assert 300 <= result["credit_score"]["score"] <= 850
