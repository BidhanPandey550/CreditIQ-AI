"""Explainability — per-prediction SHAP attributions + a plain-language narrative.

Uses SHAP's TreeExplainer when available; otherwise falls back to a marginal-contribution
method (ablate each feature toward the training mean and measure the change in PD). Both
yield signed per-feature contributions in the same contract shape.
"""
from __future__ import annotations

import numpy as np

from src.features.synthetic import FEATURES

_HUMAN = {
    "debt_to_income": "debt-to-income ratio",
    "savings_ratio": "savings ratio",
    "income_stability": "income stability",
    "cashflow_volatility": "cash-flow volatility",
    "has_delinquency": "past delinquency",
}

try:  # optional dependency
    import shap  # type: ignore
    _HAS_SHAP = True
except Exception:  # pragma: no cover
    _HAS_SHAP = False


def contributions(model, x: list[float], train_means: list[float]) -> list[dict]:
    xv = np.array(x, dtype=float).reshape(1, -1)

    if _HAS_SHAP:
        try:
            explainer = shap.TreeExplainer(model)
            vals = explainer.shap_values(xv)
            arr = vals[1] if isinstance(vals, list) else vals
            impacts = np.array(arr).reshape(-1)[: len(FEATURES)]
            return _pack(impacts, x)
        except Exception:
            pass

    # Fallback: marginal contribution toward the population mean.
    base = model.predict_proba(np.array(train_means).reshape(1, -1))[0, 1]
    impacts = []
    for i in range(len(FEATURES)):
        perturbed = xv.copy()
        perturbed[0, i] = train_means[i]
        pd_without = model.predict_proba(perturbed)[0, 1]
        # Positive impact = increases default risk.
        impacts.append(float(model.predict_proba(xv)[0, 1] - pd_without))
    _ = base
    return _pack(np.array(impacts), x)


def _pack(impacts, x) -> list[dict]:
    out = [{"feature": FEATURES[i], "impact": round(float(impacts[i]), 4),
            "value": round(float(x[i]), 4)} for i in range(len(FEATURES))]
    out.sort(key=lambda d: abs(d["impact"]), reverse=True)
    return out


def narrative(band: str, contribs: list[dict]) -> str:
    """Faithful to SHAP semantics: describe the DIRECTION each feature pushed the model's
    risk estimate for this applicant — not a value judgement on whether the value is 'good'."""
    parts = [f"Overall risk assessed as {band.upper()}."]
    for c in contribs[:3]:
        name = _HUMAN.get(c["feature"], c["feature"])
        if c["impact"] > 0.01:
            parts.append(f"The {name} ({c['value']}) pushed the assessed default risk higher.")
        elif c["impact"] < -0.01:
            parts.append(f"The {name} ({c['value']}) pulled the assessed default risk lower.")
    return " ".join(parts)
