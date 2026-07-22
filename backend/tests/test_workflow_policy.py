"""Tenant workflow choices cannot bypass mandatory lending safety stages."""

from decimal import Decimal
from types import SimpleNamespace
import uuid

import pytest
from pydantic import ValidationError

from app.modules.loan.workflow import LoanWorkflowPolicy, LoanWorkflowSettings
from app.modules.loan.models import LoanApplication
from app.modules.loan.service import transition
from app.modules.organization.models import Organization
from app.core.deps import CurrentUser
from app.core.exceptions import DomainRuleError
from app.shared.enums import LoanStatus


def test_optional_policy_allows_officer_decision_or_analyst_escalation() -> None:
    policy = LoanWorkflowPolicy(LoanWorkflowSettings())

    allowed = policy.allowed(LoanStatus.officer_review, amount=Decimal("500000"))

    assert {LoanStatus.approved, LoanStatus.rejected, LoanStatus.analyst_review}.issubset(allowed)


def test_required_policy_forces_analyst_review_before_decision() -> None:
    policy = LoanWorkflowPolicy(LoanWorkflowSettings(analyst_review_policy="required"))

    officer = policy.allowed(LoanStatus.officer_review, amount=100)
    analyst = policy.allowed(LoanStatus.analyst_review, amount=100)

    assert LoanStatus.analyst_review in officer
    assert LoanStatus.approved not in officer
    assert LoanStatus.rejected not in officer
    assert {LoanStatus.approved, LoanStatus.rejected}.issubset(analyst)


def test_amount_policy_applies_at_configured_inclusive_threshold() -> None:
    policy = LoanWorkflowPolicy(
        LoanWorkflowSettings(
            analyst_review_policy="amount_threshold",
            analyst_review_amount_threshold=1_000_000,
        )
    )

    assert LoanStatus.approved in policy.allowed(LoanStatus.officer_review, amount=999_999)
    assert LoanStatus.approved not in policy.allowed(LoanStatus.officer_review, amount=1_000_000)


def test_optional_stages_can_be_disabled_without_changing_mandatory_path() -> None:
    policy = LoanWorkflowPolicy(
        LoanWorkflowSettings(
            allow_needs_more_information=False,
            allow_default_classification=False,
        )
    )

    assert LoanStatus.needs_more_info not in policy.allowed(LoanStatus.under_review, amount=100)
    assert LoanStatus.defaulted not in policy.allowed(LoanStatus.active, amount=100)
    assert policy.allowed(LoanStatus.ai_risk_analysis, amount=100) == {LoanStatus.fraud_screening}


def test_threshold_configuration_is_structurally_validated() -> None:
    with pytest.raises(ValidationError, match="threshold is required"):
        LoanWorkflowSettings(analyst_review_policy="amount_threshold")
    with pytest.raises(ValidationError, match="only for threshold policy"):
        LoanWorkflowSettings(analyst_review_amount_threshold=50_000)


def test_transition_service_enforces_the_tenant_workflow_policy() -> None:
    org_id = uuid.uuid4()
    loan = SimpleNamespace(
        id=uuid.uuid4(),
        applicant_id=uuid.uuid4(),
        branch_id=None,
        amount=Decimal("250000"),
        status=LoanStatus.officer_review,
    )
    organization = SimpleNamespace(
        id=org_id,
        settings={"loan_workflow": {"analyst_review_policy": "required"}},
    )

    class Database:
        def get(self, model, record_id):
            if model is LoanApplication:
                return loan
            if model is Organization:
                return organization
            return None

    user = CurrentUser(
        user_id=uuid.uuid4(),
        org_id=org_id,
        branch_id=None,
        roles=["Administrator"],
        permissions={"loan:approve"},
    )

    with pytest.raises(DomainRuleError, match="Allowed:.*analyst_review"):
        transition(Database(), user, loan.id, LoanStatus.approved, "Officer approval")  # type: ignore[arg-type]
