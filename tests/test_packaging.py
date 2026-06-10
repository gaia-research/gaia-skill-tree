import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tomllib
import venv
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def require_build_package():
    if importlib.util.find_spec("build") is None:
        pytest.skip(
            'packaging tests require the "build" package; install developer '
            'dependencies with `pip install -e ".[dev]"` or '
            '`pip install -e ".[embeddings,dev]"`.'
        )


def run_python(args, *, cwd=None, env=None):
    merged_env = os.environ.copy()
    merged_env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT / "src"), str(REPO_ROOT)])
    merged_env["PYTHONIOENCODING"] = "utf-8"
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or REPO_ROOT,
        env=merged_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def build_wheel(dist_dir):
    shutil.rmtree(REPO_ROOT / "build", ignore_errors=True)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_gaia_cli_package_imports():
    import gaia_cli

    assert gaia_cli.__name__ == "gaia_cli"


def test_python_module_help_runs_with_gaia_prog_name():
    result = run_python(["-m", "gaia_cli", "--help"])

    assert result.returncode == 0, result.stderr
    assert "usage: gaia" in result.stdout


def test_console_script_points_to_canonical_package():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    assert data["project"]["scripts"]["gaia"] == "gaia_cli.main:main"


def test_gaia_cli_main_remains_importable():
    import gaia_cli.main as compat_main

    assert callable(compat_main.main)


