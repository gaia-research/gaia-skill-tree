"""
Unit tests for scripts/upstream_watcher/challenge_watch.py.

Verifies the Bounded Two-Sided Challenge Watch Engine under Yggdrasil IV doctrine:
1. Actual runner execution (end-to-end observation of releases, SHAs, and content).
2. Durable semantic dedup across retries and process restarts.
3. Bounded run budget (requests and subjects limits).
4. Both sides observed (target and traceable comparator).
5. Partial transport resilience (500 errors, network failures, 429 Retry-After).
6. Availability probe progression (t0 -> +24h -> +72h).
7. Elapsed timeout NEVER demotes or mutates canonical trust.
8. Availability recovery clears alert.
9. Return-to-routine on technical resolution.
10. Verification receipt gate rejects raw unverified manifests.
11. Verifier independence invariant (verifier != contributor).
12. Case-normalization in repository resolution (Leonxlnx/taste-skill vs leonxlnx/taste-skill).
13. CLI seam integration in scripts/upstream_watcher/watcher.py.

All tests run strictly offline with SimulatedTransport and VirtualClock; zero network I/O.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import pytest

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.upstream_watcher.challenge_watch import (
    ChallengeComparator,
    ChallengeTarget,
    ChallengeWatchResult,
    ObservationPacket,
    StewardReceiptChallengeAdapter,
    ValidatedChallenge,
    VerificationReceipt,
    WatchBudget,
    WatchLedger,
    observe_challenge,
    run_challenge_watch as _run_challenge_watch,
)
from scripts.upstream_watcher.transport import (
    Response,
    SimulatedTransport,
    VirtualClock,
)
from scripts.upstream_watcher.watcher import main as watcher_main


# ---------------------------------------------------------------------------
# Fixture Helpers
# ---------------------------------------------------------------------------


class _ExplicitTestResolver:
    """Fixture-only adapter; never wired by the scheduled production CLI."""

    def resolve(self, raw, *, registry_map, allow_shadow):
        return StewardReceiptChallengeAdapter.validate(
            raw, registry_map=registry_map, allow_shadow=allow_shadow,
        )


def run_challenge_watch(*args, **kwargs):
    kwargs.setdefault("admission_resolver", _ExplicitTestResolver())
    return _run_challenge_watch(*args, **kwargs)


def _make_verified_challenge_dict(
    subject_id: str = "pbakaus/impeccable",
    target_repo: str = "pbakaus/impeccable",
    comparator_id: str = "competitor/rival",
    claim_id: str = "claim-anti-slop-perf-1",
    pinned_version: str = "v1.0.0",
    pinned_sha: str = "sha-pinned-100",
    pinned_content_digest: str | None = None,
    status: str = "verified-pending",
    contributor_id: str = "pbakaus",
    verifier_id: str = "independent-auditor-1",
) -> dict:
    return {
        "challenge_id": f"ch-{subject_id.replace('/', '-')}-{claim_id}",
        "claim_id": claim_id,
        "subject_id": subject_id,
        "contributor_id": contributor_id,
        "behavior_id": "design-token-benchmark",
        "status": status,
        "material_to_origin": True,
        "target_repo": target_repo,
        "pinned_version": pinned_version,
        "pinned_sha": pinned_sha,
        "pinned_content_digest": pinned_content_digest,
        "comparator": comparator_id,
        "created_at_utc": "2026-10-25T00:00:00Z",
        "verification_receipt": {
            "receipt_id": "rcpt-val-001",
            "verifier_id": verifier_id,
            "verified_at_utc": "2026-10-25T01:00:00Z",
            "receipt_ref": "https://github.com/gaia-research/gaia-skill-tree/pull/999#receipt",
            "challenge_binding_digest": "binding-digest-001",
            "notes": "Verified by independent benchmark comparison",
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_runner_execution_end_to_end(tmp_path: Path) -> None:
    """1. Prove actual runner execution and verification packet emission."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()

    # Target: new release v1.1.0, new SHA sha-new, changed SKILL.md
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    transport.register_release("pbakaus", "impeccable", tag="v1.1.0")
    transport.register_commit("pbakaus", "impeccable", sha="sha-new-200")
    transport.register_content("pbakaus", "impeccable", "SKILL.md", content="# Impeccable v1.1.0\nUpdated content.")

    raw_challenge = _make_verified_challenge_dict(
        pinned_content_digest="sha-pinned-digest-000",
    )
    ledger_file = tmp_path / "ledger.json"
    packets_dir = tmp_path / "packets"

    result = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )

    assert result.active_count == 1
    assert result.resolved_count == 0
    assert result.rejected_unverified_count == 0
    assert len(result.packets) == 1

    packet = result.packets[0]
    assert packet.subject_id == "pbakaus/impeccable"
    assert packet.trigger_side == "target"
    assert "release" in packet.trigger_type
    assert "commit_sha" in packet.trigger_type
    assert "content_digest" in packet.trigger_type
    assert packet.requires_independent_verification is True
    assert packet.canonical_mutation is None
    assert "OBSERVATION ONLY" in packet.authority_notice

    # Verify packet saved to disk
    saved_packets = list(packets_dir.glob("*.json"))
    assert len(saved_packets) == 1
    disk_data = json.loads(saved_packets[0].read_text(encoding="utf-8"))
    assert disk_data["packetId"] == packet.packet_id
    packet_digest = disk_data.pop("packetSha256")
    assert packet_digest == hashlib.sha256(
        json.dumps(disk_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert disk_data["canonicalMutation"] is None

    # Verify ledger saved
    assert ledger_file.is_file()
    ledger_data = json.loads(ledger_file.read_text(encoding="utf-8"))
    assert packet.packet_id in ledger_data["emitted_packet_digests"]
    assert ledger_data["packets"][packet.packet_id]["packetSha256"] == packet_digest


def test_dedup_across_retry_and_restart(tmp_path: Path) -> None:
    """2. Prove durable semantic dedup across retry and process restart."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()

    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    transport.register_release("pbakaus", "impeccable", tag="v1.1.0")
    transport.register_commit("pbakaus", "impeccable", sha="sha-new-200")
    transport.register_content("pbakaus", "impeccable", "SKILL.md", content="# v1.1.0")

    raw_challenge = _make_verified_challenge_dict()
    ledger_file = tmp_path / "ledger.json"
    packets_dir = tmp_path / "packets"

    # First run: emits 1 packet
    res1 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res1.packets) == 1

    # Second immediate run with same transport: emits 0 packets (dedup in memory)
    res2 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res2.packets) == 0

    # Third run: fresh clock, fresh transport instance, restart process by re-reading ledger
    clock.advance_hours(1)
    transport2 = SimulatedTransport()
    transport2.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    transport2.register_release("pbakaus", "impeccable", tag="v1.1.0")
    transport2.register_commit("pbakaus", "impeccable", sha="sha-new-200")
    transport2.register_content("pbakaus", "impeccable", "SKILL.md", content="# v1.1.0")

    res3 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport2,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res3.packets) == 0  # Deduplicated from persisted ledger!


def test_bounded_run_budget_enforcement(tmp_path: Path) -> None:
    """3. Prove bounded run budget enforcement for requests and subjects."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()

    # Setup 3 challenges
    challenges = [
        _make_verified_challenge_dict(subject_id="skill-a/one", target_repo="skill-a/one", claim_id="c1"),
        _make_verified_challenge_dict(subject_id="skill-b/two", target_repo="skill-b/two", claim_id="c2"),
        _make_verified_challenge_dict(subject_id="skill-c/three", target_repo="skill-c/three", claim_id="c3"),
    ]
    for ch in challenges:
        transport.register_probe(f"https://github.com/{ch['target_repo']}", status_code=200)

    # Subject budget = 2
    budget = WatchBudget(max_requests=100, max_subjects=2)
    res = run_challenge_watch(
        challenges=challenges,
        transport=transport,
        clock=clock,
        budget=budget,
        ledger_path=tmp_path / "ledger_budget.json",
        packets_dir=tmp_path / "packets_budget",
    )
    assert res.budget_used["subjects"] == 2
    assert res.budget_exhausted is True
    assert len(res.summaries) == 2

    # Request budget = 3
    transport.recorded_requests.clear()
    budget2 = WatchBudget(max_requests=3, max_subjects=10)
    res2 = run_challenge_watch(
        challenges=challenges,
        transport=transport,
        clock=clock,
        budget=budget2,
        ledger_path=tmp_path / "ledger_budget2.json",
        packets_dir=tmp_path / "packets_budget2",
    )
    assert res2.budget_used["requests"] <= 3
    assert len(transport.recorded_requests) <= 3


def test_both_sides_observed_target_and_comparator(tmp_path: Path) -> None:
    """4. Prove two-sided observation captures both target and comparator."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()

    # Target changes release v1.0.0 -> v1.2.0
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    transport.register_release("pbakaus", "impeccable", tag="v1.2.0")
    transport.register_commit("pbakaus", "impeccable", sha="sha-pinned-100")
    transport.register_content("pbakaus", "impeccable", "SKILL.md", content="same-content")

    # Traceable Comparator also changes release v2.0.0 -> v2.1.0
    transport.register_release("competitor", "rival", tag="v2.1.0")
    transport.register_commit("competitor", "rival", sha="sha-c-999")
    transport.register_content("competitor", "rival", "SKILL.md", content="rival-content")

    raw_challenge = _make_verified_challenge_dict(
        comparator_id="competitor/rival@v2.0.0",
    )

    result = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=tmp_path / "ledger_twosided.json",
        packets_dir=tmp_path / "packets_twosided",
    )

    assert len(result.packets) == 1
    packet = result.packets[0]
    assert packet.trigger_side == "both"
    assert packet.target_observation["release"]["latest"] == "v1.2.0"
    assert packet.comparator_observation is not None
    assert packet.comparator_observation["release"]["latest"] == "v2.1.0"


def test_partial_transport_error_resilience(tmp_path: Path) -> None:
    """5. Prove partial transport failures (500, network error) do not crash runner."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()

    # Challenge 1 has failing probe (500)
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=500)

    # Challenge 2 has healthy probe and release update
    transport.register_probe("https://github.com/leonxlnx/taste-skill", status_code=200)
    transport.register_release("leonxlnx", "taste-skill", tag="v2.0.0")

    challenges = [
        _make_verified_challenge_dict(subject_id="pbakaus/impeccable", target_repo="pbakaus/impeccable", claim_id="c1"),
        _make_verified_challenge_dict(subject_id="leonxlnx/taste-skill", target_repo="leonxlnx/taste-skill", claim_id="c2"),
    ]

    result = run_challenge_watch(
        challenges=challenges,
        transport=transport,
        clock=clock,
        ledger_path=tmp_path / "ledger_resilience.json",
        packets_dir=tmp_path / "packets_resilience",
    )

    assert result.active_count == 2
    # Second challenge emitted packet despite first having transport error
    taste_packets = [p for p in result.packets if p.subject_id == "leonxlnx/taste-skill"]
    assert len(taste_packets) == 1
    assert taste_packets[0].target_observation["release"]["latest"] == "v2.0.0"


def test_rate_limit_and_retry_after_handling(tmp_path: Path) -> None:
    """6. Prove HTTP 429 Retry-After is recorded as an observation without crashing."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()

    # Probe returns 429 with Retry-After: 60
    transport.register_probe(
        "https://github.com/pbakaus/impeccable",
        status_code=429,
        headers={"retry-after": "60"},
    )

    raw_challenge = _make_verified_challenge_dict()
    ledger_file = tmp_path / "ledger_rl.json"

    result = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=tmp_path / "packets_rl",
    )

    assert len(result.packets) == 1
    packet = result.packets[0]
    assert packet.trigger_type == "rate_limit"
    assert packet.target_observation["retryAfter"] == 60

    # Ledger recorded host rate limit
    ledger = WatchLedger(ledger_file)
    assert ledger.is_rate_limited("api.github.com", clock.now_datetime())


def test_availability_probes_t0_t24_t72_progression(tmp_path: Path) -> None:
    """7. Prove progressive availability probes t0 -> +24h -> +72h."""
    clock = VirtualClock("2026-10-26T00:00:00Z")
    transport = SimulatedTransport()
    # Probe returns 404 (unavailable)
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=404)

    raw_challenge = _make_verified_challenge_dict()
    ledger_file = tmp_path / "ledger_probes.json"
    packets_dir = tmp_path / "packets_probes"

    # Step 1: Run at t0
    res1 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res1.packets) == 1
    assert res1.packets[0].target_observation["probeStep"] == "t0"

    # Step 2: Run at t0 + 12h (< 24h) -> no new packet
    clock.advance_hours(12)
    res2 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res2.packets) == 0

    # Step 3: Run at t0 + 25h (>= 24h) -> probe +24h
    clock.advance_hours(13)
    res3 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res3.packets) == 1
    assert res3.packets[0].target_observation["probeStep"] == "t24"

    # Step 4: Run at t0 + 50h (< 72h) -> no new packet
    clock.advance_hours(25)
    res4 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res4.packets) == 0

    # Step 5: Run at t0 + 73h (>= 72h) -> probe +72h review packet
    clock.advance_hours(23)
    res5 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=packets_dir,
    )
    assert len(res5.packets) == 1
    p72 = res5.packets[0]
    assert p72.trigger_type == "unavailability_review_pending"
    assert p72.target_observation["probeStep"] == "t72"
    assert p72.canonical_mutation is None
    assert "Elapsed timeout never demotes" in p72.notes


def test_elapsed_timeout_never_demotes(tmp_path: Path) -> None:
    """8. Invariant: Elapsed timeout opens review observation, NEVER mutates trust."""
    clock = VirtualClock("2026-10-26T00:00:00Z")
    transport = SimulatedTransport()
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=404)

    raw_challenge = _make_verified_challenge_dict()
    ledger_file = tmp_path / "ledger_never_demotes.json"

    # Advance clock directly past 72h after t0
    packets_dir = tmp_path / "packets"
    run_challenge_watch(challenges=[raw_challenge], transport=transport, clock=clock, ledger_path=ledger_file, packets_dir=packets_dir)
    clock.advance_hours(25)
    run_challenge_watch(challenges=[raw_challenge], transport=transport, clock=clock, ledger_path=ledger_file, packets_dir=packets_dir)
    clock.advance_hours(50)
    res = run_challenge_watch(challenges=[raw_challenge], transport=transport, clock=clock, ledger_path=ledger_file, packets_dir=packets_dir)

    review_packets = [p for p in res.packets if p.trigger_type == "unavailability_review_pending"]
    assert len(review_packets) == 1
    pkt = review_packets[0]
    assert pkt.canonical_mutation is None
    assert "never demotes" in pkt.notes


def test_availability_recovery_clears_alert(tmp_path: Path) -> None:
    """9. Prove that restoration to 200 OK emits recovery packet and clears failure state."""
    clock = VirtualClock("2026-10-26T00:00:00Z")
    transport = SimulatedTransport()
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=404)

    raw_challenge = _make_verified_challenge_dict()
    ledger_file = tmp_path / "ledger_rec.json"

    # Fail t0
    packets_dir = tmp_path / "packets"
    run_challenge_watch(challenges=[raw_challenge], transport=transport, clock=clock, ledger_path=ledger_file, packets_dir=packets_dir)

    # Recover to 200 OK
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    clock.advance_hours(2)

    res = run_challenge_watch(challenges=[raw_challenge], transport=transport, clock=clock, ledger_path=ledger_file, packets_dir=packets_dir)
    assert len(res.packets) == 1
    assert res.packets[0].trigger_type == "availability_recovered"

    ledger = WatchLedger(ledger_file)
    entry = ledger.get_challenge_entry(raw_challenge["challenge_id"])
    assert entry["availability_probes"]["status"] == "healthy"
    assert entry["availability_probes"]["failed_probes"] == 0


def test_return_to_routine_on_technical_resolution(tmp_path: Path) -> None:
    """10. Prove targeted monitoring stops when challenge status is technically resolved."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=200)

    # Resolved challenge
    raw_challenge = _make_verified_challenge_dict(status="resolved-by-upstream-improvement")
    ledger_file = tmp_path / "ledger_routine.json"

    res = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
        packets_dir=tmp_path / "packets",
    )

    assert res.resolved_count == 1
    assert res.active_count == 0
    assert len(res.packets) == 1
    assert res.packets[0].trigger_type == "returned_to_routine"

    ledger = WatchLedger(ledger_file)
    entry = ledger.get_challenge_entry(raw_challenge["challenge_id"])
    assert entry["targeted_monitoring"] == "returned_to_routine"

    # Second run does not re-emit and performs 0 requests
    transport.recorded_requests.clear()
    res2 = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=ledger_file,
    )
    assert len(res2.packets) == 0
    assert len(transport.recorded_requests) == 0


