# Business Rules and Confidence

The credit business-rule engine evaluates priority-ordered declarative rules from the unified YAML
configuration. Operators, lender thresholds, severity, action, stop behavior, and explanations are
configuration—not application code. Missing applicant fields produce warnings; invalid rule
configuration fails before evaluation. Stop actions support deterministic hard-decline policies.

The confidence engine combines probability decisiveness, calibration quality, feature
completeness, and prediction stability using configurable normalized weights. It returns a score,
configured confidence level, reliability code, and component breakdown suitable for decisions,
explanations, monitoring, and audit reports. Confidence is not approval probability.
