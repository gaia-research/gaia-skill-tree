"""Pure, exact-scoped offline weekly observation reducer (P2 Slice 1).

Scope
-----
This module implements ONLY pure in-memory observation reduction and per-named
eligibility selection for the independently versioned P2 weekly namespace:

* Scope key: ``(repository, named_id, row_id)`` where ``repository`` is the
  normalized lowercase ``owner/repo``, ``named_id`` is the exact case-sensitive
  canonical ``skillId``, and ``row_id`` is ``<repo>:<slug>``.
* Dual-evidence separation: canonical payload authority (``planned_findings``
  from ``repository_batch`` / ``envelope``) is separated from current-poll
  observation provenance (``observed_findings`` from the detector /
  ``report["observedFindings"]``). Each accepted bucket requires an explicit
  checked join on ``(repository, named_id, sourceUrl, newVersion, finding_kind)``
  in the same poll. Retained canonical siblings and closed carry-forward rows
  are history only, never current sightings.
* Single authority: the real canonical planner remains the sole authority for
  envelope structure, row status, and digests. This reducer validates canonical
  named findings via ``envelope.validate_named`` and
  ``releaseidentity.validateReleaseSource`` and carries each verified snapshot
  unchanged (including ``componentRemoves``, ``linkLiveness``, ``nameDrift``,
  ``candidates``, and ``payloadSha256``).
* Immutable provenance & pin continuity: each ``(repository, named_id, row_id)``
  records one immutable ``FirstSeenPin`` (``first_seen_version``,
  ``evidence_url``, ``first_seen_at``, ``first_seen_poll_id``). Conflicting
  incoming pins reject the affected scope fail-closed, preserving prior state
  byte-for-byte while leaving unrelated coverage unaffected.
* Honest candidate presence: current candidate presence is derived strictly from
  explicit raw ``componentAdds`` matched to validated canonical rows. Because
  ``componentAdds`` is a delta against tracked ``suiteComponents`` (and is also
  empty on bootstrap, version-only, and missing-root fallback observations),
  omission from raw ``componentAdds`` is ``unknown`` presence, NEVER proof of
  disappearance. Affirmative absence (``vanished``) or tracked upstream presence
  (``present-tracked``) is derived ONLY from an explicit, scoped complete
  inventory seam (``ScopedCompleteInventory``) bound to the exact same poll ID,
  repository, named ID, version, release source URL, and verified component
  root on a component-mode update. Ordinary ``run_repository_batch`` reports do
  not carry complete inventories and therefore never fabricate vanishings.
  Historical-only rows first encountered in canonical output remain in
  canonical view without fabricating a sighting or prior timestamp; if later
  observed in raw ``componentAdds``, they preserve their canonical version/URL
  pin while recording the real first-observation timestamp and poll ID.
* Scoped fresh urgency: urgent eligibility (HTTP 404/410) is granted ONLY from
  explicit current raw liveness checks for exact ``authority[named_id]``
  ``suiteComponents`` (excluding ``linkLivenessUnknown``, malformed, untracked,
  or unconfirmed entries) while retaining the canonical finding unchanged.
* Bounded resources & state isolation: explicit aggregate resource budgets in
  ``ReducerConfig`` fail closed before committing oversized state (while still
  permitting exact replay at capacity) with zero silent compaction. Returned
  states, ``decisions``, and ``eligible`` views expose immutable mapping
  containers and independent defensive copies with zero nested mutable aliasing
  across prior, returned, replayed, rejected, or eligible views.
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
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from scripts.upstream_watcher import envelope
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import GhError
from scripts.upstream_watcher.releaseidentity import validateReleaseSource

SCHEMA_VERSION = 1
DEFAULT_FLUSH_WEEKDAY = 0  # Monday (UTC)
DEFAULT_WINDOW_DAYS = 7
DEFAULT_MAX_SEEN_POLLS = 1024
DEFAULT_MAX_BUCKETS = 256
DEFAULT_MAX_ROWS_PER_BUCKET = 512
DEFAULT_MAX_TOTAL_ROWS = 4096
DEFAULT_MAX_VERSIONS_PER_BUCKET = 128
URGENT_HTTP_STATUSES = frozenset({404, 410})

DECISION_HOLD = "hold"
DECISION_FLUSH = "flush"
DECISION_URGENT = "urgent"
DECISION_ABSENT = "absent"
DECISION_HELD_SCOPE = "held-scope"
DECISION_UNAVAILABLE = "unavailable"
DECISION_REJECTED = "rejected"
DECISION_REPLAYED = "replayed"

PRESENCE_PRESENT_CANDIDATE = "present-candidate"
PRESENCE_PRESENT_TRACKED = "present-tracked"
PRESENCE_UNKNOWN = "unknown"
PRESENCE_VANISHED = "vanished"

DEFAULT_COMPONENT_ROOT = "skills"

_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_RFC3339_RE = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]{1,6}))?(?:([Zz])|([+-])([0-9]{2}):([0-9]{2}))\Z"
)
_OVERPRECISION_FRAC_RE = re.compile(r"[.,][0-9]{7,}")
_REQUIRED_CANONICAL_KEYS = (
    "skillId",
    "newVersion",
    "releasedAt",
    "sourceUrl",
    "mode",
    "payloadVersion",
    "payloadSha256",
    "componentAdds",
    "componentRemoves",
    "linkLiveness",
    "nameDrift",
    "candidates",
)
_REQUIRED_RAW_KEYS = (
    "finding_type",
    "skillId",
    "newVersion",
    "releasedAt",
    "sourceUrl",
    "mode",
    "componentAdds",
    "componentRemoves",
    "linkLiveness",
    "nameDrift",
)


# ---------------------------------------------------------------------------
# Strict time, identifier, and cloning helpers
# ---------------------------------------------------------------------------


def parse_strict_utc(value: dt.datetime | str) -> dt.datetime:
    """Parse an aware UTC/offset datetime or strict RFC3339 string at microsecond precision.

    Enforces an explicit extended RFC3339 string grammar:
    ``YYYY-MM-DD[T|t]HH:MM:SS[.f{1,6}](Z|z|+HH:MM|-HH:MM)``.
    Rejects naive, malformed, comma-fractional, arbitrary-separator, fractional-offset,
    or sub-microsecond (>6 fractional digits) values so accepted timestamps round-trip
    losslessly through ``format_utc`` and receipt digests.
    """
    if isinstance(value, dt.datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at datetime must be timezone-aware")
        return value.astimezone(dt.timezone.utc)
    if isinstance(value, str):
        if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("observed_at string is empty or contains control characters")
        match = _RFC3339_RE.fullmatch(value)
        if match is None:
            if _OVERPRECISION_FRAC_RE.search(value) is not None:
                raise ValueError(f"observed_at fractional seconds exceed microsecond precision: {value!r}")
            raise ValueError(f"invalid RFC3339 observed_at: {value!r}")
        year, month, day, hour, minute, second, frac, z_flag, sign, off_h, off_m = match.groups()
        microsecond = int(frac.ljust(6, "0")) if frac is not None else 0
        if z_flag is not None:
            tz = dt.timezone.utc
        else:
            oh = int(off_h)
            om = int(off_m)
            if oh > 23 or om > 59:
                raise ValueError(f"invalid RFC3339 timezone offset in observed_at: {value!r}")
            delta = dt.timedelta(hours=oh, minutes=om)
            if sign == "-":
                delta = -delta
            tz = dt.timezone(delta)
        try:
            parsed = dt.datetime(
                int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                int(second),
                microsecond,
                tzinfo=tz,
            )
        except ValueError as exc:
            raise ValueError(f"invalid RFC3339 observed_at: {value!r}") from exc
        return parsed.astimezone(dt.timezone.utc)
    raise ValueError("observed_at must be a timezone-aware datetime or RFC3339 string")


def format_utc(value: dt.datetime) -> str:
    """Format an aware datetime in canonical UTC ISO-8601, preserving microsecond precision."""
    utc = value.astimezone(dt.timezone.utc)
    if utc.microsecond:
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_valid_component_root(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("/") or value.endswith("/") or "\\" in value:
        return False
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    segments = value.split("/")
    return not any(not seg or seg in (".", "..") for seg in segments)


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


def _freeze_mapping(mapping: Mapping[Any, Any]) -> Mapping[Any, Any]:
    return MappingProxyType(dict(mapping))


def _is_nonempty_clean_str(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
    )


# ---------------------------------------------------------------------------
# Configuration & isolated state model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReducerConfig:
    """Pure review-window and aggregate resource-bound configuration (UTC)."""

    flush_weekday: int = DEFAULT_FLUSH_WEEKDAY
    window_days: int = DEFAULT_WINDOW_DAYS
    max_seen_polls: int = DEFAULT_MAX_SEEN_POLLS
    max_buckets: int = DEFAULT_MAX_BUCKETS
    max_rows_per_bucket: int = DEFAULT_MAX_ROWS_PER_BUCKET
    max_total_rows: int = DEFAULT_MAX_TOTAL_ROWS
    max_versions_per_bucket: int = DEFAULT_MAX_VERSIONS_PER_BUCKET

    def __post_init__(self) -> None:
        if type(self.flush_weekday) is not int or not 0 <= self.flush_weekday <= 6:
            raise ValueError("flush_weekday must be an integer in 0..6 (Monday..Sunday UTC)")
        if type(self.window_days) is not int or self.window_days < 1:
            raise ValueError("window_days must be a positive integer")
        for field_name in (
            "max_seen_polls",
            "max_buckets",
            "max_rows_per_bucket",
            "max_total_rows",
            "max_versions_per_bucket",
        ):
            val = getattr(self, field_name)
            if type(val) is not int or val < 1:
                raise ValueError(f"{field_name} must be a positive integer")


def is_flush_day(observed_at: dt.datetime, config: ReducerConfig) -> bool:
    return observed_at.astimezone(dt.timezone.utc).weekday() == config.flush_weekday


def next_flush_date(observed_at: dt.datetime, config: ReducerConfig) -> str:
    today = observed_at.astimezone(dt.timezone.utc).date()
    ahead = (config.flush_weekday - today.weekday()) % 7
    return (today + dt.timedelta(days=ahead)).isoformat()


@dataclass(frozen=True)
class FirstSeenPin:
    """Immutable authoritative provenance tuple for one scoped candidate row.

    For historical-only rows first encountered in canonical carry-forward
    output (omitted from current raw ``componentAdds``), ``first_seen_at`` and
    ``first_seen_poll_id`` remain ``None`` rather than fabricating a prior
    timestamp.
    """

    first_seen_version: str
    evidence_url: str
    first_seen_at: str | None
    first_seen_poll_id: str | None


@dataclass(frozen=True)
class RowHistory:
    """Exact-scoped history for one candidate row under ``(repository, named_id)``."""

    row_id: str
    slug: str
    suggested_id: str
    first_seen_pin: FirstSeenPin
    last_seen_version: str
    last_seen_at: str | None
    last_seen_poll_id: str | None
    present_in_latest: bool
    vanished_at: str | None
    vanished_poll_id: str | None
    latest_row: dict[str, Any]
    historical_only: bool = False
    presence: str = PRESENCE_UNKNOWN


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", _freeze_mapping(self.rows))

    @property
    def present_row_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(rid for rid, row in self.rows.items() if row.presence == PRESENCE_PRESENT_CANDIDATE)
        )

    @property
    def tracked_present_row_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(rid for rid, row in self.rows.items() if row.presence == PRESENCE_PRESENT_TRACKED)
        )

    @property
    def upstream_present_row_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                rid
                for rid, row in self.rows.items()
                if row.presence in (PRESENCE_PRESENT_CANDIDATE, PRESENCE_PRESENT_TRACKED)
            )
        )

    @property
    def unknown_presence_row_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                rid
                for rid, row in self.rows.items()
                if row.presence == PRESENCE_UNKNOWN and not row.historical_only
            )
        )

    @property
    def vanished_row_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                rid
                for rid, row in self.rows.items()
                if row.presence == PRESENCE_VANISHED and not row.historical_only
            )
        )

    @property
    def historical_row_ids(self) -> tuple[str, ...]:
        return tuple(sorted(rid for rid, row in self.rows.items() if row.historical_only))


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "buckets", _freeze_mapping(self.buckets))
        object.__setattr__(self, "seen_polls", _freeze_mapping(self.seen_polls))

    def get_bucket(self, repo: str, named_id: str) -> NamedBucket | None:
        bucket = self.buckets.get((envelope.repository(repo), named_id))
        return _clone_bucket(bucket) if bucket is not None else None

    def repo_buckets(self, repo: str) -> dict[str, NamedBucket]:
        normalized = envelope.repository(repo)
        return {
            named_id: _clone_bucket(bucket)
            for (bucket_repo, named_id), bucket in sorted(self.buckets.items())
            if bucket_repo == normalized
        }


def _clone_row(row: RowHistory) -> RowHistory:
    return RowHistory(
        row_id=row.row_id,
        slug=row.slug,
        suggested_id=row.suggested_id,
        first_seen_pin=row.first_seen_pin,
        last_seen_version=row.last_seen_version,
        last_seen_at=row.last_seen_at,
        last_seen_poll_id=row.last_seen_poll_id,
        present_in_latest=row.present_in_latest,
        vanished_at=row.vanished_at,
        vanished_poll_id=row.vanished_poll_id,
        latest_row=copy.deepcopy(row.latest_row),
        historical_only=row.historical_only,
        presence=row.presence,
    )


def _clone_bucket(bucket: NamedBucket) -> NamedBucket:
    return NamedBucket(
        repository=bucket.repository,
        named_id=bucket.named_id,
        pending_since=bucket.pending_since,
        first_poll_id=bucket.first_poll_id,
        last_observed_at=bucket.last_observed_at,
        last_poll_id=bucket.last_poll_id,
        sighting_count=bucket.sighting_count,
        revision=bucket.revision,
        latest_finding=copy.deepcopy(bucket.latest_finding),
        latest_finding_sha256=bucket.latest_finding_sha256,
        versions_seen=bucket.versions_seen,
        rows={rid: _clone_row(row) for rid, row in sorted(bucket.rows.items())},
    )


def _clone_state(state: ReducerState) -> ReducerState:
    return ReducerState(
        schema_version=state.schema_version,
        revision=state.revision,
        last_observed_at=state.last_observed_at,
        last_poll_id=state.last_poll_id,
        buckets={scope: _clone_bucket(bucket) for scope, bucket in sorted(state.buckets.items())},
        seen_polls=dict(state.seen_polls),
    )


def empty_state() -> ReducerState:
    return ReducerState()


# ---------------------------------------------------------------------------
# Poll input, adapter seam & reduction output types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopedCompleteInventory:
    """Explicit, scoped complete upstream-component inventory seam (offline only).

    NOTE: This is an isolated typed seam for unit-injected verified fixture
    authority, NOT a qualified production producer integration. Ordinary
    ``run_repository_batch`` reports do not populate this field.

    Usable ONLY on component-mode ``update`` findings from a full, non-truncated,
    verified component root bound to the exact same poll ID, repository, named
    ID, version, release source URL, raw ``upstreamComponentRoot``, and
    authoritative suite component root from ``authority[named_id]``.

    All three availability fields (``complete``, ``truncated``, ``root_verified``)
    default to conservative unusable values so omitted metadata can never prove
    absence.
    """

    poll_id: str
    repository: str
    named_id: str
    version: str
    source_url: str
    component_root: str
    present_slugs: frozenset[str]
    complete: bool = False
    truncated: bool = True
    root_verified: bool = False


def _authority_component_root(named_id: str, authority: Mapping[str, Any]) -> str:
    """Derive the authoritative component root for *named_id* from ``authority[named_id]``.

    Follows the watcher contract: uses configured ``upstreamComponentRoot`` when
    present and non-None (rejecting malformed configured values), and falls back
    to the documented ``"skills"`` default ONLY when ``upstreamComponentRoot`` is
    not configured. Never infers a root from raw observations.
    """
    meta = authority.get(named_id)
    if not isinstance(meta, dict) or meta.get("id") != named_id:
        raise PayloadError("named identity is not in registry authority")
    if "upstreamComponentRoot" not in meta or meta["upstreamComponentRoot"] is None:
        return DEFAULT_COMPONENT_ROOT
    configured = meta["upstreamComponentRoot"]
    if not _is_valid_component_root(configured):
        raise PayloadError("registry authority has malformed upstreamComponentRoot")
    return configured


def qualify_complete_inventory(
    inventory: ScopedCompleteInventory,
    *,
    poll_id: str,
    repository: str,
    named_id: str,
    raw_obs: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> tuple[frozenset[str] | None, str | None]:
    """Validate whether *inventory* qualifies as a complete upstream-presence proof.

    Returns ``(present_slugs, None)`` when qualified, or ``(None, reason)`` when
    unusable. Unusable inventories never prove disappearance; omitted rows stay
    ``PRESENCE_UNKNOWN``.
    """
    if not isinstance(inventory, ScopedCompleteInventory):
        return None, "inventory is not a ScopedCompleteInventory"
    if type(inventory.complete) is not bool or not inventory.complete:
        return None, "inventory is not complete"
    if type(inventory.truncated) is not bool or inventory.truncated:
        return None, "inventory is truncated"
    if type(inventory.root_verified) is not bool or not inventory.root_verified:
        return None, "inventory component root is not verified"
    if raw_obs.get("finding_type") != "update":
        return None, "complete inventory is only usable for update findings, not bootstrap"
    if raw_obs.get("mode") != "components":
        return None, "complete inventory is only usable for components mode"
    if inventory.poll_id != poll_id:
        return None, "inventory poll_id disagrees with current poll_id"
    try:
        inv_repo = envelope.repository(inventory.repository)
    except PayloadError:
        return None, "inventory repository is invalid"
    if inv_repo != repository:
        return None, "inventory repository disagrees with observed scope"
    if inventory.named_id != named_id:
        return None, "inventory named_id disagrees with observed scope"
    try:
        if envelope.authority_repository(inventory.named_id, authority) != repository:
            return None, "inventory named_id disagrees with registry authority"
        tracked_components = _tracked_components(inventory.named_id, authority)
        auth_root = _authority_component_root(inventory.named_id, authority)
    except PayloadError as exc:
        return None, str(exc)
    if not tracked_components:
        return None, "named suite has no configured suiteComponents in registry authority"
    raw_root = raw_obs.get("upstreamComponentRoot")
    if not _is_valid_component_root(raw_root):
        return None, "observed finding has missing or invalid upstreamComponentRoot"
    if not _is_valid_component_root(inventory.component_root):
        return None, "inventory has missing or invalid component_root"
    if raw_root != auth_root:
        return None, "observed upstreamComponentRoot disagrees with registry authority"
    if inventory.component_root != auth_root:
        return None, "inventory component_root disagrees with registry authority"
    if inventory.component_root != raw_root:
        return None, "inventory component_root disagrees with observed upstreamComponentRoot"
    if inventory.version != raw_obs.get("newVersion"):
        return None, "inventory version disagrees with observed newVersion"
    if inventory.source_url != raw_obs.get("sourceUrl"):
        return None, "inventory source_url disagrees with observed sourceUrl"
    try:
        if envelope.release_repository(inventory.source_url, inventory.version) != repository:
            return None, "inventory release source disagrees with scope repository"
    except PayloadError:
        return None, "inventory release source is invalid"
    if not isinstance(inventory.present_slugs, (frozenset, set, list, tuple)):
        return None, "inventory present_slugs has invalid container type"
    if not all(isinstance(s, str) and _SLUG_RE.fullmatch(s) for s in inventory.present_slugs):
        return None, "inventory present_slugs contains invalid slug"
    slugs = frozenset(inventory.present_slugs)
    if len(slugs) > envelope.MAX_ROWS:
        return None, "inventory present_slugs exceeds MAX_ROWS"
    raw_adds = raw_obs.get("componentAdds")
    if not isinstance(raw_adds, list) or not all(isinstance(s, str) and _SLUG_RE.fullmatch(s) for s in raw_adds):
        return None, "observed finding has invalid componentAdds"
    raw_adds_set = set(raw_adds)
    if not raw_adds_set <= slugs:
        return None, "inventory present_slugs omits slugs reported in raw componentAdds"
    raw_removes = raw_obs.get("componentRemoves")
    if not isinstance(raw_removes, list) or not all(isinstance(s, str) and _SLUG_RE.fullmatch(s) for s in raw_removes):
        return None, "observed finding has invalid componentRemoves"
    raw_remove_slugs = set(raw_removes)
    if len(raw_remove_slugs) != len(raw_removes):
        return None, "observed finding has duplicate slugs in componentRemoves"
    if not raw_remove_slugs.isdisjoint(slugs):
        return None, "inventory present_slugs includes slugs reported in raw componentRemoves"
    tracked_slugs = {comp_id.rsplit("/", 1)[-1] for comp_id in tracked_components}
    if not raw_adds_set.isdisjoint(tracked_slugs):
        return None, "observed componentAdds overlaps configured suiteComponents"
    if not (slugs - tracked_slugs) <= raw_adds_set:
        return None, "inventory present_slugs contains untracked slugs omitted from raw componentAdds"
    expected_removes = tracked_slugs - slugs
    if not expected_removes <= raw_remove_slugs:
        return None, "inventory present_slugs omits tracked suiteComponents absent from raw componentRemoves"
    if raw_remove_slugs != expected_removes:
        return None, "observed componentRemoves contains untracked slugs absent from configured suiteComponents"
    return slugs, None


def _serialize_complete_inventories(inventories: Any) -> list[dict[str, Any]]:
    if not isinstance(inventories, (list, tuple)):
        raise PayloadError("poll.complete_inventories must be a list or tuple")
    serialized: list[dict[str, Any]] = []
    for inv in inventories:
        if not isinstance(inv, ScopedCompleteInventory):
            raise PayloadError("poll.complete_inventories entries must be ScopedCompleteInventory")
        if not isinstance(inv.present_slugs, (frozenset, set, list, tuple)):
            raise PayloadError("inventory present_slugs must be a set, frozenset, list, or tuple")
        if not all(isinstance(slug, str) for slug in inv.present_slugs):
            raise PayloadError("inventory present_slugs entries must be strings")
        serialized.append(
            {
                "poll_id": inv.poll_id,
                "repository": inv.repository,
                "named_id": inv.named_id,
                "version": inv.version,
                "source_url": inv.source_url,
                "component_root": inv.component_root,
                "present_slugs": sorted(set(inv.present_slugs)),
                "complete": inv.complete,
                "truncated": inv.truncated,
                "root_verified": inv.root_verified,
            }
        )
    return serialized


@dataclass(frozen=True)
class PollInput:
    """One offline poll snapshot supplied to ``reduce_poll``.

    Carries two required evidence tracks:
    * ``observed_findings``: raw detector findings observed in this current poll
      (e.g. ``report["observedFindings"]`` from ``run_repository_batch``).
    * ``planned_findings``: canonical sealed named findings produced by the real
      P1 planner (which may also carry retained unobserved siblings and
      carried-forward candidate rows).

    Optionally carries ``complete_inventories``, an isolated offline seam of
    ``ScopedCompleteInventory`` proofs. Ordinary P1 reports leave this empty.
    """

    poll_id: str
    observed_at: dt.datetime | str
    observed_findings: Sequence[Mapping[str, Any]]
    planned_findings: Sequence[Mapping[str, Any]]
    complete: bool = True
    held_repos: frozenset[str] = frozenset()
    held_named_ids: frozenset[str] = frozenset()
    unavailable_named_ids: frozenset[str] = frozenset()
    complete_inventories: Sequence[ScopedCompleteInventory] = ()


def poll_input_from_batch_report(
    poll_id: str,
    observed_at: dt.datetime | str,
    report: Mapping[str, Any],
    *,
    complete: bool = True,
    held_repos: frozenset[str] = frozenset(),
    held_named_ids: frozenset[str] = frozenset(),
    unavailable_named_ids: frozenset[str] = frozenset(),
) -> PollInput:
    """Deterministic adapter from a ``run_repository_batch`` report to ``PollInput``.

    Preserves both ``report["observedFindings"]`` and canonical planned findings
    unchanged, merges any ``knownLegacyHolds`` repositories into ``held_repos``,
    requires an explicitly present ``unknownEvidence`` list and boolean
    ``complete``, and forces ``complete=False`` if the report recorded any
    ``unknownEvidence``. Never fabricates complete upstream inventories.
    """
    if not isinstance(report, Mapping):
        raise PayloadError("batch report must be a mapping")
    if type(complete) is not bool:
        raise PayloadError("complete must be a boolean")
    if "unknownEvidence" not in report or not isinstance(report["unknownEvidence"], list):
        raise PayloadError("batch report must contain an explicit unknownEvidence list")
    observed = report.get("observedFindings")
    repositories = report.get("repositories")
    if not isinstance(observed, (list, tuple)) or not isinstance(repositories, (list, tuple)):
        raise PayloadError("batch report must contain list/tuple observedFindings and repositories")
    if "knownLegacyHolds" in report and report["knownLegacyHolds"] is not None:
        if not isinstance(report["knownLegacyHolds"], list):
            raise PayloadError("malformed top-level knownLegacyHolds in batch report")
    if "unavailable" in report and report["unavailable"] is not None:
        if not isinstance(report["unavailable"], list):
            raise PayloadError("malformed unavailable list in batch report")
    if "unavailableNamedIds" in report and report["unavailableNamedIds"] is not None:
        if not isinstance(report["unavailableNamedIds"], list):
            raise PayloadError("malformed unavailableNamedIds list in batch report")

    container_types = (set, frozenset, list, tuple)
    if not isinstance(held_repos, container_types):
        raise PayloadError("held_repos must be a set, frozenset, list, or tuple")
    if not isinstance(held_named_ids, container_types):
        raise PayloadError("held_named_ids must be a set, frozenset, list, or tuple")
    if not isinstance(unavailable_named_ids, container_types):
        raise PayloadError("unavailable_named_ids must be a set, frozenset, list, or tuple")

    merged_held_repos: set[str] = set()
    for repo_name in held_repos:
        merged_held_repos.add(envelope.repository(repo_name))
    validated_held_named: set[str] = set()
    for named_id in held_named_ids:
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise PayloadError(f"invalid held_named_ids entry: {named_id!r}")
        validated_held_named.add(named_id)
    validated_unavailable_named: set[str] = set()
    for named_id in unavailable_named_ids:
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise PayloadError(f"invalid unavailable_named_ids entry: {named_id!r}")
        validated_unavailable_named.add(named_id)

    planned: list[dict[str, Any]] = []
    for repo_plan in repositories:
        if not isinstance(repo_plan, Mapping):
            raise PayloadError("malformed repository plan entry in batch report")
        if "knownLegacyHolds" in repo_plan and repo_plan["knownLegacyHolds"] is not None:
            if not isinstance(repo_plan["knownLegacyHolds"], list):
                raise PayloadError("malformed knownLegacyHolds in repository plan entry")
            if repo_plan["knownLegacyHolds"]:
                merged_held_repos.add(envelope.repository(repo_plan.get("repository")))
        payload = repo_plan.get("payload")
        if payload is not None:
            if not isinstance(payload, Mapping) or not isinstance(payload.get("findings"), list):
                raise PayloadError("malformed canonical payload in batch report")
            planned.extend(copy.deepcopy(payload["findings"]))

    unknown_evidence = report["unknownEvidence"]
    effective_complete = complete and len(unknown_evidence) == 0
    return PollInput(
        poll_id=poll_id,
        observed_at=observed_at,
        observed_findings=copy.deepcopy(list(observed)),
        planned_findings=planned,
        complete=effective_complete,
        held_repos=frozenset(merged_held_repos),
        held_named_ids=frozenset(validated_held_named),
        unavailable_named_ids=frozenset(validated_unavailable_named),
        complete_inventories=(),
    )


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
    historical_row_ids: tuple[str, ...] = ()
    tracked_present_row_ids: tuple[str, ...] = ()
    unknown_presence_row_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "row_pins", _freeze_mapping(self.row_pins))


def _clone_decision(decision: NamedDecision) -> NamedDecision:
    return NamedDecision(
        repository=decision.repository,
        named_id=decision.named_id,
        decision=decision.decision,
        eligible=decision.eligible,
        write_authorized=decision.write_authorized,
        reasons=decision.reasons,
        poll_id=decision.poll_id,
        observed_at=decision.observed_at,
        pending_since=decision.pending_since,
        next_flush=decision.next_flush,
        max_hold_until=decision.max_hold_until,
        bucket_revision=decision.bucket_revision,
        finding_sha256=decision.finding_sha256,
        finding=copy.deepcopy(decision.finding),
        row_pins=dict(decision.row_pins),
        present_row_ids=decision.present_row_ids,
        vanished_row_ids=decision.vanished_row_ids,
        historical_row_ids=decision.historical_row_ids,
        tracked_present_row_ids=decision.tracked_present_row_ids,
        unknown_presence_row_ids=decision.unknown_presence_row_ids,
    )


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "decisions", _freeze_mapping(self.decisions))


# ---------------------------------------------------------------------------
# Validation, checked join & urgency helpers
# ---------------------------------------------------------------------------


def _tracked_components(named_id: str, authority: Mapping[str, Any]) -> frozenset[str]:
    """Return validated exact ``authority[named_id]['suiteComponents']`` set."""
    meta = authority.get(named_id)
    if not isinstance(meta, dict) or meta.get("id") != named_id:
        raise PayloadError("named identity is not in registry authority")
    raw_components = meta.get("suiteComponents")
    if raw_components is None:
        return frozenset()
    if not isinstance(raw_components, list):
        raise PayloadError("malformed suiteComponents authority")
    components: set[str] = set()
    for comp_id in raw_components:
        if not isinstance(comp_id, str) or not envelope.IDENTIFIER.fullmatch(comp_id):
            raise PayloadError("malformed suiteComponents authority")
        components.add(comp_id)
    return frozenset(components)


def _validate_liveness_list(entries: Any) -> None:
    if not isinstance(entries, list):
        raise PayloadError("linkLiveness must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise PayloadError("malformed linkLiveness entry")
        skill_id = entry.get("skillId")
        url = entry.get("url")
        status = entry.get("status")
        if not isinstance(skill_id, str) or not skill_id or not isinstance(url, str) or not url:
            raise PayloadError("malformed linkLiveness entry fields")
        valid_status = status == "network_error" or (type(status) is int and 100 <= status <= 599)
        if not valid_status:
            raise PayloadError("malformed linkLiveness status")


def _validate_name_drift_list(entries: Any) -> None:
    if not isinstance(entries, list):
        raise PayloadError("nameDrift must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise PayloadError("malformed nameDrift entry")
        skill_id = entry.get("skillId")
        if not isinstance(skill_id, str) or not skill_id:
            raise PayloadError("malformed nameDrift entry fields")


def urgent_reasons(
    raw_finding: Mapping[str, Any],
    planned_finding: Mapping[str, Any],
    named_id: str,
    authority: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return sorted urgent reasons from explicit current raw checks for tracked components only.

    Excludes ``linkLivenessUnknown``, malformed entries, untracked/out-of-scope
    component IDs, and any check not confirmed with identical ``(skillId, url,
    status)`` in the sealed canonical finding.
    """
    try:
        tracked = _tracked_components(named_id, authority)
    except PayloadError:
        return ()

    raw_unknown = raw_finding.get("linkLivenessUnknown")
    unknown_ids: set[str] = set()
    if isinstance(raw_unknown, list):
        unknown_ids = {item for item in raw_unknown if isinstance(item, str)}

    canonical_checks: set[tuple[str, str, int]] = set()
    planned_liveness = planned_finding.get("linkLiveness")
    if isinstance(planned_liveness, list):
        for row in planned_liveness:
            if not isinstance(row, dict):
                continue
            sid = row.get("skillId")
            url = row.get("url")
            status = row.get("status")
            if isinstance(sid, str) and isinstance(url, str) and type(status) is int:
                canonical_checks.add((sid, url, status))

    raw_liveness = raw_finding.get("linkLiveness")
    if not isinstance(raw_liveness, list):
        return ()

    reasons: set[str] = set()
    for row in raw_liveness:
        if not isinstance(row, dict):
            continue
        skill_id = row.get("skillId")
        url = row.get("url")
        status = row.get("status")
        if (
            not isinstance(skill_id, str)
            or not isinstance(url, str)
            or type(status) is not int
            or status not in URGENT_HTTP_STATUSES
        ):
            continue
        if skill_id in unknown_ids or skill_id not in tracked:
            continue
        if (skill_id, url, status) not in canonical_checks:
            continue
        reasons.add(f"dead-link:{skill_id}:{status}")
    return tuple(sorted(reasons))


