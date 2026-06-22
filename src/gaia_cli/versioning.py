"""Version synchronization helpers for Gaia release tooling."""

from __future__ import annotations

import json
import re
from pathlib import Path

from gaia_cli.registry import registry_graph_path


VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def bump_version(version: str, bump: str) -> str:
    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(f"Invalid semantic version: {version}")
    major, minor, patch = (int(part) for part in match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown version bump: {bump}")


def _read_pyproject_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise ValueError(f"No version field found in {path}")


def read_versions(root: str | Path) -> dict[str, str]:
    root = Path(root)
    files = {
        "pyproject": root / "pyproject.toml",
        "cliNPM": root / "packages" / "cli-npm" / "package.json",
        "mcp": root / "packages" / "mcp" / "package.json",
        "registry": Path(registry_graph_path(root)),
        "docsGraph": root / "docs" / "graph" / "gaia.json",
    }
    versions = {
        "pyproject": _read_pyproject_version(files["pyproject"]),
        "cliNPM": json.loads(files["cliNPM"].read_text(encoding="utf-8"))["version"],
        "mcp": json.loads(files["mcp"].read_text(encoding="utf-8"))["version"],
    }
    if files["registry"].exists():
        versions["registry"] = json.loads(files["registry"].read_text(encoding="utf-8"))["version"]
    if files["docsGraph"].exists():
        versions["docsGraph"] = json.loads(files["docsGraph"].read_text(encoding="utf-8"))["version"]
    return versions


def verify_lockstep(root: str | Path) -> str:
    versions = read_versions(root)
    unique = set(versions.values())
    if len(unique) != 1:
        details = ", ".join(f"{name}={version}" for name, version in versions.items())
        raise ValueError(f"Version files disagree before bump: {details}")
    return unique.pop()


def _replace_pyproject_version(path: Path, new_version: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'^version = "[^"]+"$', f'version = "{new_version}"', text, count=1, flags=re.MULTILINE)
    path.write_text(text, encoding="utf-8")


def _replace_package_version(path: Path, new_version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = new_version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _replace_registry_version(path: Path, new_version: str) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = new_version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def bump_versions(root: str | Path, bump: str) -> str:
    root = Path(root)
    current = verify_lockstep(root)
    new_version = bump_version(current, bump)
    return sync_versions(root, new_version)


def sync_versions(root: str | Path, version: str) -> str:
    root = Path(root)
    _replace_pyproject_version(root / "pyproject.toml", version)
    _replace_package_version(root / "packages" / "cli-npm" / "package.json", version)
    _replace_package_version(root / "packages" / "mcp" / "package.json", version)
    _replace_registry_version(Path(registry_graph_path(root)), version)
    _replace_registry_version(root / "docs" / "graph" / "gaia.json", version)
    return version
