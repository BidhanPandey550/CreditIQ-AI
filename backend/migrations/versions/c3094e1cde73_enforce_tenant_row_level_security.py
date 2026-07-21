"""enforce tenant row level security

Revision ID: c3094e1cde73
Revises: 1bc1f3336299
Create Date: 2026-07-22 00:15:40.697121
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c3094e1cde73"
down_revision: Union[str, None] = "1bc1f3336299"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY tenant_isolation ON "{table}" '
            "USING (organization_id = current_setting('app.current_org', true)::uuid) "
            "WITH CHECK (organization_id = current_setting('app.current_org', true)::uuid)"
        )


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')


TENANT_TABLES = (
    "applicants",
    "kyc_records",
    "employment_records",
    "business_records",
    "income_records",
    "expense_records",
    "asset_records",
    "liability_records",
    "existing_loans",
    "transaction_records",
    "financial_documents",
    "loan_products",
    "loan_applications",
    "loan_workflow_events",
    "loan_decisions",
    "risk_scores",
    "credit_scores",
    "default_predictions",
    "fraud_alerts",
    "ai_explanations",
    "audit_logs",
    "notifications",
)
