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

    Floor raised to 56px because the SVG is now demoted to og:image only —
    standalone viewers (file://) lose the EB Garamond webfont and fall back
    to Times Roman, which renders ~30% wider per glyph. Anything below 56px
    is unreadable in social previews; anything above starts to overflow.
    """
    if not text:
        return default_px
    needed = len(text) * default_px * avg_glyph_ratio
    if needed <= available_w:
        return default_px
    return max(56, int(default_px * available_w / needed))


def _slug_text_block(slug_raw: str, slug_x: float, slug_y_baseline: float,
                     available_w: float, default_px: int = 80) -> dict:
    """Render the slash-skill slug as <text>, with optional <tspan> line break.

    Long slugs (>22 chars) are split on the last hyphen at-or-below the 22-char
    boundary and rendered as two <tspan> lines so the slug never runs off the
    right margin even when the EB Garamond webfont fails to load.

    Returns:
      { "svg": "<text …>", "kicker_y": <int> } — kicker_y already accounts for
      the second line of the slug if the slug wrapped, so the title kicker
      below the slug doesn't collide with the wrapped second line.
    """
    slug = html.escape(slug_raw)
    if len(slug_raw) <= 22:
        size = autoscale_font(slug_raw, default_px=default_px, available_w=available_w)
        svg = (
            f'<text x="{slug_x}" y="{slug_y_baseline}" font-family="\'EB Garamond\',Georgia,serif" '
            f'font-weight="600" font-size="{size}" fill="{CREAM_ENGRAVED}" '
            f'dominant-baseline="middle">/{slug}</text>'
        )
        return {"svg": svg, "kicker_y": int(slug_y_baseline + 50)}

    # Long slug — split on the last hyphen at-or-below position 22.
    cutoff = slug_raw.rfind("-", 0, 23)
    if cutoff == -1:
        # No hyphen in the first 22 chars — hard split at 22.
        cutoff = 22
        first = slug_raw[:cutoff]
        second = slug_raw[cutoff:]
    else:
        first = slug_raw[:cutoff]
        second = slug_raw[cutoff + 1:]  # drop the hyphen at the break

    first_e = html.escape(first)
    second_e = html.escape(second)
    longest = max(len(first), len(second) + 1)  # +1 to model the trailing hyphen
    size = autoscale_font("x" * longest, default_px=default_px, available_w=available_w)
    line_dy = int(size * 0.92)
    # Shift the slug up so the two lines stay vertically centred on slug_y_baseline.
    top_y = int(slug_y_baseline - line_dy / 2)
    svg = (
        f'<text x="{slug_x}" y="{top_y}" font-family="\'EB Garamond\',Georgia,serif" '
        f'font-weight="600" font-size="{size}" fill="{CREAM_ENGRAVED}" '
        f'dominant-baseline="middle">'
        f'<tspan x="{slug_x}">/{first_e}-</tspan>'
        f'<tspan x="{slug_x}" dy="{line_dy}">{second_e}</tspan>'
        f'</text>'
    )
    return {"svg": svg, "kicker_y": int(slug_y_baseline + line_dy / 2 + 50)}


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


def _plate_number(roman: str) -> str:
    """Top-right roman-numeral plate number, mono caps tracked +0.18em."""
    return (
        f'<text x="{OG_W - MARGIN}" y="{PLATE_NO_Y}" '
        f'font-family="\'Departure Mono\',\'JetBrains Mono\',ui-monospace,monospace" '
        f'font-size="18" letter-spacing="3.2" fill="{CREAM_ENGRAVED}" fill-opacity="0.7" '
        f'text-anchor="end" dominant-baseline="middle">PLATE {html.escape(roman)}</text>'
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

    Atlas convention: the literal word “Cataloged”, then the @handle, then —
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


def _shared_frame(plate_roman: str) -> str:
    """The four pieces every plate shares: ground, RA/Dec ticks, plate number,
    engraved rule. Caller is responsible for the magnitude band + signature
    (because their text varies per plate)."""
    return (
        f'<rect width="{OG_W}" height="{OG_H}" fill="{INK_NIGHT}"/>\n'
        + _radec_ticks() + "\n"
        + _plate_number(plate_roman) + "\n"
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
    slug_inner = _slug_text_block(slug_raw, slug_x, slug_y_baseline=286,
                                  available_w=slug_w, default_px=84)
    kicker_y = slug_inner["kicker_y"]
    sn_prefix_y = 222

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

  {_shared_frame('VI')}

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
  <text x=\"{slug_x}\" y=\"{sn_prefix_y}\" font-family=\"'Departure Mono','JetBrains Mono',ui-monospace,monospace\"
    font-size=\"28\" letter-spacing=\"4.4\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.7\">SN</text>

  <!-- Slash-skill slug (catalogue designation) -->
  {slug_inner["svg"]}

  <!-- Title kicker -->
  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">‘{title}’</text>

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
    slug_inner = _slug_text_block(slug_raw, slug_x, slug_y_baseline=268,
                                  available_w=slug_w, default_px=76)

    # Bayer prefix sits ABOVE the slug.
    bayer_y = 200
    kicker_y = slug_inner["kicker_y"]

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

  {_shared_frame('V')}

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
  {slug_inner["svg"]}

  <!-- Title kicker -->
  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">‘{title}’</text>

  <!-- Discoverer signature -->
  {_catalog_signature(contributor, is_origin, year)}

  <!-- Marginal magnitude band -->
  {_magnitude_band('5.0', 'CLASS A', stars_word, designation)}
</svg>
"""


# ─── Plate IV · SINGULARITY ───────────────────────────────────────────────────

def build_singularity_plate(skill: dict) -> str:
    """Plate IV — black hole, with real identity (Sgr A* / M87 visual register).

    Composition (post-pivot upgrade):
      - True-black radial-gradient void (#000 at center → INK_NIGHT at edge),
        visibly darker than the surrounding sky.
      - Photon sphere: thin cream ring at 1.5× the event horizon — the
        gravitational lensing of light passing behind the BH that gives Sgr A*
        and M87 their iconic silhouette.
      - Three concentric accretion disks rendered as rotated ellipses
        (rotate(-12deg) scaleY(0.22)) so they read as a tilted disk seen at an
        angle, not flat rings. Each disk has a Doppler-asymmetric brightness
        gradient — the approaching (top) side is brighter than the receding
        (bottom) side, modelled as two halves with different fill opacities.
      - Hot spot: a tiny localized brightening on the approaching side, like
        the orbital knot in Sgr A* time-lapse imaging.
      - 8 lensing-displaced field dots; 4 of them bent visibly toward the void
        with faint streak lines so the lensing tic reads at first glance.

    The marginal magnitude band reads `MAG ∞`; the star-count cell is replaced
    by a word (HARDENED / TRANSCENDENT) because a black hole has mass but no
    luminosity to count.
    """
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "4★"))
    sid = (skill.get("id") or "unknown").replace("/", "-").replace(" ", "-")

    # Black hole sits left-of-centre. Slug right.
    cx, cy = 360, 290
    void_r = 64                   # event horizon (the dark disc)
    photon_r = int(void_r * 1.5)  # photon sphere — iconic 1.5× radius

    # Three concentric accretion disks. Outer → inner radii on the major axis.
    disk_radii = [126, 108, 92]

    # Lensing-displaced stellar field — 8 dots, 4 leaning toward the void.
    # (orig_x, orig_y, displaced_x, displaced_y, opacity, is_lensed)
    lensed_pairs = [
        (170, 180, 198, 212, 0.60, True),    # upper-left, strong lensing
        (180, 410, 205, 388, 0.55, True),    # lower-left, strong lensing
        (560, 200, 560, 200, 0.50, False),   # untouched far-right
        (560, 380, 547, 360, 0.55, True),    # right, mild lensing
        (255, 130, 263, 148, 0.45, True),    # top, mild lensing
        (140, 280, 140, 280, 0.45, False),   # far-left untouched
        (470, 130, 470, 130, 0.40, False),   # upper-right untouched
        (300, 460, 300, 460, 0.40, False),   # lower-centre untouched
    ]
    field_dots = []
    for ox, oy, dx, dy, op, is_lensed in lensed_pairs:
        field_dots.append(
            f'<circle cx="{dx}" cy="{dy}" r="1.6" fill="{CREAM_ENGRAVED}" fill-opacity="{op}"/>'
        )
        if is_lensed:
            field_dots.append(
                f'<line x1="{ox}" y1="{oy}" x2="{dx}" y2="{dy}" stroke="{CREAM_ENGRAVED}" '
                f'stroke-opacity="0.16" stroke-width="0.6"/>'
            )
    field_svg = "\n  ".join(field_dots)

    # Build the three accretion disks with Doppler-asymmetric gradients.
    # Each disk = one ellipse for the approaching (top) half (brighter) +
    # one ellipse for the receding (bottom) half (dimmer), clipped via two
    # half-rectangle clip paths. The whole stack is tilted -12°.
    disk_alphas = [
        # (top_alpha, bottom_alpha) — outer dim, middle bright, inner brightest
        (0.42, 0.18),  # outer
        (0.62, 0.22),  # middle
        (0.85, 0.30),  # inner
    ]
    disks = []
    for i, r in enumerate(disk_radii):
        ry = max(6, int(r * 0.22))
        top_a, bot_a = disk_alphas[i]
        disks.append(
            f'<g clip-path="url(#bh-top-{sid})">'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{ry}" '
            f'fill="url(#bh-disk-top-{sid})" fill-opacity="{top_a}"/>'
            f'</g>'
            f'<g clip-path="url(#bh-bot-{sid})">'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{ry}" '
            f'fill="url(#bh-disk-bot-{sid})" fill-opacity="{bot_a}"/>'
            f'</g>'
        )
    disks_svg = "\n    ".join(disks)

    # Slug — right side. Conservative size + tspan line break for long slugs.
    slug_x = 640
    slug_w = OG_W - slug_x - MARGIN
    slug_inner = _slug_text_block(slug_raw, slug_x, slug_y_baseline=286,
                                  available_w=slug_w, default_px=72)

    bh_prefix_y = 222
    kicker_y = slug_inner["kicker_y"]

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
    <!-- True-black void: deeper than the surrounding sky -->
    <radialGradient id=\"bh-void-{sid}\" cx=\"50%\" cy=\"50%\" r=\"50%\">
      <stop offset=\"0%\" stop-color=\"#000000\" stop-opacity=\"1\"/>
      <stop offset=\"82%\" stop-color=\"#020108\" stop-opacity=\"1\"/>
      <stop offset=\"100%\" stop-color=\"{INK_NIGHT}\" stop-opacity=\"1\"/>
    </radialGradient>
    <!-- Approaching (top) half of the disk — bright violet → white knot -->
    <linearGradient id=\"bh-disk-top-{sid}\" x1=\"0%\" y1=\"50%\" x2=\"100%\" y2=\"50%\">
      <stop offset=\"0%\" stop-color=\"{VIOLET_HALO}\" stop-opacity=\"0.55\"/>
      <stop offset=\"45%\" stop-color=\"#d8b4fe\" stop-opacity=\"0.95\"/>
      <stop offset=\"58%\" stop-color=\"#ffffff\" stop-opacity=\"1\"/>
      <stop offset=\"75%\" stop-color=\"#d8b4fe\" stop-opacity=\"0.85\"/>
      <stop offset=\"100%\" stop-color=\"{VIOLET_HALO}\" stop-opacity=\"0.45\"/>
    </linearGradient>
    <!-- Receding (bottom) half — dimmer violet only -->
    <linearGradient id=\"bh-disk-bot-{sid}\" x1=\"0%\" y1=\"50%\" x2=\"100%\" y2=\"50%\">
      <stop offset=\"0%\" stop-color=\"{VIOLET_HALO}\" stop-opacity=\"0.30\"/>
      <stop offset=\"50%\" stop-color=\"{VIOLET_HALO}\" stop-opacity=\"0.55\"/>
      <stop offset=\"100%\" stop-color=\"{VIOLET_HALO}\" stop-opacity=\"0.30\"/>
    </linearGradient>
    <!-- Top/bottom halves clipped relative to the (untilted) disk centre.    -->
    <!-- The whole disk group is then rotated -12deg around (cx,cy).          -->
    <clipPath id=\"bh-top-{sid}\">
      <rect x=\"{cx - 200}\" y=\"{cy - 200}\" width=\"400\" height=\"200\"/>
    </clipPath>
    <clipPath id=\"bh-bot-{sid}\">
      <rect x=\"{cx - 200}\" y=\"{cy}\" width=\"400\" height=\"200\"/>
    </clipPath>
    <!-- Approaching-side hot spot — small localized brightening -->
    <radialGradient id=\"bh-hotspot-{sid}\" cx=\"50%\" cy=\"50%\" r=\"50%\">
      <stop offset=\"0%\" stop-color=\"#ffffff\" stop-opacity=\"1\"/>
      <stop offset=\"55%\" stop-color=\"#e9d5ff\" stop-opacity=\"0.75\"/>
      <stop offset=\"100%\" stop-color=\"{VIOLET_HALO}\" stop-opacity=\"0\"/>
    </radialGradient>
  </defs>

  {_shared_frame('IV')}

  <!-- Lensing-displaced stellar field -->
  {field_svg}

  <!-- Tilted accretion disks (rotated -12° around the BH centre).             -->
  <!-- Outer to inner: dim → bright. Top halves are Doppler-boosted; bottom    -->
  <!-- halves render with the muted gradient.                                  -->
  <g transform=\"rotate(-12 {cx} {cy})\">
    {disks_svg}
    <!-- Hot spot on the approaching (top-left) side of the inner disk -->
    <ellipse cx=\"{cx - 58}\" cy=\"{cy - 6}\" rx=\"22\" ry=\"7\" fill=\"url(#bh-hotspot-{sid})\"/>
  </g>

  <!-- Photon sphere ring — thin cream, 1.5× the event horizon -->
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{photon_r}\" fill=\"none\" stroke=\"{CREAM_ENGRAVED}\"
    stroke-opacity=\"0.55\" stroke-width=\"0.9\"/>

  <!-- The void itself: true-black radial gradient, no glyph -->
  <circle cx=\"{cx}\" cy=\"{cy}\" r=\"{void_r}\" fill=\"url(#bh-void-{sid})\"/>

  <!-- BH designation (catalogue prefix) -->
  <text x=\"{slug_x}\" y=\"{bh_prefix_y}\" font-family=\"'Departure Mono','JetBrains Mono',ui-monospace,monospace\"
    font-size=\"28\" letter-spacing=\"4.4\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.7\">BH-</text>

  <!-- Slash-skill slug (with optional <tspan> line break for long slugs) -->
  {slug_inner["svg"]}

  <!-- Title kicker -->
  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">‘{title}’</text>

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
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "2★"))
    plate_roman = to_roman(max(1, min(3, n_lvl - 1))) or "I"

    slug_x = MARGIN + 12
    slug_w = OG_W - slug_x - MARGIN
    slug_inner = _slug_text_block(slug_raw, slug_x, slug_y_baseline=290,
                                  available_w=slug_w, default_px=68)
    kicker_y = slug_inner["kicker_y"]

    stars = ("★" * max(1, min(3, n_lvl))) + ("☆" * max(0, 3 - n_lvl))
    designation = f"GAIA · {plate_roman} · {year}"
    mag_value = f"{n_lvl}.0" if n_lvl > 0 else "·"

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\"
  width=\"{OG_W}\" height=\"{OG_H}\" viewBox=\"0 0 {OG_W} {OG_H}\"
  class=\"plate plate--default\" data-plate=\"{plate_roman}\" data-level=\"{n_lvl}\">
  {_shared_frame(plate_roman)}

  <!-- Slash-skill slug (no celestial subject for sub-4★ skills) -->
  {slug_inner["svg"]}

  <text x=\"{slug_x}\" y=\"{kicker_y}\" font-family=\"'EB Garamond',Georgia,serif\" font-style=\"italic\"
    font-size=\"24\" fill=\"{CREAM_ENGRAVED}\" fill-opacity=\"0.6\" dominant-baseline=\"middle\">‘{title}’</text>

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


