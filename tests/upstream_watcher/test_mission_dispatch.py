"""Opt-in workflow fault probes; all gh traffic is handled by the local fake."""
import pytest

from tests.test_upstream_approve_workflow import (
    CLOSE_CHILDREN_PATH, LEGACY_PAYLOAD, REJECT_PATH, REPO_ROOT, SKIP_JOB, SKIP_STEP,
    UMBRELLA, WORKFLOW_PATH, _job_step_run, _rejected_umbrella, _run_cascade,
    _run_sibling_gate, _step_run, child_issue, run_gate, run_step, umbrella_issue, world,
)


@pytest.mark.parametrize("failure", ["empty_list", "drop_link"])
def test_approval_and_cascade_refuse_successful_incomplete_list(tmp_path, failure):
    # A missing next link is detected by the independent terminal probe/count.
    children = [child_issue(6000 + n, slug=f"item-{n}") for n in range(102)]
    data = world(umbrella_issue(LEGACY_PAYLOAD), *children, fail={failure: True})
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    gate = run_gate(gate_dir, data)
    assert gate.code != 0 and gate.outputs != {"gate_passed": "true"}
    assert not gate.workflow_runs() and not gate.closes()
    data["issues"][str(UMBRELLA)] = _rejected_umbrella(LEGACY_PAYLOAD)
    cascade_dir = tmp_path / "cascade"
    cascade_dir.mkdir()
    cascade = _run_cascade(cascade_dir, data)
    assert cascade.code != 0 and not cascade.closes()
    assert not any(call[:2] == ["issue", "edit"] for call in cascade.calls)


def test_sibling_refire_refuses_hidden_open_rows(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD), child_issue(5001), all_list_hidden=[5001])
    result = _run_sibling_gate(tmp_path, data)
    assert result.code != 0 and not result.workflow_runs()


@pytest.mark.parametrize("issue", [
    {**umbrella_issue(LEGACY_PAYLOAD), "labels": [{"name": "skip-child-gate"}]},
    {**umbrella_issue(LEGACY_PAYLOAD), "body": ""},
    {**umbrella_issue(LEGACY_PAYLOAD), "title": "[upstream] other/repo → v1"},
])
def test_skip_label_on_unowned_issue_performs_no_writes(tmp_path, issue):
    result = run_step(tmp_path, _job_step_run(WORKFLOW_PATH, SKIP_JOB, SKIP_STEP),
                      world(issue), {"ISSUE_NUMBER": str(UMBRELLA), "LABELER": "mallory"}, cwd=REPO_ROOT)
    assert result.code == 0
    assert result.calls == [["issue", "view", str(UMBRELLA), "--json", "title,body,labels"]]


@pytest.mark.parametrize("change", [
    {"state": "open"}, {"body": ""}, {"labels": [{"name": "upstream:release"}]},
    {"title": "[upstream] unrelated/repo → v1"},
])
def test_dispatch_rechecks_closed_rejected_family_before_child_writes(tmp_path, change):
    issue = {**_rejected_umbrella(LEGACY_PAYLOAD), **change}
    result = _run_cascade(tmp_path, world(issue, child_issue(5001)))
    assert result.code == 0 and not result.closes()
    assert not any(call[:2] == ["issue", "edit"] for call in result.calls)


def test_dispatch_does_not_trust_the_event_body(tmp_path):
    data = world(_rejected_umbrella(LEGACY_PAYLOAD), child_issue(5001))
    result = run_step(tmp_path, _step_run(CLOSE_CHILDREN_PATH, "Cascade close children on umbrella rejection"),
                      data, {"UMBRELLA_NUMBER": str(UMBRELLA), "UMBRELLA_BODY": "stale body"}, cwd=REPO_ROOT)
    assert result.code == 0 and result.closes() == ["5001"]


def test_reject_dispatches_explicit_cascade_for_github_token(tmp_path):
    step = _step_run(REJECT_PATH, "Explicitly dispatch rejected-family cascade")
    result = run_step(tmp_path, step, world(), {"ISSUE_NUMBER": str(UMBRELLA)})
    assert result.code == 0
    assert result.workflow_runs() == [
        ["workflow", "run", "upstream-close-children.yml", "-f", f"umbrella_number={UMBRELLA}"]
    ]


def test_reject_refuses_unowned_event_without_writes(tmp_path):
    issue = {**_rejected_umbrella(LEGACY_PAYLOAD), "body": "", "state": "open"}
    result = run_step(tmp_path, _step_run(REJECT_PATH, "Verify current rejected upstream ownership"),
                      world(issue), {"ISSUE_NUMBER": str(UMBRELLA)}, cwd=REPO_ROOT)
    assert result.code != 0
    assert len(result.calls) == 1 and result.calls[0][:2] == ["issue", "view"]
