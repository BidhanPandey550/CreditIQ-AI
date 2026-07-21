"""Aggregate all v1 routers under /api/v1."""

from fastapi import APIRouter

from app.api import analytics, health, reports
from app.modules.applicant.router import router as applicant_router
from app.modules.identity.router import auth_router, users_router
from app.modules.loan.router import router as loan_router
from app.modules.organization.router import router as organization_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(organization_router)
api_router.include_router(applicant_router)
api_router.include_router(loan_router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)
