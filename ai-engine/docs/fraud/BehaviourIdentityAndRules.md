# Fraud Behaviour, Identity, and Rules

The behaviour analyzer creates seven normalized indicators from financial history: spending
volatility, income instability, savings inconsistency, debt burden, transaction frequency,
cash-flow irregularity, and lifestyle instability. Weights and normalization caps are supplied by
the unified environment configuration; incomplete histories are explicitly reported.

Identity validation checks configured required fields and matching field pairs. Duplicate detection
is a dependency-injected hook so future database, bureau, or government-identity adapters can be
added without modifying validation logic. No external identity integration is simulated.

Fraud rules reuse the platform's canonical declarative rule evaluator, avoiding a duplicate rule
language. Fraud thresholds, priority, severity, actions, stop behavior, and explanations remain
configuration-driven and auditable.
