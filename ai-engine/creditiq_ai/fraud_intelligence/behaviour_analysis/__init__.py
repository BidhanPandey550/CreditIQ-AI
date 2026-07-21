"""Financial behaviour risk profiling."""

from creditiq_ai.fraud_intelligence.behaviour_analysis.analyzer import BehaviourAnalyzer
from creditiq_ai.fraud_intelligence.behaviour_analysis.models import (
    BehaviourInput,
    BehaviourRiskProfile,
)

__all__ = ["BehaviourAnalyzer", "BehaviourInput", "BehaviourRiskProfile"]
