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

from scripts.upstream_watcher import envelope, finder, liveness as watcher_liveness, name_drift, watcher, weekly_reducer, weekly_release_proof
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import GhError, SuiteUnavailable, UnknownEvidenceError
from scripts.upstream_watcher.liveness import ComponentTreeEnumeration
from scripts.upstream_watcher.name_drift import HostedNameDriftResult
from scripts.upstream_watcher.readonly_issue_port import HostedUpstreamClient
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
    release_status: str | None = None
    name_drift_result: HostedNameDriftResult | None = None


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


_APPROVED_RELEASE_PROOF_UNKNOWN_REASONS = frozenset({
    "invalid-authority-scope",
    "invalid-expected-repository",
    "invalid-expected-repository-id",
    "named-not-in-authority",
    "authority-repository-mismatch",
    "watch-upstream-disabled",
    "invalid-authority-source",
    "missing-authority-source",
    "authority-upstream-repo-contradiction",
    "invalid-authority-upstream-repo",
    "locked-source-violation",
    "invalid-registered-version",
    "invalid-authority-version",
    "registered-version-mismatch",
    "invalid-latest-observation",
    "invalid-redirect-flag",
    "invalid-status-code",
    "requested-repository-mismatch",
    "endpoint-url-mismatch",
    "redirect-not-allowed",
    "malformed-release-body",
    "malformed-release-tag",
    "malformed-release-time",
    "malformed-release-source",
    "release-repo-mismatch",
    "metadata-missing-for-pinned-id",
    "invalid-metadata-observation",
    "invalid-metadata-redirect-flag",
    "invalid-metadata-status-code",
    "metadata-requested-repository-mismatch",
    "metadata-endpoint-url-mismatch",
    "metadata-redirect",
    "metadata-404",
    "metadata-403",
    "metadata-non-200",
    "metadata-malformed",
    "metadata-repo-mismatch",
    "metadata-malformed-repo-id",
    "metadata-repo-id-mismatch",
    "metadata-missing-repo-id",
    "bare-404-uncorroborated",
    "missing-release-body",
    "release-proof-finding-mismatch",
    "unexpected-release-proof-status",
    "invalid-tag-tree-repository",
    "invalid-tag-tree-tag",
    "tag-ref-fetch-failed",
    "tag-ref-redirect",
    "tag-ref-not-found",
    "tag-ref-non-200",
    "tag-ref-malformed",
    "tag-ref-namespace-mismatch",
    "tag-ref-url-mismatch",
    "tag-ref-unexpected-pagination",
    "tag-ref-invalid-object-type",
    "tag-ref-invalid-object-sha",
    "tag-ref-object-url-mismatch",
    "tag-object-fetch-failed",
    "tag-object-redirect",
    "tag-object-not-found",
    "tag-object-non-200",
    "tag-object-malformed",
    "tag-object-sha-mismatch",
    "tag-object-url-mismatch",
    "tag-object-unexpected-pagination",
    "tag-object-name-mismatch",
    "tag-object-invalid-target-type",
    "tag-object-invalid-target-sha",
    "tag-object-target-url-mismatch",
    "tag-peel-cycle",
    "tag-peel-depth-exceeded",
    "commit-fetch-failed",
    "commit-redirect",
    "commit-not-found",
    "commit-non-200",
    "commit-malformed",
    "commit-sha-mismatch",
    "commit-url-mismatch",
    "commit-unexpected-pagination",
    "commit-invalid-tree-sha",
    "commit-tree-url-mismatch",
    "tree-fetch-failed",
    "tree-redirect",
    "tree-not-found",
    "tree-non-200",
    "tree-malformed",
    "tree-sha-mismatch",
    "tree-url-mismatch",
    "tree-unexpected-pagination",
    "tree-truncated",
    "tag-ref-recheck-failed",
    "tag-ref-changed",
})


def _sanitize_release_proof_unknown_reason(reason: Any) -> str:
    if isinstance(reason, str):
        if reason in _APPROVED_RELEASE_PROOF_UNKNOWN_REASONS:
            return reason
        if reason.startswith("unconfirmed-http-") and reason[17:].isdigit() and len(reason) <= 24:
            return reason
    return "unknown-evidence"