def test_partial_observation_is_unknown_retryable_and_comparator_is_explicit(tmp_path: Path) -> None:
    challenge = _make_verified_challenge_dict(comparator_id="")
    transport = SimulatedTransport()
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    transport.register_release("pbakaus", "impeccable", tag="v1.0.0", status_code=500)
    transport.register_commit("pbakaus", "impeccable", sha="sha-pinned-100")
    transport.register_content("pbakaus", "impeccable", "SKILL.md", "baseline")
    ledger_path = tmp_path / "ledger.json"

    run_challenge_watch(
        challenges=[challenge], transport=transport, clock=VirtualClock(),
        ledger_path=ledger_path, packets_dir=tmp_path / "packets",
    )
    state = json.loads(ledger_path.read_text(encoding="utf-8"))
    observation = state["challenges"][challenge["challenge_id"]]["last_observation"]
    assert observation["target"]["checks"]["release"] == "unknown"
    assert observation["target"]["partial"] is True
    assert observation["comparator"]["partial"] is True
    assert all(value == "unknown" for value in observation["comparator"]["checks"].values())

    transport.register_release("pbakaus", "impeccable", tag="v1.0.0")
    run_challenge_watch(
        challenges=[challenge], transport=transport, clock=VirtualClock("2026-10-27T00:00:00Z"),
        ledger_path=ledger_path, packets_dir=tmp_path / "packets",
    )
    state = json.loads(ledger_path.read_text(encoding="utf-8"))
    observation = state["challenges"][challenge["challenge_id"]]["last_observation"]
    assert observation["target"]["checks"]["release"] == "ok"
    assert observation["target"]["partial"] is False


