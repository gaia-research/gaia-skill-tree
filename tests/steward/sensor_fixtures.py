"""Shared fixture builders for Steward sensor tests.

Sensors read Git's inventory, so a fixture repository must be a real Git
worktree. ``make_repo`` writes files, commits them, and returns the root;
``commit_all`` re-stages after a test mutates the tree.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Mapping


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def write_files(root: Path, files: Mapping[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def make_repo(root: Path, files: Mapping[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "steward-fixture@example.invalid")
    _git(root, "config", "user.name", "Steward Fixture")
    _git(root, "config", "commit.gpgsign", "false")
    write_files(root, files)
    commit_all(root, "fixture")
    return root.resolve()


def commit_all(root: Path, message: str = "update") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--allow-empty", "-m", message)


def tree_digest(root: Path) -> str:
    """Digest of every file outside .git, for read-only assertions."""

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if ".git" in path.relative_to(root).parts or not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


# A minimal, finding-free Gaia repository surface. Every registered sensor
# family needs its domain to exist: a sensor whose whole domain is missing is
# blind (coverage unknown), not clean. Fixtures that exercise the controller or
# CLI end to end call this so that "clean" means every sensor actually looked.
COMMANDS_INIT = (
    "import importlib\n"
    "import pkgutil\n\n\n"
    "def discover_commands():\n"
    "    for _, name, _ in pkgutil.iter_modules(__path__):\n"
    "        importlib.import_module(f\"gaia_cli.commands.{name}\")\n"
)

# Evidence types shared by the fixture meta.json and trustMagnitude.TYPE_WEIGHTS,
# so the taxonomy sensor has a real canonical list to compare against.
FIXTURE_EVIDENCE_TYPES = (
    "github-stars-own", "repo-own", "social-signal", "benchmark-result",
    "peer-review", "arxiv", "self-attestation", "fusion-recipe",
    "verifier-attestation", "proxy-containment",
)
FIXTURE_EVIDENCE_META = {"evidence": {"types": [{"id": item} for item in FIXTURE_EVIDENCE_TYPES]}}
TRUST_MAGNITUDE_STUB = "TYPE_WEIGHTS = {\n" + "".join(
    f"    {item!r}: 1.0,\n" for item in FIXTURE_EVIDENCE_TYPES
) + "}\n"

MINIMAL_GAIA_DOMAINS: dict[str, str] = {
    "pyproject.toml": (
        "[project]\n"
        'name = "fixture"\n'
        'version = "1.0.0"\n'
        'license = "MIT"\n'
        'dependencies = ["pyyaml>=6.0"]\n'
        "\n"
        "[project.scripts]\n"
        'gaia = "gaia_cli.main:main"\n'
        "\n"
        "[tool.pytest.ini_options]\n"
        "markers = []\n"
    ),
    "LICENSE": "MIT License\n",
    "packages/cli-npm/package.json": '{"name": "fixture", "version": "1.0.0", "license": "MIT"}\n',
    "src/gaia_cli/__init__.py": "",
    "src/gaia_cli/impl.py": 'MUTATING_DEV_COMMANDS = frozenset({"add"})\n',
    "src/gaia_cli/main.py": (
        "from gaia_cli import impl, trustMagnitude\n\n\n"
        "def main():\n    return impl, trustMagnitude\n"
    ),
    "src/gaia_cli/trustMagnitude.py": TRUST_MAGNITUDE_STUB,
    "src/gaia_cli/commands/__init__.py": COMMANDS_INIT,
    "src/gaia_cli/commands/dev/__init__.py": (
        "MUTATING_DEV_COMMANDS = {\"add\"}\n\n\n"
        "def configure(parser):\n"
        "    dev_sub = parser.add_subparsers(dest=\"dev_command\")\n"
        "    dev_sub.add_parser(\"add\")\n"
        "    return dev_sub\n"
    ),
    "tests/test_fixture.py": "def test_fixture():\n    assert True\n",
    ".github/workflows/ci.yml": (
        "name: ci\n"
        "on: push\n"
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 5\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
    ),
    "docs/index.html": (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Fixture</title>\n</head>\n<body><p>ok</p></body>\n</html>\n"
    ),
    "docs/js/app.js": "document.title = 'fixture';\n",
    "registry/named/fixture/example.md": (
        "---\n"
        "id: fixture/example\n"
        "name: example\n"
        "contributor: fixture\n"
        "timeline:\n"
        '  - action: created\n    timestamp: "2026-01-01T00:00:00Z"\n'
        "---\n"
        "# Example\n"
    ),
}


def write_minimal_gaia_domains(root: Path, *, overwrite: bool = False) -> None:
    """Write the minimal clean domain files that are not already present."""

    for relative, content in MINIMAL_GAIA_DOMAINS.items():
        path = root / relative
        if path.exists() and not overwrite:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def track_all(root: Path) -> None:
    """Make ``root`` a Git worktree whose index tracks every current file."""

    if not (root / ".git").exists():
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.email", "steward-fixture@example.invalid")
        _git(root, "config", "user.name", "Steward Fixture")
        _git(root, "config", "commit.gpgsign", "false")
    _git(root, "add", "-A")
