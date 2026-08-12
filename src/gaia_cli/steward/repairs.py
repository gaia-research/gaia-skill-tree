"""The deliberately narrow, zero-LLM Steward Class A mirror repairs.

This module is intentionally not a generic file synchronizer.  It owns exactly
the mirror surfaces declared in ``gaia_cli.steward.mirrors``, where the
canonical tree is read-only and the mirror is the only writable project
surface.  Every mirror repair follows one path: stage canonical bytes, prove the
canonical inputs did not move, displace the previous mirror into retained
recovery, atomically install, then prove parity twice — once structurally and
once through an independent check command.

Locally owned paths (a spec's ``ignore`` set) are neither compared nor
overwritten.  Because installation replaces the whole mirror directory, those
paths are copied forward from the displaced recovery before the swap, so an
atomic install never silently deletes a file the mirror owns.
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

from gaia_cli.steward.mirrors import MirrorSpec, spec_by_id
from gaia_cli.steward.policy import RepairExecutorPolicy
from gaia_cli.steward.receipts import StateError, ensure_local_state_path


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
    # Locally owned paths matched by the spec ignore set. They are recorded so
    # a repair can prove it carried them forward byte-for-byte, but they never
    # participate in canonical parity.
    preserved: Mapping[str, TreeFile]
    # Directories holding no compared file anywhere beneath them. They carry no
    # parity meaning, so installing over them would be an unrequested deletion
    # of something a human made — including a deliberately empty directory,
    # which no file manifest can represent.
    preserved_directories: tuple[str, ...] = ()

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(self.files))

    @property
    def preserved_paths(self) -> tuple[str, ...]:
        return tuple(sorted(self.preserved))


@dataclass
class MirrorTransaction:
    root: Path
    state_root: Path
    spec: MirrorSpec
    canonical: TreeManifest
    captured_mirror: TreeManifest
    stage_root: Path
    rollback_path: Path
    had_mirror: bool
    changed: tuple[str, ...]
    installed: bool = False
    displaced: bool = False

    def receipt(self) -> dict[str, object]:
        recovery_path = self._validate_recovery()
        return {
            "executor": self.spec.id,
            "status": "repaired",
            "canonicalPath": self.spec.canonical_root,
            "writablePath": self.spec.mirror_root,
            "plannedPaths": list(self.changed),
            "repairedPaths": list(self.changed),
            "preservedPaths": list(self.captured_mirror.preserved_paths),
            "preservedDirectories": list(self.captured_mirror.preserved_directories),
            "verified": {"recursiveParity": True, "syncCheck": True},
            "recovery": {
                "path": recovery_path,
                "preRepairManifest": {
                    path: item.digest
                    for path, item in sorted(self.captured_mirror.files.items())
                },
                "originalTargetPresent": self.had_mirror,
                "retained": True,
            },
        }

    def commit(self) -> None:
        """Retain V1 recovery bytes under local Steward state for manual audit."""
        self._validate_recovery()

    def _validate_recovery(self) -> str:
        try:
            ensure_local_state_path(self.root, self.state_root, self.rollback_path)
            mode = self.rollback_path.lstat().st_mode
        except (OSError, StateError) as exc:
            raise RepairError(f"cannot validate retained repair recovery: {exc}") from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise RepairError("retained repair recovery must be a real directory")
        return self.rollback_path.relative_to(self.root).as_posix()

    def rollback(self) -> None:
        try:
            _rollback(
                self.root / self.spec.mirror_root,
                self.rollback_path,
                self.had_mirror,
                self.stage_root,
            )
        except OSError as exc:
            raise RepairError(
                f"rollback failed; original mirror recovery is preserved at {self.rollback_path}: {exc}"
            ) from exc
        try:
            shutil.rmtree(self.stage_root)
        except OSError as exc:
            raise RepairError(f"rollback completed; recovery cleanup remains at {self.stage_root}: {exc}") from exc


def repair_mirror(
    repo_root: Path,
    executor: RepairExecutorPolicy,
    *,
    state_root: Path,
) -> dict[str, object]:
    """Stage, prove, and atomically install one exact canonical mirror.

    The caller must hold Steward's transaction lock.  On every failed proof or
    interruption this function restores the previous mirror bytes before
    returning or raising.
    """

    transaction = prepare_mirror_repair(repo_root, executor, state_root=state_root)
    if transaction is None:
        spec = _spec_for(executor)
        return {
            "executor": spec.id,
            "status": "no_change",
            "canonicalPath": spec.canonical_root,
            "writablePath": spec.mirror_root,
            "plannedPaths": [],
            "repairedPaths": [],
            "preservedPaths": [],
            "preservedDirectories": [],
            "verified": {"recursiveParity": True, "syncCheck": True},
        }
    try:
        result = transaction.receipt()
        transaction.commit()
        return result
    except BaseException:
        transaction.rollback()
        raise


def prepare_mirror_repair(
    repo_root: Path, executor: RepairExecutorPolicy, *, state_root: Path,
) -> MirrorTransaction | None:
    """Install a verified mirror but retain exact rollback bytes for the controller."""

    spec = _spec_for(executor)
    root = repo_root.resolve()
    local_state = state_root if state_root.is_absolute() else root / state_root
    try:
        ensure_local_state_path(root, local_state, local_state)
    except StateError as exc:
        raise RepairBlocked(f"repair recovery must remain under repository-local state: {exc}") from exc
    _validate_executor(spec, executor)
    canonical = _manifest(root, Path(spec.canonical_root), spec, required=True, canonical=True)
    mirror = _manifest(root, Path(spec.mirror_root), spec, required=False, canonical=False)

    extras = sorted(set(mirror.files) - set(canonical.files))
    if extras:
        raise RepairBlocked(
            f"{spec.id} has mirror-only paths; refusing deletion: " + ", ".join(extras)
        )

    changed = tuple(
        path
        for path in canonical.paths
        if path not in mirror.files or canonical.files[path].digest != mirror.files[path].digest
    )
    if not changed:
        _verify(root, spec, canonical, mirror)
        return None

    _assert_clean_target(root, spec)
    _ensure_plain_ancestors(root, Path(spec.mirror_root).parent)
    local_state.mkdir(parents=True, exist_ok=True)
    try:
        ensure_local_state_path(root, local_state, local_state)
    except StateError as exc:
        raise RepairBlocked(f"repair recovery state is unsafe: {exc}") from exc
    stage_root = Path(tempfile.mkdtemp(prefix=spec.stage_prefix, dir=local_state))
    stage = stage_root / "mirror"
    rollback = stage_root / "rollback-mirror"
    try:
        ensure_local_state_path(root, local_state, stage_root)
        ensure_local_state_path(root, local_state, stage)
        ensure_local_state_path(root, local_state, rollback)
    except StateError as exc:
        shutil.rmtree(stage_root)
        raise RepairBlocked(f"repair recovery path is unsafe: {exc}") from exc
    had_mirror = (root / spec.mirror_root).exists()
    transaction = MirrorTransaction(
        root,
        local_state,
        spec,
        canonical,
        mirror,
        stage_root,
        rollback,
        had_mirror,
        changed,
    )
    try:
        _copy_manifest(root / spec.canonical_root, canonical, stage)
        if had_mirror:
            shutil.copystat(root / spec.mirror_root, stage, follow_symlinks=False)
        _assert_same_manifest(root, spec, canonical)
        if (root / spec.mirror_root).exists():
            os.replace(root / spec.mirror_root, rollback)
            transaction.displaced = True
            observed_rollback = _manifest(
                root, rollback.relative_to(root), spec, required=True, canonical=False
            )
            if (
                observed_rollback.files != mirror.files
                or observed_rollback.preserved != mirror.preserved
            ):
                raise RepairBlocked(
                    f"{spec.id} changed during handoff; restoring edited target"
                )
            # Locally owned paths belong to the mirror, not to canon. Carry them
            # across the atomic swap so installation never deletes them.
            _copy_preserved(rollback, mirror, stage)
        else:
            rollback.mkdir()
        os.replace(stage, root / spec.mirror_root)
        transaction.installed = True
        _verify(root, spec, canonical, mirror)
        _assert_same_manifest(root, spec, canonical)
    except BaseException:
        if transaction.installed or transaction.displaced:
            transaction.rollback()
        elif stage_root.exists():
            shutil.rmtree(stage_root)
        raise
    return transaction


def _spec_for(executor: RepairExecutorPolicy) -> MirrorSpec:
    spec = spec_by_id(executor.id)
    if spec is None:
        raise RepairBlocked(f"no registered Class A repair implements executor {executor.id}")
    return spec


def _validate_executor(spec: MirrorSpec, executor: RepairExecutorPolicy) -> None:
    if (
        executor.debt_kind != spec.debt_kind
        or executor.canonical_path != spec.canonical_glob
        or executor.writable_path != spec.writable_glob
        or spec.check_command not in executor.allowed_commands
        or spec.git_status_command not in executor.allowed_commands
    ):
        raise RepairBlocked(
            f"{spec.id} repair policy does not match its fixed authority envelope"
        )


def _manifest(
    root: Path,
    relative_root: Path,
    spec: MirrorSpec,
    *,
    required: bool,
    canonical: bool,
) -> TreeManifest:
    directory = root / relative_root
    _ensure_plain_ancestors(root, relative_root.parent)
    try:
        mode = directory.lstat().st_mode
    except FileNotFoundError:
        if required:
            raise RepairBlocked(f"canonical mirror root is missing: {relative_root}")
        return TreeManifest(root=relative_root, files={}, preserved={})
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise RepairBlocked(f"mirror root must be a real directory, not a symlink: {relative_root}")

    files: dict[str, TreeFile] = {}
    preserved: dict[str, TreeFile] = {}
    seen_directories: list[str] = []
    json_only = canonical and spec.json_only
    for current, directories, names in os.walk(directory, followlinks=False):
        current_path = Path(current)
        for name in sorted(directories):
            path = current_path / name
            child_mode = path.lstat().st_mode
            if stat.S_ISLNK(child_mode) or not stat.S_ISDIR(child_mode):
                raise RepairBlocked(f"mirror tree has non-directory or symlink path: {path.relative_to(root)}")
            seen_directories.append(path.relative_to(directory).as_posix())
        for name in sorted(names):
            path = current_path / name
            mode = path.lstat().st_mode
            relative = path.relative_to(directory).as_posix()
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise RepairBlocked(f"mirror tree has non-regular or symlink file: {relative_root / relative}")
            ignored = spec.is_ignored(relative)
            raw = path.read_bytes()
            if json_only and not ignored:
                if not relative.endswith(".json"):
                    raise RepairBlocked(f"canonical input is not JSON: {relative_root / relative}")
                try:
                    json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise RepairBlocked(
                        f"canonical input is invalid JSON: {relative_root / relative}: {exc}"
                    ) from exc
            after = path.lstat()
            stat_key = (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)
            if not stat.S_ISREG(after.st_mode) or after.st_size != len(raw):
                raise RepairBlocked(f"mirror input changed while reading: {relative_root / relative}")
            entry = TreeFile(
                relative=relative,
                digest=hashlib.sha256(raw).hexdigest(),
                stat_key=stat_key,
            )
            if ignored:
                preserved[relative] = entry
            else:
                files[relative] = entry
    preserved_directories = tuple(
        sorted(
            candidate
            for candidate in seen_directories
            if not any(path.startswith(candidate + "/") for path in files)
        )
    )
    return TreeManifest(
        root=relative_root,
        files=files,
        preserved=preserved,
        preserved_directories=preserved_directories,
    )


def _ensure_plain_ancestors(root: Path, relative: Path) -> None:
    candidate = root
    for part in relative.parts:
        candidate /= part
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise RepairBlocked(f"mirror path may not traverse symlink: {candidate.relative_to(root)}")
        if not stat.S_ISDIR(mode):
            raise RepairBlocked(f"mirror path ancestor is not a directory: {candidate.relative_to(root)}")


def _assert_clean_target(root: Path, spec: MirrorSpec) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", spec.mirror_root],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RepairBlocked(f"cannot establish {spec.id} target cleanliness: {result.stderr.strip()}")
    if result.stdout.strip():
        raise RepairBlocked(f"{spec.id} target has user edits; refusing overwrite")


def _copy_manifest(canonical_root: Path, manifest: TreeManifest, stage: Path) -> None:
    stage.mkdir()
    for relative in manifest.paths:
        source = canonical_root / relative
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)


def _copy_preserved(displaced_mirror: Path, manifest: TreeManifest, stage: Path) -> None:
    """Carry locally owned mirror paths into the staged replacement unchanged."""

    # Directories first: an empty one has no file to imply it back into being.
    for relative in manifest.preserved_directories:
        destination = stage / relative
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copystat(displaced_mirror / relative, destination, follow_symlinks=False)
    for relative in manifest.preserved_paths:
        source = displaced_mirror / relative
        destination = stage / relative
        if destination.exists():
            raise RepairBlocked(
                f"locally owned mirror path collides with canonical content: {relative}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != manifest.preserved[relative].digest:
            raise RepairBlocked(f"locally owned mirror path changed during repair: {relative}")


def _assert_same_manifest(root: Path, spec: MirrorSpec, expected: TreeManifest) -> None:
    current = _manifest(root, Path(spec.canonical_root), spec, required=True, canonical=True)
    if current.files != expected.files:
        raise RepairBlocked(f"{spec.id} canonical inputs changed during repair; rolling back")


def _verify(
    root: Path, spec: MirrorSpec, canonical: TreeManifest, captured_mirror: TreeManifest
) -> None:
    _assert_same_manifest(root, spec, canonical)
    mirror = _manifest(root, Path(spec.mirror_root), spec, required=True, canonical=False)
    if set(canonical.files) != set(mirror.files):
        raise RepairError(f"recursive {spec.id} parity failed: path sets differ")
    mismatches = [
        path
        for path in canonical.paths
        if canonical.files[path].digest != mirror.files[path].digest
    ]
    if mismatches:
        raise RepairError(f"recursive {spec.id} parity failed: " + ", ".join(mismatches))
    lost = sorted(
        path
        for path, item in captured_mirror.preserved.items()
        if path not in mirror.preserved or mirror.preserved[path].digest != item.digest
    )
    lost += sorted(
        f"{path}/"
        for path in captured_mirror.preserved_directories
        if not (root / spec.mirror_root / path).is_dir()
    )
    if lost:
        raise RepairError(
            f"{spec.id} lost locally owned mirror paths: " + ", ".join(lost)
        )
    result = subprocess.run(
        [sys.executable, spec.check_script, "--check"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RepairError(f"{spec.id} sync validation failed: " + result.stderr.strip())


def _rollback(mirror: Path, rollback: Path, had_mirror: bool, stage_root: Path) -> None:
    displaced = stage_root / "failed-mirror"
    if mirror.exists():
        os.replace(mirror, displaced)
    if had_mirror and rollback.exists():
        os.replace(rollback, mirror)
