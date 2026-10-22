"""Workflow contract for the batch watcher (#2131)."""

import pathlib

import pytest

import yaml

WORKFLOWS = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _run_script(doc, step_name):
    steps = doc["jobs"][next(iter(doc["jobs"]))]["steps"]
    return next(step["run"] for step in steps if step.get("name") == step_name)


def test_watcher_exposes_escalate_candidate_input():
    doc = _load("upstream-watcher.yml")
    inputs = doc[True]["workflow_dispatch"]["inputs"] if True in doc else doc["on"]["workflow_dispatch"]["inputs"]
    assert "escalate_candidate" in inputs


def test_watcher_passes_inputs_through_env_not_shell_interpolation():
    doc = _load("upstream-watcher.yml")
    run = _run_script(doc, "Run upstream watcher")
    assert "${{ inputs." not in run
    assert "--child-mode batch" in run
    assert "--report generated-output/upstream-watcher-report.json" in run


def test_watcher_escalation_branch_exits_before_polling():
    doc = _load("upstream-watcher.yml")
    run = _run_script(doc, "Run upstream watcher")
    escalate_block = run.split('if [ -n "$INPUT_ESCALATE" ]; then', 1)[1].split("fi", 1)[0]
    assert "--escalate" in escalate_block and "exit 0" in escalate_block


def test_close_children_cascade_lists_covered_rows():
    doc = _load("upstream-close-children.yml")
    run = _run_script(doc, "Cascade close children on umbrella rejection")
    assert "retained, not removed" in run
    # L3: the payload block is read through the one shared regex, not a copy of it.
    assert "from scripts.upstream_watcher.markers import PAYLOAD_RE" in run


# --- mocked execution of the real run block (no runner, no network, no GitHub writes) -------------------------
#
# The run block is executed by bash with a stub ``python`` on PATH that records its argv and exits with a code the
# test chooses. This proves the argument wiring each trigger produces. It does not prove GitHub's own behaviour on a
# real runner (permissions, concurrency queueing, cron firing), which needs a runner and is not covered here.

import os
import subprocess


def _run_block_with(tmp_path, event, env_inputs, python_exit=0):
    run = _run_script(_load("upstream-watcher.yml"), "Run upstream watcher")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "argv.log"
    stub = bin_dir / "python"
    stub.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "$*" >> "{log}"\nexit {python_exit}\n', encoding="utf-8")
    stub.chmod(0o755)
    env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "EVENT_NAME": event,
        "INPUT_SKILL_ID": "",
        "INPUT_ESCALATE": "",
        "INPUT_APPLY": "false",
        "GH_TOKEN": "stub",
        "HOME": str(tmp_path),
        **env_inputs,
    }
    result = subprocess.run(["bash", "-c", run], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return result, calls


def test_the_daily_schedule_runs_in_apply_mode_with_batch_and_no_closure_flag(tmp_path):
    result, calls = _run_block_with(tmp_path, "schedule", {})

    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert "--apply" in calls[0] and "--dry-run" not in calls[0]
    assert "--child-mode batch" in calls[0]
    assert "--report generated-output/upstream-watcher-report.json" in calls[0]
    assert "closure" not in calls[0] and "apply-closures" not in calls[0]


def test_a_manual_run_without_apply_is_a_dry_run(tmp_path):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch", {"INPUT_APPLY": "false"})

    assert result.returncode == 0, result.stderr
    assert "--dry-run" in calls[0] and "--apply" not in calls[0]


def test_a_manual_run_with_apply_writes_only_the_watcher_issues(tmp_path):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch", {"INPUT_APPLY": "true"})

    assert result.returncode == 0, result.stderr
    assert "--apply" in calls[0]


def test_an_escalation_creates_one_child_and_never_polls(tmp_path):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch",
                                    {"INPUT_APPLY": "false", "INPUT_ESCALATE": "garrytan/gbrain:ask-user"})

    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert "--escalate garrytan/gbrain:ask-user" in calls[0] and "--dry-run" in calls[0]
    assert "--child-mode" not in calls[0], "an escalation never runs the batch poll"


@pytest.mark.parametrize("env_inputs", [
    {"INPUT_SKILL_ID": "bad id; rm -rf /"},
    {"INPUT_ESCALATE": "garrytan/gbrain:$(whoami)"},
])
def test_an_input_outside_its_pattern_is_refused_before_the_watcher_runs(tmp_path, env_inputs):
    result, calls = _run_block_with(tmp_path, "workflow_dispatch", env_inputs)

    assert result.returncode == 1
    assert calls == [], "a refused input never reaches the watcher"
    assert "::error::" in result.stdout


def test_the_watcher_exit_code_reaches_the_job_so_unknown_evidence_fails_the_run(tmp_path):
    result, calls = _run_block_with(tmp_path, "schedule", {}, python_exit=3)

    assert result.returncode == 3, "exit 3 is unknown evidence and must fail the scheduled job"
    assert len(calls) == 1


def test_no_run_block_of_the_watcher_names_a_closure_flag():
    text = (WORKFLOWS / "upstream-watcher.yml").read_text(encoding="utf-8")
    assert "apply-closures" not in text and "close_issue" not in text