# ═══════════════════════════════════════════════════════════════════════════════
# HTML Plates — canonical experience (post-pivot)
# ═══════════════════════════════════════════════════════════════════════════════
#
# The HTML plate is the canonical artifact: it reflows via CSS grid + clamp()
# so the slug fits regardless of length, it carries the EB Garamond webfont via
# Google Fonts CDN so standalone-opened files look correct, and it embeds the
# celestial subject as inline SVG inside the document so a single .html file
# is fully self-contained (download → double-click → identical render).
#
# The SVG plate (above) survives in a vestigial role purely for og:image —
# Twitter / Open Graph crawlers can't read HTML for og:image, so we keep
# generating a raster-friendly .svg sibling.
# ═══════════════════════════════════════════════════════════════════════════════


def _html_googlefonts_link() -> str:
    """The single Google Fonts <link> tag every HTML plate carries."""
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n  '
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n  '
        '<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400'
        '&family=Departure+Mono&display=swap" rel="stylesheet">'
    )


def _html_base_css() -> str:
    """Shared CSS for every HTML plate.

    Inlined into every emitted .html file so a downloaded plate is fully
    self-contained — no network dependency beyond the Google Fonts link.

    Layout strategy: the .plate is a CSS grid with three rows
    (chrome / stage / footer) locked to 1200×630 inside the modal stage but
    fluid via aspect-ratio: 1200/630 + width: min(100vw, 1200px) when
    opened standalone in a browser. The slug uses clamp(40px, 6vw, 88px)
    so reflow handles every length without a Python autoscale guess.
    """
    return f"""
    :root {{
      --ink-night: {INK_NIGHT};
      --cream: {CREAM_ENGRAVED};
      --honor: {HONOR_RED};
      --apex-gold: {APEX_GOLD};
      --amber-star: {AMBER_STAR};
      --violet-halo: {VIOLET_HALO};
    }}
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: #050414; }}
    body {{
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: 'EB Garamond', Georgia, serif;
      color: var(--cream);
    }}
    .plate {{
      width: min(100vw, 1200px);
      aspect-ratio: 1200 / 630;
      background: var(--ink-night);
      color: var(--cream);
      display: grid;
      grid-template-rows: 56px 1fr 96px;
      padding: 24px 48px;
      gap: 0;
      position: relative;
      overflow: hidden;
      font-family: 'EB Garamond', Georgia, serif;
    }}
    .plate__chrome--top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      letter-spacing: 1.6px;
      font-family: 'Departure Mono', ui-monospace, monospace;
      font-size: clamp(9px, 0.9vw, 11px);
      color: var(--cream);
      opacity: 0.42;
    }}
    .plate__plate-no {{
      letter-spacing: 3.2px;
      opacity: 0.92;
      font-size: clamp(13px, 1.5vw, 18px);
    }}
    .plate__stage {{
      position: relative;
      display: grid;
      grid-template-columns: 1fr 1fr;
      align-items: center;
      gap: 32px;
      padding: 8px 0;
    }}
    .plate__designation {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;  /* let the slug clamp without overflowing */
    }}
    .plate__prefix {{
      font-family: 'Departure Mono', ui-monospace, monospace;
      font-size: clamp(18px, 2.2vw, 28px);
      letter-spacing: 4.4px;
      opacity: 0.7;
    }}
    .plate__slug {{
      font-family: 'EB Garamond', Georgia, serif;
      font-weight: 600;
      font-size: clamp(40px, 6vw, 88px);
      line-height: 0.96;
      margin: 0;
      color: var(--cream);
      overflow-wrap: anywhere;
      hyphens: auto;
    }}
    .plate__kicker {{
      font-family: 'EB Garamond', Georgia, serif;
      font-style: italic;
      font-size: clamp(15px, 1.7vw, 22px);
      opacity: 0.6;
      margin-top: 6px;
    }}
    .plate__subject {{
      width: 100%;
      height: 100%;
      max-height: 380px;
      display: block;
    }}
    .plate__footer {{
      display: flex;
      flex-direction: column;
      gap: 14px;
      justify-content: flex-end;
    }}
    .plate__signature {{
      font-family: 'EB Garamond', Georgia, serif;
      font-style: italic;
      font-size: clamp(15px, 1.7vw, 22px);
      color: var(--honor);
      letter-spacing: 0.2px;
    }}
    .plate__signature .plate__cataloged {{ font-style: normal; opacity: 0.82; }}
    .plate__signature .plate__handle {{ font-style: normal; font-weight: 600; }}
    .plate__signature .plate__origin {{
      font-style: normal;
      letter-spacing: 2.2px;
      font-size: clamp(12px, 1.4vw, 18px);
      opacity: 0.9;
      padding: 0 8px;
    }}
    .plate__signature .plate__sep {{ opacity: 0.5; padding: 0 6px; }}
    .plate__signature .plate__year {{ font-style: normal; opacity: 0.7; }}
    .plate__rule {{
      border: 0;
      height: 1px;
      width: 100%;
      background: var(--cream);
      opacity: 0.35;
      margin: 0;
    }}
    .plate__band {{
      font-family: 'Departure Mono', ui-monospace, monospace;
      font-size: clamp(10px, 1.1vw, 13px);
      letter-spacing: 1.5px;
      color: var(--cream);
      opacity: 0.7;
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
    }}
    .plate__band .plate__band-sep {{ opacity: 0.4; letter-spacing: 1px; }}
    .plate__seal {{
      position: absolute;
      top: 24px;
      left: 48px;
      width: 30px;
      height: 30px;
    }}
    /* ─── Plate VI · APEX SUPERNOVA ─── */
    .plate--apex .plate__slug {{ color: var(--cream); }}
    /* ─── Plate V · STELLAR ─── */
    .plate--stellar .plate__designation {{ order: 0; }}
    .plate--stellar .plate__subject-wrap {{ order: 1; }}
    /* ─── Plate IV · SINGULARITY ─── */
    .plate--singularity {{ }}
    /* ─── Default fallback ─── */
    .plate--default .plate__stage {{ grid-template-columns: 1fr; }}

    @media (max-aspect-ratio: 16/10) {{
      .plate__seal {{ display: none; }}
    }}
    """


