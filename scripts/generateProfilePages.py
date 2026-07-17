#!/usr/bin/env python3
"""Gaia Skill Registry — Contributor Profile Page Generator.

Reads registry/named-skills.json and generates static HTML contributor
profile pages at docs/u/{handle}/index.html.

Each page shows:
  - Contributor handle in honor red
  - Origin contributor badge + skill count
  - A grid of settled plaque cards (one per named skill)
  - An ascension log ledger

Usage:
    python scripts/generateProfilePages.py [--named PATH] [--out-dir PATH]

Exit codes:
    0 — Pages generated successfully
    1 — Fatal error
"""

import json
import os
import sys
import argparse
import html
import datetime
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
GAIA_JSON = REPO_ROOT / "registry" / "gaia.json"
DOCS_DIR = REPO_ROOT / "docs"
OUT_DIR = DOCS_DIR / "u"

# Phase 8d — share slash-naming + linked-handle helpers with the JS
# atlas-helpers module via scripts/_atlas_helpers.py.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))
from _atlas_helpers import handle_link, named_slug  # noqa: E402
from gaia_cli.redaction import is_redacted  # noqa: E402  single source of truth
from gaia_cli.taxonomy import branchFor as _compute_branch  # noqa: E402  Ygg-II branch authority
from gaia_cli.taxonomy import rankWord as _rank_word  # noqa: E402  branch-forked rank vocabulary


def skill_branch(entry: dict) -> str:
    """Derive the Yggdrasil II progression branch for a named-skill entry.

    Delegates to gaia_cli.trustMagnitude.computeBranch (rubric E1) — the single
    source of truth. Branch is a READ-TIME function of (suiteComponents present?,
    rank); the retired `type` enum is NEVER consulted. Returns one of
    ``'standard'`` (1-3★), ``'suite'`` (4★+ with suiteComponents), or
    ``'unique'`` (4★+ standalone mastery).
    """
    return _compute_branch(entry)


def branch_rank_label(level: str, branch: str) -> str:
    """Human rank word for aria labels, forked by branch (no banned vocabulary).

    e.g. ('3★','standard') -> 'Evolved'; ('5★','suite') -> 'Ultimate';
    ('4★','unique') -> 'Unique'. Below 2★ the shared ladder still applies.
    """
    return _rank_word(level, branch)


def _read_version() -> str:
    pyproject = REPO_ROOT / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.startswith("version = "):
                return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def _apply_cache_busting(text: str, version: str) -> str:
    # 1. Strip legacy no-cache meta tags if present (they break back/forward cache
    #    and prevent the browser from honoring our versioned query strings).
    text = re.sub(
        r'\n?\s*<meta\s+http-equiv="Cache-Control"\s+content="no-cache, no-store, must-revalidate">',
        '',
        text,
    )
    text = re.sub(
        r'\n?\s*<meta\s+http-equiv="Pragma"\s+content="no-cache">',
        '',
        text,
    )
    text = re.sub(
        r'\n?\s*<meta\s+http-equiv="Expires"\s+content="0">',
        '',
        text,
    )

    # 2. Inject or update window.GAIA_VERSION in <head>
    version_script = f'\n  <script>window.GAIA_VERSION = "{version}";</script>'
    if 'window.GAIA_VERSION = ' in text:
        text = re.sub(
            r'<script>\s*window\.GAIA_VERSION\s*=\s*"[^"]*";\s*</script>',
            f'<script>window.GAIA_VERSION = "{version}";</script>',
            text
        )
    else:
        text = text.replace("<head>", f"<head>{version_script}", 1)

    # 3. Append version query parameters (?v={version}) to local CSS and JS imports.
    text = re.sub(
        r'href="((?:(?:\.\./)*)css/[a-zA-Z0-9_\-\./]+\.css)(?:\?v=[^"]*)?"',
        fr'href="\1?v={version}"',
        text
    )
    text = re.sub(
        r'src="((?:(?:\.\./)*)js/[a-zA-Z0-9_\-\./]+\.js)(?:\?v=[^"]*)?"',
        fr'src="\1?v={version}"',
        text
    )
    return text


def level_num(level: str) -> int:
    """Return the integer rank (1-6) from a level string like '3★'."""
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


def rank_badge_html(level: str, variant: str = "stars", size: str = "md", label: str | None = None) -> str:
    """Stage 2 — Python sibling of window.rankBadge(level, opts).

    Emits the same .rank-badge DOM the JS component produces so that the
    server-rendered surfaces (profile pages, OG cards) stay pixel-
    identical to the live surfaces. Reads colours via CSS tokens only
    — no Python colour logic.

    Args:
        level: rank token, e.g. '4★', '4', or 4.
        variant: 'chip' | 'stars' | 'full'. Default 'stars'.
        size: 'sm' | 'md' | 'lg'. Default 'md'.
        label: chip label override. Defaults to '<N>★'.
    """
    n = level_num(level)
    if variant not in ("chip", "stars", "full"):
        variant = "chip"
    if size not in ("sm", "md", "lg"):
        size = "md"
    chip_label = label if label is not None else f"{n}★"
    aria = f"Rank {n} of 6"

    def _chip() -> str:
        return f'<span class="rank-badge__chip">{html.escape(chip_label)}</span>'

    def _stars() -> str:
        parts = ['<span class="rank-badge__stars" aria-hidden="true">']
        for i in range(1, 7):
            attr = "data-on=\"\"" if i <= n else "data-off=\"\""
            parts.append(f'<span class="rank-badge__star" {attr}>★</span>')
        parts.append("</span>")
        return "".join(parts)

    if variant == "chip":
        inner = _chip()
    elif variant == "stars":
        inner = _stars()
    else:  # full
        inner = _chip() + _stars()

    return (
        f'<span class="rank-badge" data-level="{n}" data-variant="{variant}" '
        f'data-size="{size}" role="img" aria-label="{html.escape(aria)}">'
        f"{inner}</span>"
    )


def build_stars(level: str) -> str:
    """Deprecated — kept as a one-line redirect to rank_badge_html('stars').

    Stage 2 unified the stars rendering behind .rank-badge; the legacy
    .plaque-star markup is no longer emitted. Stage 5 may remove this
    wrapper entirely once no callers remain.
    """
    return rank_badge_html(level, variant="stars")


# Stage 1 — sprite-driven icons. Profile pages live at docs/u/<handle>/index.html
# so the sprite is two levels above the page (../../assets/icons.svg).
ICON_SPRITE_REL = "../../assets/icons.svg"
# Asset base prefix for the per-handle profile page depth (docs/u/<handle>/).
# Every relative asset URL (AOV4 medallion webp, gold wreath SVG) resolves from
# here; mirrors docs/js/plaque.js _base() which strips the icons.svg suffix.
ASSET_BASE_REL = "../../"
DIAMOND_SEAL_SVG = (
    f'<svg class="ico plaque-seal" aria-hidden="true">'
    f'<use href="{ICON_SPRITE_REL}#seal-diamond"/></svg>'
)


# ── AOV4 medallion resolver (rubric E3) ──────────────────────────────
# Python sibling of docs/js/plaque.js _aovStamp/_sizeTier. The rank medallion
# IS the Ascension-Overdrive v4 stamp — never a CSS-gradient orb stand-in on a
# named skill. Suite/standard branches use the C family (c1..c6); the Unique
# branch uses the D family (d4..d6). The size tier (badge/card/hero) is chosen
# by the render variant's legacy size modifier.
AOV_SUITE_STEM = {
    1: "c1-suite-awakened", 2: "c2-suite-named", 3: "c3-suite-evolved",
    4: "c4-suite-extra", 5: "c5-suite-ultimate", 6: "c6-suite-apex",
}
AOV_UNIQUE_STEM = {
    4: "d4-unique", 5: "d5-unique-ultimate", 6: "d6-unique-impossible",
}


