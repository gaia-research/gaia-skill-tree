"""Opt-in bridge to the governed challenge domain, never a receipt issuer.

The CLI deliberately does NOT configure this bridge. Its caller must supply a
trusted challenge lookup and the existing domain VerificationReceiptResolver.
Neither inline receipt JSON nor filesystem paths/approval flags provide authority.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping

from gaia_cli.challengeDomain import Challenge, VerificationReceiptResolver, validate_challenge_history
from scripts.upstream_watcher.challenge_watch import (
    ChallengeComparator, ChallengeTarget, ValidatedChallenge, VerificationReceipt,
)


class DomainChallengeAdmissionResolver:
    """Revalidate every immutable history receipt through the accepted domain port.

    The lookups and repository bindings are trusted in-process dependencies, NOT
    fields supplied by a manifest. They must represent the independently admitted
    challenge and its exact pinned target/comparator, not a Frontier lead or an
    experiment. This bridge performs no network discovery or canonical writes.
    """

    def __init__(self, *, challenge_lookup: Callable[[str], Challenge],
                 receipt_resolver: VerificationReceiptResolver,
                 targets: Mapping[str, ChallengeTarget],
                 comparators: Mapping[str, ChallengeComparator]) -> None:
        self.challenge_lookup = challenge_lookup
        self.receipt_resolver = receipt_resolver
        self.targets = targets
        self.comparators = comparators

    def resolve(self, raw, *, registry_map=None, allow_shadow=False):
        # Reference-only contract prevents a native lead or caller status/actor
        # assertion from becoming an admitted challenge through this seam.
        if (not isinstance(raw, dict) or len(raw) != 1
                or not set(raw) <= {"challengeId", "challenge_id"}):
            return None, "admission requires a reference to an independently admitted domain challenge"
        identity = raw.get("challengeId") or raw.get("challenge_id")
        if not isinstance(identity, str) or not identity.strip():
            return None, "challenge reference is missing"
        try:
            challenge = self.challenge_lookup(identity)
            if not isinstance(challenge, Challenge) or challenge.challenge_id != identity:
                raise ValueError("lookup did not return the exact domain challenge")
            receipts = {}
            trusted_resolver = self.receipt_resolver

            class BoundCapture:
                """Bound to exactly one challenge; never reused across challenges."""

                def __init__(self, challengeId, proofSourceSha):
                    binder = getattr(trusted_resolver, "for_challenge", None)
                    if not callable(binder):
                        raise ValueError("receipt resolver cannot bind to a challenge; refusing unbound resolution")
                    bound = (binder(challengeId) if proofSourceSha is None
                             else binder(challengeId, proofSourceSha))
                    if getattr(bound, "challenge_id", None) != challengeId:
                        raise ValueError("receipt resolver is not bound to this exact challenge id")
                    self.challenge_id = challengeId
                    self._bound = bound

                def resolve(self, receipt_id):
                    receipt = self._bound.resolve(receipt_id)
                    key = (self.challenge_id, receipt_id)
                    prior = receipts.setdefault(key, receipt)
                    if prior != receipt:
                        raise ValueError("trusted receipt changed during admission")
                    return receipt

            class CapturedReceipts:
                def for_challenge(self, challengeId, proof_source_sha=None):
                    if challengeId != challenge.challenge_id:
                        raise ValueError("receipt capture is bound to a different challenge")
                    return BoundCapture(challengeId, proof_source_sha)

            validate_challenge_history(challenge, CapturedReceipts())
            target = self.targets[challenge.subject_id]
            comparator = self.comparators[challenge.comparator]
            if (target.subject_id != challenge.subject_id
                    or target.pinned_version != challenge.pinned_version
                    or target.pinned_sha != challenge.pinned_sha
                    or comparator.comparator_id != challenge.comparator):
                raise ValueError("watch repositories/pins do not bind the admitted challenge")
            # Use the exact immutable object checked during history validation;
            # no second lookup or reconstruction from manifest fields.
            receipt = receipts[(challenge.challenge_id, challenge.history[-1].receipt_id)]
            admitted = ValidatedChallenge(
                challenge_id=challenge.challenge_id, claim_id=challenge.claim_id,
                subject_id=challenge.subject_id, contributor_id=challenge.contributor_id,
                behavior_id=challenge.behavior_id, status=challenge.status.value,
                material_to_origin=challenge.material_to_origin, target=target,
                comparator=comparator, verification_receipt=VerificationReceipt(
                    receipt.receipt_id, receipt.verifier_id, receipt.verified_at_utc,
                    receipt.public_receipt_ref, receipt.context_digest,
                    notes=f"Domain history digest: {challenge.history_digest}",
                ), is_verified=True, is_shadow=False, created_at_utc=challenge.created_at_utc,
            )
            return admitted, "trusted domain history and independent receipts revalidated"
        except (KeyError, TypeError, ValueError) as exc:
            return None, f"domain admission unavailable or rejected: {exc}"