def _html_chrome(plate_roman: str) -> str:
    """Top-of-plate RA/Dec ticks + roman-numeral plate number."""
    labels = ["+20°", "+10°", "0°", "−10°", "−20°"]
    ticks = " &nbsp;·&nbsp; ".join(html.escape(l) for l in labels)
    return (
        f'<header class="plate__chrome--top">\n'
        f'    <div class="plate__radec">{ticks}</div>\n'
        f'    <div class="plate__plate-no">PLATE {html.escape(plate_roman)}</div>\n'
        f'  </header>'
    )


def _html_signature(contributor: str, is_origin: bool, year: str) -> str:
    """Honor-red discoverer signature (HTML version of _catalog_signature)."""
    handle = html.escape(contributor or "")
    origin_span = (
        '<span class="plate__origin">· ORIGIN ·</span>'
        if is_origin else
        '<span class="plate__sep">·</span>'
    )
    return (
        f'<div class="plate__signature">\n'
        f'      <span class="plate__cataloged">Cataloged by</span> '
        f'<span class="plate__handle">@{handle}</span>'
        f'{origin_span}'
        f'<span class="plate__year">{html.escape(year)}</span>\n'
        f'    </div>'
    )


def _html_band(magnitude: str, ev_class: str, stars_or_word: str, designation: str) -> str:
    """Marginal mono data band (HTML version of _magnitude_band)."""
    parts = [
        f'<span>MAG {html.escape(magnitude)}</span>',
        '<span class="plate__band-sep">···</span>',
        f'<span>{html.escape(ev_class)}</span>',
        '<span class="plate__band-sep">···</span>',
        f'<span>{html.escape(stars_or_word)}</span>',
        '<span class="plate__band-sep">···</span>',
        f'<span>{html.escape(designation)}</span>',
    ]
    return f'<div class="plate__band">\n      {"".join(parts)}\n    </div>'


