import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import pytest
pytestmark = [pytest.mark.integration]



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from gaia_cli.prWriter import _run, _render_named_block, _current_git_branch, build_intake_issue_body


class TestPrWriterBatchRender(unittest.TestCase):
    """Tests for the rich/legacy rendering split and named block safety."""

    def _base_batch(self, **overrides):
        base = {
            "batchId": "test-batch",
            "userId": "testuser",
            "sourceRepo": "owner/repo",
            "generatedAt": "2026-01-01T00:00:00Z",
            "fromFile": False,
            "knownSkills": [],
            "proposedSkills": [],
            "similarity": [],
        }
        base.update(overrides)
        return base

    def test_fromfile_true_minimal_skill_uses_details_blocks(self):
        """fromFile=True must gate rich rendering even with no attribution/evidence."""
        batch = self._base_batch(
            fromFile=True,
            proposedSkills=[{"id": "minimal-skill", "name": "Minimal", "type": "basic"}],
        )
        body = build_intake_issue_body(batch)
        self.assertIn("<details>", body, "fromFile=True batch must use <details> blocks")

    def test_fromfile_false_minimal_skill_uses_flat_table(self):
        """fromFile=False with no rich fields must fall back to legacy flat table."""
        batch = self._base_batch(
            fromFile=False,
            proposedSkills=[{"id": "minimal-skill", "name": "Minimal", "type": "basic"}],
        )
        body = build_intake_issue_body(batch)
        self.assertNotIn("<details>", body)
        self.assertIn("| ID |", body)

    def test_checklist_headings_are_lowercase(self):
        """Heading case must match what prWriter emits (fixes pre-existing assertion)."""
        batch = self._base_batch()
        body = build_intake_issue_body(batch)
        self.assertIn("### Reviewer checklist", body)
        self.assertIn("### Maintainer promotion checklist", body)

    def test_render_named_block_brace_in_contributor_does_not_raise(self):
        """Braces in contributor handle must not cause IndexError/KeyError."""
        named = {
            "contributor": "user{broken}",
            "level": "3★",
            "links_github": "https://github.com/a/b",
        }
        try:
            result = _render_named_block(named, "my-skill")
        except (IndexError, KeyError) as exc:
            self.fail(f"_render_named_block raised {type(exc).__name__}: {exc}")
        self.assertIn("my-skill", result)
        self.assertIn("user{broken}", result)

    def test_render_named_block_preserves_upstream_skill_name(self):
        named = {
            "contributor": "foo", "skill_name": "upstream-slug", "level": "2★",
            "links_github": "https://github.com/a/b/blob/main/SKILL.md",
        }
        result = _render_named_block(named, "generic-id")
        self.assertIn("foo/upstream-slug", result)
        self.assertNotIn("foo/generic-id", result)

    def test_issue_renders_packet_to_batch_provenance(self):
        batch = self._base_batch(curationHandoff={
            "contractVersion": "curation-handoff-v1",
            "packetRefs": [{
                "candidateId": "foo/upstream-slug",
                "packetPath": "registry-for-review/discovery-packets/foo.json",
                "packetContentSha256": "a" * 64,
                "sourceContentSha256": "b" * 64,
            }],
        })
        body = build_intake_issue_body(batch)
        self.assertIn("### Curation handoff provenance", body)
        self.assertIn("`foo/upstream-slug`", body)
        self.assertIn("`" + "a" * 64 + "`", body)

    def test_render_named_block_skill_id_embedded_correctly(self):
        """Named block must embed skillId directly, not via deferred format()."""
        named = {"contributor": "foo", "level": "2★", "links_github": "https://github.com/a/b"}
        result = _render_named_block(named, "my-target-skill")
        self.assertIn("foo/my-target-skill", result)

    def test_issue_body_includes_batch_branch_explicit_override(self):
        """A batch-supplied batchBranch wins over git resolution (#1785)."""
        batch = self._base_batch(batchBranch="review/meta/tester--skill")
        body = build_intake_issue_body(batch)
        self.assertIn("| Batch Branch | `review/meta/tester--skill` |", body)

    def test_issue_body_resolves_batch_branch_from_git_when_unset(self):
        """With no explicit batchBranch, fall back to the current git branch
        so intake-approval.yml can check out where the batch actually lives
        instead of assuming main (#1785)."""
        batch = self._base_batch()
        body = build_intake_issue_body(batch, repo_root=REPO_ROOT)
        self.assertIn("| Batch Branch | `", body)
        self.assertNotIn("| Batch Branch | `unknown` |", body)


