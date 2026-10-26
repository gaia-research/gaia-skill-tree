"""Regression tests for safe GitHub Actions dispatch-input handling."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/upstream-watcher.yml"


def _workflow():
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _run_block():
    workflow = _workflow()
    return workflow["jobs"]["watcher"]["steps"][-1]["run"]


def test_dispatch_inputs_are_process_environment_not_run_interpolation():
    workflow = _workflow()
    step = workflow["jobs"]["watcher"]["steps"][-1]

    assert step["env"]["ACTION_SKILL_ID"] == "${{ inputs.skill_id }}"
    assert step["env"]["ACTION_APPLY"] == "${{ inputs.apply }}"
    assert step["env"]["ACTION_CHALLENGE_WATCH"] == "${{ inputs.challenge_watch }}"
    assert step["env"]["ACTION_CHALLENGE_INPUT"] == "${{ inputs.challenge_input }}"
    assert step["env"]["ACTION_CHALLENGE_SHADOW"] == "${{ inputs.challenge_shadow }}"
    assert "${{" not in step["run"]
    assert "ARGS=()" in step["run"]
    assert '"${ARGS[@]}"' in step["run"]
    assert "eval " not in step["run"]


def test_workflow_preserves_schedule_and_default_off_gates():
    workflow = _workflow()
    assert workflow["on"]["schedule"] == [{"cron": "0 6 * * *"}]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["challenge_watch"]["default"] == "false"
    assert workflow["jobs"]["watcher"]["steps"][-1]["env"]["GAIA_CHALLENGE_WATCH_ENABLED"] == "${{ vars.GAIA_CHALLENGE_WATCH_ENABLED }}"


def test_scheduled_run_keeps_apply_behavior_without_enabling_challenge_watch(tmp_path):
    bash = shutil.which("bash")
    assert bash is not None, "bash is required to exercise the workflow's shell argv handling"

    probe = tmp_path / "argv_probe.py"
    result_file = tmp_path / "argv.json"
    probe.write_text(
        "import json, os, sys\n"
        "open(os.environ['ARGV_RESULT'], 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    run = _run_block()
    final_command = 'python scripts/upstream_watcher/watcher.py "${ARGS[@]}"'
    assert run.rstrip().endswith(final_command)
    run = run.rstrip()[: -len(final_command)] + 'python "$ARGV_PROBE" "${ARGS[@]}"\n'
    env = {
        **os.environ,
        "ACTION_SKILL_ID": "",
        "ACTION_APPLY": "false",
        "ACTION_CHALLENGE_WATCH": "false",
        "ACTION_CHALLENGE_INPUT": "",
        "ACTION_CHALLENGE_SHADOW": "false",
        "GAIA_CHALLENGE_WATCH_ENABLED": "false",
        "GITHUB_EVENT_NAME": "schedule",
        "ARGV_PROBE": str(probe),
        "ARGV_RESULT": str(result_file),
    }
    subprocess.run([bash, "-e", "-c", run], env=env, check=True, capture_output=True, text=True)
    assert json.loads(result_file.read_text(encoding="utf-8")) == ["--apply"]


def test_malicious_dispatch_values_remain_exact_argv_and_do_not_execute(tmp_path):
    bash = shutil.which("bash")
    assert bash is not None, "bash is required to exercise the workflow's shell argv handling"

    marker = tmp_path / "INJECTION_RAN"
    skill_id = f"skill with spaces; touch {marker}; # $(touch {marker})"
    challenge_input = f"challenge path with spaces; touch {marker}; # `touch {marker}`"
    probe = tmp_path / "argv_probe.py"
    result_file = tmp_path / "argv.json"
    probe.write_text(
        "import json, os, sys\n"
        "open(os.environ['ARGV_RESULT'], 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )

    run = _run_block()
    # Keep the actual workflow array-building logic; replace only its final
    # application invocation with a local argv recorder (no network/actions).
    final_command = 'python scripts/upstream_watcher/watcher.py "${ARGS[@]}"'
    assert run.rstrip().endswith(final_command)
    run = run.rstrip()[: -len(final_command)] + 'python "$ARGV_PROBE" "${ARGS[@]}"\n'

    env = {
        **os.environ,
        "ACTION_SKILL_ID": skill_id,
        "ACTION_APPLY": "false",
        "ACTION_CHALLENGE_WATCH": "true",
        "ACTION_CHALLENGE_INPUT": challenge_input,
        "ACTION_CHALLENGE_SHADOW": "true",
        "GAIA_CHALLENGE_WATCH_ENABLED": "false",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "ARGV_PROBE": str(probe),
        "ARGV_RESULT": str(result_file),
    }
    subprocess.run([bash, "-e", "-c", run], env=env, check=True, capture_output=True, text=True)

    assert not marker.exists(), "untrusted dispatch input executed shell commands"
    assert json.loads(result_file.read_text(encoding="utf-8")) == [
        "--skill",
        skill_id,
        "--dry-run",
        "--challenge-watch",
        "--challenge-input",
        challenge_input,
        "--challenge-shadow",
    ]
