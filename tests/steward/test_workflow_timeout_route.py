"""Founder ruling #14 (steward-workflow-timeout-route, #2283).

One narrow Class B route may write ``.github/workflows/*.yml`` to add job
timeouts. Everything else under ``.github/`` stays forbidden to every other
rule, and nothing in policy can widen the exception.
"""

from __future__ import annotations

import difflib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.models import AuthorityClass, DispatchPacket, Observation, RoutingBudget, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy
from gaia_cli.steward.routing import RoutingError, render_dispatch
from gaia_cli.steward.sensors_ci import CiWorkflowSensor
from gaia_cli.steward.verification import (
    PROOF_TRANSCRIPT_SCHEMA,
    evaluate,
    parse_proof_transcript,
    parse_unified_diff,
)
from gaia_cli.steward.workflowproof import apply_patch
from tests.steward.sensor_fixtures import make_repo


REPO_ROOT = Path(__file__).resolve().parents[2]
RULE = "workflow-timeout-repair"
NOW = "2026-11-07T00:00:00Z"
LOCK_SUFFIX = ".lock.yml"
FROZEN = datetime(2026, 11, 7, tzinfo=timezone.utc)


def _policy_copy(tmp_path: Path, mutate) -> Path:
    data = yaml.safe_load((REPO_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    mutate(data)
    destination = tmp_path / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    destination.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return tmp_path


def _live_rule():
    rule = StewardPolicy.load(REPO_ROOT).dispatch_rule_for("workflow_hygiene")
    assert rule is not None
    return rule


# --- the route as shipped ---------------------------------------------------


def test_the_route_is_exactly_the_ruled_envelope() -> None:
    rule = _live_rule()
    assert rule.id == RULE
    assert rule.authority is AuthorityClass.B
    assert rule.allowed_paths == (".github/workflows/*.yml",)
    assert ".github/**" not in rule.forbidden_paths
    for excluded in (
        ".github/workflows/*.lock.yml",
        ".github/workflows/shared/**",
        ".github/workflows/_disabled/**",
        ".github/actions/**",
        "founder/**",
        ".gaia/steward/**",
        "registry/**",
        "src/**",
        "tests/**",
        "docs/**",
    ):
        assert excluded in rule.forbidden_paths, excluded
    assert any("independent" in item.lower() for item in rule.proof)
    assert any("timeout-minutes" in item for item in rule.stop_conditions)
    assert (REPO_ROOT / rule.prompt_guide).is_file()


def test_no_other_debt_kind_can_write_dot_github() -> None:
    """The exception belongs to workflow_hygiene alone."""

    policy = StewardPolicy.load(REPO_ROOT)
    others = [rule for rule in policy.dispatch_rules.values() if rule.debt_kind != "workflow_hygiene"]
    assert len(others) >= 6
    for rule in others:
        assert ".github/**" in rule.forbidden_paths, rule.id
        for allowed in rule.allowed_paths:
            assert not allowed.startswith(".github"), (rule.id, allowed)
            assert "*" not in allowed.replace("/**", ""), (rule.id, allowed)
    for executor in policy.repair_executors.values():
        assert not str(executor.writable_path).startswith(".github"), executor.debt_kind


@pytest.mark.parametrize(
    "allowed",
    [
        [".github/workflows/*.yml"],
        [".github/workflows/**"],
        [".github/**"],
        [".github/workflows/*.yml", "scripts/**"],
    ],
)
def test_policy_refuses_dot_github_for_any_other_debt_kind(tmp_path: Path, allowed: list[str]) -> None:
    def mutate(data) -> None:
        data["routing"]["dispatchRules"]["registry-integrity-review"]["allowedPaths"] = allowed

    with pytest.raises(PolicyError):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


def test_policy_refuses_a_file_glob_in_another_rules_forbidden_list(tmp_path: Path) -> None:
    def mutate(data) -> None:
        data["routing"]["dispatchRules"]["registry-integrity-review"]["forbiddenPaths"].append(
            ".github/workflows/*.lock.yml"
        )

    with pytest.raises(PolicyError, match="reserved for the workflow_hygiene route"):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


@pytest.mark.parametrize(
    "allowed",
    [
        [".github/workflows/**"],
        [".github/**"],
        [".github/workflows/*.yaml"],
        [".github/workflows/*.yml", "scripts/**"],
        ["scripts/**"],
        [".github/actions/*.yml"],
    ],
)
def test_policy_pins_the_workflow_routes_allowed_paths_exactly(tmp_path: Path, allowed: list[str]) -> None:
    def mutate(data) -> None:
        data["routing"]["dispatchRules"][RULE]["allowedPaths"] = allowed

    with pytest.raises(PolicyError, match="must be exactly"):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


def test_policy_refuses_to_void_the_route_by_forbidding_all_of_dot_github(tmp_path: Path) -> None:
    def mutate(data) -> None:
        data["routing"]["dispatchRules"][RULE]["forbiddenPaths"].append(".github/**")

    with pytest.raises(PolicyError, match="may not forbid .github/"):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


@pytest.mark.parametrize(
    "dropped",
    [
        ".github/workflows/*.lock.yml",
        ".github/workflows/shared/**",
        ".github/workflows/_disabled/**",
        ".github/actions/**",
        "founder/**",
        "skill-trees/**",
    ],
)
def test_policy_requires_every_workflow_route_exclusion(tmp_path: Path, dropped: str) -> None:
    def mutate(data) -> None:
        listed = data["routing"]["dispatchRules"][RULE]["forbiddenPaths"]
        listed.remove(dropped)

    with pytest.raises(PolicyError, match="must include the protected paths"):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


# --- shared verification helpers ---------------------------------------------------------


def _packet() -> DispatchPacket:
    rule = _live_rule()
    return DispatchPacket.create(
        debt={"id": "debt:workflow_hygiene:x", "kind": "workflow_hygiene"},
        evidence={"findings": [{"rule": "missing-timeout", "detail": "job build has no timeout-minutes"}]},
        authority=AuthorityClass.B,
        rule=rule.id,
        routine=rule.routine,
        objective=rule.objective,
        allowed_paths=rule.allowed_paths,
        allowed_commands=rule.allowed_commands,
        forbidden_paths=rule.forbidden_paths,
        stop_conditions=rule.stop_conditions,
        proof=rule.proof,
        budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0),
        capability=rule.capability,
    )


def _transcript(packet: DispatchPacket):
    entries = [
        {"contractIndex": index, "command": f"proof item {index}", "exitCode": 0, "output": "ok"}
        for index in range(1, len(packet.proof) + 1)
    ]
    return parse_proof_transcript(
        json.dumps({"schemaVersion": PROOF_TRANSCRIPT_SCHEMA, "entries": entries}),
        proof_contract_length=len(packet.proof),
    )


def _verdict(diff: str, packet: DispatchPacket | None = None, *, baseline: dict[str, str | None] | None = None):
    packet = packet or _packet()
    return evaluate(
        packet=packet,
        change_set=parse_unified_diff(diff),
        transcript=_transcript(packet),
        debt_source="ci-workflow",
        sensor_sources=["ci-workflow"],
        baseline_open_debt=[],
        current_open_debt=[],
        authority_still_class_b=True,
        workflow_baseline=baseline,
    )


CI = ".github/workflows/ci.yml"


# --- policy binding: rule id and debt kind are paired ---------------------------


def test_renaming_the_original_workflow_rule_is_refused(tmp_path: Path) -> None:
    """Moving the shipped rule under another id must not carry the .github exception with it."""

    def mutate(data) -> None:
        rules = data["routing"]["dispatchRules"]
        rules["arbitrary-workflow-rule"] = rules.pop(RULE)

    with pytest.raises(PolicyError, match="belongs to rule workflow-timeout-repair and debt kind workflow_hygiene"):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


def test_a_second_workflow_hygiene_rule_is_refused(tmp_path: Path) -> None:
    def mutate(data) -> None:
        rules = data["routing"]["dispatchRules"]
        rules["another-workflow-rule"] = dict(rules[RULE])

    with pytest.raises(PolicyError, match="multiple dispatch rules|belongs to rule"):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


def test_the_workflow_rule_id_cannot_be_pointed_at_another_debt_kind(tmp_path: Path) -> None:
    def mutate(data) -> None:
        rules = data["routing"]["dispatchRules"]
        rules[RULE] = dict(rules["registry-integrity-review"])  # same id, a different debt kind
        del rules["registry-integrity-review"]

    with pytest.raises(PolicyError, match="belongs to rule"):
        StewardPolicy.load(_policy_copy(tmp_path, mutate))


# --- dispatch eligibility: only pure missing-timeout debts get the packet ------------


class _WorkflowSensor:
    id = "ci-workflow"

    def __init__(self, subject: str, findings: list[dict[str, str]], **state: object) -> None:
        self.subject, self.findings, self.state = subject, findings, state

    def scan(self, root: Path, observed_at: str) -> list[Observation]:
        return [
            Observation(
                kind="workflow_hygiene",
                subject=Subject("workflow", self.subject),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"findingCount": 0},
                observed_state={
                    "findingCount": len(self.findings),
                    "findings": self.findings,
                    "findingsCapped": False,
                    **self.state,
                },
            )
        ]


