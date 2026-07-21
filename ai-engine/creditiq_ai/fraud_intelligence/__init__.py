"""creditiq_ai.fraud_intelligence — Enterprise Fraud Intelligence & Risk Anomaly Engine (Sprint 7).

Produces an INDEPENDENT fraud assessment alongside the credit engine, to be combined into a
unified lending decision. Anomaly detection reuses creditiq_ai.fraud (no duplication); this package
adds behaviour analysis, identity validation, rules, 0–1000 scoring, confidence, explainability,
reporting, and decision-engine integration.

Module 1 (config + scoring) public API:

    from creditiq_ai.config import load_config
    from creditiq_ai.fraud_intelligence import FraudScoringEngine, FraudSignals
    engine = FraudScoringEngine(load_config().fraud_intelligence.scoring)
    result = engine.score(FraudSignals(anomaly_probability=0.8, rule_penalty=0.6))
"""

from creditiq_ai.fraud_intelligence.models.results import (
    FraudRiskLevel,
    FraudScore,
    FraudSignals,
)
from creditiq_ai.fraud_intelligence.scoring.engine import FraudScoringEngine
from creditiq_ai.fraud_intelligence.behaviour_analysis import (
    BehaviourAnalyzer,
    BehaviourInput,
    BehaviourRiskProfile,
)
from creditiq_ai.fraud_intelligence.identity_validation import (
    IdentityValidationResult,
    IdentityValidator,
)
from creditiq_ai.fraud_intelligence.rule_engine import FraudRuleEngine

__all__ = [
    "BehaviourAnalyzer",
    "BehaviourInput",
    "BehaviourRiskProfile",
    "FraudRiskLevel",
    "FraudRuleEngine",
    "FraudScore",
    "FraudScoringEngine",
    "FraudSignals",
    "IdentityValidationResult",
    "IdentityValidator",
]
