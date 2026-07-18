#!/usr/bin/env python3
"""Generate ``docs/css/tokens.css`` from ``registry/gaia.json``.

Stage 1 — Foundation. Single source of truth for tier and rank colour
tokens is ``registry/gaia.json``'s ``meta`` block. Every UI surface
(JS, CSS, generated profile pages, OG cards, sampler pages) reads the
emitted CSS custom properties — no hex codes hard-coded outside
``gaia.json``.

Emitted tokens
--------------
Tier (one block per tier in ``typeColors``)::

    --tier-<name>          /* hex */
    --tier-<name>-rgb      /* "R, G, B" triplet */
    --tier-<name>-bg       /* rgba(..., .12) translucent fill */
    --tier-<name>-border   /* rgba(..., .35) hairline */
    --tier-<name>-symbol   /* '○' / '◇' / '◉' / '◆' content() value */

Rank (one block per ``"N★"`` key in ``levelColors``, where N ∈ 0..6)::

    --rank-<N>             /* hex */
    --rank-<N>-rgb         /* "R, G, B" triplet */
    --rank-<N>-bg          /* rgba(..., .12-.22) */
    --rank-<N>-border      /* rgba(..., .35-.55) */
    --rank-<N>-edge        /* rgba(..., .55) — translucent stroke for arrows */

Edge derivatives (Stage 5 — Hunter's Atlas DAG / 3D Registry arrows)::

    --tier-<name>-edge     /* rgba(<rgb>, .55) — translucent tier stroke */

These are translucent variants of the canonical hex used as stroke colours
on DAG arrows (``.ns-dag-arrow``) and as highlighted-neighbor edge tints
in the 3D Registry canvas. Stage 5b (markdown Tree) consumes the same
tokens to highlight tier/rank edges inside the tree-dialog.

Legacy aliases (single-source-of-truth bridge for code that predates the
``--tier-*`` canonicalization)::

    --basic / --extra / --unique / --ultimate  →  var(--tier-<name>)

Wired into
----------
* ``scripts/syncDocsGraphAssets.py`` — regenerated every registry update.
* ``scripts/build_docs.py --check`` — fails CI if tokens.css is stale.

Idempotent: running this script twice on the same input produces the
exact same bytes. Stable key ordering by tier insertion order, then by
ascending star value 0..6.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAIA_JSON = ROOT / "registry" / "gaia.json"
TOKENS_CSS = ROOT / "docs" / "css" / "tokens.css"

# Background / border opacity defaults if a colour entry only provides ``hex``.
DEFAULT_BG_ALPHA = 0.12
DEFAULT_BORDER_ALPHA = 0.35

# Yggdrasil II — the Unique branch tier family. `unique` is NOT a gaia.json
# `type` (the only valid types are 'basic' and 'fusion'); it is a read-time
# branch derived by docs/js/skill-semantics.js computeBranch (a Basic node that
# reached elite rank 4★+ without ever fusing). It therefore never appears in
# meta.typeColors, but the site's CSS still needs a stable --tier-unique family
# so downstream var(--tier-unique*) reads resolve token-only (Ygg-II rubric E7).
# Emitting it here keeps `gaia dev docs` regen from silently dropping the block
# (which would re-expose hex fallbacks in consumer CSS/JS). Deep-violet accent
# per design-v6.1.1 §2.2 ("standing stones beside the tree").
UNIQUE_BRANCH_TIER = {
    "hex": "#7c3aed",
    "rgb": "124, 58, 237",
    "symbol": "◉",
}
# Edge (translucent stroke) alpha. Used for ``--tier-*-edge`` and
# ``--rank-N-edge`` derivatives consumed by DAG arrows and canvas
# highlighted-neighbor edges.
DEFAULT_EDGE_ALPHA = 0.55


def _hex_to_rgb_triplet(hex_str: str) -> tuple[int, int, int]:
    """``#38bdf8`` → ``(56, 189, 248)``."""
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Cannot parse hex colour: {hex_str!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_str(rgb: tuple[int, int, int]) -> str:
    return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"


def _star_int(level_key: str) -> int:
    """``"3★"`` → ``3``. Strict: requires a star suffix in the input."""
    if not level_key:
        return -1
    digits = "".join(c for c in level_key if c.isdigit())
    return int(digits) if digits else -1


def _emit_tier_block(name: str, color: dict, symbol: str | None) -> list[str]:
    """Emit five lines for a single tier."""
    hex_val = color.get("hex")
    rgb_raw = color.get("rgb")
    if not hex_val:
        raise ValueError(f"typeColors[{name!r}] missing 'hex'")
    if rgb_raw:
        rgb_triplet = _rgb_str(tuple(int(p.strip()) for p in str(rgb_raw).split(",")))
    else:
        rgb_triplet = _rgb_str(_hex_to_rgb_triplet(hex_val))
    bg = f"rgba({rgb_triplet}, {DEFAULT_BG_ALPHA})"
    border = f"rgba({rgb_triplet}, {DEFAULT_BORDER_ALPHA})"
    edge = f"rgba({rgb_triplet}, {DEFAULT_EDGE_ALPHA})"
    lines = [
        f"  --tier-{name}: {hex_val}; /* var(--tier-{name}, {hex_val}) */",
        f"  --tier-{name}-rgb: {rgb_triplet};",
        f"  --tier-{name}-bg: {bg};",
        f"  --tier-{name}-border: {border};",
        f"  --tier-{name}-edge: {edge};",
    ]
    if symbol:
        # Quote with single quotes; escape any embedded single quotes.
        escaped = symbol.replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"  --tier-{name}-symbol: '{escaped}';")
    return lines