def _dispatch(tmp_path: Path, subject: str, findings: list[dict[str, str]], **state: object):
    root = tmp_path / "repo"
    destination = root / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, destination)
    decisions_dest = root / "founder" / "steward" / "decisions"
    decisions_dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO_ROOT / "founder" / "steward" / "decisions", decisions_dest, dirs_exist_ok=True)
    sensor = _WorkflowSensor(subject, findings, **state)
    controller = StewardController(sensors=[sensor], clock=lambda: FROZEN)
    debt_id = sensor.scan(root, NOW)[0].debt_id
    return render_dispatch(root, debt_id, controller=controller)


MISSING = {"rule": "missing-timeout", "detail": "job build has no timeout-minutes"}
OTHER = {"rule": "write-all-permissions", "detail": "$.permissions grants write-all"}


def test_a_pure_missing_timeout_debt_gets_the_workflow_packet(tmp_path: Path) -> None:
    result = _dispatch(tmp_path, CI, [MISSING])
    assert isinstance(result.artifact, DispatchPacket)
    assert result.artifact.rule == RULE
    assert result.artifact.allowed_paths == (".github/workflows/*.yml",)


@pytest.mark.parametrize(
    ("subject", "findings", "state", "why"),
    [
        (CI, [OTHER], {}, "other than missing-timeout"),
        (CI, [MISSING, OTHER], {}, "other than missing-timeout"),
        (CI, [{"rule": "unparseable-workflow", "detail": "x"}], {}, "other than missing-timeout"),
        (CI, [MISSING], {"findingsCapped": True}, "empty or capped"),
        (CI, [], {}, "empty or capped"),
        (CI, [MISSING], {"laneEligible": False, "laneIneligibleReason": "gh-aw generated"}, "gh-aw generated"),
        (".github/workflows/steward-build-pi.lock.yml", [MISSING], {}, "direct-child hand-written"),
        (".github/workflows/ci.yaml", [MISSING], {}, "direct-child hand-written"),
        (".github/workflows/shared/x.yml", [MISSING], {}, "direct-child hand-written"),
    ],
)
def test_explicit_dispatch_refuses_a_debt_the_route_may_not_repair(
    tmp_path: Path, subject: str, findings: list[dict[str, str]], state: dict[str, object], why: str
) -> None:
    with pytest.raises(RoutingError, match=why):
        _dispatch(tmp_path, subject, findings, **state)


