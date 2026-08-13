"""Steward V1.4 — the bounded Class B rolling maintenance lane."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import shutil

import pytest
import yaml

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.lane import (
    Lane,
    LaneEntry,
    LaneError,
    LanePolicy,
    LaneTransition,
    load_lane,
    mark_dispatched,
    next_dispatchable,
    reconcile,
    record_verdict,
)
from gaia_cli.steward.models import AuthorityClass, Observation, Priority, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy
from gaia_cli.steward.routing import (
    LaneEmpty,
    RoutingError,
    record_lane_verdict,
    render_lane,
    render_lane_next,
    render_verification,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 8, 13, tzinfo=timezone.utc)
NOW = "2026-08-13T00:00:00Z"
POLICY = LanePolicy(max_in_flight=1, max_attempts=2, cooldown_seconds=3600)


def _repo(tmp_path: Path, mutate=None) -> Path:
    destination = tmp_path / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    if mutate is None:
        shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, destination)
    else:
        data = yaml.safe_load((REPO_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
        mutate(data)
        destination.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return tmp_path


class LaneSensor:
    """Emits `count` distinct Class B registry-integrity findings."""

    id = "registry-integrity"

    def __init__(self, count: int = 1) -> None:
        self.count = count

    def scan(self, root: Path, observed_at: str) -> list[Observation]:
        return [
            Observation(
                kind="registry_integrity_failed",
                subject=Subject("repository-surface", f"nodes-{number}"),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"valid": True},
                observed_state={"violations": [{"path": f"registry/nodes/{number}.json"}]},
            )
            for number in range(self.count)
        ]


def _controller(sensor: LaneSensor, *, at: datetime = FROZEN) -> StewardController:
    return StewardController(sensors=[sensor], clock=lambda: at)


def _entry(debt_id: str, **overrides) -> LaneEntry:
    defaults = dict(
        debt_id=debt_id,
        rule="registry-integrity-review",
        state="queued",
        attempts=0,
        priority=1.0,
        first_queued_at=NOW,
        last_transition_at=NOW,
        last_verdict=None,
        history=(LaneTransition(at=NOW, from_state="none", to_state="queued", reason="observed"),),
    )
    defaults.update(overrides)
    return LaneEntry(**defaults)  # type: ignore[arg-type]


def _lane(*entries: LaneEntry, policy: LanePolicy = POLICY) -> Lane:
    return Lane(entries=tuple(entries), policy=policy)


def _debt(debt_id: str, score: float = 1.0):
    from gaia_cli.steward.models import Debt

    return Debt(
        id=debt_id,
        kind="registry_integrity_failed",
        subject=Subject("repository-surface", debt_id),
        source="registry-integrity",
        current_state={},
        observed_state={},
        confidence=1.0,
        priority=Priority(
            importance=1.0, decision_impact=1.0, exposure=1.0,
            freshness_need=1.0, expected_cost=0.4, score=score,
        ),
        authority=AuthorityClass.B,
        status="open",
        first_observed_at=NOW,
        last_observed_at=NOW,
        observation_count=1,
    )


# --- bounds ------------------------------------------------------------------


def test_the_lane_bounds_are_capped_in_code_not_only_in_policy(tmp_path: Path) -> None:
    """Policy may narrow the lane's limits. It may never widen them.

    These three numbers are the only thing standing between bounded autonomous
    repair and an unattended loop, so they get the same treatment as a Class A
    envelope: pinned in code, narrowable by policy, never widenable by it.
    """

    for key, value in (("maxInFlight", 5), ("maxAttempts", 6), ("cooldownSeconds", 86_401)):
        root = _repo(tmp_path / key, lambda data, k=key, v=value: data["routing"]["lane"].update({k: v}))
        with pytest.raises(PolicyError, match=f"routing.lane.{key}"):
            StewardPolicy.load(root)


def test_the_shipped_policy_declares_a_conservative_lane() -> None:
    lane = StewardPolicy.load(REPO_ROOT).lane
    assert lane.max_in_flight == 1
    assert lane.max_attempts == 2
    assert lane.cooldown_seconds == 3600


def test_stored_lane_state_never_carries_its_own_bounds() -> None:
    """A lane that remembered its limits could outrun a lowered ceiling."""

    stored = _lane(_entry("debt:a"), policy=LanePolicy(max_in_flight=4, max_attempts=5, cooldown_seconds=0))
    narrowed = LanePolicy(max_in_flight=1, max_attempts=1, cooldown_seconds=60)
    reloaded = load_lane(stored.to_dict(), narrowed)
    assert reloaded.policy == narrowed


# --- selection ---------------------------------------------------------------


def test_selection_prefers_value_and_says_why_it_is_holding() -> None:
    lane = _lane(_entry("debt:low", priority=0.4), _entry("debt:high", priority=2.0))
    chosen, reason = next_dispatchable(lane, now=NOW)
    assert chosen is not None and chosen.debt_id == "debt:high"
    assert reason == "selected by priority"

    at_capacity = _lane(_entry("debt:a", state="dispatched", attempts=1), _entry("debt:b"))
    chosen, reason = next_dispatchable(at_capacity, now=NOW)
    assert chosen is None
    assert "maxInFlight ceiling of 1" in reason

    empty = _lane()
    chosen, reason = next_dispatchable(empty, now=NOW)
    assert chosen is None and reason == "no queued Class B debt"


def test_a_just_rejected_debt_cools_down_before_it_can_be_handed_out_again() -> None:
    lane = _lane(_entry("debt:a", attempts=1, last_verdict="reject"))
    chosen, reason = next_dispatchable(lane, now=NOW)
    assert chosen is None
    assert "cooldown after a rejected attempt" in reason

    later = (FROZEN + timedelta(seconds=3601)).isoformat(timespec="seconds").replace("+00:00", "Z")
    chosen, _reason = next_dispatchable(lane, now=later)
    assert chosen is not None

    # A debt that has never been attempted is not cooling down; it is new.
    fresh = _lane(_entry("debt:new"))
    chosen, _reason = next_dispatchable(fresh, now=NOW)
    assert chosen is not None


def test_dispatch_is_refused_beyond_the_ceiling_and_from_the_wrong_state() -> None:
    lane = _lane(_entry("debt:a", state="dispatched", attempts=1), _entry("debt:b"))
    with pytest.raises(LaneError, match="maxInFlight ceiling"):
        mark_dispatched(lane, lane.by_id("debt:b"), dispatch_id="dispatch-x", now=NOW)

    escalated = _lane(_entry("debt:c", state="escalated"))
    with pytest.raises(LaneError, match="only queued debt may be dispatched"):
        mark_dispatched(escalated, escalated.by_id("debt:c"), dispatch_id="dispatch-x", now=NOW)


# --- verdicts ----------------------------------------------------------------


def test_pending_is_not_progress_through_the_lane() -> None:
    """Machinery finding nothing wrong does not move work forward.

    The patch is still unjudged; only the record of what was last checked moves.
    """

    lane = _lane(_entry("debt:a", state="dispatched", attempts=1))
    updated = record_verdict(lane, "debt:a", "pending", now=NOW)
    entry = updated.by_id("debt:a")
    assert entry.state == "dispatched"
    assert entry.last_verdict == "pending"


def test_a_rejected_attempt_returns_to_the_queue_until_the_ceiling() -> None:
    lane = _lane(_entry("debt:a", state="dispatched", attempts=1))
    first = record_verdict(lane, "debt:a", "reject", now=NOW)
    assert first.by_id("debt:a").state == "queued"
    assert first.by_id("debt:a").attempts == 1


def test_repeated_rejection_escalates_rather_than_retrying_forever() -> None:
    """The anti-loop rule.

    A debt that keeps failing bounded repair is not asking for another attempt.
    It is evidence the envelope is wrong, and an envelope is a founder question.
    """

    exhausted = _lane(_entry("debt:a", state="dispatched", attempts=2))
    result = record_verdict(exhausted, "debt:a", "reject", now=NOW)
    entry = result.by_id("debt:a")
    assert entry.state == "escalated"
    assert "the envelope is the likelier defect" in entry.history[-1].reason


def test_escalation_leaves_the_agent_lane_and_acceptance_closes_it() -> None:
    lane = _lane(_entry("debt:a", state="dispatched", attempts=1))
    assert record_verdict(lane, "debt:a", "escalate", now=NOW).by_id("debt:a").state == "escalated"

    accepted = record_verdict(lane, "debt:a", "accept", now=NOW, note="verified by a second reader")
    entry = accepted.by_id("debt:a")
    assert entry.state == "closed"
    assert entry.last_verdict == "accept"
    assert "verified by a second reader" in entry.history[-1].reason


def test_a_verdict_is_refused_from_a_state_that_never_received_work() -> None:
    lane = _lane(_entry("debt:a", state="queued"))
    with pytest.raises(LaneError, match="only dispatched debt may take a verdict"):
        record_verdict(lane, "debt:a", "accept", now=NOW)
    with pytest.raises(LaneError, match="unknown verification verdict"):
        record_verdict(_lane(_entry("debt:a", state="dispatched", attempts=1)), "debt:a", "blessed", now=NOW)


def test_every_transition_records_why() -> None:
    lane = _lane(_entry("debt:a"))
    dispatched = mark_dispatched(lane, lane.by_id("debt:a"), dispatch_id="dispatch-zz", now=NOW)
    rejected = record_verdict(dispatched, "debt:a", "reject", now=NOW)
    reasons = [item.reason for item in rejected.by_id("debt:a").history]
    assert "observed" in reasons[0]
    assert "dispatch-zz" in reasons[1]
    assert "returned to the queue" in reasons[2]


# --- reconciliation ----------------------------------------------------------


def test_reconciliation_admits_new_findings_and_closes_vanished_ones() -> None:
    kinds = {"registry_integrity_failed": "registry-integrity-review"}
    lane = reconcile(_lane(), open_debts=[_debt("debt:a")], dispatchable_kinds=kinds, now=NOW)
    assert lane.by_id("debt:a").state == "queued"

    in_flight = mark_dispatched(lane, lane.by_id("debt:a"), dispatch_id="dispatch-x", now=NOW)
    gone = reconcile(in_flight, open_debts=[], dispatchable_kinds=kinds, now=NOW)
    entry = gone.by_id("debt:a")
    assert entry.state == "closed"
    assert "no longer observed" in entry.history[-1].reason


def test_reconciliation_does_not_reopen_an_escalated_entry() -> None:
    """An escalated entry is waiting on a founder, not on another attempt.

    Re-queueing it on the next scan would loop around the very decision it
    escalated for — the sensor keeps observing the condition precisely because
    nobody has ruled on it yet.
    """

    kinds = {"registry_integrity_failed": "registry-integrity-review"}
    escalated = _lane(_entry("debt:a", state="escalated", attempts=2))
    result = reconcile(escalated, open_debts=[_debt("debt:a")], dispatchable_kinds=kinds, now=NOW)
    assert result.by_id("debt:a").state == "escalated"


def test_a_closed_condition_that_returns_starts_its_attempt_count_over() -> None:
    kinds = {"registry_integrity_failed": "registry-integrity-review"}
    closed = _lane(_entry("debt:a", state="closed", attempts=2, last_verdict="accept"))
    result = reconcile(closed, open_debts=[_debt("debt:a")], dispatchable_kinds=kinds, now=NOW)
    entry = result.by_id("debt:a")
    assert entry.state == "queued"
    assert entry.attempts == 0
    assert entry.last_verdict is None


def test_debt_with_no_dispatch_rule_never_enters_the_lane() -> None:
    from gaia_cli.steward.models import Debt

    unroutable = _debt("debt:c")
    unroutable = Debt(**{**unroutable.__dict__, "kind": "generic_mapping"})
    lane = reconcile(
        _lane(),
        open_debts=[unroutable],
        dispatchable_kinds={"registry_integrity_failed": "registry-integrity-review"},
        now=NOW,
    )
    assert lane.entries == ()


# --- the rolling lane end to end ---------------------------------------------


def test_the_lane_hands_out_one_dispatch_then_reports_itself_at_capacity(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(LaneSensor(count=2))

    result, prompt = render_lane_next(root, controller=controller, prompt=True)
    packet = result.artifact
    assert prompt is not None and prompt.startswith("# Tree Keeper dispatch")
    assert result.receipt.action == "dispatch"  # so `verify` can find the envelope

    status = render_lane(root, controller=controller)
    summary = status.artifact.lane.summary()
    assert summary["counts"]["dispatched"] == 1
    assert summary["counts"]["queued"] == 1
    assert summary["capacity"] == 0

    with pytest.raises(LaneEmpty, match="maxInFlight ceiling"):
        render_lane_next(root, controller=controller)

    lane_state = json.loads((root / ".gaia/steward/lane.json").read_text(encoding="utf-8"))
    assert lane_state["schemaVersion"] == "steward-lane-v1"
    assert len(lane_state["entries"]) == 2


def test_an_empty_lane_is_a_healthy_outcome_distinguishable_from_a_broken_one(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(LaneSensor(count=0))
    with pytest.raises(LaneEmpty, match="no queued Class B debt"):
        render_lane_next(root, controller=controller)
    # LaneEmpty is a RoutingError, so generic handlers still catch it, but a
    # caller that wants to distinguish idle from broken can.
    assert issubclass(LaneEmpty, RoutingError)


def test_a_verification_verdict_rolls_the_lane_forward_without_bookkeeping(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(LaneSensor(count=1))
    result, _prompt = render_lane_next(root, controller=controller)
    packet = result.artifact
    debt_id = packet.debt["id"]

    diff = root / "candidate.diff"
    diff.write_text(
        "diff --git a/docs/leak.html b/docs/leak.html\n@@ -1 +1 @@\n-a\n+b\n", encoding="utf-8"
    )
    proof = root / "proof.json"
    proof.write_text(
        json.dumps(
            {
                "schemaVersion": "steward-proof-transcript-v1",
                "entries": [
                    {"contractIndex": index, "command": "x", "exitCode": 0, "output": "ok"}
                    for index in range(1, len(packet.proof) + 1)
                ],
            }
        ),
        encoding="utf-8",
    )

    verification, _text, _outputs = render_verification(
        root, debt_id, diff_path=diff, proof_path=proof, controller=controller
    )
    assert verification.artifact.verdict == "reject"  # docs/** is outside the envelope

    status = render_lane(root, controller=controller)
    entry = status.artifact.lane.by_id(debt_id)
    assert entry.state == "queued"
    assert entry.last_verdict == "reject"
    assert entry.attempts == 1


def test_recording_an_acceptance_is_always_an_explicit_act(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(LaneSensor(count=1))
    result, _prompt = render_lane_next(root, controller=controller)
    debt_id = result.artifact.debt["id"]

    recorded = record_lane_verdict(
        root, debt_id, "accept", note="reviewed by the founder", controller=controller
    )
    entry = recorded.artifact.lane.by_id(debt_id)
    assert entry.state == "closed"
    assert "reviewed by the founder" in entry.history[-1].reason

    with pytest.raises(RoutingError, match="not tracking debt"):
        record_lane_verdict(root, "debt:nonexistent", "accept", controller=controller)


def test_an_exhausted_debt_leaves_the_lane_and_lands_in_the_founder_queue(tmp_path: Path) -> None:
    """An escalation that has nowhere to land is not an escalation.

    This is the permitted B → C downgrade: bounded repair kept failing, so the
    envelope is the likelier defect, and an envelope is a governance question.
    """

    from gaia_cli.steward.routing import render_founder_queue

    root = _repo(tmp_path)
    controller = _controller(LaneSensor(count=1))
    result, _prompt = render_lane_next(root, controller=controller)
    debt_id = result.artifact.debt["id"]

    # Two rejections is the shipped ceiling.
    record_lane_verdict(root, debt_id, "reject", note="first", controller=controller)
    lane_state = root / ".gaia/steward/lane.json"
    data = json.loads(lane_state.read_text(encoding="utf-8"))
    for entry in data["entries"]:
        # Skip the cooldown rather than sleeping through it; the cooldown has
        # its own unit coverage above.
        entry["lastTransitionAt"] = "2026-08-01T00:00:00Z"
    lane_state.write_text(json.dumps(data), encoding="utf-8")

    render_lane_next(root, controller=controller)
    escalated = record_lane_verdict(root, debt_id, "reject", note="second", controller=controller)
    assert escalated.artifact.lane.by_id(debt_id).state == "escalated"

    queue = render_founder_queue(root, controller=controller)
    decisions = queue.artifact.decisions
    assert len(decisions) == 1
    assert decisions[0].rule == "lane-escalation"
    assert decisions[0].debt_ids == (debt_id,)
    assert "Another attempt under the same envelope is not one of the options" in decisions[0].objective

    # And the lane no longer offers it back to an agent.
    with pytest.raises(LaneEmpty, match="no queued Class B debt"):
        render_lane_next(root, controller=controller)


def test_a_failed_dispatch_leaves_no_lane_move_behind(tmp_path: Path, monkeypatch) -> None:
    """The receipt is the audit precondition for a lane move.

    If the receipt cannot be published, the lane must not remember handing out
    work that has no record of having been authorized.
    """

    import gaia_cli.steward.routing as routing_module

    root = _repo(tmp_path)
    controller = _controller(LaneSensor(count=1))
    render_lane(root, controller=controller)  # establish a queued entry
    before = (root / ".gaia/steward/lane.json").read_bytes()

    monkeypatch.setattr(
        routing_module, "_persist", lambda **_kwargs: (_ for _ in ()).throw(OSError("disk full"))
    )
    with pytest.raises(OSError):
        render_lane_next(root, controller=controller)

    assert (root / ".gaia/steward/lane.json").read_bytes() == before
