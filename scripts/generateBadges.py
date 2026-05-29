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
TREES_DIR = REPO_ROOT / "skill-trees"
TOKENS_CSS = REPO_ROOT / "docs" / "css" / "tokens.css"
OUT_DIR = REPO_ROOT / "docs" / "badges"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _atlas_helpers import named_slug  # noqa: E402


HONOR_RED = "#ef4444"
INK = "#0f172a"
SLATE = "#94a3b8"
AMBER = "#fbbf24"
WHITE = "#ffffff"

# Rank display names for badge right-panel text (e.g. "Hardened · 4★")
RANK_NAMES = {
    1: "Awakened", 2: "Named", 3: "Evolved",
    4: "Hardened", 5: "Transcendent", 6: "Apex",
}

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
CHAR_WIDTH = {
    " ": 4, "!": 4, '"': 5, "#": 8, "$": 7, "%": 12, "&": 9, "'": 3,
    "(": 5, ")": 5, "*": 6, "+": 8, ",": 4, "-": 5, ".": 4, "/": 5,
    "0": 7, "1": 7, "2": 7, "3": 7, "4": 7, "5": 7, "6": 7, "7": 7,
    "8": 7, "9": 7, ":": 4, ";": 4, "<": 8, "=": 8, ">": 8, "?": 7,
    "@": 12, "[": 5, "\\": 5, "]": 5, "^": 8, "_": 7, "`": 5, "{": 5,
    "|": 4, "}": 5, "~": 8,
    "★": 11, "·": 4, "—": 11, "–": 7,
}
DEFAULT_UPPER = 8
DEFAULT_LOWER = 6


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


# ─── Logo ────────────────────────────────────────────────────────────────────
# Diamond seal drawn at 14x14 in the badge's coord space, top-left (5, 3).
# Hand-tuned to match the source at docs/assets/marks/diamond-seal.svg.
def diamond_seal(color: str = WHITE) -> str:
    return (
        f'<path d="M 12 3 L 19 10 L 12 17 L 5 10 Z" '
        f'fill="none" stroke="{color}" stroke-width="1.4" '
        f'stroke-linejoin="miter"/>'
        f'<text x="12" y="10" font-family="EB Garamond, Georgia, serif" '
        f'font-weight="600" font-size="9" fill="{color}" '
        f'text-anchor="middle" dominant-baseline="central">G</text>'
    )


# ─── Badge builders ──────────────────────────────────────────────────────────
LEFT_WIDTH = 62       # left "GAIA" panel — fixed (full wordmark)
LEFT_WIDTH_SEAL = 26  # seal-only panel — diamond + 6px padding each side
TEXT_Y = 14


def _shadow_defs(uid: str = "g") -> str:
    return (
        f'<linearGradient id="s_{uid}" x2="0" y2="100%">'
        f'<stop offset="0" stop-color="#fff" stop-opacity=".15"/>'
        f'<stop offset="1" stop-opacity=".15"/>'
        f'</linearGradient>'
        f'<clipPath id="r_{uid}"><rect width="{{W}}" height="20" rx="3" fill="#fff"/></clipPath>'
    )


def _left_panel(seal_only: bool = False) -> str:
    """Dark-ink rectangle behind the seal (and optional 'Gaia' wordmark).

    Width depends on `seal_only` — seal-only badges have a much narrower
    panel so the right (data) panel can do most of the talking.
    """
    width = LEFT_WIDTH_SEAL if seal_only else LEFT_WIDTH
    return f'<rect width="{width}" height="20" fill="{INK}"/>'


def _gaia_wordmark(seal_only: bool = False) -> str:
    """Inlined diamond seal + (optional) 'Gaia' wordmark on the dark left panel.

    When `seal_only=True`, the diamond is centered in the narrower seal panel
    and the wordmark is omitted so contributors can drop the badge into a
    README without the "Gaia" copy clashing with their own brand.
    """
    if seal_only:
        # Center the 14×14 diamond inside the LEFT_WIDTH_SEAL (26) panel.
        # diamond_seal() draws at top-left (5, 3) by default — for the seal
        # panel we shift left by (LEFT_WIDTH - LEFT_WIDTH_SEAL) / 2 ≈ -18
        # so the diamond sits at x≈3..17.
        return _diamond_seal_at(x=6)
    return (
        f'{diamond_seal()}'
        f'<text x="24" y="{TEXT_Y}" font-family="EB Garamond, Georgia, serif" '
        f'font-size="12" font-weight="600" fill="#fff" letter-spacing="0.5">Gaia</text>'
    )