class TestPrWriterLegacy(unittest.TestCase):
    def test_build_intake_issue_body_contains_summary_table_and_checklists(self):
        batch = {
            "batchId": "20260429000000-tester-repo",
            "userId": "tester",
            "sourceRepo": "tester/repo",
            "generatedAt": "2026-04-29T00:00:00Z",
            "knownSkills": [{"skillId": "web-search"}],
            "proposedSkills": [
                {
                    "id": "semantic-search",
                    "name": "Semantic Search",
                    "type": "atomic",
                }
            ],
            "similarity": [
                {
                    "sourceSkillId": "semantic-search",
                    "targetSkillId": "web-search",
                    "score": 0.73,
                    "reason": "Lexical similarity from Gaia push scan.",
                }
            ],
        }
        body = build_intake_issue_body(batch)
        self.assertIn("| Known canonical skills | `1` |", body)
        self.assertIn("| Proposed new skills | `1` |", body)
        self.assertIn("`semantic-search`", body)
        self.assertIn("`web-search` (0.730)", body)
        self.assertIn("### Reviewer checklist", body)
        self.assertIn("### Maintainer promotion checklist", body)

    def test_run_exposes_gaia_cli_to_subprocesses_outside_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True):
                result = _run(
                    [
                        sys.executable,
                        "-S",
                        "-c",
                        "import gaia_cli; print(gaia_cli.__name__)",
                    ],
                    cwd=tmp,
                )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gaia_cli", result.stdout)


class TestCurrentGitBranchDetachedHead(unittest.TestCase):
    """Regression coverage for the sandbox-review finding: a detached-HEAD
    checkout (the common case in CI) must not silently fall through to
    `unknown` -> `main` in the workflow parser (that reinstates #1785)."""

    def _init_repo(self, tmp):
        env = dict(os.environ)
        env.pop("GITHUB_HEAD_REF", None)
        env.pop("GITHUB_REF_NAME", None)
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True, env=env)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True, env=env)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, check=True, env=env)
        with open(os.path.join(tmp, "f.txt"), "w") as fh:
            fh.write("x")
        subprocess.run(["git", "add", "f.txt"], cwd=tmp, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True, env=env)
        return env

    def test_detached_head_falls_back_to_github_head_ref_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._init_repo(tmp)
            subprocess.run(["git", "checkout", "-q", "--detach", "HEAD"], cwd=tmp, check=True, env=env)

            with patch.dict(os.environ, {"GITHUB_HEAD_REF": "review/meta/intake-42"}, clear=False):
                os.environ.pop("GITHUB_REF_NAME", None)
                branch = _current_git_branch(repo_root=tmp)

        self.assertEqual(branch, "review/meta/intake-42")

    def test_detached_head_falls_back_to_github_ref_name_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._init_repo(tmp)
            subprocess.run(["git", "checkout", "-q", "--detach", "HEAD"], cwd=tmp, check=True, env=env)

            with patch.dict(os.environ, {"GITHUB_REF_NAME": "dev/intake-batch"}, clear=False):
                os.environ.pop("GITHUB_HEAD_REF", None)
                branch = _current_git_branch(repo_root=tmp)

        self.assertEqual(branch, "dev/intake-batch")

    def test_detached_head_with_no_env_hints_returns_none_not_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._init_repo(tmp)
            subprocess.run(["git", "checkout", "-q", "--detach", "HEAD"], cwd=tmp, check=True, env=env)

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GITHUB_HEAD_REF", None)
                os.environ.pop("GITHUB_REF_NAME", None)
                branch = _current_git_branch(repo_root=tmp)

        self.assertIsNone(branch)

    def test_normal_branch_checkout_resolves_via_git_branch_show_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._init_repo(tmp)
            subprocess.run(["git", "checkout", "-q", "-b", "feature/x"], cwd=tmp, check=True, env=env)

            branch = _current_git_branch(repo_root=tmp)

        self.assertEqual(branch, "feature/x")


if __name__ == "__main__":
    unittest.main()
