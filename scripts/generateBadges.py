#!/usr/bin/env python3
"""Gaia Skill Registry — README badge SVG generator.

Reads registry/named-skills.json and skill-trees/<user>/skill-tree.json
and writes shields.io-style flat SVG badges to docs/badges/_assets/<handle>/:

    rank.svg          highest rank earned, color-coded by tier
    skills.svg        total skill count, amber panel
    handle.svg        '@handle/top-skill · N★', honor-red handle, rank-color skill
    <skill-slug>.svg  per-named-skill badge, format same as handle.svg

The public badge URL stays /badges/<handle>/<file>.svg — the validation worker
(worker/index.js) serves it from the _assets/ source above after checking the
?repo= query. Keeping the real SVGs out of the 2-segment /badges/<handle>/ path
is what lets the worker intercept every badge request. See docs/CLOUDFLARE-SETUP.md.

Plus a generic docs/badges/powered-by-gaia.svg.

Logos and brand colors are baked in at generation time so the SVGs render
correctly through GitHub's camo proxy (no external refs, no <style>, no
<script>, no web fonts).

Usage:
    python scripts/generateBadges.py [--out-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
TOKENS_CSS = REPO_ROOT / "docs" / "css" / "tokens.css"
OUT_DIR = REPO_ROOT / "docs" / "badges"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))
from _atlas_helpers import named_slug  # noqa: E402
from gaia_cli.redaction import REDACTED_HANDLE, is_redacted  # noqa: E402  single source of truth
from gaia_cli.taxonomy import branchFor as _compute_branch  # noqa: E402  Ygg-II branch authority
from gaia_cli.taxonomy import rankWord as _rank_word  # noqa: E402  branch-forked rank vocabulary


# Origin contributors render in GOLD (Yggdrasil II rubric E4: the deprecated
# honor-red origin mark is replaced by the gold wreath / gold handle). Mirrors
# --seal-gold in docs/css/tokens.css and the gold wreath SVG.
ORIGIN_GOLD = "#fbbf24"
INK = "#030712"
SLATE = "#94a3b8"
AMBER = "#fbbf24"
WHITE = "#ffffff"


def skill_branch(skill: dict) -> str:
    """Read-time branch for a named-skills entry ('standard'|'suite'|'unique').

    Delegates to the canonical gaia_cli.taxonomy.branchFor — branch is
    NEVER read from a stored type/tier field (Ygg-II rubric E1). The entry
    carries `level` + `suiteComponents` directly, so no genericSkillMap thread
    is needed here.
    """
    return _compute_branch(skill)


def rank_name_for(rank: int, branch: str = "suite") -> str:
    """Branch-forked rank word for a badge (e.g. 'Extra', 'Unique Ultimate').

    Mirrors docs/js/skill-semantics.js rankWord: shared 1-3★
    (Awakened/Named/Evolved), suite 4-6★ (Extra/Ultimate/Apex), unique 4-6★
    (Unique/Unique Ultimate/Unique Impossible). NEVER emits the banned
    'Hardened'/'Transcendent' words (rubric E2).
    """
    return _rank_word(f"{rank}★", branch)

# Filenames produced by the primary badges — per-skill variants whose slug
# collides with one of these are renamed with a `~` suffix so they don't
# overwrite the primary file (e.g., @mattpocock/skills → skills~.svg).
# Both wordmark and seal-only forms are reserved so a user-named skill called
# e.g. "rank-seal" can't clobber the canonical seal file.
RESERVED_FILENAMES = {
    "rank", "skills", "handle", "index", "powered-by-gaia", "not-found",
    "rank-seal", "skills-seal", "handle-seal",
}

# Verdana 11px bold approximate per-character widths (in pixels).
# Conservative — we over-pad rather than clip.
# Measured via Pillow ImageFont.getlength() on Verdana Bold 11px, ceil-rounded.
CHAR_WIDTH = {
    # Punctuation & symbols
    " ": 4, "!": 5, '"': 7, "#": 10, "$": 8, "%": 14, "&": 10, "'": 4,
    "(": 6, ")": 6, "*": 8, "+": 10, ",": 4, "-": 6, ".": 4, "/": 8,
    "0": 8, "1": 8, "2": 8, "3": 8, "4": 8, "5": 8, "6": 8, "7": 8,
    "8": 8, "9": 8, ":": 5, ";": 5, "<": 10, "=": 10, ">": 10, "?": 7,
    "@": 11, "[": 6, "\\": 8, "]": 6, "^": 10, "_": 8, "`": 8, "{": 8,
    "|": 6, "}": 8, "~": 10,
    "★": 11, "·": 4, "—": 11, "–": 7,
    # Uppercase letters
    "A": 9, "B": 9, "C": 8, "D": 10, "E": 8, "F": 8, "G": 9, "H": 10,
    "I": 6, "J": 7, "K": 9, "L": 7, "M": 11, "N": 10, "O": 10, "P": 9,
    "Q": 10, "R": 9, "S": 8, "T": 8, "U": 9, "V": 9, "W": 13, "X": 9,
    "Y": 9, "Z": 8,
    # Lowercase letters
    "a": 8, "b": 8, "c": 7, "d": 8, "e": 8, "f": 5, "g": 8, "h": 8,
    "i": 4, "j": 5, "k": 8, "l": 4, "m": 12, "n": 8, "o": 8, "p": 8,
    "q": 8, "r": 6, "s": 7, "t": 5, "u": 8, "v": 8, "w": 11, "x": 8,
    "y": 8, "z": 7,
}
DEFAULT_UPPER = 10
DEFAULT_LOWER = 8


def text_width(s: str) -> int:
    """Estimate Verdana 11px bold rendered width in pixels."""
    w = 0
    for c in s:
        if c in CHAR_WIDTH:
            w += CHAR_WIDTH[c]
        elif c.isupper():
            w += DEFAULT_UPPER
        else:
            w += DEFAULT_LOWER
    return w


def load_rank_colors() -> dict[int, str]:
    """Parse --rank-{N}: #hex from docs/css/tokens.css."""
    if not TOKENS_CSS.exists():
        return {0: SLATE, 1: "#38bdf8", 2: "#63cab7", 3: "#a78bfa",
                4: "#e879f9", 5: AMBER, 6: AMBER}
    text = TOKENS_CSS.read_text(encoding="utf-8")
    colors: dict[int, str] = {}
    for m in re.finditer(r"--rank-(\d):\s*(#[0-9a-fA-F]+)", text):
        colors[int(m.group(1))] = m.group(2).lower()
    return colors


