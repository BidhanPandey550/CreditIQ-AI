from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.deps import CurrentUser
from app.core.exceptions import ConflictError, DomainRuleError
from app.modules.fraud.schemas import FraudAlertResolution
from app.modules.fraud.service import _query, resolve_alert
from app.modules.loan.service import ensure_fraud_clearance
from app.shared.enums import FraudSeverity, FraudStatus


def _actor(*, branch_id: uuid.UUID | None = None) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        branch_id=branch_id,
        roles=["Loan Officer"] if branch_id else ["Risk Analyst"],
        permissions={"fraud:read", "fraud:resolve"},
    )


def _case(actor: CurrentUser, *, status: FraudStatus = FraudStatus.open):
    loan_id = uuid.uuid4()
    applicant_id = uuid.uuid4()
    alert = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=actor.org_id,
        loan_id=loan_id,
        severity=FraudSeverity.high,
        status=status,
        reasons=["Income is inconsistent with cash flow"],
        resolved_by=None,
        resolved_at=None,
        resolution_note=None,
        created_at=datetime.now(timezone.utc),
    )
    loan = SimpleNamespace(id=loan_id, reference_no="LN-12345678", applicant_id=applicant_id)
    applicant = SimpleNamespace(id=applicant_id, full_name="Test Applicant")
    return alert, loan, applicant


class _Result:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class _Database:
    def __init__(self, row):
        self.row = row
        self.added = []
        self.flushed = False

    def execute(self, _statement):
        return _Result(self.row)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flushed = True

    def scalar(self, _statement):
        return self.row


def test_branch_scoped_fraud_query_contains_branch_filter() -> None:
    actor = _actor(branch_id=uuid.uuid4())
    compiled = str(_query(actor))
    assert "loan_applications.branch_id" in compiled


def test_resolution_contract_rejects_open_status_and_blank_rationale() -> None:
    with pytest.raises(ValidationError):
        FraudAlertResolution(status=FraudStatus.open, note="A valid rationale")
    with pytest.raises(ValidationError):
        FraudAlertResolution(status=FraudStatus.confirmed, note="            ")


def test_confirming_alert_records_resolution_and_audit_evidence() -> None:
    actor = _actor()
    row = _case(actor)
    database = _Database(row)

    result = resolve_alert(
        database,  # type: ignore[arg-type]
        actor,
        row[0].id,
        FraudStatus.confirmed,
        "Identity documents conflict with declared employment.",
    )

    assert result.status is FraudStatus.confirmed
    assert result.resolved_by == actor.user_id
    assert result.resolved_at is not None
    assert result.resolution_note == "Identity documents conflict with declared employment."
    assert database.flushed
    audit_log = database.added[0]
    assert audit_log.action == "fraud.alert.resolve"
    assert audit_log.before == {"status": "open"}
    assert audit_log.after["status"] == "confirmed"


def test_resolved_alert_cannot_be_overwritten() -> None:
    actor = _actor()
    row = _case(actor, status=FraudStatus.dismissed)
    with pytest.raises(ConflictError, match="already been resolved"):
        resolve_alert(
            _Database(row),  # type: ignore[arg-type]
            actor,
            row[0].id,
            FraudStatus.confirmed,
            "Attempting to overwrite a prior disposition.",
        )


def test_service_rejects_non_terminal_resolution_status() -> None:
    actor = _actor()
    row = _case(actor)
    with pytest.raises(DomainRuleError, match="confirmed or dismissed"):
        resolve_alert(
            _Database(row),  # type: ignore[arg-type]
            actor,
            row[0].id,
            FraudStatus.open,
            "This should never be accepted as a resolution.",
        )


def test_blocking_fraud_alert_prevents_loan_approval() -> None:
    with pytest.raises(DomainRuleError, match="cannot be approved"):
        ensure_fraud_clearance(_Database(uuid.uuid4()), uuid.uuid4())  # type: ignore[arg-type]


def test_absence_of_blocking_alert_allows_approval() -> None:
    ensure_fraud_clearance(_Database(None), uuid.uuid4())  # type: ignore[arg-type]