def _html_footer(contributor: str, is_origin: bool, year: str,
                 magnitude: str, ev_class: str, stars_or_word: str, designation: str) -> str:
    """Bottom-of-plate signature + rule + magnitude band."""
    return (
        f'<footer class="plate__footer">\n'
        f'    {_html_signature(contributor, is_origin, year)}\n'
        f'    <hr class="plate__rule" />\n'
        f'    {_html_band(magnitude, ev_class, stars_or_word, designation)}\n'
        f'  </footer>'
    )


def _html_diamond_seal_svg() -> str:
    """Inline SVG of the Diamond Seal — Apex publisher's mark."""
    return (
        '<svg class="plate__seal" viewBox="0 0 64 64" aria-hidden="true">\n'
        '    <path d="M 32 4 L 60 32 L 32 60 L 4 32 Z" fill="none" '
        'stroke="var(--cream)" stroke-width="2.4" stroke-linejoin="miter" opacity="0.78"/>\n'
        '    <text x="32" y="34" font-family="\'EB Garamond\',Georgia,serif" font-weight="600" '
        'font-size="28" fill="var(--cream)" text-anchor="middle" dominant-baseline="central" '
        'opacity="0.8">G</text>\n'
        '  </svg>'
    )


def _html_doc_wrap(title_text: str, plate_class: str, plate_data_attrs: str,
                   chrome_html: str, stage_html: str, footer_html: str) -> str:
    """Wrap a plate's <article> body in a self-contained HTML document."""
    css = _html_base_css()
    fonts = _html_googlefonts_link()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title_text)} — Hall Plate · Gaia</title>
  {fonts}
  <style>{css}</style>
