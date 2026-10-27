"""Read-only, default-unavailable challenge projection foundation.

Neither protocol is an issuer: adapters must be supplied by a trusted caller.
This module does not authenticate a serialized record, publish data, calculate
standing, or authorize changes to canonical state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Protocol
import math

from .challengeDomain import Challenge, VerificationReceiptResolver, validate_challenge_history


class ChallengeSource(Protocol):
    """Trusted source of the complete immutable challenge set for one subject.

    None means unavailable; an empty tuple means the trusted source has
    established a complete empty set. A caller-supplied dict is not a source.
    """

    def challenges_for(self, subject_id: str) -> tuple[Challenge, ...] | None: ...


@dataclass(frozen=True)
class ChallengeProjection:
    subject_id: str
    challenges: tuple[Challenge, ...]
    material_origin_contested: bool


def project_challenges(subject_id: str, source: ChallengeSource | None = None,
                       receipt_resolver: VerificationReceiptResolver | None = None,
                       ) -> ChallengeProjection | None:
    """Return validated challenge facts, or None if any authority is unavailable.

    This is not a canonical-consequence producer. It cannot establish approved
    numeric standing, rank, or Origin ownership. All events remain on the
    immutable domain objects. One invalid, foreign, or duplicate challenge
    rejects the whole set rather than hiding evidence or claiming it is empty.
    """
    if not isinstance(subject_id, str) or not subject_id.strip():
        return None
    if source is None or receipt_resolver is None:
        return None
    class StableResolver:
        def __init__(self):
            self.cache = {}

        def resolve(self, receipt_id):
            if receipt_id not in self.cache:
                self.cache[receipt_id] = receipt_resolver.resolve(receipt_id)
            return self.cache[receipt_id]

    resolver = StableResolver()
    try:
        challenges = source.challenges_for(subject_id)
        if not isinstance(challenges, tuple):
            return None
        seen = set()
        for challenge in challenges:
            if (not isinstance(challenge, Challenge) or challenge.subject_id != subject_id
                    or type(challenge.material_to_origin) is not bool
                    or challenge.challenge_id in seen):
                return None
            # Re-run immutable identity/history digest checks on rehydration,
            # including objects altered after their original construction.
            replace(challenge)
            validate_challenge_history(challenge, resolver)
            if any(resolver.resolve(event.receipt_id).contributor_id != challenge.contributor_id
                   for event in challenge.history):
                return None
            seen.add(challenge.challenge_id)
        return ChallengeProjection(
            subject_id, challenges,
            any(item.material_to_origin and not item.resolved for item in challenges),
        )
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class CanonicalConsequence:
    """Trusted adapter result, not a deserializable approval credential.

    kind is either current-baseline or approved-decision. The adapter, not
    these fields, must establish provenance and a coherent publication snapshot.
    A pending recalibration is independently supplied by that same adapter.
    """
    subject_id: str
    generic_ref: str
    kind: str
    stars: int
    tm: float
    origin_handle: str | None
    recalibration_pending: bool = False


class CanonicalConsequenceSource(Protocol):
    def consequence_for(self, subject_id: str) -> CanonicalConsequence | None: ...


@dataclass(frozen=True)
class LifecyclePorts:
    challenges: ChallengeSource
    receipts: VerificationReceiptResolver
    consequences: CanonicalConsequenceSource | None = None


# Skill Explorer hero metric (docs/js/skill-explorer.js renderHero, plaque.js):
#   ns.trustMagnitude || ns.overallTrustMagnitude || ns.trustNumber
# i.e. the first truthy value, so a 0 or empty field silently falls through to
# the next. Every field in that chain can reach the screen, so a baseline or
# decision must agree with all of them, not only the first one present.
heroTmFields = ('trustMagnitude', 'overallTrustMagnitude', 'trustNumber')


def _displayedTrustMagnitudes(entry: dict) -> list[float] | None:
    """Return every numeric TM the Explorer could show, or None if one is unusable.

    Absent/None/empty fields are skipped (the Explorer skips them too). A present
    value that is boolean, non-numeric, or non-finite cannot be reconciled with
    a canonical consequence, so the caller must reject the entry.
    """
    values = []
    for field in heroTmFields:
        raw = entry.get(field)
        if raw is None or raw == '':
            continue
        if isinstance(raw, bool):
            return None
        if isinstance(raw, str):
            try:
                raw = float(raw)
            except ValueError:
                return None
        if type(raw) not in (int, float) or not math.isfinite(raw):
            return None
        values.append(float(raw))
    return values


def produce_lifecycle(entry: dict, ports: LifecyclePorts | None = None) -> dict | None:
    """Produce a public DTO only from explicitly installed in-process ports.

    DTO shape checking is not authentication. Source adapters are responsible
    for authenticating complete challenge and canonical consequence records.
    No production adapters are installed here. Missing challenge authority
    means no DTO; missing consequence authority remains explicitly unavailable.
    """
    if not isinstance(entry, dict) or not isinstance(ports, LifecyclePorts):
        return None
    subject = entry.get('id')
    ref = entry.get('genericSkillRef')
    if not isinstance(subject, str) or not subject.strip() or not isinstance(ref, str) or not ref.strip():
        return None
    class StableReceipts:
        def __init__(self):
            self.cache = {}

        def resolve(self, receipt_id):
            if receipt_id not in self.cache:
                self.cache[receipt_id] = ports.receipts.resolve(receipt_id)
            return self.cache[receipt_id]

    receipts = StableReceipts()
    projection = project_challenges(subject, ports.challenges, receipts)
    if projection is None:
        return None
    consequence = None
    if ports.consequences is not None:
        try:
            consequence = ports.consequences.consequence_for(subject)
        except (AttributeError, KeyError, OSError, TypeError, ValueError):
            return None
        if consequence is not None:
            if (not isinstance(consequence, CanonicalConsequence)
                    or consequence.subject_id != subject or consequence.generic_ref != ref
                    or consequence.kind not in {'current-baseline', 'approved-decision'}
                    or type(consequence.stars) is not int or not 0 <= consequence.stars <= 6
                    or type(consequence.tm) not in (int, float) or not math.isfinite(consequence.tm)
                    or consequence.tm < 0 or type(consequence.recalibration_pending) is not bool
                    or (consequence.origin_handle is not None and
                        (not isinstance(consequence.origin_handle, str) or not consequence.origin_handle.strip()))):
                return None
            level = entry.get('level')
            if isinstance(level, str) and level and level[0].isdigit() and int(level[0]) != consequence.stars:
                return None
            if isinstance(level, int) and not isinstance(level, bool) and level != consequence.stars:
                return None
            displayed = _displayedTrustMagnitudes(entry)
            if displayed is None or any(abs(value - consequence.tm) > 0.01 for value in displayed):
                return None
    items = []
    try:
        for challenge in projection.challenges:
            opening = receipts.resolve(challenge.history[0].receipt_id)
            item = {
                'challengeId': challenge.challenge_id, 'subjectId': subject,
                'linkedChallengeId': challenge.linked_challenge_id,
                'claimId': challenge.claim_id, 'claim': challenge.claim,
                'behaviorId': challenge.behavior_id, 'contributorId': challenge.contributor_id,
                'materialToOrigin': challenge.material_to_origin, 'status': challenge.status.value,
                'pinnedVersion': challenge.pinned_version, 'pinnedSha': challenge.pinned_sha,
                'environment': challenge.environment, 'testVersion': challenge.test_version,
                'baseline': challenge.baseline, 'comparator': challenge.comparator,
                'verifiedAtUTC': challenge.created_at_utc,
                'contributorNoticeRef': challenge.contributor_notice_ref,
                'verifier': {'verifierId': opening.verifier_id,
                             'verificationMethod': opening.method,
                             'receiptUrl': opening.public_receipt_ref},
                'history': [asdict(event) for event in challenge.history],
            }
            if challenge.resolved:
                event = challenge.history[-1]
                receipt = receipts.resolve(event.receipt_id)
                item['resolution'] = {'disposition': challenge.status.value,
                    'resolvedAtUTC': event.at_utc, 'verifierId': event.actor,
                    'receiptUrl': receipt.public_receipt_ref}
            items.append(item)
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return None
    return {'contract': 'gaia-trust-lifecycle/v1', 'subjectId': subject,
            'genericSkillRef': ref, 'challenges': items,
            'materialOriginContested': projection.material_origin_contested,
            'consequence': ({'kind': consequence.kind, 'stars': consequence.stars,
                             'tm': consequence.tm, 'originHandle': consequence.origin_handle,
                             'recalibrationPending': consequence.recalibration_pending}
                            if consequence is not None else {'kind': 'unavailable'})}
