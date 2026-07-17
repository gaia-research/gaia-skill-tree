#!/usr/bin/env python3
"""Gaia Skill Registry — Hall Plate (OG share card) Generator.

For each named skill, generates a Hall Plate at:
  docs/og/{handle}/{skillId}.svg   — SVG plate (always generated)
  docs/og/{handle}/{skillId}.png   — raster render (if cairosvg or pillow available)

The plates are rendered as entries in *Gaia's Celestial Atlas of Skills*: a
two-column engraved catalogue leaf. LEFT column carries the type — plate class,
slash-slug, discoverer's signature. RIGHT column carries the **subject**: the
skill's own Ascension-Overdrive V4 medallion, the exact stamp its rank and
branch earned elsewhere in the graph. One card, one cartographic style, one
authoritative subject.

  Class · APEX SUPERNOVA   (suite branch, 6★ — Apex)     → aov4-c6 medallion
  Class · STELLAR          (suite branch, 4-5★)          → aov4-c4/c5 medallion
  Class · SINGULARITY      (unique branch, 4-6★)         → aov4-d4/d5/d6 medallion
  Class · FIELD BODY       (standard branch, 1-3★)       → aov4-c1/c2/c3 medallion

The card composition, medallion asset, plate-class word, and rank label are ALL
driven by the read-time BRANCH (computeBranch) + star rank — NEVER by a stored
type/tier field (Ygg-II rubric E1). Every graded skill lands a proper plate;
no skill falls to a barren type-word fallback.

Reference grammar (Bode's Uranographia, Hevelius's Firmamentum):
  RA/Dec ticks at the top, plate-class number top-right, discoverer's signature
  in gold above an engraved rule, marginal magnitude band at the foot of every
  plate. The reader recognises the atlas; each plate is a unique entry within it.

All plates share one ground (`INK_NIGHT`, the printed night sky) and one
engraving colour (`CREAM_ENGRAVED`, warm cream linework + type). The single
chromatic event is the medallion, embedded as a same-origin relative image
(`/assets/ascension-overdrive/…-hero.webp`) so it renders when the SVG is
served from Pages, inlined into the share modal, or opened directly on-site.

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
sys.path.insert(0, str(REPO_ROOT / "src"))
from gaia_cli.redaction import REDACTED_HANDLE, is_redacted  # noqa: E402  single source of truth
from gaia_cli.trustMagnitude import computeBranch as _compute_branch  # noqa: E402  Ygg-II read-time branch
from gaia_cli.formatting import rank_word as _rank_word  # noqa: E402  branch-forked rank vocabulary
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
PLATE_NO_Y = 38            # baseline of the plate-class label

# ─── Two-column engraved-leaf geometry ────────────────────────────────────────
# The card is one catalogue leaf split into a type column (left) and a subject
# column (right). The medallion — the skill's own AOV4 stamp — fills the former
# dead zone on the right; the slug + signature keep the left. A hairline gutter
# rule separates them, echoing a real atlas plate's central fold.
COL_SPLIT_X = 720          # x of the vertical gutter rule between columns
MEDALLION_CX = 930         # centre-x of the medallion in the right column
MEDALLION_CY = 300         # centre-y of the medallion (optically above the rule)
MEDALLION_R = 206          # clip radius of the embedded medallion disc
# The AOV4 hero art is a 2048² image whose ornate ring disc spans ~77.7% of the
# frame, centred at (1024,1024). Placing the image at 2×MEDALLION_R/0.777 wide
# and offsetting so its centre lands on (MEDALLION_CX, MEDALLION_CY) fits the
# full ring inside the clip circle with the black corners cropped away.
_AOV_DISC_FRAC = 0.777

# ─── Atlas palette ────────────────────────────────────────────────────────────
# These two pigments are the entire ground+ink of every plate. They are SEALED
# to this generator — they do NOT propagate into tokens.css. The plates are a
# sub-surface inside the broader Gaia design system.
INK_NIGHT = "#0e0d20"          # OKLCH ~ oklch(13% 0.025 275); printed night-sky ground
CREAM_ENGRAVED = "#ebe5d4"     # OKLCH ~ oklch(92% 0.015  80); warm cream ink/linework

# ─── Brand voice tokens (resolved from DESIGN.md / styles.css) ────────────────
# Yggdrasil II rubric E4: the deprecated honor-red origin mark is replaced by
# gold. The discoverer's signature + `· ORIGIN ·` token now render in the same
# gold as the wreath / apex accent — no red anywhere.
SIGNATURE_GOLD = "#fbbf24"     # discoverer's signature + origin mark (was honor-red)
APEX_GOLD = "#fbbf24"          # suite plate-class accent + gutter tint (gold-leaning)
VIOLET_HALO = "#7c3aed"        # unique plate-class accent + gutter tint (darker register)
# E2/E7 contrast fix (Ygg-II W3c): VIOLET_HALO is ~3.1:1 on INK_NIGHT — fails WCAG AA.
# VIOLET_KICKER is the lighter text-safe violet used only for kicker/label fills;
# VIOLET_HALO stays for decorative strokes (gutter rule, halo ring) where contrast
# is not a readability requirement. oklch(68% 0.22 285) ≈ #a78bfa → 7.2:1 on INK_NIGHT.
VIOLET_KICKER = "#a78bfa"      # unique branch kicker text — WCAG AA+ on INK_NIGHT

# ─── AOV4 medallion resolver (mirrors docs/js/plaque.js `_aovStamp`) ──────────
# The subject art IS the skill's Ascension-Overdrive V4 stamp — the exact
# medallion its rank + branch earned across the graph. Suite/standard branches
# draw from the C family (c1..c6); the Unique branch from the D family (d4..d6).
# OG is a large surface, so every plate uses the `-hero` size tier.
AOV_SUITE_STEM = {
    1: "c1-suite-awakened", 2: "c2-suite-named", 3: "c3-suite-evolved",
    4: "c4-suite-extra", 5: "c5-suite-ultimate", 6: "c6-suite-apex",
}
AOV_UNIQUE_STEM = {
    4: "d4-unique", 5: "d5-unique-ultimate", 6: "d6-unique-impossible",
}


def aov_medallion_href(branch: str, rank: int) -> str:
    """Same-origin relative href to the AOV4 `-hero` stamp for branch+rank.

    Root-relative (`/assets/…`) so the medallion resolves identically whether
    the SVG is served standalone at `/og/<handle>/<slug>.svg`, inlined into the
    share modal via innerHTML, or opened from a locally-served `docs/` root.
    """
    if branch == "unique":
        stem = AOV_UNIQUE_STEM[max(4, min(6, rank))]
    else:
        stem = AOV_SUITE_STEM[max(1, min(6, rank))]
    return f"/assets/ascension-overdrive/aov4-{stem}-hero.webp"


# ─── Branch / rank resolution helpers (Yggdrasil II — read-time) ──────────────
# Plate dispatch + labels are driven by read-time BRANCH + rank via
# computeBranch — never a stored type/tier field. Each plate draws the skill's
# own AOV4 medallion (see aov_medallion_href) and tints its accent from the
# derived branch (gold for suite/standard, violet for unique), so no gaia.json
# colour lookup is needed here.


def og_branch(entry: dict) -> str:
    """Read-time branch for a named-skill entry ('standard'|'suite'|'unique').

    Delegates to gaia_cli.trustMagnitude.computeBranch (Ygg-II rubric E1) — the
    plate composition and labels are driven by branch+rank, never a stored type
    enum. The entry carries level+suiteComponents, so no genericSkillMap thread
    is needed.
    """
    return _compute_branch(entry)


def og_rank_label(rank: int, branch: str) -> str:
    """Top-right plate label: branch-forked rank word (Ygg-II E2).

    Mirrors docs/js/skill-semantics.js rankWord — shared 1-3★
    (Awakened/Named/Evolved), suite 4-6★ (Extra/Ultimate/Apex), unique 4-6★
    (Unique/Unique Ultimate/Unique Impossible). Never emits a banned legacy rank
    word. The label reads e.g. "Extra · 4★" so the plate's top-right stamp is
    meaningful — a graded skill is never labelled a flat type word.
    """
    word = _rank_word(f"{rank}★", branch)
    return f"{word} · {rank}★" if rank > 0 else "Basic"


# Plate-class word — the atlas classification for the card's SUBJECT column,
# keyed on the read-time branch + rank (never a stored type). Reads in the
# top-left kicker above the plate-class rule; the celestial noun tells the
# reader what kind of body the medallion depicts.
def og_plate_class(rank: int, branch: str) -> str:
    if branch == "unique":
        return "SINGULARITY"
    if rank >= 6:
        return "APEX · SUPERNOVA"
    if rank >= 4:
        return "STELLAR"
    return "FIELD BODY"


def level_num(level: str) -> int:
    if not level:
        return 0
    try:
        return int("".join(c for c in level if c.isdigit()))
    except ValueError:
        return 0


def resolveTrustData(skill: dict, fallbackMag: str) -> tuple[str, str]:
    tm = skill.get("trustMagnitude")
    if tm is not None:
        try:
            tmVal = float(tm)
            magStr = f"{tmVal:.1f}" if tmVal > 0 else fallbackMag
        except (ValueError, TypeError):
            magStr = fallbackMag
    else:
        magStr = fallbackMag

    grade = skill.get("overallTrustGrade", "")
    if grade and grade.lower() != "ungraded":
        gradeStr = f"GRADE {grade.upper()}"
    else:
        gradeStr = ""
    return magStr, gradeStr


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
    """Top RA/Dec tick row — cream Departure Mono labels at 28% alpha.

    Confined to the type column (left of the gutter) so they never collide with
    the top-right rank label that lives in the subject column."""
    labels = ["+20°", "+10°", "0°", "−10°"]
    inner_w = COL_SPLIT_X - MARGIN - 40   # stay left of the gutter
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
    """Marginal mono data band: MAG · GRADE · STARS-OR-WORD · DESIGNATION."""
    y = RULE_Y + 28
    sep = '<tspan fill-opacity="0.35"> · · · </tspan>'
    cells = []
    if magnitude and magnitude != "·":
        cells.append(f'<tspan>MAG {html.escape(magnitude)}</tspan>')
    if ev_class:
        cells.append(f'<tspan>{html.escape(ev_class)}</tspan>')
    if stars_or_word:
        cells.append(f'<tspan>{html.escape(stars_or_word)}</tspan>')
    if designation:
        cells.append(f'<tspan>{html.escape(designation)}</tspan>')
    inner = sep.join(cells)
    return (
        f'<text x="{MARGIN}" y="{y}" '
        f'font-family="\'Departure Mono\',\'JetBrains Mono\',ui-monospace,monospace" '
        f'font-size="13" letter-spacing="1.5" fill="{CREAM_ENGRAVED}" fill-opacity="0.7">'
        f'{inner}</text>'
    )


def _catalog_signature(contributor: str, is_origin: bool, year: str) -> str:
    """Discoverer's signature in gold (E4: was honor-red), EB Garamond italic 22px.

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
        f'font-size="22" font-style="italic" fill="{SIGNATURE_GOLD}" '
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


