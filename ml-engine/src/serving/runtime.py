"""Serving adapter backed exclusively by the canonical ``creditiq_ai`` library."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

import pandas as pd

from creditiq_ai.config import load_config
from creditiq_ai.credit_intelligence.algorithms.logistic_regression import LogisticRegressionTrainer
from creditiq_ai.credit_intelligence.datasets.dataset import CreditDataset
from creditiq_ai.credit_intelligence.trainers.config import TrainingConfig
from creditiq_ai.credit_intelligence.trainers.context import TrainingContext
from creditiq_ai.decision import DecisionEngine, DecisionRequest
from creditiq_ai.explainability.services.local_service import LocalExplanationService, build_context
from creditiq_ai.fraud import FraudDetectionPipeline
from creditiq_ai.fraud_intelligence import FraudScoringEngine, FraudSignals
from creditiq_ai.model_operations import (
    ArtifactKind,
    ArtifactStore,
    FileModelRegistry,
    ModelFamily,
    ModelIdentity,
    InferenceEvent,
    InMemoryDecisionMonitor,
    MonitoringSnapshot,
)

from src.features.synthetic import FEATURES, generate, vectorize
from src.serving.bundle import ServingBundle
from src.serving.settings import ServingSettings

log = logging.getLogger("creditiq.ml_serving")


@dataclass
class CanonicalRuntime:
    trainer: LogisticRegressionTrainer
    fraud: FraudDetectionPipeline
    reference: pd.DataFrame
    version: str
    metrics: dict[str, float | int]
    stage: str
    data_source: str
    feature_version: str
    monitor: InMemoryDecisionMonitor

    @classmethod
    def train(cls) -> "CanonicalRuntime":
        """Build the deterministic synthetic runtime for development and tests only."""
        X_array, y_array = generate(n=2000)
        frame = pd.DataFrame(X_array, columns=FEATURES)
        labels = pd.Series(y_array, name="default")
        dataset = CreditDataset(frame, labels, name="synthetic-serving-baseline")
        trainer = LogisticRegressionTrainer(
            TrainingConfig(
                algorithm="logistic_regression",
                params={"max_iter": 1000, "random_state": 42},
                cv_folds=3,
                primary_metric="roc_auc",
                random_seed=42,
            )
        )
        result = trainer.train(TrainingContext(dataset=dataset, config=trainer.train_config))
        config = load_config()
        fraud = FraudDetectionPipeline(config.fraud).fit(frame)
        return cls(
            trainer=trainer,
            fraud=fraud,
            reference=frame,
            version=f"logistic-{dataset.version}",
            metrics={
                "roc_auc_cv": round(result.primary_score, 4),
                "n_train": dataset.n_rows,
                "default_rate": round(float(labels.mean()), 4),
            },
            stage="development",
            data_source="synthetic",
            feature_version="serving-features-v1",
            monitor=InMemoryDecisionMonitor(config.monitoring),
        )

    @classmethod
    def load_production(cls, settings: ServingSettings) -> "CanonicalRuntime":
        """Load the unique promoted bundle through checksum-verifying infrastructure."""
        if settings.environment != "production" or settings.registry_path is None:
            raise ValueError("Production loading requires validated production settings")
        identity = ModelIdentity(
            name=settings.model_name,
            family=ModelFamily.CREDIT,
            environment=settings.model_environment,
        )
        model = FileModelRegistry(settings.registry_path).production(identity)
        artifacts = [item for item in model.artifacts if item.kind is ArtifactKind.MODEL]
        if len(artifacts) != 1:
            raise ValueError("Production model must reference exactly one serving bundle")
        bundle = ArtifactStore().load_artifact(artifacts[0])
        if not isinstance(bundle, ServingBundle):
            raise TypeError("Production artifact is not a compatible ServingBundle")
        bundle.validate()
        return cls(
            trainer=bundle.trainer,
            fraud=bundle.fraud,
            reference=bundle.reference,
            version=model.version,
            metrics=bundle.metrics,
            stage=model.stage.value,
            data_source=model.lineage.dataset_version or "registered-dataset",
            feature_version=bundle.feature_version,
            monitor=InMemoryDecisionMonitor(load_config().monitoring),
        )

    @classmethod
    def create(cls, settings: ServingSettings) -> "CanonicalRuntime":
        """Select an explicit startup policy; production always fails closed."""
        if settings.environment == "production":
            return cls.load_production(settings)
        return cls.train()

    def predict(
        self, features: dict[str, object], *, correlation_id: str | None = None
    ) -> dict[str, object]:
        """Run inference and emit one privacy-safe operational event on every outcome."""
        started = time.perf_counter()
        event_id = correlation_id or str(uuid.uuid4())
        try:
            result = self._predict(features, correlation_id=event_id)
        except Exception:
            self._record_event(
                InferenceEvent(
                    correlation_id=event_id,
                    success=False,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    model_versions={"credit": self.version},
                    warning_codes=["inference_failed"],
                )
            )
            raise
        self._record_event(
            InferenceEvent(
                correlation_id=event_id,
                success=True,
                duration_ms=(time.perf_counter() - started) * 1000,
                recommendation=str(result["decision"]["recommendation"]),
                model_versions={"credit": self.version},
            )
        )
        return result

    def monitoring_snapshot(self) -> MonitoringSnapshot:
        """Expose aggregate process-local telemetry without applicant data."""
        return self.monitor.snapshot()

    def _record_event(self, event: InferenceEvent) -> None:
        try:
            self.monitor.record(event)
        except Exception:  # noqa: BLE001 - observability must not alter a valid decision
            log.exception("Inference monitoring backend failed")

    def _predict(self, features: dict[str, object], *, correlation_id: str) -> dict[str, object]:
        config = load_config()
        model_row = pd.DataFrame([vectorize(features)], columns=FEATURES)
        decision_row = pd.DataFrame([{**features, **model_row.iloc[0].to_dict()}])
        fraud_observation: dict[str, bool] = {}

        def predict_credit(row: pd.DataFrame) -> float:
            return float(self.trainer.predict_proba(row.loc[:, FEATURES])[0])

        def assess_fraud(row: pd.DataFrame) -> FraudSignals:
            anomaly = self.fraud.analyze(row.loc[:, FEATURES])[0]
            fraud_observation["anomaly_detected"] = anomaly.anomaly_detected
            return FraudSignals(anomaly_probability=anomaly.fraud_probability)

        decision = DecisionEngine(
            config,
            credit_predictor=predict_credit,
            fraud_assessor=assess_fraud,
        ).decide(
            DecisionRequest(
                row=decision_row,
                correlation_id=correlation_id,
                model_versions={"credit": self.version, "fraud": self.version},
                feature_version=self.feature_version,
            )
        )
        probability = decision.probability_of_default
        score = decision.credit_score
        detailed_band = decision.credit_risk
        band = {"very_low": "low", "very_high": "high"}.get(detailed_band, detailed_band)
        fraud_probability = decision.fraud_probability or 0.0
        fraud_score = FraudScoringEngine(config.fraud_intelligence.scoring).score(
            FraudSignals(anomaly_probability=fraud_probability)
        )
        backend_severity = {
            "very_low": "low",
            "low": "low",
            "moderate": "medium",
            "high": "high",
            "critical": "critical",
        }[fraud_score.fraud_risk_level.value]
        fraud_reasons = (
            ["Financial profile differs materially from the reference population"]
            if fraud_observation.get("anomaly_detected", False)
            else []
        )

        context = build_context(
            self.trainer,
            self.reference,
            model_version=self.version,
            feature_version=self.feature_version,
        )
        explanation = LocalExplanationService(config.explainability).explain(context, model_row)
        contributions = [
            {
                "feature": item.feature,
                "impact": round(item.contribution, 6),
                "value": round(float(item.value), 6),
            }
            for item in explanation.explanation.top_contributors
        ]
        return {
            "model_version": self.version,
            "risk": {"band": band, "probability": round(probability, 4)},
            "credit_score": {"score": score, "subscores": {}},
            "default": {"probability": round(probability, 4), "horizon_months": 12},
            "fraud": {
                "severity": backend_severity,
                "level": fraud_score.fraud_risk_level.value,
                "reasons": fraud_reasons,
                "anomaly_score": round(fraud_probability, 4),
                "score": fraud_score.fraud_score,
            },
            "explanation": {
                "contributions": contributions,
                "narrative": explanation.explanation.narrative,
            },
            "decision": decision.model_dump(mode="json"),
        }