def test_runner_without_trusted_resolver_fails_closed_on_malicious_resolved_status(tmp_path: Path) -> None:
    raw = _make_verified_challenge_dict(status="resolved-by-upstream-improvement")
    transport = SimulatedTransport()
    result = _run_challenge_watch(
        challenges=[raw], transport=transport, clock=VirtualClock("2026-10-26T10:00:00Z"),
        ledger_path=tmp_path / "ledger.json", packets_dir=tmp_path / "packets",
    )
    assert result.unavailable_count == 1
    assert result.resolved_count == 0
    assert result.active_count == 0
    assert result.packets == []
    assert transport.recorded_requests == []


def test_verification_receipt_gate_rejects_unverified_manifest() -> None:
    """11. Prove raw challenge status string alone is rejected without durable receipt."""
    # Raw challenge with "status": "verified-pending" but NO verification_receipt
    unverified_raw = {
        "claim_id": "c1",
        "subject_id": "pbakaus/impeccable",
        "contributor_id": "pbakaus",
        "status": "verified-pending",
        "target_repo": "pbakaus/impeccable",
    }

    # Strict public watch mode: REJECTS
    val, reason = StewardReceiptChallengeAdapter.validate(unverified_raw, allow_shadow=False)
    assert val is None
    assert "REJECTED: Missing durable independent verification receipt" in reason

    # Shadow opt-in mode: Admits strictly as shadow observation
    val_shadow, reason_shadow = StewardReceiptChallengeAdapter.validate(unverified_raw, allow_shadow=True)
    assert val_shadow is not None
    assert val_shadow.is_verified is False
    assert val_shadow.is_shadow is True
    assert "ADMITTED_AS_SHADOW" in reason_shadow


