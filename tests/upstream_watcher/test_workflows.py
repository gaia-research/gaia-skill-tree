"""Workflow contract for the batch watcher (#2131)."""

import pathlib

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
    assert "gaia-upstream-payload" in run