# --- structural proof ------------------------------------------------------------------

BEFORE = """\
name: ci
on:
  pull_request:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          echo safe
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    steps:
      - run: echo lint
"""


def _timed(text: str, job: str = "build", value: str = "15") -> str:
    """Add a job-level timeout directly under ``runs-on`` of the named job."""

    marker = f"  {job}:\n    runs-on: ubuntu-latest\n"
    assert marker in text
    return text.replace(marker, marker + f"    timeout-minutes: {value}\n", 1)


def _patch(path: str, before: str | None, after: str) -> str:
    old = [] if before is None else before.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            old,
            after.splitlines(keepends=True),
            fromfile="/dev/null" if before is None else f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )


def _structural(before: str, after: str, path: str = CI):
    return _verdict(_patch(path, before, after), baseline={path: before})


def test_a_proper_job_timeout_passes_the_structural_proof() -> None:
    verdict = _structural(BEFORE, _timed(BEFORE))
    assert verdict.scope_valid, verdict.reasons
    assert verdict.verdict == "pending"  # the machine never accepts


def test_two_missing_timeouts_in_one_file_pass_together() -> None:
    before = BEFORE.replace("    timeout-minutes: 360\n", "")
    after = _timed(_timed(before, "build", "15"), "lint", "10")
    assert _structural(before, after).scope_valid


def _step_level(text: str) -> str:
    return text.replace("      - uses: actions/checkout@v4\n", "      - uses: actions/checkout@v4\n        timeout-minutes: 15\n", 1)


def _script_injection(text: str) -> str:
    # The reviewer's concrete bypass: a real job timeout plus a line inside a run: | scalar.
    return _timed(text).replace("          echo safe\n", "          echo safe\n          timeout-minutes: 15\n", 1)