def _diamond_seal_at(x: int) -> str:
    """Render the diamond seal with its bounding box left-edge at `x`.

    Used for seal-only badges. The default `diamond_seal()` is hard-coded to
    x=5; this lets us re-position it without rewriting the path.
    """
    # Original path corners: (12,3) (19,10) (12,17) (5,10) → shift by (x-5)
    dx = x - 5
    return (
        f'<path d="M {12 + dx} 3 L {19 + dx} 10 L {12 + dx} 17 L {5 + dx} 10 Z" '
        f'fill="none" stroke="{WHITE}" stroke-width="1.4" '
        f'stroke-linejoin="miter"/>'
        f'<text x="{12 + dx}" y="10" font-family="EB Garamond, Georgia, serif" '
        f'font-weight="600" font-size="9" fill="{WHITE}" '
        f'text-anchor="middle" dominant-baseline="central">G</text>'
    )


def _wrap(width: int, body: str, label: str) -> str:
    """Assemble a final 20-high SVG with rounded clip and shadow gradient."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" '
        f'viewBox="0 0 {width} 20" role="img" aria-label="{label}">'
        f'<title>{label}</title>'
        f'<linearGradient id="s" x2="0" y2="100%">'
        f'<stop offset="0" stop-color="#fff" stop-opacity=".15"/>'
        f'<stop offset="1" stop-opacity=".15"/>'
        f'</linearGradient>'
        f'<clipPath id="r"><rect width="{width}" height="20" rx="3" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#r)">{body}'
        f'<rect width="{width}" height="20" fill="url(#s)"/>'
        f'</g>'
        f'</svg>'
    )


def badge_simple(value: str, panel_color: str, label: str, seal_only: bool = False,
                 right_bg_override: str | None = None) -> str:
    """Two-tone badge: GAIA on left, single-color value on right.

    When `seal_only=True`, the left panel shrinks to just the diamond seal —
    the "Gaia" wordmark is omitted entirely.

    `right_bg_override` lets callers force a specific right-panel fill (e.g.
    pure black `#000000` for the Unique tier) instead of the default INK
    slate. Ignored for `panel_color == "white-gold"` since that branch already
    paints its own gold rectangle.
    """
    left_w = LEFT_WIDTH_SEAL if seal_only else LEFT_WIDTH
    value_w = text_width(value) + 18  # 9px padding each side
    right_w = max(value_w, 32)
    width = left_w + right_w

    if panel_color == "white-gold":
        right_bg = "#fbbf24"
        text_element = f'<tspan fill="#ffffff">{_xml(value)}</tspan>'
    else:
        right_bg = right_bg_override or INK
        text_element = f'<tspan fill="{panel_color}">{_xml(value)}</tspan>'

    body = (
        f'{_left_panel(seal_only)}'
        f'<rect x="{left_w}" width="{right_w}" height="20" fill="{right_bg}"/>'
        f'{_gaia_wordmark(seal_only)}'
        f'<text x="{left_w + right_w / 2:.1f}" y="{TEXT_Y}" '
        f'font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" '
        f'font-weight="700" text-anchor="middle">{text_element}</text>'
    )
    return _wrap(width, body, label)


def badge_handle(handle: str, slash: str, rank: int, rank_color: str, label: str,
                 seal_only: bool = False, right_bg_override: str | None = None) -> str:
    """Identity badge: '@handle/slash · N★' with multi-color tspans on dark right panel.

    `right_bg_override` lets unique-tier callers swap the default INK slate
    for pure black so the purple text reads as off-spectrum.
    """
    left_w = LEFT_WIDTH_SEAL if seal_only else LEFT_WIDTH
    star_value = f"{rank}★" if rank else "★"
    handle_text = f"@{handle}"
    sep = "  ·  "  # double-spaced middot reads cleaner
    text_inner = f"{handle_text}{slash}{sep}{star_value}"
    value_w = text_width(text_inner) + 22  # 11px padding each side
    right_w = max(value_w, 40)
    width = left_w + right_w

    gold_rect = ""
    if rank_color == "white-gold":
        slash_tspan = f'<tspan fill="#fbbf24">{_xml(slash)}</tspan>'

        # Calculate position for 6★ background gold rect
        width_before = text_width(handle_text + slash + sep)
        star_x = left_w + 11 + width_before
        star_w = text_width(star_value) + 6
        gold_rect = f'<rect x="{star_x - 3}" y="3" width="{star_w}" height="14" fill="#fbbf24" rx="2"/>'

        star_tspan = f'<tspan fill="#ffffff">{_xml(star_value)}</tspan>'
        right_bg = INK
    else:
        slash_tspan = f'<tspan fill="{rank_color}">{_xml(slash)}</tspan>'
        star_tspan = f'<tspan fill="{rank_color}">{_xml(star_value)}</tspan>'
        right_bg = right_bg_override or INK

    # Two-tone background: keep dark ink on the right to let colored text pop.
    body = (
        f'{_left_panel(seal_only)}'
        f'<rect x="{left_w}" width="{right_w}" height="20" fill="{right_bg}"/>'
        f'{gold_rect}'
        f'{_gaia_wordmark(seal_only)}'
        f'<text x="{left_w + 11}" y="{TEXT_Y}" '
        f'font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" font-weight="700">'
        f'<tspan fill="{HONOR_RED}">{_xml(handle_text)}</tspan>'
        f'{slash_tspan}'
        f'<tspan fill="{SLATE}">{_xml(sep)}</tspan>'
        f'{star_tspan}'
        f'</text>'
    )
    return _wrap(width, body, label)


def badge_powered_by() -> str:
    """Static 'Powered by Gaia' fallback badge."""
    return badge_simple("powered by gaia", "#475569", "Powered by Gaia")


def badge_not_found() -> str:
    """Validating-state badge: shown when a `?repo=` query doesn't match the
    contributor's approved repos.

    Visually almost-blank: 20px tall (so READMEs don't reflow), seal-only
    dark-ink panel on the left and a muted slate panel on the right reading
    "validating…". The intent is for users to recognise the state as
    "checking, may take up to 24 hours" rather than "broken image".
    """
    label = "Gaia: validating badge — repo not registered yet"
    # Match the seal-only width math from badge_simple() so the badge feels
    # like a real Gaia badge, not a generic placeholder.
    value = "validating…"
    value_w = text_width(value) + 18
    right_w = max(value_w, 80)
    width = LEFT_WIDTH_SEAL + right_w
    body = (
        f'{_left_panel(seal_only=True)}'
        f'<rect x="{LEFT_WIDTH_SEAL}" width="{right_w}" height="20" fill="#1e293b"/>'
        f'{_gaia_wordmark(seal_only=True)}'
        f'<text x="{LEFT_WIDTH_SEAL + right_w / 2:.1f}" y="{TEXT_Y}" '
        f'font-family="Verdana,DejaVu Sans,sans-serif" font-size="10" '
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
    """Build {handle: {top_skill, top_rank, count, named_skills[]}} from named-skills.json."""
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
        result[handle] = {
            "top_skill": top,
            "top_rank": level_num(top.get("level", "")),
            "count": len(skills),
            "named_skills": skills,
        }
    return result


def collect_scan_users() -> dict[str, dict]:
    """Build {handle: {top_rank, count}} from skill-trees/<user>/skill-tree.json."""
    result: dict[str, dict] = {}
    if not TREES_DIR.exists():
        return result
    for tree_dir in sorted(TREES_DIR.iterdir()):
        if not tree_dir.is_dir():
            continue
        tree_file = tree_dir / "skill-tree.json"
        if not tree_file.exists():
            continue
        try:
            data = json.loads(tree_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        unlocked = data.get("unlockedSkills", [])
        if not unlocked:
            continue
        levels = [level_num(s.get("level", "")) for s in unlocked]
        result[tree_dir.name] = {
            "top_rank": max(levels) if levels else 0,
            "count": data.get("stats", {}).get("totalUnlocked", len(unlocked)),
        }
    return result


# ─── Output ──────────────────────────────────────────────────────────────────
def write_user_badges(handle: str, info: dict, scan: dict | None,
                       rank_colors: dict[int, str], out_dir: Path) -> None:
    """Write rank.svg + skills.svg + handle.svg (+ per-skill variants) for one handle.

    Per-contributor SVGs live under ``<out_dir>/_assets/<handle>/`` — NOT directly
    at ``<out_dir>/<handle>/``. That keeps the public 2-segment path
    ``/badges/<handle>/<file>.svg`` free of any static asset, so the validation
    worker (worker/index.js) handles it and serves the real SVG from
    ``/badges/_assets/<handle>/<file>.svg``. See docs/CLOUDFLARE-SETUP.md.
    """
    user_dir = out_dir / "_assets" / handle
    user_dir.mkdir(parents=True, exist_ok=True)

    top_rank = info["top_rank"] if info else 0
    count = info["count"] if info else 0

    # Scan-only data can supplement a named contributor (e.g., higher rank
    # from generic-skill scans). Take the max.
    if scan:
        top_rank = max(top_rank, scan["top_rank"])
        count = max(count, scan["count"])

    # Rank badges always follow the rank color ramp — never the tier accent.
    # Tier colors (unique purple, tier-extra, etc.) live on handle/per-skill
    # badges only, which carry explicit tier context.
    def _rank_color(rank: int) -> str:
        if rank == 6:
            return "white-gold"
        return rank_colors.get(rank, AMBER)

    # Tier-unique purple — pulled from registry/gaia.json typeColors so we
    # don't hardcode the hex. Used for handle / per-skill badges whose
    # underlying skill carries `type: unique`.
    unique_color = load_tier_color("unique")

    if top_rank > 0:
        rank_name = RANK_NAMES.get(top_rank, f"{top_rank}★")
        # "Hardened · 4★" — rank class name anchors meaning, star count is numeric
        value = f"{rank_name} · {top_rank}★" if top_rank < 6 else f"{rank_name} · 6★"
        label = f"Gaia rank: {rank_name} ({top_rank} stars)"
        (user_dir / "rank.svg").write_text(
            badge_simple(value, _rank_color(top_rank), label), encoding="utf-8")
        (user_dir / "rank-seal.svg").write_text(
            badge_simple(value, _rank_color(top_rank), label, seal_only=True),
            encoding="utf-8")

    if count > 0:
        value = f"{count} named skills" if count != 1 else "1 named skill"
        label = f"Gaia: {value}"
        (user_dir / "skills.svg").write_text(
            badge_simple(value, _rank_color(top_rank), label), encoding="utf-8")
        (user_dir / "skills-seal.svg").write_text(
            badge_simple(value, _rank_color(top_rank), label, seal_only=True),
            encoding="utf-8")

    # handle.svg + per-skill badges require named skills (need a slash)
    if info and info.get("top_skill"):
        top = info["top_skill"]
        slash = named_slug(top)
        rank = level_num(top.get("level", ""))

        is_unique = top.get("type") == "unique"
        if is_unique:
            color = unique_color
        elif rank == 6:
            color = "white-gold"
        else:
            color = rank_colors.get(rank, AMBER)

        label = f"Gaia: @{handle}{slash} {rank} stars"
        bg = "#000000" if is_unique else None
        (user_dir / "handle.svg").write_text(
            badge_handle(handle, slash, rank, color, label,
                         right_bg_override=bg), encoding="utf-8")
        (user_dir / "handle-seal.svg").write_text(
            badge_handle(handle, slash, rank, color, label, seal_only=True,
                         right_bg_override=bg),
            encoding="utf-8")

        # Per-skill variants — write both wordmark and seal-only forms
        for skill in info["named_skills"]:
            sslash = named_slug(skill)
            srank = level_num(skill.get("level", ""))

            is_sunique = skill.get("type") == "unique"
            if is_sunique:
                scolor = unique_color
            elif srank == 6:
                scolor = "white-gold"
            else:
                scolor = rank_colors.get(srank, AMBER)

            slabel = f"Gaia: @{handle}{sslash} {srank} stars"
            sbg = "#000000" if is_sunique else None
            # filename: slash-skill without leading slash, e.g. /health -> health.svg
            fname = sslash.lstrip("/").replace("/", "-") or "skill"
            if fname in RESERVED_FILENAMES:
                # Avoid clobbering rank.svg / skills.svg / handle.svg.
                fname = f"{fname}~"
            (user_dir / f"{fname}.svg").write_text(
                badge_handle(handle, sslash, srank, scolor, slabel,
                             right_bg_override=sbg),
                encoding="utf-8")
            (user_dir / f"{fname}-seal.svg").write_text(
                badge_handle(handle, sslash, srank, scolor, slabel, seal_only=True,
                             right_bg_override=sbg),
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
        color = "white-gold" if n == 6 else rank_colors.get(n, AMBER)
        rank_name = RANK_NAMES.get(n, f"{n}★")
        value = f"{rank_name} · {n}★" if n < 6 else f"{rank_name} · 6★"
        label = f"Gaia rank sample: {rank_name} ({n} stars)"
        (samples_dir / f"rank-{n}.svg").write_text(
            badge_simple(value, color, label), encoding="utf-8")
        (samples_dir / f"rank-{n}-seal.svg").write_text(
            badge_simple(value, color, label, seal_only=True), encoding="utf-8")
    # Unique tier — rank 4★, purple text on a deep black panel (the unique
    # tier overrides the default INK slate to read as "rare / off-spectrum").
    # Color is pulled from registry/gaia.json.meta.typeColors.unique
    # (DESIGN.md source of truth) so we never hardcode the hex.
    unique_color = load_tier_color("unique")
    unique_value = "Unique · 4★"
    unique_label = "Gaia rank sample: Unique (4 stars)"
    (samples_dir / "rank-unique.svg").write_text(
        badge_simple(unique_value, unique_color, unique_label,
                     right_bg_override="#000000"),
        encoding="utf-8")
    (samples_dir / "rank-unique-seal.svg").write_text(
        badge_simple(unique_value, unique_color, unique_label, seal_only=True,
                     right_bg_override="#000000"),
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
        repos: dict[str, list[str]] = {}
        for skill in info["named_skills"]:
            url = (skill.get("links") or {}).get("github")
            repo = extract_repo(url) if url else None
            if not repo:
                continue
            repos.setdefault(repo, []).append(skill.get("id", ""))

        # Per-skill picker payload — includes the resolved on-disk filename so
        # the page doesn't need to recompute the reserved-name suffix logic.
        named_skills_payload = []
        for skill in info["named_skills"]:
            slash = named_slug(skill)
            fname = slash.lstrip("/").replace("/", "-") or "skill"
            if fname in RESERVED_FILENAMES:
                fname = f"{fname}~"
            named_skills_payload.append({
                "id": skill.get("id", ""),
                "name": skill.get("name", ""),
                "rank": level_num(skill.get("level", "")),
                "type": skill.get("type", ""),
                "slash": slash,
                "file": f"{fname}.svg",
                "fileSeal": f"{fname}-seal.svg",
            })
        # Sort: rank desc, then origin first, then alphabetical by id.
        named_skills_payload.sort(key=lambda s: (-s["rank"], 0 if s.get("type") == "unique" else 1, s["id"]))

        top_skill_obj = info.get("top_skill")
        top_is_unique = bool(top_skill_obj and top_skill_obj.get("type") == "unique")
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
        "generatedAt": _today_iso(),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR),
                        help="Output directory (default: docs/badges)")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rank_colors = load_rank_colors()
    contributors = collect_contributors()
    scan_users = collect_scan_users()

    # Union of all handles known to either source.
    handles = sorted(set(contributors) | set(scan_users))

    written = 0
    for handle in handles:
        info = contributors.get(handle)
        scan = scan_users.get(handle)
        if not info and not scan:
            continue
        write_user_badges(handle, info, scan, rank_colors, out_dir)
        written += 1

    write_static_badges(out_dir)
    write_sample_badges(rank_colors, out_dir)
    registry = build_registry(contributors)
    write_registry_json(registry, out_dir)
    print(f"Wrote badges for {written} contributors to {out_dir} "
          f"({len(registry)} with approved repos in registry.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
