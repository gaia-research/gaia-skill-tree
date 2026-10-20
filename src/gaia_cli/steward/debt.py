"""Semantic deduplication and debt lifecycle reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Collection, Iterable, Mapping

from gaia_cli.steward.models import AuthorityClass, Debt, Observation, stable_json
from gaia_cli.steward.policy import StewardPolicy


@dataclass(frozen=True)
class Reconciliation:
    debts: tuple[Debt, ...]
    created: tuple[str, ...]
    updated: tuple[str, ...]
    resolved: tuple[str, ...]


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
    reobserved: set[str] = set()

    for observation in _deduplicate(observations):
        debt_id = observation.debt_id
        if observation.status == "drift":
            reobserved.add(debt_id)
        previous = debts.get(debt_id)
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
    )
