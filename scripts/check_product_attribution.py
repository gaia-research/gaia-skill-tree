#!/usr/bin/env python3
"""Product-attribution checker — flag named skills that document a specific
third-party tool's own commands/API with no attribution to that tool's actual maker.

Class A detector (read-only, deterministic). Companion to verify_evidence.py /
verify_lockstep.py. Never mutates the registry.

This is not a generic-purpose "did they credit somebody" NLP classifier — that would
be unreliable and noisy. It is a curated lookup: TOOL_MAKER_MAP below names known
third-party tools that Gaia named skills document, and the maker/maintainer name(s)
that must appear somewhere in the skill's body or evidence notes for the skill to be
considered attributed. Extend the map as new instances are found; a skill id not in
the map is never flagged (no false positives from a blind heuristic).

Origin: gaia-research/gaia-skill-tree#1803, following the audit in #1801.

Usage:
    python3 scripts/check_product_attribution.py [--strict] [--output DIR]

Exit codes:
    0 — no unattributed skills found (or --strict not set)
    1 — unattributed skills detected (only with --strict)
"""

import argparse
import glob
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Optional

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMED_DIR = os.path.join(REPO_ROOT, "registry", "named")

# Seed list from #1803's audit. Each entry: skill id -> (tool name, maker/maintainer
# name(s) that count as attribution — any one appearing in body or evidence notes
# satisfies the check). Extend this map as #1801's broader sweep surfaces more
# instances; it is intentionally a curated allowlist, not an inferred one.
TOOL_MAKER_MAP = {
    "gooseworks/notte-browser": {
        "tool": "Notte Browser",
        "makers": ["Nottelabs", "Notte Labs"],
    },
    "google-deepmind/pymol": {
        "tool": "PyMOL",
        "makers": ["Schrödinger", "Schrodinger", "Warren DeLano", "DeLano Scientific"],
    },
    "google-deepmind/uniprot-database": {
        "tool": "UniProt",
        "makers": ["UniProt Consortium", "EBI", "SIB", "PIR"],
    },
    "k-dense-ai/rdkit": {
        "tool": "RDKit",
        "makers": ["Greg Landrum", "RDKit community", "RDKit contributors"],
    },
    "k-dense-ai/deepchem": {
        "tool": "DeepChem",
        "makers": ["DeepChem project", "DeepChem contributors", "DeepChem developers"],
    },
}


@dataclass
class AttributionResult:
    skill_id: str
    tool: str
    expected_makers: list
    attributed: bool
    path: str


def load_named_skills():
    named = {}
    for path in glob.glob(os.path.join(NAMED_DIR, "**", "*.md"), recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        data = yaml.safe_load(parts[1])
        if not isinstance(data, dict) or "id" not in data:
            continue
        body = parts[2].strip()
        named[data["id"]] = {
            "meta": data,
            "body": body,
            "path": os.path.relpath(path, REPO_ROOT),
        }
    return named


def evidence_text(meta: dict) -> str:
    chunks = []
    for ev in meta.get("evidence", []) or []:
        if isinstance(ev, dict):
            chunks.append(str(ev.get("notes", "")))
            chunks.append(str(ev.get("source", "")))
    return "\n".join(chunks)


def is_attributed(searchable_text: str, makers: list) -> bool:
    haystack = searchable_text.lower()
    return any(maker.lower() in haystack for maker in makers)


def run_check():
    named = load_named_skills()
    results = []

    for skill_id, spec in TOOL_MAKER_MAP.items():
        item = named.get(skill_id)
        if item is None:
            # Skill no longer exists (renamed/removed) — nothing to flag.
            continue
        searchable = "\n".join([item["body"], evidence_text(item["meta"])])
        attributed = is_attributed(searchable, spec["makers"])
        results.append(
            AttributionResult(
                skill_id=skill_id,
                tool=spec["tool"],
                expected_makers=spec["makers"],
                attributed=attributed,
                path=item["path"],
            )
        )

    return results


def generate_report(results, output_dir: Optional[str]):
    unattributed = [r for r in results if not r.attributed]
    report = {
        "checked": len(results),
        "unattributedCount": len(unattributed),
        "results": [asdict(r) for r in results],
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "product-attribution.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Wrote report to {os.path.relpath(out_path, REPO_ROOT)}")

    print(f"Checked {report['checked']} known product-documenting skill(s).")
    if unattributed:
        print(f"⚠️  {len(unattributed)} skill(s) document a third-party product with no maker attribution:")
        for r in unattributed:
            print(f"  - {r.skill_id} ({r.tool}) — expected one of {r.expected_makers} in body/evidence — {r.path}")
    else:
        print("✅ All known product-documenting skills credit their tool's maker.")

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any unattributed skill is found")
    parser.add_argument("--output", default=None, help="Directory to write product-attribution.json report")
    args = parser.parse_args()

    results = run_check()
    report = generate_report(results, args.output)

    if args.strict and report["unattributedCount"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
