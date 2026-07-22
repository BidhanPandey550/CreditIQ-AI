"""Applicant transaction evidence is reproducible, scoped, and financially consistent."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.core.deps import CurrentUser
from app.integrations.simulated import SimulatedWalletAdapter
from app.modules.applicant.service import list_transactions


class _Scalars:
    def __init__(self, values: list[object]):
        self.values = values

    def first(self):
        return self.values[0] if self.values else None

    def all(self):
        return self.values


class _Aggregate:
    def one(self):
        return 3, 1500, 550, 3


class _Database:
    def __init__(self, applicant, transactions):
        self.applicant = applicant
        self.scalar_results = iter([transactions])
        self.statements = []

    def get(self, model, record_id):
        return self.applicant if record_id == self.applicant.id else None

    def scalars(self, statement):
        self.statements.append(statement)
        return _Scalars(next(self.scalar_results))

    def execute(self, statement):
        self.statements.append(statement)
        return _Aggregate()


def _user(org_id: uuid.UUID) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        org_id=org_id,
        branch_id=None,
        roles=["Administrator"],
        permissions={"applicant:read"},
    )


def test_simulated_wallet_evidence_is_reproducible_and_explicit() -> None:
    adapter = SimulatedWalletAdapter()

    first = adapter.fetch_transactions("applicant-123", months=2)
    second = adapter.fetch_transactions("applicant-123", months=2)

    assert first == second
    assert len(first) == 40
    assert all(item["is_simulated"] is True for item in first)
    assert {item["amount"] > 0 for item in first} == {True, False}


def test_transaction_page_uses_aggregate_cashflow_and_authorized_applicant() -> None:
    org_id = uuid.uuid4()
    applicant_id = uuid.uuid4()
    applicant = SimpleNamespace(id=applicant_id, organization_id=org_id, branch_id=None)
    transactions = [
        SimpleNamespace(
            id=uuid.uuid4(),
            txn_date=datetime.now(timezone.utc),
            amount=1000,
        )
    ]
    db = _Database(applicant, transactions)

    result = list_transactions(
        db, _user(org_id), applicant_id, source_type="wallet", limit=25, offset=0
    )

    assert result["items"] == transactions
    assert result["total"] == 3
    assert result["total_credits"] == 1500.0
    assert result["total_debits"] == 550.0
    assert result["net_cashflow"] == 950.0
    assert result["simulated_count"] == 3
    assert len(db.statements) == 2
