"""Harden RLS policies against an empty pooled tenant context.

Revision ID: 0d870f3296be
Revises: c3094e1cde73
Create Date: 2026-07-22 01:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

from app.db.all_models import RLS_TABLES


revision: str = "0d870f3296be"
down_revision: Union[str, None] = "c3094e1cde73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f'DROP POLICY tenant_isolation ON "{table}"')
        op.execute(
            f'CREATE POLICY tenant_isolation ON "{table}" '
            "USING ("
            "organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid"
            ") WITH CHECK ("
            "organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid"
            ")"
        )


def downgrade() -> None:
    for table in reversed(RLS_TABLES):
        op.execute(f'DROP POLICY tenant_isolation ON "{table}"')
        op.execute(
            f'CREATE POLICY tenant_isolation ON "{table}" '
            "USING (organization_id = current_setting('app.current_org', true)::uuid) "
            "WITH CHECK (organization_id = current_setting('app.current_org', true)::uuid)"
        )
