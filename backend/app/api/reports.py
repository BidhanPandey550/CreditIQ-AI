"""Reporting & export — CSV exports of tenant-scoped data.

PDF export is a Phase-2 addition (server-side render). CSV covers the MVP need and streams
so large portfolios don't buffer in memory.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.core.data_scope import branch_predicate
from app.modules.credit_intelligence.models import CreditScore, RiskScore
from app.modules.loan.models import LoanApplication

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/loans.csv")
def export_loans_csv(
    user: CurrentUser = Depends(require("report:export")), db: Session = Depends(get_db)
) -> StreamingResponse:
    latest_risk = (
        select(
            RiskScore.loan_id,
            RiskScore.band,
            RiskScore.probability,
            func.row_number()
            .over(partition_by=RiskScore.loan_id, order_by=RiskScore.created_at.desc())
            .label("recency_rank"),
        )
        .where(RiskScore.organization_id == user.org_id)
        .subquery()
    )
    latest_credit = (
        select(
            CreditScore.loan_id,
            CreditScore.score,
            func.row_number()
            .over(partition_by=CreditScore.loan_id, order_by=CreditScore.created_at.desc())
            .label("recency_rank"),
        )
        .where(CreditScore.organization_id == user.org_id)
        .subquery()
    )
    rows = db.execute(
        select(
            LoanApplication,
            latest_risk.c.band,
            latest_risk.c.probability,
            latest_credit.c.score,
        )
        .outerjoin(
            latest_risk,
            (latest_risk.c.loan_id == LoanApplication.id) & (latest_risk.c.recency_rank == 1),
        )
        .outerjoin(
            latest_credit,
            (latest_credit.c.loan_id == LoanApplication.id) & (latest_credit.c.recency_rank == 1),
        )
        .where(LoanApplication.organization_id == user.org_id)
        .where(branch_predicate(user, LoanApplication.branch_id))
        .order_by(LoanApplication.created_at.desc())
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "reference_no",
            "amount_npr",
            "tenor_months",
            "status",
            "risk_band",
            "default_probability",
            "credit_score",
            "created_at",
        ]
    )
    for loan, risk_band, default_probability, credit_score in rows:
        writer.writerow(
            [
                loan.reference_no,
                float(loan.amount),
                loan.tenor_months,
                str(loan.status),
                risk_band or "",
                float(default_probability) if default_probability is not None else "",
                credit_score if credit_score is not None else "",
                loan.created_at.isoformat(),
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=loans_export.csv"},
    )
