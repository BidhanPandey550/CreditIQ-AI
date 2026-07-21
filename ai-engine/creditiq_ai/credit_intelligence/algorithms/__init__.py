"""creditiq_ai.credit_intelligence.algorithms — concrete trainers.

Importing this package registers all built-in trainers with the TrainingRegistry.
Optional libraries are imported lazily by their trainer, so registering the complete model zoo
does not force heavyweight dependencies into core installations.
"""

from creditiq_ai.credit_intelligence.algorithms import (  # noqa: F401  (import = register)
    catboost,
    lightgbm,
    logistic_regression,
    random_forest,
    xgboost,
)

__all__ = ["catboost", "lightgbm", "logistic_regression", "random_forest", "xgboost"]
