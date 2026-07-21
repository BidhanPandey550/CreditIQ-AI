"""Database bootstrap: create tables, apply Row-Level Security, and seed demo data.

Runs automatically on backend startup (see app/main.py lifespan). Idempotent.
"""

from __future__ import annotations

import sys

from sqlalchemy import select, text

from app.core.deps import CurrentUser
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.all_models import RLS_TABLES
from app.db.base import Base
from app.db.session import admin_session, engine, tenant_session
from app.modules.applicant.models import TransactionRecord
from app.modules.applicant.schemas import (
    ApplicantCreate,
    EmploymentIn,
    ExistingLoanIn,
    ExpenseIn,
    IncomeIn,
    LiabilityIn,
)
from app.modules.applicant.service import create_applicant
from app.modules.credit_intelligence.service import analyze_loan
from app.modules.identity.models import Role, User
from app.modules.identity.service import ensure_rbac
from app.modules.loan.schemas import LoanCreate
from app.modules.loan.service import create_loan, transition
from app.modules.organization.models import Branch, Organization
from app.shared.enums import LoanStatus, OrgType
from app.integrations.simulated import SimulatedWalletAdapter

log = get_logger("bootstrap")
DEMO_PASSWORD = "ChangeMe123!"


def create_tables() -> None:
    Base.metadata.create_all(engine)
    log.info("Tables ensured (%d)", len(Base.metadata.tables))


def apply_rls() -> None:
    """Enable + FORCE Row-Level Security and install the tenant-isolation policy.

    FORCE is required so the table owner (the app role) is also subject to RLS.
    The policy reads app.current_org (set per transaction) with missing_ok=true, so a
    session without a tenant context sees zero rows.
    """
    with admin_session() as db:
        for table in RLS_TABLES:
            db.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            db.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
            db.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
            db.execute(
                text(
                    f"CREATE POLICY tenant_isolation ON {table} "
                    f"USING (organization_id = current_setting('app.current_org', true)::uuid) "
                    f"WITH CHECK (organization_id = current_setting('app.current_org', true)::uuid)"
                )
            )
    log.info("Row-Level Security applied to %d tables", len(RLS_TABLES))


def _make_user(db, org, branch, email, name, role):
    u = User(
        organization_id=org.id,
        branch_id=branch.id,
        email=email,
        full_name=name,
        password_hash=hash_password(DEMO_PASSWORD),
    )
    u.roles = [role]
    db.add(u)
    return u


def _system_roles(db) -> dict[str, Role]:
    rows = db.scalars(select(Role).where(Role.organization_id.is_(None))).all()
    return {r.name: r for r in rows}