def _duplicate_override(text: str) -> str:
    return text.replace("    timeout-minutes: 360\n", "    timeout-minutes: 360\n    timeout-minutes: 1\n", 1)


def _changed_value(text: str) -> str:
    return text.replace("timeout-minutes: 360", "timeout-minutes: 60", 1)


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("step-level key", lambda t: _step_level(_timed(t))),
        ("script injection inside a run scalar", _script_injection),
        ("duplicate key overriding an existing timeout", _duplicate_override),
        ("rewriting an existing timeout", _changed_value),
        ("unicode numerals", lambda t: _timed(t, value="١٥")),
        ("fullwidth numerals", lambda t: _timed(t, value="１５")),
        ("hex integer", lambda t: _timed(t, value="0x0F")),
        ("octal-looking integer", lambda t: _timed(t, value="015")),
        ("underscore integer", lambda t: _timed(t, value="1_5")),
        ("sexagesimal integer", lambda t: _timed(t, value="1:30")),
        ("quoted string", lambda t: _timed(t, value="'15'")),
        ("float", lambda t: _timed(t, value="15.0")),
        ("boolean", lambda t: _timed(t, value="true")),
        ("zero", lambda t: _timed(t, value="0")),
        ("above the platform ceiling", lambda t: _timed(t, value="361")),
        ("explicit tag", lambda t: _timed(t, value="!!int 15")),
        ("alias value", lambda t: _timed(t, value="*limit")),
        ("a second change beside the timeout", lambda t: _timed(t).replace("contents: read", "contents: write", 1)),
        ("a new step beside the timeout", lambda t: _timed(t) + "      - run: echo extra\n"),
        ("a new job", lambda t: _timed(t) + "  extra:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: echo x\n"),
    ],
)
def test_the_structural_proof_rejects_anything_but_a_plain_job_timeout(label: str, mutate) -> None:
    verdict = _structural(BEFORE, mutate(BEFORE))
    assert not verdict.scope_valid, label
    assert verdict.verdict == "reject", label


def test_aliases_and_anchors_in_the_baseline_are_rejected() -> None:
    anchored = BEFORE.replace("  build:\n    runs-on: ubuntu-latest\n", "  build:\n    runs-on: &runner ubuntu-latest\n", 1)
    assert "&runner" in anchored
    verdict = _structural(anchored, anchored.replace("    runs-on: &runner ubuntu-latest\n", "    runs-on: &runner ubuntu-latest\n    timeout-minutes: 15\n", 1))
    assert not verdict.scope_valid
    assert any("anchors" in item for item in verdict.reasons)


def test_an_added_key_inside_an_anchored_mapping_is_rejected() -> None:
    before = BEFORE.replace(
        "jobs:\n",
        "x-env: &env\n  A: '1'\njobs:\n",
        1,
    ).replace("      - run: echo lint\n", "      - run: echo lint\n        env: *env\n", 1)
    after = before.replace("  A: '1'\n", "  A: '1'\n  timeout-minutes: 15\n", 1)
    verdict = _structural(before, after)
    assert not verdict.scope_valid
    assert any("aliases" in item or "anchors" in item for item in verdict.reasons)


def test_multi_document_baseline_is_rejected() -> None:
    before = BEFORE + "---\nname: second\njobs:\n  z:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo z\n"
    verdict = _structural(before, _timed(before))
    assert not verdict.scope_valid
    assert any("exactly one YAML document" in item for item in verdict.reasons)


def test_a_duplicate_key_baseline_is_rejected() -> None:
    before = BEFORE.replace("permissions:\n  contents: read\n", "permissions:\n  contents: read\npermissions:\n  contents: write\n", 1)
    verdict = _structural(before, _timed(before))
    assert not verdict.scope_valid
    assert any("duplicate mapping key" in item for item in verdict.reasons)


def test_a_reusable_workflow_call_job_cannot_take_a_timeout() -> None:
    before = BEFORE + "  call:\n    uses: ./.github/workflows/other.yml\n"
    after = before.replace("    uses: ./.github/workflows/other.yml\n", "    uses: ./.github/workflows/other.yml\n    timeout-minutes: 15\n", 1)
    verdict = _structural(before, after)
    assert not verdict.scope_valid
    assert any("reusable-workflow" in item for item in verdict.reasons)


def test_without_a_baseline_a_workflow_edit_is_unprovable_and_rejected() -> None:
    verdict = _verdict(_patch(CI, BEFORE, _timed(BEFORE)), baseline=None)
    assert not verdict.scope_valid
    assert any("no baseline content" in item for item in verdict.reasons)


