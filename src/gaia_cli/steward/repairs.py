"""The one deliberately narrow, zero-LLM Steward Class A repair.

This module is intentionally not a generic file synchronizer.  It owns exactly
the checked-in schema bundle, where the canonical registry tree is read-only
and the bundle is the only writable project surface.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from gaia_cli.steward.policy import RepairExecutorPolicy


CANONICAL_ROOT = Path("registry/schema")
MIRROR_ROOT = Path("src/gaia_cli/data/registry/schema")
EXECUTOR_ID = "bundled-schema-mirror"
SYNC_CHECK_COMMAND = "python scripts/sync_bundled_schemas.py --check"
GIT_STATUS_COMMAND = (
    "git status --porcelain=v1 --untracked-files=all -- src/gaia_cli/data/registry/schema"
)


class RepairError(RuntimeError):
    """A repair could not be proven safe; callers must leave debt open."""


class RepairBlocked(RepairError):
    """A precondition or policy ceiling deliberately prevented mutation."""


@dataclass(frozen=True)
class TreeFile:
    relative: str
    digest: str
    stat_key: tuple[int, int, int, int]


@dataclass(frozen=True)
class TreeManifest:
    root: Path
    files: Mapping[str, TreeFile]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(self.files))


def repair_bundled_schema_mirror(
    repo_root: Path,
    executor: RepairExecutorPolicy,
    *,
    state_root: Path,
) -> dict[str, object]:
    """Stage, prove, and atomically install the exact canonical schema mirror.

    The caller must hold Steward's transaction lock.  On every failed proof or
    interruption this function restores the previous mirror bytes before
    returning or raising.
    """

    root = repo_root.resolve()
    _validate_executor(executor)
    canonical = _manifest(root, CANONICAL_ROOT, required=True, json_only=True)
    mirror = _manifest(root, MIRROR_ROOT, required=False, json_only=False)
    _assert_clean_target(root)

    extras = sorted(set(mirror.files) - set(canonical.files))
    if extras:
        raise RepairBlocked(
            "bundled schema mirror has bundled-only paths; refusing deletion: " + ", ".join(extras)
        )

    changed = tuple(
        path
        for path in canonical.paths
        if path not in mirror.files or canonical.files[path].digest != mirror.files[path].digest
    )
    if not changed:
        _verify(root, canonical)
        return {
            "executor": EXECUTOR_ID,
            "status": "no_change",
            "plannedPaths": [],
            "repairedPaths": [],
            "verified": {"recursiveParity": True, "syncCheck": True},
        }

    _ensure_plain_ancestors(root, MIRROR_ROOT.parent)
    state_root.mkdir(parents=True, exist_ok=True)
    stage_root = Path(tempfile.mkdtemp(prefix="class-a-schema-", dir=state_root))
    stage = stage_root / "schema"
    rollback = stage_root / "rollback-schema"
    had_mirror = (root / MIRROR_ROOT).exists()
    installed = False
    try:
        _copy_manifest(root / CANONICAL_ROOT, canonical, stage)
        if had_mirror:
            shutil.copystat(root / MIRROR_ROOT, stage, follow_symlinks=False)
        _assert_same_manifest(root, CANONICAL_ROOT, canonical)
        if (root / MIRROR_ROOT).exists():
            os.replace(root / MIRROR_ROOT, rollback)
        os.replace(stage, root / MIRROR_ROOT)
        installed = True
        _verify(root, canonical)
        _assert_same_manifest(root, CANONICAL_ROOT, canonical)
    except BaseException:
        if installed:
            _rollback(root / MIRROR_ROOT, rollback, had_mirror, stage_root)
        raise
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root)

    return {
        "executor": EXECUTOR_ID,
        "status": "repaired",
        "plannedPaths": list(changed),
        "repairedPaths": list(changed),
        "verified": {"recursiveParity": True, "syncCheck": True},
    }


def _validate_executor(executor: RepairExecutorPolicy) -> None:
    if (
        executor.id != EXECUTOR_ID
        or executor.debt_kind != "bundled_schema_mirror_drift"
        or executor.canonical_path != "registry/schema/**"
        or executor.writable_path != "src/gaia_cli/data/registry/schema/**"
        or SYNC_CHECK_COMMAND not in executor.allowed_commands
        or GIT_STATUS_COMMAND not in executor.allowed_commands
    ):
        raise RepairBlocked("bundled schema repair policy does not match its fixed authority envelope")


def _manifest(root: Path, relative_root: Path, *, required: bool, json_only: bool) -> TreeManifest:
    directory = root / relative_root
    _ensure_plain_ancestors(root, relative_root.parent)
    try:
        mode = directory.lstat().st_mode
    except FileNotFoundError:
        if required:
            raise RepairBlocked(f"canonical schema root is missing: {relative_root}")
        return TreeManifest(root=relative_root, files={})
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise RepairBlocked(f"schema root must be a real directory, not a symlink: {relative_root}")

    files: dict[str, TreeFile] = {}
    for current, directories, names in os.walk(directory, followlinks=False):
        current_path = Path(current)
        for name in sorted(directories):
            path = current_path / name
            child_mode = path.lstat().st_mode
            if stat.S_ISLNK(child_mode) or not stat.S_ISDIR(child_mode):
                raise RepairBlocked(f"schema tree has non-directory or symlink path: {path.relative_to(root)}")
        for name in sorted(names):
            path = current_path / name
            mode = path.lstat().st_mode
            relative = path.relative_to(directory).as_posix()
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise RepairBlocked(f"schema tree has non-regular or symlink file: {relative_root / relative}")
            if json_only and not relative.endswith(".json"):
                raise RepairBlocked(f"canonical schema input is not JSON: {relative_root / relative}")
            raw = path.read_bytes()
            if json_only:
                try:
                    json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise RepairBlocked(
                        f"canonical schema input is invalid JSON: {relative_root / relative}: {exc}"
                    ) from exc
            after = path.lstat()
            stat_key = (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)
            if not stat.S_ISREG(after.st_mode) or after.st_size != len(raw):
                raise RepairBlocked(f"schema input changed while reading: {relative_root / relative}")
            files[relative] = TreeFile(
                relative=relative,
                digest=hashlib.sha256(raw).hexdigest(),
                stat_key=stat_key,
            )
    return TreeManifest(root=relative_root, files=files)


def _ensure_plain_ancestors(root: Path, relative: Path) -> None:
    candidate = root
    for part in relative.parts:
        candidate /= part
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise RepairBlocked(f"schema path may not traverse symlink: {candidate.relative_to(root)}")
        if not stat.S_ISDIR(mode):
            raise RepairBlocked(f"schema path ancestor is not a directory: {candidate.relative_to(root)}")


def _assert_clean_target(root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", str(MIRROR_ROOT)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 128 and "not a git repository" in result.stderr.lower():
        return
    if result.returncode:
        raise RepairBlocked(f"cannot establish bundled schema target cleanliness: {result.stderr.strip()}")
    if result.stdout.strip():
        raise RepairBlocked("bundled schema target has user edits; refusing overwrite")


def _copy_manifest(canonical_root: Path, manifest: TreeManifest, stage: Path) -> None:
    stage.mkdir()
    for relative in manifest.paths:
        source = canonical_root / relative
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)


def _assert_same_manifest(root: Path, relative_root: Path, expected: TreeManifest) -> None:
    current = _manifest(root, relative_root, required=True, json_only=True)
    if current.files != expected.files:
        raise RepairBlocked("canonical schema inputs changed during repair; rolling back")


def _verify(root: Path, canonical: TreeManifest) -> None:
    _assert_same_manifest(root, CANONICAL_ROOT, canonical)
    mirror = _manifest(root, MIRROR_ROOT, required=True, json_only=False)
    if set(canonical.files) != set(mirror.files):
        raise RepairError("recursive bundled schema parity failed: path sets differ")
    mismatches = [
        path
        for path in canonical.paths
        if canonical.files[path].digest != mirror.files[path].digest
    ]
    if mismatches:
        raise RepairError("recursive bundled schema parity failed: " + ", ".join(mismatches))
    result = subprocess.run(
        [sys.executable, "scripts/sync_bundled_schemas.py", "--check"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RepairError("bundled schema sync validation failed: " + result.stderr.strip())


def _rollback(mirror: Path, rollback: Path, had_mirror: bool, stage_root: Path) -> None:
    displaced = stage_root / "failed-schema"
    if mirror.exists():
        os.replace(mirror, displaced)
    if had_mirror and rollback.exists():
        os.replace(rollback, mirror)
