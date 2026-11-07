"""Semantic deduplication and debt lifecycle reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Collection, Iterable, Mapping

from gaia_cli.steward.models import AuthorityClass, Debt, Observation, debtIdFor, stable_json
from gaia_cli.steward.policy import StewardPolicy

# Debt id migration: a successor kind replaces predecessor kinds for the same
# subject. The predecessor is resolved as ``superseded`` and both debts name each
# other; nothing is deleted. ``trust_evidence_gap`` replaces the interim
# ``trust_calibration_drift`` + ``laneEligible: false`` marker (#2201).
KIND_SUPERSESSIONS: dict[str, tuple[str, ...]] = {
    "trust_evidence_gap": ("trust_calibration_drift",),
}
SUPERSEDED_RESOLUTION = "superseded"


def _interimEvidenceGap(old: Debt) -> bool:
    """The historical condition ``trust_evidence_gap`` replaces.

    Only a ``trust_calibration_drift`` debt that carried the interim evidence-gap
    marker (``evidenceGap: true``, no demotion target) is the same condition. A
    drift debt for genuine prior drift (a real target level) is a different
    finding: it is left to its own lifecycle and never linked or resolved here.
    """

    state = old.observed_state
    return state.get("evidenceGap") is True and "targetLevel" not in state


# A predecessor is linked only when its historical condition matches.
SUPERSESSION_MATCH = {"trust_evidence_gap": {"trust_calibration_drift": _interimEvidenceGap}}


@dataclass(frozen=True)
class Reconciliation:
    debts: tuple[Debt, ...]
    created: tuple[str, ...]
    updated: tuple[str, ...]
    resolved: tuple[str, ...]
    # (predecessor debt id, successor debt id) pairs linked this run.
    superseded: tuple[tuple[str, str], ...] = ()


def _deduplicate(observations: Iterable[Observation]) -> tuple[Observation, ...]:
    """Collapse observations by unresolved condition, preferring drift on conflict."""

    grouped: dict[str, list[Observation]] = {}
    for observation in observations:
        grouped.setdefault(observation.semantic_key, []).append(observation)

    selected: list[Observation] = []
    for semantic_key in sorted(grouped):
        candidates = grouped[semantic_key]
        drift = [item for item in candidates if item.status == "drift"]
        pool = drift or candidates
        # Equal duplicates collapse. Conflicting readings fail closed: a drift
        # wins, and canonical JSON ordering makes the choice reproducible.
        selected.append(max(pool, key=lambda item: stable_json(item.to_dict())))
    return tuple(selected)


def _authority_ceiling(
    existing: AuthorityClass | None, configured: AuthorityClass
) -> AuthorityClass:
    rank = {AuthorityClass.A: 1, AuthorityClass.B: 2, AuthorityClass.C: 3}
    if existing is not None and rank[existing] > rank[configured]:
        return existing
    return configured


def _link_predecessors(
    observation: Observation,
    debt_id: str,
    debts: dict[str, Debt],
    resolved: list[str],
    superseded: list[tuple[str, str]],
) -> tuple[str, ...]:
    """Link a drift observation to the debts of the kinds it supersedes.

    Returns the predecessor ids that exist in the ledger. An open predecessor is
    resolved as ``superseded`` in the same step (so the exhaustive sweep reports
    the migration, not a vanished condition); one already resolved keeps its
    resolution and only gains the forward link. The predecessor is never removed.
    """

    if observation.status != "drift":
        return ()
    found: list[str] = []
    for old_kind in KIND_SUPERSESSIONS.get(observation.kind, ()):
        old_id = debtIdFor(old_kind, observation.subject)
        old = debts.get(old_id)
        if old is None or old_id == debt_id:
            continue
        matches = SUPERSESSION_MATCH.get(observation.kind, {}).get(old_kind)
        if matches is not None and not matches(old):
            continue
        found.append(old_id)
        if old.superseded_by == debt_id and old.status == "resolved":
            continue
        if old.status == "open":
            debts[old_id] = replace(
                old,
                status="resolved",
                last_observed_at=observation.observed_at,
                resolution=SUPERSEDED_RESOLUTION,
                superseded_by=debt_id,
            )
            resolved.append(old_id)
        else:
            debts[old_id] = replace(old, superseded_by=debt_id)
        superseded.append((old_id, debt_id))
    return tuple(sorted(found))


def reconcile_debt(
    observations: Iterable[Observation],
    existing: Mapping[str, Debt],
    policy: StewardPolicy,
    *,
    exhaustive_sources: Collection[str] = (),
    observed_at: str | None = None,
) -> Reconciliation:
    """Fold one run's observations into the debt ledger.

    ``exhaustive_sources`` names the sensors that *completed* this run and
    declared ``resolution_scope = "exhaustive"``: their scan enumerates their
    whole domain and emits drift for every bad subject, so an open debt of
    theirs that was not re-observed as drift no longer holds. Each is resolved
    with ``condition_not_reobserved`` at ``observed_at``. The caller must pass
    only sensors that did not raise; a sensor that failed resolves nothing.
    """

    if exhaustive_sources and observed_at is None:
        raise ValueError("observed_at is required to sweep exhaustive sources")
    debts = dict(existing)
    created: list[str] = []
    updated: list[str] = []
    resolved: list[str] = []
    superseded: list[tuple[str, str]] = []
    reobserved: set[str] = set()

    for observation in _deduplicate(observations):
        debt_id = observation.debt_id
        if observation.status == "drift":
            reobserved.add(debt_id)
        previous = debts.get(debt_id)
        predecessors = _link_predecessors(observation, debt_id, debts, resolved, superseded)
        if predecessors and previous is not None:
            previous = replace(previous, supersedes=tuple(set(previous.supersedes) | set(predecessors)))
            debts[debt_id] = previous
        configured_authority = policy.authority_for(observation.kind)
        authority = _authority_ceiling(
            previous.authority if previous is not None else None,
            configured_authority,
        )
        priority = policy.priority_for(observation.kind, observation.confidence)

        if observation.status == "healthy":
            if previous is None or previous.status == "resolved":
                continue
            debts[debt_id] = Debt(
                id=debt_id,
                kind=observation.kind,
                subject=observation.subject,
                source=observation.source,
                current_state=observation.current_state,
                observed_state=observation.observed_state,
                confidence=observation.confidence,
                priority=priority,
                authority=authority,
                status="resolved",
                first_observed_at=previous.first_observed_at,
                last_observed_at=observation.observed_at,
                observation_count=previous.observation_count + 1,
                resolution="condition_recovered",
                supersedes=previous.supersedes,
                superseded_by=previous.superseded_by,
            )
            resolved.append(debt_id)
            continue

        if previous is None:
            debts[debt_id] = Debt(
                id=debt_id,
                kind=observation.kind,
                subject=observation.subject,
                source=observation.source,
                current_state=observation.current_state,
                observed_state=observation.observed_state,
                confidence=observation.confidence,
                priority=priority,
                authority=authority,
                status="open",
                first_observed_at=observation.observed_at,
                last_observed_at=observation.observed_at,
                observation_count=1,
                supersedes=predecessors,
            )
            created.append(debt_id)
            continue

        unchanged_same_run = (
            previous.status == "open"
            and previous.last_observed_at == observation.observed_at
            and dict(previous.current_state) == dict(observation.current_state)
            and dict(previous.observed_state) == dict(observation.observed_state)
            and previous.confidence == observation.confidence
            and previous.source == observation.source
            and previous.priority == priority
            and previous.authority == authority
        )
        if unchanged_same_run:
            continue

        debts[debt_id] = replace(
            previous,
            source=observation.source,
            current_state=observation.current_state,
            observed_state=observation.observed_state,
            confidence=observation.confidence,
            priority=priority,
            authority=authority,
            status="open",
            last_observed_at=observation.observed_at,
            observation_count=previous.observation_count + 1,
            resolution=None,
            # A reopened condition is current again, so it is no longer replaced.
            superseded_by=None if previous.status == "resolved" else previous.superseded_by,
        )
        updated.append(debt_id)

    sweep = frozenset(exhaustive_sources)
    if sweep:
        for debt_id in sorted(debts):
            previous = debts[debt_id]
            if (
                previous.status != "open"
                or previous.source not in sweep
                or debt_id in reobserved
            ):
                continue
            debts[debt_id] = replace(
                previous,
                status="resolved",
                last_observed_at=observed_at,
                resolution="condition_not_reobserved",
            )
            resolved.append(debt_id)

    return Reconciliation(
        debts=tuple(debts[key] for key in sorted(debts)),
        created=tuple(sorted(created)),
        updated=tuple(sorted(updated)),
        resolved=tuple(sorted(resolved)),
        superseded=tuple(sorted(superseded)),
    )