def _gutter_rule(accent: str) -> str:
    """Vertical fold rule separating the type column (left) from the subject
    column (right). A cream hairline overlaid by a short accent-tinted segment
    at the medallion's latitude — the atlas's central-fold convention."""
    top = TICK_Y + 20
    bot = RULE_Y - 8
    seg_top = MEDALLION_CY - 70
    seg_bot = MEDALLION_CY + 70
    return (
        f'<line x1="{COL_SPLIT_X}" y1="{top}" x2="{COL_SPLIT_X}" y2="{bot}" '
        f'stroke="{CREAM_ENGRAVED}" stroke-opacity="0.16" stroke-width="1"/>'
        f'<line x1="{COL_SPLIT_X}" y1="{seg_top}" x2="{COL_SPLIT_X}" y2="{seg_bot}" '
        f'stroke="{accent}" stroke-opacity="0.55" stroke-width="1.6"/>'
    )


def _plate_class_kicker(plate_class: str, accent: str) -> str:
    """Subject-column eyebrow: the celestial classification of the medallion,
    mono caps in the branch accent, sitting just above the medallion disc."""
    y = MEDALLION_CY - MEDALLION_R - 22
    return (
        f'<text x="{MEDALLION_CX}" y="{y}" '
        f'font-family="\'Departure Mono\',\'JetBrains Mono\',ui-monospace,monospace" '
        f'font-size="15" letter-spacing="4.0" fill="{accent}" fill-opacity="0.92" '
        f'text-anchor="middle" dominant-baseline="middle">{html.escape(plate_class)}</text>'
    )


