#!/usr/bin/env python3
"""Gaia Skill Registry — Hall Plate (OG share card) Generator.

For each named skill, generates a Hall Plate at:
  docs/og/{handle}/{skillId}.svg   — SVG plate (always generated)
  docs/og/{handle}/{skillId}.png   — raster render (if cairosvg or pillow available)

The plates are rendered as entries in *Gaia's Celestial Atlas of Skills*. Three
celestial subjects, three different plate compositions, **one cartographic style**:

  Plate VI  · APEX SUPERNOVA   (Ultimate Skill - Apex, level 6★)
  Plate V   · STELLAR          (Ultimate Skill, level <6 with type=ultimate)
  Plate IV  · SINGULARITY      (Unique Skill, type=unique)
  Plate (default)              (basic / extra — minimal fallback for the
                                cron generator; never promoted to the Atlas)

Reference grammar (Bode's Uranographia, Hevelius's Firmamentum):
  RA/Dec ticks at the top, roman-numeral plate number top-right, discoverer's
  signature in honor red above an engraved rule, marginal magnitude band at
  the foot of every plate. The reader recognises the atlas; each plate is a
  unique entry within it.

All three plates share one ground (`INK_NIGHT`, the printed night sky) and one
engraving colour (`CREAM_ENGRAVED`, warm cream linework + type). Each plate
introduces a single chromatic event — the celestial body itself.

Usage:
    python scripts/generateOgCards.py [--named PATH] [--out-dir PATH]

Exit codes:
    0 — Cards generated successfully
    1 — Fatal error
"""

import argparse
import html
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
GAIA_JSON = REPO_ROOT / "registry" / "gaia.json"
DOCS_DIR = REPO_ROOT / "docs"
OUT_DIR = DOCS_DIR / "og"

# Plate dimensions (logical px at 1x). Read by every helper.
OG_W = 1200
OG_H = 630
MARGIN = 48                # outer plate margin (top, left, right)
RULE_Y = 558               # y of the engraved rule above the marginal band
SIG_Y = 538                # baseline of the discoverer's signature line
TICK_Y = 38                # baseline of the RA/Dec tick row at the top
PLATE_NO_Y = 38            # baseline of the roman-numeral plate number

# ─── Atlas palette ────────────────────────────────────────────────────────────
# These two pigments are the entire ground+ink of every plate. They are SEALED
# to this generator — they do NOT propagate into tokens.css. The plates are a
# sub-surface inside the broader Gaia design system.
INK_NIGHT = "#0e0d20"          # OKLCH ~ oklch(13% 0.025 275); printed night-sky ground
CREAM_ENGRAVED = "#ebe5d4"     # OKLCH ~ oklch(92% 0.015  80); warm cream ink/linework

# ─── Brand voice tokens (resolved from DESIGN.md / styles.css) ────────────────
HONOR_RED = "#ef4444"          # discoverer's signature only
APEX_GOLD = "#fbbf24"          # supernova core + filaments (Plate VI)
AMBER_STAR = "#f59e0b"         # main-sequence star disc (Plate V)
VIOLET_HALO = "#7c3aed"        # black-hole accretion ring (Plate IV)


# ─── Tier / rank resolution helpers (kept compatible with previous generator) ─
_TIER_PALETTE_CACHE: dict | None = None
_RANK_PALETTE_CACHE: dict | None = None
_TYPE_BY_ID: dict | None = None


