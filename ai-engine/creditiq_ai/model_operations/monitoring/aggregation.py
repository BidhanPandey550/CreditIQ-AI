"""Pure aggregation of privacy-safe inference events into operational health."""

from __future__ import annotations

import math
from collections.abc import Sequence

from creditiq_ai.config.models import MonitoringConfig
from creditiq_ai.model_operations.monitoring.models import InferenceEvent, MonitoringSnapshot


def aggregate_events(
    events: Sequence[InferenceEvent], config: MonitoringConfig
) -> MonitoringSnapshot:
    """Aggregate a bounded event window without depending on its storage adapter."""
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
    status, reasons = _health(failure_rate, average_latency, config)
    return MonitoringSnapshot(
        prediction_count=count,
        failure_count=failures,
        failure_rate=round(failure_rate, 6),
        average_latency_ms=round(average_latency, 3),
        p95_latency_ms=round(p95_latency, 3),
        status=status,
        reasons=reasons,
    )


def _health(
    failure_rate: float, average_latency_ms: float, config: MonitoringConfig
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    critical = False
    warning = False
    if failure_rate >= config.critical_failure_rate:
        critical = True
        reasons.append("critical_failure_rate")
    elif failure_rate >= config.warning_failure_rate:
        warning = True
        reasons.append("elevated_failure_rate")
    if average_latency_ms >= config.critical_average_latency_ms:
        critical = True
        reasons.append("critical_average_latency")
    elif average_latency_ms >= config.warning_average_latency_ms:
        warning = True
        reasons.append("elevated_average_latency")
    return ("unhealthy" if critical else "degraded" if warning else "healthy"), reasons
