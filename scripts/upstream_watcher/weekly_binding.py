"""Offline read-only canonical repository plan binding for P2 weekly observations (Slice 4A).

Binds genuine committed ``weekly_journal.JournalCommitResult`` + ``weekly_reducer.PollInput``
outputs to real current P1 canonical repository plans (``repository_batch.group_findings``,
``read_repository_live``, ``inspect_history``, ``plan_repository``, and ``envelope``) over
read-only transports only.

Contract
--------
* Zero effects: never invokes mutating GitHub methods, never settles journal buckets, and
  always returns ``write_authorized=False`` and ``write_readiness=False``.
* Local checkpoint lineage: re-reads the local ``named-v3`` journal via ``load_journal``
  and requires exact local ``JournalPin``, ``persisted=True``, ``status="applied"``
  (refusing ``replayed``/``rejected``), ``poll.complete=True``, exact ``poll_id``/UTC
  ``observed_at``, and exact ``PollReceipt.input_digest``. Local pin comparison is NOT a
  claim about shared cache freshness or a cryptographic attestation against an in-process caller.
* Exact per-scope provenance: selects ONLY validated eligible ``(repository, named_id)``
  decisions matching the live journal bucket, current raw ``observed_findings``, canonical
  ``planned_findings``, and per-row ``FirstSeenPin``s.
* Real planner reproduction: re-runs ``plan_repository`` on ONLY the selected eligible raw
  subset. Every selected sealed named finding must be reproduced once with identical structure
  and ``payloadSha256``; drift declines fail-closed without re-sealing.
* Strict target & sibling rules:
  - Updates bind ONLY the lowest exact OPEN non-PR ``upstream:release`` umbrella, re-verified
    via read-only ``gh.get_issue`` against ``batch.snapshot_of``, preserving untouched existing
    siblings byte-for-byte.
  - Creates require complete issue/PR inventory, unambiguous absence of any eligible open
    umbrella (closed issues and PRs excluded), and decline if P1 carry-forward would publish
    unselected siblings.
  - Legacy holds (#1833 ``preserve-legacy-reference``) remain ``held``; ``noop`` and
    ``suppressed-processed`` are distinguished from ``candidate-intent``; records-comment
    layout is conservatively declined; bad repositories fail isolated while unrelated good
    repositories remain usable unless global inventory is incomplete.

Next-Slice Seam (Not Implemented Here)
--------------------------------------
The next slice (writer + post-effect settlement) consumes ``RepositoryBinding`` with
``status == "candidate-intent"`` and must add:
1. **Revision-checked durable intent**: atomically persist an intent CAS-checked against
   ``binding.journal_pin`` carrying ``(poll_id, repository, selected_members[(named_id,
   bucket_revision, finding_sha256)], target(action, umbrella, title, snapshot),
   envelope_sha256)`` before any GitHub write.
2. **Fresh complete readback for post-effect recovery & settlement**: after a write or crash,
   perform a fresh complete GitHub readback (verified listing + ``get_issue`` + ``envelope.read``)
   proving every selected member's exact ``finding_sha256`` and preserved sibling digests landed
   before settling the journal bucket.

Tricky cases for the next slice:
* Create succeeded, checkpoint failed: discover the lowest exact open umbrella on fresh
  readback and verify member digests instead of creating a duplicate umbrella.
* Edit succeeded, checkpoint failed: distinguish "our exact envelope landed" from a concurrent
  external edit after the snapshot advanced.
* Mid-flight umbrella closure: abort via ``ClosureGuard`` / fresh ``get_issue`` and re-bind
  without editing a closed issue.
* Records-mode two-phase partial failure: inspect comment generations and never settle on a
  placeholder body.
* Partial multi-repo batch: settle per-repository / per-named-scope so one failure does not
  lose another pending bucket.
* Approval-label reset: reset ``upstream:approved`` before body edit without conferring
  approval on any sibling.
"""

from __future__ import annotations

import copy
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from scripts.upstream_watcher import (
    batch,
    envelope,
    prechecks,
    records,
    repository_batch,
    weekly_collector,
    weekly_reducer,
)
from scripts.upstream_watcher.approval import PayloadError, canonical_hash, extract_payload
from scripts.upstream_watcher.live import GhError, mentions_suite, umbrella_suite
from scripts.upstream_watcher.releaseidentity import validateReleaseSource
from scripts.upstream_watcher.weekly_collector import (
    _exact_structural_equal,
    _index_unique_observations,
)
from scripts.upstream_watcher.weekly_journal import (
    BLOCKED_STATUSES,
    DEFAULT_MAX_JOURNAL_BYTES,
    STATUS_OK,
    USABLE_STATUSES,
    JournalCommitResult,
    JournalPin,
    load_journal,
)
from scripts.upstream_watcher.weekly_reducer import (
    DECISION_FLUSH,
    DECISION_URGENT,
    FirstSeenPin,
    NamedBucket,
    NamedDecision,
    PollInput,
    ReducerConfig,
    ReducerState,
    _canonical_json_digest,
    _freeze_mapping,
    format_utc,
    parse_strict_utc,
)

BINDING_SCHEMA_VERSION = 1

RUN_STATUS_BOUND = "bound"
RUN_STATUS_IDLE = "idle"
RUN_STATUS_REFUSED = "refused"

STATUS_CANDIDATE_INTENT = "candidate-intent"
STATUS_NOOP = "noop"
STATUS_SUPPRESSED = "suppressed-processed"
STATUS_HELD = "held"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_INCOMPLETE = "incomplete"
STATUS_DECLINED = "declined"

_ELIGIBLE_DECISIONS = frozenset({DECISION_FLUSH, DECISION_URGENT})


