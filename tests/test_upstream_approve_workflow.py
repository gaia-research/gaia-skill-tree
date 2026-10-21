"""Regression tests for issue #1921:
Gate upstream-approve workflow on the actual upstream:approved label event.

Previously, .github/workflows/upstream-approve.yml admitted any issues event if
the issue merely contained upstream:approved, meaning adding any later label
(such as skip-child-gate) retriggered approval.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import yaml
import pytest

WORKFLOW_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "upstream-approve.yml"
)
CLOSE_CHILDREN_PATH = WORKFLOW_PATH.with_name("upstream-close-children.yml")
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


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


def test_approval_wording_says_version_bump_only():
    doc = _load()
    steps = {s.get("name"): s for s in doc["jobs"]["approve"]["steps"]}
    pr_body = steps["Open draft PR"]["run"]
    comment = steps["Comment PR link on umbrella"]["run"]
    assert "Approval confirms the version bump" in pr_body
    assert "does **not** accept any batch row" in pr_body
    assert "remain open candidates" in pr_body
    assert "Approval confirms the version bump to ${NEW_VERSION} only" in comment
    assert "are not accepted" in comment


# ---------------------------------------------------------------------------
# Child lookup (#2131). The workflow steps run for real under bash, with a fake
# `gh` on PATH that serves world state from a JSON file. That exercises the
# embedded python (paginated LIST, v2 candidate verification, fail-closed exits)
# the way GitHub would answer it, with no network access.
# ---------------------------------------------------------------------------

REPO = "gaia-research/gaia-skill-tree"
UMBRELLA = 5000
LOOKUP_MARK = "# shared-child-lookup v1"

FAKE_GH = r'''
import json, os, subprocess, sys
from urllib.parse import parse_qs, urlsplit

with open(os.environ["FAKE_GH_WORLD"], encoding="utf-8") as fh:
    WORLD = json.load(fh)
ARGS = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(ARGS) + "\n")

FAIL = WORLD.get("fail", {})
ISSUES = {int(key): value for key, value in WORLD["issues"].items()}
HIDDEN = set(WORLD.get("list_hidden", []))
GONE = set(WORLD.get("gone", []))
MOVED = set(WORLD.get("moved", []))
PAGE_SIZE = WORLD.get("page_size", 100)


def die(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


def flag(name):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else None


def emit(value, jq=None):
    if jq is None:
        sys.stdout.write(json.dumps(value))
        return
    res = subprocess.run(["jq", "-r", jq], input=json.dumps(value), capture_output=True, text=True)
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    sys.exit(res.returncode)


def list_rows(query):
    wanted_state = query.get("state", ["open"])[0]
    wanted_labels = set(filter(None, query.get("labels", [""])[0].split(",")))
    rows = []
    for number in sorted(ISSUES):
        issue = ISSUES[number]
        labels = {label["name"] for label in issue.get("labels", [])}
        if issue["state"] != wanted_state or not wanted_labels <= labels or number in HIDDEN:
            continue
        row = dict(issue)
        row["number"] = number
        rows.append(row)
    return rows


cmd = ARGS[0] if ARGS else ""
if cmd == "issue" and ARGS[1] == "view":
    if FAIL.get("issue_view"):
        die("HTTP 500 (fake)")
    number = int(ARGS[2])
    if number not in ISSUES:
        die(f"issue #{number} not found (fake)")
    issue = ISSUES[number]
    view = {
        "number": number,
        "title": issue.get("title", ""),
        "body": issue.get("body", ""),
        "state": issue["state"].upper(),
        "labels": issue.get("labels", []),
        "comments": [{"body": text} for text in issue.get("comments", [])],
    }
    emit({field: view[field] for field in flag("--json").split(",")}, flag("--jq"))
elif cmd == "issue" and ARGS[1] == "list":
    # Search-lag stand-in: a list through the issue search path never reports a child.
    emit([], flag("--jq"))
elif cmd == "issue":
    print("https://github.com/gaia-research/gaia-skill-tree/issues/1")
elif cmd == "workflow":
    print("")
elif cmd == "pr" and ARGS[1] == "list":
    sys.stdout.write("")
elif cmd == "pr" and ARGS[1] == "create":
    with open(flag("--body-file"), encoding="utf-8") as fh:
        body = fh.read()
    with open(os.environ["FAKE_GH_PR_BODY"], "w", encoding="utf-8") as fh:
        fh.write(body)
    print("https://github.com/gaia-research/gaia-skill-tree/pull/7001")
elif cmd == "api":
    url = urlsplit(ARGS[-1])
    parts = [part for part in url.path.split("/") if part]
    if len(parts) == 4 and parts[3] == "issues":
        if FAIL.get("list"):
            die("HTTP 502 (fake list failure)")
        rows = list_rows(parse_qs(url.query))
        if "--paginate" in ARGS:
            pages = [rows[i:i + PAGE_SIZE] for i in range(0, len(rows), PAGE_SIZE)] or [[]]
        else:
            pages = [rows[:PAGE_SIZE]]
        sys.stdout.write("".join(json.dumps(page) for page in pages))
    elif len(parts) == 5 and parts[3] == "issues" and parts[4].isdigit():
        number = int(parts[4])
        if number in FAIL.get("get", []):
            die(f"HTTP 502 issue #{number} (fake server failure)")
        if number in FAIL.get("forbidden", []):
            die(f"HTTP 403 issue #{number} (fake forbidden)")
        if number in GONE:
            die(f"HTTP 410 issue #{number} (fake gone)")
        if number in MOVED:
            die(f"gh: Moved Permanently (HTTP 301) issue #{number} (fake transferred)")
        if number not in ISSUES:
            die(f"HTTP 404 issue #{number} (fake not found)")
        row = dict(ISSUES[number])
        row["number"] = number
        sys.stdout.write(json.dumps(row))
    else:
        die(f"unsupported api path {ARGS[-1]}")
else:
    die(f"unsupported gh command {ARGS}")
'''


class StepResult:
    def __init__(self, code, output, outputs, calls, pr_body=None):
        self.code = code
        self.output = output
        self.outputs = outputs
        self.calls = calls
        self.pr_body = pr_body

    def comments(self):
        return [args[args.index("--body") + 1] for args in self.calls if args[:2] == ["issue", "comment"]]

    def closes(self):
        return [args[2] for args in self.calls if args[:2] == ["issue", "close"]]

    def api_calls(self):
        return [args[-1] for args in self.calls if args[:1] == ["api"]]

    def workflow_runs(self):
        return [args for args in self.calls if args[:2] == ["workflow", "run"]]


def run_step(tmp_path, run_text, world_data, extra_env=None, cwd=None):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = tmp_path / "fake_gh.py"
    fake.write_text(FAKE_GH, encoding="utf-8")
    gh = bindir / "gh"
    gh.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n', encoding="utf-8")
    gh.chmod(0o755)
    world_file = tmp_path / "world.json"
    world_file.write_text(json.dumps(world_data), encoding="utf-8")
    log = tmp_path / "gh-calls.jsonl"
    log.write_text("", encoding="utf-8")
    output = tmp_path / "github_output.txt"
    output.write_text("", encoding="utf-8")
    script = tmp_path / "step.sh"
    script.write_text(run_text, encoding="utf-8")
    pr_body_file = tmp_path / "pr_body.md"
    env = {
        "PATH": f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}",
        "HOME": str(tmp_path),
        "GH_TOKEN": "test-token",
        "REPO": REPO,
        "FAKE_GH_WORLD": str(world_file),
        "FAKE_GH_LOG": str(log),
        "FAKE_GH_PR_BODY": str(pr_body_file),
        "GITHUB_OUTPUT": str(output),
        "RUNNER_TEMP": str(tmp_path),
        **(extra_env or {}),
    }
    res = subprocess.run(["bash", str(script)], cwd=cwd or tmp_path, env=env,
                         capture_output=True, text=True, timeout=120)
    outputs = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines() if "=" in line)
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    pr_body = pr_body_file.read_text(encoding="utf-8") if pr_body_file.exists() else None
    return StepResult(res.returncode, res.stdout + res.stderr, outputs, calls, pr_body)


def _step_run(path, name):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    job = next(iter(doc["jobs"].values()))
    return next(step["run"] for step in job["steps"] if step.get("name") == name)


def child_issue(number, umbrella=UMBRELLA, state="open", slug="ask-user", labels=("upstream:child",)):
    return {
        "number": number,
        "title": f"[intake] garrytan/{slug}",
        "state": state,
        "labels": [{"name": name} for name in labels],
        "body": f"> Auto-populated by upstream watcher. Umbrella: #{umbrella}.\n\n**Suggested ID:** `garrytan/{slug}`\n",
    }


def umbrella_issue(payload=None, labels=("upstream:release", "upstream:approved"), extra=()):
    body = "## Upstream release detected\n\n"
    if payload is not None:
        body += "<!-- gaia-upstream-payload\n" + json.dumps(payload) + "\n-->\n"
    return {
        "number": UMBRELLA,
        "title": "[upstream] garrytan/gbrain → v1",
        "state": "open",
        "labels": [{"name": name} for name in (*labels, *extra)],
        "body": body,
    }


def world(*issues, **extra):
    data = {"issues": {str(issue["number"]): issue for issue in issues}}
    data.update(extra)
    return data


LEGACY_PAYLOAD = {"skillId": "garrytan/gbrain", "newVersion": "v1", "componentAdds": ["ask-user"]}


def v2_payload(*children):
    rows = [
        {"id": f"garrytan/gbrain:{slug}", "slug": slug, "suggestedId": f"garrytan/{slug}",
         "status": "escalated" if number else "new", "child": number}
        for slug, number in children
    ]
    return {"payloadVersion": 2, "skillId": "garrytan/gbrain", "newVersion": "v1",
            "componentAdds": [slug for slug, _ in children], "candidates": rows}


def run_gate(tmp_path, world_data):
    return run_step(tmp_path, _step_run(WORKFLOW_PATH, "Check child gate"), world_data,
                    {"ISSUE_NUMBER": str(UMBRELLA)})


def _lookup_blocks():
    blocks = []
    for path, job in ((WORKFLOW_PATH, "approve"), (CLOSE_CHILDREN_PATH, "close-children")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for step in doc["jobs"][job]["steps"]:
            run = step.get("run", "")
            if LOOKUP_MARK in run:
                blocks.append(run.split(LOOKUP_MARK, 1)[1].split("\nPY\n", 1)[0])
    return blocks


def test_no_search_based_child_lookup_in_either_workflow():
    for path in (WORKFLOW_PATH, CLOSE_CHILDREN_PATH):
        text = path.read_text(encoding="utf-8")
        assert "--search" not in text, path.name
        assert "gh issue list" not in text, path.name


def test_shared_lookup_block_is_identical_in_every_embedding():
    blocks = _lookup_blocks()
    assert len(blocks) == 3  # approve gate, sibling re-fire, rejection cascade
    assert len(set(blocks)) == 1


def test_skip_child_gate_is_described_as_bypass_only():
    run = _step_run(WORKFLOW_PATH, "Check child gate")
    assert "does not close, accept or reject any child intake or the umbrella" in run


def test_gate_passes_with_no_open_children(tmp_path):
    result = run_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), child_issue(5001, state="closed")))
    assert result.code == 0
    assert result.outputs == {"gate_passed": "true"}


def test_gate_blocks_on_open_child_and_names_it(tmp_path):
    result = run_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), child_issue(5001)))
    assert result.code == 0 and result.outputs == {"gate_passed": "false"}
    assert "Cannot sync yet: 1 child intake(s) open: #5001" in result.comments()[-1]


def test_gate_reads_every_list_page_and_finds_child_on_second_page(tmp_path):
    data = world(
        umbrella_issue(LEGACY_PAYLOAD),
        child_issue(5001, umbrella=999, slug="other-a"),
        child_issue(5002, umbrella=999, slug="other-b"),
        child_issue(5003),
        page_size=2,
    )
    result = run_gate(tmp_path, data)
    assert result.outputs == {"gate_passed": "false"}
    assert "#5003" in result.comments()[-1] and "#5001" not in result.comments()[-1]
    paginated = [args for args in result.calls if args[:1] == ["api"] and "--paginate" in args]
    assert len(paginated) == 1 and "state=open" in paginated[0][-1] and "labels=upstream%3Achild" in paginated[0][-1]


def test_gate_matches_umbrella_number_exactly(tmp_path):
    # Child for umbrella #500 must not block umbrella #5000 (search matched loosely; the body line does not).
    result = run_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), child_issue(5010, umbrella=500, slug="near-miss")))
    assert result.outputs == {"gate_passed": "true"}


def test_gate_does_not_depend_on_search_so_index_lag_cannot_hide_a_child(tmp_path):
    # The fake answers every `gh issue list` (the search path) with no rows, as a lagging index would.
    result = run_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), child_issue(5001)))
    assert result.outputs == {"gate_passed": "false"}
    assert not [args for args in result.calls if args[:2] == ["issue", "list"]]


def test_skip_child_gate_bypasses_the_gate_only(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD, extra=("skip-child-gate",)), child_issue(5001))
    result = run_gate(tmp_path, data)
    assert result.code == 0 and result.outputs == {"gate_passed": "true"}
    assert "does not close, accept or reject any child intake or the umbrella" in result.output
    assert not result.closes() and not result.comments() and not result.api_calls()


def test_v2_adopted_child_blocks_even_when_the_list_does_not_return_it(tmp_path):
    payload = v2_payload(("ask-user", 5001), ("briefing", None))
    result = run_gate(tmp_path, world(umbrella_issue(payload), child_issue(5001), list_hidden=[5001]))
    assert result.outputs == {"gate_passed": "false"}
    assert "#5001" in result.comments()[-1]
    assert f"repos/{REPO}/issues/5001" in result.api_calls()


def test_v2_candidate_child_that_is_closed_does_not_block(tmp_path):
    payload = v2_payload(("ask-user", 5001), ("briefing", None))
    result = run_gate(tmp_path, world(umbrella_issue(payload), child_issue(5001, state="closed")))
    assert result.outputs == {"gate_passed": "true"}


def test_v1_payload_makes_no_per_child_lookups(tmp_path):
    result = run_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), child_issue(5001, state="closed")))
    assert result.outputs == {"gate_passed": "true"}
    assert not [call for call in result.api_calls() if "?" not in call]


def test_gate_list_failure_fails_closed(tmp_path):
    result = run_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), fail={"list": True}))
    assert result.code != 0
    assert "gate_passed" not in result.outputs
    assert "could not verify child intakes" in result.comments()[-1]


def test_gate_candidate_get_failure_fails_closed(tmp_path):
    payload = v2_payload(("ask-user", 5001))
    data = world(umbrella_issue(payload), child_issue(5001), list_hidden=[5001], fail={"get": [5001]})
    result = run_gate(tmp_path, data)
    assert result.code != 0
    assert "gate_passed" not in result.outputs


def test_gate_candidate_forbidden_get_fails_closed(tmp_path):
    payload = v2_payload(("ask-user", 5001))
    data = world(umbrella_issue(payload), child_issue(5001), list_hidden=[5001], fail={"forbidden": [5001]})
    result = run_gate(tmp_path, data)
    assert result.code != 0
    assert "gate_passed" not in result.outputs


def test_gate_candidate_child_deleted_404_is_absent_and_does_not_block(tmp_path):
    # Child #5001 no longer exists (deleted). The gate must not be blocked forever by it.
    payload = v2_payload(("ask-user", 5001), ("briefing", None))
    result = run_gate(tmp_path, world(umbrella_issue(payload)))
    assert result.code == 0
    assert result.outputs == {"gate_passed": "true"}
    assert "::notice::" in result.output and "#5001" in result.output
    assert "absent" in result.output


def test_gate_candidate_child_gone_410_is_absent_and_does_not_block(tmp_path):
    payload = v2_payload(("ask-user", 5001))
    result = run_gate(tmp_path, world(umbrella_issue(payload), gone=[5001]))
    assert result.outputs == {"gate_passed": "true"}
    assert "#5001" in result.output


def test_gate_candidate_child_transferred_301_is_absent_and_does_not_block(tmp_path):
    # Child #5001 was transferred: its old number answers HTTP 301. It cannot block the gate.
    payload = v2_payload(("ask-user", 5001), ("briefing", None))
    result = run_gate(tmp_path, world(umbrella_issue(payload), moved=[5001]))
    assert result.code == 0
    assert result.outputs == {"gate_passed": "true"}
    assert "::notice::" in result.output and "#5001" in result.output
    assert "absent (HTTP 301/404/410)" in result.output


def test_gate_absent_child_still_blocks_on_other_open_children(tmp_path):
    # Only the dead link is skipped; a live open child elsewhere in the payload still gates.
    payload = v2_payload(("ask-user", 5001), ("briefing", 5002))
    data = world(umbrella_issue(payload), child_issue(5002, slug="briefing"))
    result = run_gate(tmp_path, data)
    assert result.outputs == {"gate_passed": "false"}
    assert "#5002" in result.comments()[-1] and "#5001" not in result.comments()[-1]


def _rejected_umbrella(payload):
    return umbrella_issue(payload, labels=("upstream:release", "upstream:rejected"))


def _run_cascade(tmp_path, data):
    body = data["issues"][str(UMBRELLA)]["body"]
    return run_step(tmp_path, _step_run(CLOSE_CHILDREN_PATH, "Cascade close children on umbrella rejection"),
                    data, {"UMBRELLA_NUMBER": str(UMBRELLA), "UMBRELLA_BODY": body})


def test_rejected_cascade_closes_every_open_child_across_pages(tmp_path):
    payload = v2_payload(("ask-user", 5001), ("briefing", None))
    data = world(
        _rejected_umbrella(payload),
        child_issue(5001),
        child_issue(5002, slug="briefing"),
        child_issue(5003, slug="third"),
        page_size=2,
    )
    result = _run_cascade(tmp_path, data)
    assert result.code == 0
    assert result.closes() == ["5001", "5002", "5003"]
    assert any("retained, not removed" in body for body in result.comments())


def test_rejected_cascade_closes_open_children_and_skips_a_transferred_one(tmp_path):
    payload = v2_payload(("ask-user", 5001), ("briefing", 5002))
    data = world(_rejected_umbrella(payload), child_issue(5002, slug="briefing"), moved=[5001])
    result = _run_cascade(tmp_path, data)
    assert result.code == 0
    assert result.closes() == ["5002"]


def test_rejected_cascade_closes_nothing_when_the_lookup_fails(tmp_path):
    payload = v2_payload(("ask-user", 5001))
    result = _run_cascade(tmp_path, world(_rejected_umbrella(payload), child_issue(5001), fail={"list": True}))
    assert result.code != 0
    assert result.closes() == []


def _run_sibling_gate(tmp_path, data):
    closed_sibling = child_issue(5009, state="closed", slug="done-one")
    data["issues"][str(closed_sibling["number"])] = closed_sibling
    return run_step(tmp_path, _step_run(CLOSE_CHILDREN_PATH, "Re-fire approve workflow if all siblings closed"),
                    data, {"CLOSED_ISSUE_NUMBER": "5009",
                           "CLOSED_ISSUE_BODY": "> Auto-populated by upstream watcher. Umbrella: #5000.\n"})


def test_sibling_gate_refires_approve_when_no_child_is_open(tmp_path):
    result = _run_sibling_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD)))
    assert result.code == 0
    assert result.workflow_runs() == [["workflow", "run", "upstream-approve.yml", "-f", f"issue_number={UMBRELLA}"]]


def test_sibling_gate_waits_while_a_child_is_open(tmp_path):
    result = _run_sibling_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), child_issue(5001)))
    assert result.code == 0 and not result.workflow_runs()


def test_sibling_gate_waits_for_a_v2_adopted_child_the_list_omits(tmp_path):
    payload = v2_payload(("ask-user", 5001))
    result = _run_sibling_gate(tmp_path, world(umbrella_issue(payload), child_issue(5001), list_hidden=[5001]))
    assert result.code == 0 and not result.workflow_runs()


def test_sibling_gate_does_not_wait_on_a_transferred_child(tmp_path):
    payload = v2_payload(("ask-user", 5001))
    result = _run_sibling_gate(tmp_path, world(umbrella_issue(payload), moved=[5001]))
    assert result.code == 0
    assert result.workflow_runs() == [["workflow", "run", "upstream-approve.yml", "-f", f"issue_number={UMBRELLA}"]]


def test_sibling_gate_never_refires_on_lookup_failure(tmp_path):
    result = _run_sibling_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD), fail={"list": True}))
    assert result.code != 0
    assert not result.workflow_runs()


# ---------------------------------------------------------------------------
# Umbrella closure must not lose rows (#2131). The approve job counts the rows
# still owed a decision, then closes the umbrella (Fixes) only when there are none.
# Otherwise the PR references it (Refs) and says the umbrella stays open.
# ---------------------------------------------------------------------------

BRANCH = "review/meta/upstream-garrytan-gbrain-v1"


def _open_pr(tmp_path, unresolved):
    run_dir = tmp_path / f"pr-{unresolved}"
    run_dir.mkdir()
    env = {"BRANCH": BRANCH, "SKILL_ID": "garrytan/gbrain", "NEW_VERSION": "v1",
           "ISSUE_NUMBER": str(UMBRELLA), "UNRESOLVED": str(unresolved)}
    return run_step(run_dir, _step_run(WORKFLOW_PATH, "Open draft PR"), world(umbrella_issue(LEGACY_PAYLOAD)), env)


def test_pr_body_closes_the_umbrella_when_no_row_is_unresolved(tmp_path):
    result = _open_pr(tmp_path, 0)
    assert result.code == 0
    assert f"Fixes #{UMBRELLA}" in result.pr_body
    assert f"Refs #{UMBRELLA}" not in result.pr_body
    assert "Umbrella stays open" not in result.pr_body


def test_pr_body_references_and_keeps_open_when_rows_are_unresolved(tmp_path):
    result = _open_pr(tmp_path, 2)
    assert result.code == 0
    assert f"Refs #{UMBRELLA}" in result.pr_body
    assert f"Fixes #{UMBRELLA}" not in result.pr_body
    assert "Umbrella stays open: 2 unresolved candidate row(s)" in result.pr_body


def test_pr_body_keeps_version_bump_only_scope_in_both_branches(tmp_path):
    for unresolved in (0, 3):
        result = _open_pr(tmp_path, unresolved)
        assert "Approval confirms the version bump to `v1` only" in result.pr_body
        assert "does **not** accept any batch row" in result.pr_body


def _umbrella_comment(tmp_path, unresolved):
    env = {"ISSUE_NUMBER": str(UMBRELLA), "NEW_VERSION": "v1", "PR_NUMBER": "7001",
           "PR_URL": "https://github.com/gaia-research/gaia-skill-tree/pull/7001", "UNRESOLVED": str(unresolved)}
    return run_step(tmp_path, _step_run(WORKFLOW_PATH, "Comment PR link on umbrella"),
                    world(umbrella_issue(LEGACY_PAYLOAD)), env)


def test_umbrella_comment_says_it_stays_open_when_rows_are_unresolved(tmp_path):
    result = _umbrella_comment(tmp_path, 2)
    assert result.code == 0
    body = result.comments()[-1]
    assert "Umbrella stays open: 2 unresolved candidate row(s)" in body
    assert "Auto-closes" not in body


def test_umbrella_comment_keeps_auto_close_wording_when_nothing_is_unresolved(tmp_path):
    result = _umbrella_comment(tmp_path, 0)
    assert result.code == 0
    assert "Auto-closes this umbrella on merge" in result.comments()[-1]


def _row(slug, status, child=None):
    return {"id": f"garrytan/gbrain:{slug}", "slug": slug, "suggestedId": f"garrytan/{slug}",
            "status": status, "child": child}


def _child_issue(number, state):
    return {"number": number, "title": f"[intake] garrytan/c{number}", "state": state,
            "labels": [{"name": "upstream:child"}], "body": ""}


# Covers every status and child state the rule distinguishes.
MIXED_ROWS = [
    _row("ask-user", "escalated", 5001),      # open child: unresolved
    _row("briefing", "new"),                  # never escalated: unresolved
    _row("present-one", "present"),           # registry-present: resolved
    _row("rejected-one", "rejected", 5004),   # rejected: resolved
    _row("closed-one", "escalated", 5005),    # child closed: resolved
    _row("gone-one", "escalated", 5006),      # child deleted (404, not in world): unresolved
    _row("tracked-closed", "tracked", 5007),  # child closed: resolved
]
EXPECTED_UNRESOLVED = ["garrytan/gbrain:ask-user", "garrytan/gbrain:briefing", "garrytan/gbrain:gone-one"]


def _count(tmp_path, rows, **extra):
    payload = {"payloadVersion": 2, "skillId": "garrytan/gbrain", "newVersion": "v1", "candidates": rows}
    data = world(
        umbrella_issue(payload),
        _child_issue(5001, "open"), _child_issue(5004, "closed"),
        _child_issue(5005, "closed"), _child_issue(5007, "closed"),
        **extra,
    )
    return run_step(tmp_path, _step_run(WORKFLOW_PATH, "Count unresolved candidate rows"), data,
                    {"PAYLOAD": json.dumps(payload), "ISSUE_NUMBER": str(UMBRELLA)}, cwd=REPO_ROOT)


def test_count_step_treats_only_open_absent_and_unlinked_rows_as_unresolved(tmp_path):
    result = _count(tmp_path, MIXED_ROWS)
    assert result.code == 0
    assert result.outputs == {"count": "3"}
    assert json.dumps(EXPECTED_UNRESOLVED) in result.output


def test_count_step_is_zero_for_a_legacy_payload(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD))
    result = run_step(tmp_path, _step_run(WORKFLOW_PATH, "Count unresolved candidate rows"), data,
                      {"PAYLOAD": json.dumps(LEGACY_PAYLOAD), "ISSUE_NUMBER": str(UMBRELLA)}, cwd=REPO_ROOT)
    assert result.code == 0 and result.outputs == {"count": "0"}


def test_count_step_treats_a_transferred_child_as_unresolved(tmp_path):
    rows = [_row("moved-one", "escalated", 5008)]
    result = _count(tmp_path, rows, moved=[5008])
    assert result.code == 0
    assert result.outputs == {"count": "1"}
    assert json.dumps(["garrytan/gbrain:moved-one"]) in result.output


def test_count_step_fails_closed_on_a_server_error(tmp_path):
    result = _count(tmp_path, MIXED_ROWS, fail={"get": [5001]})
    assert result.code != 0
    assert "count" not in result.outputs
    assert "Could not verify candidate rows" in result.comments()[-1]


def test_count_step_fails_closed_on_forbidden(tmp_path):
    result = _count(tmp_path, MIXED_ROWS, fail={"forbidden": [5001]})
    assert result.code != 0
    assert "count" not in result.outputs


def test_every_write_step_after_the_gate_is_guarded_by_it():
    # The exit step alone does not stop the job: a later unguarded step would still open the PR.
    doc = _load()
    steps = doc["jobs"]["approve"]["steps"]
    names = [step.get("name") for step in steps]
    guard = "steps.child_gate.outputs.gate_passed == 'true'"
    after = steps[names.index("Exit if child gate failed") + 1:]
    assert after, "expected steps after the gate"
    for step in after:
        assert guard in str(step.get("if", "")), step.get("name")
