"""creditiq_ai.explainability — Explainable AI & Decision Transparency Engine (Sprint 6).

Module 1 (Local Explanations + SHAP w/ graceful fallback) public API. Importing this package
registers the built-in explainers.

    from creditiq_ai.config import load_config
    from creditiq_ai.explainability import LocalExplanationService, build_context
    cfg = load_config()
    ctx = build_context(trainer, background_df)
    service = LocalExplanationService(cfg.explainability)
    result = service.explain(ctx, applicant_row)      # LocalExplanation
"""

# Import explainer modules so they register with the registry.
from creditiq_ai.explainability.explainers import marginal  # noqa: F401
from creditiq_ai.explainability.explainers.base import (
    ExplanationContext,
    RawContributions,
)
from creditiq_ai.explainability.explainers.factory import ExplainerFactory
from creditiq_ai.explainability.explainers.registry import (
    available_explainers,
    register,
)
from creditiq_ai.explainability.explainers.result import LocalExplanation
from creditiq_ai.explainability.services.local_service import (
    LocalExplanationService,
    build_context,
)
from creditiq_ai.explainability.shap import shap_explainer  # noqa: F401

__all__ = [
    "LocalExplanationService",
    "build_context",
    "ExplanationContext",
    "RawContributions",
    "LocalExplanation",
    "ExplainerFactory",
    "register",
    "available_explainers",
]
