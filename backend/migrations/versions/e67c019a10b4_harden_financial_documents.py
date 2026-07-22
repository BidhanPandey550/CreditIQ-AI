"""Harden financial document metadata and permissions.

Revision ID: e67c019a10b4
Revises: 92c61cc1938f
Create Date: 2026-07-22 04:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e67c019a10b4"
down_revision: Union[str, None] = "92c61cc1938f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DOCUMENT_READ_ID = "e5d22920-8901-4ef4-a113-5e0ad56973f0"
DOCUMENT_UPLOAD_ID = "d31a4438-1327-4322-8114-7e02dbeb380d"


def upgrade() -> None:
    op.add_column("financial_documents", sa.Column("original_filename", sa.String(255)))
    op.add_column("financial_documents", sa.Column("content_type", sa.String(100)))
    op.add_column("financial_documents", sa.Column("size_bytes", sa.Integer()))
    op.add_column("financial_documents", sa.Column("uploaded_by", sa.Uuid()))
    op.create_foreign_key(
        "fk_financial_documents_uploaded_by_users",
        "financial_documents",
        "users",
        ["uploaded_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "INSERT INTO permissions (id, code, description) VALUES "
        f"('{DOCUMENT_READ_ID}'::uuid, 'document:read', "
        "'View authorized applicant financial documents'), "
        f"('{DOCUMENT_UPLOAD_ID}'::uuid, 'document:upload', "
        "'Upload applicant financial documents') ON CONFLICT (code) DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT roles.id, permissions.id FROM roles CROSS JOIN permissions "
        "WHERE ((roles.name IN ('Applicant', 'Loan Officer', 'Administrator') "
        "AND permissions.code IN ('document:read', 'document:upload')) "
        "OR (roles.name IN ('Risk Analyst', 'Branch Manager') "
        "AND permissions.code = 'document:read') "
        "OR roles.name = 'Super Admin') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code IN ('document:read', 'document:upload'))"
    )
    op.execute("DELETE FROM permissions WHERE code IN ('document:read', 'document:upload')")
    op.drop_constraint(
        "fk_financial_documents_uploaded_by_users", "financial_documents", type_="foreignkey"
    )
    op.drop_column("financial_documents", "uploaded_by")
    op.drop_column("financial_documents", "size_bytes")
    op.drop_column("financial_documents", "content_type")
    op.drop_column("financial_documents", "original_filename")