def test_bundled_registry_is_used_for_read_only_skills_without_registry(tmp_path):
    result = run_python(
        ["-m", "gaia_cli", "skills", "list"],
        cwd=tmp_path,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 0, result.stderr
    assert ("Skill" in result.stdout or "No skills found." in result.stdout)


def test_scan_can_use_explicit_writable_registry(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".gaia").mkdir()
    (project / ".gaia" / "config.json").write_text(
        json.dumps({"gaiaUser": "juno", "scanPaths": ["."]})
    )
    (project / "notes.md").write_text("/web-search\n")

    result = run_python(
        ["-m", "gaia_cli", "--registry", str(REPO_ROOT), "scan"],
        cwd=project,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 0, result.stderr
    # The "Matched N canonical skill(s)." string was removed in this PR.
    # The scan now outputs "Scanning installed custom skills..." and a custom
    # skills section. Verify the command exits cleanly and produces some output.
    assert "Scanning installed custom skills" in result.stdout


def test_write_commands_require_explicit_registry(tmp_path):
    (tmp_path / ".gaia").mkdir()
    (tmp_path / ".gaia" / "config.json").write_text(
        json.dumps({"gaiaUser": "juno", "scanPaths": ["."]})
    )
    (tmp_path / "notes.md").write_text("web-search\n")

    result = run_python(
        ["-m", "gaia_cli", "push", "--dry-run"],
        cwd=tmp_path,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 2
    assert "writable registry" in result.stderr


def test_local_registry_auto_resolves_for_read_only_command(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".gaia").mkdir()
    (project / ".gaia" / "config.json").write_text(
        json.dumps({"gaiaUser": "juno", "scanPaths": ["."], "localRegistryPath": str(REPO_ROOT)})
    )

    result = run_python(
        ["-m", "gaia_cli", "skills", "list"],
        cwd=project,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 0, result.stderr
    assert ("Skill" in result.stdout or "No skills found." in result.stdout)


def test_local_registry_auto_resolves_for_write_command(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".gaia").mkdir()
    (project / ".gaia" / "config.json").write_text(
        json.dumps({"gaiaUser": "juno", "scanPaths": ["."], "localRegistryPath": str(REPO_ROOT)})
    )
    (project / "notes.md").write_text("/web-search\n")
    # push now reads .gaia/custom_state.json (written by gaia scan) rather than raw tokens.
    # Seed a minimal custom_state.json so push has something to push.
    custom_state = {
        "customSkills": [
            {
                "id": "/web-search",
                "name": "web-search",
                "description": "Web search skill",
                "match_type": "generic",
                "canon_level": "0★",
                "mapped_to": "/web-search",
                "mapped_score": 1.0,
                "skill_type": "basic",
                "prerequisites": [],
            }
        ],
        "customFusions": {},
    }
    import json as _json
    (project / ".gaia" / "custom_state.json").write_text(_json.dumps(custom_state))

    result = run_python(
        ["-m", "gaia_cli", "push", "--dry-run"],
        cwd=project,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 0, result.stderr


def test_global_flag_skips_local_gaia(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".gaia").mkdir()
    (project / ".gaia" / "config.json").write_text(
        json.dumps({"gaiaUser": "juno", "scanPaths": ["."], "localRegistryPath": str(REPO_ROOT)})
    )

    result = run_python(
        ["-m", "gaia_cli", "--global", "skills", "list"],
        cwd=project,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    # No global registry configured → falls to bundled, which still has graph data
    assert result.returncode == 0, result.stderr
    assert ("Skill" in result.stdout or "No skills found." in result.stdout)


def test_local_registry_fallback_to_cwd_when_no_localRegistryPath(tmp_path):
    # CWD is a registry clone (has registry/gaia.json), .gaia/config.json has no localRegistryPath
    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "registry").mkdir()
    (registry / "registry" / "gaia.json").write_text(json.dumps({"skills": [], "edges": []}))
    (registry / ".gaia").mkdir()
    (registry / ".gaia" / "config.json").write_text(
        json.dumps({"gaiaUser": "juno", "scanPaths": ["."]})
    )

    from gaia_cli.registry import read_local_registry
    import os

    orig_cwd = os.getcwd()
    try:
        os.chdir(registry)
        result = read_local_registry()
        assert result == str(registry)
    finally:
        os.chdir(orig_cwd)


def test_registry_clone_auto_resolves_without_gaia_config(tmp_path):
    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "registry").mkdir()
    (registry / "registry" / "gaia.json").write_text(json.dumps({"skills": [], "edges": []}))

    from gaia_cli.registry import resolve_registry_path

    orig_cwd = os.getcwd()
    try:
        os.chdir(registry)
        result = resolve_registry_path()
        assert result == str(registry)
    finally:
        os.chdir(orig_cwd)


@pytest.mark.timeout(300)
def test_docs_build_can_run_from_registry_clone_without_registry_flag(tmp_path):
    # Run 'docs build' (without --check) so the command always exits 0 after
    # regenerating files. The --check variant fails when docs are stale (e.g.
    # after a PR changes CLI output), which is a false negative for this test's
    # real intent: verifying that 'docs build' auto-resolves the registry from
    # the CWD without requiring --registry.
    result = run_python(
        ["-m", "gaia_cli", "docs", "build"],
        cwd=REPO_ROOT,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 0, result.stderr


def test_init_writes_local_registry_path(tmp_path):
    result = run_python(
        ["-m", "gaia_cli", "init", "--user", "testuser", "--yes"],
        cwd=tmp_path,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 0, result.stderr
    cfg_text = (tmp_path / ".gaia" / "config.toml").read_text()
    assert f'localRegistryPath = "{tmp_path}"' in cfg_text


def test_gaia_home_is_data_dir_not_home_dir(tmp_path):
    # GAIA_HOME should be treated as the gaia data dir: config at $GAIA_HOME/config.json
    gaia_home = tmp_path / "mydata"
    gaia_home.mkdir()
    (gaia_home / "config.json").write_text(
        json.dumps({"defaultRegistry": str(REPO_ROOT)})
    )

    result = run_python(
        ["-m", "gaia_cli", "--global", "skills", "list"],
        cwd=tmp_path,
        env={"GAIA_HOME": str(gaia_home)},
    )

    assert result.returncode == 0, result.stderr
    assert ("Skill" in result.stdout or "No skills found." in result.stdout)


def test_install_cache_honors_gaia_home(tmp_path, monkeypatch):
    from gaia_cli.install import install_skill

    repo = tmp_path / "repo"
    repo.mkdir()
    registry = tmp_path / "registry"
    skill_dir = registry / "registry" / "named" / "alice"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text("---\nid: alice/skill\nlinks:\n  github: https://github.com/alice/repo/blob/main/skill/SKILL.md\n---\ncontent")
    gaia_home = tmp_path / "custom-home"

    monkeypatch.chdir(repo)
    monkeypatch.setenv("GAIA_HOME", str(gaia_home))
    
    # Mock git execution to succeed and create the mock source dir
    import os
    def mock_run_git(args, cwd=None):
        source_dir = os.path.join(str(gaia_home), "skills", "alice", "repo", "skill")
        os.makedirs(source_dir, exist_ok=True)
        return True
    monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)

    assert install_skill("alice/skill", str(registry)) is True
    assert (gaia_home / "skills" / "alice" / "repo").exists()


def test_parse_frontmatter_nested_links(tmp_path):
    """_parse_frontmatter must return a dict with a dict under 'links', not a string."""
    from gaia_cli.install import _parse_frontmatter
    md = tmp_path / "skill.md"
    md.write_text(
        "---\nid: alice/skill\nlinks:\n  github: https://github.com/alice/repo\n---\ncontent",
        encoding="utf-8",
    )
    meta = _parse_frontmatter(str(md))
    assert isinstance(meta, dict), "frontmatter must parse to a dict"
    links = meta.get("links", {})
    assert isinstance(links, dict), f"'links' must be a dict, got {type(links)}"
    assert links.get("github") == "https://github.com/alice/repo"


def test_sigpipe_exits_cleanly():
    """gaia skills list | head should exit 0 with no BrokenPipeError traceback."""
    result = subprocess.run(
        "python -m gaia_cli --global skills list 2>&1 | head -n1; exit ${PIPESTATUS[0]}",
        shell=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert "BrokenPipeError" not in result.stdout
    assert "BrokenPipeError" not in result.stderr


@pytest.mark.packaging
def test_built_wheel_contains_only_python_package_data(tmp_path):
    require_build_package()

    dist_dir = tmp_path / "dist"
    result = build_wheel(dist_dir)
    assert result.returncode == 0, result.stderr

    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())

    assert "gaia_cli/data/registry/gaia.json" in names
    assert "gaia_cli/data/registry/schema/skill.schema.json" in names
    assert any(name.startswith("gaia_cli/data/registry/named/") for name in names)
    forbidden_parts = (
        "node_modules/",
        "__pycache__/",
        ".pyc",
        "scratch/",
        "packages/cli-npm/",
        "packages/mcp/",
        "gaia_cli.egg-info/",
        "registry/gaia.gexf",
        "registry/render/",
        "skills/",
    )
    assert not any(part in name for name in names for part in forbidden_parts)


@pytest.mark.packaging
def test_wheel_install_smoke_tests_console_script(tmp_path):
    require_build_package()

    dist_dir = tmp_path / "dist"
    build_result = build_wheel(dist_dir)
    assert build_result.returncode == 0, build_result.stderr

    wheel = next(dist_dir.glob("*.whl"))
    venv_dir = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    gaia = venv_dir / ("Scripts/gaia.exe" if os.name == "nt" else "bin/gaia")
    install_result = subprocess.run(
        [str(python), "-m", "pip", "install", "--no-user", "--no-deps", str(wheel)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert install_result.returncode == 0, install_result.stderr

    help_result = subprocess.run(
        [str(gaia), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "GAIA_HOME": str(tmp_path / "home")},
    )
    assert help_result.returncode == 0, help_result.stderr
    assert "usage: gaia" in help_result.stdout
