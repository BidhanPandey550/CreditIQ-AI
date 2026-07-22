"""Controlled vocabularies used across bounded contexts."""

from enum import Enum


class OrgType(str, Enum):
    bank = "bank"
    mfi = "mfi"
    cooperative = "cooperative"
    digital_lender = "digital_lender"


class OrgStatus(str, Enum):
    provisioning = "provisioning"
    active = "active"
    suspended = "suspended"
    offboarding = "offboarding"


class UserStatus(str, Enum):
    invited = "invited"
    active = "active"
    disabled = "disabled"


class LoanStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    ai_risk_analysis = "ai_risk_analysis"
    fraud_screening = "fraud_screening"
    officer_review = "officer_review"
    analyst_review = "analyst_review"
    needs_more_info = "needs_more_info"
    approved = "approved"
    rejected = "rejected"
    disbursed = "disbursed"
    active = "active"
    closed = "closed"
    defaulted = "defaulted"


class DecisionType(str, Enum):
    approve = "approve"
    reject = "reject"
    needs_more_info = "needs_more_info"


class RiskBand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class FraudSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FraudStatus(str, Enum):
    open = "open"
    confirmed = "confirmed"
    dismissed = "dismissed"


class TransactionSource(str, Enum):
    bank = "bank"
    wallet = "wallet"
    utility = "utility"


# Allowed loan workflow transitions (config-driven in production via workflow_definitions).
LOAN_TRANSITIONS: dict[LoanStatus, set[LoanStatus]] = {
    LoanStatus.draft: {LoanStatus.submitted},
    LoanStatus.submitted: {LoanStatus.under_review},
    LoanStatus.under_review: {LoanStatus.ai_risk_analysis, LoanStatus.needs_more_info},
    LoanStatus.ai_risk_analysis: {LoanStatus.fraud_screening},
    LoanStatus.fraud_screening: {LoanStatus.officer_review},
    LoanStatus.officer_review: {
        LoanStatus.analyst_review,
        LoanStatus.needs_more_info,
        LoanStatus.approved,
        LoanStatus.rejected,
    },
    LoanStatus.analyst_review: {
        LoanStatus.approved,
        LoanStatus.rejected,
        LoanStatus.needs_more_info,
    },
    LoanStatus.needs_more_info: {LoanStatus.under_review},
    LoanStatus.approved: {LoanStatus.disbursed},
    LoanStatus.disbursed: {LoanStatus.active},
    LoanStatus.active: {LoanStatus.closed, LoanStatus.defaulted},
    LoanStatus.defaulted: {LoanStatus.closed},
}