def _emit_rank_block(star: int, color: dict) -> list[str]:
    """Emit five lines for a single rank star value (hex + rgb + bg + border + edge)."""
    hex_val = color.get("hex")
    if not hex_val:
        raise ValueError(f"levelColors[{star}★] missing 'hex'")
    # bg / border may be provided directly; otherwise derive from hex.
    rgb_triplet = _rgb_str(_hex_to_rgb_triplet(hex_val))
    bg = color.get("bg") or f"rgba({rgb_triplet}, {DEFAULT_BG_ALPHA})"
    border = color.get("border") or f"rgba({rgb_triplet}, {DEFAULT_BORDER_ALPHA})"
    edge = f"rgba({rgb_triplet}, {DEFAULT_EDGE_ALPHA})"
    return [
        f"  --rank-{star}: {hex_val}; /* var(--rank-{star}, {hex_val}) */",
        f"  --rank-{star}-rgb: {rgb_triplet};",
        f"  --rank-{star}-bg: {bg};",
        f"  --rank-{star}-border: {border};",
        f"  --rank-{star}-edge: {edge};",
    ]


def build_tokens_css(gaia: dict) -> str:
    """Render the canonical tokens.css text from a gaia.json dict."""
    meta = gaia.get("meta") or {}
    type_colors = meta.get("typeColors") or {}
    type_symbols = meta.get("typeSymbols") or {}
    level_colors = meta.get("levelColors") or {}
    version = gaia.get("version", "unknown")
    generated_at = gaia.get("generatedAt", "")

    body: list[str] = []
    body.append("/*")
    body.append(" * tokens.css — generated by scripts/generateCssTokens.py.")
    body.append(" * Source of truth: registry/gaia.json meta block.")
    body.append(" * DO NOT EDIT BY HAND. Run scripts/generateCssTokens.py to refresh.")
    body.append(" */")
    body.append("")
    body.append(":root {")
    body.append("  /* ── Tier tokens ──────────────────────────────────────────── */")

    # Stable tier order (insertion order from JSON).
    for name, color in type_colors.items():
        body.append(f"  /* tier: {name} */")
        body.extend(_emit_tier_block(name, color, type_symbols.get(name)))

    # Yggdrasil II Unique-branch tier family — always emitted (see
    # UNIQUE_BRANCH_TIER). `unique` is a read-time branch, not a taxonomy type,
    # so it is NOT in meta.typeColors; emitting it here keeps regen from
    # dropping --tier-unique* and re-exposing hex fallbacks (rubric E7).
    body.append(
        "  /* tier: unique — Yggdrasil II branch color alias (NOT a taxonomy type)."
    )
    body.append(
        "     The Unique branch is the standalone-mastery fork: a Basic node that"
    )
    body.append(
        "     reached elite rank (4★+) without ever fusing. `unique` is derived at"
    )
    body.append(
        "     read-time (see docs/js/skill-semantics.js computeBranch); it is never a"
    )
    body.append(
        "     gaia.json `type`, so it is absent from meta.typeColors. Emitted here"
    )
    body.append(
        "     (UNIQUE_BRANCH_TIER) so downstream var(--tier-unique*) reads resolve"
    )
    body.append("     token-only and a regen never drops the family (rubric E7). */")
    body.extend(
        _emit_tier_block(
            "unique",
            {"hex": UNIQUE_BRANCH_TIER["hex"], "rgb": UNIQUE_BRANCH_TIER["rgb"]},
            UNIQUE_BRANCH_TIER["symbol"],
        )
    )

    # v3 amendment (2026-07-18): the Unique DECORATION forks by rank. Membership
    # is `unique` from 4★ up, but the treatment escalates: 4★ violet (base
    # --tier-unique above), 5★ darker gold, 6★ inverted (gold ground / dark ink).
    # These mirror scripts/generateBadges.py unique_hex() so badges, graph
    # medallions, and profile plates render one consistent Unique ladder.
    body.append(
        "  /* Unique decoration ladder (v3, colorize LOCKED 2026-07-18 — Amethyst→Ember):"
    )
    body.append(
        "     4★ = --tier-unique (violet above), 5★ = burnished copper, 6★ = inverted"
    )
    body.append(
        "     (copper ground + dark engraved ink). Deliberately OFF the Suite gold axis"
    )
    body.append(
        "     so a Unique never reads as a Suite Apex — Unique is its own prestige track."
    )
    body.append(
        "     Mirrors generateBadges.unique_hex()/UNIQUE_INK; consumed by badges/graph/profile. */"
    )
    body.append("  --tier-unique-5: #b26a3a;")
    body.append("  --tier-unique-5-rgb: 178, 106, 58;")
    body.append("  --tier-unique-5-edge: rgba(178, 106, 58, 0.55);")
    body.append("  --tier-unique-6: #e0894a;")
    body.append("  --tier-unique-6-rgb: 224, 137, 74;")
    body.append("  --tier-unique-6-ink: #2a1206;")
    body.append("  --tier-unique-6-edge: rgba(224, 137, 74, 0.9);")

    body.append("")
    body.append("  /* ── Rank tokens (0★ → 6★) ───────────────────────────────── */")

    # Stable rank order by star value (0..6 ascending). Skip entries that
    # don't parse as an integer star to avoid surprises.
    parsed_ranks: list[tuple[int, dict]] = []
    for key, color in level_colors.items():
        n = _star_int(key)
        if n >= 0:
            parsed_ranks.append((n, color))
    parsed_ranks.sort(key=lambda t: t[0])
    for star, color in parsed_ranks:
        body.append(f"  /* rank: {star}★ */")
        body.extend(_emit_rank_block(star, color))

    body.append("")
    body.append("  /* ── Legacy short aliases ─────────────────────────────────── */")
    body.append("  /* Bridge for code that predates the --tier-* canonicalization. */")
    body.append("  /* Single source of truth stays in gaia.json.meta.typeColors. */")
    for name in type_colors.keys():
        body.append(f"  --{name}: var(--tier-{name});")

    body.append("")
    body.append("  /* ── Evidence Grade semantic tokens ─────────────────────────── */")
    body.append("  /* New labels for the evidence-grade philosophy; legacy aliases keep existing UI hooks working. */")
    evidence_colors = {
        "platinum": "#e2e8f0",
        "gold": "#d4af37",
        "silver": "#cbd5e1",
        "bronze": "#b45309",
    }
    for label, hex_val in evidence_colors.items():
        rgb_triplet = _rgb_str(_hex_to_rgb_triplet(hex_val))
        body.append(f"  --evidence-{label}: {hex_val};")
        body.append(f"  --evidence-{label}-rgb: {rgb_triplet};")

    body.append("  /* ── Legacy grade aliases ───────────────────────────────────── */")
    grade_aliases = {
        "S": "platinum",
        "A": "gold",
        "B": "silver",
        "C": "bronze",
    }
    for grade, label in grade_aliases.items():
        body.append(f"  --grade-{grade}: var(--evidence-{label});")
        body.append(f"  --grade-{grade}-rgb: var(--evidence-{label}-rgb);")

    body.append("}")
    body.append("")
    return "\n".join(body)


def load_gaia(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        raise SystemExit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail with exit code 1 if tokens.css is stale.",
    )
    parser.add_argument(
        "--gaia",
        default=str(GAIA_JSON),
        help="Path to registry/gaia.json (default: %(default)s).",
    )
    parser.add_argument(
        "--out",
        default=str(TOKENS_CSS),
        help="Output path (default: %(default)s).",
    )
    args = parser.parse_args(argv)

    gaia_path = Path(args.gaia)
    out_path = Path(args.out)

    gaia = load_gaia(gaia_path)
    rendered = build_tokens_css(gaia)

    if args.check:
        if not out_path.exists():
            print(
                f"ERROR: {out_path.relative_to(ROOT)} missing. "
                "Run `python scripts/generateCssTokens.py` to create it.",
                file=sys.stderr,
            )
            return 1
        current = out_path.read_text(encoding="utf-8")
        if current != rendered:
            print(
                f"ERROR: {out_path.relative_to(ROOT)} is stale. "
                "Run `python scripts/generateCssTokens.py` to refresh.",
                file=sys.stderr,
            )
            return 1
        print(f"tokens.css is up to date ({out_path.relative_to(ROOT)}).")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)} ({len(rendered)} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
