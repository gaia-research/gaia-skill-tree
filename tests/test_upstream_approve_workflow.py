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
import tempfile

import yaml

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
    # L4: a denied run must not cancel an in-flight Verifier sync, so the group never cancels.
    assert concurrency.get("cancel-in-progress") is False


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
        if (issue["state"] != wanted_state or not wanted_labels <= labels
                or number in WORLD.get("all_list_hidden", []) or (wanted_labels and number in HIDDEN)):
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
    if FAIL.get("workflow"):
        die("HTTP 403 (fake workflow dispatch refused)")
    print("")
elif cmd == "pr" and ARGS[1] == "list":
    if FAIL.get("pr_list"):
        die("HTTP 502 (fake pr list failure)")
    emit(WORLD.get("pr_list", []), flag("--jq"))
elif cmd == "pr" and ARGS[1] == "create":
    with open(flag("--body-file"), encoding="utf-8") as fh:
        body = fh.read()
    with open(os.environ["FAKE_GH_PR_BODY"], "w", encoding="utf-8") as fh:
        fh.write(body)
    print("https://github.com/gaia-research/gaia-skill-tree/pull/7001")
elif cmd == "api":
    url = urlsplit(ARGS[-1])
    parts = [part for part in url.path.split("/") if part]
    if len(parts) >= 5 and parts[3] == "compare":
        emit(WORLD.get("compare", {"total_commits": 0, "commits": []}), flag("--jq"))
    elif len(parts) == 3 and parts[0] == "repos":
        # Independent repository metadata, not derived from a possibly hidden list.
        emit({"open_issues_count": sum(row["state"] == "open" for row in ISSUES.values())})
    elif len(parts) == 4 and parts[3] == "issues":
        if FAIL.get("list"):
            die("HTTP 502 (fake list failure)")
        query = parse_qs(url.query)
        rows = list_rows(query)
        if "--include" in ARGS:
            size = int(query.get("per_page", [100])[0])
            page = int(query.get("page", [1])[0])
            start = (page - 1) * size
            current = rows[start:start + size]
            if FAIL.get("empty_list"):
                current = []
            sys.stdout.write("HTTP/1.1 200 OK\n")
            if start + size < len(rows) and not FAIL.get("drop_link"):
                from urllib.parse import urlencode
                query["page"] = [str(page + 1)]
                flat = {key: value[0] for key, value in query.items()}
                sys.stdout.write(f'Link: <https://api.github.com/{url.path}?{urlencode(flat)}>; rel="next"\n')
            sys.stdout.write("\n" + json.dumps(current))
        elif "--paginate" in ARGS:
            pages = [rows[i:i + PAGE_SIZE] for i in range(0, len(rows), PAGE_SIZE)] or [[]]
            sys.stdout.write("".join(json.dumps(page) for page in pages))
        else:
            sys.stdout.write(json.dumps(rows[:PAGE_SIZE]))
    elif len(parts) == 6 and parts[3] == "issues" and parts[4].isdigit() and parts[5] in ("events", "comments"):
        if parts[5] == "events" and FAIL.get("events"):
            die("HTTP 502 (fake events failure)")
        table = WORLD.get("events" if parts[5] == "events" else "comment_rows", {})
        rows = table.get(parts[4], [])
        pages = [rows[i:i + PAGE_SIZE] for i in range(0, len(rows), PAGE_SIZE)] or [[]]
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


def run_step(tmp_path, run_text, world_data, extra_env=None, cwd=None, shims=None):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = tmp_path / "fake_gh.py"
    fake.write_text(FAKE_GH, encoding="utf-8")
    gh = bindir / "gh"
    gh.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n', encoding="utf-8")
    gh.chmod(0o755)
    # Optional stand-ins for other commands the step runs (for example `python -m gaia_cli`).
    for name, body in (shims or {}).items():
        shim = bindir / name
        shim.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        shim.chmod(0o755)
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
    # Search every job: a workflow may hold more than one (the skip-child-gate guard job comes first, L5).
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for job in doc["jobs"].values():
        for step in job["steps"]:
            if step.get("name") == name:
                return step["run"]
    raise KeyError(name)


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
    # The workflow runs from the repo root, where the shared lookup imports scripts/upstream_watcher/markers.
    return run_step(tmp_path, _step_run(WORKFLOW_PATH, "Check child gate"), world_data,
                    {"ISSUE_NUMBER": str(UMBRELLA)}, cwd=REPO_ROOT)


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
    for path, job in ((WORKFLOW_PATH, "approve"), (CLOSE_CHILDREN_PATH, "close-children")):
        text = "\n".join(step.get("run", "") for step in yaml.safe_load(path.read_text())["jobs"][job]["steps"])
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
        *(child_issue(4800 + n, umbrella=999, slug=f"other-{n}") for n in range(100)),
        child_issue(5003),
    )
    result = run_gate(tmp_path, data)
    assert result.outputs == {"gate_passed": "false"}
    assert "#5003" in result.comments()[-1] and "#5001" not in result.comments()[-1]
    paginated = [args for args in result.calls if args[:1] == ["api"] and "--include" in args]
    assert any("page=2" in args[-1] for args in paginated)
    assert all("state=open" in args[-1] for args in paginated)


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
    # L5: the bypass is honoured only from a labeler who may approve (here a Verifier).
    data = world(umbrella_issue(LEGACY_PAYLOAD, extra=("skip-child-gate",)), child_issue(5001),
                 events={str(UMBRELLA): [_labeled(7, "alice", label="skip-child-gate")]})
    result = _gate_in_repo(tmp_path, data)
    assert result.code == 0 and result.outputs == {"gate_passed": "true"}
    assert "does not close, accept or reject any child intake or the umbrella" in result.output
    assert not result.closes() and not result.comments()
    assert not any("issues/" + str(UMBRELLA) + "/" in call[-1] and "events" not in call[-1]
                   for call in result.api_calls())


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
    assert not [call for call in result.api_calls() if "/issues/" in call and "?" not in call]


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
    return {**umbrella_issue(payload, labels=("upstream:release", "upstream:rejected")), "state": "closed"}


def run_step_repo(*args, **kwargs):
    """run_step from the repo root, where the shared lookup imports scripts/upstream_watcher/markers."""
    return run_step(*args, **{"cwd": REPO_ROOT, **kwargs})


def _run_cascade(tmp_path, data):
    body = data["issues"][str(UMBRELLA)]["body"]
    return run_step(tmp_path, _step_run(CLOSE_CHILDREN_PATH, "Cascade close children on umbrella rejection"),
                    data, {"UMBRELLA_NUMBER": str(UMBRELLA), "UMBRELLA_BODY": body}, cwd=REPO_ROOT)


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
                           "CLOSED_ISSUE_BODY": "> Auto-populated by upstream watcher. Umbrella: #5000.\n"},
                    cwd=REPO_ROOT)


def test_sibling_gate_refires_approve_when_no_child_is_open(tmp_path):
    result = _run_sibling_gate(tmp_path, world(umbrella_issue(LEGACY_PAYLOAD)))
    assert result.code == 0
    assert result.workflow_runs() == [["workflow", "run", "upstream-approve.yml", "-f", f"issue_number={UMBRELLA}",
                                       "-f", "refire=true"]]


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
    assert result.workflow_runs() == [["workflow", "run", "upstream-approve.yml", "-f", f"issue_number={UMBRELLA}",
                                       "-f", "refire=true"]]


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


def _child_issue(number, state, labels=("upstream:child",)):
    return {"number": number, "title": f"[intake] garrytan/c{number}", "state": state,
            "labels": [{"name": name} for name in labels], "body": ""}


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
        _child_issue(5001, "open"), _child_issue(5004, "closed", ("upstream:child", "upstream:rejected")),
        _child_issue(5005, "closed", ("upstream:child", "upstream:rejected")),
        _child_issue(5007, "closed", ("upstream:child", "upstream:rejected")),
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


# ---------------------------------------------------------------------------
# #2131 verifier FAIL. H1 (guard), M9 (no inputs in run blocks), L3 (approve state),
# L4 (freeze, docs and PR body), M7 and M8 (close-children), L5 (watcher permissions).
# Every run block executes under bash with the fake gh (and a python shim where it runs gaia).
# ---------------------------------------------------------------------------

BUILD_STEP = "Build the base named-skills index"
GUARD = "Check labeler is a Verifier"
RESOLVE = "Resolve issue number and actor"
VERIFY_STEP = "Verify the issue is open and approved"
FREEZE_STEP = "Freeze removed components"
DOCS_STEP = "Regenerate Class S artifacts"
PR_STEP = "Open draft PR"
CASCADE_STEP = "Cascade close children on umbrella rejection"
REFIRE_STEP = "Re-fire approve workflow if all siblings closed"
WATCHER_PATH = REPO_ROOT / ".github" / "workflows" / "upstream-watcher.yml"

