"""Offline durable fake-effect recovery proof for P2 weekly observations (Slice 4B).

Scope & Contract
----------------
This module proves a bounded, strictly offline, fake-only effect/recovery lifecycle
around accepted read-only ``weekly_binding.RepositoryBinding`` candidate intents and
genuine local ``weekly_journal`` (``named-v3``) checkpoints.

* **At-most-one local test model**: under a cooperating local POSIX lock
  (``fcntl.flock`` on ``<checkpoint>.lock``) and atomic temp-file replacement
  (``mkstemp`` + ``fsync`` + ``os.replace``), an intent transitions explicitly
  ``pending`` -> ``attempted`` BEFORE any potentially effectful fake service call.
  Once ``attempted``, the action is NEVER reissued, even after crash, ambiguous
  callback failure, incomplete readback, witness loss, or unattributed external
  matches; uncertain outcomes remain conservatively ``held``. This is an at-most-one
  attempt guarantee under a cooperating *local* test model — NOT an exactly-once
  remote API claim and NOT a shared-cache freshness proof.
* **Closed-world concrete fake-only backend**: effects may touch ONLY a concrete
  in-memory ``FakeIssueService`` hydrated from synthetic fixture data via a concrete
  ``FakeEffectTransport``. Both classes forbid subclassing and are checked by exact
  runtime type (``type(...) is ...``). No duck-typed store delegation, no externally
  injected mutation callbacks, and no ``LiveGh`` or wrapped forge ports are accepted.
* **Restart & witness boundary**: local causal correlation witnesses live inside
  ``FakeIssueService``'s backing state *outside* the canonical repository envelope.
  Recreating a fresh ``FakeEffectTransport(service)`` coordinator while the
  independent ``FakeIssueService`` persists proves coordinator restart recovery
  against a live fake service — NOT dual-side process crash recovery. If the fake
  service's process-local witness disappears, restart conservatively ``holds`` and
  never replays. A real forge does NOT supply this local correlation metadata; this
  harness does NOT create a live deployment seam.
* **No write authorization or journal settlement**: candidate intents, checkpoints,
  and confirmed ``EffectReceipt`` outputs always enforce ``write_authorized=False``,
  ``write_readiness=False``, and ``journal_settled=False``. The ``named-v3`` journal
  is read-only here; bucket removal / canonical settlement is deliberately out of
  scope and recorded below as a later-slice requirement.
* **Inline envelopes only**: complex comment-backed record layouts
  (``candidateRecords`` / ``rowStorage``) are conservatively declined.
* **Journal freshness & provenance**: checkpoint digests prove local integrity only,
  never provenance, currentness, or authority. Both preflight and confirmation/recovery
  re-read and validate the local ``named-v3`` journal via ``load_journal``; if the
  journal changed between intent persistence and confirmation, confirmation is refused
  rather than resurrecting stale scope.

Later-Slice Requirements (Not Implemented Here)
-----------------------------------------------
1. **Canonical bucket settlement / removal**: consuming a verified ``EffectReceipt``
   to settle or clear specific ``(repository, named_id)`` buckets in ``named-v3``
   without losing sibling buckets, concurrent new sightings, or audit history.
2. **Real forge causal recovery**: real GitHub REST/GraphQL APIs do not provide
   ``FakeIssueService``'s out-of-band attempt witness; real-world recovery must
   either use a ratified causal protocol or hold conservatively on unattributable
   matches.
3. **Records-mode comment layouts**: two-phase comment generation and recovery for
   oversized repository envelopes.
4. **Live write authorization & rollout**: operator/policy gating, live transport
   wiring, and multi-host/shared-cache concurrency controls.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from scripts.upstream_watcher import (
    batch,
    envelope,
    records,
    repository_batch,
    weekly_binding as wb,
    weekly_journal as wj,
)
from scripts.upstream_watcher.approval import PayloadError, extract_payload
from scripts.upstream_watcher.live import GhError, mentions_suite, umbrella_suite
from scripts.upstream_watcher.weekly_collector import _exact_structural_equal
from scripts.upstream_watcher.weekly_journal import (
    BLOCKED_STATUSES,
    DEFAULT_MAX_JOURNAL_BYTES,
    STATUS_STALE,
    JournalPin,
    load_journal,
)
from scripts.upstream_watcher.weekly_reducer import (
    DECISION_FLUSH,
    DECISION_URGENT,
    FirstSeenPin,
    ReducerConfig,
    ReducerState,
    _canonical_json_digest,
    _freeze_mapping,
    format_utc,
    parse_strict_utc,
)

INTENT_FORMAT = "gaia-upstream-weekly-fake-effect-intent"
INTENT_NAMESPACE = "fake-effect-intent-v1"
INTENT_VERSION = 1
DEFAULT_MAX_INTENT_BYTES = 2 * 1024 * 1024

INTENT_STATE_PENDING = "pending"
INTENT_STATE_ATTEMPTED = "attempted"
INTENT_STATE_CONFIRMED = "confirmed"
INTENT_STATE_HELD = "held"
VALID_INTENT_STATES = frozenset(
    {
        INTENT_STATE_PENDING,
        INTENT_STATE_ATTEMPTED,
        INTENT_STATE_CONFIRMED,
        INTENT_STATE_HELD,
    }
)

EFFECT_STATUS_CONFIRMED = "confirmed"
EFFECT_STATUS_HELD = "held"
EFFECT_STATUS_REFUSED = "refused"

_ALLOWED_ACTIONS = frozenset({"create", "update"})
_ELIGIBLE_DECISIONS = frozenset({DECISION_FLUSH, DECISION_URGENT})
_MAX_JSON_DEPTH = 64
_MAX_JSON_INT_DIGITS = 128
_MAX_JSON_FLOAT_CHARS = 128

_INTENT_TOP_KEYS = frozenset(
    {
        "format",
        "namespace",
        "intentVersion",
        "state",
        "attemptId",
        "correlationId",
        "journalPath",
        "journalPin",
        "pollId",
        "observedAt",
        "repository",
        "selectedMembers",
        "preservedSiblings",
        "target",
        "envelopeSha256",
        "expectedBodySha256",
        "holdReason",
        "receipt",
        "writeAuthorized",
        "writeReadiness",
        "journalSettled",
        "digest",
    }
)
_PIN_OBJ_KEYS = frozenset({"revision", "digest"})
_MEMBER_KEYS = frozenset(
    {
        "namedId",
        "decision",
        "bucketRevision",
        "sourceUrl",
        "newVersion",
        "findingSha256",
        "rowPins",
    }
)
_ROW_PIN_KEYS = frozenset({"firstSeenVersion", "evidenceUrl", "firstSeenAt", "firstSeenPollId"})
_TARGET_KEYS = frozenset({"action", "umbrella", "title", "preSnapshot", "preAbsent"})
_SNAPSHOT_KEYS = frozenset({"updatedAt", "bodySha256"})
_RECEIPT_KEYS = frozenset(
    {
        "attemptId",
        "correlationId",
        "action",
        "repository",
        "umbrella",
        "title",
        "postSnapshot",
        "envelopeSha256",
        "bodySha256",
        "selectedFindingDigests",
        "preservedSiblingDigests",
        "journalPin",
        "causalWitnessId",
        "writeAuthorized",
        "writeReadiness",
        "journalSettled",
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FakeEffectError(RuntimeError):
    """Base error for offline fake-effect recovery."""


class IntentValidationError(FakeEffectError):
    """Raised when a local intent checkpoint is corrupt, foreign, or contradictory."""


class FakeEffectTransportError(FakeEffectError):
    """Raised when the fake-only service/transport refuses or fails an operation."""


class FakeEffectAmbiguousError(FakeEffectTransportError):
    """Raised when a fake effect call fails ambiguously (post-call state uncertain)."""


# ---------------------------------------------------------------------------
# Public immutable data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FakeCausalWitness:
    """Fake-only local causal correlation witness stored OUTSIDE the canonical envelope.

    Owned by ``FakeIssueService`` backing state. A real GitHub forge does not supply
    this metadata; it exists solely in this offline harness to distinguish this local
    attempt's fake write from unrelated external writes carrying an identical payload.
    """

    witness_id: str
    attempt_id: str
    correlation_id: str
    action: str
    repository: str
    issue_number: int
    pre_snapshot: Mapping[str, str] | None
    post_snapshot: Mapping[str, str]
    envelope_sha256: str
    body_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pre_snapshot",
            _freeze_mapping(self.pre_snapshot) if self.pre_snapshot is not None else None,
        )
        object.__setattr__(self, "post_snapshot", _freeze_mapping(self.post_snapshot))


@dataclass(frozen=True)
class IntentMemberSpec:
    """Pinned per-named scope specification recorded inside a pending intent."""

    named_id: str
    decision: str
    bucket_revision: int
    source_url: str
    new_version: str
    finding_sha256: str
    row_pins: Mapping[str, FirstSeenPin]

    def __post_init__(self) -> None:
        object.__setattr__(self, "row_pins", _freeze_mapping(self.row_pins))


@dataclass(frozen=True)
class IntentTargetSpec:
    """Pinned target action and pre-state snapshot (or exact create absence)."""

    action: str  # "create" | "update"
    umbrella: int | None
    title: str
    pre_snapshot: Mapping[str, str] | None
    pre_absent: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pre_snapshot",
            _freeze_mapping(self.pre_snapshot) if self.pre_snapshot is not None else None,
        )


@dataclass(frozen=True)
class EffectReceipt:
    """Separately validated fake-effect receipt (output only; never settles journal)."""

    attempt_id: str
    correlation_id: str
    action: str
    repository: str
    umbrella: int
    title: str
    post_snapshot: Mapping[str, str]
    envelope_sha256: str
    body_sha256: str
    selected_finding_digests: Mapping[str, str]
    preserved_sibling_digests: Mapping[str, str]
    journal_pin: JournalPin
    causal_witness_id: str
    write_authorized: bool = False
    write_readiness: bool = False
    journal_settled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "post_snapshot", _freeze_mapping(self.post_snapshot))
        object.__setattr__(self, "selected_finding_digests", _freeze_mapping(self.selected_finding_digests))
        object.__setattr__(self, "preserved_sibling_digests", _freeze_mapping(self.preserved_sibling_digests))
        object.__setattr__(self, "write_authorized", False)
        object.__setattr__(self, "write_readiness", False)
        object.__setattr__(self, "journal_settled", False)


@dataclass(frozen=True)
class PendingEffectIntent:
    """Versioned local intent checkpoint stored in its own namespace."""

    state: str
    attempt_id: str
    correlation_id: str
    journal_path: str
    journal_pin: JournalPin
    poll_id: str
    observed_at: str
    repository: str
    selected_members: tuple[IntentMemberSpec, ...]
    preserved_siblings: Mapping[str, str]
    target: IntentTargetSpec
    envelope_sha256: str
    expected_body_sha256: str
    digest: str
    hold_reason: str | None = None
    receipt: EffectReceipt | None = None
    write_authorized: bool = False
    write_readiness: bool = False
    journal_settled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "preserved_siblings", _freeze_mapping(self.preserved_siblings))
        object.__setattr__(self, "write_authorized", False)
        object.__setattr__(self, "write_readiness", False)
        object.__setattr__(self, "journal_settled", False)


@dataclass(frozen=True)
class EffectExecutionResult:
    """Top-level outcome of executing or recovering one bounded fake effect."""

    status: str  # "confirmed" | "held" | "refused"
    reason: str | None
    intent: PendingEffectIntent | None
    receipt: EffectReceipt | None
    recovered: bool = False
    effect_called: bool = False
    write_authorized: bool = False
    write_readiness: bool = False
    journal_settled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "write_authorized", False)
        object.__setattr__(self, "write_readiness", False)
        object.__setattr__(self, "journal_settled", False)


# ---------------------------------------------------------------------------
# Closed-world concrete fake-only service and transport (no duck-typed ports)
# ---------------------------------------------------------------------------


def _normalize_fixture_issue(raw: Any, fallback_stamp: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TypeError("FakeIssueService fixture issue must be a mapping")
    row = copy.deepcopy(dict(raw))
    num = row.get("number")
    if type(num) is not int or num < 1:
        raise ValueError("FakeIssueService fixture issue requires a positive integer number")
    row.setdefault("state", "open")
    row.setdefault("updated_at", fallback_stamp)
    row.setdefault("body", "")
    row["labels"] = [
        {"name": lbl} if isinstance(lbl, str) else copy.deepcopy(lbl)
        for lbl in row.get("labels", [])
    ]
    return row


class FakeIssueService:
    """Closed-world in-memory fake issue service hydrated from synthetic fixture data only.

    Accepts NO external store objects, NO forge clients, and NO mutation callbacks.
    Owns both the synthetic issue/comment store and the out-of-band ``FakeCausalWitness``
    ledger so a fresh ``FakeEffectTransport(service)`` coordinator can recover across
    adapter recreation while this fake service stays alive.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("FakeIssueService is closed-world and cannot be subclassed")

    def __init__(
        self,
        issues: Sequence[Mapping[str, Any]] = (),
        *,
        comments: Mapping[int, Sequence[Mapping[str, Any]]] | None = None,
        repo: str = "gaia-research/gaia-skill-tree",
        next_number: int = 5000,
    ) -> None:
        if type(next_number) is not int or next_number < 1:
            raise ValueError("next_number must be a positive integer")
        self.repo = envelope.repository(repo)
        self._issues: dict[int, dict[str, Any]] = {}
        self._comments: dict[int, list[dict[str, Any]]] = {}
        self._writes: list[tuple[Any, ...]] = []
        self._attempt_calls: list[tuple[str, str, int | None]] = []
        self._witnesses_by_attempt: dict[str, FakeCausalWitness] = {}
        self._witness_seq = 0
        self._clock = 0
        self._next_number = next_number

        # Data-only failure injection flags (no external callables).
        self.fail_list: bool = False
        self.fail_get: bool = False
        self.fail_before_effect_once: bool = False
        self.fail_after_effect_once: bool = False

        for issue in issues:
            self.seed_issue(issue)
        if comments is not None:
            for num, rows in comments.items():
                if type(num) is not int or num < 1:
                    raise ValueError("comment issue number must be a positive integer")
                self._comments[num] = [copy.deepcopy(dict(r)) for r in rows]

    def _stamp(self) -> str:
        self._clock += 1
        minutes, seconds = divmod(self._clock, 60)
        return f"2026-11-19T12:{minutes % 60:02d}:{seconds:02d}Z"

    # -- Fixture seeding & test inspection (data-only) --

    @property
    def writes(self) -> tuple[tuple[Any, ...], ...]:
        return tuple(self._writes)

    @property
    def attempt_calls(self) -> tuple[tuple[str, str, int | None], ...]:
        return tuple(self._attempt_calls)

    @property
    def issue_numbers(self) -> frozenset[int]:
        return frozenset(self._issues)

    def snapshot_issue(self, number: int) -> dict[str, Any]:
        return copy.deepcopy(self._issues[number])

    def seed_issue(self, issue: Mapping[str, Any]) -> dict[str, Any]:
        row = _normalize_fixture_issue(issue, self._stamp())
        self._issues[row["number"]] = row
        self._next_number = max(self._next_number, row["number"] + 1)
        return copy.deepcopy(row)

    def remove_issue(self, number: int) -> None:
        self._issues.pop(number, None)

    def external_create_issue(self, title: str, labels: Sequence[str], body: str) -> int:
        """Simulate an external actor creating an issue WITHOUT recording a causal witness."""
        number = self._next_number
        self._next_number += 1
        self._issues[number] = {
            "number": number,
            "title": title,
            "state": "open",
            "body": body,
            "labels": [{"name": lbl} for lbl in labels],
            "updated_at": self._stamp(),
        }
        self._writes.append(("external-create", number, title))
        return number

    def external_edit_issue(self, number: int, title: str, body: str) -> None:
        """Simulate an external actor editing an issue WITHOUT recording a causal witness."""
        self._issues[number].update({"title": title, "body": body, "updated_at": self._stamp()})
        self._writes.append(("external-edit", number))

    def clear_witnesses(self) -> None:
        """Simulate loss of process-local fake witness state."""
        self._witnesses_by_attempt.clear()

    # -- Read-only inventory surface over owned fixture state --

    def list_issues(self, state: str, since: str | None = None, labels: str | None = None) -> list[dict[str, Any]]:
        if self.fail_list:
            raise GhError("fake-list-failed")
        wanted = set(filter(None, (labels or "").split(",")))
        rows = [
            copy.deepcopy(row)
            for row in self._issues.values()
            if (state == "all" or row["state"] == state)
            and (not since or str(row.get("updated_at") or "") >= since)
            and wanted <= {lbl["name"] for lbl in row["labels"] if isinstance(lbl, dict) and isinstance(lbl.get("name"), str)}
        ]
        return sorted(rows, key=lambda r: r["number"])

    def get_issue(self, number: int) -> dict[str, Any]:
        if self.fail_get:
            raise GhError("fake-get-failed")
        if number not in self._issues:
            raise GhError("fake-issue-missing")
        return copy.deepcopy(self._issues[number])

    def list_comments(self, number: int) -> list[dict[str, Any]]:
        return [copy.deepcopy(row) for row in self._comments.get(number, [])]

    def child_state(self, number: int) -> str:
        if self.fail_get:
            raise GhError("fake-get-failed")
        row = self._issues.get(number)
        if row is None:
            return "absent"
        if row["state"] != "closed":
            return "open"
        names = {lbl["name"] for lbl in row["labels"] if isinstance(lbl, dict)}
        return "closed-rejected" if "upstream:rejected" in names else "closed"

    # -- Internal closed-world fake effect methods (called only by FakeEffectTransport) --

    def _next_witness_id(self, attempt_id: str) -> str:
        self._witness_seq += 1
        token = hashlib.sha256(f"{attempt_id}:{self._witness_seq}".encode("utf-8")).hexdigest()[:24]
        return f"fake-witness-{self._witness_seq}-{token}"

    def _apply_fake_create(
        self,
        *,
        title: str,
        labels: Sequence[str],
        body: str,
        attempt_id: str,
        correlation_id: str,
        repository: str,
        envelope_sha256: str,
    ) -> int:
        if attempt_id in self._witnesses_by_attempt:
            raise FakeEffectTransportError("duplicate-fake-attempt-id")
        self._attempt_calls.append(("create", attempt_id, None))
        if self.fail_before_effect_once:
            self.fail_before_effect_once = False
            raise FakeEffectAmbiguousError("simulated-fail-before-fake-create")

        number = self._next_number
        self._next_number += 1
        row = {
            "number": number,
            "title": title,
            "state": "open",
            "body": body,
            "labels": [{"name": lbl} for lbl in labels],
            "updated_at": self._stamp(),
        }
        self._issues[number] = row
        self._writes.append(("create", number, title))
        self._witnesses_by_attempt[attempt_id] = FakeCausalWitness(
            witness_id=self._next_witness_id(attempt_id),
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            action="create",
            repository=repository,
            issue_number=number,
            pre_snapshot=None,
            post_snapshot=batch.snapshot_of(row),
            envelope_sha256=envelope_sha256,
            body_sha256=batch.body_hash(body),
        )
        if self.fail_after_effect_once:
            self.fail_after_effect_once = False
            raise FakeEffectAmbiguousError("simulated-fail-after-fake-create")
        return number

    def _apply_fake_update(
        self,
        *,
        number: int,
        title: str,
        body: str,
        pre_snapshot: Mapping[str, str],
        attempt_id: str,
        correlation_id: str,
        repository: str,
        envelope_sha256: str,
        reset_approved_label: bool = False,
    ) -> None:
        if attempt_id in self._witnesses_by_attempt:
            raise FakeEffectTransportError("duplicate-fake-attempt-id")
        self._attempt_calls.append(("update", attempt_id, number))
        if self.fail_before_effect_once:
            self.fail_before_effect_once = False
            raise FakeEffectAmbiguousError("simulated-fail-before-fake-update")

        current = self._issues.get(number)
        if current is None or current.get("state") != "open" or "pull_request" in current:
            raise FakeEffectTransportError("fake-target-not-open-issue")
        if batch.snapshot_of(current) != dict(pre_snapshot):
            raise FakeEffectTransportError("fake-pre-snapshot-mismatch")

        if reset_approved_label and "upstream:approved" in batch.label_names(current):
            names = [lbl["name"] for lbl in current["labels"]]
            names = [n for n in names if n != "upstream:approved"]
            if "upstream:needs-info" not in names:
                names.append("upstream:needs-info")
            current["labels"] = [{"name": n} for n in names]
            self._writes.append(("labels", number, ("upstream:needs-info",), ("upstream:approved",)))

        current.update({"title": title, "body": body, "updated_at": self._stamp()})
        self._writes.append(("edit", number))
        self._witnesses_by_attempt[attempt_id] = FakeCausalWitness(
            witness_id=self._next_witness_id(attempt_id),
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            action="update",
            repository=repository,
            issue_number=number,
            pre_snapshot=dict(pre_snapshot),
            post_snapshot=batch.snapshot_of(current),
            envelope_sha256=envelope_sha256,
            body_sha256=batch.body_hash(body),
        )
        if self.fail_after_effect_once:
            self.fail_after_effect_once = False
            raise FakeEffectAmbiguousError("simulated-fail-after-fake-update")

    def _lookup_witness(self, *, attempt_id: str, correlation_id: str) -> FakeCausalWitness | None:
        witness = self._witnesses_by_attempt.get(attempt_id)
        if witness is None or witness.correlation_id != correlation_id:
            return None
        return witness


