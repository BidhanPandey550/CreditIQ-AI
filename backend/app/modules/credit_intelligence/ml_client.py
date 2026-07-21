"""Anti-corruption layer to the separate ml-engine service.

If the ML engine is unreachable (timeout / down), we fall back to a transparent local
heuristic so the platform keeps working — matching the circuit-breaker design in the
architecture. The fallback is clearly labelled model_version='local-fallback'.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("ml_client")


class MLClient:
    def __init__(self) -> None:
        self.base_url = settings.ml_engine_url.rstrip("/")
        self.timeout = settings.ml_engine_timeout_seconds

    def predict(self, features: dict) -> dict:
        """Return risk, credit_score, default, fraud, explanation for a feature vector."""
        try:
            resp = httpx.post(f"{self.base_url}/predict", json={"features": features},
                              timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # pragma: no cover - network dependent
            log.warning("ML engine unavailable (%s); using local fallback", exc)
            return self._local_fallback(features)

    # --- Deterministic heuristic fallback (interpretable, no external dependency) ---
    def _local_fallback(self, f: dict) -> dict:
        dti = float(f.get("debt_to_income", 0.4))
        savings_ratio = float(f.get("savings_ratio", 0.1))
        income_stability = float(f.get("income_stability", 0.5))
        cashflow_volatility = float(f.get("cashflow_volatility", 0.5))
        delinquent = bool(f.get("has_delinquency", False))

        # Credit score 0-100
        score = 100.0
        score -= dti * 60
        score += savings_ratio * 40
        score += income_stability * 25
        score -= cashflow_volatility * 25
        score -= 20 if delinquent else 0
        score = max(0, min(100, round(score)))

        pd = max(0.01, min(0.99, 0.6 * dti + 0.3 * cashflow_volatility +
                           (0.15 if delinquent else 0) - 0.2 * savings_ratio))
        band = "low" if score >= 70 else "medium" if score >= 45 else "high"

        contributions = [
            {"feature": "debt_to_income", "impact": round(-dti * 0.6, 3),
             "value": round(dti, 3)},
            {"feature": "savings_ratio", "impact": round(savings_ratio * 0.4, 3),
             "value": round(savings_ratio, 3)},
            {"feature": "income_stability", "impact": round(income_stability * 0.25, 3),
             "value": round(income_stability, 3)},
            {"feature": "cashflow_volatility", "impact": round(-cashflow_volatility * 0.25, 3),
             "value": round(cashflow_volatility, 3)},
        ]
        if delinquent:
            contributions.append({"feature": "has_delinquency", "impact": -0.2, "value": 1})

        narrative = self._narrative(band, dti, savings_ratio, income_stability, delinquent)

        # Simple rule-based fraud signal
        fraud_reasons = []
        if f.get("income_document_mismatch"):
            fraud_reasons.append("Declared income inconsistent with transaction inflows")
        if f.get("application_velocity", 0) > 3:
            fraud_reasons.append("Multiple applications in a short window")
        fraud_severity = "high" if len(fraud_reasons) >= 2 else "medium" if fraud_reasons else "low"

        return {
            "model_version": "local-fallback",
            "risk": {"band": band, "probability": round(pd, 4)},
            "credit_score": {"score": int(score),
                             "subscores": {"leverage": round(max(0, 100 - dti * 100)),
                                           "savings": round(savings_ratio * 100),
                                           "stability": round(income_stability * 100)}},
            "default": {"probability": round(pd, 4), "horizon_months": 12},
            "fraud": {"severity": fraud_severity, "reasons": fraud_reasons},
            "explanation": {"contributions": contributions, "narrative": narrative},
        }

    @staticmethod
    def _narrative(band, dti, savings_ratio, income_stability, delinquent) -> str:
        parts = [f"Overall risk assessed as {band.upper()}."]
        if dti > 0.45:
            parts.append(f"A high debt-to-income ratio ({dti:.0%}) increased risk.")
        else:
            parts.append(f"A manageable debt-to-income ratio ({dti:.0%}) supported the assessment.")
        if savings_ratio > 0.15:
            parts.append(f"A healthy savings ratio ({savings_ratio:.0%}) reduced risk.")
        if income_stability > 0.6:
            parts.append("Stable, regular income reduced risk.")
        if delinquent:
            parts.append("A record of delinquency on existing obligations increased risk.")
        return " ".join(parts)


ml_client = MLClient()
