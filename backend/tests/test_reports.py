from __future__ import annotations

from datetime import datetime, timezone

from app.api.reports import LoanExportRow, build_loan_portfolio_pdf


def test_portfolio_pdf_is_valid_and_handles_multiple_rows() -> None:
    rows = [
        LoanExportRow(
            reference_no=f"LN-{index:04d}",
            amount_npr=250_000 + index,
            tenor_months=24,
            status="under_review",
            risk_band="medium",
            default_probability=0.18,
            credit_score=690,
            created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
        for index in range(75)
    ]

    content = build_loan_portfolio_pdf(rows, datetime(2026, 7, 22, tzinfo=timezone.utc))

    assert content.startswith(b"%PDF-")
    assert content.endswith(b"%%EOF\n")
    assert len(content) > 5_000


def test_portfolio_pdf_supports_empty_portfolios() -> None:
    content = build_loan_portfolio_pdf([], datetime(2026, 7, 22, tzinfo=timezone.utc))
    assert content.startswith(b"%PDF-")
