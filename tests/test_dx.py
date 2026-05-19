import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.main import main
from gaia_cli.scanner import scan_repo, scan_repo_detailed


def run_cli(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["gaia", *argv])
    main()


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
    (tmp_path / "src" / "app.py").write_text("web-search\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "noise.js").write_text("voice-agent\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "packed-refs").write_text("autonomous-debug\n")

    tokens = scan_repo()

    assert "web-search" in tokens
    assert "voice-agent" not in tokens
    assert "autonomous-debug" not in tokens


def test_scan_repo_detailed_reports_file_and_candidate_counts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gaia").mkdir()
    (tmp_path / ".gaia" / "config.json").write_text(
        '{"scanPaths": ["docs"], "gaiaUser": "juno"}'
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "one.md").write_text("web-search and code-generation")
    (tmp_path / "docs" / "image.png").write_bytes(b"not scanned")

    detailed = scan_repo_detailed()

    assert detailed["files_scanned"] == 1
    assert detailed["paths_found"] == ["docs"]
    assert "web-search" in detailed["tokens"]
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
    assert "gaia scan [--quiet] [--auto-promote]" in output
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
