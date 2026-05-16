#!/usr/bin/env python3
"""Copy generated graph artifacts into docs/ for GitHub Pages.

GitHub Pages commonly serves the docs/ directory as the site root. Keep the
canonical graph files in registry/, then mirror only the public artifacts that the
static page needs to fetch or download.
"""

from __future__ import annotations

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

    for rel in required:
        src = root / rel
        dst = docs_graph / src.name
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
