#!/usr/bin/env python3
"""Copy generated graph artifacts into docs/ for GitHub Pages.

GitHub Pages commonly serves the docs/ directory as the site root. Keep the
canonical graph files in registry/, then mirror only the public artifacts that the
static page needs to fetch or download.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Stage 1 — keep CSS tokens regenerated alongside the graph artifacts.
# generateCssTokens reads registry/gaia.json.meta and writes docs/css/tokens.css.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generateCssTokens import build_tokens_css, load_gaia  # noqa: E402


def _regenerate_css_tokens(root: Path) -> None:
    gaia_path = root / "registry" / "gaia.json"
    out_path = root / "docs" / "css" / "tokens.css"
    gaia = load_gaia(gaia_path)
    rendered = build_tokens_css(gaia)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"Regenerated {out_path.relative_to(root)}")


def _named_max_levels(root: Path) -> dict:
    """Map generic skill id -> highest named-variant star across its bucket."""
    order = ["2★", "3★", "4★", "5★", "6★"]
    src = root / "registry" / "named-skills.json"
    if not src.exists():
        return {}
    buckets = json.loads(src.read_text(encoding="utf-8")).get("buckets", {})
    out = {}
    for ref, entries in buckets.items():
        levels = [e.get("level") for e in entries if e.get("level") in order]
        if levels:
            out[ref] = max(levels, key=order.index)
    return out


def sync_docs_graph_assets(root: Path = ROOT) -> None:
    docs_graph = root / "docs" / "graph"
    docs_graph.mkdir(parents=True, exist_ok=True)

    # Stage 1 — CSS tokens are derived from registry/gaia.json.meta and must
    # never drift behind a registry update. Run this BEFORE the artifact
    # copy so a missing tree.md or gaia.svg doesn't block the token refresh.
    _regenerate_css_tokens(root)

    required = ("registry/gaia.json", "registry/gaia.gexf", "registry/gaia.svg")
    missing = [rel for rel in required if not (root / rel).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing generated graph artifact(s): " + ", ".join(missing) +
            ". Run scripts/exportGexf.py and scripts/renderGraphSvg.py first."
        )

    # Load layout nodes once so we can enrich gaia.json during the copy.
    # Prefer the live generated artifact; fall back to the committed registry
    # copy so CI (which has no generated-output/) can still enrich the graph.
    layouts_src = root / "generated-output" / "layouts.json"
    layout_nodes = {}
    if layouts_src.exists():
        layout_nodes = json.loads(layouts_src.read_text(encoding="utf-8"))
    else:
        committed_src = root / "registry" / "layouts_3d.json"
        if committed_src.exists():
            layout_nodes = json.loads(committed_src.read_text(encoding="utf-8")).get("nodes", {})

    for rel in required:
        src = root / rel
        dst = docs_graph / src.name
        if src.name == "gaia.json" and layout_nodes:
            # Enrich the docs copy with per-skill cluster/positions from the
            # generated layout artifact. registry/gaia.json stays schema-clean.
            gaia_data = json.loads(src.read_text(encoding="utf-8"))
            # Generic refs are rank-less — the web graph's rank legend reads the
            # top named-variant star (namedMaxLevel) instead of a generic level.
            named_max = _named_max_levels(root)
            for skill in gaia_data.get("skills", []):
                sid = skill.get("id")
                if sid in layout_nodes:
                    skill["cluster"] = layout_nodes[sid]["cluster"]
                    skill["positions"] = layout_nodes[sid]["positions"]
                if sid in named_max:
                    skill["namedMaxLevel"] = named_max[sid]
            dst.write_text(json.dumps(gaia_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Synced+enriched {src.relative_to(root)} -> {dst.relative_to(root)}")
        else:
            shutil.copyfile(src, dst)
            print(f"Synced {src.relative_to(root)} -> {dst.relative_to(root)}")

    tree_src = root / "generated-output" / "tree.md"
    if not tree_src.exists():
        raise FileNotFoundError("Missing generated-output/tree.md. Run scripts/generateProjections.py first.")
    tree_dst = root / "docs" / "tree.md"
    shutil.copyfile(tree_src, tree_dst)
    print(f"Synced generated-output/tree.md -> {tree_dst.relative_to(root)}")

    named_index_src = root / "registry" / "named-skills.json"
    if named_index_src.exists():
        named_index_dst = docs_graph / "named" / "index.json"
        named_index_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(named_index_src, named_index_dst)
        print(f"Synced registry/named-skills.json -> {named_index_dst.relative_to(root)}")


def main() -> None:
    sync_docs_graph_assets()


if __name__ == "__main__":
    main()
