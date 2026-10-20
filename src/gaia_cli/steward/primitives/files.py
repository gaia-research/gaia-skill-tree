"""Bounded, Git-backed file inventory and reading for Steward sensors."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

_TIMEOUT_SECONDS = 30
_MAX_INVENTORY_BYTES = 8 * 1024 * 1024
_DEFAULT_MAX_FILES = 5000
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024

# Findings attached to one observation are capped so a receipt stays readable.
# The cap limits what is *shown*, never what is *counted*: findingCount is
# always the full number, and a capped list says so.
FINDING_CAP = 20


class SensorUnavailable(RuntimeError):
    """A required input could not be observed completely; coverage is unknown."""


class SensorNotEvaluated(RuntimeError):
    """An optional external input was not supplied; the sensor observed nothing."""


def _git(root: Path, arguments: Sequence[str], *, max_bytes: int) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SensorUnavailable(f"git inventory command failed: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr[:1024].decode("utf-8", errors="replace").strip()
        raise SensorUnavailable(
            f"git inventory command exited {result.returncode}: {detail or 'no diagnostic'}"
        )
    if len(result.stdout) > max_bytes:
        raise SensorUnavailable("git inventory output exceeded the bounded size limit")
    return result.stdout


def git_root(repo_root: Path) -> Path:
    """Return ``repo_root`` resolved, proving it is the root of a Git worktree."""

    try:
        root = repo_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SensorUnavailable(f"repository root is unavailable: {exc}") from exc
    reported = _git(root, ["rev-parse", "--show-toplevel"], max_bytes=4096)
    try:
        top = Path(reported.decode("utf-8", errors="strict").strip()).resolve(strict=True)
    except (OSError, RuntimeError, UnicodeDecodeError) as exc:
        raise SensorUnavailable(f"git returned an unreadable repository root: {exc}") from exc
    if top != root:
        raise SensorUnavailable(f"expected the Git worktree root {top}, received {root}")
    return root


def tracked_files(
    repo_root: Path,
    prefixes: Iterable[str],
    *,
    suffixes: Iterable[str] = (),
    exclude: Iterable[str] = (),
    max_files: int = _DEFAULT_MAX_FILES,
    require_any: bool = True,
) -> list[str]:
    """Return sorted tracked POSIX paths under ``prefixes`` that exist on disk.

    The inventory is Git's, not the filesystem's: untracked scratch output and
    ignored Class P files never become findings. Exceeding ``max_files`` is a
    truncated observation and raises ``SensorUnavailable`` rather than silently
    scanning a prefix of the tree. ``require_any`` makes an empty inventory an
    unavailable input — a sensor whose whole domain vanished is blind, not clean.
    """

    root = git_root(repo_root)
    prefix_list = [str(item) for item in prefixes]
    if not prefix_list:
        raise ValueError("tracked_files requires at least one prefix")
    output = _git(root, ["ls-files", "-z", "--", *prefix_list], max_bytes=_MAX_INVENTORY_BYTES)
    try:
        paths = output.decode("utf-8", errors="strict").split("\0")
    except UnicodeDecodeError as exc:
        raise SensorUnavailable(f"git returned an unreadable inventory: {exc}") from exc
    if paths[-1] != "":
        raise SensorUnavailable("git returned a truncated inventory")
    suffix_tuple = tuple(suffixes)
    exclude_tuple = tuple(exclude)
    selected = sorted(
        path
        for path in paths[:-1]
        if path
        and (not suffix_tuple or path.endswith(suffix_tuple))
        and not any(path == item or path.startswith(item.rstrip("/") + "/") for item in exclude_tuple)
        and (root / path).is_file()
    )
    if len(selected) > max_files:
        raise SensorUnavailable(
            f"inventory of {len(selected)} files exceeds the bounded limit of {max_files}"
        )
    if require_any and not selected:
        raise SensorUnavailable(
            "required inventory is empty: " + ", ".join(prefix_list)
        )
    return selected


def read_text_bounded(path: Path, *, limit: int = _DEFAULT_MAX_BYTES) -> str:
    """Read UTF-8 text, refusing oversized or undecodable input."""

    try:
        size = path.stat().st_size
        if size > limit:
            raise SensorUnavailable(f"{path.name} exceeds the {limit}-byte read limit")
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SensorUnavailable(f"{path.name} is not UTF-8: {exc}") from exc
    except OSError as exc:
        raise SensorUnavailable(f"cannot read {path.name}: {exc}") from exc


def parse_python(path: Path) -> tuple[ast.Module | None, str | None]:
    """Parse a Python file. A syntax error is a finding, not an unavailable input."""

    text = read_text_bounded(path)
    try:
        return ast.parse(text, filename=str(path)), None
    except SyntaxError as exc:
        return None, f"SyntaxError: {exc.msg} (line {exc.lineno})"


def finding_payload(findings: Sequence[Any], *, cap: int = FINDING_CAP) -> dict[str, Any]:
    """Return the canonical capped-findings block for an observation's state."""

    ordered = list(findings)
    return {
        "findingCount": len(ordered),
        "findings": ordered[:cap],
        "findingsCapped": len(ordered) > cap,
    }
