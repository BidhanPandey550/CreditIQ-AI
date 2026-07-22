from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.api.analytics import branch_performance, calculate_delinquency_metrics, monthly_trends
from app.core.deps import CurrentUser


class _Rows:
    def __init__(self, rows: list[tuple]):
        self._rows = rows

    def all(self) -> list[tuple]:
        return self._rows


class _Database:
    def __init__(self, responses: list[list[tuple]]):
        self.responses = iter(responses)
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return _Rows(next(self.responses))


def _user() -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        branch_id=None,
        roles=["Administrator"],
        permissions={"analytics:read"},
    )


def test_monthly_trends_merge_application_and_disbursement_events() -> None:
    january = datetime(2026, 1, 1, tzinfo=timezone.utc)
    february = datetime(2026, 2, 1, tzinfo=timezone.utc)
    db = _Database(
        [
            [(january, 4), (february, 3)],
            [(february, 2, 750_000)],
        ]
    )

    result = monthly_trends(user=_user(), db=db)  # type: ignore[arg-type]

    assert result == [
        {
            "month": "2026-01-01",
            "applications": 4,
            "disbursements": 0,
            "disbursed_amount": 0.0,
        },
        {
            "month": "2026-02-01",
            "applications": 3,
            "disbursements": 2,
            "disbursed_amount": 750_000.0,
        },
    ]
    assert len(db.statements) == 2


def test_branch_performance_calculates_decided_application_rate() -> None:
    branch_id = uuid.uuid4()
    db = _Database([[(branch_id, "Head Office", 8, 5, 2, 1_250_000)]])

    result = branch_performance(user=_user(), db=db)  # type: ignore[arg-type]

    assert result == [
        {
            "branch_id": branch_id,
            "branch_name": "Head Office",
            "applications": 8,
            "approved": 5,
            "rejected": 2,
            "approval_rate": 0.714,
            "exposure": 1_250_000.0,
        }
    ]


def test_delinquency_metrics_use_total_loan_balance_for_par() -> None:
    current = uuid.uuid4()
    rows = [
        (current, date(2026, 1, 1), 1000, 100, 0, 0),
        (current, date(2026, 8, 1), 1000, 80, 0, 0),
        (uuid.uuid4(), date(2026, 8, 1), 2000, 0, 0, 0),
    ]

    result = calculate_delinquency_metrics(
        rows, as_of=date(2026, 2, 15), thresholds=[1, 30, 60], grace_days=5
    )

    assert result["portfolio_outstanding"] == 4180.0
    assert result["overdue_amount"] == 1100.0
    assert result["delinquent_loans"] == 1
    assert result["par"]["30"]["balance"] == 2180.0
    assert result["par"]["60"]["ratio"] == 0


def test_delinquency_metrics_ignore_fully_paid_installments() -> None:
    loan_id = uuid.uuid4()
    result = calculate_delinquency_metrics(
        [(loan_id, date(2025, 1, 1), Decimal("100"), Decimal("5"), 100, 5)],
        as_of=date(2026, 1, 1),
        thresholds=[30],
        grace_days=0,
    )
    assert result["portfolio_outstanding"] == 0
    assert result["delinquent_loans"] == 0
