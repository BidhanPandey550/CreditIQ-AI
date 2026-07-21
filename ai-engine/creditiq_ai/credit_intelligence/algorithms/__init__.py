"""creditiq_ai.credit_intelligence.algorithms — concrete trainers.

Importing this package registers all built-in trainers with the TrainingRegistry.
Sprint-4 next module adds: xgboost, lightgbm, catboost.
"""

from creditiq_ai.credit_intelligence.algorithms import (  # noqa: F401  (import = register)
    logistic_regression,
    random_forest,
)

__all__ = ["logistic_regression", "random_forest"]
