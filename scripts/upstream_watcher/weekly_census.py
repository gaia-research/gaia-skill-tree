"""Small offline composition of the P2 weekly seams; never an entrypoint.

This is a one-shot census for tests/demonstrations only. It collects through the
real watcher seam, runs the real repository planner in plan-only mode, adapts
that report into a PollInput, commits only to a private TemporaryDirectory, and
runs the real read-only binding against the caller's fake issue inventory.
No checkpoint path, cache, transport, workflow, or production entrypoint is
accepted here. Consequently this module cannot grant durable eligibility.
"""
from __future__ import annotations

import datetime as dt
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from scripts.upstream_watcher import repository_batch, weekly_binding, weekly_collector, weekly_journal
from scripts.upstream_watcher.approval import PayloadError


class _ReadOnlyTransport:
    """Second guard: expose the fake's reads while refusing every known mutator."""

    _MUTATORS = frozenset({"create_issue", "edit_issue", "edit_labels", "comment", "edit_comment", "delete_comment"})

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        if name in self._MUTATORS:
            raise PayloadError("weekly census refuses an issue-write transport method")
        return getattr(self._inner, name)


@dataclass(frozen=True)
class CensusScope:
    named_id: str
    repository: str | None
    collection_status: str
    proof_status: str


@dataclass(frozen=True)
class WeeklyCensus:
    """Sanitized observation/plan receipt. Contains no issue payloads or bodies."""

    poll_id: str
    status: str
    scopes: tuple[CensusScope, ...]
    binding_status: str
    repository_statuses: tuple[tuple[str, str], ...]
    refusal: str | None
    logical_candidate_count: int
    actual_creates: int = 0
    actual_updates: int = 0
    write_authorized: bool = False
    write_readiness: bool = False
    persisted: bool = False
    state_mode: str = "ephemeral-empty"
    dispositions: tuple[Any, ...] = ()


def run_weekly_census(
    suites: Sequence[Mapping[str, Any]],
    authority: Mapping[str, dict[str, Any]],
    gh: Any,
    *,
    poll_id: str,
    observed_at: dt.datetime | str,
    state_mode: str,
    held_repos: frozenset[str] = frozenset(),
    held_named_ids: frozenset[str] = frozenset(),
    unavailable_named_ids: frozenset[str] = frozenset(),
    index_loader,
    policy: dict[str, Any],
    historical_loader=lambda _identifier: {},
) -> WeeklyCensus:
    """Compose genuine offline seams using a fresh, explicitly empty state.

    The caller must explicitly choose ``state_mode="ephemeral-empty"``. A
    supplied named-v3 checkpoint is intentionally not accepted: the current
    binding contract requires a persisted, applied commit plus an independently
    trusted pin, and this bounded census has no safe supplied-state commit
    lineage. Missing/corrupt/foreign/stale checkpoint classification and
    trusted-pin validation remain the journal API's responsibility; this helper
    never opens, copies, bootstraps, or modifies a caller checkpoint.

    ``gh`` must be an offline fake/read-only transport. The repository planner
    is always invoked with ``apply=False, plan_only=True``; binding itself
    verifies the complete inventory and contains no mutators. Collector network
    functions are not replaced here: offline callers/tests must provide their
    fake upstream implementation at the existing collector seams.
    """
    if state_mode != "ephemeral-empty":
        raise PayloadError("weekly census supports only explicitly empty ephemeral state; supplied named-v3 state is deferred")
    if not isinstance(poll_id, str) or not poll_id:
        raise PayloadError("poll_id must be explicit")
    if not isinstance(suites, Sequence) or isinstance(suites, (str, bytes)):
        raise PayloadError("suites must be an explicit sequence")

    read_only_gh = _ReadOnlyTransport(gh)
    collected = weekly_collector.collect_suites(suites, authority, poll_id=poll_id)
    report, planner_code = repository_batch.run_repository_batch(
        list(collected.observed_findings),
        read_only_gh,
        apply=False,
        authority=authority,
        index_loader=index_loader,
        policy=policy,
        historical_loader=historical_loader,
        plan_only=True,
    )
    # Never treat absent finding/repository entries as clearance. Unknown
    # planner evidence is already turned into incomplete by build_poll_input;
    # collector unknowns independently make it incomplete there as well.
    complete = planner_code == 0 and not report.get("unknownEvidence")
    poll = weekly_collector.build_poll_input(
        poll_id,
        observed_at,
        report,
        collected,
        authority,
        complete=complete,
        held_repos=held_repos,
        held_named_ids=held_named_ids,
        unavailable_named_ids=unavailable_named_ids,
    )

    with tempfile.TemporaryDirectory(prefix="gaia-weekly-census-") as tmp:
        path = f"{tmp}/named-v3.json"
        commit = weekly_journal.commit_poll(
            path,
            poll,
            authority,
            allow_bootstrap=True,
            initialized=False,
        )
        bound = weekly_binding.bind_weekly_plans(
            commit,
            poll,
            read_only_gh,
            authority,
            index_loader=index_loader,
            policy=policy,
            historical_loader=historical_loader,
            journal_path=path,
        )

    scopes = tuple(
        CensusScope(
            named_id=result.named_id,
            repository=result.repository,
            collection_status=result.status,
            proof_status="verified" if result.complete_inventory is not None else (result.proof_reason or "not-proved"),
        )
        for result in collected.results
    )
    return WeeklyCensus(
        poll_id=poll_id,
        status="observed-plan-only" if planner_code == 0 else "held-unknown",
        scopes=scopes,
        binding_status=bound.status,
        repository_statuses=tuple((repo, item.status) for repo, item in sorted(bound.repositories.items())),
        refusal=bound.refusal_reason,
        logical_candidate_count=len(bound.candidate_intents),
        actual_creates=0,
        actual_updates=0,
        write_authorized=False,
        write_readiness=False,
        persisted=False,
    )
