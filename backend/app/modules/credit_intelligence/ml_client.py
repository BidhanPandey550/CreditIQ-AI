"""Anti-corruption layer to the separate canonical ML-engine service.

Credit decisions fail closed when verified model inference is unavailable. Returning a local
heuristic as though it were a governed model would be unsafe and unauditable in lending.
"""

from __future__ import annotations

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.core.request_context import current_request_id
from app.modules.credit_intelligence.schemas import MLPrediction

log = get_logger("ml_client")


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
        try:
            request_id = current_request_id()
            resp = self._http().post(
                "/predict",
                json={"features": features},
                headers={"X-Request-ID": request_id} if request_id else None,
            )
            resp.raise_for_status()
            return MLPrediction.model_validate(resp.json()).model_dump()
        except (
            httpx.HTTPError,
            ValueError,
            PydanticValidationError,
        ) as exc:  # pragma: no cover - network dependent
            log.error("ML engine inference unavailable: %s", exc)
            raise ServiceUnavailableError(
                "Governed credit intelligence is temporarily unavailable; no lending decision "
                "was produced. Retry after the ML service recovers."
            ) from exc


ml_client = MLClient()
