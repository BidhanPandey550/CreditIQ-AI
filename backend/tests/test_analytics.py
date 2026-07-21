from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.api.analytics import branch_performance, monthly_trends
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
