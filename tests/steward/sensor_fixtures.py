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