def _medallion(branch: str, rank: int, sid: str, accent: str) -> str:
    """Embed the skill's AOV4 `-hero` medallion as the subject art.

    The 2048² hero art (ornate ring disc spanning ~77.7% of the frame, centred
    at 1024,1024) is drawn at a width that maps that disc to a 2×MEDALLION_R
    circle, positioned so the disc centre lands on (MEDALLION_CX, MEDALLION_CY),
    and clipped to a circle so the black corners are cropped. A faint accent
    halo + cream hairline ring seat the disc into the engraved ground.
    """
    href = aov_medallion_href(branch, rank)
    img_w = 2 * MEDALLION_R / _AOV_DISC_FRAC
    img_x = MEDALLION_CX - img_w / 2
    img_y = MEDALLION_CY - img_w / 2
    clip_id = f"med-clip-{sid}"
    halo_id = f"med-halo-{sid}"
    return (
        f'<defs>'
        f'<clipPath id="{clip_id}"><circle cx="{MEDALLION_CX}" cy="{MEDALLION_CY}" '
        f'r="{MEDALLION_R}"/></clipPath>'
        f'<radialGradient id="{halo_id}" cx="50%" cy="50%" r="50%">'
        f'<stop offset="60%" stop-color="{accent}" stop-opacity="0"/>'
        f'<stop offset="100%" stop-color="{accent}" stop-opacity="0.22"/>'
        f'</radialGradient>'
        f'</defs>'
        # accent halo bloom behind the disc
        f'<circle cx="{MEDALLION_CX}" cy="{MEDALLION_CY}" r="{MEDALLION_R + 26}" '
        f'fill="url(#{halo_id})"/>'
        # the medallion art, clipped to the disc
        f'<image x="{img_x:.1f}" y="{img_y:.1f}" width="{img_w:.1f}" height="{img_w:.1f}" '
        f'href="{href}" xlink:href="{href}" preserveAspectRatio="xMidYMid slice" '
        f'clip-path="url(#{clip_id})"/>'
        # cream hairline ring seating the disc into the plate
        f'<circle cx="{MEDALLION_CX}" cy="{MEDALLION_CY}" r="{MEDALLION_R}" fill="none" '
        f'stroke="{CREAM_ENGRAVED}" stroke-opacity="0.30" stroke-width="1"/>'
        f'<circle cx="{MEDALLION_CX}" cy="{MEDALLION_CY}" r="{MEDALLION_R + 8}" fill="none" '
        f'stroke="{accent}" stroke-opacity="0.35" stroke-width="1.2"/>'
    )


