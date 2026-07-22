"""ML engine serving API — credit risk, credit score, default PD, fraud, and XAI.

Separate service from the backend (different runtime/scaling/release cadence). The backend's
credit-intelligence module is the only caller. This adapter delegates all model behavior to the
canonical ``creditiq_ai`` package so serving and offline evaluation cannot diverge.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from src.serving.runtime import CanonicalRuntime
from src.serving.settings import ServingSettings


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: dict[str, object] = Field(min_length=1)


runtime: CanonicalRuntime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runtime
    runtime = CanonicalRuntime.create(ServingSettings.from_environment())
    yield


app = FastAPI(title="CreditIQ AI — ML Engine", version="0.1.0", lifespan=lifespan)


def _runtime() -> CanonicalRuntime:
    if runtime is None:
        raise RuntimeError("ML runtime has not completed startup")
    return runtime


@app.get("/health")
def health() -> dict:
    serving = _runtime()
    return {"status": "ok", "model_version": serving.version, "metrics": serving.metrics}


@app.get("/models")
def models() -> dict:
    serving = _runtime()
    return {
        "version": serving.version,
        "algorithm": serving.trainer.algorithm,
        "features_used": len(serving.reference.columns),
        "metrics": serving.metrics,
        "stage": serving.stage,
        "data_source": serving.data_source,
        "feature_version": serving.feature_version,
    }


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    return _runtime().predict(req.features)
