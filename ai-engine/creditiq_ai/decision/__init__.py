"""creditiq_ai.decision — Unified Decision Engine (fix D2).

Combines the credit assessment (PD → score → risk) and the fraud assessment (signals → 0–1000
score → risk) into one lending decision. Integrity failures block; fraud failures degrade safely.

    from creditiq_ai.config import load_config
    from creditiq_ai.decision import DecisionEngine, DecisionRequest
    engine = DecisionEngine(load_config(), credit_predictor=pred, fraud_assessor=assess)
    decision = engine.decide(DecisionRequest(row=applicant_row))
"""

from creditiq_ai.decision.credit_score import CreditScoreMapper
from creditiq_ai.decision.engine import DecisionEngine
from creditiq_ai.decision.models import DecisionRequest, UnifiedDecision
from creditiq_ai.decision.policy import DecisionPolicy

__all__ = [
    "DecisionEngine",
    "DecisionRequest",
    "UnifiedDecision",
    "CreditScoreMapper",
    "DecisionPolicy",
]
