"""Thread-safe bounded inference monitor suitable for one process."""

from __future__ import annotations

import threading
from collections import deque

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.core.base import BaseComponent
from creditiq_ai.model_operations.monitoring.aggregation import aggregate_events
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
        return aggregate_events(events, self._config)
