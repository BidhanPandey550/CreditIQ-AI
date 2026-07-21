"""Database engine, session factory, and tenant-scoped session helper.

The critical function here is `tenant_session`: it opens a transaction and sets the
Postgres session variable `app.current_org`, which the Row-Level Security policies read.
Because the app connects as a non-superuser role, RLS is *enforced by the database* —
a query can never return another tenant's rows even if an app-level filter is missing.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@contextmanager
def tenant_session(org_id: str | None) -> Iterator[Session]:
    """Yield a session bound to a tenant. RLS filters everything to `org_id`."""
    session = SessionLocal()
    try:
        if org_id is not None:
            # set_config(..., is_local=true) => scoped to this transaction only.
            session.execute(
                text("SELECT set_config('app.current_org', :org, true)"), {"org": str(org_id)}
            )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def admin_session() -> Iterator[Session]:
    """Session without a tenant filter — for platform bootstrap/seed and super-admin ops.
    Use sparingly and audit every use."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
