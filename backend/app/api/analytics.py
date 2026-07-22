"""Portfolio analytics — tenant-scoped aggregations for dashboards."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.core.config import settings
from app.core.data_scope import branch_predicate
from app.modules.credit_intelligence.models import CreditScore, RiskScore
from app.modules.loan.models import LoanApplication, LoanInstallment, LoanWorkflowEvent
from app.modules.organization.models import Branch
from app.shared.enums import LoanStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(
    user: CurrentUser = Depends(require("analytics:read")),
    db: Session = Depends(get_db),
) -> dict:
    org = user.org_id
    total = (
        db.scalar(
            select(func.count())
            .select_from(LoanApplication)
            .where(LoanApplication.organization_id == org)
            .where(branch_predicate(user, LoanApplication.branch_id))
        )
        or 0
    )

    def count_status(status: LoanStatus) -> int:
        return (
            db.scalar(
                select(func.count())
                .select_from(LoanApplication)
                .where(
                    LoanApplication.organization_id == org,
                    LoanApplication.status == status,
                    branch_predicate(user, LoanApplication.branch_id),
                )
            )
            or 0
        )

    approved = (
        count_status(LoanStatus.approved)
        + count_status(LoanStatus.disbursed)
        + count_status(LoanStatus.active)
        + count_status(LoanStatus.closed)
    )
    rejected = count_status(LoanStatus.rejected)
    decided = approved + rejected

    # Count only the latest assessment per loan. Historical rescoring rows must not inflate the
    # portfolio distribution.
    ranked_risk = (
        select(
            RiskScore.loan_id,
            RiskScore.band,
            func.row_number()
            .over(partition_by=RiskScore.loan_id, order_by=RiskScore.created_at.desc())
            .label("recency_rank"),
        )
        .join(LoanApplication, LoanApplication.id == RiskScore.loan_id)
        .where(
            RiskScore.organization_id == org,
            branch_predicate(user, LoanApplication.branch_id),
        )
        .subquery()
    )
    risk_rows = db.execute(
        select(ranked_risk.c.band, func.count())
        .where(ranked_risk.c.recency_rank == 1)
        .group_by(ranked_risk.c.band)
    ).all()
    risk_distribution = {band: n for band, n in risk_rows}

    ranked_credit = (
        select(
            CreditScore.loan_id,
            CreditScore.score,
            func.row_number()
            .over(partition_by=CreditScore.loan_id, order_by=CreditScore.created_at.desc())
            .label("recency_rank"),
        )
        .join(LoanApplication, LoanApplication.id == CreditScore.loan_id)
        .where(
            CreditScore.organization_id == org,
            branch_predicate(user, LoanApplication.branch_id),
        )
        .subquery()
    )
    avg_score = db.scalar(
        select(func.avg(ranked_credit.c.score)).where(ranked_credit.c.recency_rank == 1)
    )

    exposure = (
        db.scalar(
            select(func.coalesce(func.sum(LoanApplication.amount), 0)).where(
                LoanApplication.organization_id == org,
                LoanApplication.status.in_([LoanStatus.disbursed, LoanStatus.active]),
                branch_predicate(user, LoanApplication.branch_id),
            )
        )
        or 0
    )

    return {
        "total_applications": total,
        "approved": approved,
        "rejected": rejected,
        "pending": total - decided,
        "approval_rate": round(approved / decided, 3) if decided else 0,
        "rejection_rate": round(rejected / decided, 3) if decided else 0,
        "average_credit_score": round(float(avg_score), 1) if avg_score is not None else None,
        "risk_distribution": {
            "low": risk_distribution.get("low", 0),
            "medium": risk_distribution.get("medium", 0),
            "high": risk_distribution.get("high", 0),
        },
        "portfolio_exposure": float(exposure),
    }


@router.get("/status-breakdown")
def status_breakdown(
    user: CurrentUser = Depends(require("analytics:read")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(LoanApplication.status, func.count())
        .where(LoanApplication.organization_id == user.org_id)
        .where(branch_predicate(user, LoanApplication.branch_id))
        .group_by(LoanApplication.status)
    ).all()
    return {status.value if hasattr(status, "value") else str(status): n for status, n in rows}


@router.get("/monthly-trends")
def monthly_trends(
    user: CurrentUser = Depends(require("analytics:read")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Monthly applications and actual disbursement workflow events."""
    application_month = func.date_trunc("month", LoanApplication.created_at).label("month")
    application_rows = db.execute(
        select(application_month, func.count().label("applications"))
        .where(
            LoanApplication.organization_id == user.org_id,
            branch_predicate(user, LoanApplication.branch_id),
        )
        .group_by(application_month)
    ).all()

    disbursement_month = func.date_trunc("month", LoanWorkflowEvent.created_at).label("month")
    disbursement_rows = db.execute(
        select(
            disbursement_month,
            func.count().label("disbursements"),
            func.coalesce(func.sum(LoanApplication.amount), 0).label("amount"),
        )
        .join(LoanApplication, LoanApplication.id == LoanWorkflowEvent.loan_id)
        .where(
            LoanWorkflowEvent.organization_id == user.org_id,
            LoanWorkflowEvent.to_status == LoanStatus.disbursed,
            branch_predicate(user, LoanApplication.branch_id),
        )
        .group_by(disbursement_month)
    ).all()

    by_month: dict[str, dict] = {}
    for month, applications in application_rows:
        key = month.date().isoformat()
        by_month[key] = {
            "month": key,
            "applications": applications,
            "disbursements": 0,
            "disbursed_amount": 0.0,
        }
    for month, disbursements, amount in disbursement_rows:
        key = month.date().isoformat()
        row = by_month.setdefault(
            key,
            {"month": key, "applications": 0, "disbursements": 0, "disbursed_amount": 0.0},
        )
        row["disbursements"] = disbursements
        row["disbursed_amount"] = float(amount)
    return [by_month[key] for key in sorted(by_month)[-12:]]


