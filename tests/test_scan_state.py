"""Contract tests for scan persistence layer — custom_state.json and scan-state.json.

Tests the schema and data flow for the scan output files after `gaia scan` runs.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Shared helper imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers import strip_ansi
from gaia_cli.main import main
from gaia_cli.registry import scan_state_path


# ---------------------------------------------------------------------------
# Shared helper functions (reused from test_cli_core.py)
# ---------------------------------------------------------------------------

def _make_registry(root: Path, *, skills: list[dict] | None = None) -> None:
    """Write a minimal registry (gaia.json + named-skills.json) under root/registry/."""
    registry = root / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    graph_data = {
        "version": "test",
        "generatedAt": "2026-06-10",
        "skills": skills or [],
    }
    (registry / "gaia.json").write_text(json.dumps(graph_data), encoding="utf-8")
    (registry / "named-skills.json").write_text(
        json.dumps({"buckets": {}, "awaitingClassification": []}), encoding="utf-8"
    )


def _make_skill_md(root: Path, rel_dir: str, skill_id: str, *, name: str | None = None,
                   description: str = "A test skill", prerequisites: list | None = None) -> None:
    """Create a minimal skill dir with a SKILL.md under root / rel_dir / skill_id."""
    skill_dir = root / rel_dir / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm_lines = ["---"]
    fm_lines.append(f"name: {name or skill_id}")
    if description:
        fm_lines.append(f"description: {description}")
    if prerequisites:
        fm_lines.append(f"prerequisites: {json.dumps(prerequisites)}")
    fm_lines.append("---")
    fm_lines.append(f"# {name or skill_id}")
    (skill_dir / "SKILL.md").write_text("\n".join(fm_lines), encoding="utf-8")


def _write_config_toml(project_root: Path, username: str = "testuser") -> None:
    """Write a minimal .gaia/config.toml."""
    gaia_dir = project_root / ".gaia"
    gaia_dir.mkdir(parents=True, exist_ok=True)
    config_path = gaia_dir / "config.toml"
    config_path.write_text(
        f'username = "{username}"\n'
        f'gaiaUser = "{username}"\n'
        f'gaiaRegistryRef = "https://github.com/gaia-research/gaia-skill-tree"\n'
        f'localRegistryPath = "{project_root}"\n'
        f'autoPromptCombinations = false\n'
        f'scanPaths = ["src"]\n',
        encoding="utf-8",
    )


def run_cli(monkeypatch, argv: list[str]):
    """Invoke main() with the given argv, no exec, no network."""
    monkeypatch.setattr(sys, "argv", ["gaia", *argv])
    main()


@pytest.fixture
def scan_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    A minimal project fixture with registry and one demo skill:
      - chdir to tmp_path
      - minimal registry (gaia.json + named-skills.json) under registry/
      - one demo skill under .agents/skills/demo-skill/SKILL.md
      - .gaia/config.toml configured for 'testuser'
      - src/main.py with a /demo-skill token to trigger scan detection
    """
    monkeypatch.chdir(tmp_path)

    _make_registry(tmp_path, skills=[
        {
            "id": "web-search",
            "name": "Web Search",
            "type": "basic",
            "level": "1★",
            "prerequisites": [],
            "description": "Search the web",
        }
    ])

    _make_skill_md(
        tmp_path,
        os.path.join(".agents", "skills"),
        "demo-skill",
        name="Demo Skill",
        description="A demo skill for testing",
        prerequisites=[],
    )

    _write_config_toml(tmp_path, username="testuser")

    # Put a skill token in src/ so scan finds it
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "main.py").write_text(
        "# This file references /demo-skill so scan finds it\n/demo-skill\n",
        encoding="utf-8",
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCustomStateJson:
    """Contract tests for .gaia/custom_state.json written by gaia scan."""

    def test_custom_state_created(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """gaia scan must create .gaia/custom_state.json."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        state_path = scan_project / ".gaia" / "custom_state.json"
        assert state_path.exists(), ".gaia/custom_state.json must be written by scan"

    def test_custom_state_has_top_level_keys(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """custom_state.json must have top-level customSkills (list); customFusions may be present."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        state_path = scan_project / ".gaia" / "custom_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))

        assert "customSkills" in state, "customSkills key must be present"
        assert isinstance(state["customSkills"], list), "customSkills must be a list"
        # customFusions may or may not be written by scan, but if present, must be a dict
        if "customFusions" in state:
            assert isinstance(state["customFusions"], dict), "customFusions must be a dict"

    def test_custom_skills_entry_shape(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """Each customSkills entry must have id, name, description, mapped_to, match_type, prerequisites."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        state_path = scan_project / ".gaia" / "custom_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))

        for entry in state.get("customSkills", []):
            assert "id" in entry, f"Missing 'id' in {entry}"
            assert "name" in entry, f"Missing 'name' in {entry}"
            assert "description" in entry, f"Missing 'description' in {entry}"
            assert "mapped_to" in entry, f"Missing 'mapped_to' in {entry}"
            assert "match_type" in entry, f"Missing 'match_type' in {entry}"
            assert "prerequisites" in entry, f"Missing 'prerequisites' in {entry}"

    def test_custom_skills_id_starts_with_single_slash(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """Each id in customSkills must start with exactly one '/' (regex ^/[^/])."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        state_path = scan_project / ".gaia" / "custom_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))

        for entry in state.get("customSkills", []):
            skill_id = entry["id"]
            # Must start with exactly one slash
            assert skill_id.startswith("/"), f"id '{skill_id}' must start with '/'"
            assert not skill_id.startswith("//"), f"id '{skill_id}' must not start with '//'"
            # The part after the slash must not contain another slash at the start
            after_slash = skill_id[1:]
            assert not after_slash.startswith("/"), f"id '{skill_id}' has multiple leading slashes"