def _aov_stamp(branch: str, n: int, tier: str = "card") -> str:
    """Resolve the AOV4 stamp URL for a branch + rank at a given size tier."""
    if tier not in ("badge", "card", "hero"):
        tier = "card"
    if branch == "unique":
        stem = AOV_UNIQUE_STEM[max(4, min(6, n))]
    else:
        stem = AOV_SUITE_STEM[max(1, min(6, n))]
    return f"{ASSET_BASE_REL}assets/ascension-overdrive/aov4-{stem}-{tier}.webp"


def _size_tier(size_modifier: str = "") -> str:
    """Map the legacy CSS size modifier to an AOV size tier.

    'sm' -> badge · 'lg' -> hero · (none) -> card. Mirrors plaque.js _sizeTier.
    """
    if size_modifier == "sm":
        return "badge"
    if size_modifier == "lg":
        return "hero"
    return "card"


# Stage 3 — Python sibling field helpers. One source of truth per
# field across all three variants Python emits (--mini, --tile,
# --settled) so the server-rendered DOM matches docs/js/plaque.js
# exactly. The dict below names every slot and the lambda that
# emits it; the variant functions below assemble them.
def _field_orb(ns: dict, size_modifier: str = "") -> str:
    # Rubric E3: the medallion IS the AOV4 stamp — NO CSS-gradient orb stand-in
    # on a named skill. Branch (suite/unique/standard) + rank pick the asset;
    # the surface's size modifier picks badge/card/hero. Standard-branch named
    # skills (rank 1..3) render the c1..c3 suite stamps. Mirrors docs/js/
    # plaque.js _fieldOrb: <span.plaque-orb--medallion><img.plaque-orb__stamp></span>.
    # If the webp 404s, [data-stamp-fail] falls back to a branch-tinted gradient
    # (plaque.css) so a rank medallion still reads — never an empty hole.
    branch = skill_branch(ns)
    n = level_num(ns.get("level", ""))
    mod = f" plaque-orb--{size_modifier}" if size_modifier else ""
    apex = " plaque-orb--vi" if n >= 6 else ""
    tier = _size_tier(size_modifier)
    src = _aov_stamp(branch, n, tier)
    rank_name = branch_rank_label(ns.get("level", ""), branch)
    aria = f"{rank_name} medallion" if rank_name else "rank medallion"
    return (
        f'<span class="plaque-orb plaque-orb--medallion plaque-orb--{branch}{mod}{apex}" '
        f'data-branch="{branch}" role="img" aria-label="{html.escape(aria)}">'
        f'<img class="plaque-orb__stamp" src="{html.escape(src)}" alt="" '
        f'decoding="async" loading="lazy" '
        f'onerror="this.style.display=\'none\';this.parentNode.setAttribute(\'data-stamp-fail\',\'true\')">'
        f'</span>'
    )


def _field_avatar(ns: dict, size: int = 40) -> str:
    """Contributor GitHub avatar framed by the gold origin wreath (E3/E4).

    Python sibling of docs/js/plaque.js _fieldAvatar. Every skill surface
    renders the contributor's GitHub avatar framed by the gold origin wreath
    (docs/assets/origin-wreath-gold.svg) — the NEW origin mark (red -> gold).
    The avatar links to the skill repo (links.github), replacing the deprecated
    standalone GitHub button. A missing avatar swaps to the GitHub identicon
    endpoint (never hides the img -> no empty hole). Redacted (<=1 star) skills
    expose no handle, so no avatar renders (showing one would leak the handle).
    """
    handle = ns.get("contributor", "") or ""
    if not handle:
        return ""
    if is_redacted(ns.get("level", "")):
        return ""
    clean = str(handle).lstrip("@")
    from urllib.parse import quote as _url_quote
    enc = _url_quote(clean, safe="")
    wreath_src = f"{ASSET_BASE_REL}assets/origin-wreath-gold.svg"
    avatar_src = f"https://github.com/{enc}.png?size={size * 2}"
    identicon = f"https://github.com/identicons/{enc}.png"
    links = ns.get("links", {}) or {}
    repo_url = links.get("github") or links.get("npm") or ""
    is_origin = bool(ns.get("origin"))
    title = f"Origin contributor @{clean}" if is_origin else f"@{clean}"
    # onerror: fall back to the identicon once, then stop (avoid loops). Never
    # set display:none — the frame must never render as an empty hole.
    err_attr = (
        "if(this.dataset.fbk){this.onerror=null;}else{this.dataset.fbk='1';"
        f"this.src='{identicon}';}}"
    )
    img = (
        f'<img class="plaque__avatar-img" src="{html.escape(avatar_src)}" '
        f'alt="" decoding="async" loading="lazy" referrerpolicy="no-referrer" '
        f'onerror="{html.escape(err_attr, quote=True)}">'
    )
    wreath = (
        f'<img class="plaque__avatar-wreath" src="{html.escape(wreath_src)}" '
        f'alt="" aria-hidden="true">'
    )
    inner = img + wreath
    origin_attr = ' data-origin="true"' if is_origin else ""
    style = f'style="--avatar-size:{int(size)}px"'
    if repo_url:
        return (
            f'<a class="plaque__avatar plaque__avatar--link" href="{html.escape(repo_url)}" '
            f'target="_blank" rel="noopener" title="{html.escape(title)}" '
            f'aria-label="{html.escape(title)} — view repository" '
            f'onclick="event.stopPropagation()" {style}{origin_attr}>{inner}</a>'
        )
    return (
        f'<span class="plaque__avatar" title="{html.escape(title)}" '
        f'aria-label="{html.escape(title)}" {style}{origin_attr}>{inner}</span>'
    )


def _field_slug(ns: dict) -> str:
    raw_id = ns.get("id", "")
    slug = html.escape(named_slug(ns))
    safe_id = html.escape(raw_id, quote=True)
    return (
        f'<button type="button" class="plaque__slug plaque-skill-name named-slug" '
        f'data-skill-id="{safe_id}" '
        f'title="{safe_id}" '
        f'onclick="event.stopPropagation(); if(window.openSkillExplorer)window.openSkillExplorer(\'{safe_id}\');">'
        f'{slug}</button>'
    )


def _field_title(ns: dict) -> str:
    title = ns.get("title", "") or ns.get("name", "")
    if not title:
        return ""
    return f'<div class="plaque__title plaque-title">{html.escape(title)}</div>'


def _field_handle_row(ns: dict, rel: str = "../../u/") -> str:
    # Pre-named/demoted (≤1★) skills: redact the plaque handle — slate
    # ".plaque__redacted-handle", never the honor-red named link. The skill,
    # its rank and timeline still render on the owner's own profile.
    if is_redacted(ns.get("level", "")):
        return ('<div class="plaque__handle plaque-contrib-row">'
                '<span class="plaque__redacted-handle" '
                'aria-label="Contributor not yet revealed">@[anonymous]</span></div>')
    contributor_link = handle_link(
        ns.get("contributor", ""),
        rel=rel,
        extra_class="plaque-contributor",
    )
    if not contributor_link:
        return ""
    # Rubric E4: the red inline origin mark is gone — Origin now renders in GOLD
    # as the wreath framing the contributor avatar (_field_avatar sets
    # data-origin). Mirrors docs/js/plaque.js _fieldHandleRow.
    return f'<div class="plaque__handle plaque-contrib-row">{contributor_link}</div>'


def _field_description(ns: dict) -> str:
    desc = ns.get("description", "")
    if not desc:
        return ""
    return f'<p class="plaque__description plaque-description">{html.escape(desc)}</p>'


def _field_tags(ns: dict, limit: int | None = None) -> str:
    tags = ns.get("tags", []) or []
    if limit is not None:
        tags = tags[:limit]
    if not tags:
        return ""
    inner = "".join(
        f'<span class="plaque__tag plaque-tag">{html.escape(t)}</span>' for t in tags
    )
    return f'<div class="plaque__tags plaque-tags">{inner}</div>'


def _field_rank(ns: dict, variant: str = "stars") -> str:
    rb = rank_badge_html(ns.get("level", ""), variant=variant, label=ns.get("level"))
    return f'<div class="plaque__rank">{rb}</div>'


