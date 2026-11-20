"""Small offline composition of the P2 weekly seams; never an entrypoint.

This one-shot test/demo census accepts a poll explicitly produced by the genuine
collector, plans against the closed-world synthetic issue service, commits only
to a private TemporaryDirectory, and runs the read-only weekly binding. It cannot
grant durable eligibility.
"""
from __future__ import annotations

import datetime as dt
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from scripts.upstream_watcher import repository_batch, weekly_binding, weekly_collector, weekly_journal
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.weekly_effect import FakeIssueService
from scripts.upstream_watcher.weekly_collector import CollectedPoll


class _FakeIssueReader:
    """A sealed read-only adapter over FakeIssueService's fixture-owned store."""

    __slots__ = ("_service",)
    _ALLOWED = frozenset({"list_issues", "get_issue", "list_comments", "child_state"})

    def __init__(self, service: FakeIssueService, config_repo: str) -> None:
        if type(service) is not FakeIssueService:
            raise PayloadError("weekly census requires the exact FakeIssueService")
        if service.repo != config_repo:
            raise PayloadError("weekly census fake issue store must match the configured repository")
        self._service = service

    def __getattr__(self, name: str) -> Any:
        if name not in self._ALLOWED:
            raise AttributeError(name)
        return getattr(self._service, name)


@dataclass(frozen=True)
class CensusScope:
    named_id: str
    repository: str | None
    collection_status: str
    proof_status: str
    decision: str
    current_version: str | None = None
    release_version: str | None = None
    release_source: str | None = None
    release_time: str | None = None
    structural_delta: tuple[tuple[str, tuple[str, ...]], ...] = ()
    inventory_status: str = "unknown"
    liveness: tuple[tuple[str, str], ...] = ()
    name_drift_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeeklyCensus:
    """Sanitized observation/plan receipt; no issue payloads, bodies or diagnostics."""

    poll_id: str
    status: str
    scopes: tuple[CensusScope, ...]
    binding_status: str
    repository_statuses: tuple[tuple[str, str], ...]
    refusal: str | None
    logical_candidate_count: int
    known_legacy_holds: tuple[tuple[str, tuple[int, ...], tuple[str, ...]], ...] = ()
    actual_creates: int = 0
    actual_updates: int = 0
    write_authorized: bool = False
    write_readiness: bool = False
    persisted: bool = False
    state_mode: str = "ephemeral-empty"
    dispositions: tuple[Any, ...] = ()


def _safe_release_projection(result, authority: Mapping[str, dict[str, Any]]) -> tuple[str | None, str | None, str | None, str | None, tuple]:
    finding = result.finding
    if not isinstance(finding, dict):
        return None, None, None, None, ()
    try:
        from scripts.upstream_watcher import envelope
        repo = envelope.authority_repository(result.named_id, authority)
        release_repo = envelope.release_repository(finding.get("sourceUrl"), finding.get("newVersion"))
        if repo != release_repo:
            return None, None, None, None, ()
        version = finding.get("newVersion")
        source = finding.get("sourceUrl")
        source_repo = source.removeprefix("https://github.com/").split("/releases/", 1)[0]
        if source_repo != repo or not isinstance(version, str) or not version:
            return None, None, None, None, ()
    except (PayloadError, AttributeError, TypeError):
        return None, None, None, None, ()

    delta: list[tuple[str, tuple[str, ...]]] = []
    for key in ("componentAdds", "componentRemoves"):
        values = finding.get(key)
        if isinstance(values, list) and all(
            isinstance(item, str) and item and "/" not in item and "\\" not in item
            for item in values
        ):
            delta.append((key, tuple(sorted(set(values)))))
    current_version = finding.get("currentVersion")
    if not isinstance(current_version, str):
        current_version = None
    published = finding.get("releasedAt")
    if not isinstance(published, str):
        published = None
    return current_version, version, source, published, tuple(delta)