VERIFIER_INDEX = {"buckets": {"stars": [{"contributor": "alice", "level": "4★"}]}}
NO_VERIFIER_INDEX = {"buckets": {"stars": [{"contributor": "bob", "level": "2★"}]}}

# A stand-in for `python -m gaia_cli ...` in the freeze and docs steps.
GAIA_SHIM = r'''
case "$*" in
  *"dev freeze"*)
    case "$*" in *"${FAKE_FREEZE_FAIL:-__never__}"*) exit 1 ;; esac
    exit 0 ;;
  *"dev docs"*)
    if [ -n "${FAKE_DOCS_FAIL:-}" ]; then exit 1; fi
    exit 0 ;;
esac
exit 0
'''


def _fresh(tmp_path, name):
    path = tmp_path / name
    path.mkdir(parents=True)
    return path


def _guard(tmp_path, actor, index=None, actor_type="User", actor_id="1"):
    """Run the Verifier guard in a checkout whose registry/named-skills.json is *index* (or absent)."""
    repo = _fresh(tmp_path, "repo")
    (repo / "registry").mkdir()
    (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
    if index is not None:
        text = index if isinstance(index, str) else json.dumps(index)
        (repo / "registry" / "named-skills.json").write_text(text, encoding="utf-8")
    return run_step(tmp_path, _step_run(WORKFLOW_PATH, GUARD), world(umbrella_issue(LEGACY_PAYLOAD)),
                    {"LABELER": actor, "LABELER_TYPE": actor_type, "LABELER_ID": actor_id,
                     "ISSUE_NUMBER": str(UMBRELLA)}, cwd=repo)


def test_guard_denies_when_the_index_is_missing(tmp_path):
    result = _guard(tmp_path, "mallory", index=None)
    assert result.code == 1
    assert "deny-missing-index" in result.output


def test_guard_denies_an_unparseable_index(tmp_path):
    result = _guard(tmp_path, "mallory", index="{not json")
    assert result.code == 1
    assert "deny-unparseable-index" in result.output


def test_guard_denies_an_index_without_buckets(tmp_path):
    result = _guard(tmp_path, "mallory", index=[])
    assert result.code == 1
    assert "deny-unparseable-index" in result.output


def test_guard_denies_a_parseable_index_with_no_verifiers_because_bootstrap_is_gone(tmp_path):
    # M1: bootstrap-by-absence is removed. Only the allowlist can authorize an index with no Verifier.
    result = _guard(tmp_path, "mallory", index=NO_VERIFIER_INDEX)
    assert result.code == 1
    assert "bootstrap" not in result.output


def test_guard_grants_a_verifier_and_refuses_a_non_verifier(tmp_path):
    assert _guard(_fresh(tmp_path, "a"), "alice", index=VERIFIER_INDEX).code == 0
    refused = _guard(_fresh(tmp_path, "b"), "mallory", index=VERIFIER_INDEX)
    assert refused.code == 1
    assert refused.comments() and "does not hold a 4★+ named skill" in refused.comments()[0]


def test_bot_allowlist_still_passes_without_any_index(tmp_path):
    assert _guard(tmp_path, "github-actions[bot]", index=None, actor_type="Bot").code == 0


def test_the_index_is_built_before_the_guard_runs():
    names = _step_names(_load()["jobs"]["approve"]["steps"])
    assert names.index(BUILD_STEP) < names.index(GUARD)
    build = _step_run(WORKFLOW_PATH, BUILD_STEP)
    assert "scripts/assemble_gaia.py" in build and "scripts/generateNamedIndex.py" in build


def test_no_run_block_interpolates_workflow_inputs_or_event_fields():
    for path in (WORKFLOW_PATH, CLOSE_CHILDREN_PATH, WATCHER_PATH, REJECT_PATH):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, job in doc["jobs"].items():
            if name.startswith("legacy-"):
                continue  # Exact deployed fallback is intentionally unchanged; hashes pin its limitations.
            for step in job["steps"]:
                assert "${{" not in step.get("run", ""), f"{path.name}: {step.get('name')}"


def test_resolve_step_refuses_a_non_numeric_issue_number(tmp_path):
    marker = tmp_path / "pwned"
    result = run_step(_fresh(tmp_path, "inj"), _step_run(WORKFLOW_PATH, RESOLVE), world(), {
        "EVENT_NAME": "workflow_dispatch", "INPUT_ISSUE_NUMBER": f"5; touch {marker}",
        "ACTOR_LOGIN": "alice", "EVENT_ISSUE_NUMBER": "", "SENDER_LOGIN": "",
    })
    assert result.code == 1
    assert "must be digits only" in result.output
    assert not marker.exists()


def test_resolve_step_reads_a_numeric_dispatch_input_from_env(tmp_path):
    result = run_step(_fresh(tmp_path, "ok"), _step_run(WORKFLOW_PATH, RESOLVE), world(), {
        "EVENT_NAME": "workflow_dispatch", "INPUT_ISSUE_NUMBER": "5000", "ACTOR_LOGIN": "alice",
        "EVENT_ISSUE_NUMBER": "", "SENDER_LOGIN": "",
    })
    assert result.code == 0
    assert result.outputs["number"] == "5000" and result.outputs["actor"] == "alice"
    assert result.outputs["actor_type"] == "" and result.outputs["actor_id"] == ""


def _verify(tmp_path, issue):
    return run_step(_fresh(tmp_path, "verify"), _step_run(WORKFLOW_PATH, VERIFY_STEP), world(issue),
                    {"ISSUE_NUMBER": str(UMBRELLA)})


def test_verify_step_passes_an_open_approved_umbrella(tmp_path):
    assert _verify(tmp_path, umbrella_issue(LEGACY_PAYLOAD)).code == 0


def test_verify_step_refuses_a_closed_umbrella(tmp_path):
    result = _verify(tmp_path, {**umbrella_issue(LEGACY_PAYLOAD), "state": "closed"})
    assert result.code == 1
    assert "not open" in result.output


def test_verify_step_refuses_an_umbrella_whose_approval_was_withdrawn(tmp_path):
    result = _verify(tmp_path, umbrella_issue(LEGACY_PAYLOAD, labels=("upstream:release",)))
    assert result.code == 1
    assert "upstream:approved" in result.output


def _freeze(tmp_path, removes, fail=None):
    env = {"PAYLOAD": json.dumps({"componentRemoves": removes}), "ISSUE_NUMBER": str(UMBRELLA),
           "NEW_VERSION": "v2", "GAIA_OPERATOR_OVERRIDE": "1"}
    if fail:
        env["FAKE_FREEZE_FAIL"] = fail
    return run_step(_fresh(tmp_path, "freeze"), _step_run(WORKFLOW_PATH, FREEZE_STEP),
                    world(umbrella_issue(LEGACY_PAYLOAD)), env, shims={"python": GAIA_SHIM})


def test_a_failed_freeze_fails_the_job_and_names_the_component(tmp_path):
    result = _freeze(tmp_path, ["garrytan/old-one"], fail="garrytan/old-one")
    assert result.code == 1
    assert "Freeze failed for" in result.output
    assert any("freeze failed" in body for body in result.comments())
    assert result.outputs.get("frozen_count") == "0"


def test_a_successful_freeze_reports_how_many_components_it_froze(tmp_path):
    result = _freeze(tmp_path, ["garrytan/a", "garrytan/b"])
    assert result.code == 0
    assert result.outputs["frozen_count"] == "2"


def test_a_failed_class_s_regeneration_fails_the_job_and_says_so(tmp_path):
    result = run_step(_fresh(tmp_path, "docs"), _step_run(WORKFLOW_PATH, DOCS_STEP),
                      world(umbrella_issue(LEGACY_PAYLOAD)),
                      {"ISSUE_NUMBER": str(UMBRELLA), "GAIA_OPERATOR_OVERRIDE": "1", "FAKE_DOCS_FAIL": "1"},
                      shims={"python": GAIA_SHIM})
    assert result.code == 1
    assert "gaia dev docs failed" in result.output
    assert any("Class S regeneration failed" in body for body in result.comments())


def _pr_body(tmp_path, frozen):
    return run_step(_fresh(tmp_path, "pr"), _step_run(WORKFLOW_PATH, PR_STEP),
                    world(umbrella_issue(LEGACY_PAYLOAD)),
                    {"BRANCH": BRANCH, "SKILL_ID": "garrytan/gbrain", "NEW_VERSION": "v1",
                     "ISSUE_NUMBER": str(UMBRELLA), "UNRESOLVED": "0", "FROZEN": str(frozen)})


def test_pr_body_reports_the_actual_freeze_count(tmp_path):
    result = _pr_body(tmp_path, 2)
    assert result.code == 0
    assert "Froze 2 removed component(s)" in result.pr_body


def test_pr_body_says_nothing_was_frozen_when_nothing_was(tmp_path):
    result = _pr_body(tmp_path, 0)
    assert result.code == 0
    assert "No components were removed upstream" in result.pr_body
    assert "Froze " not in result.pr_body


def test_cascade_closes_only_children_whose_own_body_names_this_umbrella(tmp_path):
    umbrella = _rejected_umbrella(v2_payload(("ask-user", 5002)))
    data = world(umbrella, child_issue(5001), child_issue(5002, umbrella=9999))
    result = run_step_repo(_fresh(tmp_path, "cascade"), _step_run(CLOSE_CHILDREN_PATH, CASCADE_STEP), data,
                      {"UMBRELLA_BODY": umbrella["body"], "UMBRELLA_NUMBER": str(UMBRELLA)})
    assert result.code == 0, result.output
    assert result.closes() == ["5001"]
    assert "not #5000" in result.output


def test_a_failed_refire_is_an_error_and_leaves_a_marker_comment(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD), fail={"workflow": True})
    result = run_step_repo(_fresh(tmp_path, "refire-fail"), _step_run(CLOSE_CHILDREN_PATH, REFIRE_STEP), data,
                      {"CLOSED_ISSUE_BODY": f"Umbrella: #{UMBRELLA}", "CLOSED_ISSUE_NUMBER": "5001"})
    assert result.code == 1
    assert "::error::Could not re-fire" in result.output
    assert any("Re-fire failed" in body for body in result.comments())