def _field_install_row(ns: dict) -> str:
    skill_id = ns.get("id", "")
    if not skill_id:
        return ""
    cmd = f"gaia install {skill_id}"
    safe_cmd = html.escape(cmd)
    copy_icon = (
        f'<svg class="ico" width="13" height="13" aria-hidden="true">'
        f'<use href="{ICON_SPRITE_REL}#copy"/></svg>'
    )
    return (
        f'<div class="plaque__install-row ns-install-row">'
        f'<span class="plaque__install-prompt ns-install-prompt">$</span>'
        f'<span class="plaque__install-cmd ns-install-cmd-txt">{safe_cmd}</span>'
        f'<button class="plaque__install-copy ns-install-copy" type="button" '
        f'title="Copy install command" data-cmd="{safe_cmd}" '
        f'onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.cmd);">'
        f"{copy_icon}</button></div>"
    )


def _field_gh_link(ns: dict) -> str:
    # Deprecated (rubric E3): the standalone "GitHub" button is removed — the
    # wreathed avatar (_field_avatar) is now the repo link. Kept as a no-op so
    # any lingering call site emits nothing rather than a duplicate link.
    # Mirrors docs/js/plaque.js _fieldGhLink.
    return ""


def _field_origin_star(ns: dict) -> str:
    if not ns.get("origin"):
        return ""
    # SVG sprite-driven origin badge shown inline beside @handle
    return (
        '<span class="plaque__origin ns-origin"'
        ' data-tooltip="Origin contributor: The creator of the first skill version"'
        ' aria-label="Origin contributor">'
        f'<svg class="ico" width="14" height="14" aria-hidden="true">'
        f'<use href="{ICON_SPRITE_REL}#origin-badge"></use></svg>'
        "</span>"
    )


# Public dispatch table: name → builder. Useful for diagnostics and
# for the OG generator to reuse the same slot vocabulary.
PLAQUE_FIELDS = {
    "orb":         _field_orb,
    "avatar":      _field_avatar,
    "slug":        _field_slug,
    "title":       _field_title,
    "handle":      _field_handle_row,
    "description": _field_description,
    "tags":        _field_tags,
    "rank":        _field_rank,
    "install":     _field_install_row,
    "gh":          _field_gh_link,
    "origin":      _field_origin_star,
}


def _plaque_shell(variant: str, ns: dict, inner: str, extra_class: str = "", skill_name: str = "") -> str:
    """Wrap a field-set string in the canonical .plaque shell."""
    n = level_num(ns.get("level", ""))
    apex = " plaque--apex-vi" if n >= 6 else ""
    # Rubric E1/E3: stamp the DERIVED data-branch (standard|suite|unique) — every
    # downstream visual selector (dark unique / gold suite) keys on data-branch,
    # NOT data-type. Legacy data-type (basic|fusion, the raw taxonomy type) is
    # retained only for old hooks; it is NEVER the dead progression enum. Mirrors
    # docs/js/plaque.js _shell().
    legacy_type = html.escape(str(ns.get("type") or "basic"))
    branch = skill_branch(ns)
    extra = f" {extra_class}" if extra_class else ""
    skill_id = html.escape(ns.get("id", ""))
    name_attr = f' data-skill-name="{html.escape(skill_name)}"' if skill_name else ""
    return (
        f'<article class="plaque plaque--{variant}{apex}{extra}" '
        f'data-skill-id="{skill_id}" data-type="{legacy_type}" '
        f'data-branch="{branch}" data-level="{n}"{name_attr}>'
        f"{inner}"
        f"</article>"
    )


def plaque_mini_html(ns: dict) -> str:
    """Stage 3 — Python sibling of window.plaque.renderMini(ns).

    HoH track plate field set: orb · wreathed avatar · handle · rank stars · slug.
    """
    inner = (
        _field_orb(ns)
        + _field_avatar(ns, 28)
        + _field_handle_row(ns)
        + _field_rank(ns, "stars")
        + _field_slug(ns)
    )
    return _plaque_shell("mini", ns, inner)


def plaque_tile_html(ns: dict) -> str:
    """Stage 3 — Python sibling of window.plaque.renderTile(ns).

    Explorer grid card: header(orb + chip + wreathed avatar) · slug · title ·
    handle · description · tags(3) · install row.
    """
    header = (
        '<div class="plaque__header plaque-header">'
        + _field_orb(ns)
        + _field_rank(ns, "chip")
        + _field_avatar(ns, 32)
        + "</div>"
    )
    inner = (
        header
        + _field_slug(ns)
        + _field_title(ns)
        + _field_handle_row(ns)
        + _field_description(ns)
        + _field_tags(ns, 3)
        + _field_install_row(ns)
    )
    return _plaque_shell("tile", ns, inner)


def _plaque_actions_html(ns: dict, handle: str = "") -> str:
    """Build the .plaque__actions block with Share (OG-conditional) and Claim buttons."""
    # Pre-named/demoted (≤1★) skills have no public OG card or badge (those
    # artifacts are intentionally suppressed), so they get no share/claim
    # actions — the plaque still shows the skill, its rank and timeline on the
    # owner's own profile, just without the public-sharing affordances.
    if is_redacted(ns.get("level", "")):
        return ""

    skill_id = ns.get("id", "")
    skill_id_short = skill_id.split("/")[-1] if "/" in skill_id else skill_id
    skill_name = ns.get("title", "") or ns.get("name", "") or skill_id_short

    # Share button — always rendered (OG SVG for inline display; PNG for download)
    share_btn_html = ""
    if handle and skill_id_short:
        og_rel = f"../../og/{handle}/{skill_id_short}.svg"
        share_btn_html = (
            f'<button class="plaque__share-btn" type="button"'
            f' data-skill-id="{html.escape(skill_id)}"'
            f' data-skill-name="{html.escape(skill_name)}"'
            f' data-handle="{html.escape(handle)}"'
            f' data-og="{html.escape(og_rel)}" aria-label="Share">'
            f'<svg class="ico" width="14" height="14" aria-hidden="true">'
            f'<use href="{ICON_SPRITE_REL}#share"></use></svg>'
            f'</button>'
        )

    claim_href = (
        f'../../badges/?u={html.escape(handle)}&s={html.escape(skill_id_short)}'
        if handle
        else '../../badges/'
    )
    claim_btn_html = (
        f'<a class="plaque__claim-btn" '
        f' href="{claim_href}" '
        f' title="Get README badge">Add to README</a>'
    )
    return f'<div class="plaque__actions">{share_btn_html}{claim_btn_html}</div>'


def plaque_settled_html(ns: dict, handle: str = "") -> str:
    """Stage 3 — Python sibling of window.plaque.renderSettled(ns).

    Profile trophy card. Tile field set + rank stars + evidence-class
    chip + gold underline. Produces DOM-equivalent output to the JS
    renderSettled — the explorer modal (detail variant) and the
    profile card (settled variant) read as the same vocabulary.
    """
    header = (
        '<div class="plaque__header plaque-header">'
        + _field_orb(ns)
        + _field_rank(ns, "chip")
        + _field_avatar(ns, 32)
        + "</div>"
    )
    tgVal = ns.get("overallTrustGrade") or ns.get("trustGrade") or ""
    evHtml = ""
    if tgVal and tgVal.lower() != "ungraded":
        evHtml = f'<div class="plaque__evidence plaque-evidence">GRADE {html.escape(tgVal.upper())}</div>'

    inner = (
        header
        + _field_slug(ns)
        + _field_title(ns)
        + _field_handle_row(ns)
        + _field_description(ns)
        + _field_tags(ns, 5)
        + _field_rank(ns, "stars")
        + evHtml
        + '<div class="plaque__underline plaque-underline plaque-underline--settled"></div>'
        + _plaque_actions_html(ns, handle)
    )
    return _plaque_shell("settled", ns, inner, skill_name=ns.get("title", "") or ns.get("name", "") or "")


