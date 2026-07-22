# Loan Servicing and Delinquency

CreditIQ AI maintains servicing records independently from origination and AI assessment. A loan
must be approved before it can be disbursed. Disbursement creates one immutable contractual record
and a monthly reducing-balance schedule; the loan then moves through `disbursed` to `active` using
the existing audited workflow state machine.

## Financial behavior

- The contractual annual rate comes from the disbursement request, its loan product, or the
  institution-level fallback, in that order.
- Monthly installments use reducing-balance amortization. Currency values are rounded with
  `ROUND_HALF_UP`, and the final installment reconciles the principal exactly.
- Repayments are locked and allocated to the oldest installment first, interest before principal.
- Overpayments and future-dated payments are rejected. External payment references are unique per
  tenant to guard against accidental duplicate posting.
- Full repayment closes either an active or previously defaulted loan through the workflow ledger.

## Delinquency and PAR

Days past due (DPD) is calculated from unpaid scheduled amounts. The configurable grace period
controls when an installment is treated as delinquent; it does not rewrite contractual due dates.
Portfolio-at-risk (PAR) includes the entire outstanding balance of a loan whose maximum DPD reaches
the configured threshold, not only its overdue installment. Default thresholds are 1, 30, 60, and
90 days and can be replaced through environment configuration.

## Security and auditability

The three servicing tables carry `organization_id`, have forced PostgreSQL RLS policies, and are
covered by the live policy inventory test. Branch authorization is applied through the parent loan.
Applicants may view only their own schedule. Only users with `loan:service` can record repayments;
disbursement continues to require `loan:disburse`. Disbursements, repayments, workflow changes, and
their request correlation metadata are written to the compliance audit log.

This module records servicing activity inside CreditIQ AI. It does not claim to transfer funds or
connect to a core banking/payment network; those operations require a future reviewed connector.
