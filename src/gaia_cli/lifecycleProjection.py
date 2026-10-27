"""Read-only, default-unavailable challenge projection foundation.

Neither protocol is an issuer: adapters must be supplied by a trusted caller.
This module does not authenticate a serialized record, publish data, calculate
standing, or authorize changes to canonical state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
            validate_challenge_history(challenge, receipt_resolver)
            seen.add(challenge.challenge_id)
        return ChallengeProjection(
            subject_id, challenges,
            any(item.material_to_origin and not item.resolved for item in challenges),
        )
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return None
