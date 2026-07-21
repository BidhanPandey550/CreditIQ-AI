# Training Orchestration and Reports

`CreditTrainingOrchestrator` provides the complete current Credit Intelligence training path:

1. Deterministic stratified train/holdout split.
2. Multi-algorithm training and cross-validation.
3. Untouched holdout probability evaluation.
4. Configurable multi-metric comparison and eligibility gates.
5. Automatic champion selection.
6. Optional atomic JSON and Markdown report generation.

The returned `CreditTrainingRun` retains training and holdout dataset versions, all lightweight
results, the selected fitted trainer, comparison report, and generated artifacts. Individual
training, evaluation, comparison, and reporting services remain independently replaceable through
their existing contracts.

The holdout set is never used to fit the models. Probability calibration should use a separately
reserved calibration partition in deployments that enable calibration; reusing the final holdout
would create optimistic evaluation estimates.
