# Automatic Model Comparison

`ModelComparisonService` ranks holdout evaluation reports and selects a champion without manual
intervention. Selection combines configurable metric weights with hard eligibility gates.

Benefit metrics such as ROC-AUC, PR-AUC, recall, and F1 are maximized. Loss metrics—Brier score and
log loss—are converted to bounded higher-is-better utility values for composition and may be
controlled with maximum eligibility gates. Matthews correlation is mapped from `[-1, 1]` to
`[0, 1]`. Weights are normalized automatically.

Eligibility is evaluated before composite score. A model that violates a mandatory performance or
calibration gate cannot become champion even when its weighted score is higher. By default,
selection fails closed when no candidate is eligible. Ranking is deterministic and every failed
gate is included in the machine-readable leaderboard.