class TestScanStateJson:
    """Contract tests for scan-state.json written at scan_state_path()."""

    def test_scan_state_created(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """gaia scan must write scan-state.json at registry.scan_state_path()."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        ss_path = scan_state_path(str(scan_project))
        assert os.path.exists(ss_path), f"scan-state.json not found at {ss_path}"

    def test_scan_state_has_skills_list(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """scan-state.json must have a top-level 'skills' key containing a list."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        ss_path = scan_state_path(str(scan_project))
        state = json.loads(Path(ss_path).read_text(encoding="utf-8"))

        assert "skills" in state, "scan-state.json must have 'skills' key"
        assert isinstance(state["skills"], list), "skills must be a list"

    def test_scan_state_skill_entry_shape(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """Each skill entry must have id, localId, level, type, description, local, origin, namedRef, matchType."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        ss_path = scan_state_path(str(scan_project))
        state = json.loads(Path(ss_path).read_text(encoding="utf-8"))

        for entry in state.get("skills", []):
            assert "id" in entry, f"Missing 'id' in {entry}"
            assert "localId" in entry, f"Missing 'localId' in {entry}"
            assert "level" in entry, f"Missing 'level' in {entry}"
            assert "type" in entry, f"Missing 'type' in {entry}"
            assert "description" in entry, f"Missing 'description' in {entry}"
            assert "local" in entry, f"Missing 'local' in {entry}"
            assert "origin" in entry, f"Missing 'origin' in {entry}"
            assert "namedRef" in entry, f"Missing 'namedRef' in {entry}"
            assert "matchType" in entry, f"Missing 'matchType' in {entry}"

    def test_scan_state_localid_never_starts_with_slash(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """Each localId in scan-state must never start with '/'."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        ss_path = scan_state_path(str(scan_project))
        state = json.loads(Path(ss_path).read_text(encoding="utf-8"))

        for entry in state.get("skills", []):
            local_id = entry["localId"]
            assert not local_id.startswith("/"), f"localId '{local_id}' must not start with '/'"

    def test_scan_state_no_double_slashes(self, scan_project: Path, monkeypatch: pytest.MonkeyPatch):
        """No id or localId in scan-state may contain '//'."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(scan_project), "scan", "--quiet"])

        ss_path = scan_state_path(str(scan_project))
        state = json.loads(Path(ss_path).read_text(encoding="utf-8"))

        for entry in state.get("skills", []):
            skill_id = entry["id"]
            local_id = entry["localId"]
            assert "//" not in skill_id, f"id '{skill_id}' contains '//'"
            assert "//" not in local_id, f"localId '{local_id}' contains '//'"
