#!/usr/bin/env python3
"""Gaia Skill Registry — OG Share Card Generator.

For each named skill, generates an OG share card at:
  docs/og/{handle}/{skillId}.svg   — SVG template (always generated)
  docs/og/{handle}/{skillId}.png   — raster render (if cairosvg or pillow available)

OG card dimensions: 1200×630 (landscape plaque), midnight ink ground,
Diamond Seal at top-left, contributor handle in honor red, skill name in apex gold.

Usage:
    python scripts/generateOgCards.py [--named PATH] [--out-dir PATH]

Exit codes:
    0 — Cards generated successfully
    1 — Fatal error
"""

import json
import os
import sys
import html
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
GAIA_JSON = REPO_ROOT / "registry" / "gaia.json"
DOCS_DIR = REPO_ROOT / "docs"
OUT_DIR = DOCS_DIR / "og"

# OG card dimensions (logical px at 1x)
OG_W = 1200
OG_H = 630

# Brand colors
BG_COLOR = "#030712"
APEX_GOLD = "#fbbf24"
HONOR_RED = "#ef4444"
TEXT_COLOR = "#e2e8f0"
MUTED_COLOR = "#64748b"
BORDER_COLOR = "#1e293b"

# Stage 2 — rank palette mirrors the --rank-N CSS tokens emitted by
# scripts/generateCssTokens.py from registry/gaia.json.meta.levelColors.
# OG cards are static SVG (no CSS engine), so we resolve the rank
# colour from the same source of truth and emit it inline. The keys
# match the .rank-badge[data-level="N"] selectors in styles.css.
_RANK_PALETTE_CACHE: dict | None = None


