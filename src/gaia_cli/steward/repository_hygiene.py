"""Read-only detection of explicitly enumerated tracked Class P leaks."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from gaia_cli.steward.models import Observation, Subject, stable_json


class RepositoryInventoryError(RuntimeError):
    """Raised when the tracked-file inventory cannot be trusted."""


# This is intentionally an allowlist, not a scan of generated-data directories.
# Class P files are normally gitignored; tracking one is the only condition
# this sensor reports. Class S under docs/graph is served content and excluded.
_TRACKED_CLASS_P_PATHS = (
    "registry/gaia.json",
    "registry/gaia.gexf",
    "registry/gaia.svg",
    "registry/named-skills.json",
    "registry/layouts_3d.json",
    "base_gaia.json",
    "src/gaia_cli/data/registry/gaia.json",
    "src/gaia_cli/data/registry/named-skills.json",
)
_MAX_INVENTORY_BYTES = 16 * 1024
_TIMEOUT_SECONDS = 5


class RepositoryHygieneSensor:
    """Report enumerated Class P paths present in Git's tracked index."""

    id = "repository-hygiene"
    debt_kind = "repository_hygiene"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = self._checked_root(repo_root)
        tracked = self._tracked_paths(root)
        leaks = sorted(tracked)
        inventory_digest = hashlib.sha256(stable_json(sorted(tracked)).encode("utf-8")).hexdigest()
        drift = bool(leaks)

        return [
            Observation(
                kind=self.debt_kind,
                subject=Subject(type="repository-surface", id="tracked-class-p-artifacts"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if drift else "healthy",
                current_state={"trackedLeakPaths": []},
                observed_state={
                    "trackedLeakPaths": leaks,
                    "inventoryDigest": inventory_digest,
                    "consistent": not drift,
                },
                confidence=1.0,
                provenance={
                    "command": "git ls-files -z -- <explicit Class P paths>",
                    "trackedPathAllowlist": list(_TRACKED_CLASS_P_PATHS),
                    "excludedTrackedCatalogs": [
                        "registry/real-skills.json",
                        "registry/real-skills.md",
                        "src/gaia_cli/data/registry/benchmark-sources.json",
                    ],
                    "excludedClassSDirectory": "docs/graph/**",
                    "inventoryDigest": inventory_digest,
                },
            )
        ]

    @staticmethod
    def _checked_root(repo_root: Path) -> Path:
        try:
            root = repo_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise RepositoryInventoryError(f"repository root is unavailable: {exc}") from exc
        if not root.is_dir():
            raise RepositoryInventoryError("repository root is not a directory")

        top_level = RepositoryHygieneSensor._git(
            root, ["rev-parse", "--show-toplevel"], max_bytes=4096
        )
        try:
            reported_root = Path(top_level.decode("utf-8", errors="strict").strip()).resolve(strict=True)
        except (OSError, RuntimeError, UnicodeDecodeError) as exc:
            raise RepositoryInventoryError(f"Git returned an unreadable repository root: {exc}") from exc
        if reported_root != root:
            raise RepositoryInventoryError(
                f"expected the Git worktree root {reported_root}, received {root}"
            )

        inside_worktree = RepositoryHygieneSensor._git(
            root, ["rev-parse", "--is-inside-work-tree"], max_bytes=64
        )
        if inside_worktree.strip() != b"true":
            raise RepositoryInventoryError("path is not inside a Git worktree")
        return root

    @staticmethod
    def _tracked_paths(root: Path) -> list[str]:
        output = RepositoryHygieneSensor._git(
            root,
            ["ls-files", "-z", "--", *_TRACKED_CLASS_P_PATHS],
            max_bytes=_MAX_INVENTORY_BYTES,
        )
        try:
            paths = output.decode("utf-8", errors="strict").split("\0")
        except UnicodeDecodeError as exc:
            raise RepositoryInventoryError(f"Git returned an unreadable tracked-path inventory: {exc}") from exc
        if paths[-1] != "":
            raise RepositoryInventoryError("Git returned a truncated tracked-path inventory")
        tracked = paths[:-1]
        if any(not path for path in tracked) or len(tracked) != len(set(tracked)):
            raise RepositoryInventoryError("Git returned a malformed tracked-path inventory")
        unexpected = sorted(set(tracked) - set(_TRACKED_CLASS_P_PATHS))
        if unexpected:
            raise RepositoryInventoryError(f"Git returned paths outside the inventory allowlist: {unexpected}")
        return tracked

    @staticmethod
    def _git(root: Path, arguments: list[str], *, max_bytes: int) -> bytes:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *arguments],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RepositoryInventoryError(f"Git inventory command failed: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr[:1024].decode("utf-8", errors="replace").strip()
            raise RepositoryInventoryError(
                f"Git inventory command exited {result.returncode}: {detail or 'no diagnostic'}"
            )
        if len(result.stdout) > max_bytes:
            raise RepositoryInventoryError("Git inventory output exceeded the bounded size limit")
        return result.stdout
