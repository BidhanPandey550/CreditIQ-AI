"""Local-explainer framework (Strategy pattern).

Purpose:  Define the interface every local explainer implements and the DI container it receives.
          Explainers produce raw signed feature contributions; the service turns those into the
          frozen `core.schemas.Explanation` contract + a config-driven narrative.
Inputs:   an ExplanationContext (model access + data) and a single-row DataFrame.
Outputs:  RawContributions (base value + prediction + per-feature signed contributions).
Deps:     pandas, numpy; core.base.BaseComponent, core.schemas.FeatureContribution.
Extend:   subclass BaseLocalExplainer, implement supports()/explain(), register with a priority.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from creditiq_ai.core.base import BaseComponent
from creditiq_ai.core.schemas import FeatureContribution

# A model-agnostic predictor: rows → positive-class (default) probability in [0,1].
PredictProba = Callable[[pd.DataFrame], np.ndarray]


@dataclass(frozen=True)
class ExplanationContext:
    """Everything an explainer needs, injected (no globals, no model coupling)."""

    predict_proba: PredictProba
    feature_names: list[str]
    background: pd.DataFrame  # reference sample (baselines / SHAP background)
    model: Any = None  # raw estimator, for SHAP Tree/Linear explainers
    model_kind: str = "other"  # "linear" | "tree" | "other"
    model_version: str | None = None
    feature_version: str | None = None


@dataclass
class RawContributions:
    base_value: float
    prediction: float
    contributions: list[FeatureContribution] = field(default_factory=list)


class BaseLocalExplainer(BaseComponent):
    """Strategy: one way of attributing a single prediction to its features."""

    method: str = "base"

    @abstractmethod
    def supports(self, ctx: ExplanationContext) -> bool:
        """Whether this explainer can run for the given model/context."""

    @abstractmethod
    def explain(self, ctx: ExplanationContext, row: pd.DataFrame) -> RawContributions:
        """Attribute the single-row prediction to features (signed: + increases default risk)."""
