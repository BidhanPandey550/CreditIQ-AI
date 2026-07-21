"""Portfolio analytics — tenant-scoped aggregations for dashboards."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.modules.credit_intelligence.models import CreditScore, RiskScore
from app.modules.loan.models import LoanApplication
from app.shared.enums import LoanStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(
    user: CurrentUser = Depends(require("analytics:read")), db: Session = Depends(get_db)
) -> dict:
    org = user.org_id
    total = (
        db.scalar(
            select(func.count())
            .select_from(LoanApplication)
            .where(LoanApplication.organization_id == org)
        )
        or 0
    )

    def count_status(status: LoanStatus) -> int:
        return (
            db.scalar(
                select(func.count())
                .select_from(LoanApplication)
                .where(LoanApplication.organization_id == org, LoanApplication.status == status)
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

    # Risk band distribution (latest per loan is approximated by all rows for MVP)
    risk_rows = db.execute(
        select(RiskScore.band, func.count())
        .where(RiskScore.organization_id == org)
        .group_by(RiskScore.band)
    ).all()
    risk_distribution = {band: n for band, n in risk_rows}

    avg_score = db.scalar(
        select(func.avg(CreditScore.score)).where(CreditScore.organization_id == org)
    )

    exposure = (
        db.scalar(
            select(func.coalesce(func.sum(LoanApplication.amount), 0)).where(
                LoanApplication.organization_id == org,
                LoanApplication.status.in_([LoanStatus.disbursed, LoanStatus.active]),
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
    user: CurrentUser = Depends(require("analytics:read")), db: Session = Depends(get_db)
) -> dict:
    rows = db.execute(
        select(LoanApplication.status, func.count())
        .where(LoanApplication.organization_id == user.org_id)
        .group_by(LoanApplication.status)
    ).all()
    return {status.value if hasattr(status, "value") else str(status): n for status, n in rows}
