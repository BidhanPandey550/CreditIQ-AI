"""Add loan servicing, schedules, and repayment ledger.

Revision ID: 92c61cc1938f
Revises: 748dadfd87d2
Create Date: 2026-07-22 04:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "92c61cc1938f"
down_revision: Union[str, None] = "748dadfd87d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ("loan_disbursements", "loan_installments", "loan_repayments")
SERVICING_PERMISSION_ID = "d8473e3d-8053-4cf5-a7e0-73a2cd4f05bc"


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "loan_disbursements",
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("annual_interest_rate", sa.Numeric(8, 5), nullable=False),
        sa.Column("disbursed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("external_reference", sa.String(120), nullable=True),
        sa.Column("disbursed_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_common_columns(),
        sa.ForeignKeyConstraint(["loan_id"], ["loan_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["disbursed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loan_id"),
    )
    op.create_index("ix_loan_disbursements_loan_id", "loan_disbursements", ["loan_id"])
    op.create_index(
        "ix_loan_disbursements_organization_id",
        "loan_disbursements",
        ["organization_id"],
    )

    op.create_table(
        "loan_installments",
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("principal_due", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest_due", sa.Numeric(18, 2), nullable=False),
        sa.Column("principal_paid", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest_paid", sa.Numeric(18, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        *_common_columns(),
        sa.ForeignKeyConstraint(["loan_id"], ["loan_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loan_id", "sequence_no", name="uq_installment_loan_sequence"),
    )
    op.create_index("ix_loan_installments_due_date", "loan_installments", ["due_date"])
    op.create_index("ix_loan_installments_loan_id", "loan_installments", ["loan_id"])
    op.create_index(
        "ix_loan_installments_organization_id", "loan_installments", ["organization_id"]
    )

    op.create_table(
        "loan_repayments",
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_reference", sa.String(120), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_common_columns(),
        sa.ForeignKeyConstraint(["loan_id"], ["loan_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "external_reference",
            name="uq_repayment_org_external_reference",
        ),
    )
    op.create_index("ix_loan_repayments_loan_id", "loan_repayments", ["loan_id"])
    op.create_index("ix_loan_repayments_organization_id", "loan_repayments", ["organization_id"])

    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY tenant_isolation ON "{table}" '
            "USING (organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid) "
            "WITH CHECK (organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid)"
        )

    op.execute(
        "INSERT INTO permissions (id, code, description) "
        f"VALUES ('{SERVICING_PERMISSION_ID}'::uuid, 'loan:service', "
        "'Record repayments and manage active loan servicing') "
        "ON CONFLICT (code) DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT roles.id, permissions.id FROM roles CROSS JOIN permissions "
        "WHERE roles.name IN ('Branch Manager', 'Administrator', 'Super Admin') "
        "AND permissions.code = 'loan:service' ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code = 'loan:service')"
    )
    op.execute("DELETE FROM permissions WHERE code = 'loan:service'")
    for table in reversed(TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"')
        op.drop_table(table)