def build_plaque_card(skill: dict, handle: str = "") -> str:
    """Build a settled plaque card HTML for a named skill.

    Stage 3 — delegates to plaque_settled_html so this code path and
    the JS renderSettled emit the same DOM. The Diamond Seal that
    used to anchor the legacy header is dropped here because the
    settled variant now uses the canonical orb-led header that
    matches the explorer modal's two-column hero.
    """
    return plaque_settled_html(skill, handle=handle)


def _parse_iso_timestamp(ts: str) -> datetime.datetime | None:
    """Parse an ISO 8601 date or date-time string into a datetime object."""
    if not ts:
        return None
    # Normalise trailing Z to +00:00 so fromisoformat works on Python < 3.11
    ts_norm = ts
    if ts_norm.endswith("Z"):
        ts_norm = ts_norm[:-1] + "+00:00"
    try:
        return datetime.datetime.fromisoformat(ts_norm)
    except ValueError:
        # Fall back: try parsing as a plain date
        try:
            d = datetime.date.fromisoformat(ts_norm[:10])
            return datetime.datetime(d.year, d.month, d.day)
        except ValueError:
            return None


def build_activity_log(tree: dict, named_index: dict) -> str:
    """Build an Activity section from tree['timeline'] events.

    Replaces the old Ascension Log. Reads the top-level `timeline[]` on
    the user tree (per skillTree.schema.json), sorts newest-first, and
    renders the last 25 events.
    """
    events = tree.get("timeline", []) if isinstance(tree, dict) else []

    # Sort newest-first; events without parseable timestamps sort to the end
    def _sort_key(ev):
        dt = _parse_iso_timestamp(ev.get("timestamp", ""))
        if dt is None:
            return datetime.datetime.min
        # Make offset-naive for comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt

    sorted_events = sorted(events, key=_sort_key, reverse=True)[:25]

    if not sorted_events:
        return (
            '<section class="profile-section" id="profile-activity">\n'
            '  <h2 class="profile-section-title">Activity</h2>\n'
            '  <p class="profile-section-sub">Recent progression events from this contributor\'s skill tree.</p>\n'
            '  <p class="profile-activity-empty">No recorded activity yet.</p>\n'
            '</section>'
        )

    items = []
    for ev in sorted_events:
        ts = ev.get("timestamp", "")
        action = ev.get("action", "")
        skill_id = ev.get("skillId", "")
        prev_val = ev.get("previousValue")
        new_val = ev.get("newValue", "")

        # Format date as "MMM YYYY"
        dt = _parse_iso_timestamp(ts)
        if dt:
            date_display = dt.strftime("%b %Y")
        else:
            date_display = "—"

        # Display name from named index, or bare id
        ns_entry = named_index.get(skill_id, {})
        display_name = ns_entry.get("name") or ns_entry.get("title") or f"/{skill_id}"
        if not display_name.startswith("/"):
            display_name = f"/{display_name}"

        action_display = html.escape(action.upper().replace("_", " "))
        skill_display = html.escape(display_name)
        safe_skill_id = html.escape(skill_id)
        safe_action = html.escape(action)

        change_html = ""
        if prev_val and new_val:
            change_html = (
                f'<span class="profile-activity-change">'
                f'{html.escape(str(prev_val))} → {html.escape(str(new_val))}</span>'
            )
        elif new_val:
            change_html = (
                f'<span class="profile-activity-change">'
                f'→ {html.escape(str(new_val))}</span>'
            )

        items.append(
            f'    <li class="profile-activity-item" data-action="{safe_action}" data-skill-id="{safe_skill_id}">\n'
            f'      <time class="profile-activity-time" datetime="{html.escape(ts)}">{html.escape(date_display)}</time>\n'
            f'      <span class="profile-activity-action">{action_display}</span>\n'
            f'      <span class="profile-activity-skill">{skill_display}</span>\n'
            f'      {change_html}\n'
            f'    </li>'
        )

    rows_html = "\n".join(items)
    return (
        '<section class="profile-section" id="profile-activity">\n'
        '  <h2 class="profile-section-title">Activity</h2>\n'
        '  <p class="profile-section-sub">Recent progression events from this contributor\'s skill tree.</p>\n'
        '  <ul class="profile-activity-list">\n'
        f'{rows_html}\n'
        '  </ul>\n'
        '</section>'
    )


def build_ascension_log(skills: list) -> str:
    """Deprecated — kept for compatibility. Returns empty string; callers use build_activity_log."""
    return ""


NAV_HTML = """<nav id="site-nav"></nav>
<script src="../../js/mounts.js"></script>
<script src="../../js/site-nav.js"></script>"""

FOOTER_HTML = """<!-- ─── FOOTER ─── -->
<div id="site-footer-mount"></div>
<script src="../../js/site-footer.js"></script>"""


SIDEBAR_HTML = """<aside class="profile-sidebar" id="profileSidebar" aria-label="Filters">
  <!-- Search row with close button -->
  <div class="profile-sidebar-section">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.5rem;">
      <label class="profile-filter-legend" for="profileSearch" style="margin:0;">Search</label>
      <button type="button" class="profile-sidebar-close" id="sidebarCloseBtn" aria-label="Close filters" style="background:none;border:none;color:var(--muted);cursor:pointer;padding:2px;display:inline-flex;align-items:center;"><svg class="ico" width="16" height="16" aria-hidden="true"><use href="../../assets/icons.svg#close-x"/></svg></button>
    </div>
    <input type="search" id="profileSearch" class="sidebar-search-input" placeholder="Search implementations…" autocomplete="off" aria-label="Search skills">
  </div>

  <!-- Branch (Yggdrasil II read-time progression fork; rubric E1) -->
  <fieldset class="profile-filter-group" data-filter-type="branch">
    <legend class="profile-filter-legend">Branch</legend>
    <div style="display:flex; flex-wrap:wrap; gap:0.4rem; width:100%;">
      <button class="profile-filter-chip" type="button" data-value="standard" aria-pressed="false"><span class="tier-glyph" data-branch="standard" aria-hidden="true" style="margin-right:3px">○</span>Standard</button>
      <button class="profile-filter-chip" type="button" data-value="suite" aria-pressed="false"><span class="tier-glyph" data-branch="suite" aria-hidden="true" style="margin-right:3px">◆</span>Suite</button>
      <button class="profile-filter-chip" type="button" data-value="unique" aria-pressed="false"><span class="tier-glyph" data-branch="unique" aria-hidden="true" style="margin-right:3px">◉</span>Unique</button>
    </div>
  </fieldset>

  <!-- Rank -->
  <fieldset class="profile-filter-group" data-filter-type="rank">
    <legend class="profile-filter-legend">Rank</legend>
    <div style="display:flex; flex-wrap:wrap; gap:0.4rem; width:100%;">
      <button class="profile-filter-chip" type="button" data-value="1" aria-pressed="false">1★</button>
      <button class="profile-filter-chip" type="button" data-value="2" aria-pressed="false">2★</button>
      <button class="profile-filter-chip" type="button" data-value="3" aria-pressed="false">3★</button>
      <button class="profile-filter-chip" type="button" data-value="4" aria-pressed="false">4★</button>
      <button class="profile-filter-chip" type="button" data-value="5" aria-pressed="false">5★</button>
      <button class="profile-filter-chip" type="button" data-value="6" aria-pressed="false">6★</button>
    </div>
  </fieldset>

  <!-- Date Range -->
  <div class="profile-sidebar-section">
    <span class="profile-filter-legend" style="float:none; display:block; margin-bottom:0.5rem;">Date Range</span>
    <div class="date-presets" style="margin-bottom:0.75rem;">
      <button class="profile-filter-chip" type="button" data-preset="30d" aria-pressed="false">30D</button>
      <button class="profile-filter-chip" type="button" data-preset="6m" aria-pressed="false">6M</button>
      <button class="profile-filter-chip" type="button" data-preset="all" aria-pressed="true">All</button>
    </div>
    <div style="display:flex; gap:0.5rem; align-items:center;">
      <input type="date" id="profileDateMin" class="sidebar-date-input" aria-label="Minimum date" placeholder="Min">
      <span style="color:var(--muted); font-size:0.7rem;">to</span>
      <input type="date" id="profileDateMax" class="sidebar-date-input" aria-label="Maximum date" placeholder="Max">
    </div>
  </div>

  <!-- Sort -->
  <div class="profile-sidebar-section">
    <label class="profile-filter-legend" for="profileSort" style="float:none; display:block; margin-bottom:0.5rem;">Sort Order</label>
    <div class="ns-sort-wrap profile-sort-wrap" style="width:100%;">
      <svg class="ico ns-sort-icon" width="14" height="14" aria-hidden="true" style="left:10px;"><use href="../../assets/icons.svg#sort-arrows"/></svg>
      <select id="profileSort" class="ns-sort-sel" aria-label="Sort skills" style="width:100%; padding-left:30px; font-family:var(--font-mono); font-size:0.72rem;">
        <option value="rank" selected>Rank · high → low</option>
        <option value="alpha">A → Z</option>
        <option value="branch">Branch</option>
      </select>
    </div>
  </div>

  <!-- Reset -->
  <button class="profile-filter-reset" type="button" style="width:100%; text-align:center; padding:0.5rem; background:var(--bg); border:1px solid var(--border); border-radius:6px; color:var(--muted); font-family:var(--font-mono); font-size:0.72rem; cursor:pointer; transition:color 0.15s, border-color 0.15s;">Reset Filters</button>
</aside>"""


