"""End-to-end fraud assessment composition."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from creditiq_ai.config.models import EngineConfig
from creditiq_ai.fraud import FraudDetectionPipeline
from creditiq_ai.fraud_intelligence.behaviour_analysis import BehaviourAnalyzer, BehaviourInput
from creditiq_ai.fraud_intelligence.confidence import FraudConfidenceEngine, FraudConfidenceInputs
from creditiq_ai.fraud_intelligence.explainability import FraudExplanationService
from creditiq_ai.fraud_intelligence.identity_validation import DuplicateCheck, IdentityValidator
from creditiq_ai.fraud_intelligence.models.results import FraudAssessment, FraudSignals
from creditiq_ai.fraud_intelligence.reporting import FraudReportGenerator
from creditiq_ai.fraud_intelligence.rule_engine import FraudRuleEngine
from creditiq_ai.fraud_intelligence.scoring.engine import FraudScoringEngine


@dataclass(frozen=True)
class FraudRequest:
    anomaly_features: pd.DataFrame
    behaviour: BehaviourInput
    identity: Mapping[str, Any]
    application: Mapping[str, Any]
    model_version: str
    score_stability: float = 1.0
    feature_quality: float = 1.0


class EnterpriseFraudPipeline:
    def __init__(
        self,
        config: EngineConfig,
        detector_pipeline: FraudDetectionPipeline,
        *,
        duplicate_check: DuplicateCheck | None = None,
    ) -> None:
        self.config = config.fraud_intelligence
        self.detectors = detector_pipeline
        self.behaviour = BehaviourAnalyzer(self.config.behaviour)
        self.identity = IdentityValidator(self.config.identity, duplicate_check=duplicate_check)
        self.rules = FraudRuleEngine(self.config.rules)
        self.scoring = FraudScoringEngine(self.config.scoring)
        self.confidence = FraudConfidenceEngine(self.config.confidence)
        self.explanations = FraudExplanationService(self.config.explainability)

    def analyze(
        self, request: FraudRequest, *, report_directory: str | Path | None = None
    ) -> FraudAssessment:
        anomaly = self.detectors.analyze(request.anomaly_features)
        if len(anomaly) != 1:
            raise ValueError("FraudRequest must contain exactly one anomaly feature row")
        anomaly_result = anomaly[0]
        behaviour = self.behaviour.analyze(request.behaviour)
        identity = self.identity.validate(request.identity)
        rules = self.rules.evaluate(request.application)
        rule_penalty = max(
            identity.risk_score,
            len(rules.triggered) / max(1, len(rules.results)),
        )
        score = self.scoring.score(
            FraudSignals(
                anomaly_probability=anomaly_result.fraud_probability,
                rule_penalty=rule_penalty,
                behaviour_risk=behaviour.risk_score,
            )
        )
        confidence = self.confidence.assess(
            FraudConfidenceInputs(
                detector_agreement=anomaly_result.detector_agreement,
                data_completeness=behaviour.data_completeness,
                feature_quality=request.feature_quality,
                score_stability=request.score_stability,
                rule_agreement=1.0 if not rules.triggered else rule_penalty,
            )
        )
        explanations = self.explanations.explain(
            anomaly=anomaly_result,
            behaviour=behaviour,
            identity=identity,
            rules=rules,
            score=score,
            confidence=confidence.score,
        )
        actions = [score.recommended_action, rules.recommended_action]
        action = max(
            actions,
            key=lambda value: self.config.action_priority.index(value)
            if value in self.config.action_priority
            else -1,
        )
        flags = [*identity.flags, *(item.rule_name for item in rules.triggered)]
        if anomaly_result.anomaly_detected:
            flags.insert(0, "anomaly_detected")
        assessment = FraudAssessment(
            fraud_probability=score.fraud_probability,
            fraud_score=score.fraud_score,
            fraud_level=score.fraud_risk_level,
            anomaly_detected=anomaly_result.anomaly_detected,
            confidence_score=confidence.score,
            confidence_level=confidence.level,
            risk_flags=flags,
            explanations=[item.model_dump() for item in explanations],
            recommended_action=action,
            detector_breakdown=anomaly_result.detector_breakdown,
            behaviour_summary=behaviour.indicators,
            identity_risk=identity.risk_score,
            model_version=request.model_version,
            warnings=[*behaviour.warnings, *rules.warnings],
        )
        if report_directory is not None:
            FraudReportGenerator().generate(assessment, report_directory)
        return assessment
