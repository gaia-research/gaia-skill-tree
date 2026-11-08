"""Founder ruling F1 (#2283): the executable trust-calibration route.

One skill, one ``gaia dev calibrate <id> <target> --no-build`` promotion to the
grade target. These tests run the real verb on a fixture registry and prove the
route accepts exactly that write and rejects everything outside its envelope:
demotions, frozen skills, recorded prior demotions (F3 proposals), cap-only
suite components to 3★+, refused preflights, extra paths, Class S writes and
hand edits.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from gaia_cli.steward.calibrationroute import (
    CALIBRATION_ROUTE_RULE_ID,
    calibrationViolations,
    ineligibilityReason,
    proveCalibrationEdit,
)
from gaia_cli.steward.models import AuthorityClass, Debt, DispatchPacket, Priority, RoutingBudget
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy
from gaia_cli.steward.routing import RoutingError, _assert_route_eligible
from gaia_cli.steward.sensors import TrustCalibrationDriftSensor
from gaia_cli.steward.verification import (
    PROOF_TRANSCRIPT_SCHEMA,
    calibration_structure_violations,
    checkoutBase,
    evaluate,
    parse_proof_transcript,
    parse_unified_diff,
)
from tests.steward.sensor_fixtures import make_repo
from tests.steward.test_trust_calibration_regression import PARENT

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-11-08T00:00:00Z"
BLOB = {"github": "https://github.com/owner/repo/blob/main/SKILL.md"}
SUBJECT = "registry/named/owner/child.md"


def _record(skill_id: str = "owner/child", **fields: object) -> str:
    skill = {
        "id": skill_id,
        "name": skill_id.split("/")[-1],
        "status": "named",
        "genericSkillRef": "parent-platform",
        "links": BLOB,
        "evidence": [{"type": "github-stars-own", "source": f"https://github.com/{skill_id}", "stars": 100}],
        **fields,
    }
    return "---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---\n\nBody text.\n"


def _repo(tmp_path: Path, **records: dict) -> Path:
    files = {"registry/nodes/fusion/parent-platform.json": json.dumps(PARENT)}
    for skill_id, fields in (records or {"owner/child": {"level": "2★"}}).items():
        files[f"registry/named/{skill_id}.md"] = _record(skill_id, **fields)
    return make_repo(tmp_path / "repo", files)


def _observation(root: Path, skill_id: str = "owner/child"):
    (observation,) = [
        item
        for item in TrustCalibrationDriftSensor().scan(root, NOW)
        if item.kind == "trust_calibration_drift" and item.subject.id == skill_id
    ]
    return observation


def _debt(observation) -> Debt:
    return Debt(
        id=observation.debt_id, kind=observation.kind, subject=observation.subject,
        status="open", first_observed_at=NOW, last_observed_at=NOW, observation_count=1,
        source=observation.source, current_state=dict(observation.current_state),
        observed_state=dict(observation.observed_state), confidence=1.0,
        priority=Priority(0.5, 0.5, 0.5, 0.5, 0.5, 0.5), authority=AuthorityClass.B,
    )


def _rule():
    rule = StewardPolicy.load(REPO_ROOT).dispatch_rule_for("trust_calibration_drift")
    assert rule is not None
    return rule


def _packet(debt: Debt) -> DispatchPacket:
    rule = _rule()
    return DispatchPacket.create(
        debt=debt.to_dict(), evidence={}, authority=AuthorityClass.B, rule=rule.id,
        routine=rule.routine, objective=rule.objective, allowed_paths=rule.allowed_paths,
        allowed_commands=rule.allowed_commands, forbidden_paths=rule.forbidden_paths,
        stop_conditions=rule.stop_conditions, proof=rule.proof,
        budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0), capability=rule.capability,
    )


def _calibrate(root: Path, skill_id: str, level: str) -> str:
    """Run the real verb exactly as a builder would, return the diff, restore the base."""

    from gaia_cli.commands.dev.calibrate import meta_calibrate_command

    meta_calibrate_command(SimpleNamespace(registry=str(root), skill_id=skill_id, level=level, no_build=True))
    diff = subprocess.run(
        ["git", "-C", str(root), "diff", "--no-color"], capture_output=True, text=True, check=True
    ).stdout
    subprocess.run(["git", "-C", str(root), "checkout", "--", "."], check=True)
    return diff


def _verdict(root: Path, packet: DispatchPacket, diff: str):
    change_set = parse_unified_diff(diff, base=checkoutBase(root))
    entries = [
        {"contractIndex": index, "command": f"proof item {index}", "exitCode": 0, "output": "ok"}
        for index in range(1, len(packet.proof) + 1)
    ]
    transcript = parse_proof_transcript(
        json.dumps({"schemaVersion": PROOF_TRANSCRIPT_SCHEMA, "entries": entries}),
        proof_contract_length=len(packet.proof),
    )
    return evaluate(
        packet=packet, change_set=change_set, transcript=transcript,
        debt_source="trust-calibration-drift", sensor_sources=["trust-calibration-drift"],
        baseline_open_debt=[], current_open_debt=[], authority_still_class_b=True,
        calibration_violations=calibration_structure_violations(root, packet, change_set),
    )


# --- the policy envelope ----------------------------------------------------


def _policy_copy(tmp_path: Path, mutate) -> Path:
    data = yaml.safe_load((REPO_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    mutate(data)
    destination = tmp_path / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    destination.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return tmp_path


def test_the_shipped_rule_is_the_ruled_envelope() -> None:
    rule = _rule()
    assert rule.id == CALIBRATION_ROUTE_RULE_ID
    assert rule.allowed_paths == ("registry/named/**",)
    assert {"docs/**", "registry/nodes/**", "registry/schema/**", "skill-trees/**", "founder/**"} <= set(
        rule.forbidden_paths
    )
    assert any("--no-build" in command for command in rule.allowed_commands)
    lane = StewardPolicy.load(REPO_ROOT).lane
    assert (lane.max_in_flight, lane.max_attempts) == (8, 2)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d["routing"]["dispatchRules"]["registry-integrity-review"]["allowedPaths"].append("registry/named/**"),
         "may not reach registry/named"),
        (lambda d: d["routing"]["dispatchRules"]["trust-calibration-drift"]["allowedPaths"].append("scripts/**"),
         "must be exactly"),
        (lambda d: d["routing"]["dispatchRules"]["trust-calibration-drift"]["forbiddenPaths"].remove("docs/**"),
         "must include"),
        (lambda d: d["routing"]["dispatchRules"]["trust-calibration-drift"].__setitem__("debtKind", "unused_import"),
         "belongs to rule trust-calibration-drift"),
    ],
)
def test_policy_cannot_widen_or_move_the_registry_write(tmp_path: Path, mutate, message: str) -> None:
    root = _policy_copy(tmp_path, mutate)
    with pytest.raises(PolicyError, match=message):
        StewardPolicy.load(root)


# --- eligibility: one rule for sensor, routing and verification -------------


ELIGIBLE = {
    "targetLevel": "3★", "direction": "promotion-candidate", "frozen": False,
    "priorGovernedDemotion": None, "capOnlySuiteComponent": False,
    "commandWouldBeRefused": False, "gatesUnmet": [],
}


@pytest.mark.parametrize(
    "change, fragment",
    [
        ({"direction": "ceiling-exceeded", "targetLevel": "1★"}, "ceiling-exceeded"),
        ({"frozen": True}, "frozen"),
        ({"frozen": None}, "frozen"),
        ({"priorGovernedDemotion": {"timestamp": "2026-09-04T00:00:00Z", "details": "retitled as prompt wrapper"}},
         "retitled as prompt wrapper"),
        ({"capOnlySuiteComponent": True}, "F2"),
        ({"capOnlySuiteComponent": None}, "capOnlySuiteComponent"),
        ({"commandWouldBeRefused": True, "gatesUnmet": [{"gate": "star-gate", "message": "no"}]}, "star-gate"),
        ({"commandWouldBeRefused": None}, "could not be evaluated"),
        ({"direction": None}, "direction"),
    ],
)
def test_every_out_of_envelope_finding_is_refused_with_its_reason(change: dict, fragment: str) -> None:
    assert ineligibilityReason(ELIGIBLE, "2★") is None
    assert fragment in (ineligibilityReason({**ELIGIBLE, **change}, "2★") or "")


def test_cap_only_suite_component_may_still_reach_2_stars() -> None:
    assert ineligibilityReason({**ELIGIBLE, "targetLevel": "2★", "capOnlySuiteComponent": True}, "1★") is None


def test_sensor_marks_out_of_envelope_findings_lane_ineligible_and_shows_the_demotion_reason(tmp_path: Path) -> None:
    root = _repo(tmp_path, **{
        "owner/child": {"level": "2★"},
        "owner/demoted": {"level": "1★", "timeline": [
            {"timestamp": "2026-09-04T00:00:00Z", "action": "demote", "details": "Demoted: no evidence yet"},
        ]},
        "owner/over": {"level": "5★"},
    })
    eligible = _observation(root, "owner/child").observed_state
    assert "laneEligible" not in eligible and eligible["capOnlySuiteComponent"] is False
    demoted = _observation(root, "owner/demoted").observed_state
    assert demoted["laneEligible"] is False
    assert "F3 proposal only" in demoted["laneIneligibleReason"]
    assert "Demoted: no evidence yet" in demoted["laneIneligibleReason"]
    over = _observation(root, "owner/over").observed_state
    assert over["laneEligible"] is False and "ceiling-exceeded" in over["laneIneligibleReason"]


def test_routing_refuses_ineligible_and_accepts_eligible(tmp_path: Path) -> None:
    root = _repo(tmp_path, **{"owner/child": {"level": "2★"}, "owner/over": {"level": "5★"}})
    rule = _rule()
    _assert_route_eligible(rule, _debt(_observation(root, "owner/child")))
    with pytest.raises(RoutingError, match="ceiling-exceeded"):
        _assert_route_eligible(rule, _debt(_observation(root, "owner/over")))


# --- verification of the real verb ------------------------------------------


def test_the_real_calibrate_write_is_accepted(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    packet = _packet(_debt(_observation(root)))
    diff = _calibrate(root, "owner/child", "3★")
    verdict = _verdict(root, packet, diff)
    assert verdict.scope_valid, verdict.reasons
    assert verdict.verdict == "pending"


def test_a_refused_preflight_writes_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path, **{"owner/child": {"level": "2★", "links": {"github": "https://github.com/owner/repo"}}})
    from gaia_cli.commands.dev.calibrate import meta_calibrate_command

    with pytest.raises(SystemExit):
        meta_calibrate_command(SimpleNamespace(registry=str(root), skill_id="owner/child", level="3★", no_build=True))
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True)
    assert status.stdout.strip() == ""


def _edited(diff_root: Path, mutate) -> str:
    path = diff_root / SUBJECT
    text = path.read_text(encoding="utf-8")
    path.write_text(mutate(text), encoding="utf-8")
    diff = subprocess.run(["git", "-C", str(diff_root), "diff", "--no-color"], capture_output=True, text=True).stdout
    subprocess.run(["git", "-C", str(diff_root), "checkout", "--", "."], check=True)
    return diff


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda t: t.replace("level: 2★", "level: 3★"), "timeline"),  # hand edit, no event
        (lambda t: t.replace("level: 2★", "level: 4★"), "post level"),
        (lambda t: t.replace("Body text.", "Body text changed."), "body changed"),
        (lambda t: t.replace("status: named", "status: awakened"), "status"),
    ],
)
def test_hand_edits_are_rejected(tmp_path: Path, mutate, fragment: str) -> None:
    root = _repo(tmp_path)
    packet = _packet(_debt(_observation(root)))
    verdict = _verdict(root, packet, _edited(root, mutate))
    assert not verdict.scope_valid
    assert verdict.verdict == "reject"
    assert any(fragment in reason for reason in verdict.reasons)


def test_a_class_s_write_or_second_skill_is_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path, **{"owner/child": {"level": "2★"}, "owner/other": {"level": "2★"}})
    packet = _packet(_debt(_observation(root)))
    from gaia_cli.commands.dev.calibrate import meta_calibrate_command

    meta_calibrate_command(SimpleNamespace(registry=str(root), skill_id="owner/child", level="3★", no_build=True))
    meta_calibrate_command(SimpleNamespace(registry=str(root), skill_id="owner/other", level="3★", no_build=True))
    diff = subprocess.run(["git", "-C", str(root), "diff", "--no-color"], capture_output=True, text=True).stdout
    subprocess.run(["git", "-C", str(root), "checkout", "--", "."], check=True)
    verdict = _verdict(root, packet, diff)
    assert verdict.verdict == "reject"
    assert any("must touch exactly" in reason for reason in verdict.reasons)


def test_a_class_s_artifact_in_the_packet_is_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "docs/graph").mkdir(parents=True)
    (root / "docs/graph/gaia.json").write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "class s"], check=True)
    packet = _packet(_debt(_observation(root)))
    from gaia_cli.commands.dev.calibrate import meta_calibrate_command

    meta_calibrate_command(SimpleNamespace(registry=str(root), skill_id="owner/child", level="3★", no_build=True))
    (root / "docs/graph/gaia.json").write_text('{"regenerated": true}\n', encoding="utf-8")
    diff = subprocess.run(["git", "-C", str(root), "diff", "--no-color"], capture_output=True, text=True).stdout
    subprocess.run(["git", "-C", str(root), "checkout", "--", "."], check=True)
    verdict = _verdict(root, packet, diff)
    assert verdict.verdict == "reject"
    assert any("forbiddenPaths" in reason and "docs/graph/gaia.json" in reason for reason in verdict.reasons)
    assert any("must touch exactly" in reason for reason in verdict.reasons)


def test_an_unproven_calibration_is_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    packet = _packet(_debt(_observation(root)))
    diff = _calibrate(root, "owner/child", "3★")
    change_set = parse_unified_diff(diff, base=checkoutBase(root))
    verdict = evaluate(
        packet=packet, change_set=change_set,
        transcript=parse_proof_transcript(
            json.dumps({"schemaVersion": PROOF_TRANSCRIPT_SCHEMA, "entries": [
                {"contractIndex": i, "command": "x", "exitCode": 0, "output": "ok"}
                for i in range(1, len(packet.proof) + 1)
            ]}),
            proof_contract_length=len(packet.proof),
        ),
        debt_source="trust-calibration-drift", sensor_sources=["trust-calibration-drift"],
        baseline_open_debt=[], current_open_debt=[], authority_still_class_b=True,
    )
    assert verdict.verdict == "reject"
    assert any("no calibration proof" in reason for reason in verdict.reasons)


def test_a_finding_that_became_ineligible_since_dispatch_is_rejected_live(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    packet = _packet(_debt(_observation(root)))
    diff = _calibrate(root, "owner/child", "3★")
    # A curator records a demotion before verification: F3 makes it a proposal again.
    path = root / SUBJECT
    meta = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
    meta["timeline"] = [{"timestamp": "2026-11-08T00:00:00Z", "action": "demote", "details": "no evidence"}]
    path.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n\nBody text.\n")
    subprocess.run(["git", "-C", str(root), "commit", "-qam", "curator demotion"], check=True)
    violations = calibrationViolations(
        root, packet_debt=packet.debt, change_paths=(SUBJECT,), created_or_deleted=(),
        base_text=(root / SUBJECT).read_text(encoding="utf-8"), post_text=None,
    )
    assert any("live re-derivation refuses" in item and "F3" in item for item in violations)


def test_the_structural_proof_rejects_a_second_event_and_a_demote(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    base = (root / SUBJECT).read_text(encoding="utf-8")
    meta = yaml.safe_load(base.split("---", 2)[1])
    meta["level"] = "3★"
    meta["timeline"] = [
        {"timestamp": "t1", "action": "rank_up", "details": "Calibrated level from 2★ to 3★"},
        {"timestamp": "t2", "action": "rank_up", "details": "Calibrated level from 2★ to 3★"},
    ]
    two = "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n\nBody text.\n"
    assert any("exactly one appended event" in item for item in proveCalibrationEdit(
        skill_id="owner/child", current_level="2★", target_level="3★", base_text=base, post_text=two))
    meta["timeline"] = [{"timestamp": "t1", "action": "demote", "details": "Calibrated level from 2★ to 3★"}]
    demote = "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n\nBody text.\n"
    assert any("not 'rank_up'" in item for item in proveCalibrationEdit(
        skill_id="owner/child", current_level="2★", target_level="3★", base_text=base, post_text=demote))