def _build_hoh_modal() -> str:
    """HOH fullscreen share modal — same experience as docs/index.html."""
    ic = ICON_SPRITE_REL
    return f"""<div id="hohFullscreenModal" class="hoh-fs-modal" aria-hidden="true" tabindex="-1">
  <div class="hoh-fs-header">
    <button class="hoh-fs-btn hoh-fs-btn--close" data-fs-action="close" title="Close modal" aria-label="Close modal">
      <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{ic}#close-x"></use></svg>
    </button>
  </div>

  <div class="hoh-fs-stage" id="hohFsStage"></div>

  <div class="hoh-fs-confirm" id="hohFsConfirm" role="group" aria-label="Confirm contributor">
    <span class="hoh-fs-confirm-text">Are you <span id="hohFsHandleText">@handle</span>?</span>
    <button type="button" class="hoh-fs-confirm-btn hoh-fs-confirm-btn--yes" data-fs-action="confirm-yes" aria-label="Yes, this is me">Yes</button>
    <button type="button" class="hoh-fs-confirm-btn hoh-fs-confirm-btn--no" data-fs-action="confirm-no" aria-label="No, dismiss notification">No</button>
  </div>

  <div class="hoh-fs-footer">
    <div class="hoh-dl-wrap" id="hohDlWrap">
      <button class="hoh-fs-btn" data-fs-action="download" title="Download OG Image Card" aria-label="Download OG Image Card" aria-expanded="false" aria-controls="hohDlPopover">
        <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{ic}#download"></use></svg>
      </button>
      <div class="hoh-dl-popover" id="hohDlPopover" role="dialog" aria-label="Choose download format" hidden>
        <div class="hoh-dl-popover-hint">1200&times;630px &middot; For social media sharing</div>
        <button class="hoh-dl-choice" data-dl-format="png" type="button">
          <span class="hoh-dl-choice-fmt">PNG</span>
          <span class="hoh-dl-choice-sub">Recommended</span>
        </button>
        <button class="hoh-dl-choice" data-dl-format="svg" type="button">
          <span class="hoh-dl-choice-fmt">SVG</span>
          <span class="hoh-dl-choice-sub">Vector / lossless</span>
        </button>
      </div>
    </div>
    <button class="hoh-fs-btn" data-fs-action="copy" title="Copy Link" aria-label="Copy Link">
      <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{ic}#link"></use></svg>
    </button>
    <button class="hoh-fs-btn" data-fs-action="x" title="Share on X" aria-label="Share on X">
      <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{ic}#x"></use></svg>
    </button>
    <button class="hoh-fs-btn" data-fs-action="instagram" title="Copy OG Link &amp; Open Instagram" aria-label="Copy OG Link &amp; Open Instagram">
      <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{ic}#instagram"></use></svg>
    </button>
  </div>

  <div class="hoh-fs-overlay" id="hohFsOverlay" hidden>
    <div class="hoh-fs-overlay-header">
      <div class="hoh-fs-overlay-title">Add to your README.md!</div>
      <div class="hoh-fs-overlay-controls">
        <button type="button" class="hoh-fs-overlay-ctl" data-fs-action="overlay-minimize" aria-label="Minimize" title="Minimize">
          <svg class="ico" width="14" height="14" aria-hidden="true" viewBox="0 0 16 16"><path d="M3 12h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        </button>
        <button type="button" class="hoh-fs-overlay-ctl" data-fs-action="overlay-close" aria-label="Close panel" title="Close panel">
          <svg class="ico" width="14" height="14" aria-hidden="true"><use href="{ic}#close-x"></use></svg>
        </button>
      </div>
    </div>
    <div class="hoh-fs-overlay-body">
      <img id="hohFsBadgePreview" class="hoh-fs-badge-img" src="" alt="Gaia contributor badge">
      <div class="hoh-fs-code-wrap">
        <code id="hohFsCodeBlock" class="hoh-fs-code"></code>
        <button id="hohFsCopyBtn" class="hoh-fs-copy-btn hoh-fs-copy-btn--icon" type="button" aria-label="Copy markdown" title="Copy markdown">
          <svg class="ico" width="14" height="14" aria-hidden="true"><use href="{ic}#copy"></use></svg>
        </button>
      </div>
    </div>
    <p id="hohFsDisclaimer" class="hoh-fs-disclaimer">Are you <span class="hoh-fs-disclaimer-handle"></span>? This will only work on <span class="hoh-fs-disclaimer-handle"></span>&rsquo;s repo!</p>
    <div>
      <a id="hohFsBadgesLink" href="../../badges/" class="hoh-fs-copy-btn" style="text-decoration:none;font-size:11px;">
        <svg class="ico" width="12" height="12" aria-hidden="true"><use href="{ic}#seal-diamond"></use></svg> Get all your badges &rarr;
      </a>
    </div>
  </div>

  <button type="button" class="hoh-fs-overlay-restore" id="hohFsOverlayRestore" data-fs-action="overlay-restore" aria-label="Show README panel" hidden>
    <svg class="ico" width="14" height="14" aria-hidden="true"><use href="{ic}#seal-diamond"></use></svg>
    <span>Add to README</span>
  </button>

  <button type="button" class="hoh-fs-fullscreen-btn" data-fs-action="fullscreen" aria-label="Toggle fullscreen" title="Toggle fullscreen">
    <svg class="ico hoh-fs-fullscreen-enter" width="16" height="16" aria-hidden="true" viewBox="0 0 16 16">
      <g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 6V2h4"/><path d="M14 6V2h-4"/>
        <path d="M2 10v4h4"/><path d="M14 10v4h-4"/>
      </g>
    </svg>
    <svg class="ico hoh-fs-fullscreen-exit" width="16" height="16" aria-hidden="true" viewBox="0 0 16 16">
      <g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 2v4H2"/><path d="M10 2v4h4"/>
        <path d="M6 14v-4H2"/><path d="M10 14v-4h4"/>
      </g>
    </svg>
  </button>
</div>"""


