#!/usr/bin/env python3
"""
buildSkillsIndex.py — generate docs/okf/index.json from existing OKF markdown files.

Reads docs/okf/skills/{basic,extra,ultimate}/*.md and emits docs/okf/index.json
with a machine-readable summary consumed by docs/skills/index.js.

Deterministic: generatedAt is null (avoids timestamp drift on unrelated PRs).

Usage:
    python scripts/buildSkillsIndex.py            # write docs/okf/index.json
    python scripts/buildSkillsIndex.py --check    # exit 1 if stale
    python scripts/buildSkillsIndex.py --out <p>  # custom output path
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OKF_DIR = ROOT / "docs" / "okf"
FAMILIES = ["basic", "extra", "ultimate"]

_RE_FM_TITLE = re.compile(r'^title:\s*"?([^"\n]+)"?', re.MULTILINE)
_RE_FM_DESC = re.compile(r'^description:\s*"?([^"\n]*)"?', re.MULTILINE)


def _parse_skill(md_path: Path) -> dict:
    """Extract id, name, summary from an OKF markdown file."""
    skill_id = md_path.stem  # filename without .md
    text = md_path.read_text(encoding="utf-8")

    # Frontmatter window
    fm_match = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    fm = fm_match.group(1) if fm_match else ""

    title_m = _RE_FM_TITLE.search(fm)
    name = title_m.group(1).strip() if title_m else skill_id.replace("-", " ").title()

    desc_m = _RE_FM_DESC.search(fm)
    summary = desc_m.group(1).strip() if desc_m else ""

    return {"id": skill_id, "name": name, "summary": summary}


def build_index() -> dict:
    """Read OKF markdown files and assemble the index payload."""
    families = []
    for family_id in FAMILIES:
        skill_dir = OKF_DIR / "skills" / family_id
        if not skill_dir.is_dir():
            families.append({"id": family_id, "count": 0, "skills": []})
            continue
        skill_files = sorted(
            [p for p in skill_dir.glob("*.md") if p.name != "index.md"]
        )
        skills = [_parse_skill(p) for p in skill_files]
        families.append({"id": family_id, "count": len(skills), "skills": skills})

    return {
        "schemaVersion": "1.0.0",
        "generatedAt": None,  # frozen null — avoids timestamp drift (CLAUDE.md §Decorative)
        "families": families,
    }


def render(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate docs/okf/index.json")
    parser.add_argument("--check", action="store_true", help="Exit 1 if file is stale")
    parser.add_argument("--out", default=str(OKF_DIR / "index.json"), help="Output path")
    args = parser.parse_args(argv)

    payload = build_index()
    rendered = render(payload)
    out_path = Path(args.out)

    if args.check:
        if not out_path.exists():
            print("docs/okf/index.json missing -- run buildSkillsIndex.py to create it")
            return 1
        existing = out_path.read_text(encoding="utf-8")
        if existing == rendered:
            return 0
        print("docs/okf/index.json is stale -- run buildSkillsIndex.py to regenerate")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    total = sum(f["count"] for f in payload["families"])
    print(f"[OK] docs/okf/index.json written ({total} skills across {len(payload['families'])} families)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
