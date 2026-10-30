"""Regression tests for safe GitHub Actions dispatch-input handling and least-privilege job shape."""

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
WATCHER_STEP = "Run upstream watcher"
CHALLENGE_STEP = "Run challenge watch"
FINAL_COMMAND = 'python scripts/upstream_watcher/watcher.py "${ARGS[@]}"'


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


def _step(job="watcher", name=WATCHER_STEP):
    steps = _workflow()["jobs"][job]["steps"]
    return next(step for step in steps if step.get("name") == name)


def _run_argv(tmp_path, job, name, env, check=True):
    """Run the real run block with only its final watcher invocation swapped for an argv recorder."""
    bash = shutil.which("bash")
    assert bash is not None, "bash is required to exercise the workflow's shell argv handling"
    probe = tmp_path / "argv_probe.py"
    result_file = tmp_path / "argv.json"
    probe.write_text(
        "import json, os, sys\n"
        "open(os.environ['ARGV_RESULT'], 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    run = _step(job, name)["run"]
    assert run.rstrip().endswith(FINAL_COMMAND)
    run = run.rstrip()[: -len(FINAL_COMMAND)] + 'python "$ARGV_PROBE" "${ARGS[@]}"\n'
    full = _env_with_python(tmp_path, {**os.environ, **env, "ARGV_PROBE": str(probe), "ARGV_RESULT": str(result_file)})
    result = subprocess.run([bash, "-e", "-c", run], env=full, cwd=tmp_path, capture_output=True, text=True)
    if check:
        assert result.returncode == 0, result.stderr
    argv = json.loads(result_file.read_text(encoding="utf-8")) if result_file.exists() else None
    return result, argv


WATCHER_ENV = {
    "INPUT_SKILL_ID": "",
    "INPUT_ESCALATE": "",
    "INPUT_APPLY": "false",
    "EVENT_NAME": "workflow_dispatch",
}
CHALLENGE_ENV = {"INPUT_CHALLENGE_INPUT": "", "INPUT_CHALLENGE_SHADOW": "false"}


# --- job shape: least privilege ------------------------------------------------------------------------------


def test_watcher_job_stays_read_only_and_never_runs_challenge_watch():
    workflow = _workflow()
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}
    watcher = workflow["jobs"]["watcher"]
    # No job-level override: the poll/issue job inherits the workflow-level contents: read.
    assert "permissions" not in watcher
    step = _step()
    assert not any(key.startswith("INPUT_CHALLENGE") for key in step["env"])
    assert "GAIA_CHALLENGE_WATCH_ENABLED" not in step["env"], "the env gate would make watcher.py push the ledger itself"
    assert "--challenge" not in step["run"]


def test_only_the_challenge_watch_job_can_write_contents_and_it_is_gated():
    workflow = _workflow()
    writers = [name for name, job in workflow["jobs"].items() if (job.get("permissions") or {}).get("contents") == "write"]
    assert writers == ["challenge-watch"]
    job = workflow["jobs"]["challenge-watch"]
    assert job["permissions"] == {"contents": "write"}
    assert job["needs"] == "watcher"
    condition = job["if"]
    assert "vars.GAIA_CHALLENGE_WATCH_ENABLED == 'true'" in condition
    assert "vars.GAIA_CHALLENGE_WATCH_ENABLED == '1'" in condition
    assert "inputs.challenge_watch == true" in condition
    assert "inputs.escalate_candidate == ''" in condition
    # Only default-branch code ever sees the write token.
    assert "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)" in condition
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"]["ref"] == "${{ github.event.repository.default_branch }}"


def test_challenge_job_hands_data_on_only_as_an_artifact():
    job = _workflow()["jobs"]["challenge-watch"]
    assert "outputs" not in job
    upload = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact"))
    assert upload["with"]["name"] == "challenge-watch-packets"


# --- inputs are environment, never interpolated into the shell -------------------------------------------------


