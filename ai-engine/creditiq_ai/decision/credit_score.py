"""Credit score mapper — probability of default → 300–850 credit score + risk band.

Purpose:  Map a model PD to the configured credit score using the standard scorecard formula, and
          resolve the credit risk band. Reuses the EXISTING `ScoringConfig` (base_score/base_odds/
          pdo/bands) — no new hardcoded thresholds.
Formula:  score = base_score + (pdo/ln2) * (ln(odds) - ln(base_odds)),  odds = (1 - p) / p.
Deps:     config.models.ScoringConfig.
"""

from __future__ import annotations

import math

from creditiq_ai.config.models import ScoringConfig
from creditiq_ai.core.base import BaseComponent

_EPS = 1e-6
_LN2 = math.log(2)


class CreditScoreMapper(BaseComponent):
    def __init__(self, config: ScoringConfig) -> None:
        super().__init__()
        self._cfg = config
        # Risk bands are ordered by min_score; higher score = lower risk.
        self._bands = sorted(config.bands, key=lambda b: b.min_score, reverse=True)

    def score(self, probability_of_default: float) -> int:
        p = min(max(probability_of_default, _EPS), 1.0 - _EPS)
        odds = (1.0 - p) / p
        raw = self._cfg.base_score + (self._cfg.pdo / _LN2) * (
            math.log(odds) - math.log(self._cfg.base_odds)
        )
        return int(min(max(round(raw), self._cfg.min_score), self._cfg.max_score))

    def band(self, score: int) -> str:
        for band in self._bands:
            if score >= band.min_score:
                return band.band
        return self._bands[-1].band if self._bands else "unknown"