def load_tier_color(tier: str) -> str:
    """Resolve a tier accent hex from the canonical sources used by tokens.css.

    Order of preference matches the documented source-of-truth chain in
    DESIGN.md:
        1. registry/gaia.json -> meta.typeColors.<tier>.hex
        2. docs/css/tokens.css -> --tier-<tier>: #hex
    Falls back to a sane default ONLY if both lookups fail (defensive — both
    files ship in the repo).
    """
    # 1. registry/gaia.json
    gaia_json = REPO_ROOT / "registry" / "gaia.json"
    if gaia_json.exists():
        try:
            data = json.loads(gaia_json.read_text(encoding="utf-8"))
            hex_val = (
                data.get("meta", {})
                    .get("typeColors", {})
                    .get(tier, {})
                    .get("hex")
            )
            if hex_val:
                return hex_val.lower()
        except (json.JSONDecodeError, OSError):
            pass
    # 2. tokens.css
    if TOKENS_CSS.exists():
        text = TOKENS_CSS.read_text(encoding="utf-8")
        m = re.search(rf"--tier-{re.escape(tier)}:\s*(#[0-9a-fA-F]+)", text)
        if m:
            return m.group(1).lower()
    # Defensive fallback only
    return {"basic": "#38bdf8", "extra": "#c084fc",
            "unique": "#7c3aed", "ultimate": "#f59e0b"}.get(tier, SLATE)


def level_num(level: str) -> int:
    """Return integer rank (0-6) from a level string like '3★'."""
    if not level:
        return 0
    digits = "".join(c for c in str(level) if c.isdigit())
    return int(digits) if digits else 0


# ─── Geometry ────────────────────────────────────────────────────────────────
# Badges render at 28px tall (up from the shields.io-standard 20) so they read
# as engraved guild plaques in a README rather than generic status pills.
H = 28                  # badge height
RX = 6                  # corner radius
LEFT_WIDTH = 82         # left "Gaia" panel — seal + wordmark
LEFT_WIDTH_SEAL = 36    # seal-only panel — diamond + padding
PAD = 13                # right-panel horizontal text padding
TEXT_Y = 18.6           # shared text baseline (vertically centered for FS)
FONT = "Verdana,DejaVu Sans,sans-serif"
FS = 12                 # right-panel data font-size
_WSCALE = FS / 11.0     # CHAR_WIDTH table is calibrated at 11px

# Apex gold ramp — a top-lit metallic bar. Locked to 6★ (PRODUCT.md §3).
GOLD = "#fbbf24"
GOLD_PALE = "#fde68a"
GOLD_DEEP = "#d9920a"
APEX_INK = "#3b2206"    # engraved text on gold — passes AA (white-on-gold didn't)

# Populated by main() from tokens.css + gaia.json so the builders can resolve a
# hex from a rank int without threading the colour maps through every call.
_RANK_COLORS: dict[int, str] = {}
_UNIQUE_COLOR = "#7c3aed"

# v3 amendment (2026-07-18, colorize LOCKED — "Amethyst→Ember"): the Unique
# DECORATION forks by rank. Membership is `unique` from 4★ up, but the treatment
# escalates: 4★ violet, 5★ burnished copper, 6★ inverted (copper ground / dark
# ink). Deliberately OFF the Suite gold axis so a Unique Impossible never reads
# as a Suite Apex — Unique is its own prestige track. Below 4★ a unique-member
# skill decorates plain (is_unique guards never fire below rank 4 in samples).
UNIQUE_COPPER_5 = "#b26a3a"   # burnished copper — Unique Ultimate (5★)
UNIQUE_COPPER_6 = "#e0894a"   # inverted copper ground — Unique Impossible (6★)
UNIQUE_COPPER_6_PALE = "#f0b98a"   # top-lit specular for the 6★ copper gradient
UNIQUE_COPPER_6_DEEP = "#8f4e24"   # bottom of the 6★ copper gradient
UNIQUE_INK = "#2a1206"        # dark engraved text on the 6★ copper ground (AA-safe)


def unique_hex(rank: int) -> str:
    """Resolve the Unique-branch DECORATION accent for a given rank (v3, LOCKED).

      4★ -> violet (base unique color)
      5★ -> burnished copper (Unique Ultimate)
      6★ -> inverted copper (Unique Impossible; the accent is the copper ground)

    Off the Suite gold axis by design — see UNIQUE_COPPER_* above.
    """
    if rank >= 6:
        return UNIQUE_COPPER_6
    if rank == 5:
        return UNIQUE_COPPER_5
    return _UNIQUE_COLOR


def rank_hex(rank: int) -> str:
    return _RANK_COLORS.get(rank, AMBER)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:g})"


def tw(s: str) -> float:
    """Rendered width of `s` at the badge's FS (CHAR_WIDTH is an 11px table)."""
    return text_width(s) * _WSCALE