def rank_palette() -> dict:
    """Return { '0': {'hex','bg','border'}, '1': {...}, … '6': {...} }."""
    global _RANK_PALETTE_CACHE
    if _RANK_PALETTE_CACHE is not None:
        return _RANK_PALETTE_CACHE
    fallback = {
        "0": {"hex": "#94a3b8", "bg": "rgba(148,163,184,.12)", "border": "rgba(148,163,184,.4)"},
        "1": {"hex": "#38bdf8", "bg": "rgba(56,189,248,.12)", "border": "rgba(56,189,248,.4)"},
        "2": {"hex": "#63cab7", "bg": "rgba(99,202,183,.15)", "border": "rgba(99,202,183,.4)"},
        "3": {"hex": "#a78bfa", "bg": "rgba(167,139,250,.15)", "border": "rgba(167,139,250,.4)"},
        "4": {"hex": "#e879f9", "bg": "rgba(232,121,249,.15)", "border": "rgba(232,121,249,.4)"},
        "5": {"hex": "#fbbf24", "bg": "rgba(251,191,36,.15)", "border": "rgba(251,191,36,.4)"},
        "6": {"hex": "#fbbf24", "bg": "rgba(251,191,36,.22)", "border": "rgba(251,191,36,.55)"},
    }
    if not GAIA_JSON.exists():
        _RANK_PALETTE_CACHE = fallback
        return _RANK_PALETTE_CACHE
    try:
        with open(GAIA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        lc = (data.get("meta") or {}).get("levelColors") or {}
        out: dict = {}
        for key, val in lc.items():
            n = "".join(c for c in key if c.isdigit())
            if n:
                out[n] = {"hex": val.get("hex", "#94a3b8"), "bg": val.get("bg", "rgba(148,163,184,.12)"), "border": val.get("border", "rgba(148,163,184,.4)")}
        # Backfill missing keys from fallback so callers never KeyError.
        for k, v in fallback.items():
            out.setdefault(k, v)
        _RANK_PALETTE_CACHE = out
    except Exception:
        _RANK_PALETTE_CACHE = fallback
    return _RANK_PALETTE_CACHE


def level_num(level: str) -> int:
    if not level:
        return 0
    try:
        return int("".join(c for c in level if c.isdigit()))
    except ValueError:
        return 0


def tier_glyph(level: str) -> str:
    n = level_num(level)
    if n >= 6:
        return "◆"
    if n >= 4:
        return "◇"
    return "○"


def evidence_class(level: str) -> str:
    n = level_num(level)
    if n >= 6:
        return "CLASS A"
    if n >= 5:
        return "CLASS A"
    if n >= 4:
        return "CLASS A"
    if n >= 3:
        return "CLASS B"
    if n >= 2:
        return "CLASS C"
    return "AWAITED"


def _star_polygon(cx: float, cy: float, r_outer: float, r_inner: float) -> str:
    import math
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = r_outer if i % 2 == 0 else r_inner
        points.append(f"{cx + r * math.cos(angle):.2f},{cy + r * math.sin(angle):.2f}")
    return " ".join(points)


def build_stars_svg(level: str, x: float, y: float) -> str:
    """Stage 2 — SVG sibling of .rank-badge[data-variant="stars"].

    Lit stars use --apex-gold; dim stars use the same low-alpha gold
    as .rank-badge__star[data-off] in styles.css. Per-star alpha drives
    the visual identity — same source-of-truth palette as the live page.
    """
    n = level_num(level)
    parts = []
    spacing = 22
    r_outer = 9
    r_inner = 3.6
    for i in range(1, 7):
        lit = i <= n
        # Match .rank-badge__star colours: gold lit / alpha-gold dim.
        color = APEX_GOLD if lit else APEX_GOLD
        opacity = "1" if lit else "0.18"
        cx = x + (i - 1) * spacing
        parts.append(
            f'<polygon points="{_star_polygon(cx, y, r_outer, r_inner)}" '
            f'fill="{color}" opacity="{opacity}"/>'
        )
    return "\n".join(parts)


def build_rank_chip_svg(level: str, x: float, y: float, anchor: str = "end") -> str:
    """Stage 2 — SVG sibling of .rank-badge[data-variant="chip"].

    Renders a pill containing the level label coloured by the rank's
    --rank-N hex (sourced from registry/gaia.json.meta.levelColors).
    Anchored at (x, y) for the text baseline.
    """
    n = level_num(level)
    palette = rank_palette().get(str(n), rank_palette()["0"])
    label = html.escape(level or f"{n}★")
    # Approximate pill geometry — width tracks label length so 1★ and 6★ read evenly.
    label_w = max(56, len(label) * 11 + 18)
    pad_x = 12
    pill_y = y - 16
    pill_h = 26
    pill_x = (x - label_w) if anchor == "end" else x
    text_x = (pill_x + label_w - pad_x) if anchor == "end" else (pill_x + pad_x)
    return (
        f'<rect x="{pill_x}" y="{pill_y}" width="{label_w}" height="{pill_h}" rx="13" '
        f'fill="{palette["bg"]}" stroke="{palette["border"]}" stroke-width="1"/>'
        f'<text x="{text_x}" y="{y}" font-family="\'Departure Mono\',\'JetBrains Mono\',monospace" '
        f'font-size="13" font-weight="600" letter-spacing="1.2" fill="{palette["hex"]}" '
        f'text-anchor="{anchor}" dominant-baseline="middle">{label}</text>'
    )


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _wrap_text(text: str, max_chars: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
            continue
        candidate = current + " " + word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    else:
        if current and len(lines) < max_lines:
            lines.append(current)
    if len(lines) == max_lines and (current or words[-1] not in (lines[-1] if lines else "")):
        last = lines[-1]
        if len(last) > 1 and not last.endswith("…"):
            lines[-1] = last[: max_chars - 1].rstrip() + "…"
    return lines


def build_og_svg(skill: dict) -> str:
    """Build a 1200×630 SVG OG card for a named skill."""
    name = html.escape(truncate(skill.get("name", skill.get("id", "Unnamed")), 40))
    contributor = html.escape(skill.get("contributor", ""))
    level = skill.get("level", "2★")
    title = html.escape(truncate(skill.get("title", ""), 55))
    description_raw = truncate(skill.get("description", ""), 240)
    description_lines = _wrap_text(description_raw, max_chars=58, max_lines=4)
    description_tspans = "\n".join(
        f'<tspan x="264" dy="{"0" if i == 0 else "28"}">{html.escape(line)}</tspan>'
        for i, line in enumerate(description_lines)
    )
    glyph = tier_glyph(level)
    level_str = html.escape(level)
    ev_class = evidence_class(level)
    is_apex = level_num(level) >= 6

    # Gradient IDs need to be unique per card
    skill_id = skill.get("id", "unknown").replace("/", "-").replace(" ", "-")
    grad_id = f"grad-{skill_id}"

    apex_effects = ""
    if is_apex:
        apex_effects = f"""<defs>
  <filter id="vi-glow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur"/>
    <feColorMatrix in="blur" type="matrix"
      values="1 0.5 0 0 0  0.8 0.8 0 0 0  0 0.2 0.2 0 0  0 0 0 0.6 0"
      result="colored"/>
    <feMerge><feMergeNode in="colored"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>"""

    stars_svg = build_stars_svg(level, 64, 435)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="{OG_W}" height="{OG_H}" viewBox="0 0 {OG_W} {OG_H}">
  <defs>
    <linearGradient id="{grad_id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{APEX_GOLD}" stop-opacity="0.04"/>
      <stop offset="50%" stop-color="{APEX_GOLD}" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="{APEX_GOLD}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  {apex_effects}

  <!-- Ground -->
  <rect width="{OG_W}" height="{OG_H}" fill="{BG_COLOR}"/>

  <!-- Subtle vignette -->
  <defs>
    <radialGradient id="vign-{skill_id}" cx="50%" cy="50%" r="70%">
      <stop offset="0%" stop-color="transparent"/>
      <stop offset="100%" stop-color="rgba(0,0,0,0.5)"/>
    </radialGradient>
  </defs>
  <rect width="{OG_W}" height="{OG_H}" fill="url(#vign-{skill_id})"/>

  <!-- Gold overlay tint -->
  <rect width="{OG_W}" height="{OG_H}" fill="url(#{grad_id})"/>

  <!-- Outer hairline border -->
  <rect x="1" y="1" width="{OG_W-2}" height="{OG_H-2}"
    fill="none" stroke="rgba(251,191,36,0.2)" stroke-width="1"/>

  <!-- Corner ornaments TL -->
  <path d="M 20 20 L 20 44 M 20 20 L 44 20"
    stroke="rgba(251,191,36,0.4)" stroke-width="1.5" fill="none"/>
  <!-- Corner ornaments BR -->
  <path d="M {OG_W-20} {OG_H-20} L {OG_W-20} {OG_H-44} M {OG_W-20} {OG_H-20} L {OG_W-44} {OG_H-20}"
    stroke="rgba(251,191,36,0.4)" stroke-width="1.5" fill="none"/>

  <!-- ─── Left column ─── -->
  <!-- Diamond Seal -->
  <svg x="48" y="52" width="52" height="52" viewBox="0 0 64 64">
    <path d="M 32 4 L 60 32 L 32 60 L 4 32 Z"
      fill="none" stroke="{APEX_GOLD}" stroke-width="2.5" stroke-linejoin="miter" opacity="0.7"/>
    <text x="32" y="34" font-family="Georgia,serif" font-weight="600" font-size="28"
      fill="{APEX_GOLD}" text-anchor="middle" dominant-baseline="central" opacity="0.7">G</text>
  </svg>

  <!-- Tier glyph (large) -->
  <text x="48" y="175" font-family="Georgia,serif" font-size="52"
    fill="{APEX_GOLD}" opacity="0.85">{glyph}</text>

  <!-- Stars -->
  {stars_svg}

  <!-- Vertical rule -->
  <line x1="220" y1="40" x2="220" y2="{OG_H-40}"
    stroke="rgba(251,191,36,0.12)" stroke-width="1"/>

  <!-- ─── Right / main column ─── -->
  <!-- Skill name -->
  <text x="264" y="160"
    font-family="EB Garamond,Georgia,serif"
    font-size="52" font-weight="600"
    fill="{APEX_GOLD}" dominant-baseline="middle">{name}</text>

  <!-- Title (italic subtitle) -->
  {'<text x="264" y="220" font-family="EB Garamond,Georgia,serif" font-size="22" font-style="italic" fill="rgba(226,232,240,0.5)" dominant-baseline="middle">' + title + '</text>' if title else ''}

  <!-- Horizontal rule -->
  <line x1="264" y1="256" x2="{OG_W-48}" y2="256"
    stroke="rgba(251,191,36,0.2)" stroke-width="1"/>

  <!-- Description -->
  <text x="264" y="298"
    font-family="Bricolage Grotesque,Helvetica,Arial,sans-serif"
    font-size="18" fill="rgba(226,232,240,0.65)">
    {description_tspans}
  </text>

  <!-- Evidence class chip -->
  <rect x="264" y="504" width="{len(ev_class) * 8 + 24}" height="28"
    rx="3" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
  <text x="276" y="518"
    font-family="monospace" font-size="11" letter-spacing="1.5"
    fill="rgba(226,232,240,0.5)" dominant-baseline="middle"
    text-transform="uppercase">{ev_class}</text>

  <!-- Stage 2 — Level chip mirrors .rank-badge[data-variant="chip"]. -->
  {build_rank_chip_svg(level, OG_W - 64, 518, anchor="end")}

  <!-- Horizontal rule bottom -->
  <line x1="264" y1="550" x2="{OG_W-48}" y2="550"
    stroke="rgba(251,191,36,0.2)" stroke-width="1"/>

  <!-- Contributor handle -->
  <text x="264" y="590"
    font-family="'Bricolage Grotesque',sans-serif" font-size="18" font-weight="600"
    fill="{HONOR_RED}" dominant-baseline="middle">@{contributor}</text>

  <!-- Gaia wordmark (bottom-right) -->
  <text x="{OG_W - 64}" y="590"
    font-family="EB Garamond,Georgia,serif" font-size="18" font-weight="600"
    fill="rgba(226,232,240,0.3)" text-anchor="end" dominant-baseline="middle">Gaia</text>

  <!-- Bottom underline accent -->
  <line x1="{OG_W//2 - 200}" y1="{OG_H - 4}" x2="{OG_W//2 + 200}" y2="{OG_H - 4}"
    stroke="{APEX_GOLD}" stroke-width="2" stroke-opacity="0.3"/>
</svg>
"""


def try_render_png(svg_content: str, out_path: Path) -> bool:
    """Try to render SVG to PNG using cairosvg or pillow. Returns True on success."""
    # Try cairosvg first
    try:
        import cairosvg
        cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            write_to=str(out_path),
            output_width=OG_W,
            output_height=OG_H,
        )
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"    cairosvg render failed: {e}", file=sys.stderr)

    # Try pillow with wand
    try:
        from wand.image import Image as WandImage
        with WandImage(blob=svg_content.encode("utf-8"), format="svg") as img:
            img.format = "png"
            img.save(filename=str(out_path))
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"    wand render failed: {e}", file=sys.stderr)

    return False


def load_named_data(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_all_skills(data: dict) -> list:
    """Return flat list of all skill entries."""
    skills = []
    for bucket_skills in data.get("buckets", {}).values():
        skills.extend(bucket_skills)
    return skills


def generate_og_cards(named_path: Path, out_dir: Path) -> int:
    """Generate OG card SVGs (and PNGs if possible). Returns total count."""
    data = load_named_data(named_path)
    skills = collect_all_skills(data)

    if not skills:
        print("No named skills found — no OG cards generated.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    svg_count = 0
    png_count = 0

    for skill in skills:
        handle = skill.get("contributor", "")
        skill_id_full = skill.get("id", "")
        if not handle or not skill_id_full:
            continue

        # Derive file stem from skill id (last segment after /)
        skill_slug = skill_id_full.split("/")[-1]

        handle_dir = out_dir / handle
        handle_dir.mkdir(parents=True, exist_ok=True)

        # Always generate SVG
        svg_path = handle_dir / f"{skill_slug}.svg"
        svg_content = build_og_svg(skill)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        svg_count += 1

        # Attempt PNG render
        png_path = handle_dir / f"{skill_slug}.png"
        if try_render_png(svg_content, png_path):
            png_count += 1
            print(f"  SVG+PNG: docs/og/{handle}/{skill_slug}.{{svg,png}}")
        else:
            print(f"  SVG:     docs/og/{handle}/{skill_slug}.svg")

    print(f"\nGenerated {svg_count} SVG card(s), {png_count} PNG render(s).")
    if png_count == 0:
        print(
            "  Note: Install cairosvg (`pip install cairosvg`) to enable PNG rendering."
        )
    return svg_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OG share cards from named-skills.json"
    )
    parser.add_argument(
        "--named",
        default=str(NAMED_JSON),
        help="Path to named-skills.json (default: registry/named-skills.json)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Output directory for OG cards (default: docs/og/)",
    )
    args = parser.parse_args()

    named_path = Path(args.named)
    out_dir = Path(args.out_dir)

    print(f"Loading named skills from: {named_path}")
    generate_og_cards(named_path, out_dir)


if __name__ == "__main__":
    main()
