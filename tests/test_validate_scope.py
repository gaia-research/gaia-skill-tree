"""Tests for scripts/validate_scope.py, the scope gate behind the always-reporting
required check "Schema + DAG + Integrity Checks" in validate.yml."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import validate_scope as scope

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


def match(pattern: str, path: str) -> bool:
    return bool(scope.compilePattern(pattern).fullmatch(path))


@pytest.mark.parametrize(
    "pattern,path,expected",
    [
        # trailing /** : nested paths and the directory's direct children
        ("registry/**", "registry/a.json", True),
        ("registry/**", "registry/nodes/deep/a.md", True),
        ("registry/**", "registryx/a.json", False),
        ("registry/**", "docs/registry/a.json", False),
        # exact root file and nested file
        ("founder/steward/PLAYBOOKS.md", "founder/steward/PLAYBOOKS.md", True),
        ("founder/steward/PLAYBOOKS.md", "x/founder/steward/PLAYBOOKS.md", False),
        ("founder/steward/PLAYBOOKS.md", "founder/steward/PLAYBOOKSxmd", False),
        # single * never crosses a slash
        ("docs/*.html", "docs/a.html", True),
        ("docs/*.html", "docs/en/a.html", False),
        ("*.md", "README.md", True),
        ("*.md", "docs/README.md", False),
        # ** followed by / matches zero or more directories
        ("a/**/b", "a/b", True),
        ("a/**/b", "a/x/b", True),
        ("a/**/b", "a/x/y/b", True),
        ("a/**/b", "a/xb", False),
        ("**/b", "b", True),
        ("**/b", "x/y/b", True),
        ("**/b.md", "xb.md", False),
        ("**", "anything/at/all", True),
        ("a/**/*.md", "a/r.md", True),
        ("a/**/*.md", "a/x/r.md", True),
        # names with special characters match as literals / via **
        ("registry/**", "registry/café/スキル.md", True),
        ("registry/**", "registry/a\tb\nc.md", True),
        ("registry/**", "registry/ lead and trail ", True),
        ("scripts/a.b", "scripts/aXb", False),
    ],
)
def test_matcher(pattern: str, path: str, expected: bool):
    assert match(pattern, path) is expected


@pytest.mark.parametrize(
    "pattern",
    ["", "a/?.md", "a/[ab].md", "!a/**", "a/b+c", "/abs/**", "a//b", "a/b**/c", "a\\b", "a/**x", "a b", "abc\n", "a/**\n"],
)
def test_unsupported_patterns_fail_closed(pattern: str):
    with pytest.raises(scope.ScopeError):
        scope.compilePattern(pattern)


def test_real_workflow_patterns_are_supported_and_drive_the_gate():
    patterns = scope.loadPatterns(str(WORKFLOW))
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = doc.get("on", doc.get(True))
    # The gate consumes exactly the push trigger's list (single source of truth)
    assert patterns == triggers["push"]["paths"]
    assert not triggers["pull_request"]
    for pattern in patterns:
        scope.compilePattern(pattern)
    assert scope.matches(patterns, "registry/nodes/x.json")
    assert scope.matches(patterns, ".github/workflows/validate.yml")
    assert scope.matches(patterns, "scripts/validate_scope.py")
    assert not scope.matches(patterns, "docs/en/index.html")
    assert not scope.matches(patterns, ".github/workflows/other.yml")
    # The workflow job must actually invoke the script with the event SHAs
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/validate_scope.py" in text
    assert "github.event.pull_request.base.sha" in text
    assert "github.event.pull_request.head.sha" in text
    assert "origin/${BASE_REF}" not in text


def test_workflow_fails_closed_when_detection_fails():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    assert jobs["validate"]["name"] == "Schema + DAG + Integrity Checks"
    assert jobs["validate"]["needs"] == "changes"
    assert "!cancelled()" in jobs["validate"]["if"]
    skillQuality = jobs["skill-quality"]["if"]
    assert "!cancelled()" in skillQuality
    assert "needs.changes.result == 'success'" in skillQuality
    gate = next(s for s in jobs["validate"]["steps"] if s.get("id") == "gate")
    assert '"$CHANGES_RESULT" = "success"' in gate["run"]
    assert '"$CHANGES_RELEVANT" = "false"' in gate["run"]


def git(repo: Path, *args: str) -> str:
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.com",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.com",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
    )
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def write(repo: Path, name: str, text: str = "x\n") -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "README.md")
    write(tmp_path, "docs/keep.html")
    write(tmp_path, "registry/old.json")
    commit(tmp_path, "base")
    return tmp_path


def paths(repo: Path, base: str, head: str) -> list[str]:
    return scope.changedPaths(str(repo), base, head)


def test_changed_paths_are_exact_raw_names(repo: Path):
    base = git(repo, "rev-parse", "HEAD")
    names = [
        "registry/café/スキル.md",
        "registry/tab\there.md",
        "registry/new\nline.md",
        "registry/ leading.md",
        "registry/trailing .md",
        'registry/quote"d.md',
    ]
    for name in names:
        write(repo, name)
    head = commit(repo, "names")
    assert sorted(paths(repo, base, head)) == sorted(names)
    patterns = ["registry/**"]
    assert all(scope.matches(patterns, p) for p in paths(repo, base, head))


def test_renames_and_deletions_report_old_and_new_paths(repo: Path):
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "mv", "registry/old.json", "docs/moved.json")
    git(repo, "rm", "-q", "docs/keep.html")
    head = commit(repo, "rename+delete")
    assert sorted(paths(repo, base, head)) == [
        "docs/keep.html",
        "docs/moved.json",
        "registry/old.json",
    ]
    # moving a relevant file out of a relevant dir still counts as relevant
    assert scope.matches(["registry/**"], "registry/old.json")


def test_diff_uses_merge_base_not_moving_base_tip(repo: Path):
    fork = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "pr")
    write(repo, "docs/en/page.html")
    head = commit(repo, "pr change")
    git(repo, "checkout", "-q", "main")
    write(repo, "scripts/unrelated-main-change.py")
    base = commit(repo, "main advanced")
    assert fork != base
    # Only the PR's own change appears, not main's newer change.
    assert paths(repo, base, head) == ["docs/en/page.html"]


@pytest.mark.parametrize("bad", ["", "HEAD", "main", "0" * 40, "g" * 40, "abc"])
def test_missing_or_bad_shas_raise(repo: Path, bad: str):
    good = git(repo, "rev-parse", "HEAD")
    with pytest.raises(scope.ScopeError):
        scope.changedPaths(str(repo), bad, good)
    with pytest.raises(scope.ScopeError):
        scope.changedPaths(str(repo), good, bad)


def run(repo: Path, workflow: Path, base: str, head: str, capsys) -> str:
    code = scope.main(
        ["--workflow", str(workflow), "--repo", str(repo), "--base", base, "--head", head]
    )
    assert code == 0
    return capsys.readouterr().out.strip()


def copyWorkflow(repo: Path) -> Path:
    target = repo / "wf.yml"
    target.write_text(WORKFLOW.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def test_main_reports_false_only_for_irrelevant_diff(repo: Path, capsys):
    workflow = copyWorkflow(repo)
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "docs/en/a.html")
    head = commit(repo, "docs only")
    assert run(repo, workflow, base, head, capsys) == "relevant=false"
    write(repo, "src/gaia_cli/x.py")
    head2 = commit(repo, "relevant")
    assert run(repo, workflow, base, head2, capsys) == "relevant=true"


def test_main_fails_closed(repo: Path, capsys, tmp_path: Path):
    workflow = copyWorkflow(repo)
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "docs/en/a.html")
    head = commit(repo, "docs only")
    # missing SHA
    assert run(repo, workflow, "", head, capsys) == "relevant=true"
    # unknown SHA
    assert run(repo, workflow, "0" * 40, head, capsys) == "relevant=true"
    # missing workflow file
    assert run(repo, tmp_path / "nope.yml", base, head, capsys) == "relevant=true"
    # unsupported pattern in the push list
    bad = tmp_path / "bad.yml"
    bad.write_text("on:\n  push:\n    paths:\n      - 'a/[ab]/**'\n", encoding="utf-8")
    assert run(repo, bad, base, head, capsys) == "relevant=true"
    # not a git repository
    assert run(tmp_path / "missing", workflow, base, head, capsys) == "relevant=true"