def _sparkle(cx: float, cy: float, r: float, color: str = "#fffdf5",
             op: float = 0.95) -> str:
    """A small four-point glint. LOCKED to the 6★ Apex tier (PRODUCT.md §3)."""
    s = r * 0.34
    return (
        f'<path d="M {cx:.1f} {cy-r:.1f} L {cx+s:.1f} {cy-s:.1f} '
        f'L {cx+r:.1f} {cy:.1f} L {cx+s:.1f} {cy+s:.1f} L {cx:.1f} {cy+r:.1f} '
        f'L {cx-s:.1f} {cy+s:.1f} L {cx-r:.1f} {cy:.1f} L {cx-s:.1f} {cy-s:.1f} Z" '
        f'fill="{color}" opacity="{op:g}"/>'
    )


# ─── Logo ────────────────────────────────────────────────────────────────────
# Diamond seal centred vertically in the 28px badge, at horizontal centre `cx`.
# Matches the source at docs/assets/marks/diamond-seal.svg.
def diamond_seal(color: str = WHITE, cx: float = 18.0) -> str:
    top, bot, mid, half = 6, 22, 14, 8
    return (
        f'<path d="M {cx} {top} L {cx + half} {mid} L {cx} {bot} L {cx - half} {mid} Z" '
        f'fill="none" stroke="{color}" stroke-width="1.5" stroke-linejoin="miter"/>'
        f'<text x="{cx}" y="{mid}" font-family="EB Garamond, Georgia, serif" '
        f'font-weight="600" font-size="11" fill="{color}" '
        f'text-anchor="middle" dominant-baseline="central">G</text>'
    )


# ─── Badge builders ──────────────────────────────────────────────────────────
def _left_panel(seal_only: bool = False) -> str:
    """Dark-ink rectangle behind the seal (and optional 'Gaia' wordmark)."""
    width = LEFT_WIDTH_SEAL if seal_only else LEFT_WIDTH
    return f'<rect width="{width}" height="{H}" fill="{INK}"/>'


def _gaia_wordmark(seal_only: bool = False, seal_color: str = WHITE) -> str:
    """Inlined diamond seal + (optional) 'Gaia' wordmark on the dark left panel.

    When `seal_only=True`, the diamond is centred in the narrower seal panel and
    the wordmark is omitted so contributors can drop the badge into a README
    without the "Gaia" copy clashing with their own brand. `seal_color` lets the
    Apex tier tint the seal gold so the whole plaque reads as one piece.
    """
    if seal_only:
        return diamond_seal(seal_color, cx=LEFT_WIDTH_SEAL / 2)
    return (
        f'{diamond_seal(seal_color, cx=18)}'
        f'<text x="34" y="{TEXT_Y}" font-family="EB Garamond, Georgia, serif" '
        f'font-size="15" font-weight="600" fill="#fff" letter-spacing="0.5">Gaia</text>'
    )


def _data_panel(x: float, w: float, rank: int, uid: str, *,
                is_unique: bool = False, gold_fill: bool = True) -> tuple[str, str]:
    """Right (data) panel background for a given rank — the rank escalation.

    Returns ``(defs, body)``. The treatment ramps with rank so visual weight is
    earned: dark ink + tier seam (1–3) → tier tint (4) → amber tint (5) →
    metallic gold + light sheen + sparkle glints (6, Apex). `gold_fill=False`
    keeps the panel dark even at Apex (handle badges, where the honor-red handle
    needs a dark ground and the gold lives in the star pill instead).

    v3 amendment (2026-07-18): the Unique DECORATION forks by rank —
    4★ violet, 5★ darker gold, 6★ inverted (gold ground / dark ink). The gold
    Apex ground and sparkle sheen are shared with suite-Apex; only the accent
    color and the 6★ inversion switch on Membership.
    """
    col = unique_hex(rank) if is_unique else rank_hex(rank)
    apex = rank >= 6 and not is_unique
    # Unique Impossible (6★ unique) renders INVERTED — but on a COPPER ground of
    # its own (not the suite gold), so it reads as a peer pinnacle on a distinct
    # prestige track rather than a clone of suite Apex (colorize LOCKED 2026-07-18).
    unique_apex = is_unique and rank >= 6
    metal_ground = (apex or unique_apex) and gold_fill
    defs = ""

    if metal_ground:
        if unique_apex:
            defs += (
                f'<linearGradient id="au{uid}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{UNIQUE_COPPER_6_PALE}"/>'
                f'<stop offset="0.46" stop-color="{UNIQUE_COPPER_6}"/>'
                f'<stop offset="0.62" stop-color="#d47a3e"/>'
                f'<stop offset="1" stop-color="{UNIQUE_COPPER_6_DEEP}"/></linearGradient>'
            )
        else:
            defs += (
                f'<linearGradient id="au{uid}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{GOLD_PALE}"/>'
                f'<stop offset="0.46" stop-color="{GOLD}"/>'
                f'<stop offset="0.62" stop-color="#f7b500"/>'
                f'<stop offset="1" stop-color="{GOLD_DEEP}"/></linearGradient>'
            )
        layers = f'<rect x="{x:.1f}" width="{w:.1f}" height="{H}" fill="url(#au{uid})"/>'
    else:
        bg = "#0a0713" if is_unique else INK
        layers = f'<rect x="{x:.1f}" width="{w:.1f}" height="{H}" fill="{bg}"/>'

    # Tier tint — a faint colour wash that turns on at rank 4 (and for Unique),
    # but NOT over a metallic ground (the metal already carries the weight).
    if ((4 <= rank <= 5) or is_unique) and not metal_ground:
        a = 0.18 if rank >= 5 else 0.14
        layers += f'<rect x="{x:.1f}" width="{w:.1f}" height="{H}" fill="{_rgba(col, a)}"/>'

    # Apex sheen — diagonal light sweep, top specular edge, and sparkle glints.
    # Shared by suite Apex and Unique Impossible (both sit on a metallic ground).
    if metal_ground:
        sx = x + w * 0.16
        layers += (
            f'<polygon points="{sx+10:.1f},0 {sx+22:.1f},0 {sx+8:.1f},{H} {sx-4:.1f},{H}" '
            f'fill="#fff" opacity="0.20"/>'
            f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="1.2" fill="#fff" opacity="0.5"/>'
            f'{_sparkle(x + w - 12, 7, 2.4)}'
            f'{_sparkle(x + w - 6, 13, 1.5, op=0.85)}'
        )

    # Tier seam — a 1px hairline at the panel's left edge, every rank.
    layers += f'<rect x="{x:.1f}" width="1" height="{H}" fill="{_rgba(col, 0.5 if rank else 0.28)}"/>'
    return defs, layers


