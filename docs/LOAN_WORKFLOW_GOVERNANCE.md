# Loan Workflow Governance

CreditIQ AI separates mandatory safety transitions from tenant-configurable review policy. An
institution may tune its operating process, but it cannot configure a path that bypasses AI risk
analysis or fraud screening.

## Immutable safety path

Every submitted application follows:

```text
draft → submitted → under_review → ai_risk_analysis → fraud_screening → officer_review
```

Approval continues to disbursement and servicing through the existing controlled state machine.
Every successful transition creates both a workflow event and a compliance audit event. Illegal
transitions fail with a domain-rule error and do not mutate the loan.

## Tenant policy

Administrators configure `settings.loan_workflow` through the organization settings API and UI:

- `analyst_review_policy=optional` allows the officer to decide or escalate to a Risk Analyst.
- `required` forces every officer-reviewed application through Risk Analyst review.
- `amount_threshold` requires Risk Analyst review when the requested amount is greater than or
  equal to the configured positive threshold.
- `allow_needs_more_information` controls the information-request loop.
- `allow_default_classification` controls whether an active loan may enter the defaulted stage.

Pydantic rejects missing, misplaced, or non-positive amount thresholds. The policy only removes
optional transitions from the domain state machine; it cannot add arbitrary transitions. This is a
deliberate control against configuration-based safety bypass.

Organization updates already record before/after settings in the tenant audit trail. Existing
tenants without workflow settings receive the backward-compatible `optional` policy.