def run_weekly_census(
    suites: Sequence[Mapping[str, Any]],
    authority: Mapping[str, dict[str, Any]],
    fake_issues: FakeIssueService,
    collected: CollectedPoll,
    *,
    poll_id: str,
    observed_at: dt.datetime | str,
    state_mode: str,
    config_repo: str,
    held_repos: frozenset[str] = frozenset(),
    held_named_ids: frozenset[str] = frozenset(),
    unavailable_named_ids: frozenset[str] = frozenset(),
    index_loader,
    policy: dict[str, Any],
    historical_loader=lambda _identifier: {},
) -> WeeklyCensus:
    """Compose genuine offline seams using explicitly empty ephemeral state."""
    if state_mode != "ephemeral-empty":
        raise PayloadError("weekly census supports only explicitly empty ephemeral state; supplied named-v3 state is deferred")
    if not isinstance(poll_id, str) or not poll_id:
        raise PayloadError("poll_id must be explicit")
    if not isinstance(suites, Sequence) or isinstance(suites, (str, bytes)):
        raise PayloadError("suites must be an explicit sequence")
    if type(collected) is not CollectedPoll or collected.poll_id != poll_id:
        raise PayloadError("weekly census requires a CollectedPoll for the exact expected poll ID")
    suite_ids = [fm.get("id") for fm in suites if isinstance(fm, Mapping)]
    if len(suite_ids) != len(suites) or any(not isinstance(item, str) for item in suite_ids):
        raise PayloadError("weekly census suites must have exact named IDs")
    if len(set(suite_ids)) != len(suite_ids) or set(suite_ids) != {item.named_id for item in collected.results}:
        raise PayloadError("weekly census suite IDs must exactly match collected scopes")

    reader = _FakeIssueReader(fake_issues, config_repo)
    report, planner_code = repository_batch.run_repository_batch(
        list(collected.observed_findings), reader, apply=False, authority=authority,
        index_loader=index_loader, policy=policy, historical_loader=historical_loader,
        plan_only=True,
    )
    complete = planner_code == 0 and not report.get("unknownEvidence")
    poll = weekly_collector.build_poll_input(
        poll_id, observed_at, report, collected, authority, complete=complete,
        held_repos=held_repos, held_named_ids=held_named_ids,
        unavailable_named_ids=unavailable_named_ids,
    )

    with tempfile.TemporaryDirectory(prefix="gaia-weekly-census-") as tmp:
        path = f"{tmp}/named-v3.json"
        commit = weekly_journal.commit_poll(path, poll, authority, allow_bootstrap=True, initialized=False)
        bound = weekly_binding.bind_weekly_plans(
            commit, poll, reader, authority, index_loader=index_loader, policy=policy,
            historical_loader=historical_loader, journal_path=path,
        )

    known_holds = []
    for hold in report.get("knownLegacyHolds", []):
        if not isinstance(hold, dict):
            continue
        repo = hold.get("repository")
        number = hold.get("issueNumber")
        members = hold.get("namedIds", hold.get("skillIds", []))
        if isinstance(repo, str) and type(number) is int and isinstance(members, list) and all(isinstance(x, str) for x in members):
            known_holds.append((repo, (number,), tuple(sorted(set(members)))))

    held_repo_set, held_named_set, unavailable_set = set(poll.held_repos), set(poll.held_named_ids), set(poll.unavailable_named_ids)
    scopes = []
    refusal_text = "" if bound.refusal_reason is None else str(bound.refusal_reason)
    for result in collected.results:
        if result.named_id in held_named_set:
            decision = "held-named-scope"
        elif result.repository in held_repo_set:
            decision = "held-repository-scope"
        elif result.named_id in unavailable_set or result.status == "unavailable":
            decision = "unavailable"
        elif result.status == "unknown" or collected.unknown_evidence:
            decision = "unknown"
        elif "legacy" in refusal_text.lower() and result.repository:
            decision = "held-legacy"
        else:
            decision = "eligible-for-read-only-binding"
        current_version, version, source, released, delta = _safe_release_projection(result, authority)
        inventory = "verified" if any(inv.named_id == result.named_id and inv.poll_id == poll_id for inv in poll.complete_inventories) else "unknown"
        proof = "verified" if inventory == "verified" else (result.proof_reason if result.proof_reason in {"bootstrap-finding", "non-component-mode", "missing-tree-enumeration", "incomplete-tree-enumeration", "component-root-mismatch"} else "unknown")
        if result.status == "observed" and inventory != "verified" and decision == "eligible-for-read-only-binding":
            decision = "unknown"
        finding = result.finding if isinstance(result.finding, dict) else {}
        liveness = tuple(sorted(
            (row["skillId"], row["status"])
            for row in finding.get("linkLiveness", [])
            if isinstance(row, dict) and isinstance(row.get("skillId"), str)
            and row.get("status") in {"alive", "dead", "unknown", "network_error"}
        ))
        drift_ids = tuple(sorted(
            row["skillId"] for row in finding.get("nameDrift", [])
            if isinstance(row, dict) and isinstance(row.get("skillId"), str)
        ))
        scopes.append(CensusScope(
            result.named_id, result.repository, result.status, proof, decision,
            current_version, version, source, released, delta, inventory, liveness, drift_ids,
        ))

    repo_statuses = tuple((repo, item.status) for repo, item in sorted(bound.repositories.items()))
    global_unknown = (planner_code != 0 or bool(report.get("unknownEvidence"))
                      or bool(collected.unknown_evidence)
                      or any(scope.decision == "unknown" for scope in scopes))
    if global_unknown:
        status = "unknown-incomplete"
    elif bound.status == "refused":
        status = "global-refusal"
    elif held_repo_set or held_named_set or unavailable_set:
        status = "scoped-holds-or-unavailable"
    elif bound.status in {"bound", "idle"} and poll.complete:
        status = "observed-plan-only"
    else:
        status = "unknown-incomplete"
    refusal_code = bound.refusal_reason if bound.refusal_reason in {"incomplete-poll", "invalid-poll", "untrusted-binding"} else None
    return WeeklyCensus(
        poll_id, status, tuple(scopes), bound.status, repo_statuses, refusal_code,
        len(bound.candidate_intents), tuple(known_holds), actual_creates=0, actual_updates=0,
        write_authorized=False, write_readiness=False, persisted=False,
    )