def tier_palette() -> dict:
    """Return { 'basic': {'hex','rgb'}, …, 'ultimate': {…} } from gaia.json."""
    global _TIER_PALETTE_CACHE
    if _TIER_PALETTE_CACHE is not None:
        return _TIER_PALETTE_CACHE
    fallback = {
        "basic":    {"hex": "#38bdf8", "rgb": "56,189,248"},
        "extra":    {"hex": "#c084fc", "rgb": "192,132,252"},
        "unique":   {"hex": "#7c3aed", "rgb": "124,58,237"},
        "ultimate": {"hex": "#f59e0b", "rgb": "245,158,11"},
    }
    if not GAIA_JSON.exists():
        _TIER_PALETTE_CACHE = fallback
        return _TIER_PALETTE_CACHE
    try:
        with open(GAIA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        tc = (data.get("meta") or {}).get("typeColors") or {}
        out: dict = {}
        for k, v in tc.items():
            out[k] = {
                "hex": v.get("hex", fallback.get(k, {}).get("hex", "#38bdf8")),
                "rgb": v.get("rgb", fallback.get(k, {}).get("rgb", "56,189,248")),
            }
        for k, v in fallback.items():
            out.setdefault(k, v)
        _TIER_PALETTE_CACHE = out
    except Exception:
        _TIER_PALETTE_CACHE = fallback
    return _TIER_PALETTE_CACHE


def rank_palette() -> dict:
    """Return { '0': {'hex'}, …, '6': {'hex'} } from gaia.json.meta.levelColors."""
    global _RANK_PALETTE_CACHE
    if _RANK_PALETTE_CACHE is not None:
        return _RANK_PALETTE_CACHE
    fallback = {
        "0": {"hex": "#94a3b8"},
        "1": {"hex": "#38bdf8"},
        "2": {"hex": "#63cab7"},
        "3": {"hex": "#a78bfa"},
        "4": {"hex": "#e879f9"},
        "5": {"hex": "#fbbf24"},
        "6": {"hex": "#fbbf24"},
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
                out[n] = {"hex": val.get("hex", "#94a3b8")}
        for k, v in fallback.items():
            out.setdefault(k, v)
        _RANK_PALETTE_CACHE = out
    except Exception:
        _RANK_PALETTE_CACHE = fallback
    return _RANK_PALETTE_CACHE


def tier_lookup_for_named() -> dict:
    """Map canonical-skill id → type so plates inherit tier from gaia.json."""
    if not GAIA_JSON.exists():
        return {}
    try:
        with open(GAIA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {s.get("id"): s.get("type", "basic") for s in data.get("skills", [])}
    except Exception:
        return {}


def resolve_type_for_og(entry: dict) -> str:
    """Resolve the canonical type for a named-skill entry."""
    global _TYPE_BY_ID
    if _TYPE_BY_ID is None:
        _TYPE_BY_ID = tier_lookup_for_named()
    ref = entry.get("genericSkillRef")
    if ref and ref in _TYPE_BY_ID:
        return _TYPE_BY_ID[ref]
    raw_id = entry.get("id", "")
    if "/" in raw_id:
        slug = raw_id.split("/", 1)[1]
        if slug in _TYPE_BY_ID:
            return _TYPE_BY_ID[slug]
    return entry.get("type", "basic") or "basic"


def level_num(level: str) -> int:
    if not level:
        return 0
    try:
        return int("".join(c for c in level if c.isdigit()))
    except ValueError:
        return 0


def evidence_class(level: str) -> str:
    n = level_num(level)
    if n >= 4:
        return "CLASS A"
    if n >= 3:
        return "CLASS B"
    if n >= 2:
        return "CLASS C"
    return "AWAITED"


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


# ─── Cataloguing helpers ──────────────────────────────────────────────────────

_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def to_roman(n: int) -> str:
    if n < 0 or n >= len(_ROMAN):
        return str(n)
    return _ROMAN[n]


def slug_after_slash(skill: dict) -> str:
    raw_id = skill.get("id", "") or ""
    if "/" in raw_id:
        return raw_id.split("/", 1)[1]
    ref = skill.get("genericSkillRef") or raw_id
    return ref or ""


def designation_year(skill: dict) -> str:
    """Return the catalogue year — uses createdAt if available, else 2026."""
    created = skill.get("createdAt") or skill.get("updatedAt") or ""
    if isinstance(created, str) and len(created) >= 4 and created[:4].isdigit():
        return created[:4]
    return "2026"


def autoscale_font(text: str, default_px: int, available_w: float, avg_glyph_ratio: float = 0.46) -> int:
    """Roughly fit `text` into `available_w` by shrinking the font size.

    EB Garamond at weight 600 averages ~0.46× the font-size per glyph at the
    sizes we render. This is approximate but good enough for the slug — long
    skill slugs (e.g. /agent-systems-architecture-toolkit) need to drop from
    88px down toward 56px to clear the right margin.
    """
    if not text:
        return default_px
    needed = len(text) * default_px * avg_glyph_ratio
    if needed <= available_w:
        return default_px
    return max(40, int(default_px * available_w / needed))


# ─── Shared atlas grammar (every plate uses these) ────────────────────────────

def _radec_ticks() -> str:
    """Top RA/Dec tick row — five labels in cream Departure Mono at 28% alpha."""
    labels = ["+20°", "+10°", "0°", "−10°", "−20°"]
    inner_w = OG_W - MARGIN * 2 - 200  # leave room for PLATE NUMBER on the right
    step = inner_w / (len(labels) - 1)
    parts = []
    for i, lab in enumerate(labels):
        x = MARGIN + i * step
        parts.append(
            f'<text x="{x:.1f}" y="{TICK_Y}" font-family="\'Departure Mono\',\'JetBrains Mono\',ui-monospace,monospace" '
            f'font-size="11" letter-spacing="1.6" fill="{CREAM_ENGRAVED}" fill-opacity="0.28" '
            f'dominant-baseline="middle">— {lab}</text>'
        )
        # tiny vertical tick mark above the label
        parts.append(
            f'<line x1="{x:.1f}" y1="{TICK_Y - 16}" x2="{x:.1f}" y2="{TICK_Y - 8}" '
            f'stroke="{CREAM_ENGRAVED}" stroke-opacity="0.22" stroke-width="0.8"/>'
        )
    return "\n  ".join(parts)


def _plate_number(label: str) -> str:
    """Top-right skill-type label, mono caps tracked +0.18em."""
    return (
        f'<text x="{OG_W - MARGIN}" y="{PLATE_NO_Y}" '
        f'font-family="\'Departure Mono\',\'JetBrains Mono\',ui-monospace,monospace" '
        f'font-size="18" letter-spacing="3.2" fill="{CREAM_ENGRAVED}" fill-opacity="0.7" '
        f'text-anchor="end" dominant-baseline="middle">{html.escape(label)}</text>'
    )


def _engraved_rule() -> str:
    """Heavy hairline rule above the magnitude band."""
    return (
        f'<line x1="{MARGIN}" y1="{RULE_Y}" x2="{OG_W - MARGIN}" y2="{RULE_Y}" '
        f'stroke="{CREAM_ENGRAVED}" stroke-opacity="0.35" stroke-width="1"/>'
    )


def _magnitude_band(magnitude: str, ev_class: str, stars_or_word: str, designation: str) -> str:
    """Marginal mono data band: MAG · CLASS · STARS-OR-WORD · DESIGNATION."""
    y = RULE_Y + 28
    sep = '<tspan fill-opacity="0.35"> · · · </tspan>'
    cells = [
        f'<tspan>MAG {html.escape(magnitude)}</tspan>',
        f'<tspan>{html.escape(ev_class)}</tspan>',
        f'<tspan>{html.escape(stars_or_word)}</tspan>',
        f'<tspan>{html.escape(designation)}</tspan>',
    ]
    inner = sep.join(cells)
    return (
        f'<text x="{MARGIN}" y="{y}" '
        f'font-family="\'Departure Mono\',\'JetBrains Mono\',ui-monospace,monospace" '
        f'font-size="13" letter-spacing="1.5" fill="{CREAM_ENGRAVED}" fill-opacity="0.7">'
        f'{inner}</text>'
    )


def _catalog_signature(contributor: str, is_origin: bool, year: str) -> str:
    """Discoverer's signature in honor red, EB Garamond italic 22px.

    Atlas convention: the literal word "Cataloged", then the @handle, then —
    if origin is set — an inline `· ORIGIN ·` token, then the year.
    """
    handle = html.escape(contributor or "")
    parts = [
        '<tspan font-style="normal" fill-opacity="0.82">Cataloged by </tspan>',
        f'<tspan font-weight="600">@{handle}</tspan>',
    ]
    if is_origin:
        parts.append(
            ' <tspan font-style="normal" letter-spacing="2.2" font-size="18" '
            'fill-opacity="0.9">· ORIGIN ·</tspan>'
        )
    else:
        parts.append(' <tspan font-style="normal" fill-opacity="0.5">·</tspan> ')
    parts.append(f'<tspan font-style="normal" fill-opacity="0.7"> {html.escape(year)}</tspan>')
    body = "".join(parts)
    return (
        f'<text x="{MARGIN}" y="{SIG_Y}" font-family="\'EB Garamond\',Georgia,serif" '
        f'font-size="22" font-style="italic" fill="{HONOR_RED}" '
        f'dominant-baseline="middle">{body}</text>'
    )


def _diamond_seal(x: float, y: float, size: float = 28.0) -> str:
    """Atlas publisher's mark — Diamond Seal in cream. Apex plates only."""
    half = size / 2
    return (
        f'<svg x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" viewBox="0 0 64 64">'
        f'<path d="M 32 4 L 60 32 L 32 60 L 4 32 Z" fill="none" '
        f'stroke="{CREAM_ENGRAVED}" stroke-width="2.4" stroke-linejoin="miter" opacity="0.78"/>'
        f'<text x="32" y="34" font-family="\'EB Garamond\',Georgia,serif" font-weight="600" '
        f'font-size="28" fill="{CREAM_ENGRAVED}" text-anchor="middle" dominant-baseline="central" '
        f'opacity="0.8">G</text>'
        f'</svg>'
    )


def _shared_frame(plate_label: str) -> str:
    """The four pieces every plate shares: ground, RA/Dec ticks, plate label,
    engraved rule. Caller is responsible for the magnitude band + signature
    (because their text varies per plate)."""
    return (
        f'<rect width="{OG_W}" height="{OG_H}" fill="{INK_NIGHT}"/>\n'
        + _radec_ticks() + "\n"
        + _plate_number(plate_label) + "\n"
        + _engraved_rule()
    )


# ─── Plate VI · APEX SUPERNOVA ────────────────────────────────────────────────

def build_supernova_plate(skill: dict) -> str:
    """Plate VI — supernova remnant.

    Composition: hot white core disc (left-of-centre) with six radial gold
    filaments — one per star earned at apex tier — plus the slug, italic
    kicker, honor-red signature, and marginal magnitude band reading
    `MAG 6.0 · CLASS A · ★★★★★★ · α 6 OBS · YYYY`.
    """
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "6★"))
    sid = (skill.get("id") or "unknown").replace("/", "-").replace(" ", "-")

    # Subject geometry — supernova sits left-of-centre.
    cx, cy = 360, 290
    core_r = 12

    # Six radial filaments, one per star. Slight irregularity in length.
    rays = []
    ray_lens = [220, 200, 230, 210, 195, 215]
    for i, length in enumerate(ray_lens):
        angle = -math.pi / 2 + i * (math.pi * 2 / 6)
        ex = cx + length * math.cos(angle)
        ey = cy + length * math.sin(angle)
        # Mild perpendicular curve so the rays read engraved, not laser-printed.
        mx = (cx + ex) / 2 + 12 * math.cos(angle + math.pi / 2)
        my = (cy + ey) / 2 + 12 * math.sin(angle + math.pi / 2)
        rays.append(
            f'<path d="M {cx} {cy} Q {mx:.1f} {my:.1f} {ex:.1f} {ey:.1f}" '
            f'stroke="{APEX_GOLD}" stroke-opacity="0.78" stroke-width="1.5" '
            f'stroke-linecap="round" fill="none"/>'
        )
    rays_svg = "\n  ".join(rays)

    # Faint scatter of stellar-field dots around the supernova.
    field_dots = []
    for fx, fy, op in [
        (180, 200, 0.5), (560, 240, 0.45), (210, 360, 0.5),
        (520, 380, 0.55), (300, 130, 0.4), (470, 410, 0.4),
    ]:
        field_dots.append(
            f'<circle cx="{fx}" cy="{fy}" r="1.4" fill="{CREAM_ENGRAVED}" fill-opacity="{op}"/>'
        )
    field_svg = "\n  ".join(field_dots)

    # Slug + kicker — right of the supernova, vertically centered with the core.
    slug_x = 660
    slug_w = OG_W - slug_x - MARGIN
    slug_size = autoscale_font(slug_raw, default_px=88, available_w=slug_w)
    slug_y = 286
    kicker_y = slug_y + 50

    # Magnitude band — apex reads "★★★★★★ · α 6 OBS · YYYY".
    stars_word = "★" * max(1, min(6, n_lvl))
    designation = f"α 6 OBS · {year}"

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\"
  width=\"{OG_W}\" height=\"{OG_H}\" viewBox=\"0 0 {OG_W} {OG_H}\"
  class=\"plate plate--apex\" data-plate=\"VI\" data-type=\"ultimate\" data-level=\"{n_lvl}\">
  <defs>
    <radialGradient id=\"sn-core-{sid}\" cx=\"50%\" cy=\"50%\" r=\"50%\">
      <stop offset=\"0%\" stop-color=\"#fff7d6\" stop-opacity=\"1\"/>
      <stop offset=\"40%\" stop-color=\"{APEX_GOLD}\" stop-opacity=\"0.95\"/>
      <stop offset=\"100%\" stop-color=\"{APEX_GOLD}\" stop-opacity=\"0\"/>
    </radialGradient>
  </defs>

  {_shared_frame('Ultimate Skill - Apex')}

  <!-- Diamond Seal (Apex only — atlas publisher's mark) -->
  {_diamond_seal(MARGIN, MARGIN + 4, size=28)}

  <!-- Stellar field scatter -->
  {field_svg}

  <!-- Six radial filaments -->
  {rays_svg}

  <!-- Hot core: blooming halo + bright disc -->
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"58\" fill=\"url(#sn-core-{sid})\"/>
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{core_r}\" fill=\"#fff7d6\"/>

  <!-- SN designation (catalogue prefix) -->
  <text x=\"{slug_x}\" y=\"{slug_y - 64}\" font-family=\"'Departure Mono','JetBrains Mono',ui-monospace,monospace\"
    font-size=\"28\" letter-spacing=\"4.4\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.7\">SN</text>

  <!-- Slash-skill slug (catalogue designation) -->
  <text x=\"{slug_x}\" y=\"{slug_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-weight=\"600\"
    font-size=\"{slug_size}\" fill=\"{CREAM_ENGRAVED}\" dominant-baseline=\"middle\">/{slug}</text>

  <!-- Title kicker -->
  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">'{title}'</text>

  <!-- Discoverer signature -->
  {_catalog_signature(contributor, is_origin, year)}

  <!-- Marginal magnitude band -->
  {_magnitude_band('6.0', 'CLASS A', stars_word, designation)}
</svg>
"""


# ─── Plate V · STELLAR ────────────────────────────────────────────────────────

def build_stellar_plate(skill: dict) -> str:
    """Plate V — main-sequence star with two concentric orbital tracks.

    Composition: amber disc centred on the right two-thirds of the plate,
    two cream hairline orbits, four cream companion dots placed on the
    orbits (abstract for v1; semantic prereq mapping is a follow-up).
    Slug uses Bayer convention: `α /sparc-methodology`.
    """
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "5★"))
    sid = (skill.get("id") or "unknown").replace("/", "-").replace(" ", "-")

    # Star sits right-of-centre. Slug occupies the left third.
    cx, cy = 880, 290
    disc_r = 42

    # Two concentric orbits (long-dash hairlines, like real chart plots).
    r1, r2 = 90, 150
    orbits = (
        f'<circle cx="{cx}" cy="{cy}" r="{r1}" fill="none" stroke="{CREAM_ENGRAVED}" '
        f'stroke-opacity="0.45" stroke-width="1" stroke-dasharray="6 4"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r2}" fill="none" stroke="{CREAM_ENGRAVED}" '
        f'stroke-opacity="0.32" stroke-width="1" stroke-dasharray="8 6"/>'
    )

    # Four companion dots — two per orbit, placed at canonical positions.
    companion_specs = [
        (r1, -math.pi / 6),
        (r1,  math.pi - math.pi / 8),
        (r2,  math.pi / 3),
        (r2, -math.pi + math.pi / 7),
    ]
    dots = []
    for r, ang in companion_specs:
        dx = cx + r * math.cos(ang)
        dy = cy + r * math.sin(ang)
        dots.append(
            f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3" fill="{CREAM_ENGRAVED}" fill-opacity="0.85"/>'
        )
    dots_svg = "\n  ".join(dots)

    # Slug — left third.
    slug_x = MARGIN + 12
    slug_w = 560
    slug_size = autoscale_font(slug_raw, default_px=80, available_w=slug_w)
    slug_y = 268

    # Bayer prefix sits ABOVE the slug.
    bayer_y = slug_y - 56
    kicker_y = slug_y + 48

    # Magnitude band — Stellar reads "5.0 · CLASS A · ★★★★★ · α SLUG · YYYY".
    stars_word = "★" * max(1, min(6, n_lvl))
    designation = f"α {slug_raw[:18].upper()} · {year}"

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\"
  width=\"{OG_W}\" height=\"{OG_H}\" viewBox=\"0 0 {OG_W} {OG_H}\"
  class=\"plate plate--stellar\" data-plate=\"V\" data-type=\"ultimate\" data-level=\"{n_lvl}\">
  <defs>
    <radialGradient id=\"st-core-{sid}\" cx=\"50%\" cy=\"50%\" r=\"50%\">
      <stop offset=\"0%\" stop-color=\"#fde2a4\" stop-opacity=\"1\"/>
      <stop offset=\"55%\" stop-color=\"{AMBER_STAR}\" stop-opacity=\"0.95\"/>
      <stop offset=\"100%\" stop-color=\"{AMBER_STAR}\" stop-opacity=\"0\"/>
    </radialGradient>
  </defs>

  {_shared_frame('Ultimate Skill')}

  <!-- Two concentric orbital tracks -->
  {orbits}

  <!-- Companion dots on the orbits -->
  {dots_svg}

  <!-- Main-sequence disc -->
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{disc_r + 30}\" fill=\"url(#st-core-{sid})\"/>
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{disc_r}\" fill=\"{AMBER_STAR}\"/>

  <!-- Bayer designation (catalogue prefix) -->
  <text x=\"{slug_x}\" y=\"{bayer_y}\" font-family=\"'Departure Mono','JetBrains Mono',ui-monospace,monospace\"
    font-size=\"28\" letter-spacing=\"4.4\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.7\">α</text>

  <!-- Slash-skill slug -->
  <text x=\"{slug_x}\" y=\"{slug_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-weight=\"600\"
    font-size=\"{slug_size}\" fill=\"{CREAM_ENGRAVED}\" dominant-baseline=\"middle\">/{slug}</text>

  <!-- Title kicker -->
  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">'{title}'</text>

  <!-- Discoverer signature -->
  {_catalog_signature(contributor, is_origin, year)}

  <!-- Marginal magnitude band -->
  {_magnitude_band('5.0', 'CLASS A', stars_word, designation)}
</svg>
"""


# ─── Plate IV · SINGULARITY ───────────────────────────────────────────────────

def build_singularity_plate(skill: dict) -> str:
    """Plate IV — black hole.

    Composition: a slightly-darker disc (pure negative space) ringed by a
    thin violet accretion hairline. Four stellar-field dots scattered
    nearby; two of them displaced toward the void to render gravitational
    lensing. The marginal magnitude band reads `MAG ∞` — a black hole
    has mass but no luminosity. The star-count cell is replaced by a word
    (`HARDENED`, `EVOLVED`, etc.) because there are no stars to count when
    there's no light.
    """
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "4★"))
    sid = (skill.get("id") or "unknown").replace("/", "-").replace(" ", "-")

    # Black hole sits left-of-centre. Slug right.
    cx, cy = 360, 290
    void_r = 80
    ring_r_outer = 96
    ring_r_inner = 90

    # Lensing-displaced stellar field — 4 dots, 2 leaning toward the void.
    # Original positions vs. lensed positions (the displacement IS the joke).
    field_dots = []
    lensed_pairs = [
        # (x, y, displaced_x, displaced_y, opacity, is_lensed)
        (180, 200, 195, 215, 0.55, True),    # leans toward void
        (560, 200, 560, 200, 0.50, False),   # untouched, off to the right
        (560, 380, 545, 365, 0.55, True),    # leans toward void
        (180, 400, 180, 400, 0.45, False),   # untouched, lower-left
        (300, 130, 300, 130, 0.40, False),
    ]
    for ox, oy, dx, dy, op, is_lensed in lensed_pairs:
        field_dots.append(
            f'<circle cx="{dx}" cy="{dy}" r="1.6" fill="{CREAM_ENGRAVED}" fill-opacity="{op}"/>'
        )
        if is_lensed:
            # Faint streak from original to displaced position — reads as the
            # lensing path. Cream at very low alpha so it doesn't shout.
            field_dots.append(
                f'<line x1="{ox}" y1="{oy}" x2="{dx}" y2="{dy}" stroke="{CREAM_ENGRAVED}" '
                f'stroke-opacity="0.12" stroke-width="0.6"/>'
            )
    field_svg = "\n  ".join(field_dots)

    # Slug — right side.
    slug_x = 640
    slug_w = OG_W - slug_x - MARGIN
    slug_size = autoscale_font(slug_raw, default_px=84, available_w=slug_w)
    slug_y = 286

    bh_prefix_y = slug_y - 64
    kicker_y = slug_y + 50

    # Rank word (replaces the star-count cell on the magnitude band).
    rank_words = {
        2: "NAMED",
        3: "EVOLVED",
        4: "HARDENED",
        5: "TRANSCENDENT",
        6: "TRANSCENDENT ★",
    }
    rank_word = rank_words.get(n_lvl, "AWAITED")
    designation = f"BH {to_roman(max(1, n_lvl))} · {year}"

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\"
  width=\"{OG_W}\" height=\"{OG_H}\" viewBox=\"0 0 {OG_W} {OG_H}\"
  class=\"plate plate--singularity\" data-plate=\"IV\" data-type=\"unique\" data-level=\"{n_lvl}\">
  <defs>
    <radialGradient id=\"bh-void-{sid}\" cx=\"50%\" cy=\"50%\" r=\"50%\">
      <stop offset=\"0%\" stop-color=\"#050410\" stop-opacity=\"1\"/>
      <stop offset=\"85%\" stop-color=\"#050410\" stop-opacity=\"1\"/>
      <stop offset=\"100%\" stop-color=\"{INK_NIGHT}\" stop-opacity=\"1\"/>
    </radialGradient>
  </defs>

  {_shared_frame('Unique Skill')}

  <!-- Lensing-displaced stellar field -->
  {field_svg}

  <!-- Accretion-disk hairline ring (thin violet) -->
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{ring_r_outer}\" fill=\"none\" stroke=\"{VIOLET_HALO}\"
    stroke-opacity=\"0.85\" stroke-width=\"1.4\"/>
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{(ring_r_outer + ring_r_inner) / 2}\" fill=\"none\"
    stroke=\"{VIOLET_HALO}\" stroke-opacity=\"0.35\" stroke-width=\"0.6\"/>

  <!-- The void itself: same colour as the page, slightly darker, no glyph -->
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{void_r}\" fill=\"url(#bh-void-{sid})\"/>

  <!-- BH designation (catalogue prefix) -->
  <text x=\"{slug_x}\" y=\"{bh_prefix_y}\" font-family=\"'Departure Mono','JetBrains Mono',ui-monospace,monospace\"
    font-size=\"28\" letter-spacing=\"4.4\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.7\">BH-</text>

  <!-- Slash-skill slug -->
  <text x=\"{slug_x}\" y=\"{slug_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-weight=\"600\"
    font-size=\"{slug_size}\" fill=\"{CREAM_ENGRAVED}\" dominant-baseline=\"middle\">/{slug}</text>

  <!-- Title kicker -->
  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">'{title}'</text>

  <!-- Discoverer signature -->
  {_catalog_signature(contributor, is_origin, year)}

  <!-- Marginal magnitude band — MAG ∞ -->
  {_magnitude_band('∞', 'CLASS A', f'⊘ {rank_word}', designation)}
