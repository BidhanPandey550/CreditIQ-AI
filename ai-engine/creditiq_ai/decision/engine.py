"""Unified Decision Engine (fix D2).

Purpose:  Compose the credit assessment (PD → credit score → risk band) and the fraud assessment
          (signals → 0–1000 fraud score → risk level) into ONE lending decision with confidence,
          reasons, versions, correlation ID, timing, warnings, and monitoring status.
Safety:   Model-integrity failures (ArtifactIntegrityError) BLOCK the decision (unsafe inference is
          never performed). A non-critical fraud-subsystem failure does NOT block — it degrades
          conservatively and is recorded as a warning (documented fallback policy).
DI:       credit predictor + fraud assessor are injected callables — no coupling to storage/registry.
Inputs:   EngineConfig + DecisionRequest.
Outputs:  UnifiedDecision.
Deps:     config; decision.{credit_score,policy,models}; fraud_intelligence scoring; exceptions.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

import pandas as pd

from creditiq_ai.config.models import EngineConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.decision.credit_score import CreditScoreMapper
from creditiq_ai.decision.models import DecisionRequest, UnifiedDecision
from creditiq_ai.decision.policy import DecisionPolicy
from creditiq_ai.exceptions import ArtifactIntegrityError
from creditiq_ai.fraud_intelligence import FraudScoringEngine, FraudSignals
from creditiq_ai.model_operations.monitoring import InferenceEvent, MonitoringSink

CreditPredictor = Callable[[pd.DataFrame], float]  # row → probability of default
FraudAssessor = Callable[[pd.DataFrame], FraudSignals]  # row → fraud signals


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


class DecisionEngine(BaseComponent):
    def __init__(
        self,
        config: EngineConfig,
        *,
        credit_predictor: CreditPredictor,
        fraud_assessor: FraudAssessor | None = None,
        monitor: MonitoringSink | None = None,
    ) -> None:
        super().__init__()
        self._cfg = config.decision
        self._score_mapper = CreditScoreMapper(config.scoring)
        self._fraud_scoring = FraudScoringEngine(config.fraud_intelligence.scoring)
        self._policy = DecisionPolicy(config.decision)
        self._credit_predictor = credit_predictor
        self._fraud_assessor = fraud_assessor
        self._monitor = monitor

    def decide(self, request: DecisionRequest) -> UnifiedDecision:
        started = time.perf_counter()
        correlation_id = request.correlation_id or str(uuid.uuid4())
        warnings: list[str] = []
        monitoring_status = "ok"
        row = request.row

        data_complete = all(
            f in row.columns and bool(row[f].notna().all()) for f in self._cfg.required_features
        )

        # --- Credit assessment (integrity failures block; other failures degrade) ---
        credit_ok = True
        try:
            pd_hat = _clamp01(float(self._credit_predictor(row)))
        except ArtifactIntegrityError:
            raise  # unsafe model → BLOCK, never decide
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(f"Credit prediction failed [{correlation_id}]: {exc}")
            credit_ok, pd_hat = False, 1.0
            warnings.append("credit_unavailable")

        credit_score = self._score_mapper.score(pd_hat)
        credit_band = self._score_mapper.band(credit_score)

        # --- Fraud assessment (non-blocking, except integrity) ---
        fraud_ok = self._fraud_assessor is not None
        fraud = None
        if self._fraud_assessor is not None:
            try:
                fraud = self._fraud_scoring.score(self._fraud_assessor(row))
            except ArtifactIntegrityError:
                raise  # unsafe fraud model → BLOCK
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(f"Fraud assessment failed [{correlation_id}]: {exc}")
                fraud_ok, monitoring_status = False, "degraded"
                warnings.append("fraud_unavailable")

        recommendation, reasons = self._policy.recommend(
            credit_band=credit_band,
            fraud_level=fraud.fraud_risk_level.value if fraud else None,
            credit_ok=credit_ok,
            fraud_ok=fraud_ok,
            data_complete=data_complete,
        )

        confidence = self._confidence(
            pd_hat, fraud.fraud_probability if fraud else None, credit_ok, fraud_ok
        )

        decision = UnifiedDecision(
            credit_score=credit_score,
            probability_of_default=round(pd_hat, 4),
            credit_risk=credit_band,
            fraud_score=fraud.fraud_score if fraud else None,
            fraud_probability=fraud.fraud_probability if fraud else None,
            fraud_risk=fraud.fraud_risk_level.value if fraud else None,
            recommendation=recommendation,
            confidence=confidence,
            decision_reasons=reasons,
            model_versions=request.model_versions,
            feature_version=request.feature_version,
            correlation_id=correlation_id,
            processing_duration_ms=round((time.perf_counter() - started) * 1000, 3),
            warnings=warnings,
            monitoring_status=monitoring_status,
        )
        self.logger.info(
            f"Decision [{correlation_id}]: {recommendation} (credit={credit_band}, "
            f"fraud={decision.fraud_risk}, conf={confidence})"
        )
        return self._record_monitoring(decision)

    def _record_monitoring(self, decision: UnifiedDecision) -> UnifiedDecision:
        """Record observability without allowing monitoring failure to block a safe decision."""
        if self._monitor is None:
            return decision
        try:
            self._monitor.record(
                InferenceEvent(
                    correlation_id=decision.correlation_id,
                    success=True,
                    duration_ms=decision.processing_duration_ms,
                    recommendation=decision.recommendation,
                    model_versions=decision.model_versions,
                    warning_codes=decision.warnings,
                )
            )
            return decision
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                f"Monitoring failed [{decision.correlation_id}] without blocking decision: {exc}"
            )
            warnings = [*decision.warnings, "monitoring_unavailable"]
            return decision.model_copy(
                update={"warnings": warnings, "monitoring_status": "degraded"}
            )

    def _confidence(
        self, pd_hat: float, fraud_prob: float | None, credit_ok: bool, fraud_ok: bool
    ) -> float:
        if not credit_ok:
            return 0.0
        credit_conf = _clamp01(2.0 * abs(pd_hat - 0.5))  # decisive PD → high confidence
        if fraud_ok and fraud_prob is not None:
            fraud_conf = _clamp01(2.0 * abs(fraud_prob - 0.5))
            w = self._cfg.confidence
            total = w.credit_weight + w.fraud_weight or 1.0
            return round((w.credit_weight * credit_conf + w.fraud_weight * fraud_conf) / total, 4)
        return round(credit_conf, 4)  # fraud unavailable → credit-only
