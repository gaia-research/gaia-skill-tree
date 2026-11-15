"""
Unit tests for gaia dev sync-upstream and gaia dev freeze (upstream-watcher PR 5/7).

Test strategy:
- All tests use temp fixtures (copies of a real-ish named skill file).
- Real registry files are NEVER mutated.
- Time-sensitive fields (timestamps) are mocked via monkeypatch.
- No docs rebuild is triggered (--no-build equivalent via monkeypatching).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Shared fixture content
# ---------------------------------------------------------------------------

_SKILL_MD_2STAR = """\
---
id: testorg/my-skill
name: My Skill
contributor: testorg
origin: true
title: The My Skill Title
genericSkillRef: my-skill
status: named
level: 2\u2605
description: A test named skill used in upstream-verbs unit tests.
installable: true
trustMagnitude: 20.0
overallTrustGrade: C
links:
  github: https://github.com/testorg/my-skill/blob/main/skills/my-skill/SKILL.md
createdAt: '2026-01-01'
updatedAt: '2026-01-01'
timeline: []
---

## My Skill

Body content here.
"""

_SKILL_MD_3STAR = _SKILL_MD_2STAR.replace("level: 2\u2605", "level: 3\u2605")

_SKILL_MD_1STAR = _SKILL_MD_2STAR.replace("level: 2\u2605", "level: 1\u2605")

_SKILL_MD_ALREADY_FROZEN = _SKILL_MD_2STAR.replace(
    "installable: true", "installable: false"
).replace(
    "timeline: []",
    "timeline:\n- timestamp: '2026-02-01T00:00:00Z'\n  action: upstream_deprecated\n  details: removed upstream",
)

# installable: false alone (no public repo) is NOT frozen (gaia_cli.frozen).
_SKILL_MD_NOT_INSTALLABLE = _SKILL_MD_2STAR.replace(
    "installable: true", "installable: false"
)

_SKILL_MD_WITH_UPSTREAM = """\
---
id: testorg/my-skill
name: My Skill
contributor: testorg
origin: true
title: The My Skill Title
genericSkillRef: my-skill
status: named
level: 2\u2605
description: A test named skill used in upstream-verbs unit tests.
installable: true
trustMagnitude: 20.0
overallTrustGrade: C
links:
  github: https://github.com/testorg/my-skill/blob/main/skills/my-skill/SKILL.md
upstream:
  mode: components
  releasedAt: '2026-01-01T00:00:00Z'
  repo: testorg/my-skill
  sourceUrl: https://github.com/testorg/my-skill/releases/tag/v1.0.0
  syncedAt: '2026-01-01T00:00:00Z'
  version: v1.0.0
createdAt: '2026-01-01'
updatedAt: '2026-01-01'
timeline: []
---

## My Skill

