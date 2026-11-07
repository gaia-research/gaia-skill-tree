"""Offline C4 proof. Source hardening is not a compiled/deployed workflow claim."""
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / ".github/workflows/shared/steward-agent.md"


def source():
    return yaml.safe_load(SHARED.read_text().split("---", 2)[1])


def test_source_requires_enabled_strict_threat_detection():
    assert source()["safe-outputs"]["threat-detection"] == {"enabled": True, "continue-on-error": False}


@pytest.mark.parametrize("engine", ("claude", "codex", "copilot", "pi"))
@pytest.mark.parametrize("role", ("build", "verify"))
def test_existing_compiled_agents_remain_manual_only_and_paused(engine, role):
    path = ROOT / f".github/workflows/steward-{role}-{engine}.lock.yml"
    lock = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
    assert set(lock["on"]) == {"workflow_dispatch"}
    # The founder pause now comes from the source (generator FOUNDERPAUSE, top-level
    # `if: ${{ false }}`), which gh-aw v0.92.6 compiles to `if: false` on activation.
    assert lock["jobs"]["activation"]["if"] == "false"
    assert "detection" in lock["jobs"]
    assert "needs.activation" in lock["jobs"]["agent"]["if"]


@pytest.mark.parametrize("run,conclusion,reason,allowed", [
    ("true", "success", "", True),
    ("true", "warning", "agent_failure", False),
    ("true", "warning", "parse_error", False),
    ("true", "failure", "threat_detected", False),
    ("true", "success", "unknown", False),
    ("true", "success", None, False),
    ("true", "unknown", "", False),
    ("true", "", "", False),
    ("false", "skipped", "", False),
    ("", "success", "", False),
])
def test_outcome_persistence_requires_complete_affirmative_clearance(tmp_path, run, conclusion, reason, allowed):
    data = tmp_path / "agent.json"
    data.write_text(json.dumps({"items": [{"type": "steward_outcome", "outcome": '{"summary":"synthetic"}'}]}))
    step = source()["safe-outputs"]["jobs"]["steward-outcome"]["steps"][0]
    env = {**os.environ, "GH_AW_RUN_DETECTION": run, "GH_AW_DETECTION_CONCLUSION": conclusion,
           "GH_AW_AGENT_OUTPUT": str(data)}
    env.pop("GH_AW_DETECTION_REASON", None)
    if reason is not None:
        env["GH_AW_DETECTION_REASON"] = reason
    result = subprocess.run(["bash", "-c", step["run"]], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert (result.returncode == 0) == allowed, result.stderr
    assert (tmp_path / "steward-outcome/outcome.json").exists() == allowed


@pytest.mark.parametrize("engine", ("claude", "codex", "copilot", "pi"))
@pytest.mark.parametrize("role", ("build", "verify"))
def test_the_founder_pause_lives_in_the_source_so_a_recompile_keeps_it(engine, role):
    wrapper = ROOT / f".github/workflows/steward-{role}-{engine}.md"
    front = yaml.safe_load(wrapper.read_text().split("---", 2)[1])
    assert front["if"] == "${{ false }}"
    assert "Founder pause (FOUNDER_LOCK_2283 C4)" in wrapper.read_text()


@pytest.mark.parametrize("engine", ("claude", "codex", "copilot", "pi"))
@pytest.mark.parametrize("role", ("build", "verify"))
def test_compiled_locks_carry_the_c4_strict_detection(engine, role):
    text = (ROOT / f".github/workflows/steward-{role}-{engine}.lock.yml").read_text()
    assert 'GH_AW_DETECTION_CONTINUE_ON_ERROR: "true"' not in text
    assert 'GH_AW_DETECTION_CONTINUE_ON_ERROR: "false"' in text
    assert 'test -z "$GH_AW_DETECTION_REASON"' in text
