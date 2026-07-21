# Credit Model Trainers

The built-in model registry contains Logistic Regression, Random Forest, XGBoost, LightGBM, and
CatBoost trainers. Every implementation inherits the same `BaseTrainer` template method, providing
consistent validation, stratified cross-validation, prediction, probability prediction,
integrity-verified persistence, provenance, and structured logging.

Gradient-boosting libraries are optional and loaded lazily. A core installation continues with the
always-available scikit-learn trainers; `poetry install -E modeling` activates all three boosting
trainers without changing application code or configuration. The training pipeline checks runtime
availability and logs skipped optional algorithms rather than failing unrelated core workflows.

Default seeds and execution settings are merged with configured parameters so deployment-specific
configuration can override them without duplicate keyword errors.
