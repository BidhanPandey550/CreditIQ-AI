"""scikit-learn based anomaly detectors.

Purpose:  Four production detectors sharing scikit-learn's estimator API (score_samples/predict).
          Each only maps sklearn's "higher = more normal" signal to the engine's
          "higher = more anomalous" convention. All hyperparameters come from config.
Deps:     scikit-learn.
Extend:   add another score_samples/predict-style estimator with the same three hooks.
"""

from __future__ import annotations

from typing import Any

from creditiq_ai.core.types import NDArray
from creditiq_ai.fraud.detectors.base import BaseFraudDetector
from creditiq_ai.fraud.detectors.registry import register


class _SklearnAnomalyDetector(BaseFraudDetector):
    """Shared behaviour: flip sklearn's score_samples, map predict==-1 to anomaly."""

    def _raw_scores(self, X: NDArray) -> NDArray:
        # sklearn: higher score_samples = more normal → negate for "higher = more anomalous".
        return -self._model.score_samples(X)

    def _raw_predict(self, X: NDArray) -> NDArray:
        return self._model.predict(X) == -1


@register("isolation_forest")
class IsolationForestDetector(_SklearnAnomalyDetector):
    detector_name = "isolation_forest"

    def _fit_model(self, X: NDArray) -> Any:
        from sklearn.ensemble import IsolationForest

        model = IsolationForest(**self.params)
        model.fit(X)
        return model


@register("local_outlier_factor")
class LocalOutlierFactorDetector(_SklearnAnomalyDetector):
    detector_name = "local_outlier_factor"

    def _fit_model(self, X: NDArray) -> Any:
        from sklearn.neighbors import LocalOutlierFactor

        # novelty=True (from config) enables scoring/predicting unseen rows.
        model = LocalOutlierFactor(**self.params)
        model.fit(X)
        return model


@register("one_class_svm")
class OneClassSVMDetector(_SklearnAnomalyDetector):
    detector_name = "one_class_svm"

    def _fit_model(self, X: NDArray) -> Any:
        from sklearn.svm import OneClassSVM

        model = OneClassSVM(**self.params)
        model.fit(X)
        return model


@register("elliptic_envelope")
class EllipticEnvelopeDetector(_SklearnAnomalyDetector):
    detector_name = "elliptic_envelope"

    def _fit_model(self, X: NDArray) -> Any:
        from sklearn.covariance import EllipticEnvelope

        model = EllipticEnvelope(**self.params)
        model.fit(X)
        return model
