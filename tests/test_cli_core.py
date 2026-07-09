"""Wave 1 — Core CLI lifecycle tests.

Headless, tmp-dir isolated coverage of the command surface introduced/overhauled in PR #635:
  bare gaia, --help, selector fallback, init, scan, push, tree, graph, fetch, reset, pull.

Every test uses monkeypatch.chdir(tmp_path) and patches out network/browser so nothing
escapes to the filesystem outside tmp_path or the network.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Shared helper imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers import strip_ansi
from gaia_cli.main import main, PUBLIC_COMMANDS, get_parser


# ---------------------------------------------------------------------------
# Shared CLI runner
# ---------------------------------------------------------------------------

def run_cli(monkeypatch, argv: list[str]):
    """Invoke main() with the given argv, no exec, no network."""
    monkeypatch.setattr(sys, "argv", ["gaia", *argv])
    main()


# ---------------------------------------------------------------------------
# Shared project fixture
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


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    A minimal project fixture:
      - chdir to tmp_path
      - minimal registry (gaia.json + named-skills.json) under registry/
      - one demo skill under .agents/skills/demo-skill/SKILL.md
      - .gaia/config.toml configured for 'testuser'
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

    # Put a skill token in src/ so pathEngine.regenerate_paths picks it up.
    # scan_command only keeps skills whose bare ID appears in paths.detectedIds.
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "main.py").write_text(
        "# This file references /demo-skill so scan finds it\n/demo-skill\n",
        encoding="utf-8",
    )

    return tmp_path


# ---------------------------------------------------------------------------
# 1. TestBareGaia — bare 'gaia' with no TTY → help printed
# ---------------------------------------------------------------------------

class TestBareGaia:
    """Bare `gaia` with argv=['gaia'] and no TTY → falls back to printing help."""

    def test_help_sections_in_output(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """Non-TTY bare invocation should print COMMAND_USAGE with section headers."""
        monkeypatch.chdir(tmp_path)
        # Ensure stdin/stdout are not TTYs so no selector runs
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        monkeypatch.setattr(sys, "argv", ["gaia"])
        main()
        out = strip_ansi(capsys.readouterr().out)
        # COMMAND_USAGE contains these section headers
        assert "Getting started" in out
        assert "Daily commands" in out or "Daily" in out
        assert "Skills" in out
        assert "Utilities" in out


# ---------------------------------------------------------------------------
# 2. TestHelp — gaia --help
# ---------------------------------------------------------------------------

class TestHelp:
    """gaia --help exits 0 and the parser registers every PUBLIC_COMMANDS entry.

    NOTE (product oddity discovered): 'fetch' and 'reset' are in PUBLIC_COMMANDS
    and are registered as subparser choices but are NOT mentioned in the
    COMMAND_USAGE epilog that --help prints.  They appear in the raw subparser
    metavar string (``{help,init,scan,fetch,...}``) but argparse truncates that
    string in the output.  We therefore verify registration via parser introspection
    rather than raw help text.
    """

    @pytest.mark.smoke
    def test_help_exits_zero(self, monkeypatch: pytest.MonkeyPatch, capsys):
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, ["--help"])
        assert exc.value.code == 0

    @pytest.mark.smoke
    def test_parser_registers_all_public_commands(self):
        """Every PUBLIC_COMMANDS entry must be a registered subparser choice."""
        import argparse
        parser, _ = get_parser()
        subparser_choices: set[str] = set()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparser_choices.update(action.choices.keys())

        for cmd in PUBLIC_COMMANDS:
            assert cmd in subparser_choices, \
                f"PUBLIC_COMMANDS entry '{cmd}' is not a registered subparser choice"

    def test_parser_has_fetch_and_reset(self):
        """fetch and reset must be registered subparser choices (plan requirement)."""
        import argparse
        parser, _ = get_parser()
        subparser_choices: set[str] = set()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparser_choices.update(action.choices.keys())
        assert "fetch" in subparser_choices, "fetch must be a registered subparser"
        assert "reset" in subparser_choices, "reset must be a registered subparser"

    def test_parser_allow_downgrade_flags(self):
        """fetch and pull subparsers must accept --allow-downgrade flag."""
        import argparse
        parser, _ = get_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                fetch_sub = action.choices["fetch"]
                pull_sub = action.choices["pull"]

                # Check for --allow-downgrade in both
                fetch_opts = [opt for sub in fetch_sub._actions for opt in sub.option_strings]
                pull_opts = [opt for sub in pull_sub._actions for opt in sub.option_strings]

                assert "--allow-downgrade" in fetch_opts, "--allow-downgrade must be in fetch options"
                assert "--allow-downgrade" in pull_opts, "--allow-downgrade must be in pull options"

    def test_help_output_contains_common_commands(self, monkeypatch: pytest.MonkeyPatch, capsys):
        """--help output must mention at least the common visible commands."""
        with pytest.raises(SystemExit):
            run_cli(monkeypatch, ["--help"])
        out = strip_ansi(capsys.readouterr().out)
        # These appear in COMMAND_USAGE epilog
        for cmd in ("init", "scan", "push", "tree", "promote"):
            assert cmd in out, f"Expected '{cmd}' in --help output"


# ---------------------------------------------------------------------------
# 3. TestSelectorFallback — run_selector when not interactive
# ---------------------------------------------------------------------------

class TestSelectorFallback:
    """run_selector(parser) when _has_interactive() → False prints help, returns None, no exec."""

    def test_fallback_prints_help(self, monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path):
        """When non-interactive, run_selector should print help (parser.print_help) and return."""
        monkeypatch.chdir(tmp_path)
        from gaia_cli import selector as sel_mod
        from gaia_cli.interactive import _has_interactive

        # Force non-interactive mode
        monkeypatch.setattr(sel_mod, "_has_interactive", lambda: False)

        parser, _ = get_parser()
        result = sel_mod.run_selector(parser)

        # Should have returned None (no command selected)
        assert result is None

        # Help text should have been printed
        out = strip_ansi(capsys.readouterr().out)
        # parser.print_help() produces argparse output mentioning the prog name
        assert "gaia" in out.lower()

    def test_fallback_no_exec(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """run_selector in non-interactive mode must not call os.execvp (guard fixture enforces it)."""
        monkeypatch.chdir(tmp_path)
        from gaia_cli import selector as sel_mod
        monkeypatch.setattr(sel_mod, "_has_interactive", lambda: False)

        parser, _ = get_parser()
        # If execvp were called, the conftest guard would raise RuntimeError
        sel_mod.run_selector(parser)  # must not raise RuntimeError


# ---------------------------------------------------------------------------
# 4. TestInit — gaia init --user testuser --yes
# ---------------------------------------------------------------------------

class TestInit:
    """gaia init --user testuser --yes creates .gaia/config.toml and calls fetch_command."""

    def test_config_toml_created(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """init --yes should write .gaia/config.toml."""
        monkeypatch.chdir(tmp_path)
        import gaia_cli.main as gaia_main

        # Patch fetch_command so no network hits
        fetch_calls: list[Any] = []
        monkeypatch.setattr(gaia_main, "fetch_command", lambda args: fetch_calls.append(args))
        # Patch _detect_github_username to avoid git subprocess
        monkeypatch.setattr(gaia_main, "_detect_github_username", lambda: None)
        # Patch detect_source_repo to avoid git subprocess inside init
        from gaia_cli import push as push_mod
        monkeypatch.setattr(push_mod, "detect_source_repo",
                            lambda config: (_ for _ in ()).throw(push_mod.NonPublicRepoError("testuser")))

        run_cli(monkeypatch, ["init", "--user", "testuser", "--yes"])

        config_path = tmp_path / ".gaia" / "config.toml"
        assert config_path.exists(), ".gaia/config.toml must be created by gaia init"
        text = config_path.read_text(encoding="utf-8")
        assert "testuser" in text

    def test_fetch_called_by_init(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """init --yes should invoke fetch_command exactly once."""
        monkeypatch.chdir(tmp_path)
        import gaia_cli.main as gaia_main

        fetch_calls: list[Any] = []
        monkeypatch.setattr(gaia_main, "fetch_command", lambda args: fetch_calls.append(args))
        monkeypatch.setattr(gaia_main, "_detect_github_username", lambda: None)
        from gaia_cli import push as push_mod
        monkeypatch.setattr(push_mod, "detect_source_repo",
                            lambda config: (_ for _ in ()).throw(push_mod.NonPublicRepoError("testuser")))

        run_cli(monkeypatch, ["init", "--user", "testuser", "--yes"])

        assert len(fetch_calls) == 1, "fetch_command should be called once by init"


# ---------------------------------------------------------------------------
# 5. TestScan — gaia scan
# ---------------------------------------------------------------------------

class TestScan:
    """gaia scan writes .gaia/custom_state.json and scan-state.json; --all parses correctly."""

    def test_scan_exits_cleanly(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """scan completes without SystemExit in a minimal fixture project."""
        import gaia_cli.main as gaia_main
        # Patch render_user_tree_outputs to avoid writing outside tmp
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        # Suppress open_pr calls if any combo detected
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(project), "scan", "--quiet"])
        # If we get here, no unhandled exception / SystemExit

    def test_custom_state_written(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """scan --quiet must write .gaia/custom_state.json with customSkills and customFusions keys."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(project), "scan", "--quiet"])

        state_path = project / ".gaia" / "custom_state.json"
        assert state_path.exists(), ".gaia/custom_state.json must be written by scan"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert "customSkills" in state, "customSkills key must be present"
        # customFusions may or may not be written by scan, but key is preserved from init

    def test_custom_state_skill_keys(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """Each entry in customSkills must have id, mapped_to, match_type, prerequisites keys."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(project), "scan", "--quiet"])

        state_path = project / ".gaia" / "custom_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for sk in state.get("customSkills", []):
            assert "id" in sk, f"Missing 'id' key in {sk}"
            assert "mapped_to" in sk, f"Missing 'mapped_to' key in {sk}"
            assert "match_type" in sk, f"Missing 'match_type' key in {sk}"
            assert "prerequisites" in sk, f"Missing 'prerequisites' key in {sk}"

    def test_scan_state_written(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """scan must write scan-state.json at scan_state_path() with skills[].{id,localId,matchType}."""
        import gaia_cli.main as gaia_main
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(project), "scan", "--quiet"])

        from gaia_cli.registry import scan_state_path
        ss_path = scan_state_path(str(project))
        assert os.path.exists(ss_path), f"scan-state.json not found at {ss_path}"
        state = json.loads(Path(ss_path).read_text(encoding="utf-8"))
        assert "skills" in state, "scan-state.json must have 'skills' key"
        for entry in state["skills"]:
            assert "id" in entry, f"Missing 'id' in scan-state skill entry"
            assert "localId" in entry, f"Missing 'localId' in scan-state skill entry"
            assert "matchType" in entry, f"Missing 'matchType' in scan-state skill entry"

    def test_scan_all_flag_parsed(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """scan --all must parse successfully (args.all == True)."""
        import gaia_cli.main as gaia_main
        captured_args: list[Any] = []

        original_scan = gaia_main.scan_command
        def capturing_scan(args):
            captured_args.append(args)
            original_scan(args)

        monkeypatch.setattr(gaia_main, "scan_command", capturing_scan)
        monkeypatch.setattr(gaia_main, "render_user_tree_outputs", lambda *a, **kw: None)
        from gaia_cli import prWriter
        monkeypatch.setattr(prWriter, "open_pr", lambda *a, **kw: None)

        run_cli(monkeypatch, ["--registry", str(project), "scan", "--all", "--quiet"])

        assert len(captured_args) == 1
        assert getattr(captured_args[0], "all", False) is True


# ---------------------------------------------------------------------------
# 6. TestPush — gaia push --dry-run and --no-pr
# ---------------------------------------------------------------------------

class TestPush:
    """gaia push --dry-run outputs batch JSON; --no-pr --yes writes batch file."""

    def _seed_custom_state(self, project: Path) -> None:
        """Seed .gaia/custom_state.json with one known/mapped + one unmatched skill + one fusion."""
        gaia_dir = project / ".gaia"
        gaia_dir.mkdir(parents=True, exist_ok=True)
        custom_state = {
            "customSkills": [
                {
                    # Known starless skill: match_type exact_generic, canon_level 0★
                    "id": "/web-search",
                    "name": "Web Search",
                    "description": "Search the web",
                    "location": ".agents/skills/web-search",
                    "mapped_to": "web-search",
                    "mapped_score": 1.0,
                    "match_type": "exact_generic",
                    "canon_level": "0★",
                    "skill_type": "basic",
                    "prerequisites": [],
                },
                {
                    # Custom/unmatched skill
                    "id": "/my-custom-skill",
                    "name": "My Custom Skill",
                    "description": "A custom skill I wrote",
                    "location": ".agents/skills/my-custom-skill",
                    "mapped_to": "/my-custom-skill",
                    "mapped_score": 0.0,
                    "match_type": None,
                    "canon_level": "0★",
                    "skill_type": "basic",
                    "prerequisites": [],
                },
            ],
            "customFusions": {
                "my-fusion": {
                    "sources": ["web-search"],
                    "type": "extra",
                    "level": "1★",
                },
            },
        }
        (gaia_dir / "custom_state.json").write_text(
            json.dumps(custom_state, indent=2), encoding="utf-8"
        )

    def test_dry_run_outputs_batch_json(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """push --dry-run must print JSON containing knownSkills and proposedCombinations."""
        self._seed_custom_state(project)
        import gaia_cli.main as gaia_main
        # Patch detect_source_repo to avoid git
        from gaia_cli import push as push_mod
        monkeypatch.setattr(push_mod, "detect_source_repo",
                            lambda config: "testuser/test-repo")

        run_cli(monkeypatch, ["--registry", str(project), "push", "--dry-run"])

        out = capsys.readouterr().out
        # Should be parseable JSON
        batch = json.loads(out)
        assert "knownSkills" in batch, "dry-run batch must include knownSkills"
        assert "proposedCombinations" in batch, "dry-run batch must include proposedCombinations"

    def test_dry_run_known_skills_have_localId(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """knownSkills entries must have both skillId and localId."""
        self._seed_custom_state(project)
        from gaia_cli import push as push_mod
        monkeypatch.setattr(push_mod, "detect_source_repo", lambda config: "testuser/test-repo")

        run_cli(monkeypatch, ["--registry", str(project), "push", "--dry-run"])

        out = capsys.readouterr().out
        batch = json.loads(out)
        for k in batch.get("knownSkills", []):
            assert "skillId" in k, f"knownSkills entry missing 'skillId': {k}"
            assert "localId" in k, f"knownSkills entry missing 'localId': {k}"

    def test_no_pr_yes_writes_batch_file(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """push --no-pr --yes must write a batch JSON file under registry-for-review/skill-batches/."""
        self._seed_custom_state(project)
        from gaia_cli import push as push_mod
        monkeypatch.setattr(push_mod, "detect_source_repo", lambda config: "testuser/test-repo")
        # Patch stdin to look non-TTY so no interactive prompt needed
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

        run_cli(monkeypatch, ["--registry", str(project), "push", "--no-pr", "--yes"])

        batches_dir = project / "registry-for-review" / "skill-batches"
        assert batches_dir.exists(), "registry-for-review/skill-batches/ must be created"
        batch_files = list(batches_dir.glob("*.json"))
        assert len(batch_files) >= 1, "At least one batch JSON file must be written"
        batch = json.loads(batch_files[0].read_text(encoding="utf-8"))
        assert "knownSkills" in batch or "proposedSkills" in batch or "proposedCombinations" in batch


# ---------------------------------------------------------------------------
# 7. TestTree — gaia tree (smoke test)
# ---------------------------------------------------------------------------

class TestTree:
    """gaia tree runs without error and outputs a legend."""

    def test_tree_exits_cleanly(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """tree command should not crash; output is readable."""
        import gaia_cli.main as gaia_main
        from gaia_cli import push as push_mod
        monkeypatch.setattr(push_mod, "detect_source_repo",
                            lambda config: (_ for _ in ()).throw(push_mod.NonPublicRepoError("testuser")))

        # Run tree with no tree file — should print a helpful message, not crash
        run_cli(monkeypatch, ["--registry", str(project), "tree"])
        # If we reach here, no crash

    def test_tree_output_readable(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """tree output (after strip_ansi) must be non-empty text."""
        import gaia_cli.main as gaia_main
        from gaia_cli import push as push_mod
        monkeypatch.setattr(push_mod, "detect_source_repo",
                            lambda config: (_ for _ in ()).throw(push_mod.NonPublicRepoError("testuser")))

        run_cli(monkeypatch, ["--registry", str(project), "tree"])
        out = strip_ansi(capsys.readouterr().out)
        # Some output is expected (either the tree or an init message)
        assert len(out.strip()) > 0, "tree output must be non-empty"


# ---------------------------------------------------------------------------
# 8. TestGraph — gaia graph (canon and custom modes)
# ---------------------------------------------------------------------------

class TestGraph:
    """graph --canon writes registry/render/gaia.html with canvas3d; default writes .gaia/render/gaia.html."""

    def test_canon_graph_writes_html(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """graph --canon must write registry/render/gaia.html containing canvas3d."""
        import webbrowser
        monkeypatch.setattr(webbrowser, "open", lambda uri: True)

        run_cli(monkeypatch, ["--registry", str(project), "graph", "--canon", "--no-open"])

        html_path = project / "registry" / "render" / "gaia.html"
        assert html_path.exists(), "graph --canon must write registry/render/gaia.html"
        content = html_path.read_text(encoding="utf-8")
        assert "canvas3d" in content, "HTML output must contain canvas3d element"

    def test_canon_graph_has_embedded_json(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """graph --canon HTML must contain an embedded JSON script tag."""
        import webbrowser
        monkeypatch.setattr(webbrowser, "open", lambda uri: True)

        run_cli(monkeypatch, ["--registry", str(project), "graph", "--canon", "--no-open"])

        html_path = project / "registry" / "render" / "gaia.html"
        content = html_path.read_text(encoding="utf-8")
        assert "gaia-graph-data" in content, "HTML must have embedded gaia-graph-data JSON"

    def test_custom_graph_writes_to_gaia_dir(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """Default (custom) graph must write to .gaia/render/gaia.html."""
        import webbrowser
        monkeypatch.setattr(webbrowser, "open", lambda uri: True)

        run_cli(monkeypatch, ["--registry", str(project), "graph", "--custom", "--no-open"])

        html_path = project / ".gaia" / "render" / "gaia.html"
        assert html_path.exists(), "Default (custom) graph must write .gaia/render/gaia.html"


# ---------------------------------------------------------------------------
# 9. TestFetch — gaia fetch (monkeypatched network)
# ---------------------------------------------------------------------------

def _make_fake_release_tarball(project: Path) -> bytes:
    """Create a minimal gaia-artifacts.tar.gz in memory with registry files."""
    import io
    import tarfile as _tarfile

    buf = io.BytesIO()
    with _tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # registry/gaia.json
        gaia_data = json.dumps({"version": "test", "skills": []}).encode("utf-8")
        info = _tarfile.TarInfo(name="registry/gaia.json")
        info.size = len(gaia_data)
        tar.addfile(info, io.BytesIO(gaia_data))
        # registry/named-skills.json
        named_data = json.dumps({"buckets": {}}).encode("utf-8")
        info2 = _tarfile.TarInfo(name="registry/named-skills.json")
        info2.size = len(named_data)
        tar.addfile(info2, io.BytesIO(named_data))
    return buf.getvalue()


def _make_tarball_with_version(project: Path, version: str) -> bytes:
    import io
    import tarfile as _tarfile

    buf = io.BytesIO()
    with _tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # registry/gaia.json
        gaia_data = json.dumps({"version": version, "skills": []}).encode("utf-8")
        info = _tarfile.TarInfo(name="registry/gaia.json")
        info.size = len(gaia_data)
        tar.addfile(info, io.BytesIO(gaia_data))
        # registry/named-skills.json
        named_data = json.dumps({"buckets": {}}).encode("utf-8")
        info2 = _tarfile.TarInfo(name="registry/named-skills.json")
        info2.size = len(named_data)
        tar.addfile(info2, io.BytesIO(named_data))
    return buf.getvalue()



def _make_release_api_response(asset_url: str, checksum_url: str = "") -> bytes:
    """Return JSON bytes for the GitHub releases/latest API."""
    assets = [{"name": "gaia-artifacts.tar.gz", "browser_download_url": asset_url}]
    if checksum_url:
        assets.append({"name": "gaia-artifacts.tar.gz.sha256", "browser_download_url": checksum_url})
    payload = {"tag_name": "v99.0.0", "assets": assets}
    return json.dumps(payload).encode("utf-8")


def _patch_fetch_urlopen(monkeypatch: "pytest.MonkeyPatch", tarball_bytes: bytes, *, with_checksum: bool = False):
    """Monkeypatch urllib.request so fetch_command gets canned responses without network."""
    import hashlib
    import io
    import urllib.request

    asset_url = "https://example.com/gaia-artifacts.tar.gz"
    checksum_url = "https://example.com/gaia-artifacts.tar.gz.sha256" if with_checksum else ""

    release_bytes = _make_release_api_response(asset_url, checksum_url)
    checksum_bytes = (hashlib.sha256(tarball_bytes).hexdigest() + "  gaia-artifacts.tar.gz\n").encode() if with_checksum else b""

    url_map = {
        asset_url: tarball_bytes,
        checksum_url: checksum_bytes,
    }

    call_log = {"count": 0}

    class _FakeResponse:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if call_log["count"] == 0:
            # First call: releases API
            call_log["count"] += 1
            return _FakeResponse(release_bytes)
        data = url_map.get(url, b"")
        call_log["count"] += 1
        return _FakeResponse(data)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


class TestFetch:
    """fetch_command writes .gaia/registry/gaia.json and named-skills.json; no real network."""

    def test_fetch_writes_registry_files(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """fetch must write gaia.json and named-skills.json under .gaia/registry/."""
        tarball = _make_fake_release_tarball(project)
        _patch_fetch_urlopen(monkeypatch, tarball)

        run_cli(monkeypatch, ["fetch"])

        assert (project / ".gaia" / "registry" / "gaia.json").exists(), \
            ".gaia/registry/gaia.json must be written by fetch"
        assert (project / ".gaia" / "registry" / "named-skills.json").exists(), \
            ".gaia/registry/named-skills.json must be written by fetch"

    def test_fetch_gaia_json_parseable(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """The gaia.json file written by fetch must be valid JSON."""
        import io
        import tarfile as _tarfile

        # Build a tarball with a specific version field
        buf = io.BytesIO()
        with _tarfile.open(fileobj=buf, mode="w:gz") as tar:
            gaia_data = json.dumps({"version": "fetched", "skills": [{"id": "web-search"}]}).encode("utf-8")
            info = _tarfile.TarInfo(name="registry/gaia.json")
            info.size = len(gaia_data)
            tar.addfile(info, io.BytesIO(gaia_data))
            named_data = json.dumps({"buckets": {}}).encode("utf-8")
            info2 = _tarfile.TarInfo(name="registry/named-skills.json")
            info2.size = len(named_data)
            tar.addfile(info2, io.BytesIO(named_data))
        tarball = buf.getvalue()

        _patch_fetch_urlopen(monkeypatch, tarball)

        run_cli(monkeypatch, ["fetch"])

        data = json.loads((project / ".gaia" / "registry" / "gaia.json").read_text(encoding="utf-8"))
        assert data["version"] == "fetched"

    def test_fetch_downgrade_blocked(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """Attempting to fetch an older registry version must block and exit with 1."""
        # 1. Seed local registry with v2.0.0
        local_dir = project / ".gaia" / "registry"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_gaia = {
            "version": "2.0.0",
            "skills": []
        }
        (local_dir / "gaia.json").write_text(json.dumps(local_gaia), encoding="utf-8")

        # 2. Build remote tarball with v1.0.0
        tarball = _make_tarball_with_version(project, "1.0.0")
        _patch_fetch_urlopen(monkeypatch, tarball)

        # 3. Run fetch without --allow-downgrade -> should sys.exit(1)
        with pytest.raises(SystemExit) as excinfo:
            run_cli(monkeypatch, ["fetch"])
        assert excinfo.value.code == 1

        # Check stderr message
        err = capsys.readouterr().err
        assert "Error: Remote release v1.0.0 is older than local registry v2.0.0" in err

        # Local version must remain 2.0.0
        data = json.loads((local_dir / "gaia.json").read_text(encoding="utf-8"))
        assert data["version"] == "2.0.0"

    def test_fetch_downgrade_allowed(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """With --allow-downgrade, fetching an older registry version warns and proceeds."""
        # 1. Seed local registry with v2.0.0
        local_dir = project / ".gaia" / "registry"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_gaia = {
            "version": "2.0.0",
            "skills": []
        }
        (local_dir / "gaia.json").write_text(json.dumps(local_gaia), encoding="utf-8")

        # 2. Build remote tarball with v1.0.0
        tarball = _make_tarball_with_version(project, "1.0.0")
        _patch_fetch_urlopen(monkeypatch, tarball)

        # 3. Run fetch with --allow-downgrade -> should succeed
        run_cli(monkeypatch, ["fetch", "--allow-downgrade"])

        # Check stderr warning message
        err = capsys.readouterr().err
        assert "Warning: Downgrading registry from v2.0.0 to v1.0.0 (--allow-downgrade)" in err

        # Local version must be updated to 1.0.0
        data = json.loads((local_dir / "gaia.json").read_text(encoding="utf-8"))
        assert data["version"] == "1.0.0"

    def test_fetch_upgrade(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """Fetching a newer registry version succeeds without requiring flags."""
        # 1. Seed local registry with v1.0.0
        local_dir = project / ".gaia" / "registry"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_gaia = {
            "version": "1.0.0",
            "skills": []
        }
        (local_dir / "gaia.json").write_text(json.dumps(local_gaia), encoding="utf-8")

        # 2. Build remote tarball with v2.0.0
        tarball = _make_tarball_with_version(project, "2.0.0")
        _patch_fetch_urlopen(monkeypatch, tarball)

        # 3. Run fetch -> should succeed
        run_cli(monkeypatch, ["fetch"])

        # Local version must be updated to 2.0.0
        data = json.loads((local_dir / "gaia.json").read_text(encoding="utf-8"))
        assert data["version"] == "2.0.0"

    def test_fetch_equal_version(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """Fetching the same registry version succeeds without requiring flags."""
        # 1. Seed local registry with v1.0.0
        local_dir = project / ".gaia" / "registry"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_gaia = {
            "version": "1.0.0",
            "skills": []
        }
        (local_dir / "gaia.json").write_text(json.dumps(local_gaia), encoding="utf-8")

        # 2. Build remote tarball with v1.0.0
        tarball = _make_tarball_with_version(project, "1.0.0")
        _patch_fetch_urlopen(monkeypatch, tarball)

        # 3. Run fetch -> should succeed
        run_cli(monkeypatch, ["fetch"])

        # Local version must remain 1.0.0
        data = json.loads((local_dir / "gaia.json").read_text(encoding="utf-8"))
        assert data["version"] == "1.0.0"

    def test_fetch_malformed_local_registry(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """If local registry gaia.json is malformed, fetch prints a warning and proceeds."""
        # 1. Seed local registry with invalid JSON
        local_dir = project / ".gaia" / "registry"
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "gaia.json").write_text("invalid json!!!", encoding="utf-8")

        # 2. Build remote tarball with v2.0.0
        tarball = _make_tarball_with_version(project, "2.0.0")
        _patch_fetch_urlopen(monkeypatch, tarball)

        # 3. Run fetch -> should succeed
        run_cli(monkeypatch, ["fetch"])

        # Check warning output
        err = capsys.readouterr().err
        assert "Warning: Could not compare registry versions. Proceeding." in err

        # Local version must be updated to 2.0.0
        data = json.loads((local_dir / "gaia.json").read_text(encoding="utf-8"))
        assert data["version"] == "2.0.0"

    def test_fetch_malformed_remote_registry(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        """If remote registry gaia.json is malformed, fetch prints a warning and proceeds."""
        # 1. Seed local registry with v1.0.0
        local_dir = project / ".gaia" / "registry"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_gaia = {
            "version": "1.0.0",
            "skills": []
        }
        (local_dir / "gaia.json").write_text(json.dumps(local_gaia), encoding="utf-8")

        # 2. Build remote tarball with invalid JSON
        import io
        import tarfile as _tarfile
        buf = io.BytesIO()
        with _tarfile.open(fileobj=buf, mode="w:gz") as tar:
            gaia_data = b"invalid json remote!!!"
            info = _tarfile.TarInfo(name="registry/gaia.json")
            info.size = len(gaia_data)
            tar.addfile(info, io.BytesIO(gaia_data))
            
            named_data = json.dumps({"buckets": {}}).encode("utf-8")
            info2 = _tarfile.TarInfo(name="registry/named-skills.json")
            info2.size = len(named_data)
            tar.addfile(info2, io.BytesIO(named_data))
        tarball = buf.getvalue()

        _patch_fetch_urlopen(monkeypatch, tarball)

        # 3. Run fetch -> should succeed
        run_cli(monkeypatch, ["fetch"])

        # Check warning output
        err = capsys.readouterr().err
        assert "Warning: Could not compare registry versions. Proceeding." in err

        # Local version must be overwritten with the remote invalid content
        assert (local_dir / "gaia.json").read_text(encoding="utf-8") == "invalid json remote!!!"




# ---------------------------------------------------------------------------
# 10. TestReset — gaia reset --yes
# ---------------------------------------------------------------------------

class TestReset:
    """reset --yes clears state files from .gaia/ but preserves config.toml and .gitignore."""

    def _seed_state(self, project: Path) -> None:
        """Populate .gaia/ with state files that reset should delete."""
        gaia_dir = project / ".gaia"
        gaia_dir.mkdir(parents=True, exist_ok=True)
        (gaia_dir / "custom_state.json").write_text("{}", encoding="utf-8")
        (gaia_dir / "scan-state.json").write_text("{}", encoding="utf-8")
        (gaia_dir / ".gitignore").write_text("*.json\n", encoding="utf-8")

    def test_config_preserved(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """reset --yes must NOT delete .gaia/config.toml."""
        self._seed_state(project)
        run_cli(monkeypatch, ["--registry", str(project), "reset", "--yes"])
        assert (project / ".gaia" / "config.toml").exists(), \
            "config.toml must be preserved after reset"

    def test_gitignore_preserved(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """reset --yes must NOT delete .gaia/.gitignore."""
        self._seed_state(project)
        run_cli(monkeypatch, ["--registry", str(project), "reset", "--yes"])
        assert (project / ".gaia" / ".gitignore").exists(), \
            ".gaia/.gitignore must be preserved after reset"

    def test_state_files_cleared(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """reset --yes should remove .gaia/custom_state.json (state file, not config)."""
        self._seed_state(project)
        run_cli(monkeypatch, ["--registry", str(project), "reset", "--yes"])
        # custom_state.json is a state file and should be cleared
        assert not (project / ".gaia" / "custom_state.json").exists(), \
            "custom_state.json should be deleted by reset"

    def test_user_tree_cleared(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """reset --yes should remove the user's skill-tree.json."""
        self._seed_state(project)
        # Create a skill tree
        tree_path = project / "skill-trees" / "testuser" / "skill-tree.json"
        tree_path.parent.mkdir(parents=True, exist_ok=True)
        tree_path.write_text(json.dumps({"userId": "testuser", "unlockedSkills": []}), encoding="utf-8")

        run_cli(monkeypatch, ["--registry", str(project), "reset", "--yes"])

        assert not tree_path.exists(), "skill-tree.json should be deleted by reset"


# ---------------------------------------------------------------------------
# 11. TestPull — gaia pull calls fetch then scan (no git)
# ---------------------------------------------------------------------------

class TestPull:
    """pull calls fetch_command then scan_command; no git subprocess involvement."""

    def test_pull_calls_fetch_and_scan(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """pull must invoke both fetch_command and scan_command."""
        import gaia_cli.main as gaia_main

        calls: list[str] = []
        monkeypatch.setattr(gaia_main, "fetch_command", lambda args: calls.append("fetch"))
        monkeypatch.setattr(gaia_main, "scan_command", lambda args: calls.append("scan"))

        run_cli(monkeypatch, ["--registry", str(project), "pull"])

        assert "fetch" in calls, "pull must invoke fetch_command"
        assert "scan" in calls, "pull must invoke scan_command"

    def test_pull_fetch_before_scan(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        """pull must call fetch before scan (order matters for registry freshness)."""
        import gaia_cli.main as gaia_main

        calls: list[str] = []
        monkeypatch.setattr(gaia_main, "fetch_command", lambda args: calls.append("fetch"))
        monkeypatch.setattr(gaia_main, "scan_command", lambda args: calls.append("scan"))

        run_cli(monkeypatch, ["--registry", str(project), "pull"])

        assert calls.index("fetch") < calls.index("scan"), \
            "fetch must be called before scan in pull"

    def test_pull_no_git_subprocess(self, project: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """pull must not raise errors in a non-git directory (no git required)."""
        import gaia_cli.main as gaia_main

        # Confirm tmp_path is not a git repo by checking .git does not exist at root
        assert not (tmp_path / ".git").exists()

        monkeypatch.setattr(gaia_main, "fetch_command", lambda args: None)
        monkeypatch.setattr(gaia_main, "scan_command", lambda args: None)

        # Must not raise in a non-repo directory
        run_cli(monkeypatch, ["--registry", str(project), "pull"])


# ═══════════════════════════════════════════════════════════════════════════
# Relocated from test_pr540_review.py — TUI flags, force-color, registry paths
# (module-level pytestmark = [integration] applies to these too)
# ═══════════════════════════════════════════════════════════════════════════


def test_tui_flag_exists():
    from gaia_cli.main import get_parser
    parser, _ = get_parser()
    args = parser.parse_args(['--tui'])
    assert args.tui is True

def test_tui_usage_mentions_gaia():
    from gaia_cli.main import COMMAND_USAGE
    from helpers import strip_ansi
    plain = strip_ansi(COMMAND_USAGE)
    assert "Open command selector" in plain

def test_tui_flag_execs_skills():
    """--tui flag causes main() to call os.execvp to replace process with 'gaia skills'."""
    from gaia_cli.main import main

    # Record the arguments passed to os.execvp
    execvp_calls = []

    def mock_execvp(program, args):
        execvp_calls.append((program, args))
        # Raise SystemExit to mimic process replacement
        raise SystemExit(0)

    with patch.object(sys, "argv", ["gaia", "--tui"]):
        with patch("os.execvp", mock_execvp):
            with pytest.raises(SystemExit) as exc_info:
                main()

    # Verify execvp was called
    assert len(execvp_calls) == 1
    program, args = execvp_calls[0]
    # The final element of args should be 'skills'
    assert args[-1] == "skills"
    assert exc_info.value.code == 0

def test_resolve_registry_path_usage_in_formatting():
    from gaia_cli import formatting
    with patch('gaia_cli.formatting.resolve_registry_path') as mock_resolve:
        mock_resolve.return_value = os.getcwd()
        try:
            formatting._load_palette_from_registry()
        except Exception:
            pass
        mock_resolve.assert_called()

def test_resolve_registry_path_usage_in_tokens():
    try:
        from gaia_cli.tui import tokens
        with patch('gaia_cli.tui.tokens.resolve_registry_path') as mock_resolve:
            mock_resolve.return_value = os.getcwd()
            try:
                tokens._load_meta()
            except Exception:
                pass
            mock_resolve.assert_called()
    except ImportError:
        pytest.skip("textual not installed")

def test_scan_screen_ansi_passthrough():
    try:
        from gaia_cli.tui.screens.scan import ScanScreen
        from rich.text import Text

        screen = ScanScreen(registry_path=".")
        test_line = "\x1b[31mRed Text\x1b[0m"
        result = screen._style_line(test_line)

        assert isinstance(result, Text)
        assert len(result.spans) > 0
        assert "Red Text" in result.plain
    except ImportError:
        pytest.skip("textual/rich not installed")


# ═══════════════════════════════════════════════════════════════════════════
# Relocated from test_pr635_review.py — parser flag shadowing / --custom / --canon
# ═══════════════════════════════════════════════════════════════════════════


class TestScrutiny_AllFlagShadowing:
    """Scrutiny #5: --all flag naming.

    args.all shadows the Python builtin `all`. Verify the parser attribute
    is properly accessible and doesn't cause runtime issues.
    """

    def test_all_flag_accessible_on_namespace(self):
        """Verify that an argparse Namespace with 'all' attribute works correctly."""
        ns = SimpleNamespace(all=True)
        assert getattr(ns, "all", False) is True

        ns2 = SimpleNamespace(all=False)
        assert getattr(ns2, "all", False) is False

    def test_parser_produces_all_attribute(self):
        """Verify the actual parser produces args.all for the scan command."""
        from gaia_cli.main import get_parser
        parser, _ = get_parser()
        args = parser.parse_args(["scan", "--all"])
        assert getattr(args, "all", False) is True

    def test_parser_custom_on_tree(self):
        """Verify --custom flag on tree command."""
        from gaia_cli.main import get_parser
        parser, _ = get_parser()
        args = parser.parse_args(["tree", "--custom"])
        assert getattr(args, "custom", False) is True

    def test_parser_custom_on_graph(self):
        """Verify --custom flag on graph command."""
        from gaia_cli.main import get_parser
        parser, _ = get_parser()
        args = parser.parse_args(["graph", "--custom"])
        assert getattr(args, "custom", False) is True

    def test_parser_canon_on_tree(self):
        """Verify --canon flag on tree command."""
        from gaia_cli.main import get_parser
        parser, _ = get_parser()
        args = parser.parse_args(["tree", "--canon"])
        assert getattr(args, "canon", False) is True

    def test_parser_canon_on_graph(self):
        """Verify --canon flag on graph command."""
        from gaia_cli.main import get_parser
        parser, _ = get_parser()
        args = parser.parse_args(["graph", "--canon"])
        assert getattr(args, "canon", False) is True
