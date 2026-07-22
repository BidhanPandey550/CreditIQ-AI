"""Tenant- and branch-scoped portfolio exports for analysis and audit workflows."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require
from app.core.data_scope import branch_predicate
from app.modules.credit_intelligence.models import CreditScore, RiskScore
from app.modules.audit import service as audit
from app.modules.loan.models import LoanApplication

router = APIRouter(prefix="/reports", tags=["reports"])


@dataclass(frozen=True)
class LoanExportRow:
    reference_no: str
    amount_npr: float
    tenor_months: int
    status: str
    risk_band: str
    default_probability: float | None
    credit_score: int | None
    created_at: datetime


def _loan_export_rows(db: Session, user: CurrentUser) -> list[LoanExportRow]:
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
    records = db.execute(
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
    return [
        LoanExportRow(
            reference_no=loan.reference_no,
            amount_npr=float(loan.amount),
            tenor_months=loan.tenor_months,
            status=loan.status.value if hasattr(loan.status, "value") else str(loan.status),
            risk_band=risk_band or "",
            default_probability=(
                float(default_probability) if default_probability is not None else None
            ),
            credit_score=credit_score,
            created_at=loan.created_at,
        )
        for loan, risk_band, default_probability, credit_score in records
    ]


def build_loan_portfolio_pdf(rows: list[LoanExportRow], generated_at: datetime) -> bytes:
    """Render a deterministic, paginated portfolio report without applicant PII."""
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="CreditIQ AI Loan Portfolio Report",
        author="CreditIQ AI",
        subject="Confidential tenant-scoped loan portfolio",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CreditIQTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )
    story: list[Any] = [
        Paragraph("CreditIQ AI — Loan Portfolio Report", title_style),
        Paragraph(
            f"Generated {generated_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
            f"{len(rows)} record(s) · CONFIDENTIAL",
            styles["Normal"],
        ),
        Spacer(1, 5 * mm),
    ]
    table_data: list[list[Any]] = [
        [
            "Reference",
            "Amount (NPR)",
            "Tenor",
            "Status",
            "Risk",
            "PD",
            "Score",
            "Created",
        ]
    ]
    for row in rows:
        table_data.append(
            [
                row.reference_no,
                f"{row.amount_npr:,.2f}",
                f"{row.tenor_months} mo",
                row.status.replace("_", " ").title(),
                row.risk_band.title() or "—",
                f"{row.default_probability:.1%}" if row.default_probability is not None else "—",
                str(row.credit_score) if row.credit_score is not None else "—",
                row.created_at.strftime("%Y-%m-%d"),
            ]
        )
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            34 * mm,
            31 * mm,
            20 * mm,
            30 * mm,
            20 * mm,
            20 * mm,
            18 * mm,
            27 * mm,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8fafc")],
                ),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (2, -1), "RIGHT"),
                ("ALIGN", (5, 1), (6, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    document.build(story)
    return output.getvalue()


@router.get("/loans.csv")
def export_loans_csv(
    user: CurrentUser = Depends(require("report:export")), db: Session = Depends(get_db)
) -> StreamingResponse:
    rows = _loan_export_rows(db, user)

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
    for row in rows:
        writer.writerow(
            [
                row.reference_no,
                row.amount_npr,
                row.tenor_months,
                row.status,
                row.risk_band,
                row.default_probability if row.default_probability is not None else "",
                row.credit_score if row.credit_score is not None else "",
                row.created_at.isoformat(),
            ]
        )
    buffer.seek(0)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="report.loans.export",
        entity_type="report",
        after={"format": "csv", "row_count": len(rows)},
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=loans_export.csv"},
    )


@router.get("/loans.pdf")
def export_loans_pdf(
    user: CurrentUser = Depends(require("report:export")), db: Session = Depends(get_db)
) -> Response:
    rows = _loan_export_rows(db, user)
    generated_at = datetime.now(timezone.utc)
    content = build_loan_portfolio_pdf(rows, generated_at)
    audit.record(
        db,
        org_id=user.org_id,
        actor_user_id=user.user_id,
        action="report.loans.export",
        entity_type="report",
        after={"format": "pdf", "row_count": len(rows)},
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=loans_portfolio.pdf"},
    )