def test_independent_verifier_cannot_be_contributor() -> None:
    """12. Invariant: Independent verifier must differ from challenged contributor."""
    conflict_raw = _make_verified_challenge_dict(
        contributor_id="pbakaus",
        verifier_id="pbakaus",  # Not independent!
    )
    val, reason = StewardReceiptChallengeAdapter.validate(conflict_raw, allow_shadow=False)
    assert val is None
    assert "Verifier must be independent from contributor" in reason


def test_case_normalization_repo_matching(tmp_path: Path) -> None:
    """13. Historical defect fix: Case mismatch in repository names must be normalized."""
    clock = VirtualClock("2026-10-26T10:00:00Z")
    transport = SimulatedTransport()

    # Upstream returns with capital Leonxlnx, registry has leonxlnx
    transport.register_probe("https://github.com/leonxlnx/taste-skill", status_code=200)
    transport.register_release("Leonxlnx", "taste-skill", tag="v1.5.0")
    transport.register_commit("Leonxlnx", "taste-skill", sha="sha-taste-150")

    raw_challenge = _make_verified_challenge_dict(
        subject_id="leonxlnx/taste-skill",
        target_repo="Leonxlnx/taste-skill",
        pinned_version="v1.0.0",
        pinned_sha="sha-taste-100",
    )

    res = run_challenge_watch(
        challenges=[raw_challenge],
        transport=transport,
        clock=clock,
        ledger_path=tmp_path / "ledger_case.json",
        packets_dir=tmp_path / "packets",
    )
    assert len(res.packets) == 1
    assert res.packets[0].target_observation["release"]["latest"] == "v1.5.0"


