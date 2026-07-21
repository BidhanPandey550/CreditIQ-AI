"""creditiq_ai.fraud.algorithms — concrete unsupervised detectors.

Importing this package registers all built-in detectors with the FraudDetectionRegistry.
"""

from creditiq_ai.fraud.algorithms import (  # noqa: F401  (import = register)
    dbscan_detector,
    sklearn_detectors,
)

__all__ = ["sklearn_detectors", "dbscan_detector"]
