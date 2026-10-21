"""The per-engine agent workflow wrappers stay in step with their generator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINES = ("copilot", "claude", "codex", "pi")


def test_wrappers_are_current():
    result = subprocess.run([sys.executable, "scripts/gen_steward_agent_workflows.py", "--check"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_every_engine_has_both_roles_compiled():
    for role in ("build", "verify"):
        for engine in ENGINES:
            assert (ROOT / f".github/workflows/steward-{role}-{engine}.md").is_file()
            assert (ROOT / f".github/workflows/steward-{role}-{engine}.lock.yml").is_file()


def test_verifier_workflows_cannot_open_pull_requests():
    for engine in ENGINES:
        text = (ROOT / f".github/workflows/shared/steward-verify.md").read_text(encoding="utf-8")
        assert "create-pull-request" not in text and "push-to-pull-request-branch" not in text
        assert engine in (ROOT / f".github/workflows/steward-verify-{engine}.md").read_text(encoding="utf-8")


def test_builder_pull_requests_are_draft_and_confined_to_steward_branches():
    text = (ROOT / ".github/workflows/shared/steward-build.md").read_text(encoding="utf-8")
    assert "draft: true" in text
    assert 'allowed-branches: ["steward/b/*"]' in text
    assert 'allowed-base-branches: ["dev/*"]' in text


def test_lock_files_reference_released_actions_not_local_paths():
    for lock in (ROOT / ".github/workflows").glob("steward-*-*.lock.yml"):
        text = lock.read_text(encoding="utf-8")
        assert "./actions/setup" not in text, f"{lock.name} was compiled by a dev build of gh-aw"
        assert "github/gh-aw-actions/setup@v" in text