</svg>
"""


# ─── Default fallback (basic / extra) ─────────────────────────────────────────

def build_default_plate(skill: dict) -> str:
    """Minimal atlas plate for basic / extra skills.

    These tiers are NOT promoted to the Atlas — the plate exists only to
    satisfy the cron generator pipeline so it never crashes on a sub-4★
    skill. Same atlas grammar; no celestial subject; just slug, kicker,
    signature, and magnitude band. The marginal star count is `· · ·` — the
    skill has not yet been catalogued as a celestial body.
    """
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "2★"))
    tier_type = resolve_type_for_og(skill)
    plate_label = "Extra Skill" if tier_type == "extra" else "Basic Skill"
    plate_css_val = plate_label.lower().replace(" ", "-")

    slug_x = MARGIN + 12
    slug_w = OG_W - slug_x - MARGIN
    slug_size = autoscale_font(slug_raw, default_px=72, available_w=slug_w)
    slug_y = 290
    kicker_y = slug_y + 46

    stars = "★" * max(1, min(6, n_lvl))
    designation = f"GAIA · {year}"
    mag_value = f"{n_lvl}.0" if n_lvl > 0 else "·"

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\"
  width=\"{OG_W}\" height=\"{OG_H}\" viewBox=\"0 0 {OG_W} {OG_H}\"
  class=\"plate plate--default\" data-plate=\"{plate_css_val}\" data-level=\"{n_lvl}\">
  {_shared_frame(plate_label)}

  <!-- Slash-skill slug (no celestial subject for sub-4★ skills) -->
  <text x=\"{slug_x}\" y=\"{slug_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-weight=\"600\"
    font-size=\"{slug_size}\" fill=\"{CREAM_ENGRAVED}\" dominant-baseline=\"middle\">/{slug}</text>

  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">'{title}'</text>

  {_catalog_signature(contributor, is_origin, year)}

  {_magnitude_band(mag_value, evidence_class(skill.get('level', '')), stars, designation)}
</svg>
"""


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def build_og_svg(skill: dict) -> str:
    """Pick the right Hall Plate based on tier + rank.

    - level 6★                         → Apex Supernova (Plate VI)
    - type=ultimate, level <6            → Stellar (Plate V)
    - type=unique                        → Singularity (Plate IV)
    - everything else (basic / extra)    → default fallback
    """
    level = skill.get("level", "")
    n_lvl = level_num(level)
    tier_type = resolve_type_for_og(skill)

    if n_lvl >= 6:
        return build_supernova_plate(skill)
    if tier_type == "ultimate":
        return build_stellar_plate(skill)
    if tier_type == "unique":
        return build_singularity_plate(skill)
    return build_default_plate(skill)


