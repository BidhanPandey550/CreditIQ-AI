# Hyperparameter Optimization

`OptunaOptimizationService` tunes any available registered trainer using the search space already
defined in the unified model-zoo configuration. Integer, floating-point, logarithmic, stepped, and
categorical dimensions are validated before a study starts.

Studies use a seeded TPE sampler, configurable median pruning, timeout, trial count, and parallel
worker count. The existing training template remains the objective, preserving identical
cross-validation, metrics, validation, and logging between tuned and fixed-parameter models.

`OptimizationResult` records every trial, the winning score, and merged fixed/best parameters. It
can be atomically persisted as JSON. A configured Optuna storage URL enables durable study history
and restart through `load_if_exists`; local in-memory studies remain the development default.