</head>
<body>
  <article class="plate {plate_class}" {plate_data_attrs}>
    {chrome_html}
    {stage_html}
    {footer_html}
  </article>
</body>
</html>
"""


# ─── Plate VI · APEX SUPERNOVA (HTML) ─────────────────────────────────────────

def build_supernova_html(skill: dict) -> str:
    """HTML version of Plate VI — supernova remnant."""
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "6★"))
    sid = (skill.get("id") or "unknown").replace("/", "-").replace(" ", "-")

    # Inline SVG of the supernova subject — same geometry as the SVG plate
    # but the parent <div> sizes it via CSS grid so it scales with the plate.
    cx, cy = 200, 175
    rays = []
    ray_lens = [150, 138, 158, 145, 132, 148]
    for i, length in enumerate(ray_lens):
        angle = -math.pi / 2 + i * (math.pi * 2 / 6)
        ex = cx + length * math.cos(angle)
        ey = cy + length * math.sin(angle)
        mx = (cx + ex) / 2 + 8 * math.cos(angle + math.pi / 2)
        my = (cy + ey) / 2 + 8 * math.sin(angle + math.pi / 2)
        rays.append(
            f'<path d="M {cx} {cy} Q {mx:.1f} {my:.1f} {ex:.1f} {ey:.1f}" '
            f'stroke="var(--apex-gold)" stroke-opacity="0.78" stroke-width="1.5" '
            f'stroke-linecap="round" fill="none"/>'
        )
    rays_svg = "\n      ".join(rays)
    field_dots = "\n      ".join(
        f'<circle cx="{fx}" cy="{fy}" r="1.4" fill="var(--cream)" fill-opacity="{op}"/>'
        for fx, fy, op in [
            (60, 110, 0.5), (340, 130, 0.45), (90, 230, 0.5),
            (320, 250, 0.55), (170, 60, 0.4), (290, 280, 0.4),
        ]
    )
    subject_svg = f"""<svg class="plate__subject" viewBox="0 0 400 350" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <radialGradient id="sn-core-{sid}" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#fff7d6" stop-opacity="1"/>
          <stop offset="40%" stop-color="var(--apex-gold)" stop-opacity="0.95"/>
          <stop offset="100%" stop-color="var(--apex-gold)" stop-opacity="0"/>
        </radialGradient>
      </defs>
      {field_dots}
      {rays_svg}
      <circle cx="{cx}" cy="{cy}" r="42" fill="url(#sn-core-{sid})"/>
      <circle cx="{cx}" cy="{cy}" r="9" fill="#fff7d6"/>
    </svg>"""

    stars_word = "★" * max(1, min(6, n_lvl))
    designation = f"α 6 OBS · {year}"
    stage_html = f"""<div class="plate__stage">
    <div class="plate__subject-wrap">
      {subject_svg}
    </div>
    <div class="plate__designation">
      <div class="plate__prefix">SN</div>
      <h1 class="plate__slug">/{slug}</h1>
      <div class="plate__kicker">‘{title}’</div>
    </div>
    {_html_diamond_seal_svg()}
  </div>"""
    return _html_doc_wrap(
        title_text=f"/{slug_raw}",
        plate_class="plate--apex",
        plate_data_attrs=f'data-plate="VI" data-type="ultimate" data-level="{n_lvl}"',
        chrome_html=_html_chrome("VI"),
        stage_html=stage_html,
        footer_html=_html_footer(contributor, is_origin, year,
                                 "6.0", "CLASS A", stars_word, designation),
    )


# ─── Plate V · STELLAR (HTML) ─────────────────────────────────────────────────

def build_stellar_html(skill: dict) -> str:
    """HTML version of Plate V — main-sequence star with two orbital tracks."""
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "5★"))
    sid = (skill.get("id") or "unknown").replace("/", "-").replace(" ", "-")

    cx, cy = 200, 175
    r1, r2 = 70, 120
    companions = [
        (r1, -math.pi / 6),
        (r1,  math.pi - math.pi / 8),
        (r2,  math.pi / 3),
        (r2, -math.pi + math.pi / 7),
    ]
    dots = "\n      ".join(
        f'<circle cx="{cx + r * math.cos(a):.1f}" cy="{cy + r * math.sin(a):.1f}" '
        f'r="3" fill="var(--cream)" fill-opacity="0.85"/>'
        for r, a in companions
    )
    subject_svg = f"""<svg class="plate__subject" viewBox="0 0 400 350" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <radialGradient id="st-core-{sid}" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#fde2a4" stop-opacity="1"/>
          <stop offset="55%" stop-color="var(--amber-star)" stop-opacity="0.95"/>
          <stop offset="100%" stop-color="var(--amber-star)" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <circle cx="{cx}" cy="{cy}" r="{r1}" fill="none" stroke="var(--cream)" stroke-opacity="0.45" stroke-width="1" stroke-dasharray="6 4"/>
      <circle cx="{cx}" cy="{cy}" r="{r2}" fill="none" stroke="var(--cream)" stroke-opacity="0.32" stroke-width="1" stroke-dasharray="8 6"/>
      {dots}
      <circle cx="{cx}" cy="{cy}" r="58" fill="url(#st-core-{sid})"/>
      <circle cx="{cx}" cy="{cy}" r="32" fill="var(--amber-star)"/>
    </svg>"""

    stars_word = "★" * max(1, min(6, n_lvl))
    designation = f"α {slug_raw[:18].upper()} · {year}"
    stage_html = f"""<div class="plate__stage">
    <div class="plate__designation">
      <div class="plate__prefix">α</div>
      <h1 class="plate__slug">/{slug}</h1>
      <div class="plate__kicker">‘{title}’</div>
    </div>
    <div class="plate__subject-wrap">
      {subject_svg}
    </div>
  </div>"""
    return _html_doc_wrap(
        title_text=f"/{slug_raw}",
        plate_class="plate--stellar",
        plate_data_attrs=f'data-plate="V" data-type="ultimate" data-level="{n_lvl}"',
        chrome_html=_html_chrome("V"),
        stage_html=stage_html,
        footer_html=_html_footer(contributor, is_origin, year,
                                 "5.0", "CLASS A", stars_word, designation),
    )


# ─── Plate IV · SINGULARITY (HTML) — the real black-hole identity ────────────

def build_singularity_html(skill: dict) -> str:
    """HTML version of Plate IV — black hole with full identity treatment.

    Photon sphere, three tilted accretion disks with Doppler asymmetry, hot
    spot on the approaching side, true-black void, 8 lensing-displaced field
    dots (4 visibly bent toward the void).
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

    cx, cy = 200, 175
    void_r = 38
    photon_r = int(void_r * 1.5)
    disk_radii = [82, 68, 56]
    disk_alphas = [(0.42, 0.18), (0.62, 0.22), (0.85, 0.30)]

    lensed_pairs = [
        (60, 70, 78, 90, 0.60, True),
        (60, 290, 80, 270, 0.55, True),
        (340, 80, 340, 80, 0.50, False),
        (340, 270, 322, 252, 0.55, True),
        (130, 35, 142, 50, 0.45, True),
        (40, 175, 40, 175, 0.45, False),
        (290, 35, 290, 35, 0.40, False),
        (175, 320, 175, 320, 0.40, False),
    ]
    field_parts = []
    for ox, oy, dx, dy, op, is_lensed in lensed_pairs:
        field_parts.append(
            f'<circle cx="{dx}" cy="{dy}" r="1.6" fill="var(--cream)" fill-opacity="{op}"/>'
        )
        if is_lensed:
            field_parts.append(
                f'<line x1="{ox}" y1="{oy}" x2="{dx}" y2="{dy}" stroke="var(--cream)" '
                f'stroke-opacity="0.18" stroke-width="0.6"/>'
            )
    field_dots = "\n      ".join(field_parts)

    # Three Doppler-asymmetric disks, each split into top / bottom halves via clip.
    disks = []
    for i, r in enumerate(disk_radii):
        ry = max(4, int(r * 0.22))
        top_a, bot_a = disk_alphas[i]
        disks.append(
            f'<g clip-path="url(#bh-h-top-{sid})">'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{ry}" '
            f'fill="url(#bh-h-disk-top-{sid})" fill-opacity="{top_a}"/>'
            f'</g>'
            f'<g clip-path="url(#bh-h-bot-{sid})">'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{ry}" '
            f'fill="url(#bh-h-disk-bot-{sid})" fill-opacity="{bot_a}"/>'
            f'</g>'
        )
    disks_svg = "\n        ".join(disks)

    subject_svg = f"""<svg class="plate__subject" viewBox="0 0 400 350" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <radialGradient id="bh-h-void-{sid}" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#000000" stop-opacity="1"/>
          <stop offset="82%" stop-color="#020108" stop-opacity="1"/>
          <stop offset="100%" stop-color="var(--ink-night)" stop-opacity="1"/>
        </radialGradient>
        <linearGradient id="bh-h-disk-top-{sid}" x1="0%" y1="50%" x2="100%" y2="50%">
          <stop offset="0%" stop-color="var(--violet-halo)" stop-opacity="0.55"/>
          <stop offset="45%" stop-color="#d8b4fe" stop-opacity="0.95"/>
          <stop offset="58%" stop-color="#ffffff" stop-opacity="1"/>
          <stop offset="75%" stop-color="#d8b4fe" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="var(--violet-halo)" stop-opacity="0.45"/>
        </linearGradient>
        <linearGradient id="bh-h-disk-bot-{sid}" x1="0%" y1="50%" x2="100%" y2="50%">
          <stop offset="0%" stop-color="var(--violet-halo)" stop-opacity="0.30"/>
          <stop offset="50%" stop-color="var(--violet-halo)" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="var(--violet-halo)" stop-opacity="0.30"/>
        </linearGradient>
        <clipPath id="bh-h-top-{sid}">
          <rect x="{cx - 130}" y="{cy - 130}" width="260" height="130"/>
        </clipPath>
        <clipPath id="bh-h-bot-{sid}">
          <rect x="{cx - 130}" y="{cy}" width="260" height="130"/>
        </clipPath>
        <radialGradient id="bh-h-hotspot-{sid}" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="1"/>
          <stop offset="55%" stop-color="#e9d5ff" stop-opacity="0.75"/>
          <stop offset="100%" stop-color="var(--violet-halo)" stop-opacity="0"/>
        </radialGradient>
      </defs>
      {field_dots}
      <g transform="rotate(-12 {cx} {cy})">
        {disks_svg}
        <ellipse cx="{cx - 38}" cy="{cy - 4}" rx="14" ry="5" fill="url(#bh-h-hotspot-{sid})"/>
      </g>
      <circle cx="{cx}" cy="{cy}" r="{photon_r}" fill="none" stroke="var(--cream)" stroke-opacity="0.55" stroke-width="0.9"/>
      <circle cx="{cx}" cy="{cy}" r="{void_r}" fill="url(#bh-h-void-{sid})"/>
    </svg>"""

    rank_words = {2: "NAMED", 3: "EVOLVED", 4: "HARDENED",
                  5: "TRANSCENDENT", 6: "TRANSCENDENT ★"}
    rank_word = rank_words.get(n_lvl, "AWAITED")
    designation = f"BH {to_roman(max(1, n_lvl))} · {year}"
    stage_html = f"""<div class="plate__stage">
    <div class="plate__subject-wrap">
      {subject_svg}
    </div>
    <div class="plate__designation">
      <div class="plate__prefix">BH-</div>
      <h1 class="plate__slug">/{slug}</h1>
      <div class="plate__kicker">‘{title}’</div>
    </div>
  </div>"""
    return _html_doc_wrap(
        title_text=f"/{slug_raw}",
        plate_class="plate--singularity",
        plate_data_attrs=f'data-plate="IV" data-type="unique" data-level="{n_lvl}"',
        chrome_html=_html_chrome("IV"),
        stage_html=stage_html,
        footer_html=_html_footer(contributor, is_origin, year,
                                 "∞", "CLASS A", f"⊘ {rank_word}", designation),
    )


