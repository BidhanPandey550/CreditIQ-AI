"""Integration ports (interfaces). Core code depends only on these — never on a concrete
provider. Real adapters (eSewa/Khalti/bank/bureau) are added later WITHOUT touching core logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol


class WalletConnectorPort(ABC):
    @abstractmethod
    def fetch_transactions(self, applicant_ref: str) -> list[dict]:
        """Return a list of {txn_date, amount, description}."""


class SmsGatewayPort(Protocol):
    def send(self, to: str, message: str) -> bool: ...


class EmailPort(Protocol):
    def send(self, to: str, subject: str, body: str) -> bool: ...


class CreditBureauPort(ABC):
    @abstractmethod
    def fetch_report(self, national_id: str) -> dict: ...


class IdentityVerificationPort(ABC):
    @abstractmethod
    def verify(self, national_id: str, full_name: str) -> dict: ...
