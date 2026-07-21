"""DBSCAN-based anomaly detector (density novelty).

Purpose:  DBSCAN has no native predict for unseen rows, so we fit it on a reference population,
          keep its core samples, and score a new row by its distance to the nearest core point:
          within `eps` → density-reachable (normal); beyond `eps` → noise/anomaly.
Deps:     scikit-learn.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from creditiq_ai.core.types import NDArray
from creditiq_ai.fraud.detectors.base import BaseFraudDetector
from creditiq_ai.fraud.detectors.registry import register


@register("dbscan")
class DBSCANDetector(BaseFraudDetector):
    detector_name = "dbscan"

    def _fit_model(self, X: NDArray) -> Any:
        from sklearn.cluster import DBSCAN
        from sklearn.neighbors import NearestNeighbors

        eps = float(self.params.get("eps", 0.8))
        min_samples = int(self.params.get("min_samples", 5))
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(X)

        core = X[clustering.core_sample_indices_]
        if len(core) == 0:  # degenerate: no dense region → fall back to all rows
            core = X
        nn = NearestNeighbors(n_neighbors=1).fit(core)
        return {"nn": nn, "eps": eps}

    def _raw_scores(self, X: NDArray) -> NDArray:
        distances, _ = self._model["nn"].kneighbors(X, n_neighbors=1)
        return distances[:, 0]  # higher distance = more anomalous

    def _raw_predict(self, X: NDArray) -> NDArray:
        distances, _ = self._model["nn"].kneighbors(X, n_neighbors=1)
        return np.asarray(distances[:, 0] > self._model["eps"])
