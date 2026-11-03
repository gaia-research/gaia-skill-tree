"""Visibly synthetic receipt source ports. TEST ONLY; never live authorization evidence.

``SyntheticReceiptPort`` returns a canned document. Its ``approvalHistoryVerified``
boolean proves nothing: it is accepted only by ``SyntheticTestResolver``, a test
subclass that explicitly opts the port into the resolver allowlist. The production
``GitHubVerificationReceiptResolver`` refuses it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from gaia_cli.steward.challenge_receipts import (
    AuthenticatedApprovalSource,
    GitHubVerificationReceiptResolver,
    TrustedReceiptConfig,
)


@dataclass(frozen=True)
class SyntheticReceiptPort(AuthenticatedApprovalSource):
    SYNTHETIC_TEST_ONLY = True
    document: Mapping[str, Any]
    archive: bytes

    def fetch(self, receipt_id: str, config: TrustedReceiptConfig) -> Mapping[str, Any]:
        del receipt_id, config
        return self.document


class SyntheticTestResolver(GitHubVerificationReceiptResolver):
    """Explicit test opt-in: allowlists the synthetic port for this subclass only."""
    AUTHENTICATED_SOURCES = (SyntheticReceiptPort,)