def test_a_successful_refire_dispatches_the_approve_workflow(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD))
    result = run_step_repo(_fresh(tmp_path, "refire-ok"), _step_run(CLOSE_CHILDREN_PATH, REFIRE_STEP), data,
                      {"CLOSED_ISSUE_BODY": f"Umbrella: #{UMBRELLA}", "CLOSED_ISSUE_NUMBER": "5001"})
    assert result.code == 0
    assert len(result.workflow_runs()) == 1


def test_close_children_grants_actions_write_to_its_own_job_only():
    doc = yaml.safe_load(CLOSE_CHILDREN_PATH.read_text(encoding="utf-8"))
    assert doc["permissions"] == {"issues": "write"}
    assert doc["jobs"]["close-children"]["permissions"] == {
        "issues": "write", "actions": "write", "contents": "read"}


def test_watcher_workflow_drops_unused_write_scopes_and_keeps_its_schedule():
    doc = yaml.safe_load(WATCHER_PATH.read_text(encoding="utf-8"))
    assert doc["permissions"] == {"issues": "write", "contents": "read"}
    triggers = doc.get("on") or doc.get(True)
    assert triggers["schedule"] == [{"cron": "0 6 * * *"}]


# ---------------------------------------------------------------------------
# #2131 round-2 verifier FAIL (C6). H4 (every post-gate step needs success()), M1 (guard denies an
# empty index), M2 (close-children fails closed on lookups), M5 (approve re-runs push safely against
# the real remote branch), L1 (watcher args as an array), L2 (reject: no expressions in run:),
# L5 (cascade labels the children it closes). The git tests use a real bare remote.
# ---------------------------------------------------------------------------

REJECT_PATH = WORKFLOW_PATH.with_name("upstream-reject.yml")
GATE_GUARD = "steps.child_gate.outputs.gate_passed == 'true'"
BOT_LOGIN = "github-actions[bot]"
SYNC_BRANCH = "review/meta/upstream-garrytan-gbrain-v1"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "setup", "GIT_AUTHOR_EMAIL": "setup@example.com",
    "GIT_COMMITTER_NAME": "setup", "GIT_COMMITTER_EMAIL": "setup@example.com",
}


def test_every_step_after_the_child_gate_requires_success_as_well_as_the_gate():
    # H4: a step with its own if: drops the implicit success(), so a failed sync step would not stop
    # the freeze, regeneration, commit or PR steps. Each must say success() and the gate.
    steps = _load()["jobs"]["approve"]["steps"]
    names = [step.get("name") for step in steps]
    after = [step for step in steps[names.index("Check child gate") + 1:]
             if step.get("name") != "Exit if child gate failed"]
    assert len(after) >= 8, [step.get("name") for step in after]
    for step in after:
        condition = str(step.get("if", ""))
        assert "success()" in condition, step.get("name")
        assert GATE_GUARD in condition, step.get("name")


def test_guard_denies_an_empty_index_with_no_buckets(tmp_path):
    result = _guard(tmp_path, "mallory", index={"buckets": {}})
    assert result.code == 1
    assert "deny-empty-index" in result.output


def test_guard_denies_a_bucket_that_is_not_a_list_of_entries(tmp_path):
    result = _guard(tmp_path, "mallory", index={"buckets": {"stars": "oops"}})
    assert result.code == 1
    assert "deny-unparseable-index" in result.output


def test_guard_denies_an_entry_that_is_not_an_object(tmp_path):
    result = _guard(tmp_path, "mallory", index={"buckets": {"stars": ["oops"]}})
    assert result.code == 1
    assert "deny-unparseable-index" in result.output


def test_guard_still_grants_a_verifier_when_other_buckets_are_empty(tmp_path):
    index = {"buckets": {"empty": [], "stars": [{"contributor": "alice", "level": "4★"}]}}
    assert _guard(tmp_path, "alice", index=index).code == 0


# -- M2: close-children fails closed on lookup errors ----------------------------------


def test_the_refire_step_fails_closed_when_the_umbrella_state_lookup_fails(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD), fail={"issue_view": True})
    result = run_step(_fresh(tmp_path, "refire-lookup"), _step_run(CLOSE_CHILDREN_PATH, REFIRE_STEP), data,
                      {"CLOSED_ISSUE_BODY": f"Umbrella: #{UMBRELLA}", "CLOSED_ISSUE_NUMBER": "5001"})
    assert result.code == 1, result.output
    assert "::error::" in result.output
    assert result.workflow_runs() == []


def test_the_cascade_fails_closed_when_the_rejected_label_lookup_fails(tmp_path):
    umbrella = umbrella_issue(v2_payload(("ask-user", 5002)), labels=("upstream:release", "upstream:rejected"))
    data = world(umbrella, child_issue(5001), fail={"issue_view": True})
    result = run_step(_fresh(tmp_path, "cascade-lookup"), _step_run(CLOSE_CHILDREN_PATH, CASCADE_STEP), data,
                      {"UMBRELLA_BODY": umbrella["body"], "UMBRELLA_NUMBER": str(UMBRELLA)})
    assert result.code == 1, result.output
    assert result.closes() == []


# -- L5: the cascade labels what it closes ----------------------------------------------


def test_the_cascade_labels_each_child_rejected_before_it_closes_the_child(tmp_path):
    umbrella = _rejected_umbrella(v2_payload(("ask-user", 5002)))
    data = world(umbrella, child_issue(5001))
    result = run_step_repo(_fresh(tmp_path, "cascade-label"), _step_run(CLOSE_CHILDREN_PATH, CASCADE_STEP), data,
                      {"UMBRELLA_BODY": umbrella["body"], "UMBRELLA_NUMBER": str(UMBRELLA)})
    assert result.code == 0, result.output
    label_at = next(i for i, call in enumerate(result.calls)
                    if call[:3] == ["issue", "edit", "5001"] and "upstream:rejected" in call)
    close_at = next(i for i, call in enumerate(result.calls) if call[:3] == ["issue", "close", "5001"])
    assert label_at < close_at


# -- L2: no expression inside a reject run block ------------------------------------------


def test_the_reject_close_step_takes_the_issue_number_from_env(tmp_path):
    result = run_step(_fresh(tmp_path, "reject-close"), _step_run(REJECT_PATH, "Close umbrella issue"), world(),
                      {"ISSUE_NUMBER": "5000", "SENDER_LOGIN": "alice"})
    assert result.code == 0, result.output
    assert result.closes() == ["5000"]


