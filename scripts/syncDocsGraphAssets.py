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


def _bucket_origins(root: Path) -> dict:
    """Map generic skill id -> its bucket's single CLI-declared origin entry.

    Yggdrasil II ORIGIN RULE (the crux): each bucket in named-skills.json has AT
    MOST ONE entry flagged ``origin: true`` (declared via the CLI before build).
    The generic/starless node surfaces THAT entry's already-emitted taxonomy
    fields (branch/rank/rankWord/medallion/level) — NOT the max-level entry.

    Buckets with zero origins are simply absent from the returned map: the
    generic node then gets nothing stamped and stays a plain starless node.
    There is deliberately NO max-level fallback — origin is the entire pipeline.
    """
    src = root / "registry" / "named-skills.json"
    if not src.exists():
        return {}
    buckets = json.loads(src.read_text(encoding="utf-8")).get("buckets", {})
    out = {}
    for ref, entries in buckets.items():
        origins = [e for e in entries if e.get("origin") is True]
        if origins:
            # Exactly one by construction; if data ever regressed, first wins.
            out[ref] = origins[0]
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

    # Load ultimate gate config for trust grade injection
    _gate_config: dict = {}
    _meta_path = root / "registry" / "schema" / "meta.json"
    if _meta_path.exists():
        try:
            _gate_config = json.loads(_meta_path.read_text(encoding="utf-8")).get("evidence", {}).get("ultimateGate", {})
        except Exception:
            pass

    for rel in required:
        src = root / rel
        dst = docs_graph / src.name
        if src.name == "gaia.json":
            # Enrich the docs copy with per-skill cluster/positions from the
            # generated layout artifact. registry/gaia.json stays schema-clean.
            gaia_data = json.loads(src.read_text(encoding="utf-8"))
            # Class S decorative invariant (#807 / Option B): the docs/graph
            # copy is rendering-only; no consumer parses its version field, and
            # having it here was the dominant source of cross-PR lockstep
            # failures. Strip on sync so the file is unambiguously a runtime
            # asset, not a release manifest.
            gaia_data.pop("version", None)
            # Generic refs are rank-less. Each bucket's CLI-declared ORIGIN
            # entry (origin: true) carries the taxonomy fields the browser reads;
            # surface them onto the generic node at build time (PURE BUILD — the
            # client never resolves branch on the starless graph). Buckets with
            # no origin leave their generic node untouched (plain starless node).
            bucket_origins = _bucket_origins(root)
            skills_list = gaia_data.get("skills", [])
            generic_skills_map = {s.get("id"): s for s in skills_list}

            # Import grading functions for Overall Trust Grade injection
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
            from gaia_cli.grading import overall_trust_grade, check_ultimate_gate  # noqa: E402

            for skill in skills_list:
                sid = skill.get("id")
                if layout_nodes and sid in layout_nodes:
                    skill["cluster"] = layout_nodes[sid]["cluster"]
                    skill["positions"] = layout_nodes[sid]["positions"]
                if sid in bucket_origins:
                    origin = bucket_origins[sid]
                    # Stamp the ORIGIN's already-emitted taxonomy fields. The
                    # graph JS reads node.branch/medallion directly and reads
                    # namedMaxLevel for rank color/size — namedMaxLevel now
                    # carries the ORIGIN's level (not the bucket max).
                    skill["branch"] = origin.get("branch")
                    skill["rank"] = origin.get("rank")
                    skill["rankWord"] = origin.get("rankWord")
                    skill["medallion"] = origin.get("medallion")
                    skill["namedMaxLevel"] = origin.get("level")
                # Inject overall trust grade (computed, not stored in nodes)
                grade = overall_trust_grade(skill.get("evidence") or [])
                if grade is not None:
                    skill["overallTrustGrade"] = grade
                # Inject ultimate gate status for ultimate-type skills
                if skill.get("type") == "ultimate":
                    gate = check_ultimate_gate(skill, generic_skills_map, _gate_config)
                    skill["ultimateGateStatus"] = {
                        "passes": gate["passes"],
                        "reason": gate["reason"],
                    }
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
