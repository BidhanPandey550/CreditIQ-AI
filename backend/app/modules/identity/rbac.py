"""RBAC catalog: permissions and the six seeded system roles.

These are the source of truth for seeding. Custom per-tenant roles compose the same
permission codes. UI enforcement is convenience only — the API is the authority.
"""

from __future__ import annotations

# --- Permission codes (verb on resource) ---
PERMISSIONS: dict[str, str] = {
    "org:configure": "Configure organization settings, workflows, policies",
    "user:manage": "Create/manage users and role assignments",
    "role:manage": "Create/manage roles and permissions",
    "applicant:read": "View applicants",
    "applicant:manage": "Create/update applicants and financial profiles",
    "loan:create": "Create loan applications",
    "loan:read": "View loan applications",
    "loan:review": "Move loans through review stages",
    "loan:approve": "Approve or reject loans (within policy limits)",
    "loan:disburse": "Disburse approved loans",
    "risk:read": "View risk scores and assessments",
    "risk:override": "Override AI risk assessment with justification",
    "credit_score:read": "View credit scores",
    "default:read": "View default probability predictions",
    "explanation:read": "View AI (SHAP) explanations",
    "fraud:read": "View fraud alerts",
    "fraud:resolve": "Confirm or dismiss fraud alerts",
    "analytics:read": "View analytics dashboards",
    "report:export": "Generate and export reports",
    "audit:read": "View audit logs",
    "platform:admin": "Platform-wide administration across tenants",
}

# --- System roles → permission sets ---
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Applicant": [
        "loan:create",
        "loan:read",
        "applicant:read",
    ],
    "Loan Officer": [
        "applicant:read",
        "applicant:manage",
        "loan:create",
        "loan:read",
        "loan:review",
        "risk:read",
        "credit_score:read",
        "explanation:read",
        "fraud:read",
        "analytics:read",
    ],
    "Risk Analyst": [
        "applicant:read",
        "loan:read",
        "loan:review",
        "risk:read",
        "risk:override",
        "credit_score:read",
        "default:read",
        "explanation:read",
        "fraud:read",
        "analytics:read",
    ],
    "Branch Manager": [
        "applicant:read",
        "loan:read",
        "loan:review",
        "loan:approve",
        "loan:disburse",
        "risk:read",
        "credit_score:read",
        "default:read",
        "explanation:read",
        "fraud:read",
        "fraud:resolve",
        "analytics:read",
        "report:export",
    ],
    "Administrator": [
        "org:configure",
        "user:manage",
        "role:manage",
        "applicant:read",
        "applicant:manage",
        "loan:read",
        "loan:review",
        "loan:approve",
        "risk:read",
        "credit_score:read",
        "default:read",
        "explanation:read",
        "fraud:read",
        "fraud:resolve",
        "analytics:read",
        "report:export",
        "audit:read",
    ],
    "Super Admin": list(PERMISSIONS.keys()),
}

SYSTEM_ROLES = list(ROLE_PERMISSIONS.keys())