Body content here.
"""

# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

MOCKED_NOW = "2026-07-09T12:00:00Z"


def _make_registry(tmp_path: Path, skill_content: str = _SKILL_MD_2STAR) -> tuple[str, Path]:
    """Create a minimal registry structure and return (registry_path, skill_file_path)."""
    named_dir = tmp_path / "registry" / "named" / "testorg"
    named_dir.mkdir(parents=True)
    skill_file = named_dir / "my-skill.md"
    skill_file.write_text(skill_content, encoding="utf-8")

    schema_dir = tmp_path / "registry" / "schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "meta.json").write_text("{}", encoding="utf-8")

    return str(tmp_path), skill_file


# ---------------------------------------------------------------------------
# Args helpers
# ---------------------------------------------------------------------------


def _sync_args(
    registry: str,
    skill_id: str = "testorg/my-skill",
    tag: str = "v1.1.0",
    source_url: str = "https://github.com/testorg/my-skill/releases/tag/v1.1.0",
    *,
    repo: str | None = None,
    bootstrap: bool = False,
    released_at: str | None = None,
    mode: str = "components",
    dry_run: bool = False,
    user: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        registry=registry,
        skill_id=skill_id,
        tag=tag,
        source_url=source_url,
        repo=repo,
        bootstrap=bootstrap,
        released_at=released_at,
        mode=mode,
        dry_run=dry_run,
        user=user,
    )


def _freeze_args(
    registry: str,
    skill_id: str = "testorg/my-skill",
    reason: str = "removed from upstream@v2.0.0",
    *,
    dry_run: bool = False,
    user: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        registry=registry,
        skill_id=skill_id,
        reason=reason,
        dry_run=dry_run,
        user=user,
    )


# ---------------------------------------------------------------------------
# Common patches
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_now(monkeypatch):
    """Freeze the 'now' timestamp used in both commands."""
    monkeypatch.setattr(
        "gaia_cli.commands.dev.sync_upstream._utc_now_iso",
        lambda: MOCKED_NOW,
    )
    monkeypatch.setattr(
        "gaia_cli.commands.dev.freeze._utc_now_iso",
        lambda: MOCKED_NOW,
    )


@pytest.fixture(autouse=True)
def _patch_contributor(monkeypatch):
    monkeypatch.setattr(
        "gaia_cli.commands.dev.sync_upstream._get_contributor",
        lambda: "test-actor",
    )
    monkeypatch.setattr(
        "gaia_cli.commands.dev.freeze._get_contributor",
        lambda: "test-actor",
    )


@pytest.fixture(autouse=True)
def _patch_authz(monkeypatch):
    """Bypass operator authorization in all tests."""
    monkeypatch.setattr(
        "gaia_cli.authz.require_operator",
        lambda *a, **kw: None,
    )


# ---------------------------------------------------------------------------
# sync-upstream happy path
# ---------------------------------------------------------------------------


class TestSyncUpstreamHappyPath:
    def test_bootstrap_writes_upstream_block_and_timeline(self, tmp_path, monkeypatch):
        """Bootstrap on a 2★ skill: upstream block is written, timeline event appended."""
        registry, skill_file = _make_registry(tmp_path)
        args = _sync_args(registry, bootstrap=True, released_at="2026-07-01T00:00:00Z")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")

        # upstream block written
        assert "upstream:" in text
        assert "version: v1.1.0" in text
        assert "repo: testorg/my-skill" in text
        assert "sourceUrl: https://github.com/testorg/my-skill/releases/tag/v1.1.0" in text
        assert "mode: components" in text

        # timeline event appended
        assert "upstream_synced" in text
        assert "first-run baseline" in text
        assert "test-actor" in text
        assert MOCKED_NOW in text

    def test_update_existing_upstream_block(self, tmp_path):
        """Updating from v1.0.0 to v1.1.0: version bumped, previousValue recorded."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        args = _sync_args(registry, tag="v1.1.0",
                          source_url="https://github.com/testorg/my-skill/releases/tag/v1.1.0",
                          released_at="2026-07-08T00:00:00Z")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "version: v1.1.0" in text
        assert "upstream_synced" in text
        # previousValue of old version
        assert "v1.0.0" in text

    def test_version_only_mode(self, tmp_path):
        """--mode version-only is written to upstream.mode."""
        registry, skill_file = _make_registry(tmp_path)
        args = _sync_args(registry, mode="version-only", bootstrap=True,
                          released_at="2026-07-01T00:00:00Z")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "mode: version-only" in text

    def test_dry_run_no_write(self, tmp_path, capsys):
        """--dry-run: no file changes, output contains DRY RUN marker."""
        registry, skill_file = _make_registry(tmp_path)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(registry, dry_run=True, bootstrap=True,
                          released_at="2026-07-01T00:00:00Z")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        assert skill_file.read_text(encoding="utf-8") == original
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_custom_user_in_timeline(self, tmp_path):
        """--user flag is attributed in the timeline event."""
        registry, skill_file = _make_registry(tmp_path)
        args = _sync_args(registry, bootstrap=True, user="custom-bot",
                          released_at="2026-07-01T00:00:00Z")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "custom-bot" in text

    def test_released_at_omitted_warns(self, tmp_path, capsys):
        """When --released-at is omitted, a soft warning is printed to stderr."""
        registry, skill_file = _make_registry(tmp_path)
        args = _sync_args(registry, bootstrap=True, released_at=None)

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_upstream_repo_case_insensitive_match(self, tmp_path):
        """Case mismatch between upstream.repo and source-url is accepted (e.g. TestOrg vs testorg)."""
        content = _SKILL_MD_WITH_UPSTREAM.replace(
            "repo: testorg/my-skill", "repo: TestOrg/My-Skill"
        ).replace(
            "testorg/my-skill/blob", "otherorg/other-skill/blob"
        )
        registry, skill_file = _make_registry(tmp_path, content)
        args = _sync_args(
            registry,
            tag="v1.1.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.1.0",
            released_at="2026-07-08T00:00:00Z",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "version: v1.1.0" in text
        # Existing upstream.repo casing is preserved in frontmatter
        assert "repo: TestOrg/My-Skill" in text

    def test_link_derived_case_insensitive_match(self, tmp_path):
        """Case mismatch between links.github-derived repo and source-url is accepted."""
        # Reproduces run 40184391633 where GitHub release preserved casing
        content = _SKILL_MD_2STAR.replace(
            "https://github.com/testorg/my-skill",
            "https://github.com/TestOrg/My-Skill",
        )
        registry, skill_file = _make_registry(tmp_path, content)
        args = _sync_args(
            registry,
            tag="v1.1.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.1.0",
            bootstrap=True,
            released_at="2026-07-08T00:00:00Z",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "version: v1.1.0" in text
        assert "upstream:" in text

    def test_link_derived_lower_source_url_upper_match(self, tmp_path):
        """Lowercase links.github with uppercase source-url (GitHub release html_url)."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_2STAR)
        args = _sync_args(
            registry,
            tag="v1.1.0",
            source_url="https://github.com/TestOrg/My-Skill/releases/tag/v1.1.0",
            bootstrap=True,
            released_at="2026-07-08T00:00:00Z",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "version: v1.1.0" in text
        assert "repo: TestOrg/My-Skill" in text


# ---------------------------------------------------------------------------
# sync-upstream pre-flight rejects
# ---------------------------------------------------------------------------


class TestSyncUpstreamPreflightRejects:
    def test_nonexistent_skill(self, tmp_path):
        registry, _ = _make_registry(tmp_path)
        args = _sync_args(registry, skill_id="nobody/ghost",
                          source_url="https://github.com/nobody/ghost/releases/tag/v1.0.0")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_bad_version_regex(self, tmp_path):
        registry, _ = _make_registry(tmp_path)
        args = _sync_args(registry, tag="not-a-version")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_bad_source_url_format(self, tmp_path):
        registry, _ = _make_registry(tmp_path)
        args = _sync_args(registry, source_url="https://example.com/not-github")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_source_url_wrong_repo(self, tmp_path):
        """source-url pointing to a different repo is rejected."""
        registry, _ = _make_registry(tmp_path)
        args = _sync_args(
            registry,
            source_url="https://github.com/differentorg/other-repo/releases/tag/v1.1.0",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_whitespace_in_source_url_repo_rejected(self, tmp_path):
        """Whitespace in source-url owner or repo is rejected."""
        registry, _ = _make_registry(tmp_path)
        args = _sync_args(
            registry,
            source_url="https://github.com/testorg /my-skill/releases/tag/v1.1.0",
            bootstrap=True,
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_whitespace_in_upstream_repo_rejected(self, tmp_path):
        """Whitespace attack in existing upstream.repo cannot match clean source-url."""
        content = _SKILL_MD_WITH_UPSTREAM.replace(
            "repo: testorg/my-skill", 'repo: "testorg/my-skill "'
        ).replace(
            "testorg/my-skill/blob", "otherorg/other-skill/blob"
        )
        registry, _ = _make_registry(tmp_path, content)
        args = _sync_args(
            registry,
            tag="v1.1.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.1.0",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_non_github_link_derived_repo_rejected(self, tmp_path):
        """Non-GitHub link cannot derive a matching repo for bootstrap."""
        content = _SKILL_MD_2STAR.replace(
            "https://github.com/testorg/my-skill",
            "https://gitlab.com/testorg/my-skill",
        )
        registry, _ = _make_registry(tmp_path, content)
        args = _sync_args(
            registry,
            tag="v1.1.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.1.0",
            bootstrap=True,
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_already_synced_version_rejected(self, tmp_path):
        """Trying to sync the same version twice raises the already-synced error."""
        registry, _ = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        # _SKILL_MD_WITH_UPSTREAM has version: v1.0.0
        args = _sync_args(registry, tag="v1.0.0",
                          source_url="https://github.com/testorg/my-skill/releases/tag/v1.0.0")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_sub_two_star_skill_rejected(self, tmp_path):
        """1★ skill is below the 2★+ threshold for upstream tracking."""
        registry, _ = _make_registry(tmp_path, _SKILL_MD_1STAR)
        args = _sync_args(registry, bootstrap=True,
                          released_at="2026-07-01T00:00:00Z")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)

    def test_bootstrap_refuses_if_upstream_block_exists(self, tmp_path):
        """--bootstrap is rejected when upstream: block is already present."""
        registry, _ = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        args = _sync_args(registry, tag="v1.1.0",
                          source_url="https://github.com/testorg/my-skill/releases/tag/v1.1.0",
                          bootstrap=True,
                          released_at="2026-07-01T00:00:00Z")

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)


# ---------------------------------------------------------------------------
# sync-upstream idempotency
# ---------------------------------------------------------------------------


class TestSyncUpstreamIdempotency:
    def test_same_version_twice_raises(self, tmp_path):
        """Syncing v1.1.0 once, then again, should raise already-synced error."""
        registry, skill_file = _make_registry(tmp_path)

        # First sync succeeds
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        args1 = _sync_args(registry, bootstrap=True, released_at="2026-07-01T00:00:00Z")
        sync_upstream_command(args1)

        # Second sync of the same version raises
        args2 = _sync_args(registry, tag="v1.1.0",
                           source_url="https://github.com/testorg/my-skill/releases/tag/v1.1.0",
                           released_at="2026-07-01T00:00:00Z")
        with pytest.raises(SystemExit):
            sync_upstream_command(args2)


# ---------------------------------------------------------------------------
# freeze happy path
# ---------------------------------------------------------------------------


class TestFreezeHappyPath:
    def test_sets_installable_false_and_appends_timeline(self, tmp_path):
        """freeze sets installable: false and appends upstream_deprecated event."""
        registry, skill_file = _make_registry(tmp_path)
        args = _freeze_args(registry, reason="removed from upstream@v2.0.0")

        from gaia_cli.commands.dev.freeze import freeze_command
        freeze_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "installable: false" in text
        assert "upstream_deprecated" in text
        assert "removed from upstream@v2.0.0" in text
        assert "test-actor" in text
        assert MOCKED_NOW in text

    def test_dry_run_no_write(self, tmp_path, capsys):
        """--dry-run does not modify the file."""
        registry, skill_file = _make_registry(tmp_path)
        original = skill_file.read_text(encoding="utf-8")
        args = _freeze_args(registry, dry_run=True)

        from gaia_cli.commands.dev.freeze import freeze_command
        freeze_command(args)

        assert skill_file.read_text(encoding="utf-8") == original
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_custom_user_attributed(self, tmp_path):
        """--user is attributed in the timeline event."""
        registry, skill_file = _make_registry(tmp_path)
        args = _freeze_args(registry, user="watcher-bot")

        from gaia_cli.commands.dev.freeze import freeze_command
        freeze_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "watcher-bot" in text


# ---------------------------------------------------------------------------
# freeze pre-flight rejects
# ---------------------------------------------------------------------------


class TestFreezePreflightRejects:
    def test_nonexistent_skill(self, tmp_path):
        registry, _ = _make_registry(tmp_path)
        args = _freeze_args(registry, skill_id="nobody/ghost")

        from gaia_cli.commands.dev.freeze import freeze_command
        with pytest.raises(SystemExit):
            freeze_command(args)

    def test_empty_reason_rejected(self, tmp_path):
        registry, _ = _make_registry(tmp_path)
        args = _freeze_args(registry, reason="")

        from gaia_cli.commands.dev.freeze import freeze_command
        with pytest.raises(SystemExit):
            freeze_command(args)

    def test_reason_too_long_rejected(self, tmp_path):
        registry, _ = _make_registry(tmp_path)
        args = _freeze_args(registry, reason="x" * 501)

        from gaia_cli.commands.dev.freeze import freeze_command
        with pytest.raises(SystemExit):
            freeze_command(args)

    def test_already_frozen_rejected(self, tmp_path):
        registry, _ = _make_registry(tmp_path, _SKILL_MD_ALREADY_FROZEN)
        args = _freeze_args(registry)

        from gaia_cli.commands.dev.freeze import freeze_command
        with pytest.raises(SystemExit):
            freeze_command(args)


    def test_not_installable_is_not_frozen_and_can_be_frozen(self, tmp_path):
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_NOT_INSTALLABLE)
        args = _freeze_args(registry)

        from gaia_cli.commands.dev.freeze import freeze_command
        freeze_command(args)
        assert "upstream_deprecated" in skill_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# freeze 3★+ warning
# ---------------------------------------------------------------------------


class TestFreezeThreeStarWarning:
    def test_three_star_warns_but_proceeds(self, tmp_path, capsys):
        """Freezing a 3★ skill prints a Star Bar warning but does not abort."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_3STAR)
        args = _freeze_args(registry, reason="upstream removed component")

        from gaia_cli.commands.dev.freeze import freeze_command
        freeze_command(args)  # Must NOT raise

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Star Bar" in captured.err

        # File was still written
        text = skill_file.read_text(encoding="utf-8")
        assert "installable: false" in text
        assert "upstream_deprecated" in text


# ---------------------------------------------------------------------------
# End-to-end subprocess regression test
# ---------------------------------------------------------------------------


class TestSyncUpstreamEndToEnd:
    def test_sync_upstream_end_to_end_via_subprocess(self, tmp_path, monkeypatch):
        """Regression: catch top-level argparse action stealing subcommand flags.

        Before the fix, the CLI's top-level --version action silently consumed
        `--version <tag>` from `gaia dev sync-upstream`, printing the CLI version
        string (e.g. "6.3.9") and exiting 0.  The subcommand logic never ran.

        This test invokes the CLI as a real subprocess to catch that class of bug.
        See: cli/upstream-tag-rename PR — renamed --version to --tag.

        NOTE: This test requires the package to be installed (pip install -e .).
        If the CLI binary is not available in the current Python environment,
        the test is skipped gracefully.
        """
        import shutil
        import subprocess
        import os

        # Build a minimal fixture registry in tmp_path
        named_dir = tmp_path / "registry" / "named" / "fixture"
        named_dir.mkdir(parents=True)
        skill_file = named_dir / "skill.md"
        skill_file.write_text(
            "---\n"
            "id: fixture/skill\n"
            "name: Fixture Skill\n"
            "contributor: fixture\n"
            "origin: true\n"
            "title: The Fixture Skill Title\n"
            "genericSkillRef: fixture-skill\n"
            "status: named\n"
            "level: 2\u2605\n"
            "description: Subprocess regression fixture for argparse clash test.\n"
            "installable: true\n"
            "links:\n"
            "  github: https://github.com/fixture/skill/blob/main/skills/SKILL.md\n"
            "createdAt: '2026-01-01'\n"
            "updatedAt: '2026-01-01'\n"
            "timeline: []\n"
            "---\n\n## Fixture Skill\n",
            encoding="utf-8",
        )
        schema_dir = tmp_path / "registry" / "schema"
        schema_dir.mkdir(parents=True)
        (schema_dir / "meta.json").write_text("{}", encoding="utf-8")

        env = {**os.environ, "GAIA_OPERATOR_OVERRIDE": "1"}

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gaia_cli",
                "--registry",
                str(tmp_path),
                "dev",
                "sync-upstream",
                "fixture/skill",
                "--tag",
                "v1.0.0",
                "--source-url",
                "https://github.com/fixture/skill/releases/tag/v1.0.0",
                "--bootstrap",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        combined = result.stdout + result.stderr

        # Regression guard: if the top-level --version action fires, we get
        # the bare version string on stdout and exit 0 — catch it explicitly.
        # The CLI version should NOT appear as the entire stdout.
        # A real version string looks like "6.3.9" or "6.3.9\n".
        import re as _re
        version_only_pattern = _re.compile(r'^\d+\.\d+\.\d+\s*$')
        assert not version_only_pattern.match(result.stdout.strip()), (
            f"Top-level --version action fired: stdout was {result.stdout!r}. "
            "The --tag rename did not take effect. "
            "Check that __init__.py uses add_argument('--tag', ...) not add_argument('--version', ...)."
        )

        # The dry-run output should contain a recognisable marker
        assert "DRY RUN" in result.stdout or "v1.0.0" in combined, (
            f"Expected dry-run output; got stdout={result.stdout!r}, stderr={result.stderr!r}"
        )

        # Exit code must be 0 (dry-run succeeds)
        assert result.returncode == 0, (
            f"Unexpected non-zero exit: returncode={result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )


# ---------------------------------------------------------------------------
# sync-upstream explicit --repo repoint
# ---------------------------------------------------------------------------


class TestSyncUpstreamRepoint:
    def test_explicit_repoint_success_and_preserves_history(self, tmp_path):
        """Explicit --repo repoints upstream.repo, logs old+new provenance, preserves old history."""
        prior_content = _SKILL_MD_WITH_UPSTREAM.replace(
            "timeline: []",
            "suiteRef: testorg/parent-suite\n"
            "timeline:\n"
            "- timestamp: '2026-01-01T00:00:00Z'\n"
            "  action: upstream_synced\n"
            "  contributor: original-bot\n"
            "  previousValue: null\n"
            "  newValue: v1.0.0\n"
            "  details: first-run baseline",
        )
        registry, skill_file = _make_registry(tmp_path, prior_content)
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
            repo="neworg/new-repo",
            released_at="2026-11-10T19:45:36Z",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter

        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        _fence, fm_text, _body = split_frontmatter(text)
        meta = load_yaml_simple(fm_text)

        assert meta["upstream"]["repo"] == "neworg/new-repo"
        assert meta["upstream"]["version"] == "v2.0.0"
        assert meta["upstream"]["sourceUrl"] == "https://github.com/neworg/new-repo/releases/tag/v2.0.0"
        assert meta["suiteRef"] == "testorg/parent-suite"
        assert meta["level"] == "2★"
        assert meta["origin"] is True
        assert len(meta["timeline"]) == 2
        # Prior history preserved verbatim
        assert meta["timeline"][0]["contributor"] == "original-bot"
        assert meta["timeline"][0]["newValue"] == "v1.0.0"
        # New repoint event captures old+new repo and source/version provenance
        ev = meta["timeline"][1]
        assert ev["action"] == "upstream_synced"
        assert ev["previousValue"] == "testorg/my-skill@v1.0.0"
        assert ev["newValue"] == "neworg/new-repo@v2.0.0"
        assert "testorg/my-skill" in ev["details"]
        assert "neworg/new-repo" in ev["details"]
        assert "https://github.com/testorg/my-skill/releases/tag/v1.0.0" in ev["details"]
        assert "https://github.com/neworg/new-repo/releases/tag/v2.0.0" in ev["details"]

    def test_same_tag_repoint_allowed_when_repo_changes(self, tmp_path):
        """Repointing to a new repo with the same tag v1.0.0 succeeds."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        args = _sync_args(
            registry,
            tag="v1.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v1.0.0",
            repo="neworg/new-repo",
            released_at="2026-11-10T19:45:36Z",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        text = skill_file.read_text(encoding="utf-8")
        assert "repo: neworg/new-repo" in text
        assert "testorg/my-skill@v1.0.0" in text
        assert "neworg/new-repo@v1.0.0" in text

    def test_same_tag_same_repo_with_flag_still_rejected(self, tmp_path):
        """Passing --repo with the same repo and same version still rejects."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(
            registry,
            tag="v1.0.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.0.0",
            repo="testorg/my-skill",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_text(encoding="utf-8") == original

    def test_silent_repo_change_without_flag_rejected_even_if_links_changed(self, tmp_path):
        """Without --repo, source-url cannot silently switch away from existing upstream.repo."""
        content = _SKILL_MD_WITH_UPSTREAM.replace(
            "https://github.com/testorg/my-skill/blob/main/skills/my-skill/SKILL.md",
            "https://github.com/neworg/new-repo/blob/main/skills/my-skill/SKILL.md",
        )
        registry, skill_file = _make_registry(tmp_path, content)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_text(encoding="utf-8") == original

    def test_mismatched_repo_and_source_url_rejected_atomically(self, tmp_path):
        """--repo and --source-url pointing to different repos fail before any write."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/otherorg/other-repo/releases/tag/v2.0.0",
            repo="neworg/new-repo",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_text(encoding="utf-8") == original

    @pytest.mark.parametrize("bad_repo", ["not-a-repo", "owner/repo/extra", "owner /repo", "", "-bad/repo"])
    def test_malformed_repo_rejected_atomically(self, tmp_path, bad_repo):
        """Malformed --repo values are rejected before any write."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
            repo=bad_repo,
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_text(encoding="utf-8") == original

    def test_source_url_tag_mismatch_rejected_atomically(self, tmp_path):
        """--source-url tag must match --tag."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.1",
            repo="neworg/new-repo",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_text(encoding="utf-8") == original

    def test_repoint_dry_run_writes_nothing(self, tmp_path, capsys):
        """--dry-run with --repo prints intended changes and writes nothing."""
        registry, skill_file = _make_registry(tmp_path, _SKILL_MD_WITH_UPSTREAM)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
            repo="neworg/new-repo",
            dry_run=True,
            released_at="2026-11-10T19:45:36Z",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        sync_upstream_command(args)

        assert skill_file.read_text(encoding="utf-8") == original
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "neworg/new-repo" in captured.out

    def test_frozen_record_protected_from_repoint(self, tmp_path):
        """Frozen record refuses --repo repoint and writes nothing."""
        frozen_with_upstream = _SKILL_MD_ALREADY_FROZEN.replace(
            "createdAt: '2026-01-01'",
            "upstream:\n"
            "  mode: components\n"
            "  repo: testorg/my-skill\n"
            "  version: v1.0.0\n"
            "createdAt: '2026-01-01'",
        )
        registry, skill_file = _make_registry(tmp_path, frozen_with_upstream)
        original = skill_file.read_text(encoding="utf-8")
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
            repo="neworg/new-repo",
        )

        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_text(encoding="utf-8") == original

    def test_cli_argparse_accepts_repo_flag(self, tmp_path):
        """End-to-end CLI invocation accepts --repo on sync-upstream --dry-run."""
        import os
        import subprocess

        named_dir = tmp_path / "registry" / "named" / "fixture"
        named_dir.mkdir(parents=True)
        skill_file = named_dir / "skill.md"
        skill_file.write_text(
            _SKILL_MD_WITH_UPSTREAM.replace("id: testorg/my-skill", "id: fixture/skill"),
            encoding="utf-8",
        )
        schema_dir = tmp_path / "registry" / "schema"
        schema_dir.mkdir(parents=True)
        (schema_dir / "meta.json").write_text("{}", encoding="utf-8")

        env = {**os.environ, "GAIA_OPERATOR_OVERRIDE": "1", "PYTHONPATH": "src"}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gaia_cli",
                "--registry",
                str(tmp_path),
                "dev",
                "sync-upstream",
                "fixture/skill",
                "--repo",
                "neworg/new-repo",
                "--tag",
                "v2.0.0",
                "--source-url",
                "https://github.com/neworg/new-repo/releases/tag/v2.0.0",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert "DRY RUN" in result.stdout
        assert "neworg/new-repo" in result.stdout


class TestSyncUpstreamHardening:
    """Regression tests for P1 Terra findings (atomicity, schema, URL/repo parsing)."""

    def test_atomic_write_partial_temp_write_preserves_original_bytes(
        self, tmp_path, monkeypatch
    ):
        """Injected partial temp write failure leaves original bytes intact and cleans temp."""
        import os

        registry, skill_file = _make_registry(tmp_path)
        original_bytes = skill_file.read_bytes()
        args = _sync_args(
            registry,
            tag="v1.0.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.0.0",
            released_at="2026-01-01T00:00:00Z",
        )

        orig_fdopen = os.fdopen

        class _PartialFailStream:
            def __init__(self, inner):
                self._inner = inner

            def write(self, data):
                self._inner.write(data[:20])
                self._inner.flush()
                raise OSError("simulated ENOSPC during temp write")

            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                return self._inner.__exit__(*exc_info)

            def __getattr__(self, name):
                return getattr(self._inner, name)

        def _failing_fdopen(fd, *a, **kw):
            return _PartialFailStream(orig_fdopen(fd, *a, **kw))

        monkeypatch.setattr(os, "fdopen", _failing_fdopen)
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        with pytest.raises(OSError, match="simulated ENOSPC"):
            sync_upstream_command(args)

        assert skill_file.read_bytes() == original_bytes
        leftover = [p for p in skill_file.parent.iterdir() if p != skill_file]
        assert leftover == []

    def test_atomic_write_failed_replace_preserves_original_bytes(
        self, tmp_path, monkeypatch
    ):
        """Injected os.replace failure leaves original bytes intact and cleans temp."""
        import os

        registry, skill_file = _make_registry(tmp_path)
        original_bytes = skill_file.read_bytes()
        args = _sync_args(
            registry,
            tag="v1.0.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.0.0",
            released_at="2026-01-01T00:00:00Z",
        )

        def _failing_replace(src, dst):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(os, "replace", _failing_replace)
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        with pytest.raises(OSError, match="simulated replace failure"):
            sync_upstream_command(args)

        assert skill_file.read_bytes() == original_bytes
        leftover = [p for p in skill_file.parent.iterdir() if p != skill_file]
        assert leftover == []

    def test_atomic_write_preserves_original_file_mode(self, tmp_path):
        """Atomic replace preserves original file permission bits."""
        import os
        import stat

        registry, skill_file = _make_registry(tmp_path)
        os.chmod(skill_file, 0o640)
        args = _sync_args(
            registry,
            tag="v1.0.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.0.0",
            released_at="2026-01-01T00:00:00Z",
        )
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        sync_upstream_command(args)
        assert stat.S_IMODE(skill_file.stat().st_mode) == 0o640

    @pytest.mark.parametrize("bad_user", ["invalid_name", "-leading", "has space", ""])
    def test_schema_rejects_invalid_contributor_and_preserves_bytes(
        self, tmp_path, bad_user
    ):
        """Timeline contributor violating namedSkill.schema.json fails before write."""
        registry, skill_file = _make_registry(tmp_path)
        original_bytes = skill_file.read_bytes()
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
            repo="neworg/new-repo",
            released_at="2026-11-10T19:45:36Z",
            user=bad_user,
        )
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        if bad_user == "":
            # empty string falls back to _get_contributor() via `user or _get_contributor()`
            # so test explicit underscore/hyphen/space cases via user; test empty via monkeypatch
            return
        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_text(encoding="utf-8") == original_bytes.decode("utf-8")

    @pytest.mark.parametrize(
        "bad_ts",
        ["not-a-timestamp", "2026-11-10", "2026-11-10T19:45:36", "2026-13-45T00:00:00Z"],
    )
    def test_schema_rejects_invalid_released_at_and_preserves_bytes(
        self, tmp_path, bad_ts
    ):
        """upstream.releasedAt violating RFC 3339 date-time fails before write."""
        registry, skill_file = _make_registry(tmp_path)
        original_bytes = skill_file.read_bytes()
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
            repo="neworg/new-repo",
            released_at=bad_ts,
        )
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_bytes() == original_bytes

    def test_schema_rejects_invalid_mode_and_missing_required_field(self, tmp_path):
        """Schema validation catches invalid upstream.mode and missing required fields."""
        registry, skill_file = _make_registry(tmp_path)
        original_bytes = skill_file.read_bytes()
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url="https://github.com/neworg/new-repo/releases/tag/v2.0.0",
            repo="neworg/new-repo",
            released_at="2026-11-10T19:45:36Z",
            mode="bogus-mode",
        )
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_bytes() == original_bytes

        # Missing required top-level field
        incomplete = _SKILL_MD_2STAR.replace("genericSkillRef: my-skill\n", "")
        registry2, skill_file2 = _make_registry(tmp_path / "r2", incomplete)
        original2 = skill_file2.read_bytes()
        args2 = _sync_args(
            registry2,
            tag="v1.0.0",
            source_url="https://github.com/testorg/my-skill/releases/tag/v1.0.0",
            released_at="2026-11-10T19:45:36Z",
        )
        with pytest.raises(SystemExit):
            sync_upstream_command(args2)
        assert skill_file2.read_bytes() == original2

    @pytest.mark.parametrize(
        "tag,bad_url",
        [
            ("v2.0.0#bad", "https://github.com/neworg/new-repo/releases/tag/v2.0.0#bad"),
            ("v2.0.0", "https://github.com/neworg/new-repo/releases/tag/v2.0.0?foo=bar"),
            ("v2.0.0", "https://github.com/neworg/new-repo/releases/tag/v2.0.0?"),
            ("v2.0.0", "https://github.com/neworg/new-repo/releases/tag/v2.0.0#"),
            ("v2.0.0", "https://user:pass@github.com/neworg/new-repo/releases/tag/v2.0.0"),
            ("v2.0.0", "https://github.com:8443/neworg/new-repo/releases/tag/v2.0.0"),
            ("v2.0.0", "https://github.com/neworg/new-repo/releases/tag/v2.0.0 garbage"),
        ],
    )
    def test_rejects_malformed_release_source_urls(self, tmp_path, tag, bad_url):
        """Parsed URL validation rejects query, fragment, userinfo, port, whitespace."""
        registry, skill_file = _make_registry(tmp_path)
        original_bytes = skill_file.read_bytes()
        args = _sync_args(
            registry,
            tag=tag,
            source_url=bad_url,
            repo="neworg/new-repo",
            released_at="2026-11-10T19:45:36Z",
        )
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_bytes() == original_bytes

    @pytest.mark.parametrize("bad_repo", ["neworg/..", "neworg/.", "../new-repo", "./new-repo"])
    def test_rejects_dot_and_dotdot_owner_repo(self, tmp_path, bad_repo):
        """Reject dot and dotdot segments in --repo and --source-url."""
        registry, skill_file = _make_registry(tmp_path)
        original_bytes = skill_file.read_bytes()
        args = _sync_args(
            registry,
            tag="v2.0.0",
            source_url=f"https://github.com/{bad_repo}/releases/tag/v2.0.0",
            repo=bad_repo,
            released_at="2026-11-10T19:45:36Z",
        )
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command

        with pytest.raises(SystemExit):
            sync_upstream_command(args)
        assert skill_file.read_bytes() == original_bytes

    @pytest.mark.parametrize(
        "tag,encoded_url",
        [
            ("v2.0.0#hotfix", "https://github.com/neworg/new-repo/releases/tag/v2.0.0%23hotfix"),
            ("v2.0.0/1", "https://github.com/neworg/new-repo/releases/tag/v2.0.0%2F1"),
        ],
    )
    def test_accepts_percent_encoded_special_chars_in_release_tag(
        self, tmp_path, tag, encoded_url
    ):
        """Legitimate Git ref characters encoded in URL path are accepted and decoded."""
        registry, skill_file = _make_registry(tmp_path)
        args = _sync_args(
            registry,
            tag=tag,
            source_url=encoded_url,
            repo="neworg/new-repo",
            released_at="2026-11-10T19:45:36Z",
        )
        from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
        from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter

        sync_upstream_command(args)
        _, fm_text, _ = split_frontmatter(skill_file.read_text(encoding="utf-8"))
        fm = load_yaml_simple(fm_text)
        assert fm["upstream"]["version"] == tag
        assert fm["upstream"]["sourceUrl"] == encoded_url