@router.get("/branch-performance")
def branch_performance(
    user: CurrentUser = Depends(require("analytics:read")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Compare application decisions and active exposure within the caller's branch scope."""
    approved_statuses = [
        LoanStatus.approved,
        LoanStatus.disbursed,
        LoanStatus.active,
        LoanStatus.closed,
    ]
    rows = db.execute(
        select(
            Branch.id,
            Branch.name,
            func.count(LoanApplication.id).label("applications"),
            func.count(LoanApplication.id)
            .filter(LoanApplication.status.in_(approved_statuses))
            .label("approved"),
            func.count(LoanApplication.id)
            .filter(LoanApplication.status == LoanStatus.rejected)
            .label("rejected"),
            func.coalesce(
                func.sum(LoanApplication.amount).filter(
                    LoanApplication.status.in_([LoanStatus.disbursed, LoanStatus.active])
                ),
                0,
            ).label("exposure"),
        )
        .outerjoin(
            LoanApplication,
            (LoanApplication.branch_id == Branch.id)
            & (LoanApplication.organization_id == user.org_id),
        )
        .where(
            Branch.organization_id == user.org_id,
            branch_predicate(user, Branch.id),
        )
        .group_by(Branch.id, Branch.name)
        .order_by(Branch.name)
    ).all()
    return [
        {
            "branch_id": branch_id,
            "branch_name": name,
            "applications": applications,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": round(approved / (approved + rejected), 3)
            if approved + rejected
            else 0,
            "exposure": float(exposure),
        }
        for branch_id, name, applications, approved, rejected, exposure in rows
    ]


def calculate_delinquency_metrics(
    rows: list[tuple], *, as_of: date, thresholds: list[int], grace_days: int
) -> dict:
    """Calculate aggregate arrears and PAR using outstanding scheduled balances."""
    loan_balances: dict[uuid.UUID, Decimal] = {}
    loan_max_dpd: dict[uuid.UUID, int] = {}
    overdue_amount = Decimal(0)
    for loan_id, due_date, principal_due, interest_due, principal_paid, interest_paid in rows:
        outstanding = max(
            Decimal(0),
            Decimal(str(principal_due))
            + Decimal(str(interest_due))
            - Decimal(str(principal_paid))
            - Decimal(str(interest_paid)),
        )
        if outstanding == 0:
            continue
        dpd = max(0, (as_of - due_date).days)
        loan_balances[loan_id] = loan_balances.get(loan_id, Decimal(0)) + outstanding
        loan_max_dpd[loan_id] = max(loan_max_dpd.get(loan_id, 0), dpd)
        if dpd > grace_days:
            overdue_amount += outstanding

    portfolio_balance = sum(loan_balances.values(), Decimal(0))
    par = {}
    for threshold in thresholds:
        at_risk = sum(
            (
                balance
                for loan_id, balance in loan_balances.items()
                if loan_max_dpd[loan_id] >= threshold
            ),
            Decimal(0),
        )
        par[str(threshold)] = {
            "balance": float(at_risk),
            "ratio": round(float(at_risk / portfolio_balance), 4) if portfolio_balance else 0,
        }
    return {
        "portfolio_outstanding": float(portfolio_balance),
        "overdue_amount": float(overdue_amount),
        "delinquent_loans": sum(dpd > grace_days for dpd in loan_max_dpd.values()),
        "max_days_past_due": max(loan_max_dpd.values(), default=0),
        "par": par,
    }


@router.get("/delinquency")
def delinquency(
    user: CurrentUser = Depends(require("analytics:read")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(
            LoanInstallment.loan_id,
            LoanInstallment.due_date,
            LoanInstallment.principal_due,
            LoanInstallment.interest_due,
            LoanInstallment.principal_paid,
            LoanInstallment.interest_paid,
        )
        .join(LoanApplication, LoanApplication.id == LoanInstallment.loan_id)
        .where(
            LoanInstallment.organization_id == user.org_id,
            LoanApplication.status.in_([LoanStatus.active, LoanStatus.defaulted]),
            branch_predicate(user, LoanApplication.branch_id),
        )
    ).all()
    return calculate_delinquency_metrics(
        list(rows),
        as_of=date.today(),
        thresholds=settings.par_threshold_days,
        grace_days=settings.servicing_grace_days,
    )