def test_the_reject_labeler_check_removes_the_label_from_env_issue_number(tmp_path):
    repo = _fresh(tmp_path, "repo")
    (repo / "registry").mkdir()
    (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
    (repo / "registry" / "named-skills.json").write_text(json.dumps(VERIFIER_INDEX), encoding="utf-8")
    result = run_step(_fresh(tmp_path, "reject-guard"), _step_run(REJECT_PATH, "Check labeler is a Verifier"),
                      world(), {"LABELER": "mallory", "ISSUE_NUMBER": "5000", "SENDER_LOGIN": "mallory"}, cwd=repo)
    assert result.code == 1
    assert ["issue", "remove-label", "5000", "upstream:rejected"] in result.calls


# -- L1: the watcher step passes arguments as an array and validates them ----------------

WATCHER_RUN = "Run upstream watcher"
ARG_LOG_SHIM = 'printf "%s\\n" "$@" > "$SHIM_LOG"'


def _watch(tmp_path, env):
    fresh = _fresh(tmp_path, "watch")
    log = fresh / "args.txt"
    base = {"INPUT_SKILL_ID": "", "INPUT_ESCALATE": "", "INPUT_APPLY": "false",
            "EVENT_NAME": "workflow_dispatch", "SHIM_LOG": str(log), "V2_ENABLED": "true"}
    result = run_step(fresh, _step_run(WATCHER_PATH, WATCHER_RUN), world(), {**base, **env},
                      shims={"python": ARG_LOG_SHIM})
    args = log.read_text(encoding="utf-8").splitlines() if log.exists() else None
    return result, args


def test_dispatch_passes_the_skill_id_as_one_intact_argument(tmp_path):
    result, args = _watch(tmp_path, {"INPUT_SKILL_ID": "mattpocock/skills", "INPUT_APPLY": "true"})
    assert result.code == 0, result.output
    assert args == ["scripts/upstream_watcher/watcher.py", "--child-mode", "fanout", "--apply",
                    "--report", "generated-output/upstream-watcher-report.json",
                    "--skill", "mattpocock/skills"]


def test_a_skill_id_with_a_space_is_refused_before_the_watcher_runs(tmp_path):
    result, args = _watch(tmp_path, {"INPUT_SKILL_ID": "mattpocock/skills extra"})
    assert result.code == 1
    assert args is None


def test_a_skill_id_with_shell_metacharacters_is_refused(tmp_path):
    result, args = _watch(tmp_path, {"INPUT_SKILL_ID": "x;touch pwned"})
    assert result.code == 1
    assert args is None


def test_escalation_passes_exactly_one_candidate_and_exits_before_polling(tmp_path):
    result, args = _watch(tmp_path, {"INPUT_ESCALATE": "garrytan/gbrain:foo", "INPUT_APPLY": "true"})
    assert result.code == 0, result.output
    assert args == ["scripts/upstream_watcher/watcher.py", "--escalate", "garrytan/gbrain:foo", "--apply"]


def test_an_escalation_id_with_a_space_is_refused(tmp_path):
    result, args = _watch(tmp_path, {"INPUT_ESCALATE": "garrytan/gbrain:foo bar"})
    assert result.code == 1
    assert args is None


# -- M5: the approve branch step against a real remote ---------------------------------


def _git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env=env or {**os.environ, **GIT_ENV})


def _commit(repo, message, author):
    env = {**os.environ, "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": f"{author}@example.com",
           "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": f"{author}@example.com"}
    slug = re.sub(r"[^A-Za-z0-9]+", "-", message).strip("-")
    (repo / f"note-{slug}.txt").write_text(message, encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    _git(repo, "commit", "-m", message, env=env)


def _sandbox(tmp_path):
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "init", "-b", "main", str(seed))
    _commit(seed, "initial", "human")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "origin", "main")
    _git(tmp_path, "clone", str(origin), str(work))
    return origin, seed, work


def _rev(origin, ref):
    result = subprocess.run(["git", "--git-dir", str(origin), "rev-parse", "--verify", "--quiet", ref],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def _remote_sha(origin, branch):
    return _rev(origin, f"refs/heads/{branch}")


def _remote_branch(seed, branch, author):
    _git(seed, "checkout", "-B", branch, "main")
    _commit(seed, f"{branch} by {author}", author)
    _git(seed, "push", "--force", "origin", branch)
    _git(seed, "checkout", "main")


def _write_sync_change(work, with_artifacts=True):
    target = work / "registry" / "named" / "garrytan"
    target.mkdir(parents=True, exist_ok=True)
    (target / "gbrain.md").write_text("synced\n", encoding="utf-8")
    if with_artifacts:
        (work / "registry" / "gaia.json").write_text("{}\n", encoding="utf-8")
        (work / "registry" / "named-skills.json").write_text("{}\n", encoding="utf-8")
        (work / "docs" / "graph").mkdir(parents=True, exist_ok=True)
        (work / "docs" / "graph" / "gaia.json").write_text("{}\n", encoding="utf-8")


def _compare(logins, total=None):
    return {
        "total_commits": len(logins) if total is None else total,
        "commits": [{"author": {"login": login}, "committer": {"login": login},
                     "commit": {"author": {"name": login}}} for login in logins],
    }


def _branch_step(tmp_path, work, logins=None, name="branch"):
    data = world(compare=_compare(logins)) if logins is not None else world()
    return run_step(_fresh(tmp_path, name), _step_run(WORKFLOW_PATH, "Create sync branch"), data,
                    {"SKILL_ID": "garrytan/gbrain", "NEW_VERSION": "v1"}, cwd=work)


def _push_step(tmp_path, work, remote_sha, name="push"):
    env = {"BRANCH": SYNC_BRANCH, "NEW_VERSION": "v1", "SKILL_ID": "garrytan/gbrain",
           "REMOTE_SHA": remote_sha, **GIT_ENV}
    return run_step(_fresh(tmp_path, name), _step_run(WORKFLOW_PATH, "Commit and push"), world(), env, cwd=work)


def test_the_first_run_pushes_the_sync_branch_when_none_exists(tmp_path):
    origin, _seed, work = _sandbox(tmp_path)
    _write_sync_change(work)
    branch = _branch_step(tmp_path, work)
    assert branch.code == 0, branch.output
    push = _push_step(tmp_path, work, branch.outputs.get("remote_sha", ""))
    assert push.code == 0, push.output
    assert _remote_sha(origin, SYNC_BRANCH)


def test_an_absent_optional_artifact_path_does_not_cancel_the_commit(tmp_path):
    # docs/graph is not generated for every sync. One missing pathspec must not make git add stage nothing
    # and the step report "No changes to commit" with exit 0 (the branch is then never pushed).
    origin, _seed, work = _sandbox(tmp_path)
    _write_sync_change(work, with_artifacts=False)
    branch = _branch_step(tmp_path, work)
    assert branch.code == 0, branch.output
    push = _push_step(tmp_path, work, branch.outputs.get("remote_sha", ""))
    assert push.code == 0, push.output
    assert "No changes to commit" not in push.output
    assert _remote_sha(origin, SYNC_BRANCH)


def test_a_rerun_replaces_only_the_bots_own_sync_commit_under_a_lease(tmp_path):
    origin, seed, work = _sandbox(tmp_path)
    _remote_branch(seed, SYNC_BRANCH, BOT_LOGIN)
    before = _remote_sha(origin, SYNC_BRANCH)
    _write_sync_change(work)

    branch = _branch_step(tmp_path, work, logins=[BOT_LOGIN])
    assert branch.code == 0, branch.output
    assert branch.outputs.get("remote_sha") == before
    push = _push_step(tmp_path, work, branch.outputs.get("remote_sha", ""))

    assert push.code == 0, push.output
    after = _remote_sha(origin, SYNC_BRANCH)
    assert after and after != before
    assert _rev(origin, f"{after}^") == _rev(origin, "refs/heads/main"), "the sync commit must sit on main"


def test_a_branch_with_a_human_commit_is_refused_before_anything_is_synced(tmp_path):
    origin, seed, work = _sandbox(tmp_path)
    _remote_branch(seed, SYNC_BRANCH, "alice")
    before = _remote_sha(origin, SYNC_BRANCH)

    branch = _branch_step(tmp_path, work, logins=["alice"])

    assert branch.code == 1, branch.output
    assert "unrelated" in branch.output
    assert _remote_sha(origin, SYNC_BRANCH) == before


def test_a_branch_whose_commit_list_is_incomplete_is_refused(tmp_path):
    origin, seed, work = _sandbox(tmp_path)
    _remote_branch(seed, SYNC_BRANCH, BOT_LOGIN)
    before = _remote_sha(origin, SYNC_BRANCH)

    branch = run_step(_fresh(tmp_path, "branch-partial"), _step_run(WORKFLOW_PATH, "Create sync branch"),
                      world(compare=_compare([BOT_LOGIN], total=3)),
                      {"SKILL_ID": "garrytan/gbrain", "NEW_VERSION": "v1"}, cwd=work)

    assert branch.code == 1, branch.output
    assert _remote_sha(origin, SYNC_BRANCH) == before


def test_a_push_against_a_moved_remote_is_refused_and_leaves_the_remote_alone(tmp_path):
    origin, seed, work = _sandbox(tmp_path)
    _remote_branch(seed, SYNC_BRANCH, BOT_LOGIN)
    before = _remote_sha(origin, SYNC_BRANCH)
    _write_sync_change(work)
    branch = _branch_step(tmp_path, work, logins=[BOT_LOGIN])
    assert branch.code == 0, branch.output

    push = _push_step(tmp_path, work, "1234567890abcdef1234567890abcdef12345678")

    assert push.code != 0
    assert _remote_sha(origin, SYNC_BRANCH) == before


def test_an_open_draft_pr_for_the_branch_is_reused_and_not_recreated(tmp_path):
    data = world(pr_list=[{"url": "https://github.com/gaia-research/gaia-skill-tree/pull/42"}])
    result = run_step(_fresh(tmp_path, "pr-reuse"), _step_run(WORKFLOW_PATH, PR_STEP), data, {
        "BRANCH": SYNC_BRANCH, "SKILL_ID": "garrytan/gbrain", "NEW_VERSION": "v1",
        "ISSUE_NUMBER": str(UMBRELLA), "UNRESOLVED": "0", "FROZEN": "0",
    })
    assert result.code == 0, result.output
    assert result.outputs["created"] == "false" and result.outputs["pr_number"] == "42"
    assert not any(call[:2] == ["pr", "create"] for call in result.calls)


def test_a_failed_draft_pr_lookup_fails_closed_and_creates_nothing(tmp_path):
    data = world(fail={"pr_list": True})
    result = run_step(_fresh(tmp_path, "pr-lookup"), _step_run(WORKFLOW_PATH, PR_STEP), data, {
        "BRANCH": SYNC_BRANCH, "SKILL_ID": "garrytan/gbrain", "NEW_VERSION": "v1",
        "ISSUE_NUMBER": str(UMBRELLA), "UNRESOLVED": "0", "FROZEN": "0",
    })
    assert result.code != 0
    assert not any(call[:2] == ["pr", "create"] for call in result.calls)


def test_a_failed_comment_lookup_on_the_umbrella_fails_closed_and_posts_nothing(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD), fail={"issue_view": True})
    result = run_step(_fresh(tmp_path, "comment-lookup"), _step_run(WORKFLOW_PATH, "Comment PR link on umbrella"),
                      data, {"ISSUE_NUMBER": str(UMBRELLA), "NEW_VERSION": "v1", "PR_NUMBER": "42",
                             "PR_URL": "https://github.com/gaia-research/gaia-skill-tree/pull/42",
                             "UNRESOLVED": "0"})
    assert result.code != 0
    assert result.comments() == []


