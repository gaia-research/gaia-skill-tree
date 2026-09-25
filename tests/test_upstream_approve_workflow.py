"""Regression tests for issue #1921:
Gate upstream-approve workflow on the actual upstream:approved label event.

Previously, .github/workflows/upstream-approve.yml admitted any issues event if
the issue merely contained upstream:approved, meaning adding any later label
(such as skip-child-gate) retriggered approval.
"""

import pathlib
import re
import yaml
import pytest

WORKFLOW_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "upstream-approve.yml"
)


def _load():
    with open(WORKFLOW_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _step_names(steps):
    return [step.get("name") or step.get("uses") for step in steps]


def test_workflow_is_valid_yaml():
    doc = _load()
    assert "jobs" in doc
    assert "approve" in doc["jobs"]


def test_triggers_include_issues_and_workflow_dispatch():
    doc = _load()
    # In YAML 1.1, 'on' can parse as True if unquoted, but PyYAML handles mapping
    triggers = doc.get("on") or doc.get(True)
    assert "issues" in triggers
    assert set(triggers["issues"]["types"]) == {"labeled", "opened"}
    assert "workflow_dispatch" in triggers
    assert "issue_number" in triggers["workflow_dispatch"]["inputs"]


def test_concurrency_is_issue_scoped():
    doc = _load()
    concurrency = doc.get("concurrency")
    assert concurrency is not None, "Workflow must declare top-level concurrency"
    group = concurrency.get("group", "")
    assert "github.event.issue.number" in group
    assert "inputs.issue_number" in group
    assert concurrency.get("cancel-in-progress") is True


def test_approve_job_if_condition_syntax():
    doc = _load()
    job_if = doc["jobs"]["approve"]["if"]
    # Check key components of the condition
    assert "github.event_name == 'issues'" in job_if
    assert "github.event.action == 'labeled'" in job_if
    assert "github.event.label.name == 'upstream:approved'" in job_if
    assert "github.event.action == 'opened'" in job_if
    assert "contains(github.event.issue.labels.*.name, 'upstream:approved')" in job_if
    assert "github.event_name == 'workflow_dispatch'" in job_if


def _evaluate_condition(
    event_name: str,
    action: str | None,
    label_name: str | None,
    issue_labels: list[str],
) -> bool:
    """Python evaluation model of the workflow if: expression:
    (github.event_name == 'issues' && (
      (github.event.action == 'labeled' && github.event.label.name == 'upstream:approved')
      || (github.event.action == 'opened' && contains(github.event.issue.labels.*.name, 'upstream:approved'))
    ))
    || github.event_name == 'workflow_dispatch'
    """
    is_issues = event_name == "issues"
    is_labeled_approve = action == "labeled" and label_name == "upstream:approved"
    is_opened_approve = action == "opened" and ("upstream:approved" in issue_labels)
    is_dispatch = event_name == "workflow_dispatch"

    return (is_issues and (is_labeled_approve or is_opened_approve)) or is_dispatch


def test_repro_1921_later_label_does_not_retrigger_approval():
    """Reproduction of issue #1921:
    When an issue already has 'upstream:approved', adding a subsequent label
    such as 'skip-child-gate' or 'p0' must NOT trigger the approve job.
    """
    # Issue already has upstream:approved, and now 'skip-child-gate' is added
    result = _evaluate_condition(
        event_name="issues",
        action="labeled",
        label_name="skip-child-gate",
        issue_labels=["upstream:approved", "skip-child-gate"],
    )
    assert result is False, "Applying skip-child-gate must not retrigger upstream-approve"

    # Another label like 'p0' added
    result_p0 = _evaluate_condition(
        event_name="issues",
        action="labeled",
        label_name="p0",
        issue_labels=["upstream:approved", "p0"],
    )
    assert result_p0 is False, "Applying p0 must not retrigger upstream-approve"


def test_labeled_upstream_approved_triggers():
    """Applying upstream:approved label triggers approval."""
    result = _evaluate_condition(
        event_name="issues",
        action="labeled",
        label_name="upstream:approved",
        issue_labels=["upstream:approved"],
    )
    assert result is True


def test_opened_with_upstream_approved_triggers():
    """Opening an issue with upstream:approved (e.g. auto-bootstrap) triggers approval."""
    result = _evaluate_condition(
        event_name="issues",
        action="opened",
        label_name=None,
        issue_labels=["upstream:bootstrap", "upstream:approved"],
    )
    assert result is True


def test_opened_without_upstream_approved_does_not_trigger():
    """Opening an issue without upstream:approved does not trigger approval."""
    result = _evaluate_condition(
        event_name="issues",
        action="opened",
        label_name=None,
        issue_labels=["upstream:release"],
    )
    assert result is False


def test_workflow_dispatch_triggers():
    """Manual dispatch via workflow_dispatch triggers approval."""
    result = _evaluate_condition(
        event_name="workflow_dispatch",
        action=None,
        label_name=None,
        issue_labels=[],
    )
    assert result is True


def test_open_draft_pr_is_idempotent():
    """Check that 'Open draft PR' step checks for existing PR before creating."""
    doc = _load()
    steps = {s.get("name"): s for s in doc["jobs"]["approve"]["steps"]}
    open_pr_step = steps.get("Open draft PR")
    assert open_pr_step is not None
    run_script = open_pr_step.get("run", "")
    assert "gh pr list --head" in run_script
    assert "gh pr create" in run_script


def test_comment_pr_link_prevents_duplicates():
    """Check that 'Comment PR link on umbrella' prevents duplicate comments."""
    doc = _load()
    steps = {s.get("name"): s for s in doc["jobs"]["approve"]["steps"]}
    comment_step = steps.get("Comment PR link on umbrella")
    assert comment_step is not None
    run_script = comment_step.get("run", "")
    assert "Draft PR #${PR_NUMBER} opened" in run_script
    assert "ALREADY_COMMENTED" in run_script
