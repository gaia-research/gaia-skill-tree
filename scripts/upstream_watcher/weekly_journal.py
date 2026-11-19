"""Isolated local offline journal persistence for P2 named weekly observations (Slice 2).

Scope & Contract
----------------
This module implements ONLY local temp/file JSON codec, strict validation,
load/save/restore, and CAS checkpoint persistence for ``weekly_reducer.ReducerState``
under an independently versioned ``named-v3`` namespace.

* Separate namespace: ``format="gaia-upstream-weekly-named-journal"``,
  ``namespace="named-v3"``, ``journalVersion=3``. Existing legacy v2 staging
  journals (``staging.Journal``, ``schemaVersion=2``) and foreign JSON files
  are classified explicitly as blocked and are NEVER overwritten or reinterpreted.
* Single source of truth: reuses ``weekly_reducer`` state types/timestamps/caps,
  ``envelope.validate_named``, ``envelope.authority_repository``,
  ``envelope.release_repository``, and ``releaseidentity.validateReleaseSource``.
  Does not copy the reducer or build/seal repository envelopes.
* Integrity vs freshness: the embedded ``digest`` (SHA-256 over canonical JSON)
  detects corruption and accidental truncation only. It is NOT a security or
  write-authorization token and CANNOT prove freshness after an external cache
  restore. Callers requiring rollback protection must supply an externally
  persisted ``trusted_latest_pin`` (``JournalPin(revision, digest)``) on load.
* Fail-closed semantic validation: a checksum-valid file with contradictory
  fields (bool-as-int, duplicate JSON keys or scopes, wrong repository/sibling
  ``skillId``, missing ``seenPolls`` receipt references, non-canonical or
  out-of-order UTC timestamps, contradictory presence/historical flags, pin
  mismatch, or resource-cap overflow) is rejected as ``corrupt`` and never
  restored or overwritten.
* Local CAS & locking contract: cooperating local callers on a POSIX filesystem
  serialize updates through an advisory ``fcntl.flock`` lock on ``<path>.lock``,
  re-read and verify the on-disk ``JournalPin`` against ``expected_pin`` before
  writing, and commit via bounded temp-file write + ``fsync`` + ``os.replace``.
  Failed or oversized writes clean up the temp file and leave prior bytes
  untouched. This local lock does NOT provide distributed/cross-host locking or
  protect against uncooperative external writers.
* Out of scope: no GitHub transport, no issue writer or settlement API, no CLI
  or dispatcher integration, no complete-inventory producer wiring, and no
  migration or production namespace activation.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import quote, urlsplit

from scripts.upstream_watcher import envelope, weekly_reducer
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import GhError
from scripts.upstream_watcher.releaseidentity import validateReleaseSource
from scripts.upstream_watcher.weekly_reducer import (
    PRESENCE_PRESENT_CANDIDATE,
    PRESENCE_PRESENT_TRACKED,
    PRESENCE_UNKNOWN,
    PRESENCE_VANISHED,
    FirstSeenPin,
    NamedBucket,
    PollInput,
    PollReceipt,
    PollReductionResult,
    ReducerConfig,
    ReducerState,
    RowHistory,
    VersionSighting,
    empty_state,
    format_utc,
    parse_strict_utc,
    reduce_poll,
)

JOURNAL_FORMAT = "gaia-upstream-weekly-named-journal"
JOURNAL_NAMESPACE = "named-v3"
JOURNAL_VERSION = 3
DEFAULT_MAX_JOURNAL_BYTES = 8 * 1024 * 1024

STATUS_OK = "ok"
STATUS_BOOTSTRAP = "bootstrap"
STATUS_MISSING = "missing"
STATUS_LOST = "lost"
STATUS_CORRUPT = "corrupt"
STATUS_LEGACY_V2 = "legacy-v2"
STATUS_FOREIGN = "foreign"
STATUS_STALE = "stale"

USABLE_STATUSES = frozenset({STATUS_OK, STATUS_BOOTSTRAP})
BLOCKED_STATUSES = frozenset(
    {
        STATUS_MISSING,
        STATUS_LOST,
        STATUS_CORRUPT,
        STATUS_LEGACY_V2,
        STATUS_FOREIGN,
        STATUS_STALE,
    }
)

_VALID_PRESENCE = frozenset(
    {
        PRESENCE_PRESENT_CANDIDATE,
        PRESENCE_PRESENT_TRACKED,
        PRESENCE_UNKNOWN,
        PRESENCE_VANISHED,
    }
)
_VALID_CANDIDATE_STATUSES = frozenset({"new", "tracked", "present", "rejected", "escalated"})
_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_MAX_JSON_DEPTH = 64
_MAX_JSON_INT_DIGITS = 128
_MAX_JSON_FLOAT_CHARS = 128

_TOP_LEVEL_KEYS = frozenset(
    {
        "format",
        "namespace",
        "journalVersion",
        "reducerSchemaVersion",
        "revision",
        "lastObservedAt",
        "lastPollId",
        "seenPolls",
        "buckets",
        "digest",
    }
)
_POLL_RECEIPT_KEYS = frozenset({"pollId", "observedAt", "complete", "inputDigest"})
_BUCKET_KEYS = frozenset(
    {
        "repository",
        "namedId",
        "pendingSince",
        "firstPollId",
        "lastObservedAt",
        "lastPollId",
        "sightingCount",
        "revision",
        "latestFindingSha256",
        "latestFinding",
        "versionsSeen",
        "rows",
    }
)
_VERSION_SIGHTING_KEYS = frozenset(
    {
        "version",
        "sourceUrl",
        "releasedAt",
        "findingSha256",
        "firstObservedAt",
        "lastObservedAt",
        "firstPollId",
        "lastPollId",
    }
)
_ROW_KEYS = frozenset(
    {
        "rowId",
        "slug",
        "suggestedId",
        "firstSeenPin",
        "lastSeenVersion",
        "lastSeenAt",
        "lastSeenPollId",
        "presentInLatest",
        "vanishedAt",
        "vanishedPollId",
        "historicalOnly",
        "presence",
        "latestRow",
    }
)
_PIN_KEYS = frozenset({"firstSeenVersion", "evidenceUrl", "firstSeenAt", "firstSeenPollId"})
_REQUIRED_CANONICAL_FINDING_KEYS = (
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


# ---------------------------------------------------------------------------
# Exceptions & public handles
# ---------------------------------------------------------------------------


class JournalError(RuntimeError):
    """Base error for local named-v3 journal persistence."""


class JournalValidationError(JournalError):
    """Raised when a journal payload or ReducerState fails strict validation."""


class JournalBlockedError(JournalError):
    """Raised when an operation refuses to overwrite or advance blocked state."""


class JournalConflictError(JournalError):
    """Raised on CAS pin mismatch or bootstrap collision against existing state."""


class JournalSizeError(JournalError):
    """Raised when serialized or on-disk journal bytes exceed configured bounds."""


@dataclass(frozen=True)
class JournalPin:
    """Explicit checkpoint identity for CAS updates and external freshness checks.

    A journal's embedded ``digest`` proves internal integrity only, NOT freshness
    relative to an external cache restore. Callers needing rollback protection
    must pass an externally persisted ``JournalPin`` as ``trusted_latest_pin``.
    """

    revision: int
    digest: str

    def __post_init__(self) -> None:
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("JournalPin.revision must be a non-negative integer")
        if not isinstance(self.digest, str) or not envelope.SHA.fullmatch(self.digest):
            raise ValueError("JournalPin.digest must be a 64-character lowercase hex SHA-256")


@dataclass(frozen=True)
class JournalHandle:
    """Immutable load/save receipt and provenance for a local named-v3 journal."""

    path: Path
    status: str
    detail: str
    state: ReducerState | None
    pin: JournalPin | None
    byte_size: int | None
    namespace: str | None
    loaded_at_revision: int | None
    existed: bool

    @property
    def usable(self) -> bool:
        return self.status in USABLE_STATUSES and self.state is not None

    @property
    def blocked(self) -> bool:
        return not self.usable


@dataclass(frozen=True)
class JournalCommitResult:
    """Result of one locked load -> ``reduce_poll`` -> atomic save transition."""

    handle: JournalHandle
    reduction: PollReductionResult
    persisted: bool


# ---------------------------------------------------------------------------
# Strict scalar, JSON, digest & cloning helpers
# ---------------------------------------------------------------------------


def _is_clean_str(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
    )


def _require_clean_str(value: Any, label: str) -> str:
    if not _is_clean_str(value):
        raise JournalValidationError(f"{label} must be a non-empty string without whitespace or control characters")
    return value


def _require_canonical_utc(value: Any, label: str) -> tuple[str, Any]:
    if not isinstance(value, str):
        raise JournalValidationError(f"{label} must be a canonical UTC RFC3339 string")
    try:
        parsed = parse_strict_utc(value)
    except ValueError as exc:
        raise JournalValidationError(f"{label} is not a valid UTC timestamp") from exc
    canonical = format_utc(parsed)
    if canonical != value:
        raise JournalValidationError(f"{label} must be in canonical UTC format")
    return canonical, parsed


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not envelope.SHA.fullmatch(value):
        raise JournalValidationError(f"{label} must be a 64-character lowercase hex SHA-256")
    return value


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise JournalValidationError(f"{label} must be an integer >= {minimum}")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise JournalValidationError(f"{label} must be a boolean")
    return value


def _unique_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JournalValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_non_finite(constant: str) -> Any:
    raise JournalValidationError(f"non-finite JSON constant is not allowed: {constant!r}")


def _parse_bounded_int(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    if len(digits) > _MAX_JSON_INT_DIGITS:
        raise JournalValidationError(f"JSON integer exceeds maximum length ({_MAX_JSON_INT_DIGITS} digits)")
    return int(token)


def _parse_bounded_float(token: str) -> float:
    if len(token) > _MAX_JSON_FLOAT_CHARS:
        raise JournalValidationError(f"JSON float exceeds maximum length ({_MAX_JSON_FLOAT_CHARS} characters)")
    value = float(token)
    if not math.isfinite(value):
        raise JournalValidationError("non-finite JSON float is not allowed")
    return value


def _validate_json_depth(root: Any, *, max_depth: int = _MAX_JSON_DEPTH) -> None:
    stack: list[tuple[Any, int]] = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, dict):
            if depth > max_depth:
                raise JournalValidationError(f"JSON nesting depth exceeds maximum ({max_depth})")
            for value in node.values():
                if isinstance(value, (dict, list)):
                    stack.append((value, depth + 1))
        elif isinstance(node, list):
            if depth > max_depth:
                raise JournalValidationError(f"JSON nesting depth exceeds maximum ({max_depth})")
            for item in node:
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))


def _journal_digest(body: Mapping[str, Any]) -> str:
    without_digest = {key: value for key, value in body.items() if key != "digest"}
    try:
        encoded = json.dumps(
            without_digest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise JournalValidationError(f"journal payload is not strict JSON: {exc}") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _clone_state(state: ReducerState) -> ReducerState:
    return ReducerState(
        schema_version=state.schema_version,
        revision=state.revision,
        last_observed_at=state.last_observed_at,
        last_poll_id=state.last_poll_id,
        buckets={
            scope: NamedBucket(
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
                rows={
                    rid: RowHistory(
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
                    for rid, row in sorted(bucket.rows.items())
                },
            )
            for scope, bucket in sorted(state.buckets.items())
        },
        seen_polls=dict(state.seen_polls),
    )


def _validate_evidence_url(url: Any, repo: str, first_seen_version: str) -> str:
    if not isinstance(url, str) or not url or any(ord(c) < 32 or ord(c) == 127 for c in url):
        raise JournalValidationError("candidate evidenceUrl is missing or malformed")
    parts = urlsplit(url)
    segments = parts.path.split("/")
    if (
        parts.scheme != "https"
        or parts.netloc.lower() != "github.com"
        or parts.query
        or parts.fragment
        or len(segments) < 7
        or "/".join(segments[1:3]).lower() != repo
        or segments[3:5] != ["blob", quote(first_seen_version, safe="")]
        or segments[-1] != "SKILL.md"
    ):
        raise JournalValidationError("candidate evidenceUrl is not pinned to its repository and firstSeenVersion")
    return url


def _validate_liveness_and_drift(finding: Mapping[str, Any]) -> None:
    liveness = finding.get("linkLiveness")
    if not isinstance(liveness, list):
        raise JournalValidationError("latestFinding.linkLiveness must be a list")
    for entry in liveness:
        if not isinstance(entry, dict):
            raise JournalValidationError("malformed linkLiveness entry in latestFinding")
        skill_id = entry.get("skillId")
        url = entry.get("url")
        status = entry.get("status")
        if not isinstance(skill_id, str) or not skill_id or not isinstance(url, str) or not url:
            raise JournalValidationError("malformed linkLiveness entry fields in latestFinding")
        if not (status == "network_error" or (type(status) is int and 100 <= status <= 599)):
            raise JournalValidationError("malformed linkLiveness status in latestFinding")

    name_drift = finding.get("nameDrift")
    if not isinstance(name_drift, list):
        raise JournalValidationError("latestFinding.nameDrift must be a list")
    for entry in name_drift:
        if not isinstance(entry, dict):
            raise JournalValidationError("malformed nameDrift entry in latestFinding")
        skill_id = entry.get("skillId")
        if not isinstance(skill_id, str) or not skill_id:
            raise JournalValidationError("malformed nameDrift entry fields in latestFinding")


def _validate_candidate_row_dict(
    latest_row: Any,
    *,
    repo: str,
    row_id: str,
    slug: str,
    suggested_id: str,
    first_seen_version: str,
    evidence_url: str,
) -> dict[str, Any]:
    if not isinstance(latest_row, dict):
        raise JournalValidationError("row.latestRow must be a JSON object")
    if "namedSkillId" in latest_row or "candidateId" in latest_row:
        raise JournalValidationError("row.latestRow must not carry repository-records wrapper fields")
    try:
        json.dumps(latest_row, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise JournalValidationError(f"row.latestRow is not strict JSON: {exc}") from exc

    if latest_row.get("id") != row_id:
        raise JournalValidationError("row.latestRow.id disagrees with rowId")
    if latest_row.get("slug") != slug:
        raise JournalValidationError("row.latestRow.slug disagrees with slug")
    if latest_row.get("suggestedId") != suggested_id:
        raise JournalValidationError("row.latestRow.suggestedId disagrees with suggestedId")
    status = latest_row.get("status")
    if not isinstance(status, str) or status not in _VALID_CANDIDATE_STATUSES:
        raise JournalValidationError("row.latestRow has invalid status")
    if latest_row.get("firstSeenVersion") != first_seen_version:
        raise JournalValidationError("row.latestRow.firstSeenVersion disagrees with firstSeenPin")
    if latest_row.get("evidenceUrl") != evidence_url:
        raise JournalValidationError("row.latestRow.evidenceUrl disagrees with firstSeenPin")
    _require_clean_str(latest_row.get("lastSeenVersion"), "row.latestRow.lastSeenVersion")
    child = latest_row.get("child")
    if child is not None and (type(child) is not int or child < 1):
        raise JournalValidationError("row.latestRow.child must be None or a positive integer")
    if "precheck" in latest_row and not isinstance(latest_row["precheck"], dict):
        raise JournalValidationError("row.latestRow.precheck must be a JSON object")
    return copy.deepcopy(latest_row)


def is_legacy_v2_payload(data: Any) -> bool:
    """Return True when *data* matches the legacy v2 staging journal shape."""
    if not isinstance(data, dict):
        return False
    if data.get("format") == JOURNAL_FORMAT or data.get("namespace") == JOURNAL_NAMESPACE:
        return False
    return type(data.get("schemaVersion")) is int and data["schemaVersion"] == 2 and isinstance(data.get("repos"), dict)


# ---------------------------------------------------------------------------
# Explicit named-v3 codec (encode / decode)
# ---------------------------------------------------------------------------


def encode_state(
    state: ReducerState,
    authority: Mapping[str, Mapping[str, Any]],
    *,
    config: ReducerConfig | None = None,
) -> dict[str, Any]:
    """Encode *state* into a deterministic, self-digested ``named-v3`` JSON object.

    Validates *state* through the same strict decoder invariants before returning,
    so contradictory or oversized states can never be persisted.
    """
    if not isinstance(state, ReducerState):
        raise JournalValidationError("state must be a ReducerState")
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        raise JournalValidationError("config must be a ReducerConfig")
    if not isinstance(authority, Mapping) or not authority:
        raise JournalValidationError("authority must be a non-empty mapping")

    seen_polls_list: list[dict[str, Any]] = []
    if not all(isinstance(k, str) for k in state.seen_polls):
        raise JournalValidationError("state.seen_polls keys must be strings")
    for poll_id in sorted(state.seen_polls):
        receipt = state.seen_polls[poll_id]
        if not isinstance(receipt, PollReceipt):
            raise JournalValidationError("state.seen_polls entries must be PollReceipt")
        if receipt.poll_id != poll_id:
            raise JournalValidationError("seen_polls key disagrees with receipt.poll_id")
        seen_polls_list.append(
            {
                "pollId": receipt.poll_id,
                "observedAt": receipt.observed_at,
                "complete": receipt.complete,
                "inputDigest": receipt.input_digest,
            }
        )

    buckets_list: list[dict[str, Any]] = []
    for scope in state.buckets:
        if (
            not isinstance(scope, tuple)
            or len(scope) != 2
            or not isinstance(scope[0], str)
            or not isinstance(scope[1], str)
        ):
            raise JournalValidationError("state.buckets keys must be (repository, named_id) string tuples")
    for scope in sorted(state.buckets):
        bucket = state.buckets[scope]
        if not isinstance(bucket, NamedBucket):
            raise JournalValidationError("state.buckets values must be NamedBucket")
        if scope != (bucket.repository, bucket.named_id):
            raise JournalValidationError("state.buckets scope key disagrees with bucket (repository, named_id)")

        versions_list: list[dict[str, Any]] = []
        for seen in bucket.versions_seen:
            if not isinstance(seen, VersionSighting):
                raise JournalValidationError("bucket.versions_seen entries must be VersionSighting")
            versions_list.append(
                {
                    "version": seen.version,
                    "sourceUrl": seen.source_url,
                    "releasedAt": seen.released_at,
                    "findingSha256": seen.finding_sha256,
                    "firstObservedAt": seen.first_observed_at,
                    "lastObservedAt": seen.last_observed_at,
                    "firstPollId": seen.first_poll_id,
                    "lastPollId": seen.last_poll_id,
                }
            )

        rows_list: list[dict[str, Any]] = []
        if not all(isinstance(k, str) for k in bucket.rows):
            raise JournalValidationError("bucket.rows keys must be strings")
        for row_id in sorted(bucket.rows):
            row = bucket.rows[row_id]
            if not isinstance(row, RowHistory):
                raise JournalValidationError("bucket.rows values must be RowHistory")
            if row.row_id != row_id:
                raise JournalValidationError("bucket.rows key disagrees with row.row_id")
            if not isinstance(row.first_seen_pin, FirstSeenPin):
                raise JournalValidationError("row.first_seen_pin must be FirstSeenPin")
            rows_list.append(
                {
                    "rowId": row.row_id,
                    "slug": row.slug,
                    "suggestedId": row.suggested_id,
                    "firstSeenPin": {
                        "firstSeenVersion": row.first_seen_pin.first_seen_version,
                        "evidenceUrl": row.first_seen_pin.evidence_url,
                        "firstSeenAt": row.first_seen_pin.first_seen_at,
                        "firstSeenPollId": row.first_seen_pin.first_seen_poll_id,
                    },
                    "lastSeenVersion": row.last_seen_version,
                    "lastSeenAt": row.last_seen_at,
                    "lastSeenPollId": row.last_seen_poll_id,
                    "presentInLatest": row.present_in_latest,
                    "vanishedAt": row.vanished_at,
                    "vanishedPollId": row.vanished_poll_id,
                    "historicalOnly": row.historical_only,
                    "presence": row.presence,
                    "latestRow": copy.deepcopy(row.latest_row),
                }
            )

        buckets_list.append(
            {
                "repository": bucket.repository,
                "namedId": bucket.named_id,
                "pendingSince": bucket.pending_since,
                "firstPollId": bucket.first_poll_id,
                "lastObservedAt": bucket.last_observed_at,
                "lastPollId": bucket.last_poll_id,
                "sightingCount": bucket.sighting_count,
                "revision": bucket.revision,
                "latestFindingSha256": bucket.latest_finding_sha256,
                "latestFinding": copy.deepcopy(bucket.latest_finding),
                "versionsSeen": versions_list,
                "rows": rows_list,
            }
        )

    payload: dict[str, Any] = {
        "format": JOURNAL_FORMAT,
        "namespace": JOURNAL_NAMESPACE,
        "journalVersion": JOURNAL_VERSION,
        "reducerSchemaVersion": state.schema_version,
        "revision": state.revision,
        "lastObservedAt": state.last_observed_at,
        "lastPollId": state.last_poll_id,
        "seenPolls": seen_polls_list,
        "buckets": buckets_list,
    }
    payload["digest"] = _journal_digest(payload)

    # Round-trip validate through the exact decoder before returning.
    decode_state(payload, authority, config=cfg)
    return payload


def serialize_state(
    state: ReducerState,
    authority: Mapping[str, Mapping[str, Any]],
    *,
    config: ReducerConfig | None = None,
    max_bytes: int = DEFAULT_MAX_JOURNAL_BYTES,
) -> tuple[bytes, JournalPin]:
    """Encode *state* to deterministic UTF-8 JSON bytes and return ``(bytes, JournalPin)``."""
    _require_int(max_bytes, "max_bytes", minimum=1)
    payload = encode_state(state, authority, config=config)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    raw = text.encode("utf-8")
    if len(raw) > max_bytes:
        raise JournalSizeError(f"encoded journal size ({len(raw)} bytes) exceeds max_bytes ({max_bytes})")
    return raw, JournalPin(revision=payload["revision"], digest=payload["digest"])


def decode_state(
    data: Any,
    authority: Mapping[str, Mapping[str, Any]],
    *,
    config: ReducerConfig | None = None,
) -> tuple[ReducerState, JournalPin]:
    """Strictly validate and decode a ``named-v3`` JSON object into ``(ReducerState, JournalPin)``.

    Rejects checksum-valid but semantically contradictory payloads with
    ``JournalValidationError``.
    """
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        raise JournalValidationError("config must be a ReducerConfig")
    if not isinstance(authority, Mapping) or not authority:
        raise JournalValidationError("authority must be a non-empty mapping")
    if not isinstance(data, dict):
        raise JournalValidationError("journal root must be a JSON object")
    _validate_json_depth(data)
    if set(data.keys()) != _TOP_LEVEL_KEYS:
        raise JournalValidationError("journal root has unexpected or missing keys")

    if data["format"] != JOURNAL_FORMAT:
        raise JournalValidationError("unexpected journal format")
    if data["namespace"] != JOURNAL_NAMESPACE:
        raise JournalValidationError("unexpected journal namespace")
    if _require_int(data["journalVersion"], "journalVersion", minimum=1) != JOURNAL_VERSION:
        raise JournalValidationError("unexpected journalVersion")
    reducer_schema = _require_int(data["reducerSchemaVersion"], "reducerSchemaVersion", minimum=1)
    if reducer_schema != weekly_reducer.SCHEMA_VERSION:
        raise JournalValidationError("unexpected reducerSchemaVersion")

    stored_digest = _require_sha256(data["digest"], "digest")
    computed_digest = _journal_digest(data)
    if stored_digest != computed_digest:
        raise JournalValidationError("journal digest mismatch")

    revision = _require_int(data["revision"], "revision", minimum=0)
    raw_seen_polls = data["seenPolls"]
    raw_buckets = data["buckets"]
    if not isinstance(raw_seen_polls, list):
        raise JournalValidationError("seenPolls must be a list")
    if not isinstance(raw_buckets, list):
        raise JournalValidationError("buckets must be a list")
    if len(raw_seen_polls) > cfg.max_seen_polls:
        raise JournalValidationError(f"seenPolls count ({len(raw_seen_polls)}) exceeds max_seen_polls ({cfg.max_seen_polls})")
    if len(raw_buckets) > cfg.max_buckets:
        raise JournalValidationError(f"buckets count ({len(raw_buckets)}) exceeds max_buckets ({cfg.max_buckets})")

    seen_polls: dict[str, PollReceipt] = {}
    poll_times: dict[str, Any] = {}
    for entry in raw_seen_polls:
        if not isinstance(entry, dict) or set(entry.keys()) != _POLL_RECEIPT_KEYS:
            raise JournalValidationError("malformed seenPolls entry")
        poll_id = _require_clean_str(entry["pollId"], "seenPolls.pollId")
        if poll_id in seen_polls:
            raise JournalValidationError(f"duplicate pollId in seenPolls: {poll_id!r}")
        obs_iso, obs_dt = _require_canonical_utc(entry["observedAt"], "seenPolls.observedAt")
        complete = _require_bool(entry["complete"], "seenPolls.complete")
        if not complete:
            raise JournalValidationError("seenPolls cannot contain an incomplete poll receipt")
        input_digest = _require_sha256(entry["inputDigest"], "seenPolls.inputDigest")
        seen_polls[poll_id] = PollReceipt(
            poll_id=poll_id,
            observed_at=obs_iso,
            complete=complete,
            input_digest=input_digest,
        )
        poll_times[poll_id] = obs_dt

    raw_last_obs = data["lastObservedAt"]
    raw_last_poll = data["lastPollId"]
    if revision == 0:
        if raw_last_obs is not None or raw_last_poll is not None or seen_polls or raw_buckets:
            raise JournalValidationError("revision 0 journal must be empty with null lastObservedAt/lastPollId")
        return empty_state(), JournalPin(revision=0, digest=stored_digest)

    if raw_last_obs is None or raw_last_poll is None:
        raise JournalValidationError("non-zero revision journal requires lastObservedAt and lastPollId")
    last_obs_iso, last_obs_dt = _require_canonical_utc(raw_last_obs, "lastObservedAt")
    last_poll_id = _require_clean_str(raw_last_poll, "lastPollId")
    if len(seen_polls) != revision:
        raise JournalValidationError("journal revision disagrees with seenPolls count")
    if last_poll_id not in seen_polls:
        raise JournalValidationError("lastPollId is not present in seenPolls")
    if seen_polls[last_poll_id].observed_at != last_obs_iso:
        raise JournalValidationError("lastObservedAt disagrees with lastPollId receipt")
    for pid, pdt in poll_times.items():
        if pdt > last_obs_dt:
            raise JournalValidationError(f"seenPolls entry {pid!r} postdates state lastObservedAt")

    buckets: dict[tuple[str, str], NamedBucket] = {}
    total_rows = 0
    for b_entry in raw_buckets:
        if not isinstance(b_entry, dict) or set(b_entry.keys()) != _BUCKET_KEYS:
            raise JournalValidationError("malformed bucket entry")

        raw_repo = b_entry["repository"]
        try:
            norm_repo = envelope.repository(raw_repo)
        except PayloadError as exc:
            raise JournalValidationError(str(exc)) from exc
        if norm_repo != raw_repo:
            raise JournalValidationError("bucket repository must be normalized lowercase")

        named_id = b_entry["namedId"]
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise JournalValidationError("bucket namedId is invalid")
        try:
            auth_repo = envelope.authority_repository(named_id, authority)
        except PayloadError as exc:
            raise JournalValidationError(str(exc)) from exc
        if auth_repo != norm_repo:
            raise JournalValidationError("bucket (repository, namedId) disagrees with registry authority")

        scope = (norm_repo, named_id)
        if scope in buckets:
            raise JournalValidationError(f"duplicate bucket scope: {scope!r}")

        pending_iso, pending_dt = _require_canonical_utc(b_entry["pendingSince"], "bucket.pendingSince")
        first_poll_id = _require_clean_str(b_entry["firstPollId"], "bucket.firstPollId")
        bucket_last_iso, bucket_last_dt = _require_canonical_utc(b_entry["lastObservedAt"], "bucket.lastObservedAt")
        bucket_last_poll_id = _require_clean_str(b_entry["lastPollId"], "bucket.lastPollId")
        sighting_count = _require_int(b_entry["sightingCount"], "bucket.sightingCount", minimum=1)
        bucket_rev = _require_int(b_entry["revision"], "bucket.revision", minimum=1)

        if bucket_rev != sighting_count:
            raise JournalValidationError("bucket.revision disagrees with bucket.sightingCount")
        if bucket_rev > revision:
            raise JournalValidationError("bucket.revision exceeds state revision")
        if first_poll_id not in seen_polls:
            raise JournalValidationError("bucket.firstPollId is not present in seenPolls")
        if bucket_last_poll_id not in seen_polls:
            raise JournalValidationError("bucket.lastPollId is not present in seenPolls")
        if seen_polls[first_poll_id].observed_at != pending_iso:
            raise JournalValidationError("bucket.pendingSince disagrees with firstPollId receipt")
        if seen_polls[bucket_last_poll_id].observed_at != bucket_last_iso:
            raise JournalValidationError("bucket.lastObservedAt disagrees with lastPollId receipt")
        if not (pending_dt <= bucket_last_dt <= last_obs_dt):
            raise JournalValidationError("bucket timestamps are out of order")
        if sighting_count == 1 and (first_poll_id != bucket_last_poll_id or pending_iso != bucket_last_iso):
            raise JournalValidationError("single-sighting bucket has mismatched first/last poll provenance")

        latest_sha = _require_sha256(b_entry["latestFindingSha256"], "bucket.latestFindingSha256")
        latest_finding = b_entry["latestFinding"]
        if not isinstance(latest_finding, dict):
            raise JournalValidationError("bucket.latestFinding must be a JSON object")
        for req_key in _REQUIRED_CANONICAL_FINDING_KEYS:
            if req_key not in latest_finding:
                raise JournalValidationError(f"bucket.latestFinding missing required key: {req_key}")
        if latest_finding.get("skillId") != named_id:
            raise JournalValidationError("bucket.latestFinding.skillId disagrees with bucket namedId")
        try:
            envelope.validate_named(latest_finding, norm_repo, authority, digest=True, mutation_scope=True)
            validateReleaseSource(latest_finding)
        except (PayloadError, GhError) as exc:
            raise JournalValidationError(f"bucket.latestFinding failed canonical validation: {exc}") from exc
        _validate_liveness_and_drift(latest_finding)
        for cand in latest_finding["candidates"]:
            if "precheck" in cand and not isinstance(cand["precheck"], dict):
                raise JournalValidationError("bucket.latestFinding candidate has malformed precheck")
        if latest_finding.get("payloadSha256") != latest_sha:
            raise JournalValidationError("bucket.latestFindingSha256 disagrees with latestFinding.payloadSha256")

        raw_versions = b_entry["versionsSeen"]
        if not isinstance(raw_versions, list) or not raw_versions:
            raise JournalValidationError("bucket.versionsSeen must be a non-empty list")
        if len(raw_versions) > cfg.max_versions_per_bucket:
            raise JournalValidationError(
                f"bucket.versionsSeen count ({len(raw_versions)}) exceeds max_versions_per_bucket ({cfg.max_versions_per_bucket})"
            )
        if len(raw_versions) > sighting_count:
            raise JournalValidationError("bucket.versionsSeen count exceeds sightingCount")

        versions_seen: list[VersionSighting] = []
        seen_version_keys: set[tuple[str, str, str]] = set()
        matched_latest_version = False
        for v_entry in raw_versions:
            if not isinstance(v_entry, dict) or set(v_entry.keys()) != _VERSION_SIGHTING_KEYS:
                raise JournalValidationError("malformed versionsSeen entry")
            v_ver = _require_clean_str(v_entry["version"], "versionsSeen.version")
            v_src = v_entry["sourceUrl"]
            try:
                if envelope.release_repository(v_src, v_ver) != norm_repo:
                    raise JournalValidationError("versionsSeen release source disagrees with bucket repository")
            except PayloadError as exc:
                raise JournalValidationError(str(exc)) from exc
            v_rel = _require_clean_str(v_entry["releasedAt"], "versionsSeen.releasedAt")
            v_sha = _require_sha256(v_entry["findingSha256"], "versionsSeen.findingSha256")
            v_first_iso, v_first_dt = _require_canonical_utc(v_entry["firstObservedAt"], "versionsSeen.firstObservedAt")
            v_last_iso, v_last_dt = _require_canonical_utc(v_entry["lastObservedAt"], "versionsSeen.lastObservedAt")
            v_first_poll = _require_clean_str(v_entry["firstPollId"], "versionsSeen.firstPollId")
            v_last_poll = _require_clean_str(v_entry["lastPollId"], "versionsSeen.lastPollId")

            if v_first_poll not in seen_polls or v_last_poll not in seen_polls:
                raise JournalValidationError("versionsSeen poll reference missing from seenPolls")
            if seen_polls[v_first_poll].observed_at != v_first_iso:
                raise JournalValidationError("versionsSeen.firstObservedAt disagrees with firstPollId receipt")
            if seen_polls[v_last_poll].observed_at != v_last_iso:
                raise JournalValidationError("versionsSeen.lastObservedAt disagrees with lastPollId receipt")
            if not (pending_dt <= v_first_dt <= v_last_dt <= bucket_last_dt):
                raise JournalValidationError("versionsSeen timestamps are out of order")

            v_key = (v_ver, v_src, v_sha)
            if v_key in seen_version_keys:
                raise JournalValidationError("duplicate (version, sourceUrl, findingSha256) in versionsSeen")
            seen_version_keys.add(v_key)

            if (
                v_ver == latest_finding["newVersion"]
                and v_src == latest_finding["sourceUrl"]
                and v_sha == latest_sha
            ):
                if v_rel != latest_finding["releasedAt"]:
                    raise JournalValidationError("latest versionsSeen entry disagrees with latestFinding.releasedAt")
                if v_last_iso != bucket_last_iso or v_last_poll != bucket_last_poll_id:
                    raise JournalValidationError("latest versionsSeen entry disagrees with bucket lastObservedAt/lastPollId")
                matched_latest_version = True

            versions_seen.append(
                VersionSighting(
                    version=v_ver,
                    source_url=v_src,
                    released_at=v_rel,
                    finding_sha256=v_sha,
                    first_observed_at=v_first_iso,
                    last_observed_at=v_last_iso,
                    first_poll_id=v_first_poll,
                    last_poll_id=v_last_poll,
                )
            )

        if versions_seen[0].first_observed_at != pending_iso or versions_seen[0].first_poll_id != first_poll_id:
            raise JournalValidationError("first versionsSeen entry disagrees with bucket pendingSince/firstPollId")
        if not matched_latest_version:
            raise JournalValidationError("bucket.versionsSeen does not include latestFinding")

        raw_rows = b_entry["rows"]
        if not isinstance(raw_rows, list):
            raise JournalValidationError("bucket.rows must be a list")
        if len(raw_rows) > cfg.max_rows_per_bucket:
            raise JournalValidationError(
                f"bucket.rows count ({len(raw_rows)}) exceeds max_rows_per_bucket ({cfg.max_rows_per_bucket})"
            )
        total_rows += len(raw_rows)
        if total_rows > cfg.max_total_rows:
            raise JournalValidationError(f"total rows ({total_rows}) exceeds max_total_rows ({cfg.max_total_rows})")

        canonical_cands_by_id = {cand["id"]: cand for cand in latest_finding["candidates"]}
        latest_component_adds = set(latest_finding["componentAdds"])
        rows_map: dict[str, RowHistory] = {}
        seen_slugs: set[str] = set()
        present_slugs_from_rows: set[str] = set()

        for r_entry in raw_rows:
            if not isinstance(r_entry, dict) or set(r_entry.keys()) != _ROW_KEYS:
                raise JournalValidationError("malformed row entry")
            row_id = r_entry["rowId"]
            slug = r_entry["slug"]
            suggested_id = r_entry["suggestedId"]
            if not isinstance(row_id, str) or not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
                raise JournalValidationError("row has invalid rowId or slug")
            row_repo, sep, row_slug = row_id.partition(":")
            if not sep or row_repo.lower() != norm_repo or row_slug != slug:
                raise JournalValidationError("rowId disagrees with bucket repository or slug")
            if row_id in rows_map or slug in seen_slugs:
                raise JournalValidationError(f"duplicate rowId or slug in bucket: {row_id!r}")
            seen_slugs.add(slug)

            if not isinstance(suggested_id, str) or not envelope.IDENTIFIER.fullmatch(suggested_id):
                raise JournalValidationError("row.suggestedId is invalid")

            raw_pin = r_entry["firstSeenPin"]
            if not isinstance(raw_pin, dict) or set(raw_pin.keys()) != _PIN_KEYS:
                raise JournalValidationError("malformed row.firstSeenPin")
            pin_ver = _require_clean_str(raw_pin["firstSeenVersion"], "firstSeenPin.firstSeenVersion")
            pin_url = _validate_evidence_url(raw_pin["evidenceUrl"], norm_repo, pin_ver)
            pin_at_raw = raw_pin["firstSeenAt"]
            pin_poll_raw = raw_pin["firstSeenPollId"]

            last_seen_ver = _require_clean_str(r_entry["lastSeenVersion"], "row.lastSeenVersion")
            last_seen_at_raw = r_entry["lastSeenAt"]
            last_seen_poll_raw = r_entry["lastSeenPollId"]
            present_in_latest = _require_bool(r_entry["presentInLatest"], "row.presentInLatest")
            vanished_at_raw = r_entry["vanishedAt"]
            vanished_poll_raw = r_entry["vanishedPollId"]
            historical_only = _require_bool(r_entry["historicalOnly"], "row.historicalOnly")
            presence = r_entry["presence"]
            if not isinstance(presence, str) or presence not in _VALID_PRESENCE:
                raise JournalValidationError(f"row.presence is invalid: {presence!r}")

            latest_row = _validate_candidate_row_dict(
                r_entry["latestRow"],
                repo=norm_repo,
                row_id=row_id,
                slug=slug,
                suggested_id=suggested_id,
                first_seen_version=pin_ver,
                evidence_url=pin_url,
            )
            if row_id in canonical_cands_by_id and latest_row != canonical_cands_by_id[row_id]:
                raise JournalValidationError("row.latestRow disagrees with bucket.latestFinding candidate row")

            if historical_only:
                if pin_at_raw is not None or pin_poll_raw is not None:
                    raise JournalValidationError("historicalOnly row cannot carry firstSeenAt/firstSeenPollId")
                if last_seen_at_raw is not None or last_seen_poll_raw is not None:
                    raise JournalValidationError("historicalOnly row cannot carry lastSeenAt/lastSeenPollId")
                if present_in_latest:
                    raise JournalValidationError("historicalOnly row cannot have presentInLatest=True")
                if vanished_at_raw is not None or vanished_poll_raw is not None:
                    raise JournalValidationError("historicalOnly row cannot carry vanishedAt/vanishedPollId")
                if presence not in (PRESENCE_UNKNOWN, PRESENCE_PRESENT_TRACKED):
                    raise JournalValidationError("historicalOnly row has disallowed presence state")
                pin_at_iso = None
                pin_poll_id = None
                last_seen_at_iso = None
                last_seen_poll_id = None
                vanished_at_iso = None
                vanished_poll_id = None
            else:
                if pin_at_raw is None or pin_poll_raw is None:
                    raise JournalValidationError("observed row requires firstSeenAt and firstSeenPollId")
                pin_at_iso, pin_at_dt = _require_canonical_utc(pin_at_raw, "firstSeenPin.firstSeenAt")
                pin_poll_id = _require_clean_str(pin_poll_raw, "firstSeenPin.firstSeenPollId")
                if pin_poll_id not in seen_polls or seen_polls[pin_poll_id].observed_at != pin_at_iso:
                    raise JournalValidationError("firstSeenPin poll reference disagrees with seenPolls")

                if last_seen_at_raw is None or last_seen_poll_raw is None:
                    raise JournalValidationError("observed row requires lastSeenAt and lastSeenPollId")
                last_seen_at_iso, last_seen_at_dt = _require_canonical_utc(last_seen_at_raw, "row.lastSeenAt")
                last_seen_poll_id = _require_clean_str(last_seen_poll_raw, "row.lastSeenPollId")
                if last_seen_poll_id not in seen_polls or seen_polls[last_seen_poll_id].observed_at != last_seen_at_iso:
                    raise JournalValidationError("row.lastSeenPollId disagrees with seenPolls")
                if not (pending_dt <= pin_at_dt <= last_seen_at_dt <= bucket_last_dt):
                    raise JournalValidationError("row first/last observation timestamps are out of order")

                if presence == PRESENCE_PRESENT_CANDIDATE:
                    if not present_in_latest:
                        raise JournalValidationError("present-candidate row must have presentInLatest=True")
                    if last_seen_at_iso != bucket_last_iso or last_seen_poll_id != bucket_last_poll_id:
                        raise JournalValidationError("present-candidate row disagrees with bucket lastObservedAt/lastPollId")
                    if vanished_at_raw is not None or vanished_poll_raw is not None:
                        raise JournalValidationError("present-candidate row cannot carry vanishedAt/vanishedPollId")
                    if slug not in latest_component_adds or row_id not in canonical_cands_by_id:
                        raise JournalValidationError("present-candidate row is absent from latestFinding componentAdds/candidates")
                    if last_seen_ver != canonical_cands_by_id[row_id]["lastSeenVersion"]:
                        raise JournalValidationError(
                            "present-candidate row.lastSeenVersion disagrees with latestFinding candidate lastSeenVersion"
                        )
                    vanished_at_iso = None
                    vanished_poll_id = None
                    present_slugs_from_rows.add(slug)
                elif presence == PRESENCE_PRESENT_TRACKED:
                    if present_in_latest:
                        raise JournalValidationError("present-tracked row cannot have presentInLatest=True")
                    if vanished_at_raw is not None or vanished_poll_raw is not None:
                        raise JournalValidationError("present-tracked row cannot carry vanishedAt/vanishedPollId")
                    vanished_at_iso = None
                    vanished_poll_id = None
                elif presence == PRESENCE_VANISHED:
                    if present_in_latest:
                        raise JournalValidationError("vanished row cannot have presentInLatest=True")
                    if vanished_at_raw is None or vanished_poll_raw is None:
                        raise JournalValidationError("vanished row requires vanishedAt and vanishedPollId")
                    vanished_at_iso, vanished_at_dt = _require_canonical_utc(vanished_at_raw, "row.vanishedAt")
                    vanished_poll_id = _require_clean_str(vanished_poll_raw, "row.vanishedPollId")
                    if vanished_poll_id not in seen_polls or seen_polls[vanished_poll_id].observed_at != vanished_at_iso:
                        raise JournalValidationError("row.vanishedPollId disagrees with seenPolls")
                    if vanished_poll_id == last_seen_poll_id or not (last_seen_at_dt <= vanished_at_dt <= bucket_last_dt):
                        raise JournalValidationError("row.vanishedAt/vanishedPollId ordering is invalid")
                else:  # PRESENCE_UNKNOWN
                    if present_in_latest:
                        raise JournalValidationError("unknown-presence row cannot have presentInLatest=True")
                    if (vanished_at_raw is None) != (vanished_poll_raw is None):
                        raise JournalValidationError("row.vanishedAt and vanishedPollId must both be set or both null")
                    if vanished_at_raw is not None:
                        vanished_at_iso, vanished_at_dt = _require_canonical_utc(vanished_at_raw, "row.vanishedAt")
                        vanished_poll_id = _require_clean_str(vanished_poll_raw, "row.vanishedPollId")
                        if vanished_poll_id not in seen_polls or seen_polls[vanished_poll_id].observed_at != vanished_at_iso:
                            raise JournalValidationError("row.vanishedPollId disagrees with seenPolls")
                        if vanished_poll_id == last_seen_poll_id or not (last_seen_at_dt <= vanished_at_dt <= bucket_last_dt):
                            raise JournalValidationError("row.vanishedAt/vanishedPollId ordering is invalid")
                    else:
                        vanished_at_iso = None
                        vanished_poll_id = None

            rows_map[row_id] = RowHistory(
                row_id=row_id,
                slug=slug,
                suggested_id=suggested_id,
                first_seen_pin=FirstSeenPin(
                    first_seen_version=pin_ver,
                    evidence_url=pin_url,
                    first_seen_at=pin_at_iso,
                    first_seen_poll_id=pin_poll_id,
                ),
                last_seen_version=last_seen_ver,
                last_seen_at=last_seen_at_iso,
                last_seen_poll_id=last_seen_poll_id,
                present_in_latest=present_in_latest,
                vanished_at=vanished_at_iso,
                vanished_poll_id=vanished_poll_id,
                latest_row=latest_row,
                historical_only=historical_only,
                presence=presence,
            )

        if not set(canonical_cands_by_id).issubset(rows_map):
            raise JournalValidationError("bucket.rows omits candidate rows present in latestFinding")
        if present_slugs_from_rows != latest_component_adds:
            raise JournalValidationError("present-candidate rows disagree with latestFinding.componentAdds")

        buckets[scope] = NamedBucket(
            repository=norm_repo,
            named_id=named_id,
            pending_since=pending_iso,
            first_poll_id=first_poll_id,
            last_observed_at=bucket_last_iso,
            last_poll_id=bucket_last_poll_id,
            sighting_count=sighting_count,
            revision=bucket_rev,
            latest_finding=copy.deepcopy(latest_finding),
            latest_finding_sha256=latest_sha,
            versions_seen=tuple(versions_seen),
            rows=rows_map,
        )

    state = ReducerState(
        schema_version=reducer_schema,
        revision=revision,
        last_observed_at=last_obs_iso,
        last_poll_id=last_poll_id,
        buckets=buckets,
        seen_polls=seen_polls,
    )
    return state, JournalPin(revision=revision, digest=stored_digest)


# ---------------------------------------------------------------------------
# Local file locking & load / save persistence
# ---------------------------------------------------------------------------


def _lock_path_for(target: Path) -> Path:
    return target.with_name(f"{target.name}.lock")


@contextmanager
def _exclusive_journal_lock(target: Path) -> Iterator[None]:
    """Acquire an advisory POSIX flock on ``<target>.lock`` for cooperating local callers."""
    lock_path = _lock_path_for(target)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def load_journal(
    path: str | os.PathLike[str],
    authority: Mapping[str, Mapping[str, Any]],
    *,
    config: ReducerConfig | None = None,
    allow_bootstrap: bool = False,
    initialized: bool = False,
    trusted_latest_pin: JournalPin | None = None,
    max_bytes: int = DEFAULT_MAX_JOURNAL_BYTES,
) -> JournalHandle:
    """Read and strictly validate a local ``named-v3`` journal file.

    Returns an immutable ``JournalHandle``. Blocked states (missing, lost,
    corrupt, legacy-v2, foreign, stale) always carry ``state=None`` and
    ``blocked=True``. Never modifies the file on disk.
    """
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        raise ValueError("config must be a ReducerConfig")
    if type(allow_bootstrap) is not bool:
        raise ValueError("allow_bootstrap must be a boolean")
    if type(initialized) is not bool:
        raise ValueError("initialized must be a boolean")
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if trusted_latest_pin is not None and not isinstance(trusted_latest_pin, JournalPin):
        raise ValueError("trusted_latest_pin must be None or a JournalPin")
    if not isinstance(authority, Mapping) or not authority:
        raise ValueError("authority must be a non-empty mapping")
    if not isinstance(path, (str, os.PathLike)) or not os.fspath(path):
        raise ValueError("journal path must be a non-empty path")

    target = Path(path)

    if not os.path.lexists(target):
        if initialized or trusted_latest_pin is not None:
            return JournalHandle(
                path=target,
                status=STATUS_LOST,
                detail="journal is missing after initialization or expected trusted pin; refusing reset",
                state=None,
                pin=None,
                byte_size=None,
                namespace=None,
                loaded_at_revision=None,
                existed=False,
            )
        if allow_bootstrap:
            return JournalHandle(
                path=target,
                status=STATUS_BOOTSTRAP,
                detail="no journal on disk; explicit offline bootstrap permitted",
                state=empty_state(),
                pin=None,
                byte_size=0,
                namespace=JOURNAL_NAMESPACE,
                loaded_at_revision=0,
                existed=False,
            )
        return JournalHandle(
            path=target,
            status=STATUS_MISSING,
            detail="no journal on disk and allow_bootstrap is False",
            state=None,
            pin=None,
            byte_size=None,
            namespace=None,
            loaded_at_revision=None,
            existed=False,
        )

    if target.is_symlink() or not target.is_file():
        return JournalHandle(
            path=target,
            status=STATUS_CORRUPT,
            detail="journal path is not a regular file",
            state=None,
            pin=None,
            byte_size=None,
            namespace=None,
            loaded_at_revision=None,
            existed=True,
        )

    try:
        st_size = target.stat().st_size
        if st_size > max_bytes:
            return JournalHandle(
                path=target,
                status=STATUS_CORRUPT,
                detail=f"journal file size ({st_size} bytes) exceeds max_bytes ({max_bytes})",
                state=None,
                pin=None,
                byte_size=st_size,
                namespace=None,
                loaded_at_revision=None,
                existed=True,
            )
        with target.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
    except OSError as exc:
        return JournalHandle(
            path=target,
            status=STATUS_CORRUPT,
            detail=f"journal file unreadable: {exc.strerror or type(exc).__name__}",
            state=None,
            pin=None,
            byte_size=None,
            namespace=None,
            loaded_at_revision=None,
            existed=True,
        )

    if len(raw) > max_bytes:
        return JournalHandle(
            path=target,
            status=STATUS_CORRUPT,
            detail=f"journal read exceeded max_bytes ({max_bytes})",
            state=None,
            pin=None,
            byte_size=len(raw),
            namespace=None,
            loaded_at_revision=None,
            existed=True,
        )

    try:
        text = raw.decode("utf-8")
        data = json.loads(
            text,
            object_pairs_hook=_unique_object_pairs,
            parse_constant=_reject_non_finite,
            parse_int=_parse_bounded_int,
            parse_float=_parse_bounded_float,
        )
        _validate_json_depth(data)
    except (UnicodeDecodeError, ValueError, RecursionError, JournalValidationError) as exc:
        return JournalHandle(
            path=target,
            status=STATUS_CORRUPT,
            detail=f"journal JSON decode failed: {exc}",
            state=None,
            pin=None,
            byte_size=len(raw),
            namespace=None,
            loaded_at_revision=None,
            existed=True,
        )

    if not isinstance(data, dict):
        return JournalHandle(
            path=target,
            status=STATUS_CORRUPT,
            detail="journal JSON root is not an object",
            state=None,
            pin=None,
            byte_size=len(raw),
            namespace=None,
            loaded_at_revision=None,
            existed=True,
        )

    if is_legacy_v2_payload(data):
        return JournalHandle(
            path=target,
            status=STATUS_LEGACY_V2,
            detail="legacy v2 staging journal detected; refusing to reinterpret or overwrite",
            state=None,
            pin=None,
            byte_size=len(raw),
            namespace="legacy-v2",
            loaded_at_revision=None,
            existed=True,
        )

    if (
        data.get("format") != JOURNAL_FORMAT
        or data.get("namespace") != JOURNAL_NAMESPACE
        or type(data.get("journalVersion")) is not int
        or data.get("journalVersion") != JOURNAL_VERSION
    ):
        return JournalHandle(
            path=target,
            status=STATUS_FOREIGN,
            detail="foreign journal format or namespace; refusing to reinterpret or overwrite",
            state=None,
            pin=None,
            byte_size=len(raw),
            namespace=None,
            loaded_at_revision=None,
            existed=True,
        )

    try:
        state, pin = decode_state(data, authority, config=cfg)
    except (JournalValidationError, PayloadError, ValueError) as exc:
        return JournalHandle(
            path=target,
            status=STATUS_CORRUPT,
            detail=f"journal validation failed: {exc}",
            state=None,
            pin=None,
            byte_size=len(raw),
            namespace=JOURNAL_NAMESPACE,
            loaded_at_revision=None,
            existed=True,
        )

    if trusted_latest_pin is not None and pin != trusted_latest_pin:
        if pin.revision < trusted_latest_pin.revision:
            reason = (
                f"on-disk journal revision {pin.revision} is older than trusted latest pin "
                f"revision {trusted_latest_pin.revision}"
            )
        elif pin.revision == trusted_latest_pin.revision:
            reason = f"on-disk journal digest disagrees with trusted latest pin at revision {pin.revision}"
        else:
            reason = (
                f"on-disk journal revision {pin.revision} disagrees with trusted latest pin "
                f"revision {trusted_latest_pin.revision}"
            )
        return JournalHandle(
            path=target,
            status=STATUS_STALE,
            detail=reason,
            state=None,
            pin=pin,
            byte_size=len(raw),
            namespace=JOURNAL_NAMESPACE,
            loaded_at_revision=pin.revision,
            existed=True,
        )

    return JournalHandle(
        path=target,
        status=STATUS_OK,
        detail="loaded verified named-v3 journal",
        state=state,
        pin=pin,
        byte_size=len(raw),
        namespace=JOURNAL_NAMESPACE,
        loaded_at_revision=state.revision,
        existed=True,
    )


def _atomic_write_bytes(target: Path, encoded_bytes: bytes) -> None:
    fd, temp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _verify_one_step_transition(
    base_state: ReducerState,
    proposed_bytes: bytes,
    proposed_pin: JournalPin,
    poll: PollInput | None,
    authority: Mapping[str, Mapping[str, Any]],
    *,
    config: ReducerConfig,
    max_bytes: int,
) -> None:
    """Prove *proposed_bytes*/*proposed_pin* is the exact ``reduce_poll`` successor of *base_state*."""
    if poll is None:
        raise JournalConflictError(
            "advancing journal state requires the verified PollInput that produced the transition; "
            "arbitrary state replacement is forbidden"
        )
    verified = reduce_poll(base_state, poll, authority, config=config)
    if verified.status != "applied":
        raise JournalConflictError(
            f"transition poll did not apply cleanly against current checkpoint (status={verified.status}: "
            f"{verified.rejection_reason or 'no-op'})"
        )
    verified_bytes, verified_pin = serialize_state(verified.state, authority, config=config, max_bytes=max_bytes)
    if verified_pin != proposed_pin or verified_bytes != proposed_bytes:
        raise JournalConflictError(
            "proposed state disagrees with exact one-step reducer transition from current on-disk checkpoint"
        )


def commit_poll(
    path: str | os.PathLike[str],
    poll: PollInput,
    authority: Mapping[str, Mapping[str, Any]],
    *,
    expected_pin: JournalPin | None = None,
    allow_bootstrap: bool = False,
    initialized: bool = False,
    trusted_latest_pin: JournalPin | None = None,
    config: ReducerConfig | None = None,
    max_bytes: int = DEFAULT_MAX_JOURNAL_BYTES,
) -> JournalCommitResult:
    """Atomically re-read *path*, apply *poll* via ``weekly_reducer.reduce_poll``, and commit on apply.

    Under the cooperating local POSIX lock:
    * Re-reads and validates the canonical on-disk checkpoint (refusing legacy-v2,
      foreign, corrupt, lost, or stale-pin targets with ``JournalBlockedError``).
    * Verifies ``expected_pin`` against the live checkpoint (refusing stale pins
      or bootstrap collisions with ``JournalConflictError``).
    * Runs ``reduce_poll(current.state, poll, authority, config=cfg)``.
    * On ``status="replayed"`` or ``status="rejected"``, leaves on-disk bytes
      untouched and returns ``persisted=False``.
    * On ``status="applied"``, enforces ``max_bytes`` and atomically replaces
      *path* via ``mkstemp`` + ``fsync`` + ``os.replace``.
    """
    if not isinstance(poll, PollInput):
        raise ValueError("poll must be a PollInput")
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        raise ValueError("config must be a ReducerConfig")
    if type(allow_bootstrap) is not bool:
        raise ValueError("allow_bootstrap must be a boolean")
    if type(initialized) is not bool:
        raise ValueError("initialized must be a boolean")
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if expected_pin is not None and not isinstance(expected_pin, JournalPin):
        raise ValueError("expected_pin must be None or a JournalPin")
    if trusted_latest_pin is not None and not isinstance(trusted_latest_pin, JournalPin):
        raise ValueError("trusted_latest_pin must be None or a JournalPin")
    if not isinstance(authority, Mapping) or not authority:
        raise ValueError("authority must be a non-empty mapping")
    if not isinstance(path, (str, os.PathLike)) or not os.fspath(path):
        raise ValueError("journal path must be a non-empty path")

    if expected_pin is None and (not allow_bootstrap or initialized):
        raise JournalBlockedError(
            "bootstrapping a new journal requires allow_bootstrap=True and initialized=False; "
            "updating an existing checkpoint requires expected_pin"
        )

    target = Path(path)
    if expected_pin is not None and not os.path.lexists(target):
        if initialized:
            raise JournalBlockedError("journal is missing after initialization; refusing reset")
        raise JournalConflictError("expected checkpoint does not exist on disk")

    target.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_journal_lock(target):
        current = load_journal(
            target,
            authority,
            config=cfg,
            allow_bootstrap=allow_bootstrap,
            initialized=initialized,
            trusted_latest_pin=trusted_latest_pin,
            max_bytes=max_bytes,
        )
        if current.blocked:
            raise JournalBlockedError(f"refusing to commit poll against {current.status} journal: {current.detail}")

        if expected_pin is None:
            if current.existed:
                raise JournalConflictError("journal already exists on disk; expected_pin is required")
        else:
            if not current.existed:
                raise JournalConflictError("expected checkpoint disappeared before commit")
            if current.pin != expected_pin:
                raise JournalConflictError(
                    f"CAS mismatch: expected (rev={expected_pin.revision}, digest={expected_pin.digest[:12]}), "
                    f"found (rev={current.pin.revision if current.pin else None}, "
                    f"digest={current.pin.digest[:12] if current.pin else None})"
                )

        assert current.state is not None
        reduction = reduce_poll(current.state, poll, authority, config=cfg)
        if reduction.status != "applied":
            return JournalCommitResult(handle=current, reduction=reduction, persisted=False)

        encoded_bytes, new_pin = serialize_state(reduction.state, authority, config=cfg, max_bytes=max_bytes)
        _atomic_write_bytes(target, encoded_bytes)

    new_handle = JournalHandle(
        path=target,
        status=STATUS_OK,
        detail="committed verified named-v3 journal transition",
        state=_clone_state(reduction.state),
        pin=new_pin,
        byte_size=len(encoded_bytes),
        namespace=JOURNAL_NAMESPACE,
        loaded_at_revision=reduction.state.revision,
        existed=True,
    )
    return JournalCommitResult(handle=new_handle, reduction=reduction, persisted=True)


def save_journal(
    path: str | os.PathLike[str],
    state: ReducerState,
    authority: Mapping[str, Mapping[str, Any]],
    *,
    expected_pin: JournalPin | None = None,
    poll: PollInput | None = None,
    allow_bootstrap: bool = False,
    initialized: bool = False,
    config: ReducerConfig | None = None,
    max_bytes: int = DEFAULT_MAX_JOURNAL_BYTES,
) -> JournalHandle:
    """Persist *state* atomically to *path* with CAS + one-step reducer lineage verification.

    * Creating a new journal requires ``expected_pin=None``, ``allow_bootstrap=True``,
      and ``initialized=False``; refuses if any file already exists at *path*.
      Bootstrapping ``empty_state()`` (revision 0) requires no poll; bootstrapping
      a non-empty state requires ``poll`` and verifies it equals
      ``reduce_poll(empty_state(), poll, authority)``.
    * Updating an existing checkpoint requires ``expected_pin`` matching the
      re-read on-disk ``JournalPin`` under the exclusive POSIX lock. Only an
      exact byte-equivalent no-op (``new_pin == expected_pin``) or a verified
      one-step ``reduce_poll(current.state, poll, authority)`` transition may
      replace initialized state; arbitrary state replacement, rollback, or
      history-discarding higher revisions are refused with ``JournalConflictError``.
    * Never overwrites legacy v2, foreign, corrupt, or missing-initialized state
      (always raises ``JournalBlockedError`` before pin comparison).
    * On any validation, size, CAS, or I/O error, prior bytes remain untouched
      and any temporary file is removed.
    """
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        raise ValueError("config must be a ReducerConfig")
    if type(allow_bootstrap) is not bool:
        raise ValueError("allow_bootstrap must be a boolean")
    if type(initialized) is not bool:
        raise ValueError("initialized must be a boolean")
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if expected_pin is not None and not isinstance(expected_pin, JournalPin):
        raise ValueError("expected_pin must be None or a JournalPin")
    if poll is not None and not isinstance(poll, PollInput):
        raise ValueError("poll must be None or a PollInput")
    if not isinstance(path, (str, os.PathLike)) or not os.fspath(path):
        raise ValueError("journal path must be a non-empty path")

    if expected_pin is None and (not allow_bootstrap or initialized):
        raise JournalBlockedError(
            "creating a new journal requires allow_bootstrap=True and initialized=False; "
            "updating an existing checkpoint requires expected_pin"
        )

    # Validate and bound-check the new state BEFORE touching the filesystem.
    encoded_bytes, new_pin = serialize_state(state, authority, config=cfg, max_bytes=max_bytes)

    target = Path(path)
    if expected_pin is not None and not os.path.lexists(target):
        if initialized:
            raise JournalBlockedError("journal is missing after initialization; refusing to overwrite lost history")
        raise JournalConflictError("expected checkpoint does not exist on disk")

    target.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_journal_lock(target):
        current = load_journal(
            target,
            authority,
            config=cfg,
            allow_bootstrap=allow_bootstrap,
            initialized=initialized,
            max_bytes=max_bytes,
        )

        if expected_pin is None:
            if current.existed:
                if current.status in (STATUS_LEGACY_V2, STATUS_FOREIGN, STATUS_CORRUPT):
                    raise JournalBlockedError(f"refusing to overwrite {current.status} file: {current.detail}")
                raise JournalConflictError("journal already exists on disk; bootstrap refuses to overwrite")
            if current.status != STATUS_BOOTSTRAP:
                raise JournalBlockedError(f"refusing bootstrap save in state {current.status}: {current.detail}")
            if state.revision > 0:
                _verify_one_step_transition(
                    empty_state(),
                    encoded_bytes,
                    new_pin,
                    poll,
                    authority,
                    config=cfg,
                    max_bytes=max_bytes,
                )
        else:
            if not current.existed:
                if initialized:
                    raise JournalBlockedError("journal is missing after initialization; refusing reset")
                raise JournalConflictError("expected checkpoint disappeared before commit")
            if current.status in (STATUS_LEGACY_V2, STATUS_FOREIGN, STATUS_CORRUPT):
                raise JournalBlockedError(f"refusing to overwrite {current.status} file: {current.detail}")
            if current.pin != expected_pin:
                raise JournalConflictError(
                    f"CAS mismatch: expected (rev={expected_pin.revision}, digest={expected_pin.digest[:12]}), "
                    f"found (rev={current.pin.revision if current.pin else None}, "
                    f"digest={current.pin.digest[:12] if current.pin else None})"
                )
            if new_pin.revision < expected_pin.revision:
                raise JournalConflictError(
                    f"refusing revision rollback from expected {expected_pin.revision} to {new_pin.revision}"
                )
            if new_pin.revision == expected_pin.revision and new_pin.digest != expected_pin.digest:
                raise JournalConflictError(
                    f"refusing digest mutation without revision advance at revision {expected_pin.revision}"
                )
            if new_pin == expected_pin:
                # Byte-equivalent checkpoint already durable on disk; leave file untouched.
                return JournalHandle(
                    path=target,
                    status=STATUS_OK,
                    detail="checkpoint unchanged; no rewrite required",
                    state=_clone_state(state),
                    pin=new_pin,
                    byte_size=current.byte_size,
                    namespace=JOURNAL_NAMESPACE,
                    loaded_at_revision=state.revision,
                    existed=True,
                )
            assert current.state is not None
            _verify_one_step_transition(
                current.state,
                encoded_bytes,
                new_pin,
                poll,
                authority,
                config=cfg,
                max_bytes=max_bytes,
            )

        _atomic_write_bytes(target, encoded_bytes)

    return JournalHandle(
        path=target,
        status=STATUS_OK,
        detail="saved verified named-v3 journal",
        state=_clone_state(state),
        pin=new_pin,
        byte_size=len(encoded_bytes),
        namespace=JOURNAL_NAMESPACE,
        loaded_at_revision=state.revision,
        existed=True,
    )
