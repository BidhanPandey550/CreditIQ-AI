import httpx
from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from app.core.config import settings
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
    try:
        redis_ok = bool(Redis.from_url(settings.redis_url).ping())
    except Exception:
        redis_ok = False
    try:
        response = httpx.get(f"{settings.ml_engine_url.rstrip('/')}/health", timeout=1.0)
        ml_ok = response.is_success
    except httpx.HTTPError:
        ml_ok = False
    ready = db_ok and redis_ok and ml_ok
    return {
        "status": "ok" if ready else "degraded",
        "database": db_ok,
        "redis": redis_ok,
        "ml_engine": ml_ok,
    }
