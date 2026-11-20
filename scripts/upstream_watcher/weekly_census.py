"""Small offline composition of the P2 weekly seams; never an entrypoint.

This one-shot test/demo census accepts a poll explicitly produced by the genuine
collector, plans against the closed-world synthetic issue service, commits only
to a private TemporaryDirectory, and runs the read-only weekly binding. It cannot
grant durable eligibility.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import re
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from scripts.upstream_watcher import envelope, repository_batch, weekly_binding, weekly_collector, weekly_journal, weekly_reducer
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

    @property
    def repo(self) -> str:
        return self._service.repo

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
    version_status: str = "unknown"
    delta_status: str = "unknown"
    canonical_removals: tuple[str, ...] = ()
    hold_reason: str | None = None


@dataclass(frozen=True)
class LegacyHold:
    repository: str
    issue: int
    legacy_named_id: str
    current_release_repository: str | None
    hold: str


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
    known_legacy_holds: tuple[LegacyHold, ...] = ()
    actual_creates: int = 0
    actual_updates: int = 0
    write_authorized: bool = False
    write_readiness: bool = False
    persisted: bool = False
    state_mode: str = "ephemeral-empty"
    dispositions: tuple[Any, ...] = ()


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}\Z")
_EMPTY_PROJECTION = (None, None, None, None, (), (), (), ())


def _safe_release_projection(result, authority, accepted):
    empty = _EMPTY_PROJECTION
    if result.status != "observed" or not accepted or not isinstance(result.finding, dict):
        return empty
    finding = result.finding
    try:
        repo, named, _, _ = weekly_reducer._validate_raw_observation(finding, authority)
        if (repo, named) != (result.repository, result.named_id):
            return empty
        weekly_reducer.parse_strict_utc(finding["releasedAt"])
        version, source = finding["newVersion"], finding["sourceUrl"]
        if not _TOKEN.fullmatch(version) or len(source) > 512:
            return empty
        current = finding.get("currentVersion")
        if current is not None and (not isinstance(current, str) or not _TOKEN.fullmatch(current)):
            return empty
        delta = []
        for key in ("componentAdds", "componentRemoves"):
            values = finding[key]
            if len(values) > envelope.MAX_ROWS or not all(isinstance(x, str) and _TOKEN.fullmatch(x) for x in values):
                return empty
            delta.append((key, tuple(sorted(values))))
        components = set(authority[named].get("suiteComponents") or [])
        live = set()
        for row in finding["linkLiveness"]:
            ident, status = row.get("skillId"), row.get("status")
            if ident not in components or not isinstance(ident, str) or not envelope.IDENTIFIER.fullmatch(ident):
                return empty
            if status == "network_error":
                code = status
            elif type(status) is int and 100 <= status <= 599 and not 200 <= status < 300:
                code = str(status)
            else:
                return empty
            live.add((ident, code))
        live_ids = {item[0] for item in live}
        for ident in finding.get("linkLivenessUnknown") or []:
            if (not isinstance(ident, str) or ident not in components
                    or not envelope.IDENTIFIER.fullmatch(ident) or ident in live_ids):
                return empty
            live.add((ident, "network_error"))
        drift = set()
        for row in finding["nameDrift"]:
            ident = row.get("skillId")
            if ident not in components or not isinstance(ident, str) or not envelope.IDENTIFIER.fullmatch(ident):
                return empty
            drift.add(ident)
        if len(live) > envelope.MAX_ROWS or len(drift) > envelope.MAX_ROWS:
            return empty
        return current, version, source, finding["releasedAt"], tuple(delta), tuple(sorted(live)), tuple(sorted(drift)), (repo, named)
    except (PayloadError, ValueError, TypeError, KeyError, AttributeError):
        return empty


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
    """Compose offline seams with empty state.

    index_loader and historical_loader are trusted, test-only local inputs: callers
    must supply data-only loaders, never network or mutation-capable callbacks.
    They do not grant issue write authority.
    """
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
    result_ids = [item.named_id for item in collected.results]
    if (len(set(suite_ids)) != len(suite_ids) or len(set(result_ids)) != len(result_ids)
            or set(suite_ids) != set(result_ids)):
        raise PayloadError("weekly census suite IDs must exactly match collected scopes")
    observations = collected.observed_findings
    observed_results = [item for item in collected.results if item.status == "observed"]
    if len(observations) != len(observed_results) or any(
        not isinstance(item.finding, dict) or sum(
            weekly_collector._observations_match_exactly(item.finding, obs) for obs in observations
        ) != 1 for item in observed_results
    ):
        raise PayloadError("weekly census observations disagree with collected results")

    invalid_observed_ids: set[str] = set()
    valid_observed_findings: list[dict[str, Any]] = []
    for item in collected.results:
        if item.status != "observed":
            continue
        if _safe_release_projection(item, authority, True) == _EMPTY_PROJECTION:
            invalid_observed_ids.add(item.named_id)
        else:
            valid_observed_findings.append(item.finding)

    reader = _FakeIssueReader(fake_issues, config_repo)
    report, planner_code = repository_batch.run_repository_batch(
        valid_observed_findings, reader, apply=False, authority=authority,
        index_loader=index_loader, policy=policy, historical_loader=historical_loader,
        plan_only=True,
    )
    complete = planner_code == 0 and not report.get("unknownEvidence")
    poll = weekly_collector.build_poll_input(
        poll_id, observed_at, report, collected, authority, complete=complete,
        held_repos=held_repos, held_named_ids=held_named_ids,
        unavailable_named_ids=unavailable_named_ids,
    )
    verified_inv_ids = {
        inv.named_id for inv in poll.complete_inventories if inv.poll_id == poll_id
    }
    incomplete_component_ids = {
        item.named_id
        for item in collected.results
        if item.status == "observed"
        and item.named_id not in invalid_observed_ids
        and isinstance(item.finding, dict)
        and item.finding.get("finding_type") == "update"
        and item.finding.get("mode") == "components"
        and item.named_id not in verified_inv_ids
    }
    poll_for_binding = (
        dataclasses.replace(poll, held_named_ids=poll.held_named_ids | frozenset(incomplete_component_ids))
        if incomplete_component_ids
        else poll
    )

    with tempfile.TemporaryDirectory(prefix="gaia-weekly-census-") as tmp:
        path = f"{tmp}/named-v3.json"
        commit = weekly_journal.commit_poll(path, poll_for_binding, authority, allow_bootstrap=True, initialized=False)
        bound = weekly_binding.bind_weekly_plans(
            commit, poll_for_binding, reader, authority, index_loader=index_loader, policy=policy,
            historical_loader=historical_loader, journal_path=path,
        )

    known_holds = []
    for hold in report.get("knownLegacyHolds", []):
        if not isinstance(hold, dict):
            continue
        try:
            repo = envelope.repository(hold.get("repository"))
            current = hold.get("currentReleaseRepository")
            if current is not None:
                current = envelope.repository(current)
            identifier, number = hold.get("legacyNamedId"), hold.get("issue")
            if (hold.get("kind") != "preserve-legacy-reference"
                    or hold.get("hold") != "separate-migration-approval-required"
                    or hold.get("writeReadiness") is not False
                    or type(number) is not int or number < 1
                    or not isinstance(identifier, str) or not envelope.IDENTIFIER.fullmatch(identifier)):
                continue
            known_holds.append(LegacyHold(repo, number, identifier, current, hold["hold"]))
        except PayloadError:
            continue

    held_repo_set, held_named_set, unavailable_set = set(poll.held_repos), set(poll.held_named_ids), set(poll.unavailable_named_ids)
    scopes = []
    for result in collected.results:
        if result.status == "unknown" or result.named_id in invalid_observed_ids or result.named_id in incomplete_component_ids:
            decision = "unknown"
        elif result.named_id in held_named_set:
            decision = "held-named-scope"
        elif result.repository in held_repo_set:
            decision = "held-repository-scope"
        elif result.named_id in unavailable_set or result.status == "unavailable":
            decision = "unavailable"
        elif collected.unknown_evidence:
            decision = "unknown"
        else:
            reduced = commit.reduction.decisions.get((result.repository, result.named_id))
            binding = bound.repositories.get(result.repository)
            if result.status == "up-to-date":
                decision = "up-to-date"
            elif (reduced is not None and reduced.eligible and bound.status == "bound"
                  and binding is not None and binding.status == "candidate-intent"
                  and any(member.named_id == result.named_id for member in binding.selected_members)):
                decision = "eligible-for-read-only-binding"
            elif reduced is not None and not reduced.eligible and reduced.decision == "hold":
                decision = "hold"
            else:
                decision = "unknown"
        scope_key = (result.repository, result.named_id)
        accepted = commit.reduction.status == "applied" and scope_key in commit.reduction.accepted_scopes
        reduced = commit.reduction.decisions.get(scope_key) if accepted else None
        matching_planned = [item for item in poll.planned_findings if item.get("skillId") == result.named_id]
        planned = matching_planned[0] if len(matching_planned) == 1 else None
        # Held or incomplete-tree scopes are not folded as eligible by the
        # reducer. Their raw observation may still be displayed as observational
        # only after canonical validation.
        observational_valid = False
        if (not accepted and commit.reduction.status == "applied" and planned is not None
                and result.named_id not in invalid_observed_ids
                and (result.repository in held_repo_set or result.named_id in held_named_set
                     or result.named_id in incomplete_component_ids)
                and not any(r.named_id == result.named_id for r in commit.reduction.rejected_observations)):
            try:
                pr, pn, _, pv = weekly_reducer._validate_planned_finding(planned, authority)
                observational_valid = ((pr, pn) == scope_key and isinstance(result.finding, dict)
                                       and pv.get("sourceUrl") == result.finding.get("sourceUrl")
                                       and pv.get("newVersion") == result.finding.get("newVersion"))
            except (PayloadError, ValueError, TypeError, KeyError):
                pass
        current_version, version, source, released, delta, liveness, drift_ids, checked = _safe_release_projection(result, authority, accepted or observational_valid)
        removals = ()
        canonical_source = reduced.finding if (accepted and reduced is not None and isinstance(reduced.finding, dict)) else None
        if checked and accepted and canonical_source is not None:
            try:
                planned_repo, planned_id, _, validated = weekly_reducer._validate_planned_finding(canonical_source, authority)
                values = validated.get("componentRemoves", [])
                if (planned_repo, planned_id) == checked and len(values) <= envelope.MAX_ROWS and all(
                    isinstance(x, str) and envelope.IDENTIFIER.fullmatch(x) for x in values
                ):
                    removals = tuple(sorted(values))
            except (PayloadError, ValueError, TypeError, KeyError):
                pass
        non_component_fact = (
            result.status == "observed"
            and result.named_id not in invalid_observed_ids
            and decision not in {"unknown", "unavailable"}
            and isinstance(result.finding, dict)
            and (result.finding.get("finding_type") == "bootstrap" or result.finding.get("mode") == "version-only")
        )
        if non_component_fact:
            inventory = "not-applicable"
        elif decision not in {"unknown", "unavailable"} and result.named_id in verified_inv_ids:
            inventory = "verified"
        else:
            inventory = "unknown"
        proof = (
            "unknown"
            if result.named_id in invalid_observed_ids
            else (
                "verified"
                if inventory == "verified"
                else (
                    result.proof_reason
                    if result.proof_reason in {
                        "bootstrap-finding",
                        "non-component-mode",
                        "missing-tree-enumeration",
                        "incomplete-tree-enumeration",
                        "component-root-mismatch",
                    }
                    else "unknown"
                )
            )
        )
        if result.status == "observed" and inventory == "unknown" and decision == "eligible-for-read-only-binding":
            decision = "unknown"
        if result.named_id in held_named_set:
            hold_reason = "held-named-scope"
        elif result.repository in held_repo_set:
            hold_reason = "held-repository-scope"
        elif result.named_id in incomplete_component_ids:
            hold_reason = "incomplete-tree"
        elif decision == "hold":
            hold_reason = "non-flush-window"
        else:
            hold_reason = None
        scopes.append(CensusScope(
            result.named_id, result.repository, result.status, proof, decision,
            current_version, version, source, released, delta, inventory, liveness, drift_ids,
            "release-observed" if checked else ("up-to-date" if result.status == "up-to-date" else "unknown"),
            "observational-raw" if checked else "unknown", removals, hold_reason,
        ))

    repo_statuses = tuple((repo, item.status) for repo, item in sorted(bound.repositories.items()))
    global_unknown = (planner_code != 0 or bool(report.get("unknownEvidence"))
                      or bool(collected.unknown_evidence)
                      or bool(invalid_observed_ids)
                      or bool(incomplete_component_ids)
                      or commit.reduction.status != "applied"
                      or bool(commit.reduction.rejected_observations)
                      or any(item.status in {"ambiguous", "declined", "incomplete"}
                             for item in bound.repositories.values())
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
