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
    (project / "notes.md").write_text("web-search\n")

    result = run_python(
        ["-m", "gaia_cli", "--registry", str(REPO_ROOT), "scan"],
        cwd=project,
        env={"GAIA_HOME": str(tmp_path / "home")},
    )

    assert result.returncode == 0, result.stderr
    assert "Matched 1 canonical skill(s)." in result.stdout


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
    (project / "notes.md").write_text("web-search\n")

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


def test_docs_build_can_run_from_registry_clone_without_registry_flag(tmp_path):
    result = run_python(
        ["-m", "gaia_cli", "docs", "build", "--check"],
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