# ---------------------------------------------------------------------------
# #2131 round-3 verifier FAIL (C7). D1 (extract recomputes the digest and the approval marker covers it),
# D2 (reject guard fails closed like approve), D3 (a bot re-fire needs refire=true and a Verifier labeler),
# D5 (branch reuse needs the bot as author AND committer), D6 (re-verify before sync), D7 (a '-->' inside
# the JSON does not end the payload). Each run block runs under bash with the fake gh.
# ---------------------------------------------------------------------------

try:  # the shared module the workflows import; absent before the C7 change, so tests fail individually
    from scripts.upstream_watcher import approval
except ImportError:  # pragma: no cover - exercised only on the pre-fix tree
    approval = None

EXTRACT = "Extract payload from issue body"
APPROVAL_STEP = "Check approval covers this payload"
REVERIFY_STEP = "Re-verify approval before sync"
REJECT_GUARD = "Check labeler is a Verifier"
REJECT_BUILD = "Build the base named-skills index"
VERIFIER = {"alice"}  # the Verifier in VERIFIER_INDEX


def _signed_body(payload):
    """A umbrella body whose payload block carries the digest the watcher writes."""
    stored = dict(payload)
    stored["payloadSha256"] = approval.canonical_hash(stored)
    return "## Upstream release detected\n\n<!-- gaia-upstream-payload\n" + json.dumps(stored, indent=2) + "\n-->\n"


def _issue_with_body(body, labels=("upstream:release", "upstream:approved")):
    row = umbrella_issue(LEGACY_PAYLOAD, labels=labels)
    row["body"] = body
    return row


SIGNED = {"payloadVersion": 2, "skillId": "garrytan/gbrain", "previousVersion": "v0", "newVersion": "v1",
          "releasedAt": "2026-10-21T00:00:00Z", "sourceUrl": "https://github.com/garrytan/gbrain/releases/tag/v1",
          "mode": "components", "componentAdds": ["ask-user"], "componentRemoves": [], "linkLiveness": [],
          "nameDrift": [], "candidates": []}


def _extract(tmp_path, body, extra_world=None, event="issues", env_extra=None):
    data = world(_issue_with_body(body), **(extra_world or {}))
    env = {"ISSUE_NUMBER": str(UMBRELLA), "EVENT_NAME": event, "RUNNER_TEMP": str(tmp_path / "rt")}
    env.update(env_extra or {})
    _fresh(tmp_path, "rt")
    return run_step(tmp_path, _step_run(WORKFLOW_PATH, EXTRACT), data, env, cwd=REPO_ROOT)


# -- D1: extract recomputes the digest --------------------------------------------------


def test_extract_accepts_a_payload_whose_stored_digest_matches_its_content(tmp_path):
    result = _extract(tmp_path, _signed_body(SIGNED))
    assert result.code == 0, result.output
    assert result.outputs["payload_sha256"] == approval.canonical_hash(SIGNED)


def test_extract_refuses_a_componentRemoves_edit_that_keeps_the_stale_stored_digest(tmp_path):
    body = _signed_body(SIGNED).replace('"componentRemoves": []', '"componentRemoves": [\n    "ghost-skill"\n  ]')
    assert '"ghost-skill"' in body
    result = _extract(tmp_path, body)
    assert result.code == 1, result.output
    assert "payload" not in result.outputs
    assert any("does not match" in text for text in result.comments())


def test_extract_refuses_a_newVersion_edit_that_keeps_the_stale_stored_digest(tmp_path):
    body = _signed_body(SIGNED).replace('"newVersion": "v1"', '"newVersion": "v9-forged"')
    assert "v9-forged" in body
    result = _extract(tmp_path, body)
    assert result.code == 1, result.output
    assert "payload" not in result.outputs


def test_extract_reads_a_payload_whose_json_contains_the_terminator_text(tmp_path):
    # D7: '-->' inside a string used to end the block early, so the payload failed to parse.
    payload = {**SIGNED, "componentAdds": ["ask-user-->x"]}
    result = _extract(tmp_path, _signed_body(payload))
    assert result.code == 0, result.output
    assert json.loads(result.outputs["payload"])["componentAdds"] == ["ask-user-->x"]


def test_extract_still_reads_a_legacy_payload_that_has_no_stored_digest(tmp_path):
    result = _extract(tmp_path, umbrella_issue(LEGACY_PAYLOAD)["body"])
    assert result.code == 0, result.output
    assert result.outputs["skill_id"] == "garrytan/gbrain"


# -- D1: the approval marker -------------------------------------------------------------


def _marker_run(tmp_path, event, sha, comment_rows=None, env_extra=None):
    data = world(umbrella_issue(LEGACY_PAYLOAD), comment_rows={str(UMBRELLA): comment_rows or []})
    env = {"EVENT_NAME": event, "ISSUE_NUMBER": str(UMBRELLA), "PAYLOAD_SHA": sha,
           "EVENT_BODY": _body_of(SIGNED)}
    env.update(env_extra or {})
    return run_step(_fresh(tmp_path, "marker"), _step_run(WORKFLOW_PATH, APPROVAL_STEP), data, env, cwd=REPO_ROOT)


def _bot_marker(sha, comment_id=1):
    return {"id": comment_id, "body": approval.approval_marker(sha),
            "user": {"login": BOT_LOGIN, "type": "Bot"}}