# ---------------------------------------------------------------------------
# Public immutable binding types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundNamedMember:
    """One verified eligible named finding bound to a current poll and journal bucket."""

    repository: str
    named_id: str
    decision: str
    reasons: tuple[str, ...]
    poll_id: str
    observed_at: str
    bucket_revision: int
    source_url: str
    new_version: str
    finding_sha256: str
    finding: dict[str, Any]
    row_pins: Mapping[str, FirstSeenPin]

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding", copy.deepcopy(self.finding))
        object.__setattr__(self, "row_pins", _freeze_mapping(self.row_pins))


@dataclass(frozen=True)
class TargetBinding:
    """Verified read-only repository target binding for a create, update, or noop."""

    action: str  # "create" | "update" | "noop"
    umbrella: int | None
    title: str
    snapshot: Mapping[str, str] | None
    duplicates: tuple[dict[str, Any], ...]
    preserved_siblings: Mapping[str, str]
    inventory_proof: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot", _freeze_mapping(self.snapshot) if self.snapshot is not None else None)
        object.__setattr__(self, "duplicates", tuple(copy.deepcopy(d) for d in self.duplicates))
        object.__setattr__(self, "preserved_siblings", _freeze_mapping(self.preserved_siblings))
        object.__setattr__(self, "inventory_proof", _freeze_mapping(copy.deepcopy(dict(self.inventory_proof))))


@dataclass(frozen=True)
class RepositoryBinding:
    """Read-only per-repository binding outcome. Never grants write readiness or approval."""

    repository: str
    status: str
    reason: str | None
    poll_id: str
    observed_at: str
    journal_pin: JournalPin
    selected_members: tuple[BoundNamedMember, ...]
    declined_scopes: Mapping[str, str]
    target: TargetBinding | None = None
    envelope_payload: dict[str, Any] | None = None
    envelope_sha256: str | None = None
    envelope_body: str | None = None
    known_legacy_holds: tuple[dict[str, Any], ...] = ()
    write_authorized: bool = False
    write_readiness: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "declined_scopes", _freeze_mapping(self.declined_scopes))
        object.__setattr__(
            self,
            "envelope_payload",
            copy.deepcopy(self.envelope_payload) if self.envelope_payload is not None else None,
        )
        object.__setattr__(self, "known_legacy_holds", tuple(copy.deepcopy(h) for h in self.known_legacy_holds))
        object.__setattr__(self, "write_authorized", False)
        object.__setattr__(self, "write_readiness", False)

    @property
    def is_candidate_intent(self) -> bool:
        return self.status == STATUS_CANDIDATE_INTENT


