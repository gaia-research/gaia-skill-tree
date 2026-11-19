"""Bounded offline collector provenance seam for P2 weekly observations (Slice 3).

Scope
-----
This module connects the actual watcher/liveness release-tree enumeration seam
(``watcher._poll_suite_with_enumeration`` / ``liveness.enumerate_component_tree``)
to ``weekly_reducer.ScopedCompleteInventory`` and ``weekly_reducer.PollInput``
using ONE shared repo/tag/root tree listing per polled suite.

Invariants
----------
* Offline / opt-in only: ordinary ``watcher.main``, ``watcher._poll_suite``,
  ``repository_batch.run_repository_batch``, and deployed workflows are NOT
  activated or altered.
* Single listing authority: raw short-slug ``(componentAdds, componentRemoves)``
  and complete-inventory provenance (``present_slugs``) come from the exact same
  ``ComponentTreeEnumeration`` object — never two unsynchronized reads or a
  fixture-only boolean.
* Exact authority binding: requires exact case-sensitive ``named_id`` in
  ``authority``, verified ``envelope.authority_repository`` ==
  ``envelope.release_repository``, ``releaseidentity.validateReleaseSource``,
  exact configured ``upstreamComponentRoot`` (default ``"skills"`` only when
  unconfigured), and the current ``poll_id``.
* Conservative unknown: bootstrap findings, version-only findings, missing/invalid/
  ambiguous roots, truncated trees (positive truncated walk is NOT enabled in
  this slice), omitted/non-false truncation flags, missing tree SHAs, malformed
  or duplicate entries, submodules under the root, ambiguous slug paths, forged
  metadata, and stale raw P1 reports without explicit proof NEVER produce a
  ``ScopedCompleteInventory`` and NEVER prove absence.
* Zero writes: performs no issue writes, no registry/data mutations, and no
  settlement.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from scripts.upstream_watcher import envelope, watcher, weekly_reducer
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import GhError, SuiteUnavailable, UnknownEvidenceError
from scripts.upstream_watcher.liveness import ComponentTreeEnumeration
from scripts.upstream_watcher.releaseidentity import validateReleaseSource
from scripts.upstream_watcher.weekly_reducer import (
    PollInput,
    ScopedCompleteInventory,
    poll_input_from_batch_report,
    qualify_complete_inventory,
)


@dataclass(frozen=True)
class SuiteCollectionResult:
    """Single-suite offline poll outcome with explicit inventory provenance."""

    named_id: str
    repository: str | None
    status: str  # "observed" | "up-to-date" | "unavailable" | "unknown"
    finding: dict[str, Any] | None = None
    enumeration: ComponentTreeEnumeration | None = None
    complete_inventory: ScopedCompleteInventory | None = None
    proof_reason: str | None = None
    unavailable_reason: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class CollectedPoll:
    """Aggregated offline collector output for one poll ID."""

    poll_id: str
    results: tuple[SuiteCollectionResult, ...]
    observed_findings: tuple[dict[str, Any], ...]
    complete_inventories: tuple[ScopedCompleteInventory, ...]
    unavailable_named_ids: frozenset[str]
    unknown_evidence: tuple[dict[str, Any], ...]
    up_to_date_named_ids: frozenset[str]


def _authority_repo_safe(named_id: Any, authority: Mapping[str, dict[str, Any]]) -> str | None:
    try:
        return envelope.authority_repository(named_id, authority)
    except PayloadError:
        return None


def _exact_structural_equal(left: Any, right: Any) -> bool:
    """Strict non-coercing structural equality for JSON-compatible values.

    Rejects Python bool/int/float coercions (e.g. ``True == 1``, ``1 == 1.0``),
    non-finite floats (NaN/Inf), and non-string mapping keys.
    """
    if type(left) is not type(right):
        return False
    if left is None or isinstance(left, (bool, str, int)):
        return left == right
    if isinstance(left, float):
        return math.isfinite(left) and math.isfinite(right) and left == right
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _exact_structural_equal(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return False
        for key in left:
            if type(key) is not str:
                return False
            if not _exact_structural_equal(left[key], right[key]):
                return False
        return True
    return False


def _observations_match_exactly(report_obs: Any, collected_obs: Any) -> bool:
    """Require exact non-coercing canonical JSON match across all raw finding fields."""
    if not isinstance(report_obs, dict) or not isinstance(collected_obs, dict):
        return False
    if not _exact_structural_equal(report_obs, collected_obs):
        return False
    try:
        left_json = json.dumps(
            report_obs,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        right_json = json.dumps(
            collected_obs,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return False
    return left_json == right_json


def _index_unique_observations(
    observations: Sequence[Any],
    authority: Mapping[str, dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], set[tuple[str, str]]]:
    """Index raw observations by exact ``(repo, named_id)`` requiring uniqueness."""
    by_scope: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_scopes: set[tuple[str, str]] = set()
    for obs in observations:
        if not isinstance(obs, dict):
            continue
        named_id = obs.get("skillId")
        repo = _authority_repo_safe(named_id, authority)
        if repo is None or not isinstance(named_id, str):
            continue
        scope = (repo, named_id)
        if scope in duplicate_scopes:
            continue
        if scope in by_scope:
            del by_scope[scope]
            duplicate_scopes.add(scope)
            continue
        by_scope[scope] = obs
    return by_scope, duplicate_scopes


def collect_suite_observation(
    fm: Mapping[str, Any],
    authority: Mapping[str, dict[str, Any]],
    *,
    poll_id: str,
    verbose: bool = False,
) -> SuiteCollectionResult:
    """Poll one suite through the actual watcher/liveness seam and bind provenance.

    Returns a :class:`SuiteCollectionResult` whose ``finding`` preserves exact
    raw short slugs and whose ``complete_inventory`` is populated ONLY when the
    same single tree listing proves complete, non-truncated, verified root
    coverage and passes ``weekly_reducer.qualify_complete_inventory``.
    """
    validated_poll_id = weekly_reducer._validate_poll_id(poll_id)
    if not isinstance(fm, Mapping):
        raise PayloadError("suite frontmatter must be a mapping")
    named_id = fm.get("id")
    if (
        not isinstance(named_id, str)
        or not named_id
        or named_id not in authority
        or not isinstance(authority[named_id], dict)
        or authority[named_id].get("id") != named_id
    ):
        return SuiteCollectionResult(
            named_id=str(named_id) if isinstance(named_id, str) else "?",
            repository=None,
            status="unknown",
            proof_reason="named-not-in-authority",
            error_detail="named identity is not in registry authority (exact case-sensitive match required)",
        )

    auth_repo = _authority_repo_safe(named_id, authority)

    try:
        finding, enumeration = watcher._poll_suite_with_enumeration(
            copy.deepcopy(dict(fm)),
            dict(authority),
            verbose=verbose,
        )
    except SuiteUnavailable as exc:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=auth_repo,
            status="unavailable",
            proof_reason=exc.reason or "suite-unavailable",
            unavailable_reason=exc.reason,
            error_detail=str(exc),
        )
    except UnknownEvidenceError as exc:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=auth_repo,
            status="unknown",
            proof_reason="unknown-evidence",
            error_detail=str(exc),
        )

    if finding is None:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=auth_repo,
            status="up-to-date",
            proof_reason="up-to-date",
        )

    observed = copy.deepcopy(finding)

    # Verify exact release repository, source identity, and configured component root.
    try:
        repo = envelope.authority_repository(named_id, authority)
        release_repo = envelope.release_repository(observed.get("sourceUrl"), observed.get("newVersion"))
        if release_repo != repo:
            raise PayloadError("observed release source disagrees with registry authority")
        validateReleaseSource(observed)
    except (PayloadError, GhError) as exc:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=auth_repo,
            status="observed",
            finding=observed,
            enumeration=enumeration,
            complete_inventory=None,
            proof_reason=str(exc),
        )

    try:
        auth_root = weekly_reducer._authority_component_root(named_id, authority)
    except PayloadError as exc:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=repo,
            status="observed",
            finding=observed,
            enumeration=enumeration,
            complete_inventory=None,
            proof_reason=str(exc),
        )

    observed["upstreamComponentRoot"] = auth_root

    if observed.get("finding_type") != "update":
        return SuiteCollectionResult(
            named_id=named_id,
            repository=repo,
            status="observed",
            finding=observed,
            enumeration=enumeration,
            complete_inventory=None,
            proof_reason="bootstrap-finding",
        )
    if observed.get("mode") != "components":
        return SuiteCollectionResult(
            named_id=named_id,
            repository=repo,
            status="observed",
            finding=observed,
            enumeration=enumeration,
            complete_inventory=None,
            proof_reason="non-component-mode",
        )
    if enumeration is None:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=repo,
            status="observed",
            finding=observed,
            enumeration=None,
            complete_inventory=None,
            proof_reason="missing-tree-enumeration",
        )
    if (
        not enumeration.complete
        or enumeration.truncated
        or not enumeration.root_verified
        or enumeration.present_slugs is None
        or enumeration.proof_reason is not None
    ):
        return SuiteCollectionResult(
            named_id=named_id,
            repository=repo,
            status="observed",
            finding=observed,
            enumeration=enumeration,
            complete_inventory=None,
            proof_reason=enumeration.proof_reason or "incomplete-tree-enumeration",
        )
    if enumeration.component_root != auth_root:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=repo,
            status="observed",
            finding=observed,
            enumeration=enumeration,
            complete_inventory=None,
            proof_reason="component-root-mismatch",
        )

    candidate = ScopedCompleteInventory(
        poll_id=validated_poll_id,
        repository=repo,
        named_id=named_id,
        version=observed["newVersion"],
        source_url=observed["sourceUrl"],
        component_root=enumeration.component_root,
        present_slugs=enumeration.present_slugs,
        complete=True,
        truncated=False,
        root_verified=True,
    )
    verified_slugs, inv_reason = qualify_complete_inventory(
        candidate,
        poll_id=validated_poll_id,
        repository=repo,
        named_id=named_id,
        raw_obs=observed,
        authority=authority,
    )
    if verified_slugs is None or inv_reason is not None:
        return SuiteCollectionResult(
            named_id=named_id,
            repository=repo,
            status="observed",
            finding=observed,
            enumeration=enumeration,
            complete_inventory=None,
            proof_reason=inv_reason or "inventory-qualification-failed",
        )

    return SuiteCollectionResult(
        named_id=named_id,
        repository=repo,
        status="observed",
        finding=observed,
        enumeration=enumeration,
        complete_inventory=candidate,
        proof_reason=None,
    )


def collect_suites(
    suites: Sequence[Mapping[str, Any]],
    authority: Mapping[str, dict[str, Any]],
    *,
    poll_id: str,
    verbose: bool = False,
) -> CollectedPoll:
    """Collect observations and optional complete-inventory proofs for a batch of suites."""
    validated_poll_id = weekly_reducer._validate_poll_id(poll_id)
    seen_ids: set[str] = set()
    results: list[SuiteCollectionResult] = []
    observed_findings: list[dict[str, Any]] = []
    complete_inventories: list[ScopedCompleteInventory] = []
    unavailable_named_ids: set[str] = set()
    unknown_evidence: list[dict[str, Any]] = []
    up_to_date_named_ids: set[str] = set()

    for fm in suites:
        if not isinstance(fm, Mapping):
            raise PayloadError("suite frontmatter entry must be a mapping")
        sid = fm.get("id")
        if isinstance(sid, str) and sid:
            if sid in seen_ids:
                raise PayloadError(f"duplicate suite identity in poll batch: {sid!r}")
            seen_ids.add(sid)

        res = collect_suite_observation(fm, authority, poll_id=validated_poll_id, verbose=verbose)
        results.append(res)
        if res.status == "observed" and res.finding is not None:
            observed_findings.append(copy.deepcopy(res.finding))
            if res.complete_inventory is not None:
                complete_inventories.append(res.complete_inventory)
        elif res.status == "unavailable":
            unavailable_named_ids.add(res.named_id)
        elif res.status == "unknown":
            unknown_evidence.append(
                {
                    "source": "github-poll",
                    "suite": res.named_id,
                    "detail": res.error_detail or res.proof_reason or "unknown evidence",
                }
            )
        elif res.status == "up-to-date":
            up_to_date_named_ids.add(res.named_id)

    return CollectedPoll(
        poll_id=validated_poll_id,
        results=tuple(results),
        observed_findings=tuple(observed_findings),
        complete_inventories=tuple(complete_inventories),
        unavailable_named_ids=frozenset(unavailable_named_ids),
        unknown_evidence=tuple(unknown_evidence),
        up_to_date_named_ids=frozenset(up_to_date_named_ids),
    )


def build_poll_input(
    poll_id: str,
    observed_at: dt.datetime | str,
    report: Mapping[str, Any],
    collected: CollectedPoll | None,
    authority: Mapping[str, dict[str, Any]],
    *,
    complete: bool = True,
    held_repos: frozenset[str] = frozenset(),
    held_named_ids: frozenset[str] = frozenset(),
    unavailable_named_ids: frozenset[str] = frozenset(),
) -> PollInput:
    """Build a ``weekly_reducer.PollInput`` from a real P1 batch report and optional collector proof.

    * When ``collected`` is ``None`` (for example, a stale raw P1 report), no
      ``ScopedCompleteInventory`` is attached and omitted rows stay unknown.
    * When ``collected`` is provided, only inventories bound to the exact same
      ``poll_id``, matching an actual ``report["observedFindings"]`` entry, and
      passing ``qualify_complete_inventory`` against that entry are attached.
    * Any ``collected.unknown_evidence`` forces ``complete=False`` fail-closed.
    """
    validated_poll_id = weekly_reducer._validate_poll_id(poll_id)
    base = poll_input_from_batch_report(
        validated_poll_id,
        observed_at,
        report,
        complete=complete,
        held_repos=held_repos,
        held_named_ids=held_named_ids,
        unavailable_named_ids=unavailable_named_ids,
    )
    if collected is None:
        return base
    if not isinstance(collected, CollectedPoll):
        raise PayloadError("collected must be a CollectedPoll or None")

    # Index observed findings in both the actual batch report and the collected
    # poll by exact (repo, named_id), requiring a unique entry on both sides.
    report_obs_by_scope, duplicate_report_scopes = _index_unique_observations(
        base.observed_findings, authority
    )
    collected_obs_by_scope, duplicate_collected_scopes = _index_unique_observations(
        collected.observed_findings, authority
    )

    verified_inventories: list[ScopedCompleteInventory] = []
    if collected.poll_id == validated_poll_id:
        inv_by_scope: dict[tuple[str, str], ScopedCompleteInventory] = {}
        duplicate_inv_scopes: set[tuple[str, str]] = set()
        for inv in collected.complete_inventories:
            if not isinstance(inv, ScopedCompleteInventory):
                continue
            try:
                inv_repo = envelope.repository(inv.repository)
            except PayloadError:
                continue
            scope = (inv_repo, inv.named_id)
            if scope in duplicate_inv_scopes:
                continue
            if scope in inv_by_scope:
                del inv_by_scope[scope]
                duplicate_inv_scopes.add(scope)
                continue
            if inv.poll_id != validated_poll_id:
                duplicate_inv_scopes.add(scope)
                continue
            inv_by_scope[scope] = inv

        excluded_scopes = (
            duplicate_report_scopes | duplicate_collected_scopes | duplicate_inv_scopes
        )
        for scope, inv in inv_by_scope.items():
            if scope in excluded_scopes:
                continue
            raw_obs = report_obs_by_scope.get(scope)
            col_obs = collected_obs_by_scope.get(scope)
            if raw_obs is None or col_obs is None:
                continue
            if not _observations_match_exactly(raw_obs, col_obs):
                continue
            inv_repo, inv_named_id = scope
            slugs, reason = qualify_complete_inventory(
                inv,
                poll_id=validated_poll_id,
                repository=inv_repo,
                named_id=inv_named_id,
                raw_obs=raw_obs,
                authority=authority,
            )
            if slugs is not None and reason is None:
                verified_inventories.append(inv)

    merged_unavailable = set(base.unavailable_named_ids)
    for named_id in collected.unavailable_named_ids:
        if isinstance(named_id, str) and envelope.IDENTIFIER.fullmatch(named_id):
            merged_unavailable.add(named_id)

    effective_complete = base.complete and len(collected.unknown_evidence) == 0
    return PollInput(
        poll_id=base.poll_id,
        observed_at=base.observed_at,
        observed_findings=base.observed_findings,
        planned_findings=base.planned_findings,
        complete=effective_complete,
        held_repos=base.held_repos,
        held_named_ids=base.held_named_ids,
        unavailable_named_ids=frozenset(merged_unavailable),
        complete_inventories=tuple(verified_inventories),
    )