def _seed_org(org_name, org_type, domain, self_employed_profiles):
    """Create one tenant with users, applicants, financials, loans, and one analyzed loan."""
    with admin_session() as db:
        if db.scalars(select(Organization).where(Organization.name == org_name)).first():
            log.info("Org '%s' already seeded; skipping", org_name)
            return
        roles = _system_roles(db)  # queried in THIS session (avoids detached instances)
        org = Organization(name=org_name, type=org_type)
        db.add(org)
        db.flush()
        branch = Branch(organization_id=org.id, name="Head Office", code="HO")
        db.add(branch)
        db.flush()
        _make_user(db, org, branch, f"admin@{domain}", "Admin User", roles["Administrator"])
        officer = _make_user(
            db, org, branch, f"officer@{domain}", "Loan Officer", roles["Loan Officer"]
        )
        _make_user(db, org, branch, f"analyst@{domain}", "Risk Analyst", roles["Risk Analyst"])
        db.flush()
        org_id, branch_id, officer_id = org.id, branch.id, officer.id

    # Business data under tenant RLS scope.
    officer_ctx = CurrentUser(
        user_id=officer_id,
        org_id=org_id,
        branch_id=branch_id,
        roles=["Loan Officer", "Risk Analyst", "Branch Manager"],
        permissions={"platform:admin"},
    )  # broad perms for seeding only
    with tenant_session(str(org_id)) as db:
        for idx, profile in enumerate(self_employed_profiles):
            applicant = create_applicant(db, officer_ctx, profile["applicant"])
            adapter = SimulatedWalletAdapter()
            for t in adapter.fetch_transactions(str(applicant.id)):
                db.add(
                    TransactionRecord(
                        organization_id=org_id,
                        applicant_id=applicant.id,
                        source_type="wallet",
                        txn_date=t["txn_date"],
                        amount=t["amount"],
                        description=t["description"],
                    )
                )
            db.flush()
            loan = create_loan(
                db,
                officer_ctx,
                LoanCreate(
                    applicant_id=applicant.id,
                    amount=profile["amount"],
                    tenor_months=profile["tenor"],
                    purpose=profile["purpose"],
                ),
            )
            # Move first loan through the full workflow so dashboards have data.
            if idx == 0:
                transition(db, officer_ctx, loan.id, LoanStatus.submitted, "seed")
                transition(db, officer_ctx, loan.id, LoanStatus.under_review, "seed")
                transition(db, officer_ctx, loan.id, LoanStatus.ai_risk_analysis, "seed")
                analyze_loan(db, org_id, loan.id, applicant.id)
                transition(db, officer_ctx, loan.id, LoanStatus.fraud_screening, "seed")
                transition(db, officer_ctx, loan.id, LoanStatus.officer_review, "seed")
    log.info("Seeded organization '%s'", org_name)


def _demo_profiles() -> list[dict]:
    return [
        {
            "applicant": ApplicantCreate(
                full_name="Sita Sharma",
                phone="9800000001",
                national_id="12-34-56-78901",
                employment=EmploymentIn(
                    employer_name="Nepal Telecom",
                    position="Engineer",
                    monthly_income=95000,
                    employment_months=48,
                ),
                incomes=[IncomeIn(source="Salary", amount=95000)],
                expenses=[ExpenseIn(category="Living", amount=42000)],
                liabilities=[],
                existing_loans=[],
            ),
            "amount": 500000,
            "tenor": 24,
            "purpose": "Home improvement",
        },
        {
            "applicant": ApplicantCreate(
                full_name="Ram Thapa",
                phone="9800000002",
                is_self_employed=True,
                national_id="98-76-54-32109",
                incomes=[IncomeIn(source="Business", amount=60000)],
                expenses=[ExpenseIn(category="Living", amount=48000)],
                existing_loans=[
                    ExistingLoanIn(
                        lender="ABC Bank",
                        outstanding_amount=300000,
                        monthly_installment=18000,
                        is_delinquent=True,
                    )
                ],
            ),
            "amount": 400000,
            "tenor": 36,
            "purpose": "Working capital",
        },
        {
            "applicant": ApplicantCreate(
                full_name="Gita Rai",
                phone="9800000003",
                employment=EmploymentIn(
                    employer_name="Local School",
                    position="Teacher",
                    monthly_income=45000,
                    employment_months=60,
                ),
                incomes=[IncomeIn(source="Salary", amount=45000)],
                expenses=[ExpenseIn(category="Living", amount=25000)],
                liabilities=[
                    LiabilityIn(
                        name="Credit card",
                        outstanding_amount=50000,
                        monthly_payment=5000,
                    )
                ],
            ),
            "amount": 200000,
            "tenor": 18,
            "purpose": "Education",
        },
    ]


def seed() -> None:
    with admin_session() as db:
        ensure_rbac(db)
    _seed_org("Himalayan Microfinance", OrgType.mfi, "himalayan-demo.com", _demo_profiles())
    _seed_org("Everest Cooperative", OrgType.cooperative, "everest-demo.com", _demo_profiles())
    log.info("Seeding complete. Demo password for all users: %s", DEMO_PASSWORD)


def run(do_seed: bool = True) -> None:
    create_tables()
    apply_rls()
    if do_seed:
        seed()


if __name__ == "__main__":
    run(do_seed="--seed" in sys.argv or len(sys.argv) == 1)
