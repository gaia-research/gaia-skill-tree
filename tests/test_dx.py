import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.main import main
from gaia_cli.scanner import scan_repo, scan_repo_detailed


def run_cli(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["gaia", *argv])
    main()


def _write_json_registry(tmp_path, entries: list[dict]) -> None:
    """Write registry/named-skills.json for CLI-level tests."""
    registry = tmp_path / "registry"
    registry.mkdir(exist_ok=True)
    buckets: dict = {}
    for meta in entries:
        ref = meta.get("genericSkillRef", meta["id"].replace("/", "-"))
        buckets.setdefault(ref, []).append(meta)
    (registry / "named-skills.json").write_text(
        json.dumps({"buckets": buckets, "awaitingClassification": []}),
        encoding="utf-8",
    )


def test_init_accepts_flags_and_uses_current_registry_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    run_cli(
        monkeypatch,
        [
            "init",
            "--user",
            "juno",
            "--scan",
            "AGENTS.md",
            "--scan",
            "scripts",
        ],
    )

    config = parse_config(tmp_path / ".gaia" / "config.toml")
    assert config["username"] == "juno"
    assert config["gaiaRegistryRef"] == "https://github.com/mbtiongson1/gaia-skill-tree"
    assert config["scanPaths"] == ["AGENTS.md", "scripts"]
    assert config["autoPromptCombinations"] is False


def test_init_yes_mode_preserves_non_interactive_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Prevent auto-detection from picking up the parent repo's username
    import gaia_cli.main as gaia_main
    monkeypatch.setattr(gaia_main, "_detect_github_username", lambda: None)

    run_cli(monkeypatch, ["init", "--yes"])

    config = parse_config(tmp_path / ".gaia" / "config.toml")
    assert config["username"] == "gaiabot"
    assert config["gaiaRegistryRef"] == "https://github.com/mbtiongson1/gaia-skill-tree"
    assert config["scanPaths"] == ["scripts", "packages/cli-npm"]


def test_scan_repo_skips_generated_and_vendor_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gaia").mkdir()
    (tmp_path / ".gaia" / "config.json").write_text(
        '{"scanPaths": ["."], "gaiaUser": "juno"}'
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("/web-search\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "noise.js").write_text("/voice-agent\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "packed-refs").write_text("/autonomous-debug\n")

    tokens = scan_repo()

    assert "/web-search" in tokens
    assert "/voice-agent" not in tokens
    assert "/autonomous-debug" not in tokens


def test_scan_repo_detailed_reports_file_and_candidate_counts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gaia").mkdir()
    (tmp_path / ".gaia" / "config.json").write_text(
        '{"scanPaths": ["docs"], "gaiaUser": "juno"}'
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "one.md").write_text("/web-search and /code-generation")
    (tmp_path / "docs" / "image.png").write_bytes(b"not scanned")

    detailed = scan_repo_detailed()

    assert detailed["files_scanned"] == 1
    assert detailed["paths_found"] == ["docs"]
    assert "/web-search" in detailed["tokens"]
    assert detailed["candidate_count"] >= 2


def test_top_level_install_commands_are_restored(monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, ["install", "--help"])
    assert exc.value.code == 0

    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, ["uninstall", "--help"])
    assert exc.value.code == 0


def test_top_level_help_shows_all_public_commands_with_usage(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, ["--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    for command in [
        "init",
        "scan",
        "pull",
        "tree",
        "push",
        "propose",
        "version",
        "mcp",
        "release",
        "graph",
        "appraise",
        "promote",
        "docs",
        "lookup",
        "skills",
    ]:
        assert command in output
    assert "_hook" not in output
    assert "gaia scan [--quiet]" in output
    assert "gaia skills search <query>" in output


def test_skills_help_shows_subcommands_with_usage(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, ["skills", "--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    for command in ["list", "search", "info", "install", "uninstall"]:
        assert command in output
    assert "gaia skills list [--exclude-pending]" in output
    assert "gaia skills install <skill> [--global | --local]" in output


def test_bare_skills_command_prints_skills_help(monkeypatch, capsys):
    run_cli(monkeypatch, ["skills"])

    output = capsys.readouterr().out
    assert "usage: gaia skills" in output
    assert "gaia skills info <skill_id>" in output


def test_skills_info_accepts_leading_slash_named_skill_id(tmp_path, monkeypatch, capsys):
    named_dir = tmp_path / "registry" / "named" / "testuser"
    named_dir.mkdir(parents=True)
    (named_dir / "my-skill.md").write_text(
        "---\n"
        "id: testuser/my-skill\n"
        "name: My Skill\n"
        "level: 2★\n"
        "description: Test skill.\n"
        "---\n"
        "Content here.",
        encoding="utf-8",
    )

    run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "info", "/testuser/my-skill"])

    output = capsys.readouterr().out
    assert "testuser/my-skill" in output
    assert "Test skill." in output


def test_promote_label_override_is_not_available(monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, ["promote", "web-search", "--label", "3★"])
    assert exc.value.code == 2


def test_lookup_lists_named_implementation_roles(tmp_path, monkeypatch, capsys):
    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "gaia.json").write_text(
        '{"skills":[{"id":"web-search","name":"Web Search","type":"basic","level":"1★","description":"Find web pages.","prerequisites":[]}]}',
        encoding="utf-8",
    )
    (registry / "named-skills.json").write_text(
        '{"buckets":{"web-search":[{"id":"alice/search","name":"Alice Search","origin":true,"role":"origin"},{"id":"bob/search","name":"Bob Search","origin":false,"role":"variant"}]}}',
        encoding="utf-8",
    )

    run_cli(monkeypatch, ["--registry", str(tmp_path), "lookup", "web-search"])

    output = capsys.readouterr().out
    assert "Web Search" in output
    assert "Type: basic    Level: 1★" in output
    assert "[origin] Alice Search (alice/search)" in output
    assert "[variant] Bob Search (bob/search)" in output

    # Verify canon flag reveals slash ID
    run_cli(monkeypatch, ["--registry", str(tmp_path), "--canon", "lookup", "web-search"])
    output_canon = capsys.readouterr().out
    assert "/web-search" in output_canon


