"""Thread-safe in-process alert store and acknowledgement service."""

from __future__ import annotations

import threading

from creditiq_ai.exceptions import AlertError
from creditiq_ai.model_operations.alerts.models import ModelAlert
from creditiq_ai.model_operations.health import ModelHealthReport


class AlertManager:
    """Create deduplicated health alerts behind a future delivery-adapter boundary."""

    def __init__(self) -> None:
        self._alerts: dict[str, ModelAlert] = {}
        self._lock = threading.RLock()

    def from_health(self, model_ref: str, report: ModelHealthReport) -> ModelAlert | None:
        if report.status in {"healthy", "stable", "unknown"}:
            return None
        code = f"model_health_{report.status}"
        with self._lock:
            existing = next(
                (
                    alert
                    for alert in self._alerts.values()
                    if alert.model_ref == model_ref
                    and alert.code == code
                    and alert.status == "open"
                ),
                None,
            )
            if existing:
                return existing
            alert = ModelAlert(
                model_ref=model_ref,
                severity="critical" if report.status in {"critical", "unhealthy"} else "warning",
                code=code,
                message="; ".join(report.reasons) or report.status,
            )
            self._alerts[alert.alert_id] = alert
            return alert

    def acknowledge(self, alert_id: str) -> ModelAlert:
        with self._lock:
            try:
                alert = self._alerts[alert_id]
            except KeyError as exc:
                raise AlertError("Alert was not found", context={"alert_id": alert_id}) from exc
            acknowledged = alert.model_copy(update={"status": "acknowledged"})
            self._alerts[alert_id] = acknowledged
            return acknowledged

    def list(self, *, status: str | None = None) -> list[ModelAlert]:
        with self._lock:
            alerts = list(self._alerts.values())
        return [alert for alert in alerts if status is None or alert.status == status]
