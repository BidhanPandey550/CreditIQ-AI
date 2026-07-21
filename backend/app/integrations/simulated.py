"""Simulated adapters for the MVP.

These generate plausible SYNTHETIC data and are explicitly flagged as simulated.
They are NOT real connections to eSewa/Khalti/banks/bureaus. Swapping in a real
provider later = implement the same port + register it; zero core changes.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from app.integrations.ports import (
    CreditBureauPort,
    IdentityVerificationPort,
    WalletConnectorPort,
)


class SimulatedWalletAdapter(WalletConnectorPort):
    is_simulated = True

    def fetch_transactions(self, applicant_ref: str, months: int = 6) -> list[dict]:
        rng = random.Random(hash(applicant_ref) & 0xFFFFFFFF)
        txns: list[dict] = []
        now = datetime.utcnow()
        for i in range(months * 20):
            day = now - timedelta(days=rng.randint(0, months * 30))
            credit = rng.random() < 0.35
            amount = round(rng.uniform(500, 40000) * (1 if credit else -1), 2)
            txns.append(
                {
                    "txn_date": day,
                    "amount": amount,
                    "description": rng.choice(
                        [
                            "Salary",
                            "Grocery",
                            "Utility",
                            "Transfer",
                            "Recharge",
                            "Rent",
                            "Merchant",
                        ]
                    ),
                    "is_simulated": True,
                }
            )
        return txns


class SimulatedCreditBureauAdapter(CreditBureauPort):
    is_simulated = True

    def fetch_report(self, national_id: str) -> dict:
        return {
            "national_id": national_id,
            "bureau_score": None,
            "note": "Simulated — no real bureau connection",
            "is_simulated": True,
        }


class SimulatedIdentityVerificationAdapter(IdentityVerificationPort):
    is_simulated = True

    def verify(self, national_id: str, full_name: str) -> dict:
        return {
            "verified": True,
            "confidence": 0.0,
            "note": "Simulated verification — not a real government check",
            "is_simulated": True,
        }