def _build_skill_explorer_modal() -> str:
    """One-per-page Skill Explorer modal so /slash-skill clicks open in-place."""
    icon_base = ICON_SPRITE_REL
    return f"""<div id="skillExplorer" class="skill-explorer" role="dialog" aria-modal="true" aria-label="Skill Explorer" tabindex="-1">
    <div class="se-topbar">
      <button id="seBack" class="se-btn-ghost"><svg class="ico" width="16" height="16" aria-hidden="true"><use href="{icon_base}#arrow-back"/></svg> Back</button>
      <span id="seBreadcrumb" class="se-breadcrumb"></span>
      <div class="se-topbar-actions">
        <button id="seOpenRepo" class="se-btn-action"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="{icon_base}#github"/></svg> Repo</button>
        <button id="seSkillDocs" class="se-btn-action"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="{icon_base}#external-link"/></svg> SKILL.md</button>
        <button id="seShare" class="se-btn-action"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="{icon_base}#share"/></svg> Share</button>
        <button id="seTrustReport" class="se-btn-action" title="View full trust report" aria-label="View trust report"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="{icon_base}#info"/></svg> Report</button>
        <button id="seSubmitEvidence" class="se-btn-action" title="Submit evidence for this skill" aria-label="Submit evidence" style="display:none"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="{icon_base}#link"/></svg> Evidence</button>
        <button id="seClose" class="se-btn-ghost se-close-x" aria-label="Close"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="{icon_base}#close-x"/></svg></button>
      </div>
    </div>
    <div class="se-body">
      <div class="se-hero">
        <div id="seHero"></div>
        <div id="se-upgrade" class="se-flow-section"></div>
      </div>
      <div class="se-flow" id="seFlow">
        <div id="se-install" class="se-flow-section"></div>
        <div id="se-docs" class="se-flow-section"></div>
        <div id="se-changelog" class="se-flow-section"></div>
      </div>
    </div>
  </div>"""


def _build_timeline_section(tree: dict, named_index: dict) -> str:
    """Build the Progression Timeline section with embedded JSON payload."""
    unlocked = tree.get("unlockedSkills", []) if isinstance(tree, dict) else []
    timeline_events = tree.get("timeline", []) if isinstance(tree, dict) else []

    skills_payload = []
    for skill in unlocked:
        skill_id = skill.get("skillId") or skill.get("id", "")
        ns_entry = named_index.get(skill_id, {})
        skills_payload.append({
            "id": skill_id,
            "name": ns_entry.get("name") or ns_entry.get("title") or skill_id.split("/")[-1],
            "type": ns_entry.get("type", "basic"),
            "origin": bool(ns_entry.get("origin", False)),
            "levelHistory": skill.get("levelHistory", []),
        })

    timeline_payload = {
        "skills": skills_payload,
        "events": timeline_events,
    }

    # Double-encode: JSON.parse(string) avoids </script> injection risks
    json_data_str = json.dumps(json.dumps(timeline_payload))

    return (
        '<section class="profile-section" id="profile-timeline-section">\n'
        '  <div class="profile-section-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">\n'
        '    <div>\n'
        '      <h2 class="profile-section-title" style="margin:0;">Progression Timeline</h2>\n'
        '      <p class="profile-section-sub" style="margin:0.25rem 0 0 0;">Skill rank progression over time. Hover for details.</p>\n'
        '    </div>\n'
        '    <button class="profile-timeline-filter-btn" id="desktopFilterToggle" aria-label="Toggle filters" style="display:inline-flex; align-items:center; gap:6px; font-family:var(--font-mono); font-size:0.72rem; letter-spacing:0.05em; text-transform:uppercase; background:var(--surface); border:1px solid var(--border); color:var(--text); padding:0.4rem 0.8rem; border-radius:6px; cursor:pointer; transition:border-color 0.15s, color 0.15s;">\n'
        '      <svg class="ico" width="14" height="14" aria-hidden="true" style="fill:currentColor;"><use href="../../assets/icons.svg#filter"/></svg>\n'
        '      <span>Filter</span>\n'
        '    </button>\n'
        '  </div>\n'
        '  <div id="profile-timeline" class="profile-timeline" role="img" aria-label="Skill progression timeline"></div>\n'
        '</section>\n'
        f'<script>window.PROFILE_TIMELINE = JSON.parse({json_data_str});</script>'
    )



