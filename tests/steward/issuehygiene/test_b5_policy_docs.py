"""Lane B5: policy rollout (B5), sensor honesty with writes off (L6), census-missing wording (D11),
coverage checker call-site precision (D12) and documentation that matches the code (D5, D13, L7, B4 skill text).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.issuehygiene.hygienepolicy import loadHygienePolicy
from gaia_cli.steward.issuehygiene.sensor import IssueHygieneSensor
from gaia_cli.steward.primitives import SensorNotEvaluated
from scripts.check_steward_coverage import _live_forge_actions
from tests.steward.issuehygiene.test_d1_sensor import (
    NOW_TEXT,
    byKind,
    makeCensus,
    makeItem,
    makeManifest,
    makeRow,
    scanOf,
    stubReconcile,
    writeCensus,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = REPO_ROOT / "founder" / "steward" / "POLICY.yaml"


def writesFixture(tmp_path: Path, writes: bool) -> Path:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "founder" / "steward").mkdir(parents=True)
    raw = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    raw["issueHygiene"]["writesEnabled"] = writes
    (tmp_path / "founder" / "steward" / "POLICY.yaml").write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------- B5: the shipped policy does not write


def test_the_repo_policy_ships_with_closure_writes_disabled() -> None:
    raw = yaml.safe_load(POLICY.read_text(encoding="utf-8"))

    policy = loadHygienePolicy(raw["issueHygiene"])

    assert raw["issueHygiene"]["writesEnabled"] is False
    assert policy.writesEnabled is False


def test_the_repo_policy_still_enables_the_five_rules_for_the_pilot() -> None:
    policy = loadHygienePolicy(yaml.safe_load(POLICY.read_text(encoding="utf-8"))["issueHygiene"])

    assert policy.enabledRules == (
        "A1-child-curated", "A2-umbrella-synced", "A3-umbrella-superseded", "A4-duplicate-child", "A5-botreport-superseded",
    )
    assert policy.maxClosuresPerRun == 10


# ---------------------------------------------------------------- L6: writes disabled reports, never emits


def test_writes_disabled_reports_closure_debt_as_ready_with_no_emit_able_plan(tmp_path: Path, monkeypatch) -> None:
    root = writesFixture(tmp_path, writes=False)
    writeCensus(root, makeCensus([makeRow(10, "[intake] alpha")]))
    items = [makeItem(10, "upstream-candidate:o/r:alpha", "A", ruleId="A1-child-curated",
                      evidence=[{"type": "registry", "ref": "registry/named/o/alpha.md", "sha256": "a" * 64, "detail": "exact"}])]
    stubReconcile(monkeypatch, makeManifest(items))

    observed = byKind(scanOf(root).observations, "issue_closure_ready")
    rule = next(o for o in observed if o.subject.id == "A1-child-curated")

    assert rule.observed_state["count"] == 1
    assert rule.observed_state["plans"] == []
    assert rule.observed_state["writesEnabled"] is False
    assert rule.observed_state["status"] == "ready (writes disabled)"


def test_writes_enabled_still_presents_the_plan(tmp_path: Path, monkeypatch) -> None:
    root = writesFixture(tmp_path, writes=True)
    writeCensus(root, makeCensus([makeRow(10, "[intake] alpha")]))
    items = [makeItem(10, "upstream-candidate:o/r:alpha", "A", ruleId="A1-child-curated",
                      evidence=[{"type": "registry", "ref": "registry/named/o/alpha.md", "sha256": "a" * 64, "detail": "exact"}])]
    stubReconcile(monkeypatch, makeManifest(items))

    rule = next(o for o in byKind(scanOf(root).observations, "issue_closure_ready") if o.subject.id == "A1-child-curated")

    assert rule.observed_state["count"] == 1
    assert len(rule.observed_state["plans"]) == 1
    assert rule.observed_state.get("status") is None or rule.observed_state["status"] != "ready (writes disabled)"


def test_a_missing_census_is_not_evaluated_and_never_a_closure(tmp_path: Path) -> None:
    root = writesFixture(tmp_path, writes=True)

    with pytest.raises(SensorNotEvaluated):
        IssueHygieneSensor().scan_detailed(root, NOW_TEXT)


# ---------------------------------------------------------------- D12: coverage checker reads the emitting call


def emitsOnly(tmp_path: Path, body: str) -> dict:
    (tmp_path / "src" / "gaia_cli" / "steward").mkdir(parents=True)
    (tmp_path / "src" / "gaia_cli" / "steward" / "fullrun.py").write_text(body, encoding="utf-8")
    return _live_forge_actions(tmp_path)


def test_a_literal_that_is_never_emitted_is_not_live(tmp_path: Path) -> None:
    body = 'CLOSEACTION = "forge.close_issue"\n\ndef other(self):\n    print("forge.close_issue documented")\n'

    assert "forge.close_issue" not in emitsOnly(tmp_path, body)


def test_the_addaction_call_site_makes_the_forge_action_live(tmp_path: Path) -> None:
    body = (
        'CLOSEACTION = "forge.close_issue"\n\n'
        "class Runner:\n"
        "    def apply(self, record, stepId, debtId, key, params, now):\n"
        "        self._addAction(record, stepId, CLOSEACTION, debtId, key, params, now)\n"
    )

    assert "forge.close_issue" in emitsOnly(tmp_path, body)


def test_a_constant_passed_to_addaction_under_another_name_is_live(tmp_path: Path) -> None:
    body = (
        'ALIAS = "forge.close_issue"\n\n'
        "class Runner:\n"
        "    def apply(self, record, stepId, debtId, key, params, now):\n"
        "        self._addAction(record, stepId, ALIAS, debtId, key, params, now)\n"
    )

    assert "forge.close_issue" in emitsOnly(tmp_path, body)


def test_a_literal_in_a_different_addaction_argument_is_not_live(tmp_path: Path) -> None:
    body = (
        'WRONG = "forge.close_issue"\n\n'
        "class Runner:\n"
        "    def apply(self, record, stepId, debtId, key, params, now):\n"
        "        self._addAction(record, stepId, 'agent.build', debtId, WRONG, params, now)\n"
    )

    assert "forge.close_issue" not in emitsOnly(tmp_path, body)


# ---------------------------------------------------------------- D5 and D13: docs state the real values


def maxInFlightOf(path: Path) -> list[str]:
    return re.findall(r"maxInFlight\W+(\d+)", path.read_text(encoding="utf-8"))


def test_documented_class_b_max_in_flight_matches_the_policy_value() -> None:
    raw = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    actual = {str(value) for value in _maxInFlightValues(raw)}
    assert actual, "POLICY.yaml must name a maxInFlight value"

    for relative in (
        "founder/steward/README.md",
        ".agents/skills/gaia-steward-full/SKILL.md",
        ".claude/skills/gaia-steward-full/SKILL.md",
    ):
        stated = maxInFlightOf(REPO_ROOT / relative)
        assert stated, relative
        assert set(stated) <= actual, f"{relative} states maxInFlight {stated}, POLICY says {sorted(actual)}"


def _maxInFlightValues(node) -> list:
    found: list = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "maxInFlight":
                found.append(value)
            else:
                found.extend(_maxInFlightValues(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_maxInFlightValues(value))
    return found


SKILL_PATHS = (
    ".agents/skills/gaia-steward-issue-hygiene/SKILL.md",
    ".claude/skills/gaia-steward-issue-hygiene/SKILL.md",
)


@pytest.mark.parametrize("relative", SKILL_PATHS)
def test_the_issue_hygiene_skill_does_not_trust_the_executor_blindly(relative: str) -> None:
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")

    assert "trusted blindly" not in text
    assert "writesEnabled" in text
    assert "enabledRules" in text
    assert "manifest" in text.lower()


@pytest.mark.parametrize("relative", SKILL_PATHS)
def test_the_issue_hygiene_skill_documents_the_exit_codes(relative: str) -> None:
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")

    for code in ("0", "1", "2", "3"):
        assert re.search(rf"\b{code}\b\s*[—:-]", text), f"exit code {code} is not documented in {relative}"


def test_the_issue_hygiene_skill_mirrors_are_byte_identical() -> None:
    canonical = (REPO_ROOT / SKILL_PATHS[0]).read_bytes()
    mirror = (REPO_ROOT / SKILL_PATHS[1]).read_bytes()

    assert canonical == mirror


def test_the_contract_states_a_missing_census_is_not_evaluated_as_the_code_does() -> None:
    contract = (REPO_ROOT / "founder/handovers/2026-10-21-steward-issue-hygiene-architecture.md").read_text(encoding="utf-8")

    assert "notEvaluated" in contract
    assert "no closure emitted" in contract or "no closure is emitted" in contract


def test_the_closure_proof_is_described_as_exactly_one_proof() -> None:
    for relative in ("founder/steward/README.md", ".agents/skills/gaia-steward-issue-hygiene/SKILL.md"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        if "commentUrl" in text:
            assert "exactly one" in text, relative
