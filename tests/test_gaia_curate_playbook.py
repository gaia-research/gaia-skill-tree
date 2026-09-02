"""Contract and fixture tests for the consolidated Gaia discovery playbook."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import check_playbook_contract


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "gaia-curate"


def test_trigger_corpus_has_valid_schema_and_route_coverage():
    suite = json.loads((SKILL / "evals" / "triggering.json").read_text(encoding="utf-8"))
    assert suite["schemaVersion"] == "gaia-playbook-triggering-v1"
    assert suite["skill"] == "gaia-curate"
    assert suite["contractRef"] == "founder/steward/PLAYBOOKS.md"

    cases = suite["cases"]
    assert len(cases) >= 8
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["expected"]["mode"] for case in cases if case["expected"]["activate"]} == {
        "single",
        "checkpointed",
        "dynamic",
        "trending",
    }
    assert any(not case["expected"]["activate"] for case in cases)

    for case in cases:
        assert len(case["prompt"].split()) >= 8
        assert set(case) == {"id", "prompt", "signals", "expected"}
        assert set(case["signals"]) == {
            "scope",
            "sourceKind",
            "trending",
            "parallel",
            "recoverable",
        }
        assert set(case["expected"]) == {"activate", "route", "mode"}
        if case["expected"]["activate"]:
            assert case["signals"]["scope"] == "discovery"
            assert case["expected"]["route"] == "gaia-curate"
            assert case["expected"]["mode"] in {
                "single",
                "checkpointed",
                "dynamic",
                "trending",
            }
        else:
            assert case["signals"]["scope"] != "discovery"
            assert case["expected"]["route"] != "gaia-curate"
            assert case["expected"]["mode"] is None


def test_forward_results_separate_observed_floor_from_unproven_dynamic_flow():
    results = json.loads(
        (SKILL / "evals" / "forward-selection-results.json").read_text(encoding="utf-8")
    )
    assert results["schemaVersion"] == "gaia-playbook-forward-selection-results-v1"
    assert results["evaluatedOn"] == "2026-09-02"
    assert results["catalogSkillCount"] == 5
    assert results["reasoner"] == {
        "model": "gpt-5.6-luna",
        "reasoningEffort": "low",
    }

    trials = results["trials"]
    assert len(trials) == 4
    assert len({trial["id"] for trial in trials}) == len(trials)
    for trial in trials:
        assert trial["selectedSkill"] == "gaia-curate"
        assert trial["selectedMode"] == trial["requestMode"]
        assert trial["exitStatus"] == 0
        assert trial["snapshotInvocations"] == 1
        assert trial["prefillInvocations"] == 1
        assert trial["decision"] == "MAP"
        assert trial["decisionReasonCode"] == "MAP_EXISTING_GENERIC"
        assert trial["genericId"] == "example-capability"
        assert trial["validator"] == "VALID discovery-packet-v2"
        assert trial["registryUnchanged"] is True
        assert trial["l4BoundaryPreserved"] is True
        assert "usage" not in trial
        assert "cost" not in trial

    selection_only = results["selectionOnlyTrials"]
    assert len(selection_only) == 6
    assert all(trial["selectionPassed"] is True for trial in selection_only)
    assert all(trial["scope"] == "selection-only" for trial in selection_only)
    assert all(trial["fixtureExecuted"] is False for trial in selection_only)
    assert all("exitStatus" not in trial for trial in selection_only)
    assert all("usage" not in trial and "cost" not in trial for trial in selection_only)
    assert {
        (trial["request"], trial["selectedSkill"], trial["selectedMode"])
        for trial in selection_only
    } == {
        ("checkpointed discovery", "gaia-curate", "checkpointed"),
        ("trending discovery", "gaia-curate", "trending"),
        ("pending intake", "gaia-draft-curate", None),
        ("bot crawler branch", "gaia-bot-curate", None),
        ("paused INITIALIZED ledger", "gaia-quick-curate", None),
        ("full discovery-through-closed-intake", "gaia-full-pipeline", None),
    }

    single_trials = [trial for trial in trials if trial["requestMode"] == "single"]
    dynamic_trials = [trial for trial in trials if trial["requestMode"] == "dynamic"]
    single = results["conclusions"]["single"]
    dynamic = results["conclusions"]["dynamic"]
    positive = results["conclusions"]["positiveModeSelection"]
    negative = results["conclusions"]["negativeRouting"]
    assert len(single_trials) == single["selectionPasses"] == single["fixturePasses"] == 2
    assert single["totalTrials"] == 2
    assert "not proof of a globally weakest model" in single["observedFloor"]["claim"]
    assert all(trial["instructionAmbiguity"] is None for trial in single_trials)

    assert len(dynamic_trials) == dynamic["selectionPasses"] == dynamic["sharedSpinePasses"] == 2
    assert dynamic["totalTrials"] == 2
    assert dynamic["endToEndStatus"] == "unproven"
    assert dynamic["trackingIssue"].endswith("/issues/1691")
    assert all(trial["fixtureScope"] == "shared-spine-only" for trial in dynamic_trials)
    assert all(trial["instructionAmbiguity"] for trial in dynamic_trials)
    assert set(dynamic["unprovenComponents"]) == {
        "12-way capacity and fan-out",
        "per-attempt usage receipts",
        "budget exhaustion",
        "resume",
    }
    assert positive["passesByMode"] == {
        "single": 2,
        "dynamic": 2,
        "checkpointed": 1,
        "trending": 1,
    }
    assert positive["totalPasses"] == 6
    assert negative["avoidedGaiaCurate"] == negative["totalTrials"] == 4


def test_repository_has_exactly_one_machine_valid_playbook():
    scanned, opted_in, errors = check_playbook_contract.validate_repository(ROOT)
    assert errors == []
    assert opted_in == 1
    assert scanned == 62
    assert scanned == len(list((ROOT / ".agents" / "skills").glob("*/SKILL.md")))


def test_fixture_payload_is_not_discoverable_as_a_project_skill():
    discovered = sorted((SKILL / "fixtures").glob("**/SKILL.md"))

    assert discovered == []
    assert (
        SKILL
        / "fixtures"
        / "playbook-runtime"
        / "source"
        / "UPSTREAM_SKILL.md"
    ).is_file()


def test_retired_discovery_skills_have_no_live_agent_references():
    retired = ("gaia-curate-chain", "gaia-curate-dynamic", "gaia-curate-trending")
    for tree in (ROOT / ".agents" / "skills", ROOT / ".claude" / "skills"):
        for name in retired:
            assert not (tree / name).exists()

    live_entrypoints = [
        ROOT / "AGENTS.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "DEV.md",
        ROOT / "README.md",
        ROOT / "docs" / "agent.md",
        ROOT / "docs" / "en" / "contributing.html",
        ROOT / "docs" / "en" / "index.html",
        ROOT / "founder" / "steward" / "PLAYBOOKS.md",
        *(ROOT / ".agents" / "skills").glob("**/*.md"),
        *(ROOT / ".claude" / "skills").glob("**/*.md"),
    ]
    for path in live_entrypoints:
        content = path.read_text(encoding="utf-8")
        for name in retired:
            assert name not in content, f"retired entrypoint {name!r} remains in {path}"


def test_agent_pipeline_preserves_the_human_merge_gate():
    pipeline = (
        ROOT / ".agents" / "skills" / "gaia-full-pipeline" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "gh pr merge" not in pipeline
    assert "final integration-to-`main` merge is the founder's decision" in pipeline


def test_fixture_dry_run_exercises_live_spine_to_l4(tmp_path: Path):
    output = tmp_path / "fixture-run"
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "run_fixture_dry_run.py"),
            "--output-dir",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["snapshotInvocationCount"] == 1
    assert receipt["prefillInvocationCount"] == 1
    assert receipt["decision"] == {
        "value": "MAP",
        "reasonCode": "MAP_EXISTING_GENERIC",
        "genericId": "example-capability",
    }
    assert receipt["registrySha256Before"] == receipt["registrySha256After"]
    assert receipt["validator"] == "VALID discovery-packet-v2"

    snapshot = json.loads((output / "generic-snapshot.json").read_text(encoding="utf-8"))
    prefill = json.loads((output / "prefill-packet.json").read_text(encoding="utf-8"))
    packet = json.loads((output / "candidate-playbook-001.json").read_text(encoding="utf-8"))
    presentation = (output / "L4-REVIEW.md").read_text(encoding="utf-8")

    assert packet["genericSnapshot"]["generics"] == snapshot
    assert packet["mappingOptions"] == prefill["mappingOptions"]
    assert packet["decision"]["genericId"] == prefill["mappingOptions"][0]["genericId"]
    assert "candidate-playbook-001" in presentation
    assert "MAP_EXISTING_GENERIC" in presentation
    assert "example-capability" in presentation
    assert "1.000000" in presentation
    assert "candidate-playbook-001.json" in presentation


def test_command_spine_adapter_invokes_the_same_validator():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_discovery_packet.py",
            "--generic-snapshot",
            str(SKILL / "fixtures" / "generic-snapshot.json"),
            str(SKILL / "fixtures" / "playbook-l4-packet.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "VALID discovery-packet-v2"
