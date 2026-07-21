"""Operational monitoring and Decision Engine degradation-policy tests."""

import pandas as pd

from creditiq_ai.config import load_config
from creditiq_ai.decision import DecisionEngine, DecisionRequest
from creditiq_ai.fraud_intelligence import FraudSignals
from creditiq_ai.model_operations.monitoring import InferenceEvent, InMemoryDecisionMonitor


def _event(index: int, *, success: bool = True, latency: float = 10.0) -> InferenceEvent:
    return InferenceEvent(correlation_id=f"event-{index}", success=success, duration_ms=latency)


def test_monitor_reports_unknown_before_first_event():
    snapshot = InMemoryDecisionMonitor(load_config().monitoring).snapshot()
    assert snapshot.status == "unknown"
    assert snapshot.prediction_count == 0


def test_monitor_aggregates_count_failures_and_latency():
    monitor = InMemoryDecisionMonitor(load_config().monitoring)
    monitor.record(_event(1, latency=10.0))
    monitor.record(_event(2, success=False, latency=30.0))
    snapshot = monitor.snapshot()
    assert snapshot.prediction_count == 2
    assert snapshot.failure_count == 1
    assert snapshot.failure_rate == 0.5
    assert snapshot.average_latency_ms == 20.0
    assert snapshot.p95_latency_ms == 30.0
    assert snapshot.status == "unhealthy"


def test_monitor_retention_is_bounded():
    config = load_config().monitoring.model_copy(update={"retention_events": 2})
    monitor = InMemoryDecisionMonitor(config)
    for index in range(3):
        monitor.record(_event(index))
    assert monitor.snapshot().prediction_count == 2


def test_decision_engine_records_privacy_safe_monitoring_event():
    config = load_config()
    monitor = InMemoryDecisionMonitor(config.monitoring)
    engine = DecisionEngine(
        config,
        credit_predictor=lambda _row: 0.02,
        fraud_assessor=lambda _row: FraudSignals(anomaly_probability=0.05),
        monitor=monitor,
    )
    decision = engine.decide(
        DecisionRequest(
            row=pd.DataFrame([{"monthly_income": 80_000, "monthly_expenses": 30_000}]),
            correlation_id="monitor-test",
            model_versions={"credit": "1.0.0"},
        )
    )
    snapshot = monitor.snapshot()
    assert decision.monitoring_status == "ok"
    assert snapshot.prediction_count == 1
    assert snapshot.failure_count == 0


def test_monitoring_backend_failure_does_not_block_decision():
    class BrokenMonitor:
        def record(self, event: InferenceEvent) -> None:
            raise RuntimeError("monitor unavailable")

    config = load_config()
    engine = DecisionEngine(
        config,
        credit_predictor=lambda _row: 0.02,
        fraud_assessor=lambda _row: FraudSignals(anomaly_probability=0.05),
        monitor=BrokenMonitor(),
    )
    decision = engine.decide(
        DecisionRequest(row=pd.DataFrame([{"monthly_income": 80_000, "monthly_expenses": 30_000}]))
    )
    assert decision.recommendation
    assert decision.monitoring_status == "degraded"
    assert "monitoring_unavailable" in decision.warnings