def test_a_diff_that_does_not_apply_to_the_baseline_is_rejected() -> None:
    verdict = _verdict(_patch(CI, BEFORE, _timed(BEFORE)), baseline={CI: BEFORE.replace("ubuntu-latest", "macos-latest")})
    assert not verdict.scope_valid
    assert any("does not apply" in item for item in verdict.reasons)


def test_a_no_op_workflow_diff_proves_nothing_and_is_rejected() -> None:
    verdict = _structural(BEFORE, BEFORE.replace("name: ci", "name: ci2", 1))
    assert not verdict.scope_valid


def test_no_newline_at_end_of_file_is_applied_exactly_but_the_rewrite_is_rejected() -> None:
    """The applier is exact; the byte gate then refuses to rewrite the last line."""

    before = "jobs:\n  a:\n    runs-on: x"
    after = "jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5"
    diff = (
        f"diff --git a/{CI} b/{CI}\n--- a/{CI}\n+++ b/{CI}\n"
        "@@ -1,3 +1,4 @@\n jobs:\n   a:\n-    runs-on: x\n\\ No newline at end of file\n"
        "+    runs-on: x\n+    timeout-minutes: 5\n\\ No newline at end of file\n"
    )
    changes = parse_unified_diff(diff)
    assert apply_patch(before, changes.workflow_patches[0][1]) == after
    verdict = _verdict(diff, baseline={CI: before})
    assert not verdict.scope_valid
    assert any("existing byte changes" in item or "rewrites an existing line" in item for item in verdict.reasons)


# --- creation, deletion, header-only sections ---------------------------------------------


def test_creating_a_workflow_is_rejected_even_when_it_is_only_a_timeout_line() -> None:
    new_file = (
        f"diff --git a/{CI} b/{CI}\nnew file mode 100644\nindex 0000000..2222222\n"
        f"--- /dev/null\n+++ b/{CI}\n@@ -0,0 +1 @@\n+    timeout-minutes: 15\n"
    )
    verdict = _verdict(new_file, baseline={CI: None})
    assert not verdict.scope_valid
    assert verdict.change_set.changes[0].created_file
    assert any("creation is never allowed" in item for item in verdict.change_set.workflow_edit_violations)


def test_creating_a_workflow_without_the_new_file_mode_line_is_still_creation() -> None:
    new_file = f"--- /dev/null\n+++ b/{CI}\n@@ -0,0 +1 @@\n+    timeout-minutes: 15\n"
    verdict = _verdict(new_file, baseline={CI: None})
    assert not verdict.scope_valid
    assert verdict.change_set.changes[0].created_file


def test_an_empty_new_workflow_with_no_hunks_is_still_seen_and_rejected() -> None:
    """git applies a header-only section; it has no ---/+++ pair, so it used to be invisible."""

    empty = f"diff --git a/{CI} b/{CI}\nnew file mode 100644\nindex 0000000..e69de29\n"
    verdict = _verdict(empty, baseline={CI: None})
    assert not verdict.scope_valid
    assert [change.path for change in verdict.change_set.changes] == [CI]
    assert verdict.change_set.changes[0].created_file


def test_a_header_only_section_outside_the_envelope_is_now_scope_checked() -> None:
    empty = "diff --git a/scripts/evil.py b/scripts/evil.py\nnew file mode 100755\nindex 0000000..e69de29\n"
    verdict = _verdict(empty)
    assert not verdict.scope_valid
    assert "scripts/evil.py" in " ".join(verdict.reasons)


def test_deleting_a_workflow_is_rejected() -> None:
    diff = (
        f"diff --git a/{CI} b/{CI}\ndeleted file mode 100644\nindex 1111111..0000000\n"
        f"--- a/{CI}\n+++ /dev/null\n@@ -1 +0,0 @@\n-name: ci\n"
    )
    verdict = _verdict(diff, baseline={CI: "name: ci\n"})
    assert not verdict.scope_valid
    assert any("deletes the workflow file" in item for item in verdict.change_set.workflow_edit_violations)


