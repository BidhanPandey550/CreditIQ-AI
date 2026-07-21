"""Decision policy — combine credit + fraud risk into a recommendation (config-driven).

Purpose:  Encapsulate the lending policy so the engine stays thin. All mappings/overrides come from
          DecisionConfig — no hardcoded decisions. Fraud can only make a decision MORE conservative
          (block/reject), never auto-approve something credit would reject.
Deps:     config.models.DecisionConfig.
"""

from __future__ import annotations

from creditiq_ai.config.models import DecisionConfig


class DecisionPolicy:
    def __init__(self, config: DecisionConfig) -> None:
        self._cfg = config

    def recommend(
        self,
        *,
        credit_band: str,
        fraud_level: str | None,
        credit_ok: bool,
        fraud_ok: bool,
        data_complete: bool,
    ) -> tuple[str, list[str]]:
        reasons: list[str] = []

        if not data_complete:
            reasons.append("incomplete_required_data")
            return self._cfg.on_incomplete_data, reasons
        if not credit_ok:
            reasons.append("credit_assessment_unavailable")
            return self._cfg.on_credit_failure, reasons

        base = self._cfg.credit_recommendation.get(credit_band, "review")
        reasons.append(f"credit_risk={credit_band}->{base}")

        if fraud_ok and fraud_level is not None:
            if fraud_level in self._cfg.fraud_reject_levels:
                reasons.append(f"fraud_risk={fraud_level}->reject_override")
                return "reject", reasons
            if fraud_level in self._cfg.fraud_block_levels and base == "approve":
                reasons.append(f"fraud_risk={fraud_level}->block_auto_approval")
                return self._cfg.fraud_block_action, reasons
            reasons.append(f"fraud_risk={fraud_level}")
        elif not fraud_ok:
            reasons.append("fraud_assessment_unavailable")
            if base == "approve":  # conservative: don't auto-approve blind
                return self._cfg.on_fraud_failure, reasons

        return base, reasons
