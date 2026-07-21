# Enterprise Fraud Pipeline

The enterprise pipeline composes the fitted anomaly ensemble, financial behaviour profile,
identity consistency validation, declarative fraud rules, 0–1000 scoring, confidence estimation,
business explanations, and JSON/Markdown reports into one stable `FraudAssessment` contract.

Inputs remain explicit: anomaly features, behaviour history, identity fields, application fields,
model version, feature quality, and score stability. Duplicate detection is injected. The pipeline
does not call or imitate external identity, bank, wallet, or credit-bureau services.

Risk actions are resolved using configured action priority. Every result carries detector
breakdown, behaviour indicators, identity risk, triggered flags, structured explanations,
confidence, warnings, and model version for Decision Engine and future API integration.