# --- the route cannot write anywhere else --------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/steward-build-pi.lock.yml",
        ".github/workflows/shared/steward-agent.yml",
        ".github/workflows/_disabled/old.yml",
        ".github/workflows/ci.yaml",
        ".github/actions/setup/action.yml",
        ".github/CODEOWNERS",
        ".github/ISSUE_TEMPLATE/new_skill_intake.yml",
        "docs/.github/workflows/ci.yml",
        "scripts/.github/workflows/ci.yml",
        "registry/nodes/x.json",
        "founder/steward/POLICY.yaml",
    ],
)
def test_the_route_cannot_write_anywhere_else(path: str) -> None:
    verdict = _verdict(_patch(path, "a: 1\n", "a: 1\nb: 2\n"), baseline={path: "a: 1\n"})
    assert not verdict.scope_valid
    assert verdict.verdict == "reject"


def _other_rule_packet(rule_id: str) -> DispatchPacket:
    rule = StewardPolicy.load(REPO_ROOT).dispatch_rules[rule_id]
    return DispatchPacket.create(
        debt={"id": f"debt:{rule.debt_kind}:x", "kind": rule.debt_kind},
        evidence={},
        authority=AuthorityClass.B,
        rule=rule.id,
        routine=rule.routine,
        objective=rule.objective,
        allowed_paths=rule.allowed_paths,
        allowed_commands=rule.allowed_commands,
        forbidden_paths=rule.forbidden_paths,
        stop_conditions=rule.stop_conditions,
        proof=rule.proof,
        budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0),
        capability=rule.capability,
    )


@pytest.mark.parametrize(
    "rule_id",
    sorted(
        rule.id
        for rule in StewardPolicy.load(REPO_ROOT).dispatch_rules.values()
        if rule.debt_kind != "workflow_hygiene"
    ),
)
def test_every_other_rules_packet_rejects_a_workflow_write(rule_id: str) -> None:
    packet = _other_rule_packet(rule_id)
    for path in (CI, ".github/workflows/steward-build-pi.lock.yml"):
        verdict = _verdict(_patch(path, BEFORE, _timed(BEFORE)), packet, baseline={path: BEFORE})
        assert not verdict.scope_valid, (rule_id, path)
        assert verdict.verdict == "reject", (rule_id, path)


# --- the sensor keeps non-routable debt out of the lane ---------------------------------------


WORKFLOW_NO_TIMEOUT = "name: ci\non: push\npermissions:\n  contents: read\njobs:\n  build:\n    runs-on: ubuntu-latest\n"


def test_non_routable_workflow_debt_stays_visible_but_never_takes_a_lane_slot(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "repo",
        {
            ".github/workflows/ci.yml": WORKFLOW_NO_TIMEOUT,
            f".github/workflows/steward-build-pi{LOCK_SUFFIX}": WORKFLOW_NO_TIMEOUT,
            ".github/workflows/compiled.yml": "# This file was automatically generated by gh-aw. DO NOT EDIT.\n"
            + WORKFLOW_NO_TIMEOUT,
            ".github/workflows/legacy.yaml": WORKFLOW_NO_TIMEOUT,
            ".github/workflows/mixed.yml": WORKFLOW_NO_TIMEOUT.replace("contents: read", "write-all").replace(
                "permissions:\n  write-all", "permissions: write-all"
            ),
        },
    )
    by_id = {o.subject.id: o for o in CiWorkflowSensor().scan(root, NOW)}
    assert "laneEligible" not in by_id[".github/workflows/ci.yml"].observed_state
    for ineligible in (
        f".github/workflows/steward-build-pi{LOCK_SUFFIX}",
        ".github/workflows/compiled.yml",
        ".github/workflows/legacy.yaml",
        ".github/workflows/mixed.yml",
    ):
        state = by_id[ineligible].observed_state
        assert state["laneEligible"] is False, ineligible
        assert state["laneIneligibleReason"], ineligible


def test_the_routine_guide_says_findings_are_configuration_not_runtime_timeouts() -> None:
    guide = (REPO_ROOT / _live_rule().prompt_guide).read_text(encoding="utf-8")
    assert "configuration" in guide
    assert "does **not** say the job ever hung" in guide
    assert "never merges its own change" in guide
    assert ".lock.yml" in guide


def test_unavailable_run_history_is_an_unconditional_stop() -> None:
    """Unreadable history has no fallback of any kind.

    The no-history default (decision steward-workflow-timeout-no-history-2283)
    applies only when history WAS read and holds no successful run of the job;
    it never stands in for history that could not be read.
    """

    rule = _live_rule()
    joined = " ".join(rule.stop_conditions).lower()
    assert "history cannot be read" in joined
    assert "do not bound" not in joined and "semantics do not" not in joined
    guide = (REPO_ROOT / rule.prompt_guide).read_text(encoding="utf-8")
    assert "there is no semantics-only fallback for unreadable history" in guide
    assert "History was read and the job has no successful run in it" in guide
    assert "does not bound" not in guide


