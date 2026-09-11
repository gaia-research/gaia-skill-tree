"""Regression tests for issue #1815: Meta Guard's authorization step always passed.

registry/named-skills.json is a gitignored Class P artifact, so a fresh CI
checkout never has it. The inline check treated a missing index as bootstrap
and authorized every actor. The Verifier set must also come from the base
branch, or a PR could promote its own author.
"""

import pathlib

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "meta-guard.yml"


def job(name):
    doc = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    return doc["jobs"][name]


def index(steps, predicate):
    return next(i for i, s in enumerate(steps) if predicate(s))


def test_meta_guard_builds_index_from_base_before_checking():
    steps = job("meta-guard")["steps"]
    checkout = steps[index(steps, lambda s: s.get("uses", "").startswith("actions/checkout"))]
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    build = index(steps, lambda s: "generateNamedIndex.py" in s.get("run", ""))
    check = index(steps, lambda s: s.get("name") == "Check authorized meta mutation")
    assert build < check


def test_meta_guard_uses_authz_and_fails_closed_without_index():
    steps = job("meta-guard")["steps"]
    run = steps[index(steps, lambda s: s.get("name") == "Check authorized meta mutation")]["run"]
    assert "from gaia_cli.authz import authorization_status" in run
    assert "refusing to fall back to bootstrap" in run
    # PR commits are read by explicit head SHA, since HEAD is the base commit.
    assert '"$MERGE_BASE..$HEAD_SHA"' in run


def test_apex_gate_builds_base_index_before_verifier_signoffs():
    steps = job("apex-gate")["steps"]
    build = index(steps, lambda s: "generateNamedIndex.py" in s.get("run", ""))
    signoffs = index(steps, lambda s: "check_verifier_signoffs.py" in s.get("run", ""))
    assert build < signoffs
    # Verifiers come from the base registry, not the PR's own.
    assert steps[build]["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert 'git worktree add --no-checkout --detach "$BASE_TREE" "$BASE_SHA"' in steps[build]["run"]