def test_a_labeled_approval_records_the_marker_for_the_payload_it_covers(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    result = _marker_run(tmp_path, "issues", sha)
    assert result.code == 0, result.output
    posted = [body for body in result.comments() if approval.approval_marker(sha) in body]
    assert len(posted) == 1


def test_a_labeled_approval_for_an_already_recorded_payload_posts_nothing_new(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    result = _marker_run(tmp_path, "issues", sha, comment_rows=[_bot_marker(sha)])
    assert result.code == 0, result.output
    assert result.comments() == []


def test_a_dispatch_refuses_a_payload_that_no_approval_covers(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    result = _marker_run(tmp_path, "workflow_dispatch", sha, comment_rows=[_bot_marker("0" * 64)])
    assert result.code == 1, result.output
    assert any("does not cover" in text for text in result.comments())


def test_a_dispatch_accepts_the_payload_the_bot_marker_covers(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    result = _marker_run(tmp_path, "workflow_dispatch", sha, comment_rows=[_bot_marker(sha)])
    assert result.code == 0, result.output


def test_a_marker_written_by_a_human_is_not_an_approval(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    human = {"id": 2, "body": approval.approval_marker(sha), "user": {"login": "mallory", "type": "User"}}
    result = _marker_run(tmp_path, "workflow_dispatch", sha, comment_rows=[human])
    assert result.code == 1, result.output


# -- D6: re-verify the approval and the payload immediately before the sync -------------


def _reverify(tmp_path, issue, sha, comment_rows):
    data = world(issue, comment_rows={str(UMBRELLA): comment_rows})
    return run_step(_fresh(tmp_path, "reverify"), _step_run(WORKFLOW_PATH, REVERIFY_STEP), data,
                    {"ISSUE_NUMBER": str(UMBRELLA), "PAYLOAD_SHA": sha}, cwd=REPO_ROOT)


def test_reverify_passes_an_open_approved_umbrella_whose_payload_is_the_approved_one(tmp_path):
    issue = _issue_with_body(_signed_body(SIGNED))
    sha = approval.canonical_hash(SIGNED)
    assert _reverify(tmp_path, issue, sha, [_bot_marker(sha)]).code == 0


def test_reverify_refuses_a_payload_edited_after_extraction(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    edited = _signed_body(SIGNED).replace('"newVersion": "v1"', '"newVersion": "v2"')
    result = _reverify(tmp_path, _issue_with_body(edited), sha, [_bot_marker(sha)])
    assert result.code == 1, result.output


def test_reverify_refuses_a_closed_umbrella(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    issue = {**_issue_with_body(_signed_body(SIGNED)), "state": "closed"}
    result = _reverify(tmp_path, issue, sha, [_bot_marker(sha)])
    assert result.code == 1 and "not open" in result.output


def test_reverify_refuses_an_umbrella_whose_approval_was_withdrawn(tmp_path):
    sha = approval.canonical_hash(SIGNED)
    issue = _issue_with_body(_signed_body(SIGNED), labels=("upstream:release",))
    result = _reverify(tmp_path, issue, sha, [_bot_marker(sha)])
    assert result.code == 1 and "upstream:approved" in result.output


def test_reverify_is_ordered_after_the_unresolved_count_and_before_the_branch():
    names = _step_names(_load()["jobs"]["approve"]["steps"])
    assert names.index("Count unresolved candidate rows") < names.index(REVERIFY_STEP) < names.index("Create sync branch")
    run = _step_run(WORKFLOW_PATH, REVERIFY_STEP)
    assert "from scripts.upstream_watcher.approval import" in run


def test_the_approval_marker_step_runs_before_the_child_gate_so_a_blocked_approval_is_still_recorded():
    names = _step_names(_load()["jobs"]["approve"]["steps"])
    assert names.index(EXTRACT) < names.index(APPROVAL_STEP) < names.index("Check child gate")


# -- D3: the approve guard and a bot re-fire ---------------------------------------------

BOT_ACTOR = "github-actions[bot]"


def _guard_run(tmp_path, *, event, actor, labels_events=None, refire="", index=VERIFIER_INDEX, fail=None, issue=None):
    scratch = pathlib.Path(tempfile.mkdtemp(dir=tmp_path))
    repo = _fresh(scratch, "repo")
    (repo / "registry").mkdir()
    (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
    if index is not None:
        text = index if isinstance(index, str) else json.dumps(index)
        (repo / "registry" / "named-skills.json").write_text(text, encoding="utf-8")
    data = world(issue or umbrella_issue(LEGACY_PAYLOAD), events={str(UMBRELLA): labels_events or []}, fail=fail or {})
    actor_type = "Bot" if actor.endswith("[bot]") else "User"
    env = {"LABELER": actor, "LABELER_TYPE": actor_type, "LABELER_ID": "1", "ISSUE_NUMBER": str(UMBRELLA),
           "EVENT_NAME": event, "INPUT_REFIRE": refire}
    return run_step(_fresh(scratch, "guard-run"), _step_run(WORKFLOW_PATH, GUARD), data, env, cwd=repo)


def _labeled(event_id, actor, label="upstream:approved"):
    # The issue-events actor carries its type and id (M2). The known human handle has its real id.
    actor_id = 153011150 if actor == "mbtiongson1" else 1
    actor_type = "Bot" if actor.endswith("[bot]") else "User"
    return {"id": event_id, "event": "labeled", "label": {"name": label},
            "actor": {"login": actor, "type": actor_type, "id": actor_id}}


def test_guard_labeled_by_a_verifier_passes(tmp_path):
    assert _guard_run(tmp_path, event="issues", actor="alice").code == 0


def test_guard_labeled_by_a_non_verifier_is_refused(tmp_path):
    result = _guard_run(tmp_path, event="issues", actor="mallory")
    assert result.code == 1 and "does not hold a 4★+" in result.comments()[0]


def test_guard_labeled_by_an_allowlisted_bot_keeps_its_existing_treatment(tmp_path):
    assert _guard_run(tmp_path, event="issues", actor=BOT_ACTOR).code == 0


def test_guard_bot_redispatch_without_refire_true_is_refused_even_for_a_verifier_label(tmp_path):
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="",
                        labels_events=[_labeled(5, "alice")])
    assert result.code == 1, result.output
    assert any("refire" in text for text in result.comments())


def test_guard_bot_redispatch_with_refire_passes_when_the_latest_labeler_is_a_verifier(tmp_path):
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true",
                        labels_events=[_labeled(5, "alice")])
    assert result.code == 0, result.output


def test_guard_bot_redispatch_is_refused_when_the_latest_labeler_is_not_a_verifier(tmp_path):
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true",
                        labels_events=[_labeled(5, "mallory")])
    assert result.code == 1, result.output


def test_guard_bot_redispatch_reads_the_most_recent_labeling_not_an_earlier_one(tmp_path):
    events = [_labeled(3, "alice"), _labeled(9, "mallory")]
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true",
                        labels_events=events)
    assert result.code == 1, "the verifier labeled first, but the most recent label was not a verifier's"


def test_guard_bot_redispatch_ignores_label_events_for_other_labels(tmp_path):
    events = [_labeled(3, "alice"), _labeled(9, "mallory", label="skip-child-gate")]
    assert _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true",
                      labels_events=events).code == 0


def test_guard_bot_redispatch_fails_closed_when_the_events_cannot_be_read(tmp_path):
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true",
                        labels_events=[_labeled(5, "alice")], fail={"events": True})
    assert result.code == 1, result.output


def test_guard_bot_redispatch_with_no_labeling_event_is_refused(tmp_path):
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true", labels_events=[])
    assert result.code == 1, result.output


def test_guard_bot_redispatch_accepts_the_human_allowlist_handle_as_labeler(tmp_path):
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true",
                        labels_events=[_labeled(5, "mbtiongson1")])
    assert result.code == 0, result.output


def test_guard_bot_redispatch_is_refused_when_the_index_is_missing(tmp_path):
    result = _guard_run(tmp_path, event="workflow_dispatch", actor=BOT_ACTOR, refire="true",
                        labels_events=[_labeled(5, "alice")], index=None)
    assert result.code == 1, result.output


def test_guard_human_redispatch_still_needs_a_verifier_actor(tmp_path):
    assert _guard_run(tmp_path, event="workflow_dispatch", actor="alice").code == 0
    assert _guard_run(tmp_path, event="workflow_dispatch", actor="mallory").code == 1


def test_unrelated_issue_dispatch_by_unauthorized_actor_makes_no_writes(tmp_path):
    unrelated = {
        "number": UMBRELLA, "title": "Unrelated issue", "state": "open",
        "labels": [{"name": "upstream:approved"}], "body": "not an upstream watcher issue",
    }
    result = _guard_run(tmp_path, event="workflow_dispatch", actor="mallory", issue=unrelated)
    assert result.code == 0, result.output
    assert not result.comments()
    assert not any(call[:2] == ["issue", "remove-label"] or call[:2] == ["issue", "edit"]
                   for call in result.calls)
    assert any(call[:3] == ["issue", "view", str(UMBRELLA)] for call in result.calls)


def test_staged_close_children_dispatch_checks_out_trusted_main_not_dispatch_ref():
    doc = yaml.safe_load(CLOSE_CHILDREN_PATH.read_text(encoding="utf-8"))
    checkout = doc["jobs"]["close-children"]["steps"][0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"]["ref"] == "main"
    assert checkout["with"]["fetch-depth"] == 1


def test_close_children_refire_names_refire_true_so_the_guard_can_check_the_labeler():
    text = CLOSE_CHILDREN_PATH.read_text(encoding="utf-8")
    assert "-f issue_number=\"$UMBRELLA_NUMBER\" -f refire=true" in text


def test_approve_workflow_declares_the_refire_input_as_a_string_default_false():
    doc = _load()
    triggers = doc.get("on") or doc.get(True)
    assert triggers["workflow_dispatch"]["inputs"]["refire"]["default"] == "false"


# -- D2: the reject guard fails closed on a missing, empty or unparseable index ----------


def _reject_guard(tmp_path, actor, index=None):
    scratch = pathlib.Path(tempfile.mkdtemp(dir=tmp_path))
    repo = _fresh(scratch, "repo")
    (repo / "registry").mkdir()
    (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
    if index is not None:
        text = index if isinstance(index, str) else json.dumps(index)
        (repo / "registry" / "named-skills.json").write_text(text, encoding="utf-8")
    return run_step(_fresh(scratch, "reject-run"), _step_run(REJECT_PATH, REJECT_GUARD), world(),
                    {"LABELER": actor, "ISSUE_NUMBER": "5000", "SENDER_LOGIN": actor}, cwd=repo)


def test_reject_guard_denies_a_missing_index_and_removes_the_label(tmp_path):
    result = _reject_guard(tmp_path, "mallory", index=None)
    assert result.code == 1
    assert ["issue", "remove-label", "5000", "upstream:rejected"] in result.calls


def test_reject_guard_denies_an_unparseable_index(tmp_path):
    result = _reject_guard(tmp_path, "mallory", index="{not json")
    assert result.code == 1 and ["issue", "remove-label", "5000", "upstream:rejected"] in result.calls


def test_reject_guard_denies_an_empty_index_instead_of_bootstrapping(tmp_path):
    result = _reject_guard(tmp_path, "mallory", index={"buckets": {}})
    assert result.code == 1 and ["issue", "remove-label", "5000", "upstream:rejected"] in result.calls


def test_reject_guard_denies_a_bucket_that_is_not_a_list_of_entries(tmp_path):
    result = _reject_guard(tmp_path, "mallory", index={"buckets": {"stars": "oops"}})
    assert result.code == 1


def test_reject_guard_grants_a_verifier_and_refuses_a_non_verifier(tmp_path):
    assert _reject_guard(_fresh(tmp_path, "a"), "alice", index=VERIFIER_INDEX).code == 0
    assert _reject_guard(_fresh(tmp_path, "b"), "mallory", index=VERIFIER_INDEX).code == 1


def test_reject_guard_denies_a_parseable_index_with_no_verifier_because_bootstrap_is_gone(tmp_path):
    # M1: no bootstrap grant in the reject guard either.
    assert _reject_guard(tmp_path, "mallory", index=NO_VERIFIER_INDEX).code == 1


def test_reject_workflow_builds_the_index_before_its_guard():
    doc = yaml.safe_load(REJECT_PATH.read_text(encoding="utf-8"))
    names = _step_names(doc["jobs"]["reject"]["steps"])
    assert names.index(REJECT_BUILD) < names.index(REJECT_GUARD)
    build = _step_run(REJECT_PATH, REJECT_BUILD)
    assert "scripts/assemble_gaia.py" in build and "scripts/generateNamedIndex.py" in build


# -- D5: a reused branch must be the bot's own work as author AND committer -------------


def _branch_with(tmp_path, compare):
    origin, seed, work = _sandbox(tmp_path)
    _remote_branch(seed, SYNC_BRANCH, BOT_LOGIN)
    before = _remote_sha(origin, SYNC_BRANCH)
    result = run_step(_fresh(tmp_path, "branch-d5"), _step_run(WORKFLOW_PATH, "Create sync branch"),
                      world(compare=compare), {"SKILL_ID": "garrytan/gbrain", "NEW_VERSION": "v1"}, cwd=work)
    return result, origin, before


def test_a_branch_commit_with_a_null_author_is_refused_even_when_its_name_is_the_bot(tmp_path):
    compare = {"total_commits": 1, "commits": [{"author": None, "committer": {"login": BOT_LOGIN},
                                                 "commit": {"author": {"name": BOT_LOGIN}}}]}
    result, origin, before = _branch_with(tmp_path, compare)
    assert result.code == 1 and "unrelated" in result.output
    assert _remote_sha(origin, SYNC_BRANCH) == before


def test_a_branch_commit_whose_committer_is_not_the_bot_is_refused(tmp_path):
    compare = {"total_commits": 1, "commits": [{"author": {"login": BOT_LOGIN}, "committer": {"login": "mallory"},
                                                 "commit": {"author": {"name": BOT_LOGIN}}}]}
    result, _origin, _before = _branch_with(tmp_path, compare)
    assert result.code == 1 and "unrelated" in result.output


def test_a_branch_commit_with_no_committer_object_is_refused(tmp_path):
    compare = {"total_commits": 1, "commits": [{"author": {"login": BOT_LOGIN}, "committer": None,
                                                 "commit": {"author": {"name": BOT_LOGIN}}}]}
    result, _origin, _before = _branch_with(tmp_path, compare)
    assert result.code == 1


# ---------------------------------------------------------------------------
# #2131 round-4 verifier FAIL (C8): H1 (TOCTOU), L1, L5, M1, M2 and M6 at the workflow level.
# Each step runs under bash with the fake gh, as the other tests here do.
# ---------------------------------------------------------------------------

SKIP_JOB = "skip-child-gate-guard"
SKIP_STEP = "Check skip-child-gate labeler"
REJECT_GUARD = "Check labeler is a Verifier"
NO_TYPE = {"LABELER_TYPE": "", "LABELER_ID": ""}


def _signed(payload):
    from scripts.upstream_watcher.approval import canonical_hash

    payload = dict(payload)
    payload["payloadSha256"] = canonical_hash(payload)
    return payload


def _body_of(payload):
    return "## Upstream release detected\n\n<!-- gaia-upstream-payload\n" + json.dumps(payload) + "\n-->\n"


def _v2(version):
    return _signed({"payloadVersion": 2, "skillId": "garrytan/gbrain", "previousVersion": "v0",
                    "newVersion": version, "componentAdds": ["ask-user"], "componentRemoves": [],
                    "linkLiveness": [], "nameDrift": [], "candidates": []})


def _approval_run(tmp_path, *, event_body, live_body, event_name="issues", comment_rows=None):
    from scripts.upstream_watcher.approval import extract_payload

    _payload, live_sha = extract_payload(live_body)
    data = {"issues": {str(UMBRELLA): {"number": UMBRELLA, "title": "t", "state": "open", "labels": [],
                                       "body": live_body}},
            "comment_rows": {str(UMBRELLA): comment_rows or []}}
    env = {"EVENT_NAME": event_name, "EVENT_BODY": event_body, "PAYLOAD_SHA": live_sha,
           "ISSUE_NUMBER": str(UMBRELLA)}
    return run_step(_fresh(tmp_path, "approval"), _step_run(WORKFLOW_PATH, APPROVAL_STEP), data, env,
                    cwd=REPO_ROOT)


# H1: the approval marker covers the body the Verifier labelled, not the body read at extract time.


def test_h1_probe_event_body_v1_and_live_body_v2_is_refused_with_no_marker(tmp_path):
    v1, v2 = _body_of(_v2("v1")), _body_of(_v2("v2"))
    result = _approval_run(tmp_path, event_body=v1, live_body=v2)
    assert result.code == 1, result.output
    assert any("payload changed after approval; re-apply the label" in text for text in result.comments())
    assert not any("gaia-upstream-approval payload=" in text for text in result.comments()), \
        "no marker may be minted for a body the Verifier did not label"


def test_h1_the_labelled_body_matches_the_live_body_so_the_marker_is_minted(tmp_path):
    body = _body_of(_v2("v2"))
    result = _approval_run(tmp_path, event_body=body, live_body=body)
    assert result.code == 0, result.output
    assert any("gaia-upstream-approval payload=" in text for text in result.comments())


def test_h1_an_event_body_with_no_payload_is_refused(tmp_path):
    result = _approval_run(tmp_path, event_body="no payload here", live_body=_body_of(_v2("v2")))
    assert result.code == 1
    assert any("payload changed after approval" in text for text in result.comments())


def test_h1_a_dispatch_still_reads_the_recorded_marker_and_ignores_the_event_body(tmp_path):
    body = _body_of(_v2("v2"))
    result = _approval_run(tmp_path, event_body="ignored", live_body=body, event_name="workflow_dispatch")
    assert result.code == 1
    assert any("does not cover this payload" in text for text in result.comments())


def test_h1_the_event_body_reaches_the_step_through_env_only():
    step = next(s for s in _load()["jobs"]["approve"]["steps"] if s.get("name") == APPROVAL_STEP)
    assert step["env"]["EVENT_BODY"] == "${{ github.event.issue.body }}"
    assert "${{" not in step["run"]


# L1: a denied approval removes upstream:approved, as reject does.


def test_l1_a_denied_labeler_loses_the_approval_label(tmp_path):
    result = _guard(tmp_path, "mallory", index=VERIFIER_INDEX)
    assert result.code == 1
    assert ["issue", "edit", str(UMBRELLA), "--remove-label", "upstream:approved"] in result.calls


def test_l1_a_missing_index_denial_also_removes_the_label(tmp_path):
    result = _guard(tmp_path, "mallory", index=None)
    assert result.code == 1
    assert ["issue", "edit", str(UMBRELLA), "--remove-label", "upstream:approved"] in result.calls


# M1: no bootstrap in either guard.


def test_m1_a_parseable_index_with_no_verifier_denies_the_labeler(tmp_path):
    result = _guard(tmp_path, "mallory", index=NO_VERIFIER_INDEX)
    assert result.code == 1
    assert "does not hold a 4★+ named skill" in result.comments()[0]


def test_m1_the_reject_guard_denies_a_parseable_index_with_no_verifier(tmp_path):
    repo = _repo_with_index(tmp_path, NO_VERIFIER_INDEX)
    result = run_step(_fresh(tmp_path, "rj"), _step_run(REJECT_PATH, REJECT_GUARD), world(),
                      {"LABELER": "mallory", "LABELER_TYPE": "User", "LABELER_ID": "2",
                       "ISSUE_NUMBER": str(UMBRELLA), "SENDER_LOGIN": "mallory"}, cwd=repo)
    assert result.code == 1, result.output
    assert "bootstrap" not in result.output


# M2: the allowlist needs the sender type. A human account named codex is not a bot.


def test_m2_a_human_account_named_codex_is_refused_and_loses_the_label(tmp_path):
    result = _guard(tmp_path, "codex", index=VERIFIER_INDEX, actor_type="User", actor_id="99")
    assert result.code == 1
    assert "does not hold a 4★+" in result.comments()[0]
    assert ["issue", "edit", str(UMBRELLA), "--remove-label", "upstream:approved"] in result.calls


def test_m2_the_codex_bot_is_still_allowlisted(tmp_path):
    assert _guard(tmp_path, "codex", index=None, actor_type="Bot", actor_id="7").code == 0


def test_m2_the_bot_suffix_needs_a_bot_sender(tmp_path):
    assert _guard(tmp_path, BOT_ACTOR, index=None, actor_type="User", actor_id="8").code == 1


def test_m2_the_human_handle_needs_its_user_type_and_known_id(tmp_path):
    assert _guard(_fresh(tmp_path, "ok"), "mbtiongson1", index=None,
                  actor_type="User", actor_id="153011150").code == 0
    assert _guard(_fresh(tmp_path, "wrong-id"), "mbtiongson1", index=None,
                  actor_type="User", actor_id="1").code == 1
    assert _guard(_fresh(tmp_path, "wrong-type"), "mbtiongson1", index=None,
                  actor_type="Bot", actor_id="153011150").code == 1


def test_m2_reject_refuses_a_human_named_codex_and_removes_the_label(tmp_path):
    repo = _repo_with_index(tmp_path, VERIFIER_INDEX)
    result = run_step(_fresh(tmp_path, "rj2"), _step_run(REJECT_PATH, REJECT_GUARD), world(),
                      {"LABELER": "codex", "LABELER_TYPE": "User", "LABELER_ID": "99",
                       "ISSUE_NUMBER": str(UMBRELLA), "SENDER_LOGIN": "codex"}, cwd=repo)
    assert result.code == 1
    assert ["issue", "remove-label", str(UMBRELLA), "upstream:rejected"] in result.calls


def test_m2_reject_accepts_the_codex_bot(tmp_path):
    result = run_step(_fresh(tmp_path, "rj3"), _step_run(REJECT_PATH, REJECT_GUARD), world(),
                      {"LABELER": "codex", "LABELER_TYPE": "Bot", "LABELER_ID": "7",
                       "ISSUE_NUMBER": str(UMBRELLA), "SENDER_LOGIN": "codex"}, cwd=REPO_ROOT)
    assert result.code == 0, result.output


def _repo_with_index(tmp_path, index):
    repo = _fresh(tmp_path, "repo")
    (repo / "registry").mkdir()
    (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
    text = index if isinstance(index, str) else json.dumps(index)
    (repo / "registry" / "named-skills.json").write_text(text, encoding="utf-8")
    return repo


# L5: skip-child-gate is gated by its own labeler check, and the child gate ignores an unauthorized one.


def _job_step_run(path, job, name):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return next(step["run"] for step in doc["jobs"][job]["steps"] if step.get("name") == name)


def test_l5_a_job_runs_the_labeler_check_when_skip_child_gate_is_applied():
    doc = _load()
    assert SKIP_JOB in doc["jobs"]
    condition = str(doc["jobs"][SKIP_JOB]["if"])
    assert "labeled" in condition and "skip-child-gate" in condition


def test_l5_a_non_verifier_applying_skip_child_gate_loses_the_label_with_a_comment(tmp_path):
    repo = _repo_with_index(tmp_path, VERIFIER_INDEX)
    result = run_step(_fresh(tmp_path, "skip-deny"), _job_step_run(WORKFLOW_PATH, SKIP_JOB, SKIP_STEP), world(umbrella_issue(LEGACY_PAYLOAD)),
                      {"LABELER": "mallory", "LABELER_TYPE": "User", "LABELER_ID": "2",
                       "ISSUE_NUMBER": str(UMBRELLA), "SENDER_LOGIN": "mallory"}, cwd=repo)
    assert result.code == 1, result.output
    assert ["issue", "edit", str(UMBRELLA), "--remove-label", "skip-child-gate"] in result.calls
    assert result.comments()


def test_l5_a_verifier_applying_skip_child_gate_keeps_it(tmp_path):
    repo = _repo_with_index(tmp_path, VERIFIER_INDEX)
    result = run_step(_fresh(tmp_path, "skip-ok"), _job_step_run(WORKFLOW_PATH, SKIP_JOB, SKIP_STEP), world(umbrella_issue(LEGACY_PAYLOAD)),
                      {"LABELER": "alice", "LABELER_TYPE": "User", "LABELER_ID": "1",
                       "ISSUE_NUMBER": str(UMBRELLA), "SENDER_LOGIN": "alice"}, cwd=repo)
    assert result.code == 0, result.output
    assert not any(call[:3] == ["issue", "edit", str(UMBRELLA)] for call in result.calls)


def _gate_in_repo(tmp_path, world_data, index=VERIFIER_INDEX):
    repo = _repo_with_index(tmp_path, index) if index is not None else _fresh(tmp_path, "norepo")
    return run_step(_fresh(tmp_path, "gate"), _step_run(WORKFLOW_PATH, "Check child gate"), world_data,
                    {"ISSUE_NUMBER": str(UMBRELLA)}, cwd=repo)


def test_l5_the_child_gate_ignores_a_skip_label_applied_by_a_non_verifier(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD, extra=("skip-child-gate",)), child_issue(5001),
                 events={str(UMBRELLA): [_labeled(7, "mallory", label="skip-child-gate")]})
    result = _gate_in_repo(tmp_path, data)
    assert result.outputs == {"gate_passed": "false"}, result.output
    assert any("Cannot sync yet" in text for text in result.comments())


def test_l5_the_child_gate_ignores_a_skip_label_with_no_labeling_event(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD, extra=("skip-child-gate",)), child_issue(5001))
    assert _gate_in_repo(tmp_path, data).outputs == {"gate_passed": "false"}


def test_l5_the_child_gate_honours_a_skip_label_applied_by_a_verifier(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD, extra=("skip-child-gate",)), child_issue(5001),
                 events={str(UMBRELLA): [_labeled(7, "alice", label="skip-child-gate")]})
    result = _gate_in_repo(tmp_path, data)
    assert result.code == 0 and result.outputs == {"gate_passed": "true"}, result.output


def test_l5_the_child_gate_fails_closed_when_the_labeling_history_cannot_be_read(tmp_path):
    data = world(umbrella_issue(LEGACY_PAYLOAD, extra=("skip-child-gate",)), child_issue(5001),
                 events={str(UMBRELLA): [_labeled(7, "alice", label="skip-child-gate")]}, fail={"events": True})
    result = _gate_in_repo(tmp_path, data)
    assert result.code != 0 and "gate_passed" not in result.outputs


# M6 (count step): a closed child without a disposition is unresolved; a closed rejected child is resolved.


def test_m6_count_step_counts_a_child_closed_without_a_disposition(tmp_path):
    rows = [_row("undisposed", "escalated", 5009)]
    data = world(umbrella_issue({"payloadVersion": 2, "candidates": rows}), _child_issue(5009, "closed"))
    payload = {"payloadVersion": 2, "skillId": "garrytan/gbrain", "newVersion": "v1", "candidates": rows}
    result = run_step(tmp_path, _step_run(WORKFLOW_PATH, "Count unresolved candidate rows"), data,
                      {"PAYLOAD": json.dumps(payload), "ISSUE_NUMBER": str(UMBRELLA)}, cwd=REPO_ROOT)
    assert result.code == 0 and result.outputs == {"count": "1"}, result.output


def test_m6_count_step_resolves_a_child_closed_with_a_rejection(tmp_path):
    rows = [_row("rejected-child", "escalated", 5010)]
    payload = {"payloadVersion": 2, "skillId": "garrytan/gbrain", "newVersion": "v1", "candidates": rows}
    data = world(umbrella_issue(payload),
                 {**_child_issue(5010, "closed"), "labels": [{"name": "upstream:child"},
                                                              {"name": "upstream:rejected"}]})
    result = run_step(tmp_path, _step_run(WORKFLOW_PATH, "Count unresolved candidate rows"), data,
                      {"PAYLOAD": json.dumps(payload), "ISSUE_NUMBER": str(UMBRELLA)}, cwd=REPO_ROOT)
    assert result.code == 0 and result.outputs == {"count": "0"}, result.output


# L4 and L3 at the workflow level.


def test_l4_a_denied_or_in_flight_approve_is_never_cancelled():
    concurrency = _load()["concurrency"]
    assert concurrency["cancel-in-progress"] is False