# ─── Default fallback (HTML) ──────────────────────────────────────────────────

def build_default_html(skill: dict) -> str:
    """Minimal HTML plate for basic / extra skills.

    Same atlas grammar as the SVG default; no celestial subject. Reflows
    via clamp() so the slug always fits.
    """
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 64))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", "2★"))
    plate_roman = to_roman(max(1, min(3, n_lvl - 1))) or "I"

    stars = ("★" * max(1, min(3, n_lvl))) + ("☆" * max(0, 3 - n_lvl))
    designation = f"GAIA · {plate_roman} · {year}"
    mag_value = f"{n_lvl}.0" if n_lvl > 0 else "·"

    stage_html = f"""<div class="plate__stage">
    <div class="plate__designation" style="grid-column: 1 / -1; align-items: center; text-align: center;">
      <h1 class="plate__slug">/{slug}</h1>
      <div class="plate__kicker">‘{title}’</div>
    </div>
  </div>"""
    return _html_doc_wrap(
        title_text=f"/{slug_raw}",
        plate_class="plate--default",
        plate_data_attrs=f'data-plate="{plate_roman}" data-level="{n_lvl}"',
        chrome_html=_html_chrome(plate_roman),
        stage_html=stage_html,
        footer_html=_html_footer(contributor, is_origin, year,
                                 mag_value, evidence_class(skill.get("level", "")),
                                 stars, designation),
    )


