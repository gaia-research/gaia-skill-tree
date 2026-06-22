"""Cross-platform link creation with Windows-specific fallbacks.

The standard library ``os.symlink`` works reliably on Linux and macOS, but on
Windows it requires either Administrator privileges, Developer Mode, or the
``SeCreateSymbolicLinkPrivilege``. Even with Developer Mode enabled, some
Python builds, CI environments, anti-virus products, and group policies will
still reject the call.

This module provides ``makeLink`` which transparently falls back to mechanisms
that do *not* require elevation on Windows:

* For directories: NTFS junctions (``mklink /J``).
* For files: hardlinks (``os.link``), then a copy via ``shutil.copy2``.

On Linux and macOS the fallback code is unreachable — ``os.symlink`` is the
sole path executed and the function behaves exactly like the stdlib call.

A companion helper ``isLinkOrJunction`` lets tests assert that *some* form of
link was created without caring whether it is a true symlink or an NTFS
junction.

Caveat: ``os.readlink`` does NOT work on NTFS junctions. Callers that need to
read the link target back should use ``os.path.realpath`` (which resolves
junctions transparently) instead.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Union

PathLike = Union[str, "os.PathLike[str]"]


def makeLink(
    src: PathLike,
    dst: PathLike,
    *,
    targetIsDirectory: bool | None = None,
) -> str:
    """Create a link from ``dst`` pointing at ``src``.

    Args:
        src: The existing path to link to.
        dst: The new path to create.
        targetIsDirectory: Whether the target is a directory. Inferred from
            ``src`` via ``os.path.isdir`` when ``None`` (matches the semantics
            of ``os.symlink``'s ``target_is_directory`` argument).

    Returns:
        A string describing the mechanism used: ``"symlink"`` (the default
        path on every platform), ``"junction"`` (Windows directory fallback),
        ``"hardlink"`` (Windows file fallback), or ``"copy"`` (Windows file
        last-resort).

    Raises:
        OSError: When ``os.symlink`` fails on a non-Windows platform, or when
            every Windows fallback also fails.
    """
    srcPath = os.fspath(src)
    dstPath = os.fspath(dst)
    if targetIsDirectory is None:
        targetIsDirectory = os.path.isdir(srcPath)

    # Primary path: real symlink. Works on Linux/macOS unconditionally; works
    # on Windows when symlink creation is permitted for the current user.
    try:
        os.symlink(srcPath, dstPath, target_is_directory=targetIsDirectory)
        return "symlink"
    except OSError as primaryError:
        if sys.platform != "win32":
            raise

    # ---- Windows fallbacks below this point ----

    if targetIsDirectory:
        # NTFS junction: same-volume only, but no elevation required.
        try:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", dstPath, srcPath],
                check=True,
                capture_output=True,
                text=True,
            )
            return "junction"
        except (subprocess.CalledProcessError, FileNotFoundError) as junctionError:
            stderr = getattr(junctionError, "stderr", "") or ""
            raise OSError(
                f"Failed to link {dstPath!r} -> {srcPath!r}: "
                f"symlink denied ({primaryError}) and junction failed "
                f"({stderr.strip() or junctionError})"
            ) from junctionError

    # File fallbacks: try hardlink first (same-volume only, no elevation),
    # then a plain copy.
    try:
        os.link(srcPath, dstPath)
        return "hardlink"
    except OSError:
        shutil.copy2(srcPath, dstPath)
        return "copy"


def isLinkOrJunction(path: PathLike) -> bool:
    """Return True when ``path`` is a symlink or an NTFS junction.

    ``os.path.islink`` returns False for junctions on Windows, so tests that
    only care that *some* form of link exists should use this helper.
    """
    p = os.fspath(path)
    if os.path.islink(p):
        return True
    if sys.platform != "win32":
        return False
    # On Windows, a junction is a reparse point with a directory attribute.
    # The cheapest reliable detection is the FILE_ATTRIBUTE_REPARSE_POINT
    # bit on the lstat result.
    try:
        attrs = os.lstat(p).st_file_attributes  # type: ignore[attr-defined]
    except (OSError, AttributeError):
        return False
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def readLinkTarget(path: PathLike) -> str:
    """Return the resolved absolute path that ``path`` ultimately points to.

    Works for both real symlinks and NTFS junctions. Prefer this over
    ``os.readlink`` in cross-platform code — ``os.readlink`` does not support
    junctions and raises ``OSError`` for them.
    """
    return os.path.realpath(os.fspath(path))
