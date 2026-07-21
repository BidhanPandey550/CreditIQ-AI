"""Add tenant-scoped API key lifecycle storage.

Revision ID: 748dadfd87d2
Revises: 218f34e3390e
Create Date: 2026-07-22 03:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "748dadfd87d2"
down_revision: Union[str, None] = "218f34e3390e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
TENANT_TABLES = ("api_keys",)


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("prefix", sa.String(length=24), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
        sa.UniqueConstraint("prefix"),
    )
    op.create_index(op.f("ix_api_keys_organization_id"), "api_keys", ["organization_id"])
    op.create_index(op.f("ix_api_keys_prefix"), "api_keys", ["prefix"])
    op.create_index(op.f("ix_api_keys_revoked_at"), "api_keys", ["revoked_at"])
    op.execute('ALTER TABLE "api_keys" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "api_keys" FORCE ROW LEVEL SECURITY')
    op.execute(
        'CREATE POLICY tenant_isolation ON "api_keys" '
        "USING (organization_id = current_setting('app.current_org', true)::uuid) "
        "WITH CHECK (organization_id = current_setting('app.current_org', true)::uuid)"
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS tenant_isolation ON "api_keys"')
    op.drop_index(op.f("ix_api_keys_revoked_at"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_prefix"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_organization_id"), table_name="api_keys")
    op.drop_table("api_keys")
