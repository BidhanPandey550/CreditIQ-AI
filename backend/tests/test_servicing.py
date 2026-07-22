from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import DomainRuleError
from app.modules.loan.models import LoanInstallment
from app.modules.loan.servicing import (
    add_months,
    allocate_repayment,
    build_amortization_schedule,
)


def test_add_months_preserves_valid_month_end() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2026, 12, 15), 2) == date(2027, 2, 15)


def test_zero_interest_schedule_reconciles_principal_exactly() -> None:
    schedule = build_amortization_schedule(100_000, 0, 3, date(2026, 2, 28))

    assert len(schedule) == 3
    assert sum((item.principal_due for item in schedule), Decimal(0)) == Decimal("100000.00")
    assert sum((item.interest_due for item in schedule), Decimal(0)) == Decimal("0.00")
    assert [item.due_date for item in schedule] == [
        date(2026, 2, 28),
        date(2026, 3, 28),
        date(2026, 4, 28),
    ]


def test_reducing_balance_schedule_has_interest_and_exact_principal() -> None:
    schedule = build_amortization_schedule(500_000, 12, 24, date(2026, 3, 1))

    assert sum((item.principal_due for item in schedule), Decimal(0)) == Decimal("500000.00")
    assert sum((item.interest_due for item in schedule), Decimal(0)) > Decimal("0")
    assert schedule[0].interest_due > schedule[-1].interest_due


@pytest.mark.parametrize("principal,tenor", [(0, 12), (-1, 12), (1000, 0)])
def test_schedule_rejects_invalid_financial_terms(principal: float, tenor: int) -> None:
    with pytest.raises(DomainRuleError):
        build_amortization_schedule(principal, 10, tenor, date(2026, 3, 1))


def _installment(sequence: int, principal: float, interest: float) -> LoanInstallment:
    return LoanInstallment(
        sequence_no=sequence,
        due_date=date(2026, sequence, 1),
        principal_due=principal,
        interest_due=interest,
        principal_paid=0,
        interest_paid=0,
    )


def test_repayment_allocates_oldest_interest_before_principal() -> None:
    first = _installment(1, 1000, 100)
    second = _installment(2, 1000, 80)
    paid_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    original_balance = allocate_repayment([first, second], 1150, paid_at)

    assert original_balance == Decimal("2180.00")
    assert first.interest_paid == Decimal("100.00")
    assert first.principal_paid == Decimal("1000.00")
    assert first.paid_at == paid_at
    assert second.interest_paid == Decimal("50.00")
    assert second.principal_paid == Decimal("0.00")


def test_repayment_rejects_overpayment() -> None:
    with pytest.raises(DomainRuleError, match="exceeds"):
        allocate_repayment([_installment(1, 1000, 100)], 1100.01, datetime.now(timezone.utc))
