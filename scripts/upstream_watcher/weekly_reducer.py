"""Pure, exact-scoped offline weekly observation reducer (P2 Slice 1).

Scope
-----
This module implements ONLY pure in-memory observation reduction and per-named
eligibility selection for the independently versioned P2 weekly namespace:

* Scope key: ``(repository, named_id, row_id)`` where ``repository`` is the
  normalized lowercase ``owner/repo``, ``named_id`` is the exact case-sensitive
  canonical ``skillId``, and ``row_id`` is ``<repo>:<slug>``.
* Single authority: the real canonical planner (``repository_batch`` /
  ``envelope``) remains the sole authority for envelope structure, row status,
  and digests. This reducer validates canonical named findings via
  ``envelope.validate_named`` and ``releaseidentity.validateReleaseSource`` and
  carries each verified snapshot unchanged (including ``componentRemoves``,
  ``linkLiveness``, ``nameDrift``, ``candidates``, and ``payloadSha256``).
* Immutable provenance: each ``(repository, named_id, row_id)`` records one
  immutable ``FirstSeenPin`` (first-seen version, pinned release evidence URL,
  first-seen timestamp, and poll ID) that later sightings never overwrite.
* Honest history: a row is marked vanished ONLY when a verified current
  observation for that exact ``(repository, named_id)`` in a complete poll
  omits it. Missing, held, unavailable, rejected, or incomplete observations
  never infer vanishings and never confer eligibility.
* Exact-run eligibility: eligibility (``urgent``, ``flush-day``, or
  ``window-elapsed`` from ``pending_since``) is evaluated per exact named
  bucket ONLY when that bucket was validly observed in the current poll.
* No writes / no settlement / no persistence: this module performs no file I/O,
  no network/GitHub calls, builds or seals no envelopes, models no
  ``EffectProof``, and never authorizes writes (``write_authorized`` is always
  ``False``).
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from scripts.upstream_watcher import envelope
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import GhError
from scripts.upstream_watcher.releaseidentity import validateReleaseSource

SCHEMA_VERSION = 1
DEFAULT_FLUSH_WEEKDAY = 0  # Monday (UTC)
DEFAULT_WINDOW_DAYS = 7
URGENT_HTTP_STATUSES = frozenset({404, 410})

DECISION_HOLD = "hold"
DECISION_FLUSH = "flush"
DECISION_URGENT = "urgent"
DECISION_ABSENT = "absent"
DECISION_HELD_SCOPE = "held-scope"
DECISION_UNAVAILABLE = "unavailable"
DECISION_REJECTED = "rejected"
DECISION_REPLAYED = "replayed"


# ---------------------------------------------------------------------------
# Strict time and identifier helpers
# ---------------------------------------------------------------------------


def parse_strict_utc(value: dt.datetime | str) -> dt.datetime:
    """Parse an aware UTC/offset datetime or ISO-8601 string. Rejects naive/malformed values."""
    if isinstance(value, dt.datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at datetime must be timezone-aware")
        return value.astimezone(dt.timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text or any(ord(c) < 32 or ord(c) == 127 for c in text):
            raise ValueError("observed_at string is empty or contains control characters")
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = dt.datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"invalid ISO-8601 observed_at: {value!r}") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("observed_at string must include explicit UTC or offset timezone")
        return parsed.astimezone(dt.timezone.utc)
    raise ValueError("observed_at must be a timezone-aware datetime or ISO-8601 string")


def format_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_poll_id(poll_id: Any) -> str:
    if (
        not isinstance(poll_id, str)
        or not poll_id
        or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in poll_id)
    ):
        raise ValueError("poll_id must be a non-empty string without whitespace or control characters")
    return poll_id


def _canonical_json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Configuration & immutable state model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReducerConfig:
    """Pure review-window configuration (UTC)."""

    flush_weekday: int = DEFAULT_FLUSH_WEEKDAY
    window_days: int = DEFAULT_WINDOW_DAYS

    def __post_init__(self) -> None:
        if type(self.flush_weekday) is not int or not 0 <= self.flush_weekday <= 6:
            raise ValueError("flush_weekday must be an integer in 0..6 (Monday..Sunday UTC)")
        if type(self.window_days) is not int or self.window_days < 1:
            raise ValueError("window_days must be a positive integer")


def is_flush_day(observed_at: dt.datetime, config: ReducerConfig) -> bool:
    return observed_at.astimezone(dt.timezone.utc).weekday() == config.flush_weekday


def next_flush_date(observed_at: dt.datetime, config: ReducerConfig) -> str:
    today = observed_at.astimezone(dt.timezone.utc).date()
    ahead = (config.flush_weekday - today.weekday()) % 7
    return (today + dt.timedelta(days=ahead)).isoformat()


@dataclass(frozen=True)
class FirstSeenPin:
    """Immutable authoritative provenance tuple for one scoped candidate row."""

    first_seen_version: str
    evidence_url: str
    first_seen_at: str
    first_seen_poll_id: str


@dataclass(frozen=True)
class RowHistory:
    """Exact-scoped history for one candidate row under ``(repository, named_id)``."""

    row_id: str
    slug: str
    suggested_id: str
    first_seen_pin: FirstSeenPin
    last_seen_version: str
    last_seen_at: str
    last_seen_poll_id: str
    present_in_latest: bool
    vanished_at: str | None
    vanished_poll_id: str | None
    latest_row: dict[str, Any]


@dataclass(frozen=True)
class VersionSighting:
    """Observed release sighting within one pending named bucket."""

    version: str
    source_url: str
    released_at: str
    finding_sha256: str
    first_observed_at: str
    last_observed_at: str
    first_poll_id: str
    last_poll_id: str


@dataclass(frozen=True)
class NamedBucket:
    """Pending observation state for one exact ``(repository, named_id)`` scope."""

    repository: str
    named_id: str
    pending_since: str
    first_poll_id: str
    last_observed_at: str
    last_poll_id: str
    sighting_count: int
    revision: int
    latest_finding: dict[str, Any]
    latest_finding_sha256: str
    versions_seen: tuple[VersionSighting, ...]
    rows: Mapping[str, RowHistory]

    @property
    def present_row_ids(self) -> tuple[str, ...]:
        return tuple(sorted(rid for rid, row in self.rows.items() if row.present_in_latest))

    @property
    def vanished_row_ids(self) -> tuple[str, ...]:
        return tuple(sorted(rid for rid, row in self.rows.items() if not row.present_in_latest))


@dataclass(frozen=True)
class PollReceipt:
    """Per-poll identity receipt used only to detect exact replay vs conflicting poll IDs."""

    poll_id: str
    observed_at: str
    complete: bool
    input_digest: str


@dataclass(frozen=True)
class ReducerState:
    """Pure in-memory reducer state for the independently versioned P2 weekly namespace."""

    schema_version: int = SCHEMA_VERSION
    revision: int = 0
    last_observed_at: str | None = None
    last_poll_id: str | None = None
    buckets: Mapping[tuple[str, str], NamedBucket] = field(default_factory=dict)
    seen_polls: Mapping[str, PollReceipt] = field(default_factory=dict)

    def get_bucket(self, repo: str, named_id: str) -> NamedBucket | None:
        return self.buckets.get((envelope.repository(repo), named_id))

    def repo_buckets(self, repo: str) -> dict[str, NamedBucket]:
        normalized = envelope.repository(repo)
        return {
            named_id: bucket
            for (bucket_repo, named_id), bucket in sorted(self.buckets.items())
            if bucket_repo == normalized
        }


def empty_state() -> ReducerState:
    return ReducerState()


# ---------------------------------------------------------------------------
# Poll input & reduction output types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PollInput:
    """One offline poll snapshot supplied to ``reduce_poll``."""

    poll_id: str
    observed_at: dt.datetime | str
    findings: Sequence[dict[str, Any]]
    complete: bool = True
    held_repos: frozenset[str] = frozenset()
    held_named_ids: frozenset[str] = frozenset()
    unavailable_named_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RejectedObservation:
    """A malformed, unverified, mis-scoped, or conflicting observation rejected fail-closed."""

    index: int
    named_id: str | None
    repository: str | None
    reason: str


@dataclass(frozen=True)
class NamedDecision:
    """Per-named reduction and eligibility decision for one poll.

    ``write_authorized`` is ALWAYS ``False``: this reducer never grants write
    permission and never assembles or settles an envelope.
    """

    repository: str
    named_id: str
    decision: str
    eligible: bool
    write_authorized: bool
    reasons: tuple[str, ...]
    poll_id: str
    observed_at: str
    pending_since: str | None
    next_flush: str | None
    max_hold_until: str | None
    bucket_revision: int | None
    finding_sha256: str | None
    finding: dict[str, Any] | None
    row_pins: Mapping[str, FirstSeenPin]
    present_row_ids: tuple[str, ...]
    vanished_row_ids: tuple[str, ...]


@dataclass(frozen=True)
class PollReductionResult:
    """Result of one pure ``reduce_poll`` step."""

    status: str  # "applied" | "replayed" | "rejected"
    state: ReducerState
    poll_id: str | None
    observed_at: str | None
    replayed: bool
    rejection_reason: str | None
    accepted_scopes: tuple[tuple[str, str], ...]
    rejected_observations: tuple[RejectedObservation, ...]
    decisions: Mapping[tuple[str, str], NamedDecision]
    eligible: tuple[NamedDecision, ...]
    write_authorized: bool = False


# ---------------------------------------------------------------------------
# Validation & urgency helpers
# ---------------------------------------------------------------------------


def urgent_reasons(finding: Mapping[str, Any]) -> tuple[str, ...]:
    """Return sorted urgent reasons: strictly HTTP 404 or 410 on a tracked component."""
    reasons: set[str] = set()
    liveness = finding.get("linkLiveness") or []
    if not isinstance(liveness, list):
        return ()
    for row in liveness:
        if not isinstance(row, dict):
            continue
        status = row.get("status")
        if type(status) is int and status in URGENT_HTTP_STATUSES:
            reasons.add(f"dead-link:{row.get('skillId', '?')}:{status}")
    return tuple(sorted(reasons))


def _validate_evidence_lists(finding: dict[str, Any]) -> None:
    """Strict shape checks for linkLiveness and nameDrift beyond envelope.validate_named."""
    for entry in finding.get("linkLiveness", []):
        if not isinstance(entry, dict):
            raise PayloadError("malformed linkLiveness entry")
        skill_id = entry.get("skillId")
        url = entry.get("url")
        status = entry.get("status")
        if not isinstance(skill_id, str) or not skill_id or not isinstance(url, str) or not url:
            raise PayloadError("malformed linkLiveness entry fields")
        valid_status = (
            status == "network_error"
            or (type(status) is int and 100 <= status <= 599)
        )
        if not valid_status:
            raise PayloadError("malformed linkLiveness status")

    for entry in finding.get("nameDrift", []):
        if not isinstance(entry, dict):
            raise PayloadError("malformed nameDrift entry")
        skill_id = entry.get("skillId")
        if not isinstance(skill_id, str) or not skill_id:
            raise PayloadError("malformed nameDrift entry fields")


def _validate_finding_observation(
    raw_finding: Any,
    authority: Mapping[str, dict[str, Any]],
) -> tuple[str, str, dict[str, Any]]:
    """Validate one canonical named finding observation via the repo's real authority rules.

    Returns ``(repo, named_id, deep_copied_finding)`` or raises ``PayloadError``.
    """
    if not isinstance(raw_finding, dict):
        raise PayloadError("observation is not a JSON object")
    try:
        json.dumps(raw_finding, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PayloadError(f"observation is not strict JSON: {exc}") from exc

    named_id = raw_finding.get("skillId")
    repo = envelope.authority_repository(named_id, authority)
    try:
        validateReleaseSource(raw_finding)
    except GhError as exc:
        raise PayloadError(str(exc)) from exc

    envelope.validate_named(raw_finding, repo, authority, digest=True, mutation_scope=True)
    _validate_evidence_lists(raw_finding)
    return repo, named_id, copy.deepcopy(raw_finding)


def _best_effort_scope(
    raw_finding: Any,
    authority: Mapping[str, dict[str, Any]],
) -> tuple[str | None, str | None]:
    """Extract (repo, named_id) for rejection attribution without raising."""
    if not isinstance(raw_finding, dict):
        return None, None
    named_id = raw_finding.get("skillId")
    if not isinstance(named_id, str) or not named_id:
        return None, None
    try:
        repo = envelope.authority_repository(named_id, authority)
    except PayloadError:
        repo = None
    return repo, named_id


def _normalize_scope_sets(
    poll: PollInput,
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    held_repos: set[str] = set()
    for repo in poll.held_repos:
        held_repos.add(envelope.repository(repo))
    for named_id in poll.held_named_ids:
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise PayloadError(f"invalid held_named_ids entry: {named_id!r}")
    for named_id in poll.unavailable_named_ids:
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise PayloadError(f"invalid unavailable_named_ids entry: {named_id!r}")
    return frozenset(held_repos), frozenset(poll.held_named_ids), frozenset(poll.unavailable_named_ids)


# ---------------------------------------------------------------------------
# Pure reducer
# ---------------------------------------------------------------------------


def _fold_bucket(
    prior: NamedBucket | None,
    repo: str,
    named_id: str,
    finding: dict[str, Any],
    poll_id: str,
    observed_at_iso: str,
) -> NamedBucket:
    """Fold one verified current observation into its exact ``(repo, named_id)`` bucket."""
    version = finding["newVersion"]
    source_url = finding["sourceUrl"]
    released_at = finding["releasedAt"]
    finding_sha256 = finding["payloadSha256"]

    incoming_by_id = {row["id"]: copy.deepcopy(row) for row in finding["candidates"]}
    next_rows: dict[str, RowHistory] = {}

    if prior is None:
        for row_id, row in sorted(incoming_by_id.items()):
            pin = FirstSeenPin(
                first_seen_version=row["firstSeenVersion"],
                evidence_url=row["evidenceUrl"],
                first_seen_at=observed_at_iso,
                first_seen_poll_id=poll_id,
            )
            next_rows[row_id] = RowHistory(
                row_id=row_id,
                slug=row["slug"],
                suggested_id=row["suggestedId"],
                first_seen_pin=pin,
                last_seen_version=row["lastSeenVersion"],
                last_seen_at=observed_at_iso,
                last_seen_poll_id=poll_id,
                present_in_latest=True,
                vanished_at=None,
                vanished_poll_id=None,
                latest_row=row,
            )
        versions_seen = (
            VersionSighting(
                version=version,
                source_url=source_url,
                released_at=released_at,
                finding_sha256=finding_sha256,
                first_observed_at=observed_at_iso,
                last_observed_at=observed_at_iso,
                first_poll_id=poll_id,
                last_poll_id=poll_id,
            ),
        )
        return NamedBucket(
            repository=repo,
            named_id=named_id,
            pending_since=observed_at_iso,
            first_poll_id=poll_id,
            last_observed_at=observed_at_iso,
            last_poll_id=poll_id,
            sighting_count=1,
            revision=1,
            latest_finding=finding,
            latest_finding_sha256=finding_sha256,
            versions_seen=versions_seen,
            rows=next_rows,
        )

    # Existing bucket: preserve immutable FirstSeenPin for known rows, mark
    # omitted rows as legitimately vanished ONLY because this exact bucket
    # received a verified current observation.
    for row_id, row in sorted(incoming_by_id.items()):
        old_row = prior.rows.get(row_id)
        if old_row is not None:
            pin = old_row.first_seen_pin
        else:
            pin = FirstSeenPin(
                first_seen_version=row["firstSeenVersion"],
                evidence_url=row["evidenceUrl"],
                first_seen_at=observed_at_iso,
                first_seen_poll_id=poll_id,
            )
        next_rows[row_id] = RowHistory(
            row_id=row_id,
            slug=row["slug"],
            suggested_id=row["suggestedId"],
            first_seen_pin=pin,
            last_seen_version=row["lastSeenVersion"],
            last_seen_at=observed_at_iso,
            last_seen_poll_id=poll_id,
            present_in_latest=True,
            vanished_at=None,
            vanished_poll_id=None,
            latest_row=row,
        )

    for row_id, old_row in sorted(prior.rows.items()):
        if row_id in next_rows:
            continue
        next_rows[row_id] = RowHistory(
            row_id=old_row.row_id,
            slug=old_row.slug,
            suggested_id=old_row.suggested_id,
            first_seen_pin=old_row.first_seen_pin,
            last_seen_version=old_row.last_seen_version,
            last_seen_at=old_row.last_seen_at,
            last_seen_poll_id=old_row.last_seen_poll_id,
            present_in_latest=False,
            vanished_at=old_row.vanished_at or observed_at_iso,
            vanished_poll_id=old_row.vanished_poll_id or poll_id,
            latest_row=copy.deepcopy(old_row.latest_row),
        )

    updated_versions: list[VersionSighting] = []
    matched_version = False
    for seen in prior.versions_seen:
        if (
            seen.version == version
            and seen.source_url == source_url
            and seen.finding_sha256 == finding_sha256
        ):
            updated_versions.append(
                VersionSighting(
                    version=seen.version,
                    source_url=seen.source_url,
                    released_at=seen.released_at,
                    finding_sha256=seen.finding_sha256,
                    first_observed_at=seen.first_observed_at,
                    last_observed_at=observed_at_iso,
                    first_poll_id=seen.first_poll_id,
                    last_poll_id=poll_id,
                )
            )
            matched_version = True
        else:
            updated_versions.append(seen)
    if not matched_version:
        updated_versions.append(
            VersionSighting(
                version=version,
                source_url=source_url,
                released_at=released_at,
                finding_sha256=finding_sha256,
                first_observed_at=observed_at_iso,
                last_observed_at=observed_at_iso,
                first_poll_id=poll_id,
                last_poll_id=poll_id,
            )
        )

    return NamedBucket(
        repository=repo,
        named_id=named_id,
        pending_since=prior.pending_since,
        first_poll_id=prior.first_poll_id,
        last_observed_at=observed_at_iso,
        last_poll_id=poll_id,
        sighting_count=prior.sighting_count + 1,
        revision=prior.revision + 1,
        latest_finding=finding,
        latest_finding_sha256=finding_sha256,
        versions_seen=tuple(updated_versions),
        rows=next_rows,
    )


def _decision_for_observed_bucket(
    bucket: NamedBucket,
    poll_id: str,
    observed_at_dt: dt.datetime,
    observed_at_iso: str,
    config: ReducerConfig,
) -> NamedDecision:
    pending_dt = parse_strict_utc(bucket.pending_since)
    deadline_dt = pending_dt + dt.timedelta(days=config.window_days)
    urgent = urgent_reasons(bucket.latest_finding)
    if urgent:
        decision = DECISION_URGENT
        eligible = True
        reasons = urgent
    elif is_flush_day(observed_at_dt, config):
        decision = DECISION_FLUSH
        eligible = True
        reasons = ("flush-day",)
    elif observed_at_dt >= deadline_dt:
        decision = DECISION_FLUSH
        eligible = True
        reasons = ("window-elapsed",)
    else:
        decision = DECISION_HOLD
        eligible = False
        reasons = ("within-review-window",)

    return NamedDecision(
        repository=bucket.repository,
        named_id=bucket.named_id,
        decision=decision,
        eligible=eligible,
        write_authorized=False,
        reasons=reasons,
        poll_id=poll_id,
        observed_at=observed_at_iso,
        pending_since=bucket.pending_since,
        next_flush=next_flush_date(observed_at_dt, config),
        max_hold_until=format_utc(deadline_dt),
        bucket_revision=bucket.revision,
        finding_sha256=bucket.latest_finding_sha256,
        finding=copy.deepcopy(bucket.latest_finding),
        row_pins={rid: row.first_seen_pin for rid, row in sorted(bucket.rows.items())},
        present_row_ids=bucket.present_row_ids,
        vanished_row_ids=bucket.vanished_row_ids,
    )


def _decision_for_unobserved_bucket(
    bucket: NamedBucket,
    decision: str,
    reasons: tuple[str, ...],
    poll_id: str,
    observed_at_dt: dt.datetime,
    observed_at_iso: str,
    config: ReducerConfig,
) -> NamedDecision:
    pending_dt = parse_strict_utc(bucket.pending_since)
    deadline_dt = pending_dt + dt.timedelta(days=config.window_days)
    return NamedDecision(
        repository=bucket.repository,
        named_id=bucket.named_id,
        decision=decision,
        eligible=False,
        write_authorized=False,
        reasons=reasons,
        poll_id=poll_id,
        observed_at=observed_at_iso,
        pending_since=bucket.pending_since,
        next_flush=next_flush_date(observed_at_dt, config),
        max_hold_until=format_utc(deadline_dt),
        bucket_revision=bucket.revision,
        finding_sha256=None,
        finding=None,
        row_pins={rid: row.first_seen_pin for rid, row in sorted(bucket.rows.items())},
        present_row_ids=bucket.present_row_ids,
        vanished_row_ids=bucket.vanished_row_ids,
    )


def _rejected_poll(
    state: ReducerState,
    reason: str,
    *,
    poll_id: str | None = None,
    observed_at: str | None = None,
) -> PollReductionResult:
    return PollReductionResult(
        status="rejected",
        state=state,
        poll_id=poll_id,
        observed_at=observed_at,
        replayed=False,
        rejection_reason=reason,
        accepted_scopes=(),
        rejected_observations=(),
        decisions={},
        eligible=(),
        write_authorized=False,
    )


def reduce_poll(
    state: ReducerState,
    poll: PollInput,
    authority: Mapping[str, dict[str, Any]],
    config: ReducerConfig | None = None,
) -> PollReductionResult:
    """Purely reduce one offline poll snapshot against *state* and *authority*.

    Guarantees:
    * Exact replay of an already-seen ``poll_id`` with identical timestamp and
      inputs is an idempotent no-op (``status="replayed"``, state and revisions
      unchanged, ``eligible=()``).
    * Conflicting reuse of an existing ``poll_id``, stale ``observed_at``, or
      ``complete=False`` fails closed (``status="rejected"``, state unchanged,
      ``eligible=()``).
    * Malformed, tampered, mis-scoped, or conflicting observations are rejected
      per-observation without raising uncaught exceptions and without disturbing
      unrelated repositories or unaffected siblings.
    * Eligibility is evaluated per exact ``(repository, named_id)`` ONLY for
      validly observed, unheld, available buckets from THIS actual poll.
    * ``write_authorized`` is always ``False``.
    """
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(state, ReducerState):
        raise TypeError("state must be a ReducerState")
    if not isinstance(poll, PollInput):
        return _rejected_poll(state, "poll must be a PollInput")
    if not isinstance(authority, Mapping) or not authority:
        return _rejected_poll(state, "registry authority must be a non-empty mapping")

    try:
        poll_id = _validate_poll_id(poll.poll_id)
    except ValueError as exc:
        return _rejected_poll(state, str(exc))

    try:
        observed_at_dt = parse_strict_utc(poll.observed_at)
    except ValueError as exc:
        return _rejected_poll(state, str(exc), poll_id=poll_id)
    observed_at_iso = format_utc(observed_at_dt)

    if type(poll.complete) is not bool:
        return _rejected_poll(state, "poll.complete must be a boolean", poll_id=poll_id, observed_at=observed_at_iso)

    if not isinstance(poll.findings, (list, tuple)):
        return _rejected_poll(
            state, "poll.findings must be a list or tuple", poll_id=poll_id, observed_at=observed_at_iso
        )

    try:
        held_repos, held_named_ids, unavailable_named_ids = _normalize_scope_sets(poll)
    except PayloadError as exc:
        return _rejected_poll(state, str(exc), poll_id=poll_id, observed_at=observed_at_iso)

    # Canonical input digest for exact replay vs conflicting poll_id detection only.
    try:
        input_digest = _canonical_json_digest(
            {
                "poll_id": poll_id,
                "observed_at": observed_at_iso,
                "complete": poll.complete,
                "held_repos": sorted(held_repos),
                "held_named_ids": sorted(held_named_ids),
                "unavailable_named_ids": sorted(unavailable_named_ids),
                "findings": list(poll.findings),
            }
        )
    except (TypeError, ValueError) as exc:
        return _rejected_poll(
            state, f"poll inputs are not strict JSON: {exc}", poll_id=poll_id, observed_at=observed_at_iso
        )

    prior_receipt = state.seen_polls.get(poll_id)
    if prior_receipt is not None:
        if (
            prior_receipt.observed_at == observed_at_iso
            and prior_receipt.complete == poll.complete
            and prior_receipt.input_digest == input_digest
        ):
            replay_decisions = {
                scope: _decision_for_unobserved_bucket(
                    bucket,
                    DECISION_REPLAYED,
                    ("replayed-poll",),
                    poll_id,
                    observed_at_dt,
                    observed_at_iso,
                    cfg,
                )
                for scope, bucket in sorted(state.buckets.items())
            }
            return PollReductionResult(
                status="replayed",
                state=state,
                poll_id=poll_id,
                observed_at=observed_at_iso,
                replayed=True,
                rejection_reason=None,
                accepted_scopes=(),
                rejected_observations=(),
                decisions=replay_decisions,
                eligible=(),
                write_authorized=False,
            )
        return _rejected_poll(
            state,
            f"conflicting poll_id {poll_id!r} does not match prior poll receipt",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )

    if state.last_observed_at is not None and observed_at_dt < parse_strict_utc(state.last_observed_at):
        return _rejected_poll(
            state,
            f"stale observed_at {observed_at_iso} predates state last_observed_at {state.last_observed_at}",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )

    if not poll.complete:
        return _rejected_poll(
            state,
            "incomplete poll snapshot; refusing to infer vanishings or eligibility",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )

    # Validate each observation independently (fail-closed per scope, no uncaught TypeErrors).
    validated_by_scope: dict[tuple[str, str], dict[str, Any]] = {}
    conflicting_scopes: set[tuple[str, str]] = set()
    rejected_observations: list[RejectedObservation] = []
    rejected_scopes: set[tuple[str, str]] = set()
    held_incoming_scopes: set[tuple[str, str]] = set()
    unavailable_incoming_scopes: set[tuple[str, str]] = set()

    for idx, raw_finding in enumerate(poll.findings):
        try:
            repo, named_id, finding = _validate_finding_observation(raw_finding, authority)
        except (PayloadError, GhError, TypeError, ValueError, KeyError) as exc:
            best_repo, best_named = _best_effort_scope(raw_finding, authority)
            rejected_observations.append(
                RejectedObservation(index=idx, named_id=best_named, repository=best_repo, reason=str(exc))
            )
            if best_repo is not None and best_named is not None:
                rejected_scopes.add((best_repo, best_named))
            continue

        scope = (repo, named_id)
        if named_id in unavailable_named_ids:
            unavailable_incoming_scopes.add(scope)
            continue
        if repo in held_repos or named_id in held_named_ids:
            held_incoming_scopes.add(scope)
            continue

        if scope in conflicting_scopes:
            rejected_observations.append(
                RejectedObservation(
                    index=idx,
                    named_id=named_id,
                    repository=repo,
                    reason="conflicting duplicate observation for same (repository, named_id) in poll",
                )
            )
            continue

        existing = validated_by_scope.get(scope)
        if existing is not None:
            if existing != finding:
                del validated_by_scope[scope]
                conflicting_scopes.add(scope)
                rejected_scopes.add(scope)
                rejected_observations.append(
                    RejectedObservation(
                        index=idx,
                        named_id=named_id,
                        repository=repo,
                        reason="conflicting duplicate observation for same (repository, named_id) in poll",
                    )
                )
            continue

        validated_by_scope[scope] = finding

    # Remove any scope that also had a malformed entry in the same poll.
    for scope in list(validated_by_scope):
        if scope in rejected_scopes:
            del validated_by_scope[scope]

    next_buckets: dict[tuple[str, str], NamedBucket] = dict(state.buckets)
    accepted_scopes: list[tuple[str, str]] = []
    decisions: dict[tuple[str, str], NamedDecision] = {}

    for scope in sorted(validated_by_scope):
        repo, named_id = scope
        prior = state.buckets.get(scope)
        if prior is not None and observed_at_dt < parse_strict_utc(prior.last_observed_at):
            rejected_observations.append(
                RejectedObservation(
                    index=-1,
                    named_id=named_id,
                    repository=repo,
                    reason="stale observed_at predates bucket last_observed_at",
                )
            )
            rejected_scopes.add(scope)
            continue
        folded = _fold_bucket(prior, repo, named_id, validated_by_scope[scope], poll_id, observed_at_iso)
        next_buckets[scope] = folded
        accepted_scopes.append(scope)
        decisions[scope] = _decision_for_observed_bucket(folded, poll_id, observed_at_dt, observed_at_iso, cfg)

    # Record explicit non-eligible decisions for existing buckets not accepted in this poll,
    # plus incoming held/unavailable scopes that have no prior bucket yet.
    all_unobserved_scopes = (
        (set(next_buckets) - set(accepted_scopes))
        | held_incoming_scopes
        | unavailable_incoming_scopes
    )
    for scope in sorted(all_unobserved_scopes):
        repo, named_id = scope
        bucket = next_buckets.get(scope)
        if repo in held_repos or named_id in held_named_ids:
            decision_kind = DECISION_HELD_SCOPE
            reasons = ("explicit-hold",)
        elif named_id in unavailable_named_ids:
            decision_kind = DECISION_UNAVAILABLE
            reasons = ("suite-unavailable",)
        elif scope in rejected_scopes:
            decision_kind = DECISION_REJECTED
            reasons = ("observation-rejected",)
        else:
            decision_kind = DECISION_ABSENT
            reasons = ("not-observed-in-current-poll",)

        if bucket is not None:
            decisions[scope] = _decision_for_unobserved_bucket(
                bucket, decision_kind, reasons, poll_id, observed_at_dt, observed_at_iso, cfg
            )
        else:
            decisions[scope] = NamedDecision(
                repository=repo,
                named_id=named_id,
                decision=decision_kind,
                eligible=False,
                write_authorized=False,
                reasons=reasons,
                poll_id=poll_id,
                observed_at=observed_at_iso,
                pending_since=None,
                next_flush=next_flush_date(observed_at_dt, cfg),
                max_hold_until=None,
                bucket_revision=None,
                finding_sha256=None,
                finding=None,
                row_pins={},
                present_row_ids=(),
                vanished_row_ids=(),
            )

    next_seen_polls = dict(state.seen_polls)
    next_seen_polls[poll_id] = PollReceipt(
        poll_id=poll_id,
        observed_at=observed_at_iso,
        complete=poll.complete,
        input_digest=input_digest,
    )

    next_state = ReducerState(
        schema_version=state.schema_version,
        revision=state.revision + 1,
        last_observed_at=observed_at_iso,
        last_poll_id=poll_id,
        buckets=next_buckets,
        seen_polls=next_seen_polls,
    )

    eligible = tuple(
        decisions[scope]
        for scope in sorted(decisions)
        if decisions[scope].eligible
    )

    return PollReductionResult(
        status="applied",
        state=next_state,
        poll_id=poll_id,
        observed_at=observed_at_iso,
        replayed=False,
        rejection_reason=None,
        accepted_scopes=tuple(accepted_scopes),
        rejected_observations=tuple(rejected_observations),
        decisions=decisions,
        eligible=eligible,
        write_authorized=False,
    )
