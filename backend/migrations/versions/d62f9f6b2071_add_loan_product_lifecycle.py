"""add loan product lifecycle

Revision ID: d62f9f6b2071
Revises: b523e91570b8
Create Date: 2026-07-22 16:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d62f9f6b2071"
down_revision: Union[str, None] = "b523e91570b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("loan_products", sa.Column("code", sa.String(length=30), nullable=True))
    op.execute(
        "UPDATE loan_products SET code = 'LEGACY-' || UPPER(SUBSTRING(REPLACE(id::text, '-', '') FROM 1 FOR 8)) WHERE code IS NULL"
    )
    op.alter_column("loan_products", "code", nullable=False)
    op.add_column(
        "loan_products",
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
    )
    op.create_unique_constraint(
        "uq_loan_product_org_code", "loan_products", ["organization_id", "code"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_loan_product_org_code", "loan_products", type_="unique")
    op.drop_column("loan_products", "status")
    op.drop_column("loan_products", "code")
