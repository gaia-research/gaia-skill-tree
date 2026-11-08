"""Reusable failure fixtures for loader-swap proofs (#2283).

A verifier proving a swallowed-exception repair that swaps in
``gaia_cli.structuredRead`` runs the enclosing function against each fixture
at the base and at the candidate commit and compares the results (see
``loader-route-notes.md``, repair shape LS-1). ``F3`` is ``None`` where a
permission error cannot be produced (running as root, or on Windows).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Expected ReadDiagnostic / InputReadError ``kind`` for each failure fixture.
EXPECTED_KIND = {
    "F1-missing": "missing",
    "F2-malformed": "malformed",
    "F3-permission": "unreadable",
    "F4-encoding": "encoding",
    "F5-shape": "shape",
}


def permissionErrorsPossible() -> bool:
    if sys.platform.startswith("win"):
        return False
    return not (hasattr(os, "geteuid") and os.geteuid() == 0)


def jsonFixtures(directory: Path, *, good: str = '{"a": 1}', incomplete: str = '{"items": [{}]}') -> dict[str, Path | None]:
    """Write the F0-F6 JSON fixtures under ``directory``; return name -> path.

    F6 (an object whose nested entry lacks a key) is not a read failure; it
    checks that post-read logic behaves the same before and after a swap.
    Call :func:`restorePermissions` when done.
    """

    directory.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path | None] = {}

    def put(name: str, data: bytes) -> Path:
        path = directory / f"{name}.json"
        path.write_bytes(data)
        return path

    paths["F0-good"] = put("F0-good", good.encode("utf-8"))
    paths["F1-missing"] = directory / "F1-missing.json"
    paths["F2-malformed"] = put("F2-malformed", b'{"a": 1,')
    if permissionErrorsPossible():
        denied = put("F3-permission", good.encode("utf-8"))
        denied.chmod(0)
        paths["F3-permission"] = denied
    else:
        paths["F3-permission"] = None
    paths["F4-encoding"] = put("F4-encoding", b'{"a": "caf\xe9"}')
    paths["F5-shape"] = put("F5-shape", b"[1, 2]")
    paths["F6-incomplete"] = put("F6-incomplete", incomplete.encode("utf-8"))
    return paths


def restorePermissions(paths: dict[str, Path | None]) -> None:
    denied = paths.get("F3-permission")
    if denied is not None and denied.exists():
        denied.chmod(0o600)