def _validate_raw_observation(
    raw_obs: Any,
    authority: Mapping[str, Any],
) -> tuple[str, str, str, dict[str, Any]]:
    """Validate one raw current-poll detector observation.

    Returns ``(repo, named_id, finding_kind, deep_copied_obs)`` or raises ``PayloadError``.
    """
    if not isinstance(raw_obs, dict):
        raise PayloadError("observed finding is not a JSON object")
    try:
        json.dumps(raw_obs, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PayloadError(f"observed finding is not strict JSON: {exc}") from exc

    for key in _REQUIRED_RAW_KEYS:
        if key not in raw_obs:
            raise PayloadError(f"observed finding missing required field: {key}")

    finding_kind = raw_obs["finding_type"]
    if finding_kind not in ("update", "bootstrap"):
        raise PayloadError(f"unsupported observed finding_type: {finding_kind!r}")

    named_id = raw_obs["skillId"]
    repo = envelope.authority_repository(named_id, authority)
    _tracked_components(named_id, authority)

    for key in ("newVersion", "releasedAt"):
        if not _is_nonempty_clean_str(raw_obs[key]):
            raise PayloadError(f"observed finding has invalid {key}")

    if envelope.release_repository(raw_obs["sourceUrl"], raw_obs["newVersion"]) != repo:
        raise PayloadError("observed finding release source disagrees with registry authority")
    try:
        validateReleaseSource(raw_obs)
    except GhError as exc:
        raise PayloadError(str(exc)) from exc

    if raw_obs["mode"] not in ("components", "version-only", "bootstrap"):
        raise PayloadError("observed finding has invalid mode")

    adds = raw_obs["componentAdds"]
    if not isinstance(adds, list) or len(adds) > envelope.MAX_ROWS:
        raise PayloadError("observed finding componentAdds must be a bounded list")
    if not all(isinstance(slug, str) and _SLUG_RE.fullmatch(slug) for slug in adds) or len(adds) != len(set(adds)):
        raise PayloadError("observed finding has duplicate or malformed componentAdds")

    removes = raw_obs["componentRemoves"]
    if not isinstance(removes, list):
        raise PayloadError("observed finding componentRemoves must be a list")
    if not all(_is_nonempty_clean_str(item) for item in removes) or len(removes) != len(set(removes)):
        raise PayloadError("observed finding has duplicate or malformed componentRemoves")

    _validate_liveness_list(raw_obs["linkLiveness"])
    _validate_name_drift_list(raw_obs["nameDrift"])

    if "linkLivenessUnknown" in raw_obs and raw_obs["linkLivenessUnknown"] is not None:
        unknown = raw_obs["linkLivenessUnknown"]
        if not isinstance(unknown, list) or not all(_is_nonempty_clean_str(item) for item in unknown):
            raise PayloadError("observed finding has malformed linkLivenessUnknown")

    return repo, named_id, finding_kind, copy.deepcopy(raw_obs)


def _validate_planned_finding(
    raw_finding: Any,
    authority: Mapping[str, Any],
) -> tuple[str, str, str, dict[str, Any]]:
    """Validate one canonical named finding via the repo's real authority rules.

    Returns ``(repo, named_id, finding_kind, deep_copied_finding)`` or raises ``PayloadError``.
    """
    if not isinstance(raw_finding, dict):
        raise PayloadError("canonical finding is not a JSON object")
    try:
        json.dumps(raw_finding, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PayloadError(f"canonical finding is not strict JSON: {exc}") from exc

    for key in _REQUIRED_CANONICAL_KEYS:
        if key not in raw_finding:
            raise PayloadError(f"canonical finding missing required field: {key}")

    named_id = raw_finding["skillId"]
    repo = envelope.authority_repository(named_id, authority)
    _tracked_components(named_id, authority)
    try:
        validateReleaseSource(raw_finding)
    except GhError as exc:
        raise PayloadError(str(exc)) from exc

    envelope.validate_named(raw_finding, repo, authority, digest=True, mutation_scope=True)
    _validate_liveness_list(raw_finding["linkLiveness"])
    _validate_name_drift_list(raw_finding["nameDrift"])

    for row in raw_finding["candidates"]:
        if "precheck" in row and not isinstance(row["precheck"], dict):
            raise PayloadError("malformed candidate precheck field")

    finding_kind = raw_finding.get("findingType") or "update"
    return repo, named_id, finding_kind, copy.deepcopy(raw_finding)


def _best_effort_scope(
    raw_entry: Any,
    authority: Mapping[str, Any],
) -> tuple[str | None, str | None]:
    """Extract (repo, named_id) for rejection attribution without raising."""
    if not isinstance(raw_entry, dict):
        return None, None
    named_id = raw_entry.get("skillId")
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
    container_types = (set, frozenset, list, tuple)
    if not isinstance(poll.held_repos, container_types):
        raise PayloadError("poll.held_repos must be a set, frozenset, list, or tuple")
    if not isinstance(poll.held_named_ids, container_types):
        raise PayloadError("poll.held_named_ids must be a set, frozenset, list, or tuple")
    if not isinstance(poll.unavailable_named_ids, container_types):
        raise PayloadError("poll.unavailable_named_ids must be a set, frozenset, list, or tuple")

    held_repos: set[str] = set()
    for repo in poll.held_repos:
        held_repos.add(envelope.repository(repo))
    held_named: set[str] = set()
    for named_id in poll.held_named_ids:
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise PayloadError(f"invalid held_named_ids entry: {named_id!r}")
        held_named.add(named_id)
    unavailable_named: set[str] = set()
    for named_id in poll.unavailable_named_ids:
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise PayloadError(f"invalid unavailable_named_ids entry: {named_id!r}")
        unavailable_named.add(named_id)
    return frozenset(held_repos), frozenset(held_named), frozenset(unavailable_named)


def _match_current_candidates(
    repo: str,
    raw_obs: Mapping[str, Any],
    planned_finding: Mapping[str, Any],
) -> frozenset[str]:
    """Derive current present candidate row IDs from explicit raw ``componentAdds``.

    Verifies exact compatibility with the validated canonical finding's
    ``componentAdds`` and ``candidates`` rows using the shared producer rule
    (``<repo>:<slug>`` with exact slug match). Retained canonical rows not in
    raw ``componentAdds`` are permitted and excluded from the returned set.
    """
    raw_adds = raw_obs["componentAdds"]
    planned_adds = planned_finding["componentAdds"]
    if set(raw_adds) != set(planned_adds):
        raise PayloadError("raw componentAdds disagrees with canonical finding componentAdds")

    by_slug: dict[str, dict[str, Any]] = {}
    for row in planned_finding["candidates"]:
        by_slug[row["slug"]] = row

    present_ids: set[str] = set()
    for slug in raw_adds:
        row = by_slug.get(slug)
        if row is None:
            raise PayloadError(f"raw componentAdd {slug!r} is missing from canonical candidates")
        row_repo, sep, row_slug = row["id"].partition(":")
        if not sep or row_repo.lower() != repo or row_slug != slug:
            raise PayloadError(f"canonical candidate row id {row['id']!r} disagrees with ({repo}, {slug})")
        present_ids.add(row["id"])
    return frozenset(present_ids)


def _check_pin_continuity(prior: NamedBucket, planned_finding: Mapping[str, Any]) -> None:
    """Reject any incoming canonical row whose pin contradicts prior authoritative state."""
    for row in planned_finding["candidates"]:
        old_row = prior.rows.get(row["id"])
        if old_row is None:
            continue
        pin = old_row.first_seen_pin
        if row["firstSeenVersion"] != pin.first_seen_version or row["evidenceUrl"] != pin.evidence_url:
            raise PayloadError(
                f"pin conflict for {row['id']}: prior=({pin.first_seen_version}, {pin.evidence_url}) "
                f"!= incoming=({row['firstSeenVersion']}, {row['evidenceUrl']})"
            )


# ---------------------------------------------------------------------------
# Pure reducer
# ---------------------------------------------------------------------------


def _fold_bucket(
    prior: NamedBucket | None,
    repo: str,
    named_id: str,
    finding: dict[str, Any],
    current_present_row_ids: frozenset[str],
    verified_present_slugs: frozenset[str] | None,
    poll_id: str,
    observed_at_iso: str,
) -> NamedBucket:
    """Fold one verified joined observation into its exact ``(repo, named_id)`` bucket."""
    version = finding["newVersion"]
    source_url = finding["sourceUrl"]
    released_at = finding["releasedAt"]
    finding_sha256 = finding["payloadSha256"]

    incoming_by_id = {row["id"]: copy.deepcopy(row) for row in finding["candidates"]}
    next_rows: dict[str, RowHistory] = {}

    if prior is None:
        for row_id, row in sorted(incoming_by_id.items()):
            if row_id in current_present_row_ids:
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
                    historical_only=False,
                    presence=PRESENCE_PRESENT_CANDIDATE,
                )
            else:
                # Retained canonical row omitted by current raw componentAdds:
                # keep in canonical view without fabricating a current sighting or prior timestamp.
                pin = FirstSeenPin(
                    first_seen_version=row["firstSeenVersion"],
                    evidence_url=row["evidenceUrl"],
                    first_seen_at=None,
                    first_seen_poll_id=None,
                )
                presence = (
                    PRESENCE_PRESENT_TRACKED
                    if verified_present_slugs is not None and row["slug"] in verified_present_slugs
                    else PRESENCE_UNKNOWN
                )
                next_rows[row_id] = RowHistory(
                    row_id=row_id,
                    slug=row["slug"],
                    suggested_id=row["suggestedId"],
                    first_seen_pin=pin,
                    last_seen_version=row["lastSeenVersion"],
                    last_seen_at=None,
                    last_seen_poll_id=None,
                    present_in_latest=False,
                    vanished_at=None,
                    vanished_poll_id=None,
                    latest_row=row,
                    historical_only=True,
                    presence=presence,
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
            latest_finding=copy.deepcopy(finding),
            latest_finding_sha256=finding_sha256,
            versions_seen=versions_seen,
            rows=next_rows,
        )

    # Existing bucket: pin continuity has already been verified.
    for row_id, row in sorted(incoming_by_id.items()):
        old_row = prior.rows.get(row_id)
        if row_id in current_present_row_ids:
            if old_row is not None:
                if old_row.historical_only or old_row.first_seen_pin.first_seen_at is None:
                    # Transitioning from historical-only to first actual reducer observation:
                    # preserve canonical version/URL pin while recording this poll's real first_seen_at/poll_id.
                    pin = FirstSeenPin(
                        first_seen_version=old_row.first_seen_pin.first_seen_version,
                        evidence_url=old_row.first_seen_pin.evidence_url,
                        first_seen_at=observed_at_iso,
                        first_seen_poll_id=poll_id,
                    )
                else:
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
                historical_only=False,
                presence=PRESENCE_PRESENT_CANDIDATE,
            )
        elif old_row is not None and not old_row.historical_only:
            # Previously observed row omitted from raw componentAdds:
            # only a qualified scoped complete inventory can prove tracked presence or absence.
            if verified_present_slugs is not None:
                if old_row.slug in verified_present_slugs:
                    presence = PRESENCE_PRESENT_TRACKED
                    vanished_at = None
                    vanished_poll_id = None
                else:
                    presence = PRESENCE_VANISHED
                    vanished_at = old_row.vanished_at or observed_at_iso
                    vanished_poll_id = old_row.vanished_poll_id or poll_id
            else:
                presence = PRESENCE_UNKNOWN
                vanished_at = old_row.vanished_at
                vanished_poll_id = old_row.vanished_poll_id
            next_rows[row_id] = RowHistory(
                row_id=old_row.row_id,
                slug=old_row.slug,
                suggested_id=old_row.suggested_id,
                first_seen_pin=old_row.first_seen_pin,
                last_seen_version=old_row.last_seen_version,
                last_seen_at=old_row.last_seen_at,
                last_seen_poll_id=old_row.last_seen_poll_id,
                present_in_latest=False,
                vanished_at=vanished_at,
                vanished_poll_id=vanished_poll_id,
                latest_row=row,
                historical_only=False,
                presence=presence,
            )
        elif old_row is not None:
            # Still historical-only: never observed as current raw candidate by this reducer.
            presence = (
                PRESENCE_PRESENT_TRACKED
                if verified_present_slugs is not None and old_row.slug in verified_present_slugs
                else PRESENCE_UNKNOWN
            )
            next_rows[row_id] = RowHistory(
                row_id=old_row.row_id,
                slug=old_row.slug,
                suggested_id=old_row.suggested_id,
                first_seen_pin=old_row.first_seen_pin,
                last_seen_version=row["lastSeenVersion"],
                last_seen_at=None,
                last_seen_poll_id=None,
                present_in_latest=False,
                vanished_at=None,
                vanished_poll_id=None,
                latest_row=row,
                historical_only=True,
                presence=presence,
            )
        else:
            # Newly encountered historical-only row in canonical candidates.
            pin = FirstSeenPin(
                first_seen_version=row["firstSeenVersion"],
                evidence_url=row["evidenceUrl"],
                first_seen_at=None,
                first_seen_poll_id=None,
            )
            presence = (
                PRESENCE_PRESENT_TRACKED
                if verified_present_slugs is not None and row["slug"] in verified_present_slugs
                else PRESENCE_UNKNOWN
            )
            next_rows[row_id] = RowHistory(
                row_id=row_id,
                slug=row["slug"],
                suggested_id=row["suggestedId"],
                first_seen_pin=pin,
                last_seen_version=row["lastSeenVersion"],
                last_seen_at=None,
                last_seen_poll_id=None,
                present_in_latest=False,
                vanished_at=None,
                vanished_poll_id=None,
                latest_row=row,
                historical_only=True,
                presence=presence,
            )

    for row_id, old_row in sorted(prior.rows.items()):
        if row_id in next_rows:
            continue
        if old_row.historical_only:
            presence = (
                PRESENCE_PRESENT_TRACKED
                if verified_present_slugs is not None and old_row.slug in verified_present_slugs
                else PRESENCE_UNKNOWN
            )
            next_rows[row_id] = RowHistory(
                row_id=old_row.row_id,
                slug=old_row.slug,
                suggested_id=old_row.suggested_id,
                first_seen_pin=old_row.first_seen_pin,
                last_seen_version=old_row.last_seen_version,
                last_seen_at=old_row.last_seen_at,
                last_seen_poll_id=old_row.last_seen_poll_id,
                present_in_latest=False,
                vanished_at=None,
                vanished_poll_id=None,
                latest_row=copy.deepcopy(old_row.latest_row),
                historical_only=True,
                presence=presence,
            )
        else:
            if verified_present_slugs is not None:
                if old_row.slug in verified_present_slugs:
                    presence = PRESENCE_PRESENT_TRACKED
                    vanished_at = None
                    vanished_poll_id = None
                else:
                    presence = PRESENCE_VANISHED
                    vanished_at = old_row.vanished_at or observed_at_iso
                    vanished_poll_id = old_row.vanished_poll_id or poll_id
            else:
                presence = PRESENCE_UNKNOWN
                vanished_at = old_row.vanished_at
                vanished_poll_id = old_row.vanished_poll_id
            next_rows[row_id] = RowHistory(
                row_id=old_row.row_id,
                slug=old_row.slug,
                suggested_id=old_row.suggested_id,
                first_seen_pin=old_row.first_seen_pin,
                last_seen_version=old_row.last_seen_version,
                last_seen_at=old_row.last_seen_at,
                last_seen_poll_id=old_row.last_seen_poll_id,
                present_in_latest=False,
                vanished_at=vanished_at,
                vanished_poll_id=vanished_poll_id,
                latest_row=copy.deepcopy(old_row.latest_row),
                historical_only=False,
                presence=presence,
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
        latest_finding=copy.deepcopy(finding),
        latest_finding_sha256=finding_sha256,
        versions_seen=tuple(updated_versions),
        rows=next_rows,
    )


