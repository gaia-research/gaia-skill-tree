#!/usr/bin/env python3
"""Count 6★ Apex skills currently in the registry.

Usage:
  python scripts/countApexSkills.py [--json]

Output (default): a single integer count to stdout.
Output (--json):  {"apexCount": N, "systemWideCap": M, "withinCap": true/false}

Exit code:
  0 — within system-wide cap (or cap check not requested)
  1 — exceeds system-wide cap (only when --check-cap flag is given)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_META_SCHEMA = _REPO_ROOT / "registry" / "schema" / "meta.json"
_NAMED_DIR = _REPO_ROOT / "registry" / "named"
_NODES_DIR = _REPO_ROOT / "registry" / "nodes"


def readSystemWideCap() -> int:
    """Read apexGate.systemWideCap from registry/schema/meta.json."""
    try:
        data = json.loads(_META_SCHEMA.read_text(encoding="utf-8"))
        cap = data.get("apexGate", {}).get("systemWideCap")
        if isinstance(cap, int):
            return cap
    except (json.JSONDecodeError, OSError):
        pass
    # Fallback — should not happen if schema is intact
    return 5


def parseFrontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a Markdown file; return {} on error."""
    try:
        import yaml
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        return yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}


def countApexSkills() -> list[str]:
    """Return list of skill IDs (named or node) currently at level 6★."""
    apexIds: list[str] = []

    # Named skills (markdown frontmatter)
    for mdFile in _NAMED_DIR.rglob("*.md"):
        meta = parseFrontmatter(mdFile)
        level = str(meta.get("level", ""))
        if level.startswith("6"):
            sid = meta.get("id") or f"{mdFile.parent.name}/{mdFile.stem}"
            apexIds.append(sid)

    # Registry nodes (JSON)
    for jsonFile in _NODES_DIR.rglob("*.json"):
        try:
            data = json.loads(jsonFile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        level = str(data.get("level", ""))
        if level.startswith("6"):
            sid = data.get("id") or jsonFile.stem
            apexIds.append(sid)

    return apexIds


def main() -> int:
    parser = argparse.ArgumentParser(description="Count 6★ Apex skills in the registry.")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a plain integer.")
    parser.add_argument("--check-cap", action="store_true",
                        help="Exit 1 if count exceeds apexGate.systemWideCap.")
    args = parser.parse_args()

    apexIds = countApexSkills()
    count = len(apexIds)
    cap = readSystemWideCap()
    withinCap = count <= cap

    if args.json:
        print(json.dumps({"apexCount": count, "systemWideCap": cap, "withinCap": withinCap,
                          "skills": sorted(apexIds)}, indent=2))
    else:
        print(count)

    if args.check_cap and not withinCap:
        print(
            f"ERROR: {count} apex skill(s) found — exceeds systemWideCap of {cap}.",
            file=sys.stderr,
        )
        print("Skills at 6★:", file=sys.stderr)
        for sid in sorted(apexIds):
            print(f"  - {sid}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