# --- primary gate: byte preservation ----------------------------------------------------------

REF_BEFORE = """\
name: ci
on:
  pull_request:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      MODE: on
      N: 012
    steps:
      - uses: actions/checkout@v4
        with:
          ref: on
      - run: |
          echo safe
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    steps:
      - run: echo lint
"""


def _rewrite(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        # YAML-equal rewrites a loader cannot tell apart; GitHub Actions can (the reviewer's example first).
        ("checkout ref on -> yes", lambda t: _rewrite(t, "          ref: on\n", "          ref: yes\n")),
        ("env value on -> yes", lambda t: _rewrite(t, "      MODE: on\n", "      MODE: yes\n")),
        ("env value 012 -> 10", lambda t: _rewrite(t, "      N: 012\n", "      N: 10\n")),
        ("env value 012 -> 0o12", lambda t: _rewrite(t, "      N: 012\n", "      N: 0o12\n")),
        ("env value 12 -> 0xC", lambda t: _rewrite(_rewrite(t, "N: 012", "N: 12"), "N: 12", "N: 0xC")),
        ("root trigger key on -> yes", lambda t: _rewrite(t, "\non:\n", "\nyes:\n")),
        ("quoted vs unquoted value", lambda t: _rewrite(t, "    runs-on: ubuntu-latest\n    timeout-minutes: 15\n", '    runs-on: "ubuntu-latest"\n    timeout-minutes: 15\n')),
        ("unquoting a quoted value", lambda t: _rewrite(t, "      MODE: on\n", "      MODE: 'on'\n")),
        # Byte-level changes with no YAML meaning at all.
        ("whitespace-only change (trailing space)", lambda t: _rewrite(t, "name: ci\n", "name: ci \n")),
        ("whitespace-only change (indent of a continuation)", lambda t: _rewrite(t, "          echo safe\n", "           echo safe\n")),
        ("comment change", lambda t: "# new comment\n" + t),
        ("existing comment rewritten", lambda t: _rewrite(t, "name: ci\n", "name: ci # why\n")),
        ("trailing newline removed", lambda t: t.rstrip("\n")),
        ("extra trailing blank line", lambda t: t + "\n"),
        ("CRLF conversion", lambda t: t.replace("\n", "\r\n")),
        ("BOM added", lambda t: "\ufeff" + t),
    ],
)
def test_the_byte_gate_rejects_any_change_to_existing_bytes_even_beside_a_real_timeout(label: str, mutate) -> None:
    """Each patch also adds a proper job timeout, so only the rewrite can be what rejects it."""

    after = mutate(_timed(REF_BEFORE))
    verdict = _structural(REF_BEFORE, after)
    assert not verdict.scope_valid, label
    assert verdict.verdict == "reject", label


def test_the_reviewers_checkout_ref_patch_is_rejected_with_an_explicit_reason() -> None:
    after = _rewrite(_timed(REF_BEFORE), "          ref: on\n", "          ref: yes\n")
    verdict = _structural(REF_BEFORE, after)
    assert not verdict.scope_valid
    assert any("removes or rewrites an existing line" in item for item in verdict.reasons)


def _insert_after(text: str, anchor: str, line: str) -> str:
    assert text.count(anchor) == 1, anchor
    return text.replace(anchor, anchor + line + "\n", 1)


BUILD_RUNS_ON = "  build:\n    runs-on: ubuntu-latest\n"


@pytest.mark.parametrize(
    "line",
    [
        "    timeout-minutes: 15 # why",
        "    timeout-minutes: 15 ",
        "    timeout-minutes: 15\t",
        "    timeout-minutes:  15",
        "    timeout-minutes: '15'",
        '    timeout-minutes: "15"',
        "    timeout-minutes: 015",
        "    timeout-minutes: 0",
        "    timeout-minutes: 361",
        "    timeout-minutes: 1000",
        "    timeout-minutes: ١٥",
        "    timeout-minutes: 0xF",
        "    timeout-minutes: 15.0",
        "    Timeout-minutes: 15",
        "    timeout-minutes : 15",
        "\ttimeout-minutes: 15",
        "timeout-minutes: 15",
        "    - timeout-minutes: 15",
        "    # timeout-minutes: 15",
        "",
    ],
)
def test_every_inserted_line_must_match_the_exact_timeout_pattern(line: str) -> None:
    verdict = _structural(REF_BEFORE, _insert_after(REF_BEFORE, BUILD_RUNS_ON, line))
    assert not verdict.scope_valid, repr(line)