def test_watcher_cli_invocation_with_challenge_watch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """14. Seam integration: Prove scripts/upstream_watcher/watcher.py CLI flag triggers watch."""
    raw_challenge = _make_verified_challenge_dict()
    challenge_file = tmp_path / "challenges.json"
    challenge_file.write_text(json.dumps([raw_challenge]), encoding="utf-8")
    ledger_file = tmp_path / "cli_ledger.json"
    packets_dir = tmp_path / "cli_packets"

    # Mock _build_registry_map and iter_suite_skills to keep test fast and isolated
    monkeypatch.setattr("scripts.upstream_watcher.watcher._build_registry_map", lambda: {})
    monkeypatch.setattr("scripts.upstream_watcher.watcher.iter_suite_skills", lambda: iter([]))

    # Mock transport inside challenge_watch to use simulated responses
    sim = SimulatedTransport()
    sim.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    sim.register_release("pbakaus", "impeccable", tag="v1.1.0")
    monkeypatch.setattr("scripts.upstream_watcher.challenge_watch.HttpTransport", lambda: sim)

    # Run watcher main with --challenge-watch
    exit_code = watcher_main([
        "--dry-run",
        "--challenge-watch",
        "--challenge-input", str(challenge_file),
        "--challenge-ledger", str(ledger_file),
        "--challenge-output", str(packets_dir),
    ])
    assert exit_code == 0
    assert ledger_file.is_file()
