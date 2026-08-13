"""Steward V1.5 — the founder digest."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.digest import decision_labels, digest_payload, render_founder_digest
from gaia_cli.steward.lane import Lane, LanePolicy
from gaia_cli.steward.models import FounderDecision, FounderQueue, Observation, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.routing import render_founder_digest as route_digest


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 8, 13, tzinfo=timezone.utc)
EMPTY_LANE = Lane(entries=(), policy=LanePolicy(max_in_flight=1, max_attempts=2, cooldown_seconds=3600))


def _repo(tmp_path: Path) -> Path:
    policy = tmp_path / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    return tmp_path


class DigestSensor:
    id = "digest-fixture"

    def __init__(self, *, mappings: int = 0, broken: bool = False) -> None:
        self.mappings = mappings
        self.broken = broken

    def scan(self, root: Path, observed_at: str) -> list[Observation]:
        if self.broken:
            raise RuntimeError("the sensor could not read its input")
        return [
            Observation(
                kind="generic_mapping",
                subject=Subject("generic-mapping-candidate", f"owner/candidate-{number}"),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"genericMapping": "unresolved"},
                observed_state={
                    "decisionTarget": f"generic-mapping/owner/candidate-{number}",
                    "sourceRepo": "owner/repo",
                    "inputDigest": "deadbeef" * 8,
                },
            )
            for number in range(self.mappings)
        ]


def _controller(sensor: DigestSensor) -> StewardController:
    return StewardController(sensors=[sensor], clock=lambda: FROZEN)


def _decision(target: str, rule: str = "generic-mapping-decision", debts: int = 1) -> FounderDecision:
    return FounderDecision.create(
        rule=rule,
        decision_target=target,
        objective="Decide the canonical generic mapping for the explicit normalized target.",
        debt_ids=tuple(f"debt:{target}:{index}" for index in range(debts)),
        evidence=tuple(
            {"debtId": f"debt:{target}:{index}", "subject": {"id": target}, "observedState": {"sourceRepo": "o/r"}}
            for index in range(debts)
        ),
    )


# --- labels ------------------------------------------------------------------


def test_labels_are_short_stable_and_survive_a_decision_being_resolved() -> None:
    """A positional C-001..C-00N would renumber on every resolution.

    A label that moves is not a label — the founder cannot refer to one out
    loud on Tuesday and mean the same thing on Wednesday.
    """

    first = _decision("generic-mapping/a")
    second = _decision("generic-mapping/b")
    third = _decision("generic-mapping/c")

    full = decision_labels([first, second, third])
    after_resolution = decision_labels([first, third])

    assert full[first.decision_id] == after_resolution[first.decision_id]
    assert full[third.decision_id] == after_resolution[third.decision_id]
    assert all(label.startswith("C-") and len(label) == 6 for label in full.values())


def test_labels_lengthen_together_when_they_would_collide() -> None:
    """Two printings of one queue must not disagree about label length."""

    class Colliding:
        def __init__(self, digest: str) -> None:
            self.decision_id = f"decision-{digest}"

    labels = decision_labels([Colliding("aaaabbbb"), Colliding("aaaacccc")])  # type: ignore[list-item]
    values = list(labels.values())
    assert len(set(values)) == 2
    assert len({len(value) for value in values}) == 1
    assert values[0] != values[1]


# --- report by exception -----------------------------------------------------


def test_a_quiet_repository_produces_a_short_digest_that_says_so(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(DigestSensor(mappings=0))
    _result, text = route_digest(root, controller=controller)

    assert "Nothing requires a decision." in text
    assert "expected outcome" in text
    assert "Question" not in text
    # A digest that summarises a healthy repository at length trains its
    # reader to stop opening it.
    assert len(text.splitlines()) < 25


def test_decisions_carry_the_question_what_they_block_and_the_evidence(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(DigestSensor(mappings=2))
    _result, text = route_digest(root, controller=controller)

    assert "2 decision(s) require founder judgment" in text
    assert "Steward has taken\nno action on any of them." in text
    assert text.count("Question") == 2
    assert "Blocks  1 debt item(s)" in text
    assert "sourceRepo: owner/repo" in text
    assert "owner/candidate-0" in text


def test_provenance_noise_is_left_out_of_the_evidence(tmp_path: Path) -> None:
    """The digest is for deciding, not for auditing.

    Digests and input paths are how the observation was made, not what is
    being asked; the receipt already carries them verbatim.
    """

    root = _repo(tmp_path)
    _result, text = route_digest(root, controller=_controller(DigestSensor(mappings=1)))
    assert "inputDigest" not in text
    assert "deadbeef" not in text


# --- recommendations ---------------------------------------------------------


def test_steward_offers_no_recommendation_where_it_has_no_basis() -> None:
    queue = FounderQueue.create((_decision("generic-mapping/x"),))
    text = render_founder_digest(_scan_stub(), queue, EMPTY_LANE)
    assert "None. This turns on product, ontology, or prestige judgment" in text


def test_a_lane_escalation_carries_a_recommendation_that_is_derivable() -> None:
    """The one Class C question with a mechanically obvious shape.

    Bounded repair reached its ceiling, so the envelope is the likelier
    defect — that follows from the ceiling itself, not from an opinion.
    """

    queue = FounderQueue.create(
        (_decision("lane-escalation/cli-contract-drift", rule="lane-escalation", debts=3),)
    )
    text = render_founder_digest(_scan_stub(), queue, EMPTY_LANE)
    flowed = " ".join(text.split())  # the digest wraps to 66 columns
    assert "reached its attempt ceiling" in flowed
    assert "the envelope is the likelier defect" in flowed.lower()
    assert "cli-contract-drift" in text
    assert "Blocks  3 debt item(s)" in text
    # And it never suggests the one thing the ceiling already ruled out.
    assert "trying again under the same terms" in flowed


def test_the_payload_carries_the_same_recommendation_as_the_text() -> None:
    queue = FounderQueue.create((
        _decision("generic-mapping/x"),
        _decision("lane-escalation/cli-contract-drift", rule="lane-escalation"),
    ))
    payload = digest_payload(_scan_stub(), queue, EMPTY_LANE)
    by_rule = {item["rule"]: item for item in payload["decisions"]}
    assert by_rule["generic-mapping-decision"]["recommendation"] is None
    assert "attempt ceiling" in by_rule["lane-escalation"]["recommendation"]
    assert all(item["label"].startswith("C-") for item in payload["decisions"])


# --- health ------------------------------------------------------------------


def test_blindness_is_reported_louder_than_debt(tmp_path: Path) -> None:
    """A sensor that could not run means Steward does not know what is true.

    Open debt is information; blindness is a defect, and it pauses the Class A
    lane. It must not read as one more line in a status table.
    """

    from gaia_cli.steward.routing import RoutingError

    root = _repo(tmp_path)
    controller = _controller(DigestSensor(broken=True))
    # Routing refuses outright while coverage is unknown — a blind Steward
    # must not hand out a queue that looks complete.
    with pytest.raises(RoutingError, match="sensor coverage is unknown"):
        route_digest(root, controller=controller)


def test_the_health_block_reports_class_counts_and_the_oldest_debt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _result, text = route_digest(root, controller=_controller(DigestSensor(mappings=2)))
    assert "Sensor coverage          healthy" in text
    assert "(A 0  B 0  C 2)" in text
    assert "Oldest open debt" in text
    assert "Class B lane             0 queued, 0 in flight, 0 escalated" in text
    assert "Decisions for you        2" in text


def test_the_digest_is_a_pure_projection_and_writes_no_second_receipt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(DigestSensor(mappings=1))
    result, _text = route_digest(root, controller=controller)
    receipts = sorted(result.receipt_path.parent.glob("*.json"))
    # One scan receipt plus one founder routing receipt. The digest adds none.
    assert len(receipts) == 2
    assert result.receipt.action == "founder"


def _scan_stub():
    """A minimal ScanResult stand-in for pure-rendering tests."""

    from gaia_cli.steward.controller import ScanResult
    from gaia_cli.steward.models import Receipt

    receipt = Receipt(
        run_id="steward-20260813T000000Z-0000000000000000",
        started_at="2026-08-13T00:00:00Z",
        finished_at="2026-08-13T00:00:00Z",
        observations_collected=4,
        coverage_unknown=(),
        debt_created=(),
        debt_updated=(),
        debt_resolved=(),
        open_debt=(),
        authority_counts={"A": 0, "B": 0, "C": 0},
        result_status="debt_reported",
    )
    return ScanResult(
        observations=(),
        debts=(),
        receipt=receipt,
        debt_state_path=Path("debt.json"),
        receipt_path=Path("receipt.json"),
        fresh_open_debt_ids=frozenset(),
    )