class FakeEffectTransport:
    """Closed-world coordinator adapter bound exclusively to a concrete ``FakeIssueService``.

    Rejects any non-``FakeIssueService`` object (including ``LiveGh``, wrapped/duck-typed
    forge clients, or subclasses). Holds no witness state of its own, so tests can
    instantiate a fresh ``FakeEffectTransport(service)`` on coordinator restart.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("FakeEffectTransport is closed-world and cannot be subclassed")

    def __init__(self, service: FakeIssueService) -> None:
        if type(service) is not FakeIssueService:
            raise TypeError("FakeEffectTransport requires an exact FakeIssueService instance")
        self._service = service
        self.repo = service.repo

    @property
    def service(self) -> FakeIssueService:
        return self._service

    def list_issues(self, state: str, since: str | None = None, labels: str | None = None) -> list[dict[str, Any]]:
        return self._service.list_issues(state, since=since, labels=labels)

    def get_issue(self, number: int) -> dict[str, Any]:
        return self._service.get_issue(number)

    def list_comments(self, number: int) -> list[dict[str, Any]]:
        return self._service.list_comments(number)

    def child_state(self, number: int) -> str:
        return self._service.child_state(number)

    def fake_create_umbrella(
        self,
        *,
        title: str,
        labels: Sequence[str],
        body: str,
        attempt_id: str,
        correlation_id: str,
        repository: str,
        envelope_sha256: str,
    ) -> int:
        return self._service._apply_fake_create(
            title=title,
            labels=labels,
            body=body,
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            repository=repository,
            envelope_sha256=envelope_sha256,
        )

    def fake_update_umbrella(
        self,
        *,
        number: int,
        title: str,
        body: str,
        pre_snapshot: Mapping[str, str],
        attempt_id: str,
        correlation_id: str,
        repository: str,
        envelope_sha256: str,
        reset_approved_label: bool = False,
    ) -> None:
        self._service._apply_fake_update(
            number=number,
            title=title,
            body=body,
            pre_snapshot=pre_snapshot,
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            repository=repository,
            envelope_sha256=envelope_sha256,
            reset_approved_label=reset_approved_label,
        )

    def lookup_causal_witness(self, *, attempt_id: str, correlation_id: str) -> FakeCausalWitness | None:
        return self._service._lookup_witness(attempt_id=attempt_id, correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# Strict JSON, deterministic identity, locking & atomic persistence helpers
# ---------------------------------------------------------------------------


def _is_clean_str(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
    )


def _require_clean_str(value: Any, label: str) -> str:
    if not _is_clean_str(value):
        raise IntentValidationError(f"invalid-{label}")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not envelope.SHA.fullmatch(value):
        raise IntentValidationError(f"invalid-{label}")
    return value


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise IntentValidationError(f"invalid-{label}")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise IntentValidationError(f"invalid-{label}")
    return value


def _require_canonical_utc(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise IntentValidationError(f"invalid-{label}")
    try:
        canonical = format_utc(parse_strict_utc(value))
    except ValueError:
        raise IntentValidationError(f"invalid-{label}") from None
    if canonical != value:
        raise IntentValidationError(f"non-canonical-{label}")
    return canonical


def _unique_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise IntentValidationError("duplicate-json-key")
        out[key] = value
    return out


def _reject_non_finite(_constant: str) -> Any:
    raise IntentValidationError("non-finite-json-constant")


def _parse_bounded_int(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    if len(digits) > _MAX_JSON_INT_DIGITS:
        raise IntentValidationError("json-int-too-large")
    return int(token)


def _parse_bounded_float(token: str) -> float:
    if len(token) > _MAX_JSON_FLOAT_CHARS:
        raise IntentValidationError("json-float-too-large")
    value = float(token)
    if not math.isfinite(value):
        raise IntentValidationError("non-finite-json-constant")
    return value


def _validate_json_depth(root: Any, *, max_depth: int = _MAX_JSON_DEPTH) -> None:
    stack: list[tuple[Any, int]] = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, dict):
            if depth > max_depth:
                raise IntentValidationError("json-depth-exceeded")
            for value in node.values():
                if isinstance(value, (dict, list)):
                    stack.append((value, depth + 1))
        elif isinstance(node, list):
            if depth > max_depth:
                raise IntentValidationError("json-depth-exceeded")
            for item in node:
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))


def _parse_bounded_json(text: str) -> Any:
    try:
        data = json.loads(
            text,
            object_pairs_hook=_unique_object_pairs,
            parse_constant=_reject_non_finite,
            parse_int=_parse_bounded_int,
            parse_float=_parse_bounded_float,
        )
    except (ValueError, RecursionError):
        raise IntentValidationError("malformed-intent-json") from None
    _validate_json_depth(data)
    return data


def _intent_digest(payload: Mapping[str, Any]) -> str:
    without_digest = {k: v for k, v in payload.items() if k != "digest"}
    encoded = json.dumps(
        without_digest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _serialize_member_spec(member: IntentMemberSpec) -> dict[str, Any]:
    return {
        "namedId": member.named_id,
        "decision": member.decision,
        "bucketRevision": member.bucket_revision,
        "sourceUrl": member.source_url,
        "newVersion": member.new_version,
        "findingSha256": member.finding_sha256,
        "rowPins": {
            row_id: {
                "firstSeenVersion": pin.first_seen_version,
                "evidenceUrl": pin.evidence_url,
                "firstSeenAt": pin.first_seen_at,
                "firstSeenPollId": pin.first_seen_poll_id,
            }
            for row_id, pin in sorted(member.row_pins.items())
        },
    }


def _serialize_target_spec(target: IntentTargetSpec) -> dict[str, Any]:
    return {
        "action": target.action,
        "umbrella": target.umbrella,
        "title": target.title,
        "preSnapshot": dict(target.pre_snapshot) if target.pre_snapshot is not None else None,
        "preAbsent": target.pre_absent,
    }


def _compute_attempt_identity(
    *,
    journal_pin: JournalPin,
    poll_id: str,
    observed_at: str,
    repository: str,
    selected_members: tuple[IntentMemberSpec, ...],
    preserved_siblings: Mapping[str, str],
    target: IntentTargetSpec,
    envelope_sha256: str,
    expected_body_sha256: str,
) -> tuple[str, str]:
    basis = {
        "namespace": INTENT_NAMESPACE,
        "intentVersion": INTENT_VERSION,
        "journalPin": {"revision": journal_pin.revision, "digest": journal_pin.digest},
        "pollId": poll_id,
        "observedAt": observed_at,
        "repository": repository,
        "selectedMembers": [_serialize_member_spec(m) for m in selected_members],
        "preservedSiblings": {k: preserved_siblings[k] for k in sorted(preserved_siblings)},
        "target": _serialize_target_spec(target),
        "envelopeSha256": envelope_sha256,
        "expectedBodySha256": expected_body_sha256,
    }
    basis_digest = _canonical_json_digest(basis)
    attempt_id = f"fake-attempt-{basis_digest[:32]}"
    corr_digest = _canonical_json_digest({"kind": "fake-local-correlation-v1", "basisDigest": basis_digest})
    correlation_id = f"fake-corr-{corr_digest[:32]}"
    return attempt_id, correlation_id


def _lock_path_for(target: Path) -> Path:
    return target.with_name(f"{target.name}.lock")


def _paths_or_locks_collide(first: Path, second: Path) -> bool:
    first_paths = {first.resolve(), _lock_path_for(first).resolve()}
    second_paths = {second.resolve(), _lock_path_for(second).resolve()}
    return bool(first_paths & second_paths)


@contextmanager
def _exclusive_intent_lock(target: Path) -> Iterator[None]:
    """Acquire an advisory POSIX flock on ``<checkpoint>.lock`` for cooperating local callers."""
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


# ---------------------------------------------------------------------------
# Intent checkpoint codec (encode / decode / load / save)
# ---------------------------------------------------------------------------


def _serialize_receipt(receipt: EffectReceipt) -> dict[str, Any]:
    return {
        "attemptId": receipt.attempt_id,
        "correlationId": receipt.correlation_id,
        "action": receipt.action,
        "repository": receipt.repository,
        "umbrella": receipt.umbrella,
        "title": receipt.title,
        "postSnapshot": dict(receipt.post_snapshot),
        "envelopeSha256": receipt.envelope_sha256,
        "bodySha256": receipt.body_sha256,
        "selectedFindingDigests": {k: receipt.selected_finding_digests[k] for k in sorted(receipt.selected_finding_digests)},
        "preservedSiblingDigests": {k: receipt.preserved_sibling_digests[k] for k in sorted(receipt.preserved_sibling_digests)},
        "journalPin": {"revision": receipt.journal_pin.revision, "digest": receipt.journal_pin.digest},
        "causalWitnessId": receipt.causal_witness_id,
        "writeAuthorized": False,
        "writeReadiness": False,
        "journalSettled": False,
    }


def _encode_intent(intent: PendingEffectIntent) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": INTENT_FORMAT,
        "namespace": INTENT_NAMESPACE,
        "intentVersion": INTENT_VERSION,
        "state": intent.state,
        "attemptId": intent.attempt_id,
        "correlationId": intent.correlation_id,
        "journalPath": intent.journal_path,
        "journalPin": {"revision": intent.journal_pin.revision, "digest": intent.journal_pin.digest},
        "pollId": intent.poll_id,
        "observedAt": intent.observed_at,
        "repository": intent.repository,
        "selectedMembers": [_serialize_member_spec(m) for m in intent.selected_members],
        "preservedSiblings": {k: intent.preserved_siblings[k] for k in sorted(intent.preserved_siblings)},
        "target": _serialize_target_spec(intent.target),
        "envelopeSha256": intent.envelope_sha256,
        "expectedBodySha256": intent.expected_body_sha256,
        "holdReason": intent.hold_reason,
        "receipt": _serialize_receipt(intent.receipt) if intent.receipt is not None else None,
        "writeAuthorized": False,
        "writeReadiness": False,
        "journalSettled": False,
    }
    payload["digest"] = _intent_digest(payload)
    return payload


def _decode_snapshot(raw: Any, label: str) -> dict[str, str]:
    if not isinstance(raw, dict) or set(raw.keys()) != _SNAPSHOT_KEYS:
        raise IntentValidationError(f"invalid-{label}")
    updated_at = raw["updatedAt"]
    if not wb._is_valid_utc_timestamp(updated_at):
        raise IntentValidationError(f"invalid-{label}-updated-at")
    body_sha = _require_sha256(raw["bodySha256"], f"{label}-body-sha")
    return {"updatedAt": updated_at, "bodySha256": body_sha}


def _decode_pin_obj(raw: Any, label: str) -> JournalPin:
    if not isinstance(raw, dict) or set(raw.keys()) != _PIN_OBJ_KEYS:
        raise IntentValidationError(f"invalid-{label}")
    rev = _require_int(raw["revision"], f"{label}-revision", minimum=1)
    dig = _require_sha256(raw["digest"], f"{label}-digest")
    return JournalPin(revision=rev, digest=dig)


def _decode_intent(data: Any) -> PendingEffectIntent:
    if not isinstance(data, dict):
        raise IntentValidationError("intent-root-not-object")
    if set(data.keys()) != _INTENT_TOP_KEYS:
        raise IntentValidationError("intent-keys-mismatch")
    if data["format"] != INTENT_FORMAT or data["namespace"] != INTENT_NAMESPACE:
        raise IntentValidationError("foreign-intent-namespace")
    if _require_int(data["intentVersion"], "intent-version", minimum=1) != INTENT_VERSION:
        raise IntentValidationError("unsupported-intent-version")

    stored_digest = _require_sha256(data["digest"], "intent-digest")
    if _intent_digest(data) != stored_digest:
        raise IntentValidationError("intent-digest-mismatch")

    if (
        _require_bool(data["writeAuthorized"], "write-authorized") is not False
        or _require_bool(data["writeReadiness"], "write-readiness") is not False
        or _require_bool(data["journalSettled"], "journal-settled") is not False
    ):
        raise IntentValidationError("intent-forbids-write-auth-or-settlement")

    state = data["state"]
    if not isinstance(state, str) or state not in VALID_INTENT_STATES:
        raise IntentValidationError("invalid-intent-state")

    journal_path = data["journalPath"]
    if not isinstance(journal_path, str) or not journal_path or any(ord(c) < 32 or ord(c) == 127 for c in journal_path):
        raise IntentValidationError("invalid-journal-path")
    journal_pin = _decode_pin_obj(data["journalPin"], "journal-pin")
    poll_id = _require_clean_str(data["pollId"], "poll-id")
    observed_at = _require_canonical_utc(data["observedAt"], "observed-at")
    try:
        repository = envelope.repository(data["repository"])
    except PayloadError:
        raise IntentValidationError("invalid-repository") from None
    if repository != data["repository"]:
        raise IntentValidationError("repository-not-normalized")

    raw_members = data["selectedMembers"]
    if not isinstance(raw_members, list) or not raw_members or len(raw_members) > envelope.MAX_FINDINGS:
        raise IntentValidationError("invalid-selected-members")
    members: list[IntentMemberSpec] = []
    seen_ids: list[str] = []
    for entry in raw_members:
        if not isinstance(entry, dict) or set(entry.keys()) != _MEMBER_KEYS:
            raise IntentValidationError("malformed-selected-member")
        named_id = entry["namedId"]
        if not isinstance(named_id, str) or not envelope.IDENTIFIER.fullmatch(named_id):
            raise IntentValidationError("invalid-member-named-id")
        decision = entry["decision"]
        if not isinstance(decision, str) or decision not in _ELIGIBLE_DECISIONS:
            raise IntentValidationError("invalid-member-decision")
        bucket_rev = _require_int(entry["bucketRevision"], "member-bucket-revision", minimum=1)
        source_url = _require_clean_str(entry["sourceUrl"], "member-source-url")
        new_version = _require_clean_str(entry["newVersion"], "member-new-version")
        try:
            if envelope.release_repository(source_url, new_version) != repository:
                raise IntentValidationError("member-source-disagrees-with-repository")
        except PayloadError:
            raise IntentValidationError("invalid-member-source") from None
        finding_sha = _require_sha256(entry["findingSha256"], "member-finding-sha")
        raw_pins = entry["rowPins"]
        if not isinstance(raw_pins, dict):
            raise IntentValidationError("invalid-member-row-pins")
        row_pins: dict[str, FirstSeenPin] = {}
        for row_id, raw_pin in sorted(raw_pins.items()):
            if not _is_clean_str(row_id) or not isinstance(raw_pin, dict) or set(raw_pin.keys()) != _ROW_PIN_KEYS:
                raise IntentValidationError("malformed-row-pin")
            row_pins[row_id] = FirstSeenPin(
                first_seen_version=_require_clean_str(raw_pin["firstSeenVersion"], "pin-version"),
                evidence_url=_require_clean_str(raw_pin["evidenceUrl"], "pin-url"),
                first_seen_at=_require_canonical_utc(raw_pin["firstSeenAt"], "pin-at"),
                first_seen_poll_id=_require_clean_str(raw_pin["firstSeenPollId"], "pin-poll-id"),
            )
        seen_ids.append(named_id)
        members.append(
            IntentMemberSpec(
                named_id=named_id,
                decision=decision,
                bucket_revision=bucket_rev,
                source_url=source_url,
                new_version=new_version,
                finding_sha256=finding_sha,
                row_pins=row_pins,
            )
        )
    if seen_ids != sorted(set(seen_ids)):
        raise IntentValidationError("selected-members-unordered-or-duplicate")
    selected_tuple = tuple(members)
    selected_set = set(seen_ids)

    raw_siblings = data["preservedSiblings"]
    if not isinstance(raw_siblings, dict):
        raise IntentValidationError("invalid-preserved-siblings")
    preserved_siblings: dict[str, str] = {}
    for sib_id, sib_sha in sorted(raw_siblings.items()):
        if not isinstance(sib_id, str) or not envelope.IDENTIFIER.fullmatch(sib_id) or sib_id in selected_set:
            raise IntentValidationError("invalid-preserved-sibling-id")
        preserved_siblings[sib_id] = _require_sha256(sib_sha, "preserved-sibling-sha")

    raw_target = data["target"]
    if not isinstance(raw_target, dict) or set(raw_target.keys()) != _TARGET_KEYS:
        raise IntentValidationError("malformed-target")
    action = raw_target["action"]
    if not isinstance(action, str) or action not in _ALLOWED_ACTIONS:
        raise IntentValidationError("invalid-target-action")
    title = raw_target["title"]
    if not isinstance(title, str) or not title or any(ord(c) < 32 or ord(c) == 127 for c in title):
        raise IntentValidationError("invalid-target-title")
    pre_absent = _require_bool(raw_target["preAbsent"], "target-pre-absent")
    if action == "create":
        if raw_target["umbrella"] is not None or raw_target["preSnapshot"] is not None or not pre_absent or preserved_siblings:
            raise IntentValidationError("create-target-contradiction")
        target = IntentTargetSpec(action="create", umbrella=None, title=title, pre_snapshot=None, pre_absent=True)
    else:
        umbrella = _require_int(raw_target["umbrella"], "target-umbrella", minimum=1)
        if pre_absent or raw_target["preSnapshot"] is None:
            raise IntentValidationError("update-target-contradiction")
        pre_snapshot = _decode_snapshot(raw_target["preSnapshot"], "pre-snapshot")
        target = IntentTargetSpec(
            action="update",
            umbrella=umbrella,
            title=title,
            pre_snapshot=pre_snapshot,
            pre_absent=False,
        )

    envelope_sha = _require_sha256(data["envelopeSha256"], "envelope-sha")
    expected_body_sha = _require_sha256(data["expectedBodySha256"], "expected-body-sha")

    attempt_id = _require_clean_str(data["attemptId"], "attempt-id")
    correlation_id = _require_clean_str(data["correlationId"], "correlation-id")
    exp_attempt, exp_corr = _compute_attempt_identity(
        journal_pin=journal_pin,
        poll_id=poll_id,
        observed_at=observed_at,
        repository=repository,
        selected_members=selected_tuple,
        preserved_siblings=preserved_siblings,
        target=target,
        envelope_sha256=envelope_sha,
        expected_body_sha256=expected_body_sha,
    )
    if attempt_id != exp_attempt or correlation_id != exp_corr:
        raise IntentValidationError("attempt-or-correlation-identity-mismatch")

    hold_reason = data["holdReason"]
    raw_receipt = data["receipt"]
    receipt: EffectReceipt | None = None

    if state == INTENT_STATE_HELD:
        if not _is_clean_str(hold_reason) or raw_receipt is not None:
            raise IntentValidationError("held-intent-requires-reason-and-no-receipt")
    elif state == INTENT_STATE_CONFIRMED:
        if hold_reason is not None or not isinstance(raw_receipt, dict) or set(raw_receipt.keys()) != _RECEIPT_KEYS:
            raise IntentValidationError("confirmed-intent-requires-valid-receipt")
        if (
            _require_bool(raw_receipt["writeAuthorized"], "receipt-write-auth") is not False
            or _require_bool(raw_receipt["writeReadiness"], "receipt-write-readiness") is not False
            or _require_bool(raw_receipt["journalSettled"], "receipt-journal-settled") is not False
        ):
            raise IntentValidationError("receipt-forbids-write-auth-or-settlement")
        r_pin = _decode_pin_obj(raw_receipt["journalPin"], "receipt-journal-pin")
        r_post = _decode_snapshot(raw_receipt["postSnapshot"], "receipt-post-snapshot")
        r_umbrella = _require_int(raw_receipt["umbrella"], "receipt-umbrella", minimum=1)
        r_sel = raw_receipt["selectedFindingDigests"]
        r_sib = raw_receipt["preservedSiblingDigests"]
        expected_sel = {m.named_id: m.finding_sha256 for m in selected_tuple}
        if (
            raw_receipt["attemptId"] != attempt_id
            or raw_receipt["correlationId"] != correlation_id
            or raw_receipt["action"] != action
            or raw_receipt["repository"] != repository
            or raw_receipt["title"] != title
            or raw_receipt["envelopeSha256"] != envelope_sha
            or raw_receipt["bodySha256"] != expected_body_sha
            or r_pin != journal_pin
            or not isinstance(r_sel, dict)
            or r_sel != expected_sel
            or not isinstance(r_sib, dict)
            or r_sib != preserved_siblings
            or (action == "update" and r_umbrella != target.umbrella)
            or not _is_clean_str(raw_receipt["causalWitnessId"])
        ):
            raise IntentValidationError("receipt-disagrees-with-intent")
        receipt = EffectReceipt(
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            action=action,
            repository=repository,
            umbrella=r_umbrella,
            title=title,
            post_snapshot=r_post,
            envelope_sha256=envelope_sha,
            body_sha256=expected_body_sha,
            selected_finding_digests=expected_sel,
            preserved_sibling_digests=preserved_siblings,
            journal_pin=journal_pin,
            causal_witness_id=raw_receipt["causalWitnessId"],
        )
    else:
        if hold_reason is not None or raw_receipt is not None:
            raise IntentValidationError("pending-or-attempted-cannot-carry-receipt-or-hold")

    return PendingEffectIntent(
        state=state,
        attempt_id=attempt_id,
        correlation_id=correlation_id,
        journal_path=journal_path,
        journal_pin=journal_pin,
        poll_id=poll_id,
        observed_at=observed_at,
        repository=repository,
        selected_members=selected_tuple,
        preserved_siblings=preserved_siblings,
        target=target,
        envelope_sha256=envelope_sha,
        expected_body_sha256=expected_body_sha,
        digest=stored_digest,
        hold_reason=hold_reason,
        receipt=receipt,
    )


def load_intent_checkpoint(
    path: str | os.PathLike[str],
    *,
    max_bytes: int = DEFAULT_MAX_INTENT_BYTES,
) -> tuple[PendingEffectIntent | None, str | None]:
    """Read and strictly validate a local fake-effect intent checkpoint."""
    if type(max_bytes) is not int or max_bytes < 1:
        return None, "invalid-max-intent-bytes"
    if not isinstance(path, (str, os.PathLike)) or not os.fspath(path):
        return None, "invalid-checkpoint-path"
    target = Path(path)
    if not os.path.lexists(target):
        return None, "missing"
    if target.is_symlink() or not target.is_file():
        return None, "corrupt-intent-checkpoint"
    try:
        if target.stat().st_size > max_bytes:
            return None, "oversized-intent-checkpoint"
        with target.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
    except OSError:
        return None, "unreadable-intent-checkpoint"
    if len(raw) > max_bytes:
        return None, "oversized-intent-checkpoint"
    try:
        data = _parse_bounded_json(raw.decode("utf-8"))
        if isinstance(data, dict) and wj.is_legacy_v2_payload(data):
            return None, "foreign-legacy-v2-journal"
        if isinstance(data, dict) and data.get("format") == wj.JOURNAL_FORMAT:
            return None, "foreign-named-v3-journal"
        intent = _decode_intent(data)
    except (UnicodeDecodeError, IntentValidationError) as exc:
        code = str(exc) if isinstance(exc, IntentValidationError) else "corrupt-intent-json"
        return None, code
    return intent, None


def _persist_intent_locked(
    target: Path,
    intent: PendingEffectIntent,
    *,
    max_bytes: int,
) -> PendingEffectIntent:
    payload = _encode_intent(intent)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    raw = text.encode("utf-8")
    if len(raw) > max_bytes:
        raise IntentValidationError("oversized-intent-checkpoint")
    verified = _decode_intent(_parse_bounded_json(raw.decode("utf-8")))
    _atomic_write_bytes(target, raw)
    return verified


def _build_intent_from_binding(
    binding: wb.RepositoryBinding,
    journal_path: Path,
    *,
    state: str = INTENT_STATE_PENDING,
) -> PendingEffectIntent:
    assert binding.target is not None
    assert binding.envelope_sha256 is not None
    assert binding.envelope_body is not None
    members = tuple(
        IntentMemberSpec(
            named_id=m.named_id,
            decision=m.decision,
            bucket_revision=m.bucket_revision,
            source_url=m.source_url,
            new_version=m.new_version,
            finding_sha256=m.finding_sha256,
            row_pins=dict(m.row_pins),
        )
        for m in sorted(binding.selected_members, key=lambda x: x.named_id)
    )
    preserved = {k: binding.target.preserved_siblings[k] for k in sorted(binding.target.preserved_siblings)}
    target_spec = IntentTargetSpec(
        action=binding.target.action,
        umbrella=binding.target.umbrella,
        title=binding.target.title,
        pre_snapshot=dict(binding.target.snapshot) if binding.target.snapshot is not None else None,
        pre_absent=(binding.target.action == "create"),
    )
    expected_body_sha = batch.body_hash(binding.envelope_body)
    attempt_id, correlation_id = _compute_attempt_identity(
        journal_pin=binding.journal_pin,
        poll_id=binding.poll_id,
        observed_at=binding.observed_at,
        repository=binding.repository,
        selected_members=members,
        preserved_siblings=preserved,
        target=target_spec,
        envelope_sha256=binding.envelope_sha256,
        expected_body_sha256=expected_body_sha,
    )
    draft = PendingEffectIntent(
        state=state,
        attempt_id=attempt_id,
        correlation_id=correlation_id,
        journal_path=str(journal_path.resolve()),
        journal_pin=binding.journal_pin,
        poll_id=binding.poll_id,
        observed_at=binding.observed_at,
        repository=binding.repository,
        selected_members=members,
        preserved_siblings=preserved,
        target=target_spec,
        envelope_sha256=binding.envelope_sha256,
        expected_body_sha256=expected_body_sha,
        digest="0" * 64,
    )
    return _decode_intent(_encode_intent(draft))


def _with_state(
    intent: PendingEffectIntent,
    *,
    state: str,
    hold_reason: str | None = None,
    receipt: EffectReceipt | None = None,
) -> PendingEffectIntent:
    draft = PendingEffectIntent(
        state=state,
        attempt_id=intent.attempt_id,
        correlation_id=intent.correlation_id,
        journal_path=intent.journal_path,
        journal_pin=intent.journal_pin,
        poll_id=intent.poll_id,
        observed_at=intent.observed_at,
        repository=intent.repository,
        selected_members=intent.selected_members,
        preserved_siblings=intent.preserved_siblings,
        target=intent.target,
        envelope_sha256=intent.envelope_sha256,
        expected_body_sha256=intent.expected_body_sha256,
        digest="0" * 64,
        hold_reason=hold_reason,
        receipt=receipt,
    )
    return _decode_intent(_encode_intent(draft))


def _intents_same_scope(a: PendingEffectIntent, b: PendingEffectIntent) -> bool:
    return (
        a.attempt_id == b.attempt_id
        and a.correlation_id == b.correlation_id
        and a.journal_path == b.journal_path
        and a.journal_pin == b.journal_pin
        and a.poll_id == b.poll_id
        and a.observed_at == b.observed_at
        and a.repository == b.repository
        and a.selected_members == b.selected_members
        and dict(a.preserved_siblings) == dict(b.preserved_siblings)
        and a.target == b.target
        and a.envelope_sha256 == b.envelope_sha256
        and a.expected_body_sha256 == b.expected_body_sha256
    )


# ---------------------------------------------------------------------------
# Scoped validation: binding, live named-v3 journal, and complete fake readback
# ---------------------------------------------------------------------------


def _refused(
    reason: str,
    *,
    intent: PendingEffectIntent | None = None,
    recovered: bool = False,
    effect_called: bool = False,
) -> EffectExecutionResult:
    return EffectExecutionResult(
        status=EFFECT_STATUS_REFUSED,
        reason=reason,
        intent=intent,
        receipt=None,
        recovered=recovered,
        effect_called=effect_called,
    )


def _held(
    reason: str,
    *,
    intent: PendingEffectIntent | None = None,
    recovered: bool = False,
    effect_called: bool = False,
) -> EffectExecutionResult:
    return EffectExecutionResult(
        status=EFFECT_STATUS_HELD,
        reason=reason,
        intent=intent,
        receipt=None,
        recovered=recovered,
        effect_called=effect_called,
    )


def _verify_live_journal_for_intent(
    *,
    journal_path: Path,
    expected_pin: JournalPin,
    poll_id: str,
    observed_at: str,
    repository: str,
    members: tuple[IntentMemberSpec, ...],
    authority: Mapping[str, dict[str, Any]],
    config: ReducerConfig,
    trusted_latest_pin: JournalPin | None,
    max_journal_bytes: int,
) -> tuple[ReducerState | None, str | None]:
    if trusted_latest_pin is not None and trusted_latest_pin != expected_pin:
        return None, "journal-changed-since-intent"
    handle = load_journal(
        journal_path,
        authority,
        config=config,
        allow_bootstrap=False,
        initialized=True,
        trusted_latest_pin=expected_pin,
        max_bytes=max_journal_bytes,
    )
    if handle.status == STATUS_STALE:
        return None, "journal-changed-since-intent"
    if handle.blocked or handle.state is None or handle.pin is None:
        status = handle.status if handle.status in BLOCKED_STATUSES else "unknown"
        return None, f"local-journal-blocked:{status}"
    if handle.pin != expected_pin:
        return None, "journal-changed-since-intent"

    state = handle.state
    if (
        state.revision != expected_pin.revision
        or state.last_poll_id != poll_id
        or state.last_observed_at != observed_at
    ):
        return None, "journal-state-disagrees-with-intent"

    receipt = state.seen_polls.get(poll_id)
    if receipt is None or not receipt.complete or receipt.observed_at != observed_at:
        return None, "journal-poll-receipt-mismatch"

    for member in members:
        try:
            if envelope.authority_repository(member.named_id, authority) != repository:
                return None, "member-authority-mismatch"
        except PayloadError:
            return None, "member-authority-mismatch"
        bucket = state.buckets.get((repository, member.named_id))
        if (
            bucket is None
            or bucket.revision != member.bucket_revision
            or bucket.last_poll_id != poll_id
            or bucket.last_observed_at != observed_at
            or bucket.latest_finding_sha256 != member.finding_sha256
        ):
            return None, "journal-bucket-disagrees-with-intent"
        for row_id, pin in member.row_pins.items():
            row_hist = bucket.rows.get(row_id)
            if row_hist is None or row_hist.first_seen_pin != pin:
                return None, "journal-row-pin-disagrees-with-intent"
    return state, None


def _validate_binding_input(
    binding: Any,
    journal_path: Path,
    authority: Mapping[str, dict[str, Any]],
    *,
    config: ReducerConfig,
    trusted_latest_pin: JournalPin | None,
    max_journal_bytes: int,
) -> tuple[PendingEffectIntent | None, str | None]:
    if not isinstance(binding, wb.RepositoryBinding):
        return None, "binding-must-be-repository-binding"
    if binding.status != wb.STATUS_CANDIDATE_INTENT:
        return None, f"binding-not-candidate-intent:{binding.status}"
    if binding.write_authorized is not False or binding.write_readiness is not False:
        return None, "binding-unexpectedly-claims-write-auth"
    if not isinstance(binding.journal_pin, JournalPin):
        return None, "missing-binding-journal-pin"
    if binding.target is None or binding.target.action not in _ALLOWED_ACTIONS:
        return None, "binding-target-action-not-executable"
    if (
        not isinstance(binding.envelope_payload, dict)
        or not isinstance(binding.envelope_body, str)
        or not isinstance(binding.envelope_sha256, str)
        or not envelope.SHA.fullmatch(binding.envelope_sha256)
    ):
        return None, "binding-missing-canonical-envelope"
    if "candidateRecords" in binding.envelope_payload or any(
        isinstance(f, dict) and ("rowStorage" in f or "candidateRecords" in f)
        for f in binding.envelope_payload.get("findings", [])
    ):
        return None, "records-comment-layout-out-of-scope"

    try:
        repo = envelope.repository(binding.repository)
    except PayloadError:
        return None, "invalid-binding-repository"
    if repo != binding.repository:
        return None, "binding-repository-not-normalized"

    try:
        expected_title = envelope.title(binding.envelope_payload)
        if binding.target.title != expected_title:
            return None, "binding-title-disagrees-with-envelope"
        envelope.validate(binding.envelope_payload, authority, title=expected_title)
        if binding.envelope_payload.get("payloadSha256") != binding.envelope_sha256:
            return None, "binding-envelope-digest-mismatch"
        parsed_body = envelope.read(binding.envelope_body, authority, title_text=expected_title)
        if not _exact_structural_equal(parsed_body, binding.envelope_payload):
            return None, "binding-body-disagrees-with-envelope"
        if envelope.render(binding.envelope_payload) != binding.envelope_body:
            return None, "binding-body-not-canonical-inline-render"
    except PayloadError:
        return None, "binding-envelope-validation-failed"

    if not binding.selected_members:
        return None, "binding-has-no-selected-members"
    findings_by_id = {f["skillId"]: f for f in binding.envelope_payload["findings"]}
    selected_ids: set[str] = set()
    for member in binding.selected_members:
        if not isinstance(member, wb.BoundNamedMember):
            return None, "invalid-bound-member"
        if (
            member.repository != repo
            or member.poll_id != binding.poll_id
            or member.observed_at != binding.observed_at
            or member.decision not in _ELIGIBLE_DECISIONS
            or member.named_id in selected_ids
        ):
            return None, "binding-member-identity-mismatch"
        selected_ids.add(member.named_id)
        env_finding = findings_by_id.get(member.named_id)
        if (
            env_finding is None
            or env_finding.get("payloadSha256") != member.finding_sha256
            or not _exact_structural_equal(env_finding, member.finding)
        ):
            return None, "binding-member-disagrees-with-envelope"

    preserved = dict(binding.target.preserved_siblings)
    if binding.target.action == "create":
        if (
            binding.target.umbrella is not None
            or binding.target.snapshot is not None
            or preserved
            or binding.target.inventory_proof.get("complete") is not True
            or binding.target.inventory_proof.get("unambiguousAbsence") is not True
            or binding.target.inventory_proof.get("closedAndPrExcluded") is not True
        ):
            return None, "invalid-create-target-binding"
        if set(findings_by_id) != selected_ids:
            return None, "create-envelope-contains-unselected-siblings"
    else:
        if (
            type(binding.target.umbrella) is not int
            or binding.target.umbrella <= 0
            or binding.target.snapshot is None
            or not wb._is_valid_snapshot(dict(binding.target.snapshot))
            or binding.target.inventory_proof.get("complete") is not True
            or binding.target.inventory_proof.get("closedAndPrExcluded") is not True
        ):
            return None, "invalid-update-target-binding"
        if set(findings_by_id) != (selected_ids | set(preserved)):
            return None, "update-envelope-member-set-mismatch"
        for sib_id, sib_sha in preserved.items():
            if sib_id in selected_ids or findings_by_id[sib_id].get("payloadSha256") != sib_sha:
                return None, "preserved-sibling-digest-mismatch"

    try:
        intent = _build_intent_from_binding(binding, journal_path, state=INTENT_STATE_PENDING)
    except IntentValidationError as exc:
        return None, str(exc)

    live_state, err = _verify_live_journal_for_intent(
        journal_path=journal_path,
        expected_pin=intent.journal_pin,
        poll_id=intent.poll_id,
        observed_at=intent.observed_at,
        repository=intent.repository,
        members=intent.selected_members,
        authority=authority,
        config=config,
        trusted_latest_pin=trusted_latest_pin,
        max_journal_bytes=max_journal_bytes,
    )
    if err is not None or live_state is None:
        return None, err or "local-journal-verification-failed"

    for member in binding.selected_members:
        bucket = live_state.buckets[(repo, member.named_id)]
        if not _exact_structural_equal(bucket.latest_finding, member.finding):
            return None, "journal-bucket-finding-disagrees-with-binding"
        for row in member.finding.get("candidates", []):
            row_hist = bucket.rows.get(row["id"])
            if row_hist is None or not _exact_structural_equal(row_hist.latest_row, row):
                return None, "journal-bucket-row-disagrees-with-binding"

    return intent, None


def _read_and_validate_complete_inventory(
    repo: str,
    transport: FakeEffectTransport,
    authority: Mapping[str, dict[str, Any]],
    *,
    policy: dict[str, Any],
    historical_loader: Any,
) -> tuple[dict[str, Any] | None, Any, list[dict[str, Any]] | None, dict[int, dict[str, Any]] | None, str | None]:
    """Perform a real complete fake-inventory readback and history inspection."""
    try:
        raw_adapter = wb._RawInventoryReadAdapter(transport)
        live = repository_batch.read_repository_live(raw_adapter)
        raw_adapter.verify_complete_coverage()
        live = wb._validate_live_inventory(live, authority, raw_adapter=raw_adapter)
    except wb._InventoryValidationError as exc:
        return None, None, None, None, f"incomplete-or-invalid-inventory:{exc.code}"
    except (GhError, PayloadError, OSError, ValueError, TypeError, KeyError):
        return None, None, None, None, "inventory-readback-failed"

    try:
        found, holds, stored = repository_batch.inspect_history(
            repo, live, transport, authority, policy, historical_loader
        )
    except PayloadError as exc:
        msg_lower = str(exc).lower()
        code = "history-ambiguous" if ("ambiguous" in msg_lower or "malformed claimed" in msg_lower) else "history-refused"
        return None, None, None, None, code
    except (GhError, records.RecordError):
        return None, None, None, None, "history-readback-incomplete"
    except (OSError, ValueError, TypeError, KeyError):
        return None, None, None, None, "history-readback-malformed"

    if found.ambiguous:
        return None, None, None, None, "ambiguous-open-umbrella"
    if holds:
        return None, None, None, None, "legacy-migration-hold"
    return live, found, holds, stored, None


def _preflight_fake_effect(
    intent: PendingEffectIntent,
    transport: FakeEffectTransport,
    authority: Mapping[str, dict[str, Any]],
    *,
    policy: dict[str, Any],
    historical_loader: Any,
) -> tuple[bool, str | None]:
    """Verify exact pre-effect fake inventory and target preconditions."""
    live, found, _holds, stored, err = _read_and_validate_complete_inventory(
        intent.repository,
        transport,
        authority,
        policy=policy,
        historical_loader=historical_loader,
    )
    if err is not None or live is None or found is None or stored is None:
        return False, err or "preflight-inventory-failed"

    if intent.target.action == "create":
        if found.canonical is not None or found.duplicates:
            return False, "preflight-create-open-umbrella-exists"
        for issue in live["issues"]:
            if issue.get("state") == "open" and "pull_request" not in issue and "upstream:release" in batch.label_names(issue):
                title_text = issue.get("title") or ""
                if umbrella_suite(title_text) == intent.repository or mentions_suite(title_text, intent.repository):
                    return False, "preflight-create-absence-not-proven"
        return False, None

    canonical = found.canonical
    if (
        canonical is None
        or canonical.get("number") != intent.target.umbrella
        or canonical.get("state") != "open"
        or "pull_request" in canonical
        or "upstream:release" not in batch.label_names(canonical)
        or umbrella_suite(canonical.get("title") or "") != intent.repository
        or any(canonical["number"] >= dup["number"] for dup in found.duplicates)
    ):
        return False, "preflight-update-target-mismatch"

    try:
        current = transport.get_issue(intent.target.umbrella)  # type: ignore[arg-type]
    except GhError:
        return False, "preflight-target-reread-failed"

    current_labels = wb._validated_label_names(current) if isinstance(current, dict) else None
    if (
        not isinstance(current, dict)
        or current.get("number") != intent.target.umbrella
        or current.get("state") != "open"
        or "pull_request" in current
        or not isinstance(current.get("title"), str)
        or current.get("title") != canonical.get("title")
        or not isinstance(current.get("body"), str)
        or not wb._is_valid_utc_timestamp(current.get("updated_at"))
        or current_labels is None
        or "upstream:release" not in current_labels
        or batch.snapshot_of(current) != dict(intent.target.pre_snapshot or {})
    ):
        return False, "preflight-target-snapshot-mismatch"

    try:
        raw_payload, _ = extract_payload(current["body"])
        if not isinstance(raw_payload, dict) or not envelope.is_envelope(raw_payload):
            return False, "preflight-target-not-canonical-envelope"
        if "candidateRecords" in raw_payload:
            return False, "records-comment-layout-out-of-scope"
        current_env = envelope.read(current["body"], authority, title_text=current["title"])
    except PayloadError:
        return False, "preflight-existing-envelope-invalid"

    existing_by_id = {f["skillId"]: f for f in current_env["findings"]}
    for sib_id, sib_sha in intent.preserved_siblings.items():
        existing_sib = existing_by_id.get(sib_id)
        if existing_sib is None or existing_sib.get("payloadSha256") != sib_sha:
            return False, "preflight-preserved-sibling-mismatch"

    return ("upstream:approved" in current_labels), None


def _verify_post_effect_readback(
    intent: PendingEffectIntent,
    transport: FakeEffectTransport,
    authority: Mapping[str, dict[str, Any]],
    *,
    config: ReducerConfig,
    policy: dict[str, Any],
    historical_loader: Any,
    trusted_latest_pin: JournalPin | None,
    max_journal_bytes: int,
) -> tuple[EffectReceipt | None, str | None, bool]:
    """Verify current journal freshness, complete fresh fake inventory, envelope, siblings, and causal witness."""
    _, journal_err = _verify_live_journal_for_intent(
        journal_path=Path(intent.journal_path),
        expected_pin=intent.journal_pin,
        poll_id=intent.poll_id,
        observed_at=intent.observed_at,
        repository=intent.repository,
        members=intent.selected_members,
        authority=authority,
        config=config,
        trusted_latest_pin=trusted_latest_pin,
        max_journal_bytes=max_journal_bytes,
    )
    if journal_err is not None:
        return None, journal_err, True

    live, found, _holds, _stored, inv_err = _read_and_validate_complete_inventory(
        intent.repository,
        transport,
        authority,
        policy=policy,
        historical_loader=historical_loader,
    )
    if inv_err is not None or live is None or found is None:
        return None, inv_err or "post-effect-inventory-incomplete", False

    selected_digests = {m.named_id: m.finding_sha256 for m in intent.selected_members}
    preserved_digests = dict(intent.preserved_siblings)
    expected_member_ids = set(selected_digests) | set(preserved_digests)

    if intent.target.action == "create":
        if found.canonical is None:
            return None, "attempted-without-causal-evidence", False
        if found.duplicates:
            return None, "duplicate-open-umbrellas-after-create", False
        canonical = found.canonical
        target_num = canonical["number"]
        for issue in live["issues"]:
            if (
                issue.get("number") != target_num
                and issue.get("state") == "open"
                and "pull_request" not in issue
                and "upstream:release" in batch.label_names(issue)
            ):
                title_text = issue.get("title") or ""
                if umbrella_suite(title_text) == intent.repository or mentions_suite(title_text, intent.repository):
                    return None, "competing-open-umbrella-after-create", False
    else:
        canonical = found.canonical
        if (
            canonical is None
            or canonical.get("number") != intent.target.umbrella
            or any(canonical["number"] >= dup["number"] for dup in found.duplicates)
        ):
            return None, "post-effect-target-umbrella-mismatch", False
        target_num = canonical["number"]

    try:
        current = transport.get_issue(target_num)
    except GhError:
        return None, "post-effect-target-reread-failed", False

    current_labels = wb._validated_label_names(current) if isinstance(current, dict) else None
    if (
        not isinstance(current, dict)
        or current.get("number") != target_num
        or current.get("state") != "open"
        or "pull_request" in current
        or not isinstance(current.get("title"), str)
        or current.get("title") != canonical.get("title")
        or current.get("title") != intent.target.title
        or not isinstance(current.get("body"), str)
        or not wb._is_valid_utc_timestamp(current.get("updated_at"))
        or current_labels is None
        or "upstream:release" not in current_labels
        or batch.snapshot_of(current) != batch.snapshot_of(canonical)
    ):
        return None, "post-effect-target-state-or-title-mismatch", False

    if intent.target.action == "update" and "upstream:approved" in current_labels:
        return None, "post-effect-approval-label-not-reset", False

    post_snapshot = batch.snapshot_of(current)
    if intent.target.action == "update" and post_snapshot == dict(intent.target.pre_snapshot or {}):
        return None, "post-effect-target-unchanged", False

    if post_snapshot["bodySha256"] != intent.expected_body_sha256:
        return None, "post-effect-body-digest-mismatch", False

    try:
        raw_payload, _ = extract_payload(current["body"])
        if not isinstance(raw_payload, dict) or not envelope.is_envelope(raw_payload):
            return None, "post-effect-not-canonical-envelope", False
        if "candidateRecords" in raw_payload:
            return None, "records-comment-layout-out-of-scope", False
        parsed_env = envelope.read(current["body"], authority, title_text=current["title"])
        envelope.validate(parsed_env, authority, title=intent.target.title)
    except PayloadError:
        return None, "post-effect-envelope-invalid", False

    if parsed_env.get("payloadSha256") != intent.envelope_sha256:
        return None, "post-effect-envelope-digest-mismatch", False

    by_id = {f["skillId"]: f for f in parsed_env["findings"]}
    if set(by_id) != expected_member_ids:
        return None, "post-effect-member-set-mismatch", False
    for named_id, expected_sha in selected_digests.items():
        if by_id[named_id].get("payloadSha256") != expected_sha:
            return None, "post-effect-selected-finding-mismatch", False
    for sib_id, expected_sib_sha in preserved_digests.items():
        if by_id[sib_id].get("payloadSha256") != expected_sib_sha:
            return None, "post-effect-preserved-sibling-mutated", False

    # Fake-only local causal linkage proof: identical payload without attempt witness is NOT confirmed.
    witness = transport.lookup_causal_witness(
        attempt_id=intent.attempt_id,
        correlation_id=intent.correlation_id,
    )
    if witness is None:
        code = "unattributed-matching-create" if intent.target.action == "create" else "unattributed-matching-update"
        return None, code, False

    expected_pre = None if intent.target.action == "create" else dict(intent.target.pre_snapshot or {})
    witness_pre = None if witness.pre_snapshot is None else dict(witness.pre_snapshot)
    if (
        witness.action != intent.target.action
        or witness.repository != intent.repository
        or witness.issue_number != target_num
        or witness_pre != expected_pre
        or dict(witness.post_snapshot) != post_snapshot
        or witness.envelope_sha256 != intent.envelope_sha256
        or witness.body_sha256 != intent.expected_body_sha256
    ):
        return None, "causal-witness-disagrees-with-readback", False

    receipt = EffectReceipt(
        attempt_id=intent.attempt_id,
        correlation_id=intent.correlation_id,
        action=intent.target.action,
        repository=intent.repository,
        umbrella=target_num,
        title=intent.target.title,
        post_snapshot=post_snapshot,
        envelope_sha256=intent.envelope_sha256,
        body_sha256=intent.expected_body_sha256,
        selected_finding_digests=selected_digests,
        preserved_sibling_digests=preserved_digests,
        journal_pin=intent.journal_pin,
        causal_witness_id=witness.witness_id,
    )
    return receipt, None, False


def _reconcile_existing_intent_locked(
    ckpt: Path,
    existing: PendingEffectIntent,
    transport: FakeEffectTransport,
    authority: Mapping[str, dict[str, Any]],
    *,
    cfg: ReducerConfig,
    policy: dict[str, Any] | None,
    historical_loader: Any,
    trusted_latest_pin: JournalPin | None,
    max_journal_bytes: int,
    max_intent_bytes: int,
) -> EffectExecutionResult:
    """Reconcile or recover an already-persisted checkpoint with ZERO fake effect calls."""
    if existing.state == INTENT_STATE_CONFIRMED:
        with wj._exclusive_journal_lock(Path(existing.journal_path)):
            _, journal_err = _verify_live_journal_for_intent(
                journal_path=Path(existing.journal_path),
                expected_pin=existing.journal_pin,
                poll_id=existing.poll_id,
                observed_at=existing.observed_at,
                repository=existing.repository,
                members=existing.selected_members,
                authority=authority,
                config=cfg,
                trusted_latest_pin=trusted_latest_pin,
                max_journal_bytes=max_journal_bytes,
            )
            if journal_err is not None:
                return _refused(journal_err, intent=existing)
        return EffectExecutionResult(
            status=EFFECT_STATUS_CONFIRMED,
            reason=None,
            intent=existing,
            receipt=existing.receipt,
            recovered=False,
            effect_called=False,
        )

    if existing.state == INTENT_STATE_HELD:
        return _held(existing.hold_reason or "intent-previously-held", intent=existing)

    if existing.state == INTENT_STATE_PENDING:
        return _held("pending-intent-not-attempted", intent=existing)

    try:
        resolved_policy = repository_batch.policy_record() if policy is None else policy
    except (PayloadError, OSError, ValueError):
        return _held("policy-record-unavailable", intent=existing)

    receipt, err, must_refuse = _verify_post_effect_readback(
        existing,
        transport,
        authority,
        config=cfg,
        policy=resolved_policy,
        historical_loader=historical_loader,
        trusted_latest_pin=trusted_latest_pin,
        max_journal_bytes=max_journal_bytes,
    )
    if must_refuse:
        return _refused(err or "post-effect-refused", intent=existing)
    if receipt is None:
        return _held(err or "attempted-without-causal-evidence", intent=existing)

    confirmed = _with_state(existing, state=INTENT_STATE_CONFIRMED, receipt=receipt)
    with wj._exclusive_journal_lock(Path(existing.journal_path)):
        _, journal_err = _verify_live_journal_for_intent(
            journal_path=Path(existing.journal_path),
            expected_pin=existing.journal_pin,
            poll_id=existing.poll_id,
            observed_at=existing.observed_at,
            repository=existing.repository,
            members=existing.selected_members,
            authority=authority,
            config=cfg,
            trusted_latest_pin=trusted_latest_pin,
            max_journal_bytes=max_journal_bytes,
        )
        if journal_err is not None:
            return _refused(journal_err, intent=existing)
        persisted = _persist_intent_locked(ckpt, confirmed, max_bytes=max_intent_bytes)
    return EffectExecutionResult(
        status=EFFECT_STATUS_CONFIRMED,
        reason=None,
        intent=persisted,
        receipt=persisted.receipt,
        recovered=True,
        effect_called=False,
    )


# ---------------------------------------------------------------------------
# Public entrypoints: execute_fake_effect and recover_fake_effect
# ---------------------------------------------------------------------------


def recover_fake_effect(
    checkpoint_path: str | os.PathLike[str],
    transport: FakeEffectTransport,
    authority: Mapping[str, dict[str, Any]],
    *,
    binding: wb.RepositoryBinding | None = None,
    journal_path: str | os.PathLike[str] | None = None,
    trusted_latest_pin: JournalPin | None = None,
    config: ReducerConfig | None = None,
    policy: dict[str, Any] | None = None,
    historical_loader: Any = repository_batch.historical_authority,
    max_journal_bytes: int = DEFAULT_MAX_JOURNAL_BYTES,
    max_intent_bytes: int = DEFAULT_MAX_INTENT_BYTES,
) -> EffectExecutionResult:
    """Strictly read-only recovery of a persisted fake-effect intent checkpoint.

    Requires an exact concrete ``FakeEffectTransport`` bound to a concrete
    ``FakeIssueService``. Never invokes any mutating method and never settles
    the ``named-v3`` journal.
    """
    if type(transport) is not FakeEffectTransport:
        return _refused("transport-must-be-fake-effect-transport")
    if type(transport.service) is not FakeIssueService:
        return _held("fake-service-unavailable")
    if not isinstance(authority, Mapping) or not authority:
        return _refused("authority-must-be-non-empty-mapping")
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        return _refused("invalid-reducer-config")
    if trusted_latest_pin is not None and not isinstance(trusted_latest_pin, JournalPin):
        return _refused("invalid-trusted-latest-pin")
    if not isinstance(checkpoint_path, (str, os.PathLike)) or not os.fspath(checkpoint_path):
        return _refused("invalid-checkpoint-path")

    ckpt = Path(checkpoint_path).resolve()
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_intent_lock(ckpt):
        existing, load_err = load_intent_checkpoint(ckpt, max_bytes=max_intent_bytes)
        if load_err == "missing" or existing is None:
            return _refused(f"intent-checkpoint-unavailable:{load_err or 'missing'}")

        existing_journal = Path(existing.journal_path).resolve()
        if _paths_or_locks_collide(ckpt, existing_journal):
            return _refused("checkpoint-path-collides-with-journal", intent=existing)
        if journal_path is not None and str(Path(journal_path).resolve()) != existing.journal_path:
            return _refused("checkpoint-journal-path-mismatch", intent=existing)

        if binding is not None:
            candidate_intent, bind_err = _validate_binding_input(
                binding,
                Path(existing.journal_path),
                authority,
                config=cfg,
                trusted_latest_pin=trusted_latest_pin,
                max_journal_bytes=max_journal_bytes,
            )
            if bind_err is not None or candidate_intent is None:
                return _refused(bind_err or "binding-validation-failed", intent=existing)
            if not _intents_same_scope(existing, candidate_intent):
                return _refused("conflicting-existing-intent", intent=existing)

        return _reconcile_existing_intent_locked(
            ckpt,
            existing,
            transport,
            authority,
            cfg=cfg,
            policy=policy,
            historical_loader=historical_loader,
            trusted_latest_pin=trusted_latest_pin,
            max_journal_bytes=max_journal_bytes,
            max_intent_bytes=max_intent_bytes,
        )


def execute_fake_effect(
    binding: wb.RepositoryBinding,
    journal_path: str | os.PathLike[str],
    checkpoint_path: str | os.PathLike[str],
    transport: FakeEffectTransport,
    authority: Mapping[str, dict[str, Any]],
    *,
    initialized: bool = False,
    trusted_latest_pin: JournalPin | None = None,
    config: ReducerConfig | None = None,
    policy: dict[str, Any] | None = None,
    historical_loader: Any = repository_batch.historical_authority,
    max_journal_bytes: int = DEFAULT_MAX_JOURNAL_BYTES,
    max_intent_bytes: int = DEFAULT_MAX_INTENT_BYTES,
) -> EffectExecutionResult:
    """Persist pending/attempted intent, execute at-most-one fake effect, and confirm via fresh readback.

    Requires an exact concrete ``FakeEffectTransport`` bound to a concrete
    ``FakeIssueService``. If *checkpoint_path* already exists, NEVER reissues a
    fake effect. Never modifies the ``named-v3`` journal and never grants write auth.
    """
    if type(transport) is not FakeEffectTransport:
        return _refused("transport-must-be-fake-effect-transport")
    if type(transport.service) is not FakeIssueService:
        return _refused("fake-service-unavailable")
    if not isinstance(authority, Mapping) or not authority:
        return _refused("authority-must-be-non-empty-mapping")
    if type(initialized) is not bool:
        return _refused("invalid-initialized-flag")
    cfg = config if config is not None else ReducerConfig()
    if not isinstance(cfg, ReducerConfig):
        return _refused("invalid-reducer-config")
    if trusted_latest_pin is not None and not isinstance(trusted_latest_pin, JournalPin):
        return _refused("invalid-trusted-latest-pin")
    if not isinstance(journal_path, (str, os.PathLike)) or not os.fspath(journal_path):
        return _refused("invalid-journal-path")
    if not isinstance(checkpoint_path, (str, os.PathLike)) or not os.fspath(checkpoint_path):
        return _refused("invalid-checkpoint-path")

    jpath = Path(journal_path).resolve()
    ckpt = Path(checkpoint_path).resolve()
    if _paths_or_locks_collide(ckpt, jpath):
        return _refused("checkpoint-path-collides-with-journal")

    ckpt.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_intent_lock(ckpt):
        existing, load_err = load_intent_checkpoint(ckpt, max_bytes=max_intent_bytes)
        if load_err != "missing":
            if existing is None:
                return _refused(f"intent-checkpoint-invalid:{load_err}")
            candidate_intent, bind_err = _validate_binding_input(
                binding,
                jpath,
                authority,
                config=cfg,
                trusted_latest_pin=trusted_latest_pin,
                max_journal_bytes=max_journal_bytes,
            )
            if bind_err is not None or candidate_intent is None:
                return _refused(bind_err or "binding-validation-failed", intent=existing)
            if not _intents_same_scope(existing, candidate_intent):
                return _refused("conflicting-existing-intent", intent=existing)
            return _reconcile_existing_intent_locked(
                ckpt,
                existing,
                transport,
                authority,
                cfg=cfg,
                policy=policy,
                historical_loader=historical_loader,
                trusted_latest_pin=trusted_latest_pin,
                max_journal_bytes=max_journal_bytes,
                max_intent_bytes=max_intent_bytes,
            )

        if initialized:
            return _refused("intent-checkpoint-missing-after-init")

        pending_intent, bind_err = _validate_binding_input(
            binding,
            jpath,
            authority,
            config=cfg,
            trusted_latest_pin=trusted_latest_pin,
            max_journal_bytes=max_journal_bytes,
        )
        if bind_err is not None or pending_intent is None:
            return _refused(bind_err or "binding-validation-failed")

        try:
            resolved_policy = repository_batch.policy_record() if policy is None else policy
        except (PayloadError, OSError, ValueError):
            return _refused("policy-record-unavailable")

        reset_approved, pre_err = _preflight_fake_effect(
            pending_intent,
            transport,
            authority,
            policy=resolved_policy,
            historical_loader=historical_loader,
        )
        if pre_err is not None:
            return _refused(pre_err)

        # Keep the established lock order (checkpoint, then journal). The complete
        # inventory preflight above is deliberately outside the journal lock.
        with wj._exclusive_journal_lock(jpath):
            _, journal_err = _verify_live_journal_for_intent(
                journal_path=jpath,
                expected_pin=pending_intent.journal_pin,
                poll_id=pending_intent.poll_id,
                observed_at=pending_intent.observed_at,
                repository=pending_intent.repository,
                members=pending_intent.selected_members,
                authority=authority,
                config=cfg,
                trusted_latest_pin=trusted_latest_pin,
                max_journal_bytes=max_journal_bytes,
            )
            if journal_err is not None:
                return _refused(journal_err)

            # 1. Durably persist pending, then attempted, before the fake call.
            pending_persisted = _persist_intent_locked(ckpt, pending_intent, max_bytes=max_intent_bytes)
            attempted_intent = _with_state(pending_persisted, state=INTENT_STATE_ATTEMPTED)
            attempted_persisted = _persist_intent_locked(ckpt, attempted_intent, max_bytes=max_intent_bytes)

            # 2. Invoke at-most-one fake effect while this short journal-pin segment
            # prevents a cooperating commit from crossing the final pre-effect check.
            assert binding.envelope_body is not None
            try:
                if attempted_persisted.target.action == "create":
                    transport.fake_create_umbrella(
                        title=attempted_persisted.target.title,
                        labels=["upstream:release", "needs-triage"],
                        body=binding.envelope_body,
                        attempt_id=attempted_persisted.attempt_id,
                        correlation_id=attempted_persisted.correlation_id,
                        repository=attempted_persisted.repository,
                        envelope_sha256=attempted_persisted.envelope_sha256,
                    )
                else:
                    assert attempted_persisted.target.umbrella is not None
                    assert attempted_persisted.target.pre_snapshot is not None
                    transport.fake_update_umbrella(
                        number=attempted_persisted.target.umbrella,
                        title=attempted_persisted.target.title,
                        body=binding.envelope_body,
                        pre_snapshot=attempted_persisted.target.pre_snapshot,
                        attempt_id=attempted_persisted.attempt_id,
                        correlation_id=attempted_persisted.correlation_id,
                        repository=attempted_persisted.repository,
                        envelope_sha256=attempted_persisted.envelope_sha256,
                        reset_approved_label=reset_approved,
                    )
            except (FakeEffectError, GhError):
                return _held("effect-callback-ambiguous", intent=attempted_persisted, effect_called=True)

        # 4. Fresh complete readback + causal witness + journal pin verification.
        receipt, err, must_refuse = _verify_post_effect_readback(
            attempted_persisted,
            transport,
            authority,
            config=cfg,
            policy=resolved_policy,
            historical_loader=historical_loader,
            trusted_latest_pin=trusted_latest_pin,
            max_journal_bytes=max_journal_bytes,
        )
        if must_refuse:
            return _refused(err or "post-effect-refused", intent=attempted_persisted, effect_called=True)
        if receipt is None:
            return _held(err or "attempted-without-causal-evidence", intent=attempted_persisted, effect_called=True)

        # 5. Atomically persist confirmed receipt. If this replace crashes, the checkpoint
        # stays "attempted" on disk and a fresh coordinator recovers without reissuing.
        confirmed_intent = _with_state(attempted_persisted, state=INTENT_STATE_CONFIRMED, receipt=receipt)
        # Readbacks run without the journal lock; revalidate after them, then keep
        # the cooperating journal lock through the atomic receipt replacement.
        with wj._exclusive_journal_lock(jpath):
            _, journal_err = _verify_live_journal_for_intent(
                journal_path=jpath,
                expected_pin=attempted_persisted.journal_pin,
                poll_id=attempted_persisted.poll_id,
                observed_at=attempted_persisted.observed_at,
                repository=attempted_persisted.repository,
                members=attempted_persisted.selected_members,
                authority=authority,
                config=cfg,
                trusted_latest_pin=trusted_latest_pin,
                max_journal_bytes=max_journal_bytes,
            )
            if journal_err is not None:
                return _refused(journal_err, intent=attempted_persisted, effect_called=True)
            confirmed_persisted = _persist_intent_locked(ckpt, confirmed_intent, max_bytes=max_intent_bytes)
        return EffectExecutionResult(
            status=EFFECT_STATUS_CONFIRMED,
            reason=None,
            intent=confirmed_persisted,
            receipt=confirmed_persisted.receipt,
            recovered=False,
            effect_called=True,
        )