def _collect_suite_hosted(
    fm: dict[str, Any],
    authority: Mapping[str, dict[str, Any]],
    upstream_client: HostedUpstreamClient,
) -> tuple[str, dict[str, Any] | None, ComponentTreeEnumeration | None, str | None, HostedNameDriftResult | None]:
    """Hosted read-only poll path using ``HostedUpstreamClient`` + ``classify_release_proof``."""
    if type(upstream_client) is not HostedUpstreamClient:
        raise PayloadError("hosted collector requires exact HostedUpstreamClient")
    named_id = fm.get("id", "?")
    resolved = finder.resolve_suite_source(fm)
    if not resolved:
        raise UnknownEvidenceError(f"{named_id}: missing suite source")
    owner, repo, _ = resolved
    auth_repo = envelope.authority_repository(named_id, authority)
    upstream_block = fm.get("upstream")
    registered_version = upstream_block.get("version") if isinstance(upstream_block, Mapping) else None

    latest_obs, meta_obs = upstream_client.fetch_release_observations(owner, repo)
    proof = weekly_release_proof.classify_release_proof(
        named_id,
        authority,
        expected_repository=auth_repo,
        registered_version=registered_version,
        latest_response=latest_obs,
        repo_metadata_response=meta_obs,
    )
    if proof.status == "unknown":
        return "unknown", None, None, _sanitize_release_proof_unknown_reason(proof.reason), None
    if proof.status == "unavailable":
        raise SuiteUnavailable(proof.reason, reason="permanent")
    if proof.status == "no-visible-latest-release":
        return "no-visible-latest-release", None, None, None, None
    if proof.status != "observed":
        return "unknown", None, None, "unexpected-release-proof-status", None

    if proof.relation == "same-version":
        return (
            "same-version",
            {
                "skillId": named_id,
                "currentVersion": proof.release_version,
                "newVersion": proof.release_version,
                "sourceUrl": proof.release_source,
                "releasedAt": proof.release_time,
            },
            None,
            None,
            None,
        )

    if not isinstance(latest_obs.body, Mapping):
        return "unknown", None, None, "missing-release-body", None
    finding = finder.compute_finding(fm, dict(latest_obs.body))
    if (
        not isinstance(finding, dict)
        or finding.get("newVersion") != proof.release_version
        or finding.get("sourceUrl") != proof.release_source
    ):
        return "unknown", None, None, "release-proof-finding-mismatch", None

    registry_map = dict(authority)
    mode = finder.detect_mode(fm, registry_map)
    finding["mode"] = mode
    new_version = finding["newVersion"]
    components = fm.get("suiteComponents") or []
    component_root = fm.get("upstreamComponentRoot") or "skills"
    enumeration: ComponentTreeEnumeration | None = None
    drift_result: HostedNameDriftResult | None = None
    if finding["finding_type"] == "update" and mode == "components":
        tree_proof = upstream_client.fetch_verified_tag_tree(owner, repo, new_version)
        if not tree_proof.ok or tree_proof.tree_data is None or tree_proof.tree_sha is None:
            return "unknown", None, None, _sanitize_release_proof_unknown_reason(tree_proof.reason), None
        try:
            enumeration = watcher_liveness.enumerate_component_tree_from_verified_data(
                owner,
                repo,
                new_version,
                component_root,
                components,
                tree_data=tree_proof.tree_data,
                expected_tree_sha=tree_proof.tree_sha,
            )
        except UnknownEvidenceError as exc:
            reason = _sanitize_release_proof_unknown_reason(str(exc))
            return "unknown", None, None, reason if reason != "unknown-evidence" else "tree-malformed", None
        finding["componentAdds"] = list(enumeration.adds)
        finding["componentRemoves"] = list(enumeration.removes)
        live_rows = watcher_liveness.check_component_liveness(
            components,
            registry_map,
            head_check_fn=upstream_client.head_check,
        )
        finding["linkLiveness"] = [row for row in live_rows if row["status"] != "network_error"]
        finding["linkLivenessUnknown"] = sorted(
            row["skillId"] for row in live_rows if row["status"] == "network_error"
        )
        drift_result = name_drift.check_name_drift_hosted(
            components,
            registry_map,
            fetch_text_fn=upstream_client.fetch_text,
        )
        finding["nameDrift"] = [{"skillId": comp_id} for comp_id in drift_result.verified_drift]
    else:
        finding["componentAdds"] = []
        finding["componentRemoves"] = []
        finding["linkLiveness"] = []
        finding["linkLivenessUnknown"] = []
        finding["nameDrift"] = []
    return "observed", finding, enumeration, None, drift_result


def collect_suite_observation(
    fm: Mapping[str, Any],
    authority: Mapping[str, dict[str, Any]],
    *,
    poll_id: str,
    verbose: bool = False,
    upstream_client: HostedUpstreamClient | None = None,
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

    drift_result: HostedNameDriftResult | None = None
    try:
        if upstream_client is not None:
            rel_status, finding, enumeration, hosted_reason, drift_result = _collect_suite_hosted(
                copy.deepcopy(dict(fm)),
                authority,
                upstream_client,
            )
            if rel_status == "unknown":
                safe_reason = _sanitize_release_proof_unknown_reason(hosted_reason)
                return SuiteCollectionResult(
                    named_id=named_id,
                    repository=auth_repo,
                    status="unknown",
                    proof_reason=safe_reason,
                    error_detail=safe_reason,
                    release_status="bare-404-uncorroborated" if safe_reason == "bare-404-uncorroborated" else None,
                )
            if rel_status in {"same-version", "no-visible-latest-release"}:
                return SuiteCollectionResult(
                    named_id=named_id,
                    repository=auth_repo,
                    status="up-to-date",
                    finding=finding,
                    proof_reason=rel_status,
                    release_status=rel_status,
                )
        else:
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
            proof_reason="uncorroborated-404" if str(exc) == "uncorroborated-404" else "unknown-evidence",
            error_detail=str(exc),
            release_status="uncorroborated-404" if str(exc) == "uncorroborated-404" else None,
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
            name_drift_result=drift_result,
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
            name_drift_result=drift_result,
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
            name_drift_result=drift_result,
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
            name_drift_result=drift_result,
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
            name_drift_result=drift_result,
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
            name_drift_result=drift_result,
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
            name_drift_result=drift_result,
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
            name_drift_result=drift_result,
        )

    return SuiteCollectionResult(
        named_id=named_id,
        repository=repo,
        status="observed",
        finding=observed,
        enumeration=enumeration,
        complete_inventory=candidate,
        proof_reason=None,
        name_drift_result=drift_result,
    )


def collect_suites(
    suites: Sequence[Mapping[str, Any]],
    authority: Mapping[str, dict[str, Any]],
    *,
    poll_id: str,
    verbose: bool = False,
    upstream_client: HostedUpstreamClient | None = None,
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

        res = collect_suite_observation(
            fm,
            authority,
            poll_id=validated_poll_id,
            verbose=verbose,
            upstream_client=upstream_client,
        )
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
