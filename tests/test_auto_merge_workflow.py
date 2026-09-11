"""Regression tests for issue #1816: auto-merge-small-prs.yml could never merge."""

import pathlib

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "auto-merge-small-prs.yml"


def steps():
    doc = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    return {s.get("name"): s for s in doc["jobs"]["auto-merge"]["steps"]}


def test_merge_uses_merge_commit_not_squash():
    # Squash merging is disabled repo-wide; `--squash` always failed silently.
    run = steps()["Merge PR"]["run"]
    assert "--merge" in run
    assert "--squash" not in run
    assert "|| echo" not in run


def test_wait_loop_ignores_its_own_pending_check():
    doc = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    wait = steps()["Wait for checks and update body"]
    assert wait["env"]["SELF_CHECK"] == doc["jobs"]["auto-merge"]["name"]
    assert "select(.name != $self)" in wait["run"]