# ─── HTML Dispatcher ──────────────────────────────────────────────────────────

def build_og_html(skill: dict) -> str:
    """Pick the right HTML Hall Plate based on tier + rank.

    Mirrors build_og_svg's routing: 6★ → Apex, ultimate <6 → Stellar,
    unique → Singularity, everything else → default.
    """
    level = skill.get("level", "")
    n_lvl = level_num(level)
    tier_type = resolve_type_for_og(skill)

    if n_lvl >= 6:
        return build_supernova_html(skill)
    if tier_type == "ultimate":
        return build_stellar_html(skill)
    if tier_type == "unique":
        return build_singularity_html(skill)
    return build_default_html(skill)


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
    """Generate Hall Plate HTML + SVG (and PNGs if possible). Returns total count.

    HTML is the canonical experience (modal + download); SVG is the og:image
    fallback consumed by Twitter / Open-Graph crawlers; PNG is rasterised from
    the SVG via cairosvg / wand when available.
    """
    data = load_named_data(named_path)
    skills = collect_all_skills(data)

    if not skills:
        print("No named skills found — no plates generated.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    html_count = 0
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

        # Canonical: HTML plate (reflows, self-contained, downloadable)
        html_path = handle_dir / f"{skill_slug}.html"
        html_content = build_og_html(skill)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        html_count += 1

        # og:image: SVG sibling (Twitter/Open-Graph crawlers can't read HTML)
        svg_path = handle_dir / f"{skill_slug}.svg"
        svg_content = build_og_svg(skill)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        svg_count += 1

        # Optional raster
        png_path = handle_dir / f"{skill_slug}.png"
        if try_render_png(svg_content, png_path):
            png_count += 1
            print(f"  HTML+SVG+PNG: docs/og/{handle}/{skill_slug}.{{html,svg,png}}")
        else:
            print(f"  HTML+SVG:     docs/og/{handle}/{skill_slug}.{{html,svg}}")

    print(f"\nGenerated {html_count} HTML, {svg_count} SVG, {png_count} PNG plate(s).")
    if png_count == 0:
        print(
            "  Note: Install cairosvg (`pip install cairosvg`) to enable PNG rendering."
        )
    return html_count


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
