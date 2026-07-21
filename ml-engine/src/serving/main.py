"""ML engine serving API — credit risk, credit score, default PD, fraud, and SHAP explanation.

Separate service from the backend (different runtime/scaling/release cadence). The backend's
credit_intelligence module is the only caller and degrades to a local heuristic if this is down.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

from src.explainability.explain import contributions, narrative
from src.features.synthetic import vectorize
from src.models.registry import registry


class PredictRequest(BaseModel):
    features: dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load()  # train models once on startup
    yield


app = FastAPI(title="CreditIQ AI — ML Engine", version="0.1.0", lifespan=lifespan)


def _band(pd: float) -> str:
    return "low" if pd < 0.25 else "medium" if pd < 0.55 else "high"


@app.get("/health")
def health() -> dict:
    bundle = registry.load()
    return {"status": "ok", "model_version": bundle.version, "metrics": bundle.metrics}


@app.get("/models")
def models() -> dict:
    b = registry.load()
    return {"version": b.version, "algorithm": b.algorithm, "features_used": 5,
            "metrics": b.metrics, "stage": "production"}


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    bundle = registry.load()
    f = req.features
    x = vectorize(f)
    pd = float(bundle.default_model.predict_proba(np.array(x).reshape(1, -1))[0, 1])
    band = _band(pd)

    score = int(max(0, min(100, round((1 - pd) * 100))))
    subscores = {
        "leverage": int(max(0, min(100, round((1 - float(f.get("debt_to_income", 0.4))) * 100)))),
        "savings": int(max(0, min(100, round(float(f.get("savings_ratio", 0.1)) * 100)))),
        "stability": int(max(0, min(100, round(float(f.get("income_stability", 0.5)) * 100)))),
    }

    contribs = contributions(bundle.default_model, x, bundle.train_means)

    # Hybrid fraud engine: deterministic rules + unsupervised anomaly detection.
    reasons = []
    if f.get("income_document_mismatch"):
        reasons.append("Declared income inconsistent with transaction inflows")
    if float(f.get("application_velocity", 0)) > 3:
        reasons.append("Multiple applications in a short window")

    xv = np.array(x).reshape(1, -1)
    is_anomaly = int(bundle.fraud_model.predict(xv)[0]) == -1
    anomaly_score = float(bundle.fraud_model.score_samples(xv)[0])  # lower = more anomalous
    if is_anomaly:
        reasons.append("Financial profile is a statistical outlier vs. the population")

    rule_hits = len([r for r in reasons if "outlier" not in r])
    if rule_hits >= 2 or (rule_hits >= 1 and is_anomaly):
        severity = "high"
    elif rule_hits >= 1 or is_anomaly:
        severity = "medium"
    else:
        severity = "low"

    return {
        "model_version": bundle.version,
        "risk": {"band": band, "probability": round(pd, 4)},
        "credit_score": {"score": score, "subscores": subscores},
        "default": {"probability": round(pd, 4), "horizon_months": 12},
        "fraud": {"severity": severity, "reasons": reasons,
                  "anomaly_score": round(anomaly_score, 4)},
        "explanation": {"contributions": contribs, "narrative": narrative(band, contribs)},
    }
