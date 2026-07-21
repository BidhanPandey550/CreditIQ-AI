from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from creditiq_ai.config import load_config
from creditiq_ai.fraud_intelligence import FraudSignals
from creditiq_ai.inference import EnterpriseInferenceEngine, InferenceRequest, InferenceValidator
from creditiq_ai.model_operations import InMemoryDecisionMonitor
from creditiq_ai.exceptions import ValidationError


class DeterministicCreditModel:
    algorithm = "logistic_regression"

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probability = np.clip(
            frame["monthly_expenses"].to_numpy() / frame["monthly_income"].to_numpy(), 0, 1
        )
        return np.column_stack([1 - probability, probability])


def _engine():
    config = load_config()
    background = pd.DataFrame(
        {
            "monthly_income": [50000.0, 80000.0, 100000.0],
            "monthly_expenses": [15000.0, 25000.0, 30000.0],
        }
    )
    monitor = InMemoryDecisionMonitor(config.monitoring)
    engine = EnterpriseInferenceEngine(
        config,
        credit_model=DeterministicCreditModel(),
        explanation_background=background,
        fraud_assessor=lambda _: FraudSignals(
            anomaly_probability=0.05, rule_penalty=0.0, behaviour_risk=0.1
        ),
        monitor=monitor,
    )
    return engine, monitor


def test_enterprise_inference_returns_decision_explanation_and_monitoring():
    engine, monitor = _engine()
    response = engine.infer(
        InferenceRequest(
            features={"monthly_income": 100000.0, "monthly_expenses": 20000.0},
            correlation_id="request-1",
            model_versions={"credit": "credit@1", "fraud": "fraud@1"},
            feature_version="features@1",
        )
    )
    assert response.decision.correlation_id == "request-1"
    assert response.decision.probability_of_default == 0.2
    assert response.decision.fraud_score is not None
    assert response.explanation is not None
    assert response.explanation.model_version == "credit@1"
    assert monitor.snapshot().prediction_count == 1


def test_batch_inference_preserves_order_and_can_disable_xai():
    engine, _ = _engine()
    responses = engine.infer_many(
        [
            InferenceRequest(
                features={"monthly_income": 100000.0, "monthly_expenses": expense},
                correlation_id=f"request-{index}",
                include_explanation=False,
            )
            for index, expense in enumerate([10000.0, 40000.0])
        ]
    )
    assert [item.decision.correlation_id for item in responses] == ["request-0", "request-1"]
    assert all(item.explanation is None for item in responses)


def test_inference_validator_rejects_missing_and_unknown_features():
    validator = InferenceValidator(required=["income"], expected=["income"])
    with pytest.raises(ValidationError):
        validator.validate({})
    with pytest.raises(ValidationError):
        validator.validate({"income": 1, "secret": "value"})
