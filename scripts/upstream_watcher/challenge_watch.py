"""
scripts.upstream_watcher.challenge_watch — Bounded Two-Sided Challenge Watch Engine.

Extends the Gaia Upstream Watcher under Yggdrasil IV doctrine (RFC #2148 / D8 /
Ratification 2026-10-25) to track open, independently verified challenges on
both standalone/Unique and suite implementations.

Core Invariants:
1. Two-Sided: Observes both challenged target and traceable comparator
   (releases, commit SHAs, and SKILL.md content events).
2. Verification Gate: No public verified challenge authority without a durable
   independent verification receipt. Raw status strings alone are never accepted
   as proof. Unverified challenges are rejected or restricted to shadow mode.
3. Bounded Run Budget: Hard limits on network requests and evaluated subjects.
4. Durable Semantic Dedup: State stored in .gaia/upstream-watcher/challenge-watch-ledger.json
   deduplicates events across retries and restarts.
5. Availability Probes: Progressive t0 -> +24h -> +72h schedule; elapsed timeout
   NEVER demotes or mutates canonical trust.
6. Observations Only: Description/release events produce verification packets for
   independent testing; descriptions alone cannot prove recovery; no canonical
   score or star mutation.
7. Return to Routine: Targeted monitoring ceases when a challenge is technically
   resolved.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Protocol
from urllib.parse import urlparse

from scripts.lib.github_api import parse_owner_repo, parse_owner_repo_normalized
from scripts.upstream_watcher.transport import (
    BaseTransport,
    Clock,
    HttpTransport,
    Response,
    SystemClock,
)

# ---------------------------------------------------------------------------
# Constants & Authority Notices
# ---------------------------------------------------------------------------

RESOLVED_STATUSES: frozenset[str] = frozenset({
    "technically-rebutted",
    "resolved-by-upstream-improvement",
    "rejected",
})

OPEN_STATUSES: frozenset[str] = frozenset({
    "verified-pending",
    "upheld",
    "narrowed",
})

AUTHORITY_NOTICE: str = (
    "OBSERVATION ONLY. No public verified challenge authority without durable "
    "independent verification receipt. Observations do not prove recovery, "
    "alter Trust Magnitude, or trigger canonical mutation."
)

DEFAULT_LEDGER_PATH = Path(".gaia/upstream-watcher/challenge-watch-ledger.json")
DEFAULT_PACKETS_DIR = Path(".gaia/upstream-watcher/packets")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerificationReceipt:
    """Proof of independent verification required to authorize public watch."""

    receipt_id: str
    verifier_id: str
    verified_at_utc: str
    receipt_ref: str
    challenge_binding_digest: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChallengeTarget:
    """Side A: The challenged skill or suite."""

    subject_id: str
    owner: str
    repo: str
    pinned_version: str | None = None
    pinned_sha: str | None = None
    pinned_content_digest: str | None = None
    watched_paths: tuple[str, ...] = ("SKILL.md",)

    @property
    def repo_slug(self) -> str:
        return f"{self.owner.lower()}/{self.repo.lower()}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "subjectId": self.subject_id,
            "owner": self.owner,
            "repo": self.repo,
            "repoSlug": self.repo_slug,
            "pinnedVersion": self.pinned_version,
            "pinnedSha": self.pinned_sha,
            "pinnedContentDigest": self.pinned_content_digest,
            "watchedPaths": list(self.watched_paths),
        }


@dataclass(frozen=True)
class ChallengeComparator:
    """Side B: The traceable competing implementation or benchmark rival."""

    comparator_id: str
    owner: str | None = None
    repo: str | None = None
    is_traceable: bool = False
    pinned_version: str | None = None
    pinned_sha: str | None = None
    pinned_content_digest: str | None = None

    @property
    def repo_slug(self) -> str | None:
        if self.owner and self.repo:
            return f"{self.owner.lower()}/{self.repo.lower()}"
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparatorId": self.comparator_id,
            "owner": self.owner,
            "repo": self.repo,
            "repoSlug": self.repo_slug,
            "isTraceable": self.is_traceable,
            "pinnedVersion": self.pinned_version,
            "pinnedSha": self.pinned_sha,
            "pinnedContentDigest": self.pinned_content_digest,
        }


@dataclass(frozen=True)
class ValidatedChallenge:
    """A validated challenge admitted to watch (either public or shadow)."""

    challenge_id: str
    claim_id: str
    subject_id: str
    contributor_id: str
    behavior_id: str
    status: str
    material_to_origin: bool
    target: ChallengeTarget
    comparator: ChallengeComparator
    verification_receipt: VerificationReceipt | None
    is_verified: bool
    is_shadow: bool
    created_at_utc: str

    @property
    def is_resolved(self) -> bool:
        return self.status in RESOLVED_STATUSES

    @property
    def is_open(self) -> bool:
        return (not self.is_resolved) and (self.status in OPEN_STATUSES or self.status == "open")

    def to_dict(self) -> dict[str, Any]:
        return {
            "challengeId": self.challenge_id,
            "claimId": self.claim_id,
            "subjectId": self.subject_id,
            "contributorId": self.contributor_id,
            "behaviorId": self.behavior_id,
            "status": self.status,
            "materialToOrigin": self.material_to_origin,
            "target": self.target.to_dict(),
            "comparator": self.comparator.to_dict(),
            "verificationReceipt": self.verification_receipt.to_dict() if self.verification_receipt else None,
            "isVerified": self.is_verified,
            "isShadow": self.is_shadow,
            "createdAtUTC": self.created_at_utc,
        }


@dataclass(frozen=True)
class ObservationPacket:
    """Durable verification packet emitted when upstream change is observed.

    Observations NEVER mutate canonical trust or prove recovery.
    """

    packet_id: str
    challenge_id: str
    subject_id: str
    comparator_id: str | None
    observed_at_utc: str
    trigger_side: str  # "target" | "comparator" | "both" | "availability" | "lifecycle"
    trigger_type: str  # "release" | "commit_sha" | "content_digest" | "availability_probe" | "rate_limit" | "unavailability_review_pending" | "returned_to_routine"
    target_observation: dict[str, Any]
    comparator_observation: dict[str, Any] | None
    requires_independent_verification: bool = True
    canonical_mutation: None = None
    notes: str = ""
    authority_notice: str = AUTHORITY_NOTICE

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "packetId": self.packet_id,
            "challengeId": self.challenge_id,
            "subjectId": self.subject_id,
            "comparatorId": self.comparator_id,
            "observedAtUTC": self.observed_at_utc,
            "triggerSide": self.trigger_side,
            "triggerType": self.trigger_type,
            "targetObservation": self.target_observation,
            "comparatorObservation": self.comparator_observation,
            "requiresIndependentVerification": self.requires_independent_verification,
            "canonicalMutation": self.canonical_mutation,
            "notes": self.notes,
            "authorityNotice": self.authority_notice,
        }
        payload["packetSha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return payload


class ChallengeAdmissionResolver(Protocol):
    """Caller-owned trust boundary; the scheduled CLI deliberately has none."""

    def resolve(self, raw: dict[str, Any], *, registry_map: dict[str, dict] | None,
                allow_shadow: bool) -> tuple[ValidatedChallenge | None, str]: ...


@dataclass
class WatchBudget:
    """Run budget bounding network requests and evaluated subjects."""

    max_requests: int = 20
    max_subjects: int = 10
    requests_used: int = 0
    subjects_evaluated: int = 0

    def can_request(self) -> bool:
        return self.requests_used < self.max_requests

    def record_request(self) -> None:
        self.requests_used += 1

    def can_evaluate_subject(self) -> bool:
        return self.subjects_evaluated < self.max_subjects

    def record_subject(self) -> None:
        self.subjects_evaluated += 1

    @property
    def is_exhausted(self) -> bool:
        return (
            self.requests_used >= self.max_requests
            or self.subjects_evaluated >= self.max_subjects
        )


@dataclass
class ChallengeWatchResult:
    """Summary of a challenge watch execution run."""

    packets: list[ObservationPacket] = field(default_factory=list)
    summaries: list[dict[str, Any]] = field(default_factory=list)
    budget_used: dict[str, int] = field(default_factory=dict)
    active_count: int = 0
    resolved_count: int = 0
    rejected_unverified_count: int = 0
    unavailable_count: int = 0
    budget_exhausted: bool = False


# ---------------------------------------------------------------------------
# Admission is intentionally resolver-only. Tests provide explicit fixtures.


# ---------------------------------------------------------------------------
# Durable Semantic Dedup Ledger
# ---------------------------------------------------------------------------


class WatchLedger:
    """Manages durable state for challenge tracking across retries and restarts."""

    def __init__(self, ledger_path: Path = DEFAULT_LEDGER_PATH, *, shared_store: Any = None) -> None:
        self.path = ledger_path
        self.shared_store = shared_store
        self.ledger_version = 1
        self.last_run_utc: str | None = None
        self.rate_limits: dict[str, str] = {}
        self.emitted_packet_digests: set[str] = set()
        self.packets: dict[str, dict[str, Any]] = {}
        self.inputs: list[dict[str, Any]] = []
        self.challenges: dict[str, dict[str, Any]] = {}
        # A shared transport is authoritative. Never seed it from an ephemeral
        # clone-local file, including when the shared operation has not yet been
        # initialized.
        if self.shared_store is None:
            self._load()
        else:
            from gaia_cli.steward.ledger import LedgerUnavailable
            try:
                document, _ = self.shared_store.load()
                data = document.get("operations", {}).get("upstreamWatcherChallengeWatch")
                if data is not None:
                    self._restore(data)
            except LedgerUnavailable:
                raise

    def _restore(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("shared challenge-watch state must be an object")
        self.ledger_version = data.get("ledger_version", 1)
        self.last_run_utc = data.get("last_run_utc")
        self.rate_limits = data.get("rate_limits", {})
        self.emitted_packet_digests = set(data.get("emitted_packet_digests", []))
        self.packets = data.get("packets", {})
        self.inputs = data.get("inputs", [])
        self.challenges = data.get("challenges", {})
        if not isinstance(self.inputs, list) or not all(isinstance(item, dict) for item in self.inputs):
            raise ValueError("challenge-watch inputs must be a list of objects")
        if not isinstance(self.packets, dict):
            raise ValueError("challenge-watch packets must be an object")
        for packet_id, packet in self.packets.items():
            _verify_packet_payload(packet, packet_id)
        if not isinstance(self.rate_limits, dict) or not isinstance(self.challenges, dict):
            raise ValueError("shared challenge-watch maps must be objects")

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            self.ledger_version = data.get("ledger_version", 1)
            self.last_run_utc = data.get("last_run_utc")
            self.rate_limits = data.get("rate_limits", {})
            self.emitted_packet_digests = set(data.get("emitted_packet_digests", []))
            self.packets = data.get("packets", {})
            self.inputs = data.get("inputs", [])
            self.challenges = data.get("challenges", {})
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] Could not load challenge ledger from {self.path}: {exc}", file=sys.stderr)

    def save(self) -> None:
        payload = {
            "ledger_version": self.ledger_version,
            "last_run_utc": self.last_run_utc,
            "rate_limits": self.rate_limits,
            "emitted_packet_digests": sorted(self.emitted_packet_digests),
            "packets": self.packets,
            "inputs": self.inputs,
            "challenges": self.challenges,
        }
        if self.shared_store is not None:
            from gaia_cli.steward.ledger import update

            def merge(document: dict[str, Any]) -> None:
                operations = document.setdefault("operations", {})
                previous = operations.get("upstreamWatcherChallengeWatch", {})
                # Preserve all unrelated operational metadata and union durable
                # packet identities across CAS retries/processes.
                merged = dict(previous) if isinstance(previous, dict) else {}
                merged.update(payload)
                merged["emitted_packet_digests"] = sorted(
                    set(merged.get("emitted_packet_digests", []))
                    | set(payload["emitted_packet_digests"])
                )
                old_challenges = previous.get("challenges", {}) if isinstance(previous, dict) else {}
                merged["challenges"] = {**old_challenges, **payload["challenges"]}
                old_packets = previous.get("packets", {}) if isinstance(previous, dict) else {}
                merged["packets"] = {**old_packets, **payload["packets"]}
                operations["upstreamWatcherChallengeWatch"] = merged

            update(self.shared_store, merge, message="upstream watcher challenge observation")
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.path)

    def is_packet_emitted(self, packet_id: str) -> bool:
        return packet_id in self.emitted_packet_digests

    def record_packet(self, packet: ObservationPacket) -> None:
        self.emitted_packet_digests.add(packet.packet_id)
        self.packets[packet.packet_id] = packet.to_dict()

    def get_challenge_entry(self, challenge_id: str) -> dict[str, Any]:
        if challenge_id not in self.challenges:
            self.challenges[challenge_id] = {
                "status": "unknown",
                "targeted_monitoring": "active",
                "last_checked_utc": None,
                "target": {},
                "comparator": {},
                "availability_probes": {
                    "status": "healthy",
                    "t0_utc": None,
                    "t24_utc": None,
                    "t72_utc": None,
                    "failed_probes": 0,
                },
            }
        return self.challenges[challenge_id]

    def is_rate_limited(self, host: str, now: datetime) -> bool:
        retry_until = self.rate_limits.get(host)
        if not retry_until:
            return False
        try:
            until_dt = datetime.fromisoformat(retry_until.replace("Z", "+00:00")).astimezone(timezone.utc)
            return now < until_dt
        except Exception:
            return False

    def set_rate_limit(self, host: str, retry_until_utc: str) -> None:
        self.rate_limits[host] = retry_until_utc


# ---------------------------------------------------------------------------
# Availability Prober Engine (t0 -> +24h -> +72h)
# ---------------------------------------------------------------------------


def _verify_packet_payload(payload: dict[str, Any], expected_id: str | None = None) -> None:
    if not isinstance(payload, dict):
        raise ValueError("stored packet payload must be an object")
    supplied = payload.get("packetSha256")
    body = {key: value for key, value in payload.items() if key != "packetSha256"}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if supplied != digest:
        raise ValueError("stored packet integrity digest mismatch")
    packet_id = payload.get("packetId")
    if expected_id is not None and packet_id != expected_id:
        raise ValueError("stored packet identity mismatch")


def _compute_digest(data: Any) -> str:
    # Packet identity is semantic/window scoped, not tied to poll time. This
    # keeps repeated daily observations from manufacturing duplicate intents.
    if isinstance(data, dict):
        data = {key: value for key, value in data.items()
                if key not in {"observedAtUTC", "observed_at_utc"}}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def process_availability_probe(
    challenge: ValidatedChallenge,
    probe_response: Response,
    probe_state: dict[str, Any],
    clock: Clock,
    ledger: WatchLedger,
) -> ObservationPacket | None:
    """Evaluate HTTP probe against t0 / +24h / +72h availability state.

    CRITICAL INVARIANT:
    Elapsed timeout NEVER demotes or mutates canonical trust. It opens an
    unavailability review observation for human adjudication.
    """
    now_utc = clock.now_utc()
    now_dt = clock.now_datetime()

    failed_probes = probe_state.get("failed_probes", 0)
    t0_utc = probe_state.get("t0_utc")
    t24_utc = probe_state.get("t24_utc")
    t72_utc = probe_state.get("t72_utc")

    # Success: Reachable!
    if probe_response.is_success:
        if failed_probes > 0:
            # Recovery observed!
            probe_state["status"] = "healthy"
            probe_state["failed_probes"] = 0
            probe_state["t0_utc"] = None
            probe_state["t24_utc"] = None
            probe_state["t72_utc"] = None

            packet_payload = {
                "challengeId": challenge.challenge_id,
                "subjectId": challenge.subject_id,
                "observedAtUTC": now_utc,
                "triggerType": "availability_recovered",
                "notes": "Target repository has returned to reachable status; availability alert cleared.",
            }
            packet_id = _compute_digest(packet_payload)
            if not ledger.is_packet_emitted(packet_id):
                return ObservationPacket(
                    packet_id=packet_id,
                    challenge_id=challenge.challenge_id,
                    subject_id=challenge.subject_id,
                    comparator_id=challenge.comparator.comparator_id,
                    observed_at_utc=now_utc,
                    trigger_side="target",
                    trigger_type="availability_recovered",
                    target_observation={"availability": "reachable", "statusCode": probe_response.status_code},
                    comparator_observation=None,
                    notes=packet_payload["notes"],
                )
        return None

    # Probe failure (404 / 410 / connection failure)
    if failed_probes == 0 or not t0_utc:
        # First failure: t0
        probe_state["t0_utc"] = now_utc
        probe_state["failed_probes"] = 1
        probe_state["status"] = "probe_t0"

        packet_payload = {
            "challengeId": challenge.challenge_id,
            "subjectId": challenge.subject_id,
            "observedAtUTC": now_utc,
            "triggerType": "availability_probe",
            "probeStep": "t0",
            "statusCode": probe_response.status_code,
            "notes": "Initial availability probe failure (t0). Scheduled for +24h confirmation probe.",
        }
        packet_id = _compute_digest(packet_payload)
        if not ledger.is_packet_emitted(packet_id):
            return ObservationPacket(
                packet_id=packet_id,
                challenge_id=challenge.challenge_id,
                subject_id=challenge.subject_id,
                comparator_id=challenge.comparator.comparator_id,
                observed_at_utc=now_utc,
                trigger_side="target",
                trigger_type="availability_probe",
                target_observation={"availability": "unavailable_suspect", "probeStep": "t0", "statusCode": probe_response.status_code},
                comparator_observation=None,
                notes=packet_payload["notes"],
            )
        return None

    # Already failed t0: check elapsed time for +24h
    t0_dt = datetime.fromisoformat(t0_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
    elapsed_seconds = (now_dt - t0_dt).total_seconds()

    if failed_probes == 1:
        if elapsed_seconds >= 24 * 3600.0:  # >= 24 hours
            probe_state["t24_utc"] = now_utc
            probe_state["failed_probes"] = 2
            probe_state["status"] = "probe_t24"

            packet_payload = {
                "challengeId": challenge.challenge_id,
                "subjectId": challenge.subject_id,
                "observedAtUTC": now_utc,
                "triggerType": "availability_probe",
                "probeStep": "t24",
                "statusCode": probe_response.status_code,
                "notes": "Sustained availability probe failure (+24h). Scheduled for +72h final probe.",
            }
            packet_id = _compute_digest(packet_payload)
            if not ledger.is_packet_emitted(packet_id):
                return ObservationPacket(
                    packet_id=packet_id,
                    challenge_id=challenge.challenge_id,
                    subject_id=challenge.subject_id,
                    comparator_id=challenge.comparator.comparator_id,
                    observed_at_utc=now_utc,
                    trigger_side="target",
                    trigger_type="availability_probe",
                    target_observation={"availability": "unavailable_suspect", "probeStep": "t24", "statusCode": probe_response.status_code},
                    comparator_observation=None,
                    notes=packet_payload["notes"],
                )
        return None

    if failed_probes == 2:
        if elapsed_seconds >= 72 * 3600.0:  # >= 72 hours
            probe_state["t72_utc"] = now_utc
            probe_state["failed_probes"] = 3
            probe_state["status"] = "unavailability_review_pending"

            packet_payload = {
                "challengeId": challenge.challenge_id,
                "subjectId": challenge.subject_id,
                "observedAtUTC": now_utc,
                "triggerType": "unavailability_review_pending",
                "probeStep": "t72",
                "statusCode": probe_response.status_code,
                "notes": (
                    "Availability failure sustained across t0, +24h, and +72h probes. "
                    "Unavailability review packet opened for human adjudication. "
                    "CRITICAL: Elapsed timeout never demotes or alters canonical trust scores."
                ),
            }
            packet_id = _compute_digest(packet_payload)
            if not ledger.is_packet_emitted(packet_id):
                return ObservationPacket(
                    packet_id=packet_id,
                    challenge_id=challenge.challenge_id,
                    subject_id=challenge.subject_id,
                    comparator_id=challenge.comparator.comparator_id,
                    observed_at_utc=now_utc,
                    trigger_side="target",
                    trigger_type="unavailability_review_pending",
                    target_observation={
                        "availability": "sustained_unavailable",
                        "probeStep": "t72",
                        "statusCode": probe_response.status_code,
                        "canonicalMutation": None,
                    },
                    comparator_observation=None,
                    canonical_mutation=None,
                    notes=packet_payload["notes"],
                )

    return None


# ---------------------------------------------------------------------------
# Two-Sided Watch Core Execution
# ---------------------------------------------------------------------------


def observe_challenge(
    challenge: ValidatedChallenge,
    transport: BaseTransport,
    clock: Clock,
    budget: WatchBudget,
    ledger: WatchLedger,
) -> list[ObservationPacket]:
    """Observe both target and comparator for one validated challenge."""
    packets: list[ObservationPacket] = []
    now_utc = clock.now_utc()
    entry = ledger.get_challenge_entry(challenge.challenge_id)

    # ── Check Resolution & Return-to-Routine ────────────────────────────────
    if challenge.is_resolved:
        if entry.get("targeted_monitoring") != "returned_to_routine":
            entry["targeted_monitoring"] = "returned_to_routine"
            entry["status"] = challenge.status
            entry["last_checked_utc"] = now_utc

            packet_payload = {
                "challengeId": challenge.challenge_id,
                "subjectId": challenge.subject_id,
                "observedAtUTC": now_utc,
                "triggerType": "returned_to_routine",
                "status": challenge.status,
                "notes": f"Challenge resolved as '{challenge.status}'. Targeted monitoring stopped; returned to routine cadence.",
            }
            packet_id = _compute_digest(packet_payload)
            if not ledger.is_packet_emitted(packet_id):
                packet = ObservationPacket(
                    packet_id=packet_id,
                    challenge_id=challenge.challenge_id,
                    subject_id=challenge.subject_id,
                    comparator_id=challenge.comparator.comparator_id,
                    observed_at_utc=now_utc,
                    trigger_side="lifecycle",
                    trigger_type="returned_to_routine",
                    target_observation={"status": challenge.status},
                    comparator_observation=None,
                    notes=packet_payload["notes"],
                )
                ledger.record_packet(packet)
                packets.append(packet)
        return packets

    # Mark monitoring active
    entry["targeted_monitoring"] = "active" if challenge.is_verified else "unverified_shadow"
    entry["status"] = challenge.status
    entry["last_checked_utc"] = now_utc

    # ── Check Rate Limits ───────────────────────────────────────────────────
    if ledger.is_rate_limited("api.github.com", clock.now_datetime()):
        return packets

    target_state = entry.setdefault("target", {})
    comparator_state = entry.setdefault("comparator", {})
    probe_state = entry.setdefault("availability_probes", {
        "status": "healthy", "t0_utc": None, "t24_utc": None, "t72_utc": None, "failed_probes": 0
    })

    # ── Side A: Probe Target ────────────────────────────────────────────────
    target_probe_url = f"https://github.com/{challenge.target.owner}/{challenge.target.repo}"
    if not budget.can_request():
        return packets

    budget.record_request()
    probe_resp = transport.probe(target_probe_url)

    # Check for rate limiting
    if probe_resp.is_rate_limited and probe_resp.retry_after_seconds:
        from datetime import timedelta
        until = clock.now_datetime() + timedelta(seconds=probe_resp.retry_after_seconds)
        ledger.set_rate_limit("api.github.com", until.strftime("%Y-%m-%dT%H:%M:%SZ"))
        # Emit rate limit observation
        rl_payload = {
            "challengeId": challenge.challenge_id,
            "host": "api.github.com",
            "retryAfterSeconds": probe_resp.retry_after_seconds,
            "observedAtUTC": now_utc,
        }
        rl_id = _compute_digest(rl_payload)
        if not ledger.is_packet_emitted(rl_id):
            p = ObservationPacket(
                packet_id=rl_id,
                challenge_id=challenge.challenge_id,
                subject_id=challenge.subject_id,
                comparator_id=challenge.comparator.comparator_id,
                observed_at_utc=now_utc,
                trigger_side="target",
                trigger_type="rate_limit",
                target_observation={"statusCode": probe_resp.status_code, "retryAfter": probe_resp.retry_after_seconds},
                comparator_observation=None,
                notes=f"Rate limit observed from upstream host. Retrying deferred for {probe_resp.retry_after_seconds}s.",
            )
            ledger.record_packet(p)
            packets.append(p)
        return packets

    probe_packet = process_availability_probe(challenge, probe_resp, probe_state, clock, ledger)
    if probe_packet:
        ledger.record_packet(probe_packet)
        packets.append(probe_packet)
        # If target is unavailable, do not continue to poll releases
        if not probe_resp.is_success:
            return packets

    # ── Side A: Observe Target Releases, Commit SHA, and Content ────────────
    target_changes: list[str] = []
    target_obs: dict[str, Any] = {"checks": {}}

    # Target Release
    if budget.can_request():
        budget.record_request()
        rel_resp = transport.get_release(challenge.target.owner, challenge.target.repo)
        target_obs["checks"]["release"] = "ok" if rel_resp.is_success and isinstance(rel_resp.data, dict) else "unknown"
        if rel_resp.is_success and isinstance(rel_resp.data, dict):
            new_tag = rel_resp.data.get("tag_name")
            last_tag = target_state.get("last_version") or challenge.target.pinned_version
            target_obs["release"] = {"latest": new_tag, "previous": last_tag, "url": rel_resp.data.get("html_url")}
            if new_tag and last_tag and new_tag != last_tag:
                target_changes.append("release")
            target_state["last_version"] = new_tag
    else:
        target_obs["checks"]["release"] = "not_run_budget"

    # Target Commit SHA
    if budget.can_request():
        budget.record_request()
        commit_resp = transport.get_commit(challenge.target.owner, challenge.target.repo, "HEAD")
        target_obs["checks"]["commit"] = "ok" if commit_resp.is_success and isinstance(commit_resp.data, dict) else "unknown"
        if commit_resp.is_success and isinstance(commit_resp.data, dict):
            new_sha = commit_resp.data.get("sha")
            last_sha = target_state.get("last_sha") or challenge.target.pinned_sha
            target_obs["commit"] = {"latestSha": new_sha, "previousSha": last_sha}
            if new_sha and last_sha and new_sha != last_sha:
                target_changes.append("commit_sha")
            target_state["last_sha"] = new_sha
    else:
        target_obs["checks"]["commit"] = "not_run_budget"

    # Target Content (SKILL.md)
    if budget.can_request():
        budget.record_request()
        path = challenge.target.watched_paths[0] if challenge.target.watched_paths else "SKILL.md"
        content_resp = transport.get_content(challenge.target.owner, challenge.target.repo, path)
        target_obs["checks"]["content"] = "ok" if content_resp.is_success and isinstance(content_resp.data, str) else "unknown"
        if content_resp.is_success and isinstance(content_resp.data, str):
            content_digest = hashlib.sha256(content_resp.data.encode("utf-8")).hexdigest()
            last_digest = target_state.get("last_content_digest") or challenge.target.pinned_content_digest
            target_obs["content"] = {"path": path, "digest": content_digest, "previousDigest": last_digest}
            if last_digest and content_digest != last_digest:
                target_changes.append("content_digest")
            target_state["last_content_digest"] = content_digest
    else:
        target_obs["checks"]["content"] = "not_run_budget"

    # ── Side B: Observe Traceable Comparator ─────────────────────────────────
    comparator_changes: list[str] = []
    comparator_obs: dict[str, Any] | None = None

    if challenge.comparator.is_traceable and challenge.comparator.owner and challenge.comparator.repo:
        comparator_obs = {"checks": {}}

        # Comparator Release
        if budget.can_request():
            budget.record_request()
            c_rel_resp = transport.get_release(challenge.comparator.owner, challenge.comparator.repo)
            if c_rel_resp.is_success and isinstance(c_rel_resp.data, dict):
                c_new_tag = c_rel_resp.data.get("tag_name")
                c_last_tag = comparator_state.get("last_version") or challenge.comparator.pinned_version
                comparator_obs["release"] = {"latest": c_new_tag, "previous": c_last_tag}
                if c_new_tag and c_last_tag and c_new_tag != c_last_tag:
                    comparator_changes.append("release")
                comparator_state["last_version"] = c_new_tag
                comparator_obs["checks"]["release"] = "ok"
            else:
                comparator_obs["checks"]["release"] = "unknown"
        else:
            comparator_obs["checks"]["release"] = "not_run_budget"

        # Comparator Commit SHA
        if budget.can_request():
            budget.record_request()
            c_commit_resp = transport.get_commit(challenge.comparator.owner, challenge.comparator.repo, "HEAD")
            if c_commit_resp.is_success and isinstance(c_commit_resp.data, dict):
                c_new_sha = c_commit_resp.data.get("sha")
                c_last_sha = comparator_state.get("last_sha") or challenge.comparator.pinned_sha
                comparator_obs["commit"] = {"latestSha": c_new_sha, "previousSha": c_last_sha}
                if c_new_sha and c_last_sha and c_new_sha != c_last_sha:
                    comparator_changes.append("commit_sha")
                comparator_state["last_sha"] = c_new_sha
                comparator_obs["checks"]["commit"] = "ok"
            else:
                comparator_obs["checks"]["commit"] = "unknown"
        else:
            comparator_obs["checks"]["commit"] = "not_run_budget"

        # Comparator Content
        if budget.can_request():
            budget.record_request()
            c_content_resp = transport.get_content(challenge.comparator.owner, challenge.comparator.repo, "SKILL.md")
            if c_content_resp.is_success and isinstance(c_content_resp.data, str):
                c_digest = hashlib.sha256(c_content_resp.data.encode("utf-8")).hexdigest()
                c_last_digest = comparator_state.get("last_content_digest")
                comparator_obs["content"] = {"path": "SKILL.md", "digest": c_digest, "previousDigest": c_last_digest}
                if c_last_digest and c_digest != c_last_digest:
                    comparator_changes.append("content_digest")
                comparator_state["last_content_digest"] = c_digest
                comparator_obs["checks"]["content"] = "ok"
            else:
                comparator_obs["checks"]["content"] = "unknown"
        else:
            comparator_obs["checks"]["content"] = "not_run_budget"
    else:
        comparator_obs = {"checks": {"release": "unknown", "commit": "unknown", "content": "unknown"},
                          "partial": True, "reason": "comparator repository is unavailable or untraceable"}

    # ── Synthesize Verification Packet if Changes Observed ───────────────────
    target_obs["partial"] = any(status != "ok" for status in target_obs["checks"].values())
    if comparator_obs:
        comparator_obs["partial"] = any(status != "ok" for status in comparator_obs["checks"].values())
    entry["last_observation"] = {
        "observedAtUTC": now_utc,
        "target": target_obs,
        "comparator": comparator_obs,
        "partial": bool(target_obs.get("partial") or (comparator_obs or {}).get("partial")),
    }
    if target_changes or comparator_changes:
        trigger_side = (
            "both" if (target_changes and comparator_changes)
            else "target" if target_changes
            else "comparator"
        )
        trigger_type = "+".join(sorted(set(target_changes + comparator_changes)))

        packet_payload = {
            "challengeId": challenge.challenge_id,
            "subjectId": challenge.subject_id,
            "observedAtUTC": now_utc,
            "triggerSide": trigger_side,
            "triggerType": trigger_type,
            "targetObservation": target_obs,
            "comparatorObservation": comparator_obs,
            "notes": (
                "Upstream event observed on active challenge. Verification packet opened "
                "for independent testing. Descriptions alone cannot prove recovery. "
                "No canonical trust mutation."
            ),
        }
        packet_id = _compute_digest(packet_payload)

        if not ledger.is_packet_emitted(packet_id):
            packet = ObservationPacket(
                packet_id=packet_id,
                challenge_id=challenge.challenge_id,
                subject_id=challenge.subject_id,
                comparator_id=challenge.comparator.comparator_id,
                observed_at_utc=now_utc,
                trigger_side=trigger_side,
                trigger_type=trigger_type,
                target_observation=target_obs,
                comparator_observation=comparator_obs,
                notes=packet_payload["notes"],
            )
            ledger.record_packet(packet)
            packets.append(packet)

    return packets


# ---------------------------------------------------------------------------
# Runner Seam
# ---------------------------------------------------------------------------


def run_challenge_watch(
    challenges: list[dict[str, Any]] | Path | str | None = None,
    *,
    registry_map: dict[str, dict] | None = None,
    transport: BaseTransport | None = None,
    clock: Clock | None = None,
    budget: WatchBudget | None = None,
    ledger_path: Path | str | None = None,
    packets_dir: Path | str | None = None,
    shared_store: Any = None,
    receipts_root: Path | str | None = None,
    allow_shadow: bool = False,
    admission_resolver: ChallengeAdmissionResolver | None = None,
    verbose: bool = False,
) -> ChallengeWatchResult:
    """Execute the bounded two-sided challenge watch.

    Parameters
    ----------
    challenges:
        List of challenge dicts, path to JSON file, or None (defaults to looking
        for .gaia/challenges/active.json or .gaia/upstream-watcher/challenges.json).
    registry_map:
        Optional skill-id -> frontmatter mapping.
    transport:
        Transport to use (defaults to live HttpTransport).
    clock:
        Clock to use (defaults to live SystemClock).
    budget:
        Run budget (defaults to 20 requests, 10 subjects).
    ledger_path:
        Path to state ledger file (defaults to .gaia/upstream-watcher/challenge-watch-ledger.json).
    packets_dir:
        Directory to write emitted verification packets (defaults to .gaia/upstream-watcher/packets).
    receipts_root:
        Path to directory with Steward verification receipts.
    allow_shadow:
        If True, unverified challenges run as shadow-only observations without public authority.
    admission_resolver:
        Explicit trusted adapter. Raw manifests and local receipt files are never
        authentication. None means fail-closed Class C/unavailable.
    verbose:
        If True, log progress to stderr.

    Returns
    -------
    ChallengeWatchResult
    """
    transport = transport or HttpTransport()
    clock = clock or SystemClock()
    budget = budget or WatchBudget()
    l_path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    p_dir = Path(packets_dir) if packets_dir else DEFAULT_PACKETS_DIR
    r_root = Path(receipts_root) if receipts_root else Path(".gaia/steward/receipts")

    ledger = WatchLedger(l_path, shared_store=shared_store)
    result = ChallengeWatchResult()

    # Load challenges
    raw_list: list[dict[str, Any]] = []
    if challenges is None:
        default_candidates = [
            Path(".gaia/challenges/active.json"),
            Path(".gaia/upstream-watcher/challenges.json"),
        ]
        for cand in default_candidates:
            if cand.is_file():
                try:
                    data = json.loads(cand.read_text(encoding="utf-8"))
                    raw_list = data if isinstance(data, list) else data.get("challenges", [])
                    break
                except Exception:
                    continue
    elif isinstance(challenges, (str, Path)):
        c_path = Path(challenges)
        if c_path.is_file():
            data = json.loads(c_path.read_text(encoding="utf-8"))
            raw_list = data if isinstance(data, list) else data.get("challenges", [])
    elif isinstance(challenges, list):
        raw_list = challenges

    # Merge by immutable challenge identity; filtered manifests cannot silently
    # drop an already-admitted watch, and context changes are explicit conflicts.
    if not raw_list and ledger.inputs:
        raw_list = ledger.inputs
    incoming = [item for item in raw_list if isinstance(item, dict)]
    by_identity = {
        str(item.get("challenge_id") or item.get("challengeId") or ""): item
        for item in ledger.inputs
    }
    for item in incoming:
        identity = str(item.get("challenge_id") or item.get("challengeId") or "")
        if not identity:
            identity = _compute_digest({k: v for k, v in item.items() if k not in {"observedAtUTC", "observed_at_utc"}})
        prior = by_identity.get(identity)
        if prior is not None and prior != item:
            raise ValueError(f"conflicting challenge context for immutable identity {identity}")
        by_identity[identity] = item
    ledger.inputs = list(by_identity.values())
    raw_list = ledger.inputs
    if verbose:
        print(f"[challenge-watch] Loaded {len(raw_list)} challenge input(s).", file=sys.stderr)

    # Validate each challenge through the trusted resolver; manifests are hints only.
    validated_challenges: list[ValidatedChallenge] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        if admission_resolver is None:
            validated, status_msg = None, (
                "UNAVAILABLE: trusted VerificationReceiptResolver is not configured; "
                "Class C required, no verified publication or lifecycle authority"
            )
            result.unavailable_count += 1
            result.summaries.append({
                "subjectId": item.get("subject_id") or item.get("subjectId"),
                "status": "class-c-required",
                "verification": "unavailable",
                "publication": "not-verified",
                "reason": status_msg,
            })
        else:
            validated, status_msg = admission_resolver.resolve(
                item, registry_map=registry_map, allow_shadow=allow_shadow,
            )
        if validated is None:
            result.rejected_unverified_count += 1
            if verbose:
                print(f"  [reject] {item.get('subject_id') or item.get('claim_id')}: {status_msg}", file=sys.stderr)
            continue
        validated_challenges.append(validated)

    # Observe validated challenges within budget
    for challenge in validated_challenges:
        if budget.is_exhausted or not budget.can_evaluate_subject():
            result.budget_exhausted = True
            if verbose:
                print("  [budget] Budget limit reached; stopping challenge watch run.", file=sys.stderr)
            break

        budget.record_subject()
        if challenge.is_resolved:
            result.resolved_count += 1
        else:
            result.active_count += 1

        packets = observe_challenge(challenge, transport, clock, budget, ledger)
        result.packets.extend(packets)

        result.summaries.append({
            "challengeId": challenge.challenge_id,
            "subjectId": challenge.subject_id,
            "isVerified": challenge.is_verified,
            "isShadow": challenge.is_shadow,
            "status": challenge.status,
            "packetsEmitted": len(packets),
        })

    # Update ledger metadata & persist
    ledger.last_run_utc = clock.now_utc()
    ledger.save()  # Persist packet payloads/intents before local materialization.
    for packet in result.packets:
        packet_data = packet.to_dict()
        packet_path = p_dir / f"{packet.packet_id}.json"
        p_dir.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(packet_data, indent=2, sort_keys=True) + "\n"
        if packet_path.exists():
            existing = json.loads(packet_path.read_text(encoding="utf-8"))
            _verify_packet_payload(existing, packet.packet_id)
            if existing != packet_data:
                raise ValueError(f"immutable packet collision for {packet.packet_id}")
        else:
            try:
                with packet_path.open("x", encoding="utf-8") as handle:
                    handle.write(encoded)
            except FileExistsError:
                existing = json.loads(packet_path.read_text(encoding="utf-8"))
                _verify_packet_payload(existing, packet.packet_id)
                if existing != packet_data:
                    raise ValueError(f"immutable packet collision for {packet.packet_id}")

    result.budget_used = {
        "requests": budget.requests_used,
        "maxRequests": budget.max_requests,
        "subjects": budget.subjects_evaluated,
        "maxSubjects": budget.max_subjects,
    }

    if verbose:
        print(
            f"[challenge-watch] Completed: {len(result.packets)} packet(s) emitted, "
            f"{result.active_count} active, {result.resolved_count} resolved, "
            f"{result.rejected_unverified_count} unverified rejected.",
            file=sys.stderr,
        )

    return result
