"""Import every ORM model so Base.metadata is fully populated for create_all / Alembic."""

# noqa: F401
from app.modules.applicant import models as applicant_models  # noqa: F401
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.credit_intelligence import models as ci_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.integration import models as integration_models  # noqa: F401
from app.modules.loan import models as loan_models  # noqa: F401
from app.modules.organization import models as org_models  # noqa: F401

# Tables that carry tenant data and MUST be protected by Row-Level Security.
RLS_TABLES = [
    "applicants",
    "kyc_records",
    "employment_records",
    "business_records",
    "income_records",
    "expense_records",
    "asset_records",
    "liability_records",
    "existing_loans",
    "transaction_records",
    "financial_documents",
    "loan_products",
    "loan_applications",
    "loan_workflow_events",
    "loan_decisions",
    "risk_scores",
    "credit_scores",
    "default_predictions",
    "fraud_alerts",
    "ai_explanations",
    "audit_logs",
    "notifications",
    "api_keys",
]
