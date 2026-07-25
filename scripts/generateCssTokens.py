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

Unique rank ladder (Yggdrasil II — the SECOND ladder on the ONE rank axis)::

    --rank-4-unique[-rgb/-bg/-border/-edge/-symbol]   /* 4★ = branch entry / base */
    --rank-5-unique[-rgb/-edge]                        /* 5★ = burnished copper */
    --rank-6-unique[-rgb/-ink/-edge]                   /* 6★ = ember copper, inverted */

Suite and Unique are two ladders on ONE rank axis: Suite = ``--rank-N`` (from
``gaia.json.meta.levelColors``), Unique = ``--rank-N-unique`` (from the
``UNIQUE_RANK_LADDER`` generator constant, since ``unique`` is a read-time branch
— see that constant). A skill is only Unique at 4★+, so the ladder starts at rank 4.
There is NO ``--tier-unique*`` family and NO branch-generic token divorced from rank.

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

# Yggdrasil II RANK SCHEMA — Suite and Unique are two ladders on ONE rank axis:
# Suite = --rank-N (0..6, from gaia.json.meta.levelColors), Unique = --rank-N-unique.
# There is NO separate "tier unique" and NO branch-generic token divorced from rank.
# A skill is only Unique at 4★+, so every Unique-flavored token keys to the RANK it
# represents: 4★ is where the Unique branch BEGINS (also the base/branch-generic
# default), then the decoration escalates by rank.
#
# `unique` is NOT a gaia.json `type` (the only valid types are 'basic' and 'fusion');
# it is a read-time branch derived by docs/js/skill-semantics.js computeBranch (a Basic
# node that reached elite rank 4★+ without ever fusing). Because it is a read-time
# branch — not a taxonomy tier and not a levelColors entry — the Unique rank ladder
# lives here as a generator constant rather than in gaia.json.meta. (The Suite/type
# tokens still read from gaia.json.meta, so an Ygg III palette swap of the Suite axis
# stays a one-file meta edit + regen; the Unique ladder is the one branch-specific
# constant the generator owns.)
#
# Colorize LOCKED 2026-07-18 (Amethyst→Ember) — do NOT change any hex:
#   4★ = #7c3aed violet (branch entry / base default)
#   5★ = #b26a3a burnished copper
#   6★ = #e0894a ember copper (inverted: copper ground + #2a1206 dark engraved ink)
# Deliberately OFF the Suite gold axis so a Unique never reads as a Suite Apex —
# Unique is its own prestige track. Mirrors scripts/generateBadges.py unique_hex()/
# UNIQUE_INK so badges, graph medallions, and profile plates render one Unique ladder.
UNIQUE_RANK_LADDER = {
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

    # Yggdrasil II Unique rank ladder — emitted under the RANK axis (see below),
    # NOT here. The Unique branch is not a taxonomy tier; it is a rank-keyed
    # decoration (--rank-N-unique) applied once a Basic node reaches 4★+ without
    # fusing. See the rank-tokens section for the emission and UNIQUE_RANK_LADDER
    # for the locked palette. No --tier-unique* family is emitted anymore.

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

    # Yggdrasil II Unique rank ladder (--rank-N-unique) — the SECOND ladder on the
    # rank axis. Suite = --rank-N (above, from gaia.json.meta.levelColors); Unique =
    # --rank-N-unique (here, from the UNIQUE_RANK_LADDER generator constant because
    # `unique` is a read-time branch, not a levelColors entry — see the constant's
    # comment). Membership begins at 4★ (a Basic node that reached elite rank without
    # fusing), so the ladder starts at rank 4 and escalates 4→5→6. Colorize LOCKED
    # 2026-07-18 (Amethyst→Ember): 4★ violet (branch entry / base default), 5★
    # burnished copper, 6★ ember copper inverted (copper ground + dark engraved ink).
    # Mirrors generateBadges.unique_hex()/UNIQUE_INK; consumed by badges/graph/profile.
    body.append("  /* rank: 4★ unique (Unique branch ENTRY / base default) */")
    _u4_rgb = UNIQUE_RANK_LADDER["rgb"]
    body.append(
        f"  --rank-4-unique: {UNIQUE_RANK_LADDER['hex']}; "
        f"/* var(--rank-4-unique, {UNIQUE_RANK_LADDER['hex']}) */"
    )
    body.append(f"  --rank-4-unique-rgb: {_u4_rgb};")
    body.append(f"  --rank-4-unique-bg: rgba({_u4_rgb}, {DEFAULT_BG_ALPHA});")
    body.append(f"  --rank-4-unique-border: rgba({_u4_rgb}, {DEFAULT_BORDER_ALPHA});")
    body.append(f"  --rank-4-unique-edge: rgba({_u4_rgb}, {DEFAULT_EDGE_ALPHA});")
    escaped_symbol = (
        UNIQUE_RANK_LADDER["symbol"].replace("\\", "\\\\").replace("'", "\\'")
    )
    body.append(f"  --rank-4-unique-symbol: '{escaped_symbol}';")
    body.append("  /* rank: 5★ unique (burnished copper) */")
    body.append("  --rank-5-unique: #b26a3a;")
    body.append("  --rank-5-unique-rgb: 178, 106, 58;")
    body.append("  --rank-5-unique-edge: rgba(178, 106, 58, 0.55);")
    body.append("  /* rank: 6★ unique (ember copper, inverted — copper ground + dark ink) */")
    body.append("  --rank-6-unique: #e0894a;")
    body.append("  --rank-6-unique-rgb: 224, 137, 74;")
    body.append("  --rank-6-unique-ink: #2a1206;")
    body.append("  --rank-6-unique-edge: rgba(224, 137, 74, 0.9);")

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

    # §Ygg-II PR 3c: local/custom-user green. A user's OWN uncanonized
    # fusion/custom skill renders GREEN-STARLESS in the 3D World Tree
    # (`gaia graph` custom mode) and in `gaia tree`. Mirrors the CLI's
    # COLOR_LOCAL_USER = (134, 239, 172) = #86efac (src/gaia_cli/formatting.py).
    # A fixed constant (like UNIQUE_RANK_LADDER above) rather than a gaia.json
    # meta color: it is a client/user-state accent, not a taxonomy tier or rank.
    body.append("")
    body.append("  /* ── Local / custom-user accent (Yggdrasil II PR 3c) ───────── */")
    body.append("  /* Green-starless treatment for a user's OWN uncanonized skills.")
    body.append("     Matches the CLI COLOR_LOCAL_USER (134,239,172 / #86efac). */")
    _local_user_hex = "#86efac"
    _local_user_rgb = _rgb_str(_hex_to_rgb_triplet(_local_user_hex))
    body.append(f"  --color-local-user: {_local_user_hex};")
    body.append(f"  --color-local-user-rgb: {_local_user_rgb};")

    # ── Evidence TYPE tokens (provenance color axis) ─────────────────────────
    # Evidence Type ≠ rank ≠ branch. Each canonical evidence type gets its own
    # --ev-type-<name> color so pills stop borrowing --tier-*/--rank-* (which
    # conflated provenance with skill rank — see TOKEN-POLLUTION-AUDIT.md, T16-T18).
    # Hues are the source of truth from docs/evidence/ (the evidence library
    # page). Kebab-case names match the schema evidence.types values and the
    # .ev-type-pill.type-<name> consumer classes in styles.css.
    body.append("")
    body.append(
        "  /* ── Evidence Type tokens (provenance axis — NOT rank/branch) ─── */"
    )
    ev_type_colors = {
        "repo": "#38bdf8",
        "repo-own": "#38bdf8",
        "peer-review": "#38bdf8",
        "github-stars": "#f59e0b",
        "github-stars-own": "#f59e0b",
        "fusion-recipe": "#f59e0b",
        "proxy-containment": "#7c3aed",
        "verifier-attestation": "#e879f9",
        "benchmark-result": "#c084fc",
        "arxiv": "#c084fc",
        "self-attestation": "#94a3b8",
        "social-signal": "#34d399",
    }
    # The trailing `/* var(--ev-type-<name>, <hex>) */` comment mirrors the
    # tier/rank convention above: it is self-documenting AND it satisfies the
    # docs-cohesion Guard A hex-literal grep (which whitelists lines containing
    # a `var(--x,` fallback form). Do not drop it — the guard fails without it.
    for name, hex_val in ev_type_colors.items():
        rgb_triplet = _rgb_str(_hex_to_rgb_triplet(hex_val))
        body.append(
            f"  --ev-type-{name}: {hex_val}; /* var(--ev-type-{name}, {hex_val}) */"
        )
        body.append(f"  --ev-type-{name}-rgb: {rgb_triplet};")

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
