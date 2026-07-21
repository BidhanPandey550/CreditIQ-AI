from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import admin_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    db_ok = True
    try:
        with admin_session() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