def _frame(width: int, rank: int, is_unique: bool = False) -> str:
    """Full-badge inset border — the plaque rim. Escalates from rank 4 up."""
    # Apex rim at 6★: suite Apex = gold; Unique Impossible = copper (own track).
    if rank >= 6:
        rim = _rgba(UNIQUE_COPPER_6_DEEP, 0.9) if is_unique else _rgba(GOLD_DEEP, 0.9)
        return (f'<rect x="0.7" y="0.7" width="{width-1.4:.1f}" height="{H-1.4}" '
                f'fill="none" stroke="{rim}" stroke-width="1.4" rx="{RX}"/>')
    if rank >= 4 or is_unique:
        col = unique_hex(rank) if is_unique else rank_hex(rank)
        a = 0.55 if (rank >= 5 or is_unique) else 0.45
        return (f'<rect x="0.6" y="0.6" width="{width-1.2:.1f}" height="{H-1.2}" '
                f'fill="none" stroke="{_rgba(col, a)}" stroke-width="1" rx="{RX}"/>')
    return ""


def _wrap(width: int, body: str, label: str) -> str:
    """Assemble the final SVG with rounded clip and a subtle top sheen."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" '
        f'viewBox="0 0 {width} {H}" role="img" aria-label="{label}">'
        f'<title>{label}</title>'
        f'<linearGradient id="sh" x2="0" y2="100%">'
        f'<stop offset="0" stop-color="#fff" stop-opacity=".10"/>'
        f'<stop offset="1" stop-opacity=".14"/>'
        f'</linearGradient>'
        f'<clipPath id="rc"><rect width="{width}" height="{H}" rx="{RX}" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#rc)">{body}'
        f'<rect width="{width}" height="{H}" fill="url(#sh)"/>'
        f'</g>'
        f'</svg>'
    )


def badge_simple(value: str, rank: int, label: str, *, seal_only: bool = False,
                 is_unique: bool = False, neutral: str | None = None) -> str:
    """Two-tone badge: Gaia seal on the left, a single value on the right.

    The right panel's treatment is driven by `rank` via `_data_panel` /
    `_frame` so the rank escalation is consistent across every badge type.
    `neutral` forces a rank-less muted style (the static "powered by" badge).
    """
    left_w = LEFT_WIDTH_SEAL if seal_only else LEFT_WIDTH
    right_w = max(tw(value) + 2 * PAD, 40)
    width = round(left_w + right_w)
    panel_w = width - left_w
    apex = rank >= 6 and not is_unique
    # Unique Impossible (6★ unique) renders inverted on a COPPER ground — dark
    # engraved copper ink, its own track (colorize LOCKED 2026-07-18).
    unique_apex = is_unique and rank >= 6

    if neutral is not None:
        defs = ""
        layers = (
            f'<rect x="{left_w}" width="{panel_w}" height="{H}" fill="{INK}"/>'
            f'<rect x="{left_w}" width="1" height="{H}" fill="{_rgba(neutral, 0.35)}"/>'
        )
        text_fill, frame, seal_color = neutral, "", WHITE
    else:
        defs, layers = _data_panel(left_w, panel_w, rank, "s", is_unique=is_unique)
        if unique_apex:
            text_fill = UNIQUE_INK        # dark engraved ink on the copper ground
        elif apex:
            text_fill = APEX_INK          # dark engraved text on the gold ground
        elif is_unique:
            text_fill = unique_hex(rank)  # 4★ violet, 5★ burnished copper
        else:
            text_fill = rank_hex(rank)
        frame = _frame(width, rank, is_unique)
        seal_color = (
            UNIQUE_COPPER_6 if unique_apex
            else GOLD if apex
            else WHITE
        )

    body = (
        f'{defs}'
        f'{_left_panel(seal_only)}'
        f'{layers}'
        f'{_gaia_wordmark(seal_only, seal_color)}'
        f'<text x="{left_w + panel_w / 2:.1f}" y="{TEXT_Y}" font-family="{FONT}" '
        f'font-size="{FS}" font-weight="700" text-anchor="middle" '
        f'fill="{text_fill}">{_xml(value)}</text>'
        f'{frame}'
    )
    return _wrap(width, body, label)


def badge_handle(handle: str, slash: str, rank: int, label: str, *,
                 seal_only: bool = False, is_unique: bool = False) -> str:
    """Identity badge: '@handle/slash · N★' on a dark right panel.

    The data panel stays dark even at Apex (so the honor-red handle keeps a dark
    ground); the 6★ gold lives in a metallic star pill with engraved dark text.
    """
    left_w = LEFT_WIDTH_SEAL if seal_only else LEFT_WIDTH
    star_value = f"{rank}★" if rank else "★"
    handle_text = f"@{handle}"
    sep = "  ·  "  # double-spaced middot reads cleaner
    text_inner = f"{handle_text}{slash}{sep}{star_value}"
    apex = rank >= 6 and not is_unique
    value_w = tw(text_inner) + 2 * PAD + (6 if apex else 0)
    right_w = max(value_w, 48)
    width = round(left_w + right_w)
    panel_w = width - left_w

    # Dark panel always (gold_fill=False) so the honor-red handle reads.
    defs, layers = _data_panel(left_w, panel_w, rank, "h",
                               is_unique=is_unique, gold_fill=False)
    accent = _UNIQUE_COLOR if is_unique else rank_hex(rank)
    frame = _frame(width, rank, is_unique)
    seal_color = GOLD if apex else WHITE

    if apex:
        # Metallic star pill, right-anchored to the panel edge with the star
        # CENTERED inside it — keeps the number boxed in any substitute font.
        star_w = tw(star_value)
        pill_pad = 7
        pill_w = star_w + 2 * pill_pad
        pill_right = width - 8
        pill_left = pill_right - pill_w
        pill_cx = pill_left + pill_w / 2
        defs += (
            f'<linearGradient id="aph" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{GOLD_PALE}"/>'
            f'<stop offset="0.5" stop-color="{GOLD}"/>'
            f'<stop offset="1" stop-color="{GOLD_DEEP}"/></linearGradient>'
        )
        pill = (
            f'<rect x="{pill_left:.1f}" y="5" width="{pill_w:.1f}" height="{H-10}" '
            f'rx="5" fill="url(#aph)"/>'
            # glint at the pill's top-left corner — light catching the metal
            f'{_sparkle(pill_left + 3.5, 8, 1.7)}'
        )
        sep_text = (
            f'<text x="{pill_left - 6:.1f}" y="{TEXT_Y}" text-anchor="end" '
            f'font-family="{FONT}" font-size="{FS}" font-weight="700" '
            f'fill="{SLATE}">{_xml("·")}</text>'
        )
        star_text = (
            f'<text x="{pill_cx:.1f}" y="{TEXT_Y}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{FS}" font-weight="700" '
            f'fill="{APEX_INK}">{_xml(star_value)}</text>'
        )
        body = (
            f'{defs}{_left_panel(seal_only)}{layers}{pill}'
            f'{_gaia_wordmark(seal_only, seal_color)}'
            f'<text x="{left_w + PAD:.1f}" y="{TEXT_Y}" font-family="{FONT}" '
            f'font-size="{FS}" font-weight="700">'
            f'<tspan fill="{ORIGIN_GOLD}">{_xml(handle_text)}</tspan>'
            f'<tspan fill="{GOLD}">{_xml(slash)}</tspan></text>'
            f'{sep_text}{star_text}{frame}'
        )
    else:
        body = (
            f'{defs}{_left_panel(seal_only)}{layers}'
            f'{_gaia_wordmark(seal_only, seal_color)}'
            f'<text x="{left_w + PAD:.1f}" y="{TEXT_Y}" font-family="{FONT}" '
            f'font-size="{FS}" font-weight="700">'
            f'<tspan fill="{ORIGIN_GOLD}">{_xml(handle_text)}</tspan>'
            f'<tspan fill="{accent}">{_xml(slash)}</tspan>'
            f'<tspan fill="{SLATE}">{_xml(sep)}</tspan>'
            f'<tspan fill="{accent}">{_xml(star_value)}</tspan></text>'
            f'{frame}'
        )
    return _wrap(width, body, label)


def badge_powered_by() -> str:
    """Static 'Powered by Gaia' fallback badge."""
    return badge_simple("powered by gaia", 0, "Powered by Gaia", neutral=SLATE)


def badge_not_found() -> str:
    """Validating-state badge: shown when a `?repo=` query doesn't match the
    contributor's approved repos.

    Visually almost-blank: 28px tall (matching the real badges so READMEs don't
    reflow), seal-only dark-ink panel on the left and a muted slate panel on the
    right reading "validating…". The intent is for users to recognise the state
    as "checking, may take up to 24 hours" rather than "broken image".
    """
    label = "Gaia: validating badge — repo not registered yet"
    value = "validating…"
    right_w = max(tw(value) + 2 * PAD, 92)
    width = round(LEFT_WIDTH_SEAL + right_w)
    body = (
        f'{_left_panel(seal_only=True)}'
        f'<rect x="{LEFT_WIDTH_SEAL}" width="{width - LEFT_WIDTH_SEAL}" height="{H}" fill="#1e293b"/>'
        f'<rect x="{LEFT_WIDTH_SEAL}" width="1" height="{H}" fill="{_rgba(SLATE, 0.28)}"/>'
        f'{_gaia_wordmark(seal_only=True)}'
        f'<text x="{LEFT_WIDTH_SEAL + (width - LEFT_WIDTH_SEAL) / 2:.1f}" y="{TEXT_Y}" '
        f'font-family="{FONT}" font-size="11" '
        f'font-weight="500" fill="{SLATE}" text-anchor="middle" '
        f'font-style="italic">{value}</text>'
    )
    return _wrap(width, body, label)


def _xml(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


# ─── Data assembly ───────────────────────────────────────────────────────────
def collect_contributors() -> dict[str, dict]:
    """Build {handle: {top_skill, top_rank, count, named_skills[]}} from named-skills.json.

    Entirely pre-named/demoted contributors (top rank ≤1★ across all bucketed
    and awaitingClassification entries) are filtered out per the redaction
    invariant — see :func:`prenamed_contributor_handles` for the standalone set
    used to gate the scan-only path in :func:`main`.
    """
    if not NAMED_JSON.exists():
        return {}
    data = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
    buckets = data.get("buckets", {})
    per: dict[str, dict] = defaultdict(lambda: {"named_skills": []})
    for entries in buckets.values():
        for entry in entries:
            handle = entry.get("contributor")
            if not handle:
                continue
            per[handle]["named_skills"].append(entry)

    # Also collect awakened/pre-named entries awaiting classification
    awaiting = data.get("awaitingClassification", [])
    for entry in awaiting:
        handle = entry.get("contributor")
        if not handle:
            continue
        per[handle]["named_skills"].append(entry)

    result: dict[str, dict] = {}
    for handle, info in per.items():
        skills = info["named_skills"]
        # Highest rank, tiebreak: origin role first, then alphabetical by id.
        def sort_key(e: dict) -> tuple:
            return (
                -level_num(e.get("level", "")),
                0 if e.get("role") == "origin" else 1,
                e.get("id", ""),
            )
        skills_sorted = sorted(skills, key=sort_key)
        top = skills_sorted[0]
        top_rank = level_num(top.get("level", ""))
        # Redaction invariant (META.md §1, see CLAUDE.md "Known Badges Issues"
        # and src/gaia_cli/redaction.py): an entirely pre-named/demoted
        # contributor — every named entry is ≤1★, including awaitingClassification
        # rows — must not appear in any downstream public artifact (badge dir,
        # registry.json, OG card). Dropping them here is the single source of
        # truth that breaks the auto-sync regen loop at its origin
        # (PR #800 / #802 retro: 8 stale dirs kept reappearing on every
        # ``gaia dev docs`` run because the redaction was only enforced in
        # ``write_user_badges`` — scan_users still made them surface).
        if is_redacted(top_rank):
            continue
        result[handle] = {
            "top_skill": top,
            "top_rank": top_rank,
            "count": len(skills),
            "named_skills": skills,
        }
    return result


def prenamed_contributor_handles() -> set[str]:
    """Return the set of handles whose every named-skills entry is ≤1★.

    Drives the scan-only filter in :func:`main` so a contributor whose only
    registry presence is pre-named/demoted does not get a /badges/_assets/
    directory through the scan path. Mirrors the dedicated check in
    ``scripts/validate_redaction.py`` (Section D) — keep them in lockstep.
    """
    if not NAMED_JSON.exists():
        return set()
    data = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
    top_rank: dict[str, int] = {}
    for entries in data.get("buckets", {}).values():
        for entry in entries:
            handle = entry.get("contributor")
            if not handle:
                continue
            top_rank[handle] = max(top_rank.get(handle, 0),
                                   level_num(entry.get("level", "")))
    for entry in data.get("awaitingClassification", []):
        handle = entry.get("contributor")
        if not handle:
            continue
        top_rank[handle] = max(top_rank.get(handle, 0),
                               level_num(entry.get("level", "")))
    return {h for h, r in top_rank.items() if is_redacted(r)}



# ─── Output ──────────────────────────────────────────────────────────────────
def write_user_badges(handle: str, info: dict,
                       rank_colors: dict[int, str], out_dir: Path) -> None:
    """Write rank.svg + skills.svg + handle.svg (+ per-skill variants) for one handle.

    Per-contributor SVGs live under ``<out_dir>/_assets/<handle>/`` — NOT directly
    at ``<out_dir>/<handle>/``. That keeps the public 2-segment path
    ``/badges/<handle>/<file>.svg`` free of any static asset, so the validation
    worker (worker/index.js) handles it and serves the real SVG from
    ``/badges/_assets/<handle>/<file>.svg``. See docs/CLOUDFLARE-SETUP.md.
    """
    named_top_rank = info["top_rank"] if info else 0

    # Path-level redaction: a NAMED contributor whose named work is all ≤1★
    # (pre-named/demoted) is not yet publicly named — emit NO badge so the
    # handle never appears in a /badges/_assets/<handle>/ path. We gate on
    # *named* standing only: a personal skill-tree (scan) must not un-redact a
    # contributor whose registry contributions are all pre-named. Pure scan-only
    # users (no named entry, info is None) keep their handle-free rank/skills
    # badges. The shared gate decides the threshold.
    if info is not None and is_redacted(named_top_rank):
        return

    top_rank = named_top_rank
    count = info["count"] if info else 0

    user_dir = out_dir / "_assets" / handle
    user_dir.mkdir(parents=True, exist_ok=True)

    if top_rank > 0:
        # Branch-forked rank word (Ygg-II E1/E2): the highest-ranked named
        # skill determines the branch. computeBranch reads level+suiteComponents,
        # NEVER a stored type/tier field.
        top_branch = skill_branch(info["top_skill"]) if info and info.get("top_skill") else "suite"
        rank_name = rank_name_for(top_rank, top_branch)
        # "Extra · 4★" / "Unique · 4★" — rank word anchors meaning, star count numeric
        value = f"{rank_name} · {top_rank}★"
        label = f"Gaia rank: {rank_name} ({top_rank} stars)"
        (user_dir / "rank.svg").write_text(
            badge_simple(value, top_rank, label), encoding="utf-8")
        (user_dir / "rank-seal.svg").write_text(
            badge_simple(value, top_rank, label, seal_only=True),
            encoding="utf-8")

    if count > 0:
        value = f"{count} named skills" if count != 1 else "1 named skill"
        label = f"Gaia: {value}"
        (user_dir / "skills.svg").write_text(
            badge_simple(value, top_rank, label), encoding="utf-8")
        (user_dir / "skills-seal.svg").write_text(
            badge_simple(value, top_rank, label, seal_only=True),
            encoding="utf-8")

    # handle.svg + per-skill badges require named skills (need a slash)
    if info and info.get("top_skill"):
        top = info["top_skill"]
        slash = named_slug(top)
        rank = level_num(top.get("level", ""))
        is_unique = skill_branch(top) == "unique"

        badge_handle_text = REDACTED_HANDLE if is_redacted(rank) else handle
        label = f"Gaia: @{badge_handle_text}{slash} {rank} stars"
        (user_dir / "handle.svg").write_text(
            badge_handle(badge_handle_text, slash, rank, label,
                         is_unique=is_unique), encoding="utf-8")
        (user_dir / "handle-seal.svg").write_text(
            badge_handle(badge_handle_text, slash, rank, label, seal_only=True,
                         is_unique=is_unique),
            encoding="utf-8")

        # Per-skill variants — write both wordmark and seal-only forms.
        for skill in info["named_skills"]:
            sslash = named_slug(skill)
            srank = level_num(skill.get("level", ""))

            # Pre-named/demoted (≤1★) skills get no shareable per-skill badge —
            # suppressing the file keeps the handle out of a guessable
            # /badges/_assets/<handle>/<slug>.svg path.
            if is_redacted(srank):
                continue

            is_sunique = skill_branch(skill) == "unique"
            # srank is always ≥ 2 here (≤1★ skipped above) — handle is public.
            badge_handle_text = handle
            slabel = f"Gaia: @{badge_handle_text}{sslash} {srank} stars"
            # filename: slash-skill without leading slash, e.g. /health -> health.svg
            fname = sslash.lstrip("/").replace("/", "-") or "skill"
            if fname in RESERVED_FILENAMES:
                # Avoid clobbering rank.svg / skills.svg / handle.svg.
                fname = f"{fname}~"
            (user_dir / f"{fname}.svg").write_text(
                badge_handle(badge_handle_text, sslash, srank, slabel,
                             is_unique=is_sunique),
                encoding="utf-8")
            (user_dir / f"{fname}-seal.svg").write_text(
                badge_handle(badge_handle_text, sslash, srank, slabel, seal_only=True,
                             is_unique=is_sunique),
                encoding="utf-8")


def write_static_badges(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "powered-by-gaia.svg").write_text(badge_powered_by(), encoding="utf-8")
    # The "validating…" badge served by the site Worker (worker/index.js)
    # whenever a `?repo=` query param doesn't match the contributor's approved repos.
    # Page UI explains the 24h propagation window so users don't read this
    # as "broken" — see docs/badges/index.html § "Why is my badge blank?".
    (out_dir / "not-found.svg").write_text(badge_not_found(), encoding="utf-8")


def write_sample_badges(rank_colors: dict[int, str], out_dir: Path) -> None:
    """Write 6 demo rank.svg files (1★ → 6★) plus a `unique` sample used by the
    badges-page sampler. Each rank also gets a `-seal.svg` variant so the page
    can preview the seal-only mode under the "Hide Gaia" toggle."""
    samples_dir = out_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    for n in range(1, 7):
        # Sample ladder shows the shared 1-3★ words + the suite 4-6★ fork
        # (Extra/Ultimate/Apex); the unique fork gets its own sample below.
        rank_name = rank_name_for(n, "suite")
        value = f"{rank_name} · {n}★"
        label = f"Gaia rank sample: {rank_name} ({n} stars)"
        (samples_dir / f"rank-{n}.svg").write_text(
            badge_simple(value, n, label), encoding="utf-8")
        (samples_dir / f"rank-{n}-seal.svg").write_text(
            badge_simple(value, n, label, seal_only=True), encoding="utf-8")
    # Unique branch samples — 4★/5★/6★ (Unique / Unique Ultimate / Unique Impossible)
    for u_n, u_word, u_slug in [
        (4, "Unique", "unique"),
        (5, "Unique Ultimate", "unique-5"),
        (6, "Unique Impossible", "unique-6"),
    ]:
        u_value = f"{u_word} · {u_n}★"
        u_label = f"Gaia rank sample: {u_word} ({u_n} stars)"
        (samples_dir / f"rank-{u_slug}.svg").write_text(
            badge_simple(u_value, u_n, u_label, is_unique=True),
            encoding="utf-8")
        (samples_dir / f"rank-{u_slug}-seal.svg").write_text(
            badge_simple(u_value, u_n, u_label, seal_only=True, is_unique=True),
            encoding="utf-8")


def extract_repo(url: str) -> str | None:
    """Pull '<owner>/<repo>' from a GitHub URL.

    Accepts the `blob/branch/path` form documented by install.py — bare
    repo URLs work too. Returns None for anything that doesn't look like
    a GitHub URL.
    """
    if not url:
        return None
    m = re.match(r"^https?://github\.com/([\w.-]+)/([\w.-]+)", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    # Strip trailing `.git` if present (common in clone URLs).
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}"


def build_registry(contributors: dict[str, dict]) -> dict:
    """Build the public approved-repos manifest consumed by the sampler and
    the future Cloudflare Worker that validates `?repo=` on each request.
    """
    out: dict[str, dict] = {}
    for handle, info in contributors.items():
        # Entirely pre-named/demoted contributors emit no badges (see
        # write_user_badges) and must not appear in the public manifest.
        if is_redacted(info.get("top_rank", 0)):
            continue
        # Only named (≥2★) skills are publicly listed — a pre-named skill has
        # no shareable badge, so it never enters the manifest.
        public_skills = [s for s in info["named_skills"] if not is_redacted(level_num(s.get("level", "")))]
        repos: dict[str, list[str]] = {}
        for skill in public_skills:
            url = (skill.get("links") or {}).get("github")
            repo = extract_repo(url) if url else None
            if not repo:
                continue
            repos.setdefault(repo, []).append(skill.get("id", ""))

        # Per-skill picker payload — includes the resolved on-disk filename so
        # the page doesn't need to recompute the reserved-name suffix logic.
        named_skills_payload = []
        for skill in public_skills:
            slash = named_slug(skill)
            fname = slash.lstrip("/").replace("/", "-") or "skill"
            if fname in RESERVED_FILENAMES:
                fname = f"{fname}~"
            named_skills_payload.append({
                "id": skill.get("id", ""),
                "name": skill.get("name", ""),
                "rank": level_num(skill.get("level", "")),
                "type": skill.get("type", ""),
                "branch": skill_branch(skill),
                "slash": slash,
                "file": f"{fname}.svg",
                "fileSeal": f"{fname}-seal.svg",
            })
        # Sort: rank desc, then unique-branch first, then alphabetical by id.
        # Branch is read-time derived (E1) — never the dead `type == "unique"`.
        named_skills_payload.sort(key=lambda s: (-s["rank"], 0 if s.get("branch") == "unique" else 1, s["id"]))

        top_skill_obj = info.get("top_skill")
        top_is_unique = bool(top_skill_obj and skill_branch(top_skill_obj) == "unique")
        out[handle] = {
            "repos": sorted(repos.keys()),
            "skillsByRepo": {r: sorted(ids) for r, ids in repos.items()},
            "topSkill": top_skill_obj.get("id", "") if top_skill_obj else None,
            "topRank": info.get("top_rank", 0),
            "topIsUnique": top_is_unique,
            "count": info.get("count", 0),
            "namedSkills": named_skills_payload,
        }
        if not repos and not named_skills_payload:
            del out[handle]
    return out


def write_registry_json(contributors: dict[str, dict], out_dir: Path) -> None:
    """Write docs/badges/registry.json — the public per-contributor manifest."""
    payload = {
        "generatedAt": _source_generated_at(),
        "schema": "gaia-badges-registry/2",
        "description": (
            "Approved repos per contributor for Gaia README badges. "
            "Derived from registry/named-skills.json `links.github` URLs. "
            "The site Worker at worker/index.js handles /badges/<handle>/<file>.svg "
            "(the real SVGs live at /badges/_assets/<handle>/<file>.svg) and serves "
            "the `validating…` SVG (docs/badges/not-found.svg) when the `?repo=` "
            "query string doesn't match a repo listed here. Schema v2 adds "
            "`fileSeal` for the seal-only (no 'Gaia' wordmark) variant."
        ),
        "contributors": contributors,
    }
    (out_dir / "registry.json").write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _today_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).date().isoformat()


def _source_generated_at() -> str:
    """Stamp the badge registry with the source's own ``generatedAt`` so the
    artifact is reproducible.

    Using wall-clock time here made ``docs/badges/registry.json`` drift every
    calendar day, which tripped the strict ``build_docs.py --check`` diff on any
    CI run that happened after the last regeneration. Mirroring the committed
    ``registry/named-skills.json`` date keeps the output deterministic — it only
    changes when the source data is regenerated (a committed change in itself).
    Falls back to today's date if the source lacks the field.
    """
    try:
        data = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
        stamp = data.get("generatedAt")
        if isinstance(stamp, str) and stamp:
            return stamp
    except (OSError, ValueError):
        pass
    return _today_iso()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR),
                        help="Output directory (default: docs/badges)")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rank_colors = load_rank_colors()
    # Publish the colour maps to module scope so the badge builders can resolve
    # a hex from a rank int (and the Unique tier accent) without threading the
    # maps through every call.
    _RANK_COLORS.clear()
    _RANK_COLORS.update(rank_colors)
    global _UNIQUE_COLOR
    _UNIQUE_COLOR = load_tier_color("unique")

    contributors = collect_contributors()
    # Union of all handles known to either source.
    handles = sorted(contributors.keys())

    written = 0
    for handle in handles:
        info = contributors.get(handle)
        if not info:
            continue
        write_user_badges(handle, info, rank_colors, out_dir)
        written += 1

    write_static_badges(out_dir)
    write_sample_badges(rank_colors, out_dir)
    registry = build_registry(contributors)
    # Backstop: if named-skills.json had real contributor buckets coming in but
    # the registry collapsed to {} (filter/redaction wiped them all, or a stale
    # snapshot got read), fail loudly rather than overwrite a healthy on-disk
    # registry.json with an empty one. The sanity guard in build_docs.py is the
    # primary gate; this catches direct invocations of this script too.
    #
    # The signal is "named-skills had inputs but contributors came out empty",
    # NOT "_assets/ has any dirs at all" — scan-only users legitimately produce
    # /_assets/<handle>/ dirs without entering registry.json (they have no
    # approved repo). The earlier "asset_dirs > 0" heuristic false-fired in
    # tests that monkey-patched NAMED_JSON to {} but couldn't patch the real
    # skill-trees/ directory the scan path reads.
    had_named_inputs = False
    if NAMED_JSON.exists():
        try:
            _named_payload = json.loads(NAMED_JSON.read_text(encoding="utf-8"))
            had_named_inputs = bool(_named_payload.get("buckets")) or bool(
                _named_payload.get("awaitingClassification"))
        except json.JSONDecodeError:
            had_named_inputs = False
    if had_named_inputs and len(registry) == 0:
        import sys as _sys
        print(
            "ERROR: named-skills.json has bucket entries but registry.json::"
            "contributors collapsed to empty. Filter/redaction likely wiped "
            "every contributor — refusing to write a starved registry.",
            file=_sys.stderr,
        )
        return 1
    write_registry_json(registry, out_dir)
    print(f"Wrote badges for {written} contributors to {out_dir} "
          f"({len(registry)} with approved repos in registry.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
