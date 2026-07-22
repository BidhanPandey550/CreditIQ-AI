"""ML engine serving API — credit risk, credit score, default PD, fraud, and XAI.

Separate service from the backend (different runtime/scaling/release cadence). The backend's
credit-intelligence module is the only caller. This adapter delegates all model behavior to the
canonical ``creditiq_ai`` package so serving and offline evaluation cannot diverge.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Preserve or create a correlation ID across the inference boundary."""
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def _runtime() -> CanonicalRuntime:
    if runtime is None:
        raise RuntimeError("ML runtime has not completed startup")
    return runtime


@app.get("/health")
def health() -> dict:
    serving = _runtime()
    monitoring = serving.monitoring_snapshot()
    return {
        "status": "ok",
        "model_version": serving.version,
        "metrics": serving.metrics,
        "monitoring": monitoring.model_dump(mode="json"),
    }


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


@app.get("/monitoring")
def monitoring() -> dict:
    return _runtime().monitoring_snapshot().model_dump(mode="json")


@app.post("/predict")
def predict(req: PredictRequest, request: Request) -> dict:
    return _runtime().predict(req.features, correlation_id=request.state.request_id)