def _load_user_tree(handle: str) -> dict:
    """Load a user's skill-tree.json if it exists, else return empty tree dict."""
    tree_path = REPO_ROOT / "skill-trees" / handle / "skill-tree.json"
    if tree_path.exists():
        try:
            with open(tree_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _build_named_index_for_handle(skills: list) -> dict:
    """Build a simple skillId -> entry dict from the named skills list for a contributor."""
    index = {}
    for s in skills:
        skill_id = s.get("id", "")
        if skill_id:
            # strip contributor prefix if present (e.g. "mbtiongson1/web-scrape" -> keyed by both)
            index[skill_id] = s
            if "/" in skill_id:
                bare = skill_id.split("/", 1)[1]
                index[bare] = s
    return index


def build_hero_medallion(handle: str, skills: list) -> str:
    """Build the profile-hero medallion: wreathed GitHub avatar + AOV4 rank stamp.

    N-13 item 4 — the per-user profile hero previously carried only the handle
    and a meta line, so there was no avatar to center. This routes the hero
    through the SAME shared medallion path the plaques use (never a bespoke
    re-implementation): the contributor's GitHub avatar framed by the gold
    origin wreath (_field_avatar) plus the AOV4 rank stamp orb (_field_orb),
    picked from the contributor's highest-ranked named skill so the hero
    reflects their peak standing.

    Returns '' when the contributor has no non-redacted skill (all ≤1★) — a
    redacted contributor exposes no handle, so showing a resolvable avatar
    would leak it (mirrors _field_avatar's own redaction guard).
    """
    # Pick the highest-ranked skill to drive the medallion branch + rank.
    def _rank_key(s: dict) -> int:
        return level_num(s.get("level", ""))

    top = max(skills, key=_rank_key, default=None)
    if not top or is_redacted(top.get("level", "")):
        return ""

    # Synthetic ns carrying the contributor + top skill's rank/branch signal.
    # links omitted so the hero avatar is a non-link portrait (the per-skill
    # plaques below already link each skill to its repo).
    ns = {
        "contributor": handle,
        "level": top.get("level", ""),
        "type": top.get("type", "basic"),
        "suiteComponents": top.get("suiteComponents"),
        "origin": any(s.get("origin") for s in skills),
        "links": {},
    }
    orb = _field_orb(ns, "lg")
    avatar = _field_avatar(ns, 96)
    if not avatar:
        return ""
    return (
        '<div class="profile-hero-medallion">'
        f'{avatar}{orb}'
        '</div>'
    )


def build_profile_page(handle: str, skills: list, named_index: dict | None = None) -> str:
    """Build the full HTML for a contributor profile page."""
    safe_handle = html.escape(handle)
    skill_count = len(skills)
    origin_count = sum(1 for s in skills if s.get("origin"))
    max_level = max((level_num(s.get("level", "")) for s in skills), default=0)
    highest_level = f"{max_level}★" if max_level else "—"

    plaques_html = "\n".join(build_plaque_card(s, handle) for s in skills)

    # Load user's own skill tree for timeline/activity data
    tree = _load_user_tree(handle)

    # Build a named_index keyed by skillId for lookup in activity/timeline sections
    if named_index is None:
        named_index = _build_named_index_for_handle(skills)

    timeline_section_html = _build_timeline_section(tree, named_index)
    hoh_modal_html = _build_hoh_modal()
    skill_explorer_modal_html = _build_skill_explorer_modal()
    hero_medallion_html = build_hero_medallion(handle, skills)

    # OG image tag (vector SVG for social crawlers). Pre-named/demoted skills
    # have no OG card, so pick the first *named* (≥2★) skill; omit the tag
    # entirely when the contributor has no public card yet.
    _og_skill = next((s for s in skills if not is_redacted(s.get("level", ""))), None)
    og_image_tags = (
        f'  <meta property="og:image" content="../../og/{html.escape(handle)}/'
        f'{html.escape(_og_skill["id"].split("/")[-1])}.png">'
        if _og_skill else ""
    )

    page_title = f"@{safe_handle} — Gaia Skill Registry"
    og_description = (
        f"Contributor profile for @{safe_handle} on the Gaia Skill Registry. "
        f"{skill_count} named skill{'s' if skill_count != 1 else ''}, "
        f"highest rank {highest_level}."
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-icon-base="../../assets/icons.svg">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title}</title>
  <meta name="description" content="{html.escape(og_description)}">
  <!-- OG meta -->
  <meta property="og:type" content="profile">
  <meta property="og:title" content="{page_title}">
  <meta property="og:description" content="{html.escape(og_description)}">
  <meta property="og:url" content="https://gaiaskilltree.com/u/{html.escape(handle)}/">
{og_image_tags}
  <!-- Stage 1 — Web fonts (EB Garamond display, Bricolage body, JetBrains Mono fallback). -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="../../css/tokens.css">
  <link rel="stylesheet" href="../../css/styles.css">
  <link rel="stylesheet" href="../../css/plaque.css">
  <!-- Stage 1 — icon sprite helper, loaded BEFORE other UI scripts. -->
  <script src="../../js/icons.js"></script>
  <!-- Stage 2 — rank-badge component, loaded after icons.js. -->
  <script src="../../js/rank-badge.js"></script>
  <!-- Stage 3 — TM config (single source of truth for formulas/RFC), before plaque. -->
  <script src="../../js/tm-config.js"></script>
  <!-- Stage 4 — plaque component family, loaded after tm-config.js. -->
  <script src="../../js/plaque.js"></script>
  <script src="../../js/ui.js" defer></script>
</head>
<body class="profile-page">

  {NAV_HTML}

  <div class="profile-grid-container">
    <main class="profile-main">
      <!-- ─── PROFILE BACK ─── -->
      <div class="profile-back-row">
        <a class="profile-back" href="../" aria-label="Back" onclick="if(history.length>1){{event.preventDefault();history.back();}}">
          <svg class="ico" width="14" height="14" aria-hidden="true"><use href="../../assets/icons.svg#arrow-back"/></svg>
          <span>Back</span>
        </a>
        <a class="profile-back profile-back--alt" href="../" aria-label="View all named contributors">
          <span>View all contributors</span>
          <svg class="ico ico-flip-x" width="14" height="14" aria-hidden="true"><use href="../../assets/icons.svg#arrow-back"/></svg>
        </a>
      </div>

      <!-- ─── PROFILE HERO ─── -->
      <div class="profile-hero">
        {hero_medallion_html}
        <h1 class="profile-handle">{safe_handle}</h1>
        <div class="profile-meta">
          {skill_count} named skill{'s' if skill_count != 1 else ''} · highest rank {highest_level}
        </div>
      </div>

      <!-- ─── PROGRESSION TIMELINE ─── -->
      {timeline_section_html}

      <!-- ─── SKILL PLAQUES ─── -->
      <section class="profile-section">
        <h2 class="profile-section-title">Named Skills</h2>
        <p class="profile-section-sub">All named implementations attributed to @{safe_handle} in the Gaia registry.</p>
        <div class="plaque-grid">
          {plaques_html}
        </div>
      </section>

      <!-- ─── ADD MORE SKILLS CTA ─── -->
      <div class="profile-add-skills-cta">
        <p>Want to add more skills?</p>
        <a href="../../index.html#paths" class="profile-cta-link">Register your repo →</a>
      </div>
    </main>

    {SIDEBAR_HTML}
  </div>

  {FOOTER_HTML}

  <script src="../../js/plaque-reveal.js" defer></script>
  <script src="../../js/profile-timeline.js" defer></script>
  <script src="../../js/profile-filter.js" defer></script>
  <script src="../../js/named-skills.js" defer></script>
  <script src="../../js/skill-explorer.js" defer></script>
  <script src="../../js/hoh-modal.js" defer></script>

  <button id="scrollToTop" class="scroll-to-top" aria-label="Scroll to top">
    <svg class="ico" width="20" height="20" aria-hidden="true"><use href="../../assets/icons.svg#arrow-up"/></svg>
  </button>

  <!-- Floating Mobile Filters Toggle -->
  <div class="profile-sidebar-backdrop" id="sidebarBackdrop"></div>
  <button class="profile-filter-toggle" id="mobileFilterToggle" aria-label="Toggle filters">
    <svg class="ico" width="14" height="14" aria-hidden="true"><use href="../../assets/icons.svg#filter"/></svg>
    <span>Filter</span>
  </button>

  {hoh_modal_html}

  {skill_explorer_modal_html}

</body>
</html>
"""
    return _apply_cache_busting(html_content, _read_version())


def load_named_data(path: Path) -> dict:
    """Load and return named-skills.json data."""
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_by_contributor(data: dict) -> dict:
    """Return dict of handle -> list of skill entries (including awaitingClassification)."""
    by_handle: dict[str, list] = {}

    # Named buckets
    for bucket_skills in data.get("buckets", {}).values():
        for entry in bucket_skills:
            handle = entry.get("contributor", "")
            if not handle:
                continue
            by_handle.setdefault(handle, []).append(entry)

    # awaiting classification — include if they have a contributor
    for entry in data.get("awaitingClassification", []):
        handle = entry.get("contributor", "")
        if not handle:
            continue
        by_handle.setdefault(handle, []).append(entry)

    return by_handle


def _peak_rank_to_tier(peak: int) -> tuple[int, str]:
    """Map a contributor's peak rank (1-6) to a tier index and display label.

    Returns (tier_index, tier_title) where tier_index is 1-4 used for
    data-tier attribute styling. Contributors with peak rank 0 (no rated
    skills yet) are grouped with Tier I — Foundations.
    """
    if peak >= 6:
        return 4, "Tier IV — Apex"
    if peak >= 5:
        return 3, "Tier III — Originators"
    if peak >= 3:
        return 2, "Tier II — Builders"
    return 1, "Tier I — Foundations"


def build_directory_page(by_contributor: dict) -> str:
    """Build the full HTML for the contributors directory page at docs/u/index.html.

    Contributors are grouped into tier sections by their peak rank so visitors
    see Apex/Originators/Builders/Foundations bands rather than a flat wall of
    handles. Cards within each tier are sorted alphabetically by handle.
    """
    total_contributors = len(by_contributor)
    total_skills = sum(len(skills) for skills in by_contributor.values())

    # Group contributors by tier (derived from peak rank). Tier 4 = Apex (6★+),
    # Tier 3 = Originators (5★), Tier 2 = Builders (3-4★), Tier 1 = Foundations (1-2★).
    tier_buckets: dict[int, list[tuple[str, str]]] = {1: [], 2: [], 3: [], 4: []}
    tier_titles: dict[int, str] = {}

    # Sort contributors alphabetically by handle (stable secondary sort)
    for handle, skills in sorted(by_contributor.items(), key=lambda x: x[0].lower()):
        skill_count = len(skills)
        s_suffix = "s" if skill_count != 1 else ""
        origin_count = sum(1 for s in skills if s.get("origin"))
        max_level = max((level_num(s.get("level", "")) for s in skills), default=0)
        highest_level = f"{max_level}★" if max_level else "—"

        # Origin badge HTML if they have any origin skills
        origin_badge_html = ""
        if origin_count > 0:
            origin_badge_html = (
                f'<span class="plaque__origin ns-origin" '
                f'data-tooltip="Origin contributor: The creator of the first skill version" '
                f'aria-label="Origin contributor: The creator of the first skill version">'
                f'<svg class="ico" width="16" height="16" aria-hidden="true">'
                f'<use href="../assets/icons.svg#origin-badge"></use></svg>'
                f'</span>'
            )

        # Rank badge for highest rank reached
        rank_badge_dir_html = ""
        if max_level > 0:
            rank_badge_dir_html = rank_badge_html(f"{max_level}★", variant="chip", size="sm")

        # Top 3 skills preview
        sorted_skills = sorted(skills, key=lambda s: level_num(s.get("level")), reverse=True)[:3]
        skills_preview_parts = []
        skills_list = []
        for s in sorted_skills:
            skill_id = s.get("id", "")
            skill_id_short = skill_id.split("/")[-1] if "/" in skill_id else skill_id
            level = s.get("level", "")
            skills_list.append(skill_id_short)
            
            # Simple small chip
            skills_preview_parts.append(
                f'<span class="dir-skill-chip" data-level="{level_num(level)}">'
                f'/{html.escape(skill_id_short)} {html.escape(level)}'
                f'</span>'
            )
        
        skills_preview_html = "".join(skills_preview_parts)
        skills_list_str = " ".join(skills_list)

        card_html = f"""
    <article class="contributor-card plaque" data-handle="{html.escape(handle)}" data-skills="{html.escape(skills_list_str)}">
      <div class="contributor-card-header">
        <div class="contributor-card-handle-wrap">
          <a class="contributor-card-handle" href="./{html.escape(handle)}/">@{html.escape(handle)}</a>
          {origin_badge_html}
        </div>
        {rank_badge_dir_html}
      </div>
      
      <div class="contributor-card-stats">
        <span class="contributor-stat-item">
          <svg class="ico" width="13" height="13" aria-hidden="true"><use href="../assets/icons.svg#view-tile"/></svg>
          {skill_count} named skill{s_suffix}
        </span>
        <span class="contributor-stat-item contributor-stat-level">
          Highest rank: {html.escape(highest_level)}
        </span>
      </div>

      <div class="contributor-card-skills-preview">
        {skills_preview_html}
      </div>

      <a class="contributor-card-link-btn" href="./{html.escape(handle)}/">
        <span>View Profile</span>
        <svg class="ico" width="12" height="12" aria-hidden="true" style="transform: rotate(180deg);"><use href="../assets/icons.svg#arrow-back"/></svg>
      </a>
    </article>"""
        tier_idx, tier_title = _peak_rank_to_tier(max_level)
        tier_buckets[tier_idx].append((handle, card_html))
        tier_titles[tier_idx] = tier_title

    # Render tier sections, top tier (Apex) first so visitors see the heaviest
    # hitters before scrolling down to Foundations.
    tier_sections = []
    for tier_idx in (4, 3, 2, 1):
        bucket = tier_buckets.get(tier_idx, [])
        if not bucket:
            continue
        title = tier_titles.get(tier_idx, "")
        cards_html = "\n".join(card for _handle, card in bucket)
        tier_sections.append(
            f'    <section class="directory-tier" data-tier="{tier_idx}">\n'
            f'      <h2 class="directory-tier__title">{html.escape(title)}</h2>\n'
            f'      <div class="plaque-grid">\n{cards_html}\n      </div>\n'
            f'    </section>'
        )

    contributors_cards_html = "\n".join(tier_sections)

    NAV_DIR_HTML = """<nav id="site-nav"></nav>
<script src="../js/mounts.js"></script>
<script src="../js/site-nav.js"></script>"""

    FOOTER_DIR_HTML = """<!-- ─── FOOTER ─── -->
<div id="site-footer-mount"></div>
<script src="../js/site-footer.js"></script>"""

    page_title = "Contributors Directory — Gaia Skill Registry"
    og_description = (
        f"Browse the contributors of the Gaia Skill Registry. "
        f"{total_contributors} active builders with {total_skills} named skills claimed."
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-icon-base="../assets/icons.svg">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title}</title>
  <meta name="description" content="{html.escape(og_description)}">
  <!-- OG meta -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="{page_title}">
  <meta property="og:description" content="{html.escape(og_description)}">
  <meta property="og:url" content="https://gaiaskilltree.com/u/">
  <!-- Stage 1 — Web fonts (EB Garamond display, Bricolage body, JetBrains Mono fallback). -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="../css/tokens.css">
  <link rel="stylesheet" href="../css/styles.css">
  <link rel="stylesheet" href="../css/plaque.css">
  <!-- Stage 1 — icon sprite helper, loaded BEFORE other UI scripts. -->
  <script src="../js/icons.js"></script>
  <!-- Stage 2 — rank-badge component, loaded after icons.js. -->
  <script src="../js/rank-badge.js"></script>
  <script src="../js/ui.js" defer></script>
</head>
<body class="profile-directory-page">

  {NAV_DIR_HTML}

  <!-- ─── PROFILE BACK ─── -->
  <div class="profile-back-row">
    <a class="profile-back" href="../" aria-label="Back" onclick="if(history.length>1){{event.preventDefault();history.back();}}">
      <svg class="ico" width="14" height="14" aria-hidden="true"><use href="../assets/icons.svg#arrow-back"/></svg>
      <span>Back</span>
    </a>
  </div>

  <!-- ─── PROFILE HERO ─── -->
  <div class="profile-hero">
    <h1 class="profile-directory-title" style="font-family: var(--font-display); font-size: clamp(2rem, 5vw, 3.2rem); font-weight: 600; color: var(--text); margin-bottom: 0.5rem;">Named Contributors</h1>
    <div class="profile-meta">
      {total_contributors} active builders · {total_skills} named skills claimed
    </div>
  </div>

  <!-- ─── CONTRIBUTORS GRID ─── -->
  <section class="profile-section">
    <div class="directory-controls" style="max-width: 600px; margin: 0 auto 2.5rem; position: relative;">
      <input type="search" id="directorySearch" class="directory-search" aria-label="Search contributors by handle or skills" placeholder="Search contributors or skills…" autocomplete="off">
    </div>

    <div id="contributorGrid">
{contributors_cards_html}
    </div>
  </section>

  {FOOTER_DIR_HTML}

  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const searchInput = document.getElementById('directorySearch');
      const cards = Array.from(document.querySelectorAll('.contributor-card'));
      
      if (searchInput) {{
        searchInput.addEventListener('input', () => {{
          const query = searchInput.value.toLowerCase().trim();
          cards.forEach(card => {{
            const handle = card.getAttribute('data-handle').toLowerCase();
            const skills = card.getAttribute('data-skills').toLowerCase();
            const match = handle.includes(query) || skills.includes(query);
            if (match) {{
              card.removeAttribute('hidden');
            }} else {{
              card.setAttribute('hidden', '');
            }}
          }});
          // Hide tier sections whose cards are all filtered out
          document.querySelectorAll('.directory-tier').forEach(section => {{
            const visible = section.querySelectorAll('.contributor-card:not([hidden])').length;
            if (visible === 0) {{
              section.setAttribute('hidden', '');
            }} else {{
              section.removeAttribute('hidden');
            }}
          }});
        }});
      }}
    }});
  </script>

</body>
</html>
"""
    return _apply_cache_busting(html_content, _read_version())


def generate_pages(named_path: Path, out_dir: Path) -> int:
    """Generate all profile pages. Returns number of pages written."""
    data = load_named_data(named_path)
    by_contributor = collect_by_contributor(data)

    if not by_contributor:
        print("No contributors found in named-skills.json — no pages generated.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for handle, skills in sorted(by_contributor.items()):
        handle_dir = out_dir / handle
        handle_dir.mkdir(parents=True, exist_ok=True)
        page_html = build_profile_page(handle, skills)
        out_file = handle_dir / "index.html"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"  Generated: docs/u/{handle}/index.html ({len(skills)} skill(s))")
        count += 1

    # Generate the main directory page
    dir_html = build_directory_page(by_contributor)
    dir_file = out_dir / "index.html"
    with open(dir_file, "w", encoding="utf-8") as f:
        f.write(dir_html)
    print(f"  Generated: docs/u/index.html ({len(by_contributor)} contributor(s))")

    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate contributor profile pages from named-skills.json"
    )
    parser.add_argument(
        "--named",
        default=str(NAMED_JSON),
        help="Path to named-skills.json (default: registry/named-skills.json)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Output directory for profile pages (default: docs/u/)",
    )
    args = parser.parse_args()

    named_path = Path(args.named)
    out_dir = Path(args.out_dir)

    print(f"Loading named skills from: {named_path}")
    count = generate_pages(named_path, out_dir)
    print(f"\nDone. {count} contributor profile page(s) generated in {out_dir}/")


if __name__ == "__main__":
    main()
