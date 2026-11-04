#!/usr/bin/env python3
"""Read-only freshness guard for the #2283 evidence matrix, never a secret allowlist.

Changed bytes require human re-review. This tool does not resolve debt, alter
Steward authority, or exempt anything from SecretScanSensor or scrub().
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

REPOROOT = Path(__file__).resolve().parents[1]
MATRIX = Path("docs/agents/security/2283-dispositions.json")


def checkDispositions(root: Path, document: dict) -> list[str]:
    """Check exact reviewed file bytes and canonical/mirror grouping, no writes."""
    problems = []
    rows = document.get("rows", [])
    if len(rows) != 39 or len({row.get("debtId") for row in rows}) != 39:
        problems.append("expected 39 unique credential finding ID strings")
    counts = {group: sum(row.get("group") == group for row in rows) for group in ("D1", "D2", "D3")}
    if counts != {"D1": 16, "D2": 14, "D3": 9}:
        problems.append("D1/D2/D3 row counts differ")
    for row in rows:
        identifier = row.get("debtId", "")
        if not identifier.startswith("debt:credential_leak:"):
            problems.append("unexpected debt kind")
        for key in ("sourcePath", "canonicalSource"):
            rel = Path(row[key])
            if rel.is_absolute() or ".." in rel.parts or str(rel) == ".":
                problems.append(f"unsafe {key}")
                continue
            full = root / rel
            if any((root / Path(*rel.parts[:index])).is_symlink() for index in range(1, len(rel.parts) + 1)):
                problems.append(f"symlinked {key}: {rel}")
                continue
            try:
                digest = hashlib.sha256(full.read_bytes()).hexdigest()
            except OSError:
                problems.append(f"unreadable {key}: {rel}")
                continue
            if digest != row["reviewedSourceSha256"]:
                problems.append(f"changed {key}: {rel}; classification requires re-review")
        findings = row.get("findings", [])
        if not findings or any(
            not re.fullmatch(r"[0-9a-f]{12}", finding.get("fingerprint", ""))
            or not isinstance(finding.get("line"), int)
            or finding["line"] < 1
            or finding.get("status") not in ("harmless", "fixture", "exposure", "unknown")
            or not finding.get("reason")
            for finding in findings
        ):
            problems.append(f"invalid finding evidence: {identifier}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOROOT)
    args = parser.parse_args()
    try:
        document = json.loads((args.root / MATRIX).read_text(encoding="utf-8"))
        problems = checkDispositions(args.root, document)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print("security disposition matrix is unreadable or malformed")
        return 1
    if problems:
        print("\n".join(problems))
        return 1
    print("39 matrix rows pass count, shape and reviewed-source-byte checks; identity and scanner authority are not authenticated here")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
