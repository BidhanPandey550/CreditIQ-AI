from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.exceptions import DomainRuleError
from app.core.deps import CurrentUser
from app.modules.loan.products import normalize_code, validate_application
from app.modules.loan.schemas import LoanCreate, LoanProductCreate
from app.modules.loan.service import create_loan


def _product(**overrides):
    values = {
        "status": "active",
        "min_amount": 50_000,
        "max_amount": 1_000_000,
        "min_tenor_months": 3,
        "max_tenor_months": 60,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_product_code_is_normalized_for_tenant_uniqueness() -> None:
    assert normalize_code("  sme-working_capital ") == "SME-WORKING_CAPITAL"


def test_product_schema_rejects_inverted_amount_and_tenor_ranges() -> None:
    with pytest.raises(ValidationError, match="Minimum amount"):
        LoanProductCreate(
            code="SME",
            name="SME Loan",
            min_amount=200_000,
            max_amount=100_000,
            min_tenor_months=3,
            max_tenor_months=12,
            interest_rate=12,
        )
    with pytest.raises(ValidationError, match="Minimum tenor"):
        LoanProductCreate(
            code="SME",
            name="SME Loan",
            min_amount=100_000,
            max_amount=200_000,
            min_tenor_months=24,
            max_tenor_months=12,
            interest_rate=12,
        )


def test_application_inside_product_policy_is_accepted() -> None:
    validate_application(_product(), amount=500_000, tenor_months=24)


@pytest.mark.parametrize(
    ("amount", "tenor", "message"),
    [
        (10_000, 24, "amount"),
        (2_000_000, 24, "amount"),
        (500_000, 1, "tenor"),
        (500_000, 120, "tenor"),
    ],
)
def test_application_outside_product_policy_is_rejected(amount, tenor, message) -> None:
    with pytest.raises(DomainRuleError, match=message):
        validate_application(_product(), amount=amount, tenor_months=tenor)


def test_inactive_product_cannot_accept_new_applications() -> None:
    with pytest.raises(DomainRuleError, match="inactive"):
        validate_application(_product(status="inactive"), amount=500_000, tenor_months=24)


def test_origination_delegates_to_selected_product_policy(monkeypatch) -> None:
    org_id = uuid.uuid4()
    branch_id = uuid.uuid4()
    applicant_id = uuid.uuid4()
    actor = CurrentUser(
        user_id=uuid.uuid4(),
        org_id=org_id,
        branch_id=branch_id,
        roles=["Loan Officer"],
        permissions={"loan:create"},
    )
    product = _product(id=uuid.uuid4(), organization_id=org_id)
    applicant = SimpleNamespace(id=applicant_id, branch_id=branch_id)
    calls = []

    class Database:
        def get(self, _model, _identifier):
            return applicant

        def add(self, value):
            if getattr(value, "id", None) is None:
                value.id = uuid.uuid4()

        def flush(self):
            return None

    monkeypatch.setattr("app.modules.loan.service.require_branch", lambda *_args: None)
    monkeypatch.setattr("app.modules.loan.service.get_product", lambda *_args: product)
    monkeypatch.setattr(
        "app.modules.loan.service.validate_application",
        lambda selected, amount, tenor: calls.append((selected, amount, tenor)),
    )

    create_loan(
        Database(),  # type: ignore[arg-type]
        actor,
        LoanCreate(
            applicant_id=applicant_id,
            product_id=product.id,
            amount=250_000,
            tenor_months=12,
        ),
    )

    assert calls == [(product, 250_000, 12)]
