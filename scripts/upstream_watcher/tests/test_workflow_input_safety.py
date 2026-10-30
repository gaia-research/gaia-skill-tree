"""Regression tests for safe GitHub Actions dispatch-input handling."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/upstream-watcher.yml"


def _workflow():
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _env_with_python(tmp_path, env):
    """The run block calls `python`; hosts that only ship `python3` get a shim so the block runs unchanged."""
    shim = tmp_path / "pybin"
    shim.mkdir(exist_ok=True)
    link = shim / "python"
    if not link.exists():
        link.symlink_to(sys.executable)
    return {**env, "PATH": f"{shim}{os.pathsep}{env.get('PATH', '')}"}


def _step():
    # The run step is no longer last: main appends an "Upload watcher report" step after it.
    steps = _workflow()["jobs"]["watcher"]["steps"]
    return next(step for step in steps if step.get("name") == "Run upstream watcher")


def _run_block():
    return _step()["run"]


def test_dispatch_inputs_are_process_environment_not_run_interpolation():
    step = _step()

    assert step["env"]["INPUT_SKILL_ID"] == "${{ inputs.skill_id }}"
    assert step["env"]["INPUT_APPLY"] == "${{ inputs.apply }}"
    assert step["env"]["INPUT_CHALLENGE_WATCH"] == "${{ inputs.challenge_watch }}"
    assert step["env"]["INPUT_CHALLENGE_INPUT"] == "${{ inputs.challenge_input }}"
    assert step["env"]["INPUT_CHALLENGE_SHADOW"] == "${{ inputs.challenge_shadow }}"
    assert "${{" not in step["run"]
    assert "ARGS=(--child-mode" in step["run"]
    assert '"${ARGS[@]}"' in step["run"]
    assert "eval " not in step["run"]


def test_workflow_preserves_schedule_and_default_off_gates():
    workflow = _workflow()
    assert workflow["on"]["schedule"] == [{"cron": "0 6 * * *"}]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["challenge_watch"]["default"] == "false"
    assert _step()["env"]["GAIA_CHALLENGE_WATCH_ENABLED"] == "${{ vars.GAIA_CHALLENGE_WATCH_ENABLED }}"


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
        "INPUT_SKILL_ID": "",
        "INPUT_ESCALATE": "",
        "INPUT_APPLY": "false",
        "INPUT_CHALLENGE_WATCH": "false",
        "INPUT_CHALLENGE_INPUT": "",
        "INPUT_CHALLENGE_SHADOW": "false",
        "GAIA_CHALLENGE_WATCH_ENABLED": "false",
        "EVENT_NAME": "schedule",
        "ARGV_PROBE": str(probe),
        "ARGV_RESULT": str(result_file),
    }
    subprocess.run([bash, "-e", "-c", run], env=_env_with_python(tmp_path, env), cwd=tmp_path, check=True, capture_output=True, text=True)
    assert json.loads(result_file.read_text(encoding="utf-8")) == [
        "--child-mode",
        "fanout",
        "--apply",
        "--report",
        "generated-output/upstream-watcher-report.json",
    ]


def test_malicious_dispatch_values_remain_exact_argv_and_do_not_execute(tmp_path):
    bash = shutil.which("bash")
    assert bash is not None, "bash is required to exercise the workflow's shell argv handling"

    marker = tmp_path / "INJECTION_RAN"
    # skill_id is validated by the workflow (L1) before use, so only a well-formed id reaches argv; the free-form
    # challenge_input path is the value that must survive as one exact argv element.
    skill_id = "owner/repo"
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
        "INPUT_SKILL_ID": skill_id,
        "INPUT_ESCALATE": "",
        "INPUT_APPLY": "false",
        "INPUT_CHALLENGE_WATCH": "true",
        "INPUT_CHALLENGE_INPUT": challenge_input,
        "INPUT_CHALLENGE_SHADOW": "true",
        "GAIA_CHALLENGE_WATCH_ENABLED": "false",
        "EVENT_NAME": "workflow_dispatch",
        "ARGV_PROBE": str(probe),
        "ARGV_RESULT": str(result_file),
    }
    subprocess.run([bash, "-e", "-c", run], env=_env_with_python(tmp_path, env), cwd=tmp_path, check=True, capture_output=True, text=True)

    assert not marker.exists(), "untrusted dispatch input executed shell commands"
    assert json.loads(result_file.read_text(encoding="utf-8")) == [
        "--child-mode",
        "fanout",
        "--dry-run",
        "--report",
        "generated-output/upstream-watcher-report.json",
        "--skill",
        skill_id,
        "--challenge-watch",
        "--challenge-input",
        challenge_input,
        "--challenge-shadow",
    ]


def test_malformed_skill_id_is_rejected_before_any_command_runs(tmp_path):
    bash = shutil.which("bash")
    assert bash is not None, "bash is required to exercise the workflow's shell argv handling"

    marker = tmp_path / "INJECTION_RAN"
    run = _run_block()
    env = {
        **os.environ,
        "INPUT_SKILL_ID": f"skill with spaces; touch {marker}; # $(touch {marker})",
        "INPUT_ESCALATE": "",
        "INPUT_APPLY": "false",
        "INPUT_CHALLENGE_WATCH": "false",
        "INPUT_CHALLENGE_INPUT": "",
        "INPUT_CHALLENGE_SHADOW": "false",
        "GAIA_CHALLENGE_WATCH_ENABLED": "false",
        "EVENT_NAME": "workflow_dispatch",
    }
    result = subprocess.run([bash, "-e", "-c", run], env=env, cwd=tmp_path, capture_output=True, text=True)

    assert result.returncode != 0
    assert "skill_id must match" in result.stdout + result.stderr
    assert not marker.exists(), "untrusted dispatch input executed shell commands"
