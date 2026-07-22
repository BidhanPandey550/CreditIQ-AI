"""Anti-corruption layer to the separate canonical ML-engine service.

Credit decisions fail closed when verified model inference is unavailable. Returning a local
heuristic as though it were a governed model would be unsafe and unauditable in lending.
"""

from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.core.request_context import current_request_id
from app.modules.credit_intelligence.schemas import (
    MLModelStatus,
    MLMonitoringStatus,
    MLPrediction,
    ModelOperationsStatus,
)

log = get_logger("ml_client")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class MLClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.base_url = settings.ml_engine_url.rstrip("/")
        self.timeout = settings.ml_engine_timeout_seconds
        self._client = client

    def close(self) -> None:
        """Release pooled downstream connections during application shutdown."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        return self._client

    def predict(self, features: dict) -> dict:
        """Return risk, credit_score, default, fraud, explanation for a feature vector."""
        return self._request(MLPrediction, "/predict", payload={"features": features}).model_dump()

    def operations_status(self) -> ModelOperationsStatus:
        """Return validated model identity and process-local operational telemetry."""
        model = self._request(MLModelStatus, "/models")
        monitoring = self._request(MLMonitoringStatus, "/monitoring")
        return ModelOperationsStatus(model=model, monitoring=monitoring)

    def _request(
        self,
        schema: type[SchemaT],
        path: str,
        *,
        payload: dict | None = None,
    ) -> SchemaT:
        try:
            request_id = current_request_id()
            resp = self._http().request(
                "POST" if payload is not None else "GET",
                path,
                json=payload,
                headers={"X-Request-ID": request_id} if request_id else None,
            )
            resp.raise_for_status()
            return schema.model_validate(resp.json())
        except (
            httpx.HTTPError,
            ValueError,
            PydanticValidationError,
        ) as exc:  # pragma: no cover - network dependent
            log.error("ML service request failed: %s", exc)
            raise ServiceUnavailableError(
                "Governed ML service is temporarily unavailable or returned an invalid contract. "
                "No unverified result was accepted; retry after the service recovers."
            ) from exc


ml_client = MLClient()