@pytest.mark.parametrize("value", ["1", "9", "10", "99", "100", "299", "300", "359", "360"])
def test_every_integer_from_one_to_360_is_an_accepted_value(value: str) -> None:
    verdict = _structural(REF_BEFORE, _timed(REF_BEFORE, value=value))
    assert verdict.scope_valid, (value, verdict.reasons)


@pytest.mark.parametrize(
    ("label", "anchor", "line"),
    [
        ("under env (a nested mapping)", "    env:\n", "      timeout-minutes: 15"),
        ("inside a block scalar", "          echo safe\n", "          timeout-minutes: 15"),
        ("under the last step of a job", "    steps:\n      - run: echo lint\n", "        timeout-minutes: 15"),
        ("under a step", "      - uses: actions/checkout@v4\n", "        timeout-minutes: 15"),
        ("under with", "        with:\n", "          timeout-minutes: 15"),
        ("job indentation too deep", BUILD_RUNS_ON, "     timeout-minutes: 15"),
        ("job indentation too shallow", BUILD_RUNS_ON, "   timeout-minutes: 15"),
        ("root level", "name: ci\n", "timeout-minutes: 15"),
        ("under permissions", "permissions:\n", "  timeout-minutes: 15"),
        ("under on", "on:\n", "  timeout-minutes: 15"),
        ("a job that already has one", "    timeout-minutes: 360\n", "    timeout-minutes: 15"),
    ],
)
def test_an_inserted_timeout_must_sit_directly_in_a_job_mapping_block(label: str, anchor: str, line: str) -> None:
    verdict = _structural(REF_BEFORE, _insert_after(REF_BEFORE, anchor, line))
    assert not verdict.scope_valid, label


def test_a_job_may_receive_at_most_one_inserted_line() -> None:
    after = _insert_after(_timed(REF_BEFORE), BUILD_RUNS_ON + "    timeout-minutes: 15\n", "    timeout-minutes: 20")
    verdict = _structural(REF_BEFORE, after)
    assert not verdict.scope_valid


def test_a_flow_mapping_job_cannot_take_an_inserted_line() -> None:
    before = "name: ci\non: push\njobs:\n  build: {runs-on: x}\n"
    after = before.replace("  build: {runs-on: x}\n", "  build: {runs-on: x}\n    timeout-minutes: 15\n")
    assert not _structural(before, after).scope_valid


def test_insertion_at_the_end_of_a_job_before_the_next_job_is_accepted() -> None:
    before = "name: ci\non: push\njobs:\n  a:\n    runs-on: x\n  b:\n    runs-on: y\n"
    after = before.replace("    runs-on: x\n", "    runs-on: x\n    timeout-minutes: 7\n", 1)
    assert _structural(before, after).scope_valid
    final = before + "    timeout-minutes: 9\n"
    assert _structural(before, final).scope_valid  # the last job, at end of file


def test_crlf_baseline_takes_an_lf_inserted_line_and_keeps_every_existing_byte() -> None:
    """The diff is split on LF only, so the CR of CRLF context survives and applies exactly."""

    before = REF_BEFORE.replace("\n", "\r\n")
    after = before.replace("    runs-on: ubuntu-latest\r\n    env:", "    runs-on: ubuntu-latest\r\n    timeout-minutes: 15\n    env:", 1)
    assert after.count("timeout-minutes: 15\n") == 1
    verdict = _structural(before, after)
    assert verdict.scope_valid, verdict.reasons


def test_a_bom_in_the_baseline_is_preserved_not_rewritten() -> None:
    before = "\ufeff" + REF_BEFORE
    assert _structural(before, _timed(before)).scope_valid


def test_the_byte_gate_runs_before_and_independently_of_the_structural_gate() -> None:
    from gaia_cli.steward.workflowproof import byte_gate_problems, prove_workflow_edit

    rewrite = parse_unified_diff(_patch(CI, REF_BEFORE, _rewrite(REF_BEFORE, "ref: on", "ref: yes"))).workflow_patches[0][1]
    assert any("rewrites an existing line" in item for item in byte_gate_problems(rewrite))
    assert prove_workflow_edit(REF_BEFORE, rewrite)
    clean = parse_unified_diff(_patch(CI, REF_BEFORE, _timed(REF_BEFORE))).workflow_patches[0][1]
    assert byte_gate_problems(clean) == []
    assert prove_workflow_edit(REF_BEFORE, clean) == []