# ─── Raster fallback (optional cairosvg / wand pipeline) ──────────────────────

def try_render_png(svg_content: str, out_path: Path) -> bool:
    """Try to render SVG to PNG using cairosvg or pillow. Returns True on success."""
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


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def load_named_data(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_all_skills(data: dict) -> list:
    skills = []
    for bucket_skills in data.get("buckets", {}).values():
        skills.extend(bucket_skills)
    return skills


def generate_og_cards(named_path: Path, out_dir: Path) -> int:
    """Generate Hall Plate SVGs (and PNGs if possible). Returns total count."""
    data = load_named_data(named_path)
    skills = collect_all_skills(data)

    if not skills:
        print("No named skills found — no plates generated.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    svg_count = 0
    png_count = 0

    for skill in skills:
        handle = skill.get("contributor", "")
        skill_id_full = skill.get("id", "")
        if not handle or not skill_id_full:
            continue

        skill_slug = skill_id_full.split("/")[-1]

        handle_dir = out_dir / handle
        handle_dir.mkdir(parents=True, exist_ok=True)

        svg_path = handle_dir / f"{skill_slug}.svg"
        svg_content = build_og_svg(skill)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        svg_count += 1

        png_path = handle_dir / f"{skill_slug}.png"
        if try_render_png(svg_content, png_path):
            png_count += 1
            print(f"  SVG+PNG: docs/og/{handle}/{skill_slug}.{{svg,png}}")
        else:
            print(f"  SVG:     docs/og/{handle}/{skill_slug}.svg")

    print(f"\nGenerated {svg_count} SVG plate(s), {png_count} PNG render(s).")
    if png_count == 0:
        print(
            "  Note: Install cairosvg (`pip install cairosvg`) to enable PNG rendering."
        )
    return svg_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Hall Plate share cards from named-skills.json"
    )
    parser.add_argument("--named", default=str(NAMED_JSON),
                        help="Path to named-skills.json (default: registry/named-skills.json)")
    parser.add_argument("--out-dir", default=str(OUT_DIR),
                        help="Output directory for plates (default: docs/og/)")
    args = parser.parse_args()

    named_path = Path(args.named)
    out_dir = Path(args.out_dir)

    print(f"Loading named skills from: {named_path}")
    generate_og_cards(named_path, out_dir)


if __name__ == "__main__":
    main()
