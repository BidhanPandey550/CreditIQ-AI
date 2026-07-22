from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.deps import CurrentUser
from app.modules.applicant.schemas import (
    ApplicantProfileOut,
    ApplicantProfileUpdate,
    AssetIn,
    ExpenseIn,
    IncomeIn,
    LiabilityIn,
)
from app.modules.applicant.service import _replace_many, update_profile
from app.modules.applicant.models import IncomeRecord


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (IncomeIn, {"source": "Salary", "amount": -1}),
        (ExpenseIn, {"category": "Living", "amount": -1}),
        (AssetIn, {"name": "House", "value": -1}),
        (LiabilityIn, {"name": "Card", "outstanding_amount": -1}),
    ],
)
def test_financial_profile_rejects_negative_values(schema, payload) -> None:
    with pytest.raises(ValidationError):
        schema(**payload)


def test_partial_profile_preserves_omitted_collections() -> None:
    update = ApplicantProfileUpdate(phone="9800000000")
    assert update.model_fields_set == {"phone"}
    assert update.incomes is None


@pytest.mark.parametrize("field", ["full_name", "is_self_employed"])
def test_required_profile_fields_cannot_be_explicitly_cleared(field) -> None:
    with pytest.raises(ValidationError):
        ApplicantProfileUpdate(**{field: None})


def test_collection_replacement_is_atomic_at_the_session_boundary() -> None:
    database = SimpleNamespace(
        executed=[],
        added=[],
    )
    database.execute = lambda statement: database.executed.append(statement)
    database.add_all = lambda values: database.added.extend(values)
    org_id = uuid.uuid4()
    applicant_id = uuid.uuid4()

    _replace_many(
        database,  # type: ignore[arg-type]
        IncomeRecord,
        org_id,
        applicant_id,
        [IncomeIn(source="Salary", amount=80_000)],
    )

    assert len(database.executed) == 1
    assert len(database.added) == 1
    assert database.added[0].organization_id == org_id
    assert database.added[0].applicant_id == applicant_id


def _profile(applicant_id: uuid.UUID, *, phone: str) -> ApplicantProfileOut:
    return ApplicantProfileOut(
        id=applicant_id,
        branch_id=None,
        full_name="Applicant Name",
        date_of_birth=date(1990, 1, 1),
        gender=None,
        phone=phone,
        email=None,
        address=None,
        is_self_employed=False,
        national_id=None,
        kyc_verification_status=None,
        employment=None,
        business=None,
        incomes=[],
        expenses=[],
        assets=[],
        liabilities=[],
        existing_loans=[],
    )


def test_profile_update_records_full_before_and_after_audit(monkeypatch) -> None:
    org_id = uuid.uuid4()
    applicant_id = uuid.uuid4()
    actor = CurrentUser(
        user_id=uuid.uuid4(),
        org_id=org_id,
        branch_id=None,
        roles=["Risk Analyst"],
        permissions={"applicant:manage"},
    )
    applicant = SimpleNamespace(
        id=applicant_id,
        branch_id=None,
        phone="9800000000",
        full_name="Applicant Name",
        date_of_birth=date(1990, 1, 1),
        gender=None,
        email=None,
        address=None,
        is_self_employed=False,
    )

    class Database:
        def __init__(self):
            self.added = []
            self.flushed = False

        def refresh(self, _value, **_kwargs):
            return None

        def add(self, value):
            self.added.append(value)

        def flush(self):
            self.flushed = True

    database = Database()
    profiles = iter(
        [_profile(applicant_id, phone="9800000000"), _profile(applicant_id, phone="9811111111")]
    )
    monkeypatch.setattr("app.modules.applicant.service.get_applicant", lambda *_args: applicant)
    monkeypatch.setattr("app.modules.applicant.service.get_profile", lambda *_args: next(profiles))

    result = update_profile(
        database,  # type: ignore[arg-type]
        actor,
        applicant_id,
        ApplicantProfileUpdate(phone="9811111111"),
    )

    assert applicant.phone == "9811111111"
    assert result.phone == "9811111111"
    assert database.flushed
    event = database.added[0]
    assert event.action == "applicant.profile.update"
    assert event.before["phone"].startswith("hmac-sha256:")
    assert event.after["phone"].startswith("hmac-sha256:")
    assert event.before["phone"] != event.after["phone"]