# ─── Unified atlas plate ──────────────────────────────────────────────────────

def build_plate(skill: dict) -> str:
    """Render one catalogue leaf for any branch + rank.

    Composition (Ygg-II /impeccable reshape):
      LEFT column  — plate-class rule (RA/Dec ticks), slash-slug, italic title
                     kicker, gold discoverer's signature, marginal magnitude band.
      RIGHT column — the skill's own AOV4 medallion (`build_plate` never draws
                     procedural line-art; the stamp its rank earned IS the art),
                     seated under a branch-classed kicker.

    Everything — medallion asset, plate-class word, top-right rank label, gutter
    tint — is keyed on the read-time BRANCH (computeBranch) + star rank, never a
    stored type/tier field (E1). Every graded skill lands a proper plate: a 5★
    suite reads "Ultimate · 5★" over its gold apex-family medallion; a 4★ unique
    reads "Unique · 4★" over its violet singularity stamp.
    """
    contributor = skill.get("contributor", "")
    title_text = skill.get("title") or skill.get("name") or ""
    title = html.escape(truncate(title_text, 60))
    slug_raw = slug_after_slash(skill)
    slug = html.escape(slug_raw)
    year = designation_year(skill)
    is_origin = bool(skill.get("origin"))
    n_lvl = level_num(skill.get("level", ""))
    sid = (skill.get("id") or "unknown").replace("/", "-").replace(" ", "-")

    branch = og_branch(skill)
    # Decorative accent (strokes, gutter rule, halo ring) — can be dark violet
    accent = VIOLET_HALO if branch == "unique" else APEX_GOLD
    # Text-fill for the plate-class kicker — must pass WCAG AA on INK_NIGHT
    kicker_fill = VIOLET_KICKER if branch == "unique" else APEX_GOLD
    rank_label = og_rank_label(n_lvl, branch)
    plate_class = og_plate_class(n_lvl, branch)

    # LEFT column type block. Slug is vertically centred with the medallion so
    # the two columns balance; the title kicker sits just below it.
    slug_x = MARGIN + 12
    slug_w = COL_SPLIT_X - slug_x - 40
    # +1 char for the leading slash; 0.53 ratio matches EB Garamond 600 better
    # than the 0.46 default (which let long slugs overrun into the medallion).
    slug_size = autoscale_font("/" + slug_raw, default_px=82,
                               available_w=slug_w, avg_glyph_ratio=0.53)
    slug_y = MEDALLION_CY - 8
    prefix_y = slug_y - slug_size * 0.62 - 18
    kicker_y = slug_y + 50

    # Catalogue prefix above the slug — a mono designation echoing the plate
    # class (SN for supernova, α for stellar, BH for singularity, GAIA field).
    prefix_map = {"SINGULARITY": "BH", "APEX · SUPERNOVA": "SN", "STELLAR": "α"}
    prefix = prefix_map.get(plate_class, "GAIA")

    # Marginal magnitude band. Suite/standard count stars; unique reads its
    # branch-forked rank word (no stars — a singularity emits no light) — only
    # the valid Unique ladder words, never a banned legacy rank word (E2).
    if branch == "unique":
        rank_word = _rank_word(f"{n_lvl}★", "unique").upper() if n_lvl >= 4 else "AWAITED"
        stars_or_word = f"⊘ {rank_word}"
        designation = f"BH {to_roman(max(1, n_lvl))} · {year}"
        fallback_mag = "∞"
    else:
        stars_or_word = "★" * max(1, min(6, n_lvl))
        if plate_class == "APEX · SUPERNOVA":
            designation = f"α 6 OBS · {year}"
        elif plate_class == "STELLAR":
            designation = f"α {slug_raw[:16].upper()} · {year}"
        else:
            designation = f"GAIA · {year}"
        fallback_mag = f"{n_lvl}.0" if n_lvl > 0 else "·"

    mag_val, grade_val = resolveTrustData(skill, fallback_mag)

    # Apex earns the atlas publisher's Diamond Seal in the top-left corner.
    seal = _diamond_seal(MARGIN, MARGIN + 4, size=28) if n_lvl >= 6 else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="{OG_W}" height="{OG_H}" viewBox="0 0 {OG_W} {OG_H}"
  class="plate plate--{branch}" data-branch="{branch}" data-level="{n_lvl}"
  data-plate-class="{html.escape(plate_class)}"
  aria-label="{html.escape(rank_label)} — {html.escape(plate_class)} plate for /{slug}">
  {_shared_frame(rank_label)}
  {seal}
  {_gutter_rule(accent)}

  <!-- SUBJECT column: the skill's own AOV4 medallion -->
  {_plate_class_kicker(plate_class, kicker_fill)}
  {_medallion(branch, n_lvl, sid, accent)}

  <!-- TYPE column: catalogue prefix + slash-slug + title kicker -->
  <text x="{slug_x}" y="{prefix_y:.1f}" font-family="'Departure Mono','JetBrains Mono',ui-monospace,monospace"
    font-size="26" letter-spacing="4.2" fill="{CREAM_ENGRAVED}" fill-opacity="0.65">{html.escape(prefix)}</text>

  <text x="{slug_x}" y="{slug_y}" font-family="'EB Garamond',Georgia,serif" font-weight="600"
    font-size="{slug_size}" fill="{CREAM_ENGRAVED}" dominant-baseline="middle">/{slug}</text>

  <text x="{slug_x}" y="{kicker_y}" font-family="'EB Garamond',Georgia,serif" font-style="italic"
    font-size="24" fill="{CREAM_ENGRAVED}" fill-opacity="0.6" dominant-baseline="middle">'{title}'</text>

  <!-- Discoverer signature -->
  {_catalog_signature(contributor, is_origin, year)}

  <!-- Marginal magnitude band -->
  {_magnitude_band(mag_val, grade_val, stars_or_word, designation)}
</svg>
"""


# ─── Dispatcher ───────────────────────────────────────────────────────────────


def build_og_svg(skill: dict) -> str:
    """Render the Hall Plate for a skill via the unified branch+rank builder.

    Read-time BRANCH (computeBranch) + star rank drive the whole composition
    (Ygg-II E1) — never a stored type enum. That enum once sent every named
    skill (type is only ever basic/fusion) to a barren fallback plate;
    `build_plate` now classes the subject medallion, the plate-class word, the
    rank label, and the gutter tint off that branch+rank instead.
    """
    level = skill.get("level", "")

    # Defence-in-depth: pre-named/demoted skills get no OG card path at all
    # (the main loop skips them), but if a preview/sample ever renders one,
    # withhold the handle and origin mark via the shared gate.
    if is_redacted(level):
        skill = dict(skill)
        skill["contributor"] = REDACTED_HANDLE
        skill["origin"] = False

    return build_plate(skill)



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

        # Path-level redaction: a pre-named/demoted (≤1★) skill is not yet
        # publicly named — emit no OG card so the handle never appears in a
        # /og/<handle>/<slug>.svg path.
        if is_redacted(skill.get("level", "")):
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
