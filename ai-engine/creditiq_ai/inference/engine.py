"""Enterprise inference composition service."""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np
import pandas as pd

from creditiq_ai.config.models import EngineConfig
from creditiq_ai.decision import DecisionEngine, DecisionRequest
from creditiq_ai.decision.engine import FraudAssessor
from creditiq_ai.explainability.services.local_service import LocalExplanationService, build_context
from creditiq_ai.inference.models import InferenceRequest, InferenceResponse
from creditiq_ai.inference.validator import InferenceValidator
from creditiq_ai.model_operations.monitoring import MonitoringSink


class Predictor(Protocol):
    algorithm: str

    def predict_proba(self, frame: pd.DataFrame) -> Any: ...


class Transformer(Protocol):
    def transform(self, frame: pd.DataFrame) -> pd.DataFrame: ...


class EnterpriseInferenceEngine:
    """Compose validation, preprocessing, credit/fraud decisioning and optional local XAI."""

    def __init__(
        self,
        config: EngineConfig,
        *,
        credit_model: Predictor,
        explanation_background: pd.DataFrame,
        preprocessor: Transformer | None = None,
        fraud_assessor: FraudAssessor | None = None,
        monitor: MonitoringSink | None = None,
        validator: InferenceValidator | None = None,
    ) -> None:
        self._config = config
        self._model = credit_model
        self._preprocessor = preprocessor
        self._background = explanation_background
        self._validator = validator or InferenceValidator(
            required=config.decision.required_features
        )
        self._explanations = LocalExplanationService(config.explainability)
        self._decision = DecisionEngine(
            config,
            credit_predictor=self._predict,
            fraud_assessor=fraud_assessor,
            monitor=monitor,
        )

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        raw = self._validator.validate(request.features)
        processed = self._preprocessor.transform(raw) if self._preprocessor else raw
        decision = self._decision.decide(
            DecisionRequest(
                row=processed,
                correlation_id=request.correlation_id,
                model_versions=request.model_versions,
                feature_version=request.feature_version,
            )
        )
        explanation = None
        if request.include_explanation:
            context = build_context(
                self._model,
                self._background,
                model_version=request.model_versions.get("credit"),
                feature_version=request.feature_version,
            )
            explanation = self._explanations.explain(context, processed)
        return InferenceResponse(
            decision=decision,
            explanation=explanation,
            processed_features=list(processed.columns),
        )

    def infer_many(self, requests: list[InferenceRequest]) -> list[InferenceResponse]:
        """Process independently auditable requests while preserving caller order."""
        return [self.infer(request) for request in requests]

    def _predict(self, frame: pd.DataFrame) -> float:
        probabilities = np.asarray(self._model.predict_proba(frame))
        if probabilities.ndim == 2:
            probabilities = probabilities[:, 1]
        return float(probabilities[0])
