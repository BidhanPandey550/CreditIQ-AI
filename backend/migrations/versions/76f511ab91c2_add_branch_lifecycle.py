"""Add branch code uniqueness and lifecycle status.

Revision ID: 76f511ab91c2
Revises: e67c019a10b4
Create Date: 2026-07-22 05:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "76f511ab91c2"
down_revision: Union[str, None] = "e67c019a10b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "branches",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.create_unique_constraint("uq_branch_org_code", "branches", ["organization_id", "code"])


def downgrade() -> None:
    op.drop_constraint("uq_branch_org_code", "branches", type_="unique")
    op.drop_column("branches", "status")