@dataclass(frozen=True)
class WeeklyBindingResult:
    """Top-level read-only binding result for one committed weekly poll."""

    status: str  # "bound" | "idle" | "refused"
    refusal_reason: str | None
    poll_id: str | None
    observed_at: str | None
    journal_pin: JournalPin | None
    repositories: Mapping[str, RepositoryBinding]
    candidate_intents: tuple[RepositoryBinding, ...]
    non_eligible_scopes: Mapping[tuple[str, str], str]
    schema_version: int = BINDING_SCHEMA_VERSION
    write_authorized: bool = False
    write_readiness: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "repositories", _freeze_mapping(self.repositories))
        object.__setattr__(self, "non_eligible_scopes", _freeze_mapping(self.non_eligible_scopes))
        object.__setattr__(self, "write_authorized", False)
        object.__setattr__(self, "write_readiness", False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _refused(
    reason: str,
    *,
    poll_id: str | None = None,
    observed_at: str | None = None,
    journal_pin: JournalPin | None = None,
    non_eligible_scopes: Mapping[tuple[str, str], str] | None = None,
) -> WeeklyBindingResult:
    return WeeklyBindingResult(
        status=RUN_STATUS_REFUSED,
        refusal_reason=reason,
        poll_id=poll_id,
        observed_at=observed_at,
        journal_pin=journal_pin,
        repositories={},
        candidate_intents=(),
        non_eligible_scopes=non_eligible_scopes or {},
    )


def _poll_input_digest(poll: PollInput, poll_id: str, observed_at_iso: str) -> str:
    held_repos, held_named_ids, unavailable_named_ids = weekly_reducer._normalize_scope_sets(poll)
    return _canonical_json_digest(
        {
            "poll_id": poll_id,
            "observed_at": observed_at_iso,
            "complete": poll.complete,
            "held_repos": sorted(held_repos),
            "held_named_ids": sorted(held_named_ids),
            "unavailable_named_ids": sorted(unavailable_named_ids),
            "observed_findings": list(poll.observed_findings),
            "planned_findings": list(poll.planned_findings),
            "complete_inventories": weekly_reducer._serialize_complete_inventories(poll.complete_inventories),
        }
    )


class _InventoryValidationError(RuntimeError):
    """Sanitized fixed-code inventory validation failure (never carries untrusted payload text)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _is_valid_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parse_strict_utc(value)
    except ValueError:
        return False
    return True


def _is_valid_snapshot(snapshot: Any) -> bool:
    if not isinstance(snapshot, dict) or set(snapshot.keys()) != {"updatedAt", "bodySha256"}:
        return False
    updated_at, body_sha = snapshot.get("updatedAt"), snapshot.get("bodySha256")
    return (
        _is_valid_utc_timestamp(updated_at)
        and isinstance(body_sha, str)
        and bool(envelope.SHA.fullmatch(body_sha))
    )


def _normalize_issue_labels(raw_labels: Any) -> tuple[list[dict[str, Any]], set[str]] | None:
    """Validate and normalize genuine issue label shapes without coercing invalid values."""
    if not isinstance(raw_labels, list):
        return None
    normalized: list[dict[str, Any]] = []
    names: set[str] = set()
    for entry in raw_labels:
        if isinstance(entry, dict):
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                return None
            normalized.append(dict(entry))
            names.add(name)
        elif isinstance(entry, str) and entry.strip():
            normalized.append({"name": entry})
            names.add(entry)
        else:
            return None
    return normalized, names


def _validated_label_names(issue: Mapping[str, Any]) -> set[str] | None:
    if "labels" not in issue:
        return None
    parsed = _normalize_issue_labels(issue["labels"])
    return parsed[1] if parsed is not None else None


def _safe_authority_repo(identifier: Any, authority: Mapping[str, dict[str, Any]]) -> str | None:
    if not isinstance(identifier, str) or identifier not in authority:
        return None
    try:
        return envelope.authority_repository(identifier, authority)
    except PayloadError:
        return None


def _validate_watcher_row_evidence(
    row: Mapping[str, Any],
    label_names: set[str],
    authority: Mapping[str, dict[str, Any]],
) -> None:
    """Require usable, authoritatively attributable evidence on watcher-labelled history rows.

    A parseable title is only a claim, not authoritative attribution: an opaque or
    unattributable ``upstream:release`` / ``upstream:bootstrap`` / active ``upstream:child``
    record must fail closed globally rather than allowing unrelated create/update proofs on
    incomplete shared inventory.
    """
    body = row.get("body")
    title = row["title"]
    updated_at = row.get("updated_at")

    if "upstream:release" in label_names:
        if not isinstance(body, str) or not _is_valid_utc_timestamp(updated_at):
            raise _InventoryValidationError("opaque-release-history")
        try:
            payload, _ = extract_payload(body)
        except PayloadError:
            raise _InventoryValidationError("opaque-release-history") from None
        if envelope.is_envelope(payload):
            try:
                env_repo = envelope.repository(payload.get("repository"))
            except PayloadError:
                raise _InventoryValidationError("unattributable-release-envelope") from None
            findings = payload.get("findings")
            if not isinstance(findings, list) or not 1 <= len(findings) <= envelope.MAX_FINDINGS:
                raise _InventoryValidationError("unattributable-release-envelope")
            any_auth_match = False
            for entry in findings:
                if not isinstance(entry, dict):
                    raise _InventoryValidationError("unattributable-release-envelope")
                sid = entry.get("skillId")
                if not isinstance(sid, str) or not envelope.IDENTIFIER.fullmatch(sid):
                    raise _InventoryValidationError("unattributable-release-envelope")
                try:
                    entry_repo = envelope.release_repository(entry.get("sourceUrl"), entry.get("newVersion"))
                except PayloadError:
                    raise _InventoryValidationError("unattributable-release-envelope") from None
                if entry_repo != env_repo:
                    raise _InventoryValidationError("unattributable-release-envelope")
                if _safe_authority_repo(sid, authority) == env_repo:
                    any_auth_match = True
            title_repo = umbrella_suite(title)
            if title_repo is None and not any_auth_match:
                raise _InventoryValidationError("unattributable-release-envelope")
        else:
            sid = payload.get("skillId")
            if not isinstance(sid, str) or not envelope.IDENTIFIER.fullmatch(sid):
                raise _InventoryValidationError("unattributable-legacy-release")
            try:
                rel_repo = envelope.release_repository(payload.get("sourceUrl"), payload.get("newVersion"))
            except PayloadError:
                raise _InventoryValidationError("unattributable-legacy-release") from None
            title_repo = umbrella_suite(title)
            auth_repo = _safe_authority_repo(sid, authority)
            if title_repo is None and auth_repo is None:
                raise _InventoryValidationError("unattributable-legacy-release")
            if title_repo is not None and title_repo != rel_repo and auth_repo != rel_repo:
                raise _InventoryValidationError("unattributable-legacy-release")

    if "upstream:bootstrap" in label_names and "upstream:release" not in label_names:
        if not isinstance(body, str) or not _is_valid_utc_timestamp(updated_at):
            raise _InventoryValidationError("opaque-bootstrap-history")
        try:
            payload, _ = extract_payload(body)
        except PayloadError:
            raise _InventoryValidationError("opaque-bootstrap-history") from None
        sid = payload.get("skillId")
        if not isinstance(sid, str) or not envelope.IDENTIFIER.fullmatch(sid):
            raise _InventoryValidationError("unattributable-bootstrap-history")
        try:
            envelope.release_repository(payload.get("sourceUrl"), payload.get("newVersion"))
        except PayloadError:
            raise _InventoryValidationError("unattributable-bootstrap-history") from None

    if "upstream:child" in label_names and (row["state"] == "open" or "upstream:rejected" in label_names):
        if not isinstance(body, str) or not prechecks.suggested_id_of(body):
            raise _InventoryValidationError("opaque-child-history")


def _validate_live_inventory(
    live: Any,
    authority: Mapping[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(live, dict) or not isinstance(live.get("issues"), list) or not isinstance(live.get("closedUmbrellas"), list):
        raise _InventoryValidationError("missing-inventory-lists")
    validated: dict[str, list[dict[str, Any]]] = {"issues": [], "closedUmbrellas": []}
    by_list_num: dict[str, dict[int, tuple[dict[str, Any], set[str]]]] = {"issues": {}, "closedUmbrellas": {}}
    for list_name in ("issues", "closedUmbrellas"):
        seen: set[int] = set()
        for row in live[list_name]:
            if not isinstance(row, dict):
                raise _InventoryValidationError("malformed-inventory-row")
            if "pull_request" in row:
                raise _InventoryValidationError("pull-request-marker-present")
            num = row.get("number")
            state = row.get("state")
            valid_state = state == "closed" if list_name == "closedUmbrellas" else state in ("open", "closed")
            if type(num) is not int or num <= 0 or num in seen or not valid_state:
                raise _InventoryValidationError("invalid-issue-identity-or-state")
            if "labels" not in row:
                raise _InventoryValidationError("missing-issue-labels")
            parsed_labels = _normalize_issue_labels(row["labels"])
            if parsed_labels is None:
                raise _InventoryValidationError("malformed-issue-labels")
            norm_labels, label_names = parsed_labels
            if list_name == "closedUmbrellas" and "upstream:release" not in label_names:
                raise _InventoryValidationError("closed-umbrella-missing-release-label")
            if not isinstance(row.get("title"), str):
                raise _InventoryValidationError("non-string-issue-title")
            body = row.get("body")
            if body is not None and not isinstance(body, str):
                raise _InventoryValidationError("non-string-issue-body")
            updated_at = row.get("updated_at")
            if updated_at is not None and not _is_valid_utc_timestamp(updated_at):
                raise _InventoryValidationError("invalid-issue-updated-at")
            normalized_row = {**row, "labels": norm_labels}
            seen.add(num)
            validated[list_name].append(normalized_row)
            by_list_num[list_name][num] = (normalized_row, label_names)

    issues_index = by_list_num["issues"]
    closed_index = by_list_num["closedUmbrellas"]
    for num, (issue_row, issue_labels) in issues_index.items():
        if issue_row["state"] == "closed" and "upstream:release" in issue_labels and num not in closed_index:
            raise _InventoryValidationError("closed-release-missing-from-closed-umbrellas")
        if num in closed_index:
            closed_row, closed_labels = closed_index[num]
            if (
                issue_row["state"] != closed_row["state"]
                or issue_row["title"] != closed_row["title"]
                or issue_row.get("body") != closed_row.get("body")
                or issue_row.get("updated_at") != closed_row.get("updated_at")
                or issue_labels != closed_labels
            ):
                raise _InventoryValidationError("contradictory-issue-across-lists")

    checked: set[int] = set()
    for index_map in (issues_index, closed_index):
        for num, (norm_row, label_names) in index_map.items():
            if num in checked:
                continue
            checked.add(num)
            _validate_watcher_row_evidence(norm_row, label_names, authority)

    return validated


def _verify_eligible_member(
    dec: NamedDecision,
    *,
    poll_id: str,
    observed_at_iso: str,
    live_state: ReducerState,
    accepted_scopes: frozenset[tuple[str, str]],
    decisions_map: Mapping[tuple[str, str], NamedDecision],
    held_repos: frozenset[str],
    held_named_ids: frozenset[str],
    unavailable_named_ids: frozenset[str],
    raw_by_scope: Mapping[tuple[str, str], dict[str, Any]],
    duplicate_raw_scopes: set[tuple[str, str]],
    planned_by_scope: Mapping[tuple[str, str], dict[str, Any]],
    duplicate_planned_scopes: set[tuple[str, str]],
    authority: Mapping[str, dict[str, Any]],
) -> tuple[BoundNamedMember | None, dict[str, Any] | None, str | None]:
    if not isinstance(dec, NamedDecision):
        return None, None, "eligible-entry-not-named-decision"
    try:
        repo = envelope.repository(dec.repository)
    except PayloadError:
        return None, None, "invalid-decision-repository"
    if repo != dec.repository:
        return None, None, "decision-repository-not-normalized"
    named_id = dec.named_id
    scope = (repo, named_id)

    if not dec.eligible or dec.decision not in _ELIGIBLE_DECISIONS or dec.write_authorized is not False:
        return None, None, "decision-not-validly-eligible"
    if dec.poll_id != poll_id or dec.observed_at != observed_at_iso:
        return None, None, "decision-poll-identity-mismatch"
    if repo in held_repos or named_id in held_named_ids or named_id in unavailable_named_ids:
        return None, None, "scope-held-or-unavailable"
    if scope not in accepted_scopes or decisions_map.get(scope) != dec:
        return None, None, "decision-disagrees-with-accepted-reduction"

    bucket: NamedBucket | None = live_state.buckets.get(scope)
    if (
        bucket is None
        or bucket.repository != repo
        or bucket.named_id != named_id
        or bucket.last_poll_id != poll_id
        or bucket.last_observed_at != observed_at_iso
        or type(dec.bucket_revision) is not int
        or bucket.revision != dec.bucket_revision
        or not isinstance(dec.finding_sha256, str)
        or not envelope.SHA.fullmatch(dec.finding_sha256)
        or bucket.latest_finding_sha256 != dec.finding_sha256
        or not isinstance(dec.finding, dict)
        or not _exact_structural_equal(dec.finding, bucket.latest_finding)
    ):
        return None, None, "decision-disagrees-with-live-journal-bucket"

    try:
        if envelope.authority_repository(named_id, authority) != repo:
            return None, None, "named-id-disagrees-with-release-authority"
        envelope.validate_named(dec.finding, repo, authority, digest=True, mutation_scope=True)
        validateReleaseSource(dec.finding)
    except (PayloadError, GhError):
        return None, None, "canonical-finding-authority-validation-failed"

    if dec.finding.get("payloadSha256") != dec.finding_sha256 or canonical_hash(dec.finding) != dec.finding_sha256:
        return None, None, "canonical-finding-digest-mismatch"

    for row in dec.finding.get("candidates", []):
        row_id = row["id"]
        bucket_row = bucket.rows.get(row_id)
        dec_pin = dec.row_pins.get(row_id)
        if (
            bucket_row is None
            or dec_pin is None
            or bucket_row.first_seen_pin != dec_pin
            or row["firstSeenVersion"] != dec_pin.first_seen_version
            or row["evidenceUrl"] != dec_pin.evidence_url
            or not _exact_structural_equal(bucket_row.latest_row, row)
        ):
            return None, None, "candidate-row-pin-or-bucket-mismatch"

    if scope in duplicate_raw_scopes or scope not in raw_by_scope:
        return None, None, "missing-or-duplicate-current-raw-observation"
    try:
        raw_repo, raw_named_id, raw_kind, validated_raw = weekly_reducer._validate_raw_observation(
            raw_by_scope[scope], authority
        )
    except PayloadError:
        return None, None, "current-raw-observation-validation-failed"

    finding_kind = dec.finding.get("findingType") or "update"
    if (
        (raw_repo, raw_named_id) != scope
        or raw_kind != finding_kind
        or validated_raw["newVersion"] != dec.finding["newVersion"]
        or validated_raw["sourceUrl"] != dec.finding["sourceUrl"]
        or validated_raw["releasedAt"] != dec.finding["releasedAt"]
        or validated_raw["mode"] != dec.finding["mode"]
        or set(validated_raw["componentAdds"]) != set(dec.finding["componentAdds"])
    ):
        return None, None, "current raw observation disagrees with validated canonical finding"

    if scope in duplicate_planned_scopes or scope not in planned_by_scope:
        return None, None, "missing or duplicate canonical planned_finding for eligible scope"
    if not _exact_structural_equal(planned_by_scope[scope], dec.finding):
        return None, None, "poll planned_finding disagrees with journal/decision canonical finding"

    member = BoundNamedMember(
        repository=repo,
        named_id=named_id,
        decision=dec.decision,
        reasons=tuple(dec.reasons),
        poll_id=poll_id,
        observed_at=observed_at_iso,
        bucket_revision=bucket.revision,
        source_url=dec.finding["sourceUrl"],
        new_version=dec.finding["newVersion"],
        finding_sha256=dec.finding_sha256,
        finding=dec.finding,
        row_pins={rid: pin for rid, pin in sorted(dec.row_pins.items())},
    )
    return member, validated_raw, None


def _verify_repo_plan(
    repo: str,
    members: list[BoundNamedMember],
    raw_rows: list[dict[str, Any]],
    *,
    poll_id: str,
    observed_at_iso: str,
    journal_pin: JournalPin,
    gh: Any,
    index: dict[str, Any],
    live: dict[str, Any],
    authority: Mapping[str, dict[str, Any]],
    policy: dict[str, Any],
    historical_loader: Any,
) -> RepositoryBinding:
    selected_members = tuple(sorted(members, key=lambda m: m.named_id))
    expected_by_id = {m.named_id: m for m in selected_members}

    def _result(
        status: str,
        reason: str | None = None,
        *,
        declined_scopes: Mapping[str, str] | None = None,
        target: TargetBinding | None = None,
        payload: dict[str, Any] | None = None,
        body: str | None = None,
        holds: tuple[dict[str, Any], ...] = (),
    ) -> RepositoryBinding:
        return RepositoryBinding(
            repository=repo,
            status=status,
            reason=reason,
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=journal_pin,
            selected_members=selected_members,
            declined_scopes=declined_scopes or {},
            target=target,
            envelope_payload=payload,
            envelope_sha256=payload["payloadSha256"] if isinstance(payload, dict) else None,
            envelope_body=body,
            known_legacy_holds=holds,
        )

    def _all_scopes(msg: str) -> dict[str, str]:
        return {m.named_id: msg for m in selected_members}

    try:
        found, holds, stored = repository_batch.inspect_history(repo, live, gh, authority, policy, historical_loader)
    except PayloadError as exc:
        msg_lower = str(exc).lower()
        if "ambiguous" in msg_lower or "malformed claimed" in msg_lower:
            code = "inspect-history-ambiguous"
            st = STATUS_AMBIGUOUS
        else:
            code = "inspect-history-refused"
            st = STATUS_DECLINED
        return _result(st, code, declined_scopes=_all_scopes(code))
    except (GhError, records.RecordError) as exc:
        code = "history-records-incomplete" if isinstance(exc, records.RecordError) else "history-read-incomplete"
        return _result(STATUS_INCOMPLETE, code, declined_scopes=_all_scopes(code))
    except (KeyError, ValueError, TypeError, OSError, subprocess.SubprocessError):
        code = "history-read-malformed"
        return _result(STATUS_INCOMPLETE, code, declined_scopes=_all_scopes(code))

    if found.ambiguous:
        return _result(STATUS_AMBIGUOUS, "ambiguous open repository umbrella title", declined_scopes=_all_scopes("ambiguous title"))

    try:
        plan = repository_batch.plan_repository(
            repo, copy.deepcopy(raw_rows), gh, index, live, authority, policy, historical_loader=historical_loader
        )
    except PayloadError as exc:
        if "ambiguous" in str(exc).lower():
            code = "plan-repository-ambiguous"
            st = STATUS_AMBIGUOUS
        else:
            code = "plan-repository-refused"
            st = STATUS_DECLINED
        return _result(st, code, declined_scopes=_all_scopes(code))
    except (GhError, records.RecordError) as exc:
        code = "plan-repository-records-incomplete" if isinstance(exc, records.RecordError) else "plan-repository-incomplete"
        return _result(STATUS_INCOMPLETE, code, declined_scopes=_all_scopes(code))
    except (KeyError, ValueError, TypeError, OSError, subprocess.SubprocessError):
        code = "plan-repository-malformed"
        return _result(STATUS_INCOMPLETE, code, declined_scopes=_all_scopes(code))

    if plan.get("knownLegacyHolds") or not plan.get("writeReadiness"):
        return _result(STATUS_HELD, "legacy-migration-hold", holds=tuple(plan.get("knownLegacyHolds") or holds))

    action = plan.get("action")
    if action == "suppressed-processed":
        return _result(STATUS_SUPPRESSED, "already-covered-by-closed-history")
    if action not in ("create", "update", "noop"):
        code = "unexpected-planner-action"
        return _result(STATUS_DECLINED, code, declined_scopes=_all_scopes(code))

    if plan.get("records") is not None or (
        plan.get("recordPlan") is not None and (plan["recordPlan"].prewrites or plan["recordPlan"].cleanup)
    ):
        return _result(STATUS_DECLINED, "records-comment-layout-out-of-scope", declined_scopes=_all_scopes("records-mode"))

    planned_payload, planned_body = plan.get("payload"), plan.get("body")
    if not isinstance(planned_payload, dict) or not isinstance(planned_body, str):
        return _result(STATUS_DECLINED, "planner produced missing canonical envelope payload or body", declined_scopes=_all_scopes("missing envelope"))

    try:
        expected_title = envelope.title(planned_payload)
        envelope.validate(planned_payload, authority, title=expected_title)
        if not _exact_structural_equal(envelope.read(planned_body, authority, title_text=expected_title), planned_payload):
            raise PayloadError("rendered envelope body disagrees with canonical payload")
    except PayloadError:
        code = "canonical-envelope-validation-failed"
        return _result(STATUS_DECLINED, code, declined_scopes=_all_scopes(code))

    by_id_counts: dict[str, list[dict[str, Any]]] = {}
    for entry in planned_payload.get("findings", []):
        by_id_counts.setdefault(entry["skillId"], []).append(entry)

    drift_reasons: dict[str, str] = {}
    for named_id, member in expected_by_id.items():
        matches = by_id_counts.get(named_id, [])
        if len(matches) != 1:
            drift_reasons[named_id] = f"selected named finding appeared {len(matches)} times in fresh canonical plan"
        elif matches[0].get("payloadSha256") != member.finding_sha256 or not _exact_structural_equal(matches[0], member.finding):
            drift_reasons[named_id] = "fresh canonical finding drifted from eligible sealed finding"
    if drift_reasons:
        return _result(STATUS_DECLINED, "fresh-plan-drift-from-eligible-finding", declined_scopes=drift_reasons)

    open_issues_count = sum(1 for row in live["issues"] if row.get("state") == "open")
    closed_umbrellas_count = len(live["closedUmbrellas"])
    planned_ids, selected_ids = set(by_id_counts), set(expected_by_id)

    if action == "create":
        if found.canonical is not None or found.duplicates or plan.get("umbrella") is not None:
            return _result(STATUS_DECLINED, "create-target-contradicts-open-umbrella-inventory", declined_scopes=_all_scopes("open umbrella exists"))
        for issue in live["issues"]:
            if issue.get("state") == "open" and "pull_request" not in issue and "upstream:release" in batch.label_names(issue):
                title_text = issue.get("title") or ""
                if umbrella_suite(title_text) == repo or mentions_suite(title_text, repo):
                    return _result(STATUS_AMBIGUOUS, "unambiguous-absence-not-proven-for-create", declined_scopes=_all_scopes("open release issue references repo"))
        extra_siblings = sorted(planned_ids - selected_ids)
        if extra_siblings:
            msg = f"create-would-include-unselected-carried-siblings: {', '.join(extra_siblings)}"
            return _result(STATUS_DECLINED, msg, declined_scopes=_all_scopes(msg))
        target = TargetBinding(
            action="create",
            umbrella=None,
            title=expected_title,
            snapshot=None,
            duplicates=(),
            preserved_siblings={},
            inventory_proof={
                "complete": True,
                "openIssuesScanned": open_issues_count,
                "closedUmbrellasScanned": closed_umbrellas_count,
                "closedAndPrExcluded": True,
                "unambiguousAbsence": True,
            },
        )
        return _result(STATUS_CANDIDATE_INTENT, None, target=target, payload=planned_payload, body=planned_body)

    canonical = found.canonical
    if (
        canonical is None
        or plan.get("umbrella") != canonical.get("number")
        or canonical.get("state") != "open"
        or "pull_request" in canonical
        or "upstream:release" not in batch.label_names(canonical)
        or umbrella_suite(canonical.get("title") or "") != repo
        or any(canonical["number"] >= dup["number"] for dup in found.duplicates)
    ):
        return _result(STATUS_DECLINED, "target-umbrella-is-not-lowest-open-exact-release-issue", declined_scopes=_all_scopes("invalid target umbrella"))

    existing_env = stored.get(canonical["number"])
    if not isinstance(existing_env, dict):
        return _result(STATUS_DECLINED, "existing-open-umbrella-envelope-not-validated", declined_scopes=_all_scopes("existing envelope unverified"))

    planned_snapshot = plan.get("snapshot")
    if not _is_valid_snapshot(planned_snapshot) or planned_snapshot != batch.snapshot_of(canonical):
        return _result(STATUS_INCOMPLETE, "target-snapshot-unverifiable", declined_scopes=_all_scopes("invalid snapshot"))

    try:
        current_issue = gh.get_issue(canonical["number"])
    except GhError:
        code = "target-issue-reread-failed"
        return _result(STATUS_INCOMPLETE, code, declined_scopes=_all_scopes(code))

    current_labels = _validated_label_names(current_issue) if isinstance(current_issue, dict) else None
    if (
        not isinstance(current_issue, dict)
        or type(current_issue.get("number")) is not int
        or current_issue.get("number") != canonical["number"]
        or current_issue.get("state") != "open"
        or "pull_request" in current_issue
        or not isinstance(current_issue.get("title"), str)
        or current_issue.get("title") != canonical.get("title")
        or not isinstance(current_issue.get("body"), str)
        or not _is_valid_utc_timestamp(current_issue.get("updated_at"))
        or current_labels is None
        or "upstream:release" not in current_labels
        or batch.snapshot_of(current_issue) != planned_snapshot
    ):
        return _result(STATUS_DECLINED, "target-snapshot-or-state-drifted-during-binding", declined_scopes=_all_scopes("target snapshot drifted"))

    existing_by_id = {f["skillId"]: f for f in existing_env["findings"]}
    if planned_ids != (set(existing_by_id) | selected_ids):
        return _result(STATUS_DECLINED, "update-envelope-member-set-disagrees-with-existing-plus-selected", declined_scopes=_all_scopes("unexpected member set"))

    preserved_siblings: dict[str, str] = {}
    for sibling_id, existing_sibling in sorted(existing_by_id.items()):
        if sibling_id in selected_ids:
            continue
        planned_sibling = by_id_counts[sibling_id][0]
        if planned_sibling.get("payloadSha256") != existing_sibling.get("payloadSha256") or not _exact_structural_equal(
            planned_sibling, existing_sibling
        ):
            return _result(STATUS_DECLINED, f"untouched-sibling-mutated: {sibling_id}", declined_scopes=_all_scopes(f"sibling mutated: {sibling_id}"))
        preserved_siblings[sibling_id] = existing_sibling["payloadSha256"]

    target = TargetBinding(
        action=action,
        umbrella=canonical["number"],
        title=expected_title,
        snapshot=planned_snapshot,
        duplicates=tuple(plan.get("duplicates") or ()),
        preserved_siblings=preserved_siblings,
        inventory_proof={
            "complete": True,
            "openIssuesScanned": open_issues_count,
            "closedUmbrellasScanned": closed_umbrellas_count,
            "closedAndPrExcluded": True,
            "unambiguousAbsence": False,
        },
    )
    return _result(
        STATUS_NOOP if action == "noop" else STATUS_CANDIDATE_INTENT,
        "canonical-envelope-already-matches-open-umbrella" if action == "noop" else None,
        target=target,
        payload=planned_payload,
        body=planned_body,
    )


# ---------------------------------------------------------------------------
# Main read-only binding entry point
# ---------------------------------------------------------------------------


def bind_weekly_plans(
    commit_result: JournalCommitResult,
    poll: PollInput,
    gh: Any,
    authority: Mapping[str, dict[str, Any]],
    *,
    index_loader=prechecks.load_registry_index,
    policy: dict[str, Any] | None = None,
    historical_loader=repository_batch.historical_authority,
    config: ReducerConfig | None = None,
    trusted_latest_pin: JournalPin | None = None,
    journal_path: str | os.PathLike[str] | None = None,
    max_journal_bytes: int = DEFAULT_MAX_JOURNAL_BYTES,
) -> WeeklyBindingResult:
    """Bind eligible named findings from one committed poll to real P1 canonical repository plans."""
    if not isinstance(commit_result, JournalCommitResult):
        return _refused("commit_result must be a JournalCommitResult")
    if not isinstance(poll, PollInput):
        return _refused("poll must be a PollInput")
    if not isinstance(authority, Mapping) or not authority:
        return _refused("authority must be a non-empty mapping")

    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        return _refused("config must be a ReducerConfig")
    if trusted_latest_pin is not None and not isinstance(trusted_latest_pin, JournalPin):
        return _refused("trusted_latest_pin must be None or a JournalPin")

    handle, reduction = commit_result.handle, commit_result.reduction
    if reduction.replayed or reduction.status == "replayed":
        return _refused("replayed-poll-cannot-bind-new-intent", poll_id=reduction.poll_id, observed_at=reduction.observed_at, journal_pin=handle.pin)
    if reduction.status != "applied":
        red_status = reduction.status if reduction.status in ("applied", "replayed", "rejected") else "unknown"
        return _refused(f"unapplied-reduction-status:{red_status}", poll_id=reduction.poll_id, observed_at=reduction.observed_at, journal_pin=handle.pin)
    if not commit_result.persisted:
        return _refused("unpersisted-journal-commit-cannot-bind", poll_id=reduction.poll_id, observed_at=reduction.observed_at, journal_pin=handle.pin)
    if reduction.write_authorized is not False:
        return _refused("reduction-unexpectedly-claims-write-authorized", poll_id=reduction.poll_id, observed_at=reduction.observed_at, journal_pin=handle.pin)
    if not handle.usable or handle.status != STATUS_OK or handle.pin is None or handle.state is None:
        handle_status = handle.status if handle.status in (USABLE_STATUSES | BLOCKED_STATUSES) else "unknown"
        return _refused(f"unusable-journal-handle:{handle_status}", poll_id=reduction.poll_id, observed_at=reduction.observed_at, journal_pin=handle.pin)

    try:
        poll_id = weekly_reducer._validate_poll_id(poll.poll_id)
        observed_at_iso = format_utc(parse_strict_utc(poll.observed_at))
    except ValueError:
        return _refused("invalid-poll-identity", poll_id=reduction.poll_id, observed_at=reduction.observed_at, journal_pin=handle.pin)
    if type(poll.complete) is not bool or not poll.complete:
        return _refused("incomplete-poll-cannot-bind", poll_id=poll_id, observed_at=observed_at_iso, journal_pin=handle.pin)
    if reduction.poll_id != poll_id or reduction.observed_at != observed_at_iso:
        return _refused("poll-identity-disagrees-with-reduction", poll_id=poll_id, observed_at=observed_at_iso, journal_pin=handle.pin)

    # Re-read local journal checkpoint: load_journal enforces trusted_latest_pin (or handle.pin)
    # against the on-disk checkpoint, and live_handle.pin != handle.pin catches a stale commit
    # even when the caller supplies the newer current trusted_latest_pin.
    target_path = Path(journal_path) if journal_path is not None else handle.path
    effective_pin = trusted_latest_pin if trusted_latest_pin is not None else handle.pin
    live_handle = load_journal(
        target_path,
        authority,
        config=cfg,
        allow_bootstrap=False,
        initialized=True,
        trusted_latest_pin=effective_pin,
        max_bytes=max_journal_bytes,
    )
    if live_handle.blocked or live_handle.state is None or live_handle.pin is None:
        live_status = live_handle.status if live_handle.status in BLOCKED_STATUSES else "unknown"
        return _refused(
            f"local-journal-blocked:{live_status}",
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin or handle.pin,
        )
    if live_handle.pin != handle.pin:
        return _refused(
            "stale-journal-revision-against-local-checkpoint",
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin,
        )
    live_state = live_handle.state
    if (
        live_state.revision != reduction.state.revision
        or live_state.revision != handle.loaded_at_revision
        or live_state.last_poll_id != poll_id
        or live_state.last_observed_at != observed_at_iso
    ):
        return _refused(
            "journal-checkpoint-disagrees-with-committed-poll-state",
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin,
        )

    try:
        expected_input_digest = _poll_input_digest(poll, poll_id, observed_at_iso)
        held_repos, held_named_ids, unavailable_named_ids = weekly_reducer._normalize_scope_sets(poll)
    except (PayloadError, TypeError, ValueError):
        return _refused("poll-input-validation-failed", poll_id=poll_id, observed_at=observed_at_iso, journal_pin=live_handle.pin)

    receipt = live_state.seen_polls.get(poll_id)
    if (
        receipt is None
        or not receipt.complete
        or receipt.observed_at != observed_at_iso
        or receipt.input_digest != expected_input_digest
    ):
        return _refused("poll-input-disagrees-with-committed-poll-receipt", poll_id=poll_id, observed_at=observed_at_iso, journal_pin=live_handle.pin)

    non_eligible_scopes = {scope: dec.decision for scope, dec in sorted(reduction.decisions.items()) if not dec.eligible}
    if not reduction.eligible:
        return WeeklyBindingResult(
            status=RUN_STATUS_IDLE,
            refusal_reason=None,
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin,
            repositories={},
            candidate_intents=(),
            non_eligible_scopes=non_eligible_scopes,
        )

    raw_by_scope, duplicate_raw_scopes = _index_unique_observations(poll.observed_findings, authority)
    planned_by_scope, duplicate_planned_scopes = _index_unique_observations(poll.planned_findings, authority)
    accepted_scopes = frozenset(reduction.accepted_scopes)

    verified_members_by_repo: dict[str, list[BoundNamedMember]] = {}
    verified_raw_by_repo: dict[str, list[dict[str, Any]]] = {}
    provenance_failures_by_repo: dict[str, dict[str, str]] = {}
    seen_eligible: set[tuple[str, str]] = set()

    for dec in reduction.eligible:
        repo_key = dec.repository if isinstance(dec, NamedDecision) and isinstance(dec.repository, str) else "?"
        named_key = dec.named_id if isinstance(dec, NamedDecision) and isinstance(dec.named_id, str) else "?"
        if (repo_key, named_key) in seen_eligible:
            provenance_failures_by_repo.setdefault(repo_key, {})[named_key] = "duplicate eligible decision"
            continue
        seen_eligible.add((repo_key, named_key))
        member, raw_obs, err = _verify_eligible_member(
            dec,
            poll_id=poll_id,
            observed_at_iso=observed_at_iso,
            live_state=live_state,
            accepted_scopes=accepted_scopes,
            decisions_map=reduction.decisions,
            held_repos=held_repos,
            held_named_ids=held_named_ids,
            unavailable_named_ids=unavailable_named_ids,
            raw_by_scope=raw_by_scope,
            duplicate_raw_scopes=duplicate_raw_scopes,
            planned_by_scope=planned_by_scope,
            duplicate_planned_scopes=duplicate_planned_scopes,
            authority=authority,
        )
        if err is not None or member is None or raw_obs is None:
            provenance_failures_by_repo.setdefault(repo_key, {})[named_key] = err or "provenance verification failed"
            continue
        verified_members_by_repo.setdefault(member.repository, []).append(member)
        verified_raw_by_repo.setdefault(member.repository, []).append(raw_obs)

    repo_bindings: dict[str, RepositoryBinding] = {}
    for repo, failures in sorted(provenance_failures_by_repo.items()):
        verified_members = tuple(sorted(verified_members_by_repo.pop(repo, []), key=lambda m: m.named_id))
        verified_raw_by_repo.pop(repo, None)
        repo_bindings[repo] = RepositoryBinding(
            repository=repo,
            status=STATUS_DECLINED,
            reason="eligible-scope-provenance-verification-failed",
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin,
            selected_members=verified_members,
            declined_scopes=failures,
        )

    if not verified_raw_by_repo:
        return WeeklyBindingResult(
            status=RUN_STATUS_BOUND,
            refusal_reason=None,
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin,
            repositories=repo_bindings,
            candidate_intents=(),
            non_eligible_scopes=non_eligible_scopes,
        )

    selected_raw_all = [row for repo in sorted(verified_raw_by_repo) for row in verified_raw_by_repo[repo]]
    stage = "policy"
    try:
        resolved_policy = repository_batch.policy_record() if policy is None else policy
        stage = "group-findings"
        grouped = repository_batch.group_findings(selected_raw_all, authority)
        stage = "registry-index"
        index = index_loader()
        stage = "live-read"
        live = repository_batch.read_repository_live(gh)
        stage = "inventory-validation"
        live = _validate_live_inventory(live, authority)
    except _InventoryValidationError as exc:
        return _refused(
            f"global-inventory-or-setup-incomplete:{exc.code}",
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin,
            non_eligible_scopes=non_eligible_scopes,
        )
    except (
        PayloadError,
        GhError,
        prechecks.RegistryUnreadable,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        subprocess.SubprocessError,
    ):
        return _refused(
            f"global-inventory-or-setup-incomplete:{stage}",
            poll_id=poll_id,
            observed_at=observed_at_iso,
            journal_pin=live_handle.pin,
            non_eligible_scopes=non_eligible_scopes,
        )

    for repo in sorted(grouped):
        repo_bindings[repo] = _verify_repo_plan(
            repo,
            verified_members_by_repo[repo],
            grouped[repo],
            poll_id=poll_id,
            observed_at_iso=observed_at_iso,
            journal_pin=live_handle.pin,
            gh=gh,
            index=index,
            live=live,
            authority=authority,
            policy=resolved_policy,
            historical_loader=historical_loader,
        )

    candidate_intents = tuple(repo_bindings[r] for r in sorted(repo_bindings) if repo_bindings[r].is_candidate_intent)
    return WeeklyBindingResult(
        status=RUN_STATUS_BOUND,
        refusal_reason=None,
        poll_id=poll_id,
        observed_at=observed_at_iso,
        journal_pin=live_handle.pin,
        repositories=repo_bindings,
        candidate_intents=candidate_intents,
        non_eligible_scopes=non_eligible_scopes,
    )