def parse_config(path):
    data = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        value = raw.strip()
        if value.startswith("["):
            data[key.strip()] = [item.strip().strip('"') for item in value[1:-1].split(",") if item.strip()]
        elif value in ("true", "false"):
            data[key.strip()] = value == "true"
        else:
            data[key.strip()] = value.strip('"')
    return data


# ---------------------------------------------------------------------------
# gaia skills list / search / info  (CLI-level)
# ---------------------------------------------------------------------------


def test_skills_list_shows_skills_from_named_skills_json(tmp_path, monkeypatch, capsys):
    """gaia skills list prints skills from registry/named-skills.json."""
    _write_json_registry(
        tmp_path,
        [
            {"id": "alice/search", "name": "Alice Search", "level": "2★", "type": "basic", "description": "Fast search."},
            {"id": "bob/code", "name": "Bob Code", "level": "3★", "type": "basic", "description": "Code gen."},
        ],
    )
    run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "list"])
    output = capsys.readouterr().out
    assert "alice/search" in output
    assert "bob/code" in output


def test_skills_list_shows_suite_skill_entry(tmp_path, monkeypatch, capsys):
    """Suite skills appear in `gaia skills list` output."""
    _write_json_registry(
        tmp_path,
        [
            {
                "id": "testuser/my-suite",
                "name": "My Suite",
                "level": "5★",
                "type": "basic",
                "description": "A test suite.",
                "suiteComponents": ["testuser/alpha"],
            },
        ],
    )
    run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "list"])
    output = capsys.readouterr().out
    assert "testuser/my-suite" in output


def test_skills_search_filters_by_name(tmp_path, monkeypatch, capsys):
    """gaia skills search <query> returns skills matching the name and excludes non-matches."""
    _write_json_registry(
        tmp_path,
        [
            {"id": "testuser/alpha-skill", "name": "Alpha Skill", "level": "2★", "type": "basic", "description": "Does alpha things."},
            {"id": "testuser/beta-skill", "name": "Beta Skill", "level": "2★", "type": "basic", "description": "Does beta things."},
        ],
    )
    run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "search", "alpha"])
    output = capsys.readouterr().out
    assert "alpha-skill" in output
    assert "beta-skill" not in output


def test_skills_search_filters_by_description(tmp_path, monkeypatch, capsys):
    """gaia skills search matches on description field, not only name."""
    _write_json_registry(
        tmp_path,
        [
            {"id": "testuser/x", "name": "X", "level": "2★", "type": "basic", "description": "uniqueterm in description"},
            {"id": "testuser/y", "name": "Y", "level": "2★", "type": "basic", "description": "no match here"},
        ],
    )
    run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "search", "uniqueterm"])
    output = capsys.readouterr().out
    assert "testuser/x" in output
    assert "testuser/y" not in output


def test_skills_info_shows_level_and_description(tmp_path, monkeypatch, capsys):
    """gaia skills info outputs the skill level and description."""
    _write_json_registry(
        tmp_path,
        [
            {
                "id": "testuser/my-skill",
                "name": "My Skill",
                "level": "3★",
                "type": "basic",
                "description": "Does something useful.",
            }
        ],
    )
    run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "info", "testuser/my-skill"])
    output = capsys.readouterr().out
    assert "testuser/my-skill" in output
    assert "Does something useful." in output


def test_skills_info_exits_nonzero_for_unknown_skill(tmp_path, monkeypatch, capsys):
    """gaia skills info exits with code 1 when skill_id is not found."""
    _write_json_registry(tmp_path, [])
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "info", "nobody/nope"])
    assert exc.value.code == 1


