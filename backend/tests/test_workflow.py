"""Loan state-machine invariants (pure, no DB required)."""

from app.shared.enums import LOAN_TRANSITIONS, LoanStatus


def test_draft_can_only_go_to_submitted():
    assert LOAN_TRANSITIONS[LoanStatus.draft] == {LoanStatus.submitted}


def test_cannot_skip_from_submitted_to_approved():
    assert LoanStatus.approved not in LOAN_TRANSITIONS[LoanStatus.submitted]


def test_officer_review_can_approve_or_reject():
    allowed = LOAN_TRANSITIONS[LoanStatus.officer_review]
    assert LoanStatus.approved in allowed
    assert LoanStatus.rejected in allowed


def test_approved_leads_to_disbursed():
    assert LOAN_TRANSITIONS[LoanStatus.approved] == {LoanStatus.disbursed}


def test_terminal_states_have_no_forward_edges():
    assert LoanStatus.rejected not in LOAN_TRANSITIONS
    assert LoanStatus.closed not in LOAN_TRANSITIONS


def test_defaulted_loan_can_close_after_full_repayment():
    assert LOAN_TRANSITIONS[LoanStatus.defaulted] == {LoanStatus.closed}
