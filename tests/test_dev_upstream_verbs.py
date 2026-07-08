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