def test_skills_install_creates_manifest_entry_via_cli(tmp_path, monkeypatch):
    """gaia skills install <skill> adds an entry to .gaia/install-manifest.json."""
    monkeypatch.chdir(tmp_path)
    _write_json_registry(
        tmp_path,
        [
            {
                "id": "testuser/test-skill",
                "name": "Test Skill",
                "links": {"github": "https://github.com/testuser/repo/blob/main/test-skill/SKILL.md"},
            }
        ],
    )

    def mock_run_git(args, cwd=None):
        if args[0] == "clone":
            os.makedirs(os.path.join(args[-1], "test-skill"), exist_ok=True)
        return True

    monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
    monkeypatch.setattr(
        "gaia_cli.install.get_global_cache_dir",
        lambda: str(tmp_path / ".gaia" / "skills"),
    )

    run_cli(monkeypatch, ["--registry", str(tmp_path), "skills", "install", "testuser/test-skill"])

    from gaia_cli.install import load_manifest
    manifest = load_manifest()
    assert any(e["id"] == "testuser/test-skill" for e in manifest["installed"])


def test_skills_uninstall_removes_skill_via_cli(tmp_path, monkeypatch):
    """gaia skills uninstall <skill> removes the skill from manifest and filesystem."""
    monkeypatch.chdir(tmp_path)

    skill_path = tmp_path / ".agents" / "skills" / "test-skill"
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text("content")

    from gaia_cli.install import save_manifest
    save_manifest({"installed": [{"id": "testuser/test-skill", "localPath": str(skill_path)}]})

    run_cli(monkeypatch, ["skills", "uninstall", "testuser/test-skill"])

    from gaia_cli.install import load_manifest
    manifest = load_manifest()
    assert not any(e["id"] == "testuser/test-skill" for e in manifest["installed"])


def test_skills_uninstall_nonexistent_exits_nonzero(tmp_path, monkeypatch):
    """BUG: gaia skills uninstall on a non-installed skill exits 0 (should exit 1).

    Because uninstall_skill() returns True for non-existent skills,
    skills_command() never calls sys.exit(1) for this case.
    When the underlying bug is fixed, change the assertion to expect SystemExit(1).
    """
    monkeypatch.chdir(tmp_path)
    from gaia_cli.install import save_manifest
    save_manifest({"installed": []})

    # BUG: should raise SystemExit(1) but currently succeeds (exits 0 silently)
    # If the bug is fixed, this line will raise SystemExit, changing test behaviour.
    with pytest.raises(SystemExit) as excinfo:
        run_cli(monkeypatch, ["skills", "uninstall", "nobody/not-installed"])
    assert excinfo.value.code == 1


def test_gaia_install_command_installs_skill(tmp_path, monkeypatch):
    """gaia install <skill> (top-level command) creates a manifest entry."""
    monkeypatch.chdir(tmp_path)
    _write_json_registry(
        tmp_path,
        [
            {
                "id": "testuser/test-skill",
                "name": "Test Skill",
                "links": {"github": "https://github.com/testuser/repo/blob/main/test-skill/SKILL.md"},
            }
        ],
    )

    def mock_run_git(args, cwd=None):
        if args[0] == "clone":
            os.makedirs(os.path.join(args[-1], "test-skill"), exist_ok=True)
        return True

    monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
    monkeypatch.setattr(
        "gaia_cli.install.get_global_cache_dir",
        lambda: str(tmp_path / ".gaia" / "skills"),
    )

    run_cli(monkeypatch, ["--registry", str(tmp_path), "install", "testuser/test-skill"])

    from gaia_cli.install import load_manifest
    manifest = load_manifest()
    assert any(e["id"] == "testuser/test-skill" for e in manifest["installed"])


def test_gaia_uninstall_command_removes_skill(tmp_path, monkeypatch):
    """gaia uninstall <skill> (top-level command) removes the manifest entry."""
    monkeypatch.chdir(tmp_path)

    skill_path = tmp_path / ".agents" / "skills" / "test-skill"
    skill_path.mkdir(parents=True)

    from gaia_cli.install import save_manifest
    save_manifest({"installed": [{"id": "testuser/test-skill", "localPath": str(skill_path)}]})

    run_cli(monkeypatch, ["uninstall", "testuser/test-skill"])

    from gaia_cli.install import load_manifest
    manifest = load_manifest()
    assert not any(e["id"] == "testuser/test-skill" for e in manifest["installed"])


def test_init_force_overwrite(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    # First init
    run_cli(monkeypatch, ["init", "--user", "firstuser", "--yes"])
    config = parse_config(tmp_path / ".gaia" / "config.toml")
    assert config["username"] == "firstuser"

    # Second init without --force (should print message and not overwrite)
    run_cli(monkeypatch, ["init", "--user", "seconduser", "--yes"])
    output = capsys.readouterr().out
    assert "Gaia is already initialized in this repository. Use --force to overwrite." in output
    config = parse_config(tmp_path / ".gaia" / "config.toml")
    assert config["username"] == "firstuser"  # unchanged

    # Third init with --force (should overwrite)
    run_cli(monkeypatch, ["init", "--user", "seconduser", "--yes", "--force"])
    config = parse_config(tmp_path / ".gaia" / "config.toml")
    assert config["username"] == "seconduser"  # overwritten