def test_dispatch_inputs_are_process_environment_not_run_interpolation():
    step = _step()
    assert step["env"]["INPUT_SKILL_ID"] == "${{ inputs.skill_id }}"
    assert step["env"]["INPUT_APPLY"] == "${{ inputs.apply }}"
    assert "${{" not in step["run"]
    assert "ARGS=(--child-mode" in step["run"]
    assert '"${ARGS[@]}"' in step["run"]
    assert "eval " not in step["run"]

    challenge = _step("challenge-watch", CHALLENGE_STEP)
    assert challenge["env"]["INPUT_CHALLENGE_INPUT"] == "${{ inputs.challenge_input }}"
    assert challenge["env"]["INPUT_CHALLENGE_SHADOW"] == "${{ inputs.challenge_shadow }}"
    assert "${{" not in challenge["run"]
    assert '"${ARGS[@]}"' in challenge["run"]
    assert "eval " not in challenge["run"]


def test_workflow_preserves_schedule_and_default_off_gates():
    workflow = _workflow()
    assert workflow["on"]["schedule"] == [{"cron": "0 6 * * *"}]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["challenge_watch"]["default"] == "false"
    # The repository variable is read by the job `if`, not exported: unset means the job is skipped.
    assert "vars.GAIA_CHALLENGE_WATCH_ENABLED" in workflow["jobs"]["challenge-watch"]["if"]


# --- argv handling ---------------------------------------------------------------------------------------------


def test_scheduled_watcher_run_keeps_apply_behavior_and_adds_no_challenge_flags(tmp_path):
    _, argv = _run_argv(tmp_path, "watcher", WATCHER_STEP, {**WATCHER_ENV, "EVENT_NAME": "schedule"})
    assert argv == [
        "--child-mode",
        "fanout",
        "--apply",
        "--report",
        "generated-output/upstream-watcher-report.json",
    ]


def test_challenge_job_argv_is_minimal_by_default(tmp_path):
    _, argv = _run_argv(tmp_path, "challenge-watch", CHALLENGE_STEP, CHALLENGE_ENV)
    assert argv == ["--challenge-only", "--challenge-output", "generated-output/challenge-packets"]


def test_malicious_challenge_values_remain_exact_argv_and_do_not_execute(tmp_path):
    marker = tmp_path / "INJECTION_RAN"
    challenge_input = f"challenge path with spaces; touch {marker}; # `touch {marker}`"
    _, argv = _run_argv(
        tmp_path,
        "challenge-watch",
        CHALLENGE_STEP,
        {"INPUT_CHALLENGE_INPUT": challenge_input, "INPUT_CHALLENGE_SHADOW": "true"},
    )
    assert not marker.exists(), "untrusted dispatch input executed shell commands"
    assert argv == [
        "--challenge-only",
        "--challenge-output",
        "generated-output/challenge-packets",
        "--challenge-input",
        challenge_input,
        "--challenge-shadow",
    ]


def test_watcher_skill_id_with_exact_argv_and_malformed_one_rejected(tmp_path):
    _, argv = _run_argv(tmp_path, "watcher", WATCHER_STEP, {**WATCHER_ENV, "INPUT_SKILL_ID": "owner/repo"})
    assert argv == [
        "--child-mode",
        "fanout",
        "--dry-run",
        "--report",
        "generated-output/upstream-watcher-report.json",
        "--skill",
        "owner/repo",
    ]

    marker = tmp_path / "INJECTION_RAN"
    result, _ = _run_argv(
        tmp_path,
        "watcher",
        WATCHER_STEP,
        {**WATCHER_ENV, "INPUT_SKILL_ID": f"skill with spaces; touch {marker}; # $(touch {marker})"},
        check=False,
    )
    assert result.returncode != 0
    assert "skill_id must match" in result.stdout + result.stderr
    assert not marker.exists(), "untrusted dispatch input executed shell commands"
