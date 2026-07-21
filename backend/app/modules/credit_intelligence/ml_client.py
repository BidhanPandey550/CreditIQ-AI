"""Anti-corruption layer to the separate canonical ML-engine service.

Credit decisions fail closed when verified model inference is unavailable. Returning a local
heuristic as though it were a governed model would be unsafe and unauditable in lending.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger

log = get_logger("ml_client")


class MLClient:
    def __init__(self) -> None:
        self.base_url = settings.ml_engine_url.rstrip("/")
        self.timeout = settings.ml_engine_timeout_seconds

    def predict(self, features: dict) -> dict:
        """Return risk, credit_score, default, fraud, explanation for a feature vector."""
        try:
            resp = httpx.post(
                f"{self.base_url}/predict",
                json={"features": features},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except (
            httpx.HTTPError,
            ValueError,
        ) as exc:  # pragma: no cover - network dependent
            log.error("ML engine inference unavailable: %s", exc)
            raise ServiceUnavailableError(
                "Governed credit intelligence is temporarily unavailable; no lending decision "
                "was produced. Retry after the ML service recovers."
            ) from exc


ml_client = MLClient()