def _decision_for_observed_bucket(
    bucket: NamedBucket,
    raw_obs: Mapping[str, Any],
    authority: Mapping[str, Any],
    poll_id: str,
    observed_at_dt: dt.datetime,
    observed_at_iso: str,
    config: ReducerConfig,
) -> NamedDecision:
    pending_dt = parse_strict_utc(bucket.pending_since)
    deadline_dt = pending_dt + dt.timedelta(days=config.window_days)
    urgent = urgent_reasons(raw_obs, bucket.latest_finding, bucket.named_id, authority)
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
        historical_row_ids=bucket.historical_row_ids,
        tracked_present_row_ids=bucket.tracked_present_row_ids,
        unknown_presence_row_ids=bucket.unknown_presence_row_ids,
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
        historical_row_ids=bucket.historical_row_ids,
        tracked_present_row_ids=bucket.tracked_present_row_ids,
        unknown_presence_row_ids=bucket.unknown_presence_row_ids,
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
        state=_clone_state(state),
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
    """Purely reduce one dual-evidence offline poll snapshot against *state* and *authority*.

    Guarantees:
    * Exact replay of an already-seen ``poll_id`` with identical timestamp,
      both evidence tracks, and hold/scope sets is an idempotent no-op
      (``status="replayed"``, isolated state clone, ``eligible=()``).
    * Conflicting reuse of an existing ``poll_id``, stale ``observed_at``,
      malformed poll containers, or ``complete=False`` fails closed
      (``status="rejected"``, isolated state clone, ``eligible=()``).
    * Every accepted scope requires an exact verified join between raw
      ``observed_findings`` and canonical ``planned_findings``. Retained
      canonical siblings without current raw observations are history only.
    * Pin conflicts, missing canonical matches, or malformed/conflicting
      observations reject only the affected scope without raising uncaught
      exceptions and without disturbing unrelated repositories or siblings.
    * Eligibility is evaluated per exact ``(repository, named_id)`` ONLY for
      validly joined, unheld, available buckets from THIS actual poll.
    * ``write_authorized`` is always ``False``.
    """
    if not isinstance(state, ReducerState):
        raise TypeError("state must be a ReducerState")
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        return _rejected_poll(state, "config must be a ReducerConfig")
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

    if not isinstance(poll.observed_findings, (list, tuple)):
        return _rejected_poll(
            state,
            "poll.observed_findings must be a list or tuple",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )
    if not isinstance(poll.planned_findings, (list, tuple)):
        return _rejected_poll(
            state,
            "poll.planned_findings must be a list or tuple",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )

    try:
        held_repos, held_named_ids, unavailable_named_ids = _normalize_scope_sets(poll)
        serialized_inventories = _serialize_complete_inventories(poll.complete_inventories)
    except (PayloadError, TypeError, ValueError) as exc:
        return _rejected_poll(state, str(exc), poll_id=poll_id, observed_at=observed_at_iso)

    # Canonical input digest covering both evidence tracks, complete-inventory seam, and all hold/scope sets.
    try:
        input_digest = _canonical_json_digest(
            {
                "poll_id": poll_id,
                "observed_at": observed_at_iso,
                "complete": poll.complete,
                "held_repos": sorted(held_repos),
                "held_named_ids": sorted(held_named_ids),
                "unavailable_named_ids": sorted(unavailable_named_ids),
                "observed_findings": list(poll.observed_findings),
                "planned_findings": list(poll.planned_findings),
                "complete_inventories": serialized_inventories,
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
            cloned = _clone_state(state)
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
                for scope, bucket in sorted(cloned.buckets.items())
            }
            return PollReductionResult(
                status="replayed",
                state=cloned,
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

    if len(state.seen_polls) >= cfg.max_seen_polls:
        return _rejected_poll(
            state,
            f"resource budget exceeded: seen_polls limit ({cfg.max_seen_polls}) reached",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )

    # 1. Validate raw observed findings independently.
    raw_by_scope: dict[tuple[str, str], tuple[int, str, dict[str, Any]]] = {}
    conflicting_raw_scopes: set[tuple[str, str]] = set()
    rejected_observations: list[RejectedObservation] = []
    rejected_scopes: set[tuple[str, str]] = set()

    for idx, raw_obs in enumerate(poll.observed_findings):
        try:
            repo, named_id, finding_kind, obs = _validate_raw_observation(raw_obs, authority)
        except (PayloadError, GhError, TypeError, ValueError, KeyError) as exc:
            best_repo, best_named = _best_effort_scope(raw_obs, authority)
            rejected_observations.append(
                RejectedObservation(index=idx, named_id=best_named, repository=best_repo, reason=str(exc))
            )
            if best_repo is not None and best_named is not None:
                rejected_scopes.add((best_repo, best_named))
            continue

        scope = (repo, named_id)
        if scope in conflicting_raw_scopes:
            rejected_observations.append(
                RejectedObservation(
                    index=idx,
                    named_id=named_id,
                    repository=repo,
                    reason="conflicting duplicate raw observation for same (repository, named_id) in poll",
                )
            )
            continue

        existing_raw = raw_by_scope.get(scope)
        if existing_raw is not None:
            if existing_raw[1] != finding_kind or existing_raw[2] != obs:
                del raw_by_scope[scope]
                conflicting_raw_scopes.add(scope)
                rejected_scopes.add(scope)
                rejected_observations.append(
                    RejectedObservation(
                        index=idx,
                        named_id=named_id,
                        repository=repo,
                        reason="conflicting duplicate raw observation for same (repository, named_id) in poll",
                    )
                )
            continue
        raw_by_scope[scope] = (idx, finding_kind, obs)

    # 2. Validate canonical planned findings independently.
    planned_by_scope: dict[tuple[str, str], tuple[int, str, dict[str, Any]]] = {}
    conflicting_planned_scopes: set[tuple[str, str]] = set()

    for idx, raw_planned in enumerate(poll.planned_findings):
        try:
            repo, named_id, finding_kind, finding = _validate_planned_finding(raw_planned, authority)
        except (PayloadError, GhError, TypeError, ValueError, KeyError) as exc:
            best_repo, best_named = _best_effort_scope(raw_planned, authority)
            rejected_observations.append(
                RejectedObservation(index=idx, named_id=best_named, repository=best_repo, reason=str(exc))
            )
            if best_repo is not None and best_named is not None:
                rejected_scopes.add((best_repo, best_named))
            continue

        scope = (repo, named_id)
        if scope in conflicting_planned_scopes:
            rejected_observations.append(
                RejectedObservation(
                    index=idx,
                    named_id=named_id,
                    repository=repo,
                    reason="conflicting duplicate canonical finding for same (repository, named_id) in poll",
                )
            )
            continue

        existing_planned = planned_by_scope.get(scope)
        if existing_planned is not None:
            if existing_planned[1] != finding_kind or existing_planned[2] != finding:
                del planned_by_scope[scope]
                conflicting_planned_scopes.add(scope)
                rejected_scopes.add(scope)
                rejected_observations.append(
                    RejectedObservation(
                        index=idx,
                        named_id=named_id,
                        repository=repo,
                        reason="conflicting duplicate canonical finding for same (repository, named_id) in poll",
                    )
                )
            continue
        planned_by_scope[scope] = (idx, finding_kind, finding)

    # 3. Checked join: ONLY scopes explicitly present in raw observed_findings
    #    can advance history or become eligible. Retained canonical siblings not
    #    present in observed_findings are history only.
    joined_by_scope: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any], frozenset[str]]] = {}
    held_incoming_scopes: set[tuple[str, str]] = set()
    unavailable_incoming_scopes: set[tuple[str, str]] = set()

    for scope in sorted(raw_by_scope):
        repo, named_id = scope
        raw_idx, raw_kind, raw_obs = raw_by_scope[scope]

        if named_id in unavailable_named_ids:
            unavailable_incoming_scopes.add(scope)
            continue
        if repo in held_repos or named_id in held_named_ids:
            held_incoming_scopes.add(scope)
            continue
        if scope in rejected_scopes:
            continue

        planned_entry = planned_by_scope.get(scope)
        if planned_entry is None:
            rejected_observations.append(
                RejectedObservation(
                    index=raw_idx,
                    named_id=named_id,
                    repository=repo,
                    reason="missing canonical planned finding for observed scope",
                )
            )
            rejected_scopes.add(scope)
            continue

        _planned_idx, planned_kind, planned_finding = planned_entry
        raw_join_key = (repo, named_id, raw_obs["sourceUrl"], raw_obs["newVersion"], raw_kind)
        planned_join_key = (repo, named_id, planned_finding["sourceUrl"], planned_finding["newVersion"], planned_kind)
        if raw_join_key != planned_join_key:
            rejected_observations.append(
                RejectedObservation(
                    index=raw_idx,
                    named_id=named_id,
                    repository=repo,
                    reason=(
                        f"raw/canonical join mismatch for ({repo}, {named_id}): "
                        f"raw={raw_join_key[2:]} != canonical={planned_join_key[2:]}"
                    ),
                )
            )
            rejected_scopes.add(scope)
            continue

        try:
            current_present_row_ids = _match_current_candidates(repo, raw_obs, planned_finding)
        except PayloadError as exc:
            rejected_observations.append(
                RejectedObservation(index=raw_idx, named_id=named_id, repository=repo, reason=str(exc))
            )
            rejected_scopes.add(scope)
            continue

        joined_by_scope[scope] = (raw_obs, planned_finding, current_present_row_ids)

    # 3b. Index optional complete-inventory seam entries by normalized scope.
    #     Conflicting duplicate entries for the same scope are treated as unusable.
    inventories_by_scope: dict[tuple[str, str], ScopedCompleteInventory] = {}
    conflicting_inventory_scopes: set[tuple[str, str]] = set()
    for inv in poll.complete_inventories:
        try:
            inv_repo = envelope.repository(inv.repository)
        except PayloadError:
            continue
        inv_scope = (inv_repo, inv.named_id)
        if inv_scope in conflicting_inventory_scopes:
            continue
        existing_inv = inventories_by_scope.get(inv_scope)
        if existing_inv is not None:
            if existing_inv != inv:
                del inventories_by_scope[inv_scope]
                conflicting_inventory_scopes.add(inv_scope)
            continue
        inventories_by_scope[inv_scope] = inv

    # 4. Clone untouched prior buckets so returned state never aliases prior state.
    next_buckets: dict[tuple[str, str], NamedBucket] = {
        scope: _clone_bucket(bucket) for scope, bucket in sorted(state.buckets.items())
    }
    accepted_scopes: list[tuple[str, str]] = []
    decisions: dict[tuple[str, str], NamedDecision] = {}

    for scope in sorted(joined_by_scope):
        repo, named_id = scope
        raw_obs, planned_finding, current_present_row_ids = joined_by_scope[scope]
        prior = state.buckets.get(scope)
        if prior is not None:
            if observed_at_dt < parse_strict_utc(prior.last_observed_at):
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
            try:
                _check_pin_continuity(prior, planned_finding)
            except PayloadError as exc:
                rejected_observations.append(
                    RejectedObservation(index=-1, named_id=named_id, repository=repo, reason=str(exc))
                )
                rejected_scopes.add(scope)
                continue

        verified_present_slugs: frozenset[str] | None = None
        candidate_inv = inventories_by_scope.get(scope)
        if candidate_inv is not None:
            verified_present_slugs, _inv_reason = qualify_complete_inventory(
                candidate_inv,
                poll_id=poll_id,
                repository=repo,
                named_id=named_id,
                raw_obs=raw_obs,
                authority=authority,
            )

        folded = _fold_bucket(
            prior,
            repo,
            named_id,
            planned_finding,
            current_present_row_ids,
            verified_present_slugs,
            poll_id,
            observed_at_iso,
        )
        next_buckets[scope] = folded
        accepted_scopes.append(scope)
        decisions[scope] = _decision_for_observed_bucket(
            folded,
            raw_obs,
            authority,
            poll_id,
            observed_at_dt,
            observed_at_iso,
            cfg,
        )

    # 4b. Enforce explicit aggregate resource contract fail-closed BEFORE committing state.
    if len(next_buckets) > cfg.max_buckets:
        return _rejected_poll(
            state,
            f"resource budget exceeded: buckets limit ({cfg.max_buckets}) exceeded",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )
    total_rows = 0
    for scope, bucket in sorted(next_buckets.items()):
        if len(bucket.rows) > cfg.max_rows_per_bucket:
            return _rejected_poll(
                state,
                f"resource budget exceeded: rows_per_bucket limit ({cfg.max_rows_per_bucket}) exceeded for {scope}",
                poll_id=poll_id,
                observed_at=observed_at_iso,
            )
        if len(bucket.versions_seen) > cfg.max_versions_per_bucket:
            return _rejected_poll(
                state,
                f"resource budget exceeded: versions_per_bucket limit ({cfg.max_versions_per_bucket}) exceeded for {scope}",
                poll_id=poll_id,
                observed_at=observed_at_iso,
            )
        total_rows += len(bucket.rows)
    if total_rows > cfg.max_total_rows:
        return _rejected_poll(
            state,
            f"resource budget exceeded: total_rows limit ({cfg.max_total_rows}) exceeded",
            poll_id=poll_id,
            observed_at=observed_at_iso,
        )

    # 5. Record explicit non-eligible decisions for existing buckets not accepted in
    #    this poll, plus incoming held/unavailable scopes without a prior bucket.
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
                historical_row_ids=(),
                tracked_present_row_ids=(),
                unknown_presence_row_ids=(),
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
        _clone_decision(decisions[scope])
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
