"""Thread-safe bounded inference monitor suitable for one process."""

from __future__ import annotations

import math
import threading
from collections import deque

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.model_operations.monitoring.models import InferenceEvent, MonitoringSnapshot


class InMemoryDecisionMonitor(BaseComponent):
    """Collect inference events and evaluate health against configured operational thresholds."""

    def __init__(self, config: MonitoringConfig) -> None:
        super().__init__()
        self._config = config
        self._events: deque[InferenceEvent] = deque(maxlen=config.retention_events)
        self._lock = threading.RLock()

    def record(self, event: InferenceEvent) -> None:
        """Append a privacy-safe event to the bounded window."""
        if not self._config.enabled:
            return
        with self._lock:
            self._events.append(event)

    def snapshot(self) -> MonitoringSnapshot:
        """Return deterministic aggregate health for the retained event window."""
        with self._lock:
            events = list(self._events)
        count = len(events)
        if count == 0:
            return MonitoringSnapshot(
                prediction_count=0,
                failure_count=0,
                failure_rate=0.0,
                average_latency_ms=0.0,
                p95_latency_ms=0.0,
                status="unknown",
                reasons=["no_inference_events"],
            )

        failures = sum(not event.success for event in events)
        failure_rate = failures / count
        latencies = sorted(event.duration_ms for event in events)
        average_latency = sum(latencies) / count
        percentile_index = max(0, math.ceil(0.95 * count) - 1)
        p95_latency = latencies[percentile_index]
        status, reasons = self._health(failure_rate, average_latency)
        return MonitoringSnapshot(
            prediction_count=count,
            failure_count=failures,
            failure_rate=round(failure_rate, 6),
            average_latency_ms=round(average_latency, 3),
            p95_latency_ms=round(p95_latency, 3),
            status=status,
            reasons=reasons,
        )

    def _health(self, failure_rate: float, average_latency_ms: float) -> tuple[str, list[str]]:
        reasons: list[str] = []
        critical = False
        warning = False
        if failure_rate >= self._config.critical_failure_rate:
            critical = True
            reasons.append("critical_failure_rate")
        elif failure_rate >= self._config.warning_failure_rate:
            warning = True
            reasons.append("elevated_failure_rate")
        if average_latency_ms >= self._config.critical_average_latency_ms:
            critical = True
            reasons.append("critical_average_latency")
        elif average_latency_ms >= self._config.warning_average_latency_ms:
            warning = True
            reasons.append("elevated_average_latency")
        return ("unhealthy" if critical else "degraded" if warning else "healthy"), reasons
