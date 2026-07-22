"""Prove PostgreSQL enforces tenant isolation independently of application filters."""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.db.all_models import RLS_TABLES


ADMIN_DATABASE_URL = os.getenv("TEST_ADMIN_DATABASE_URL")
APP_DATABASE_URL = os.getenv("TEST_APP_DATABASE_URL")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not ADMIN_DATABASE_URL or not APP_DATABASE_URL,
        reason="live PostgreSQL integration URLs are not configured",
    ),
]


def _set_tenant(connection: object, organization_id: uuid.UUID) -> None:
    connection.execute(  # type: ignore[attr-defined]
        text("SELECT set_config('app.current_org', :organization_id, true)"),
        {"organization_id": str(organization_id)},
    )


def test_database_blocks_cross_tenant_reads_and_writes() -> None:
    """The application role can only see and create rows for its active organization."""
    organization_a = uuid.uuid4()
    organization_b = uuid.uuid4()
    applicant_a = uuid.uuid4()
    applicant_b = uuid.uuid4()
    admin_engine = create_engine(ADMIN_DATABASE_URL, future=True)
    app_engine = create_engine(APP_DATABASE_URL, future=True)

    try:
        with admin_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO organizations (id, name, type, status, settings) "
                    "VALUES (:a, 'RLS Test A', 'bank', 'active', '{}'), "
                    "(:b, 'RLS Test B', 'bank', 'active', '{}')"
                ),
                {"a": organization_a, "b": organization_b},
            )

        with app_engine.begin() as connection:
            _set_tenant(connection, organization_a)
            connection.execute(
                text(
                    "INSERT INTO applicants "
                    "(id, organization_id, full_name, is_self_employed) "
                    "VALUES (:id, :organization_id, 'Tenant A Applicant', false)"
                ),
                {"id": applicant_a, "organization_id": organization_a},
            )

        with app_engine.begin() as connection:
            _set_tenant(connection, organization_b)
            connection.execute(
                text(
                    "INSERT INTO applicants "
                    "(id, organization_id, full_name, is_self_employed) "
                    "VALUES (:id, :organization_id, 'Tenant B Applicant', false)"
                ),
                {"id": applicant_b, "organization_id": organization_b},
            )

        with app_engine.connect() as connection, connection.begin():
            _set_tenant(connection, organization_a)
            visible_ids = set(connection.execute(text("SELECT id FROM applicants")).scalars())
            assert visible_ids == {applicant_a}

        with app_engine.connect() as connection, connection.begin():
            _set_tenant(connection, organization_b)
            visible_ids = set(connection.execute(text("SELECT id FROM applicants")).scalars())
            assert visible_ids == {applicant_b}

        with app_engine.connect() as connection, connection.begin():
            assert connection.scalar(text("SELECT count(*) FROM applicants")) == 0

        with pytest.raises(DBAPIError), app_engine.begin() as connection:
            _set_tenant(connection, organization_a)
            connection.execute(
                text(
                    "INSERT INTO applicants "
                    "(id, organization_id, full_name, is_self_employed) "
                    "VALUES (:id, :organization_id, 'Forbidden Applicant', false)"
                ),
                {"id": uuid.uuid4(), "organization_id": organization_b},
            )
    finally:
        with admin_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM organizations WHERE id IN (:a, :b)"),
                {"a": organization_a, "b": organization_b},
            )
        app_engine.dispose()
        admin_engine.dispose()


def test_every_tenant_table_has_forced_rls_and_policy() -> None:
    """New tenant tables cannot silently ship without enforced database isolation."""
    engine = create_engine(ADMIN_DATABASE_URL, future=True)
    try:
        with engine.connect() as connection:
            protected = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT c.relname FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND c.relrowsecurity AND c.relforcerowsecurity"
                    )
                )
            }
            policies = {
                row[0]
                for row in connection.execute(
                    text("SELECT tablename FROM pg_policies WHERE schemaname = 'public'")
                )
            }
        assert set(RLS_TABLES) <= protected
        assert set(RLS_TABLES) <= policies
    finally:
        engine.dispose()
