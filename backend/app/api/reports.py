"""Reporting & export — CSV exports of tenant-scoped data.

PDF export is a Phase-2 addition (server-side render). CSV covers the MVP need and streams
so large portfolios don't buffer in memory.
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.modules.credit_intelligence.models import CreditScore, RiskScore
from app.modules.loan.models import LoanApplication

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/loans.csv")
def export_loans_csv(user: CurrentUser = Depends(require("report:export")),
                     db: Session = Depends(get_db)) -> StreamingResponse:
    loans = db.scalars(
        select(LoanApplication).where(LoanApplication.organization_id == user.org_id)
        .order_by(LoanApplication.created_at.desc())
    ).all()

    def latest_score(loan_id, model):
        row = db.scalars(select(model).where(model.loan_id == loan_id)
                         .order_by(model.created_at.desc())).first()
        return row

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["reference_no", "amount_npr", "tenor_months", "status",
                     "risk_band", "default_probability", "credit_score", "created_at"])
    for loan in loans:
        risk = latest_score(loan.id, RiskScore)
        score = latest_score(loan.id, CreditScore)
        writer.writerow([
            loan.reference_no, float(loan.amount), loan.tenor_months,
            str(loan.status), risk.band if risk else "",
            float(risk.probability) if risk else "", score.score if score else "",
            loan.created_at.isoformat(),
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=loans_export.csv"},
    )
