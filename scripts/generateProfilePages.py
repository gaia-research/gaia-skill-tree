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
from _atlas_helpers import handle_link, named_slug  # noqa: E402


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


def load_type_lookup(gaia_path: Path) -> dict:
    """Return a dict mapping canonical skill id → type (ultimate/unique/extra/basic)."""
    if not gaia_path.exists():
        return {}
    with open(gaia_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s.get("id"): s.get("type", "basic") for s in data.get("skills", [])}


TYPE_LOOKUP: dict = {}


def resolve_type(entry: dict) -> str:
    """Resolve the canonical type for a named-skill entry, with slug fallback."""
    ref = entry.get("genericSkillRef")
    if ref and ref in TYPE_LOOKUP:
        return TYPE_LOOKUP[ref]
    raw_id = entry.get("id", "")
    if "/" in raw_id:
        slug = raw_id.split("/", 1)[1]
        if slug in TYPE_LOOKUP:
            return TYPE_LOOKUP[slug]
    return "basic"


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
DIAMOND_SEAL_SVG = (
    f'<svg class="ico plaque-seal" aria-hidden="true">'
    f'<use href="{ICON_SPRITE_REL}#seal-diamond"/></svg>'
)


# Stage 3 — Python sibling field helpers. One source of truth per
# field across all three variants Python emits (--mini, --tile,
# --settled) so the server-rendered DOM matches docs/js/plaque.js
# exactly. The dict below names every slot and the lambda that
# emits it; the variant functions below assemble them.
def _field_orb(ns: dict, size_modifier: str = "") -> str:
    type_str = resolve_type(ns)
    n = level_num(ns.get("level", ""))
    mod = f" plaque-orb--{size_modifier}" if size_modifier else ""
    apex = " plaque-orb--vi" if n >= 6 else ""
    return f'<div class="plaque-orb plaque-orb--{type_str}{mod}{apex}" aria-hidden="true"></div>'


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
    contributor_link = handle_link(
        ns.get("contributor", ""),
        rel=rel,
        extra_class="plaque-contributor",
    )
    if not contributor_link:
        return ""
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
    links = ns.get("links", {}) or {}
    url = links.get("github") or links.get("npm") or ""
    if not url:
        return ""
    gh_icon = (
        f'<svg class="ico" width="14" height="14" aria-hidden="true">'
        f'<use href="{ICON_SPRITE_REL}#github"/></svg>'
    )
    return (
        f'<a class="plaque__gh-link ns-gh-link" href="{html.escape(url)}" '
        f'target="_blank" rel="noopener" onclick="event.stopPropagation()" '
        f'title="View on GitHub">{gh_icon}</a>'
    )


def _field_origin_star(ns: dict) -> str:
    if not ns.get("origin"):
        return ""
    # Stage 4 — SVG sprite-driven origin badge, mirrors plaque.js _fieldOriginBadge exactly.
    return (
        '<span class="plaque__origin ns-origin"'
        ' data-tooltip="Origin contributor: The creator of the first skill version"'
        ' aria-label="Origin contributor: The creator of the first skill version">'
        f'<svg class="ico" width="16" height="16" aria-hidden="true">'
        f'<use href="{ICON_SPRITE_REL}#origin-badge"></use></svg>'
        '<span class="origin-info" style="margin-left:3px;color:var(--muted);opacity:.7">'
        f'<svg class="ico" width="10" height="10" aria-hidden="true">'
        f'<use href="{ICON_SPRITE_REL}#info"></use></svg>'
        "</span>"
        "</span>"
    )


# Public dispatch table: name → builder. Useful for diagnostics and
# for the OG generator to reuse the same slot vocabulary.
PLAQUE_FIELDS = {
    "orb":         _field_orb,
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
    type_str = resolve_type(ns)
    extra = f" {extra_class}" if extra_class else ""
    skill_id = html.escape(ns.get("id", ""))
    name_attr = f' data-skill-name="{html.escape(skill_name)}"' if skill_name else ""
    return (
        f'<article class="plaque plaque--{variant}{apex}{extra}" '
        f'data-skill-id="{skill_id}" data-type="{type_str}" data-level="{n}"{name_attr}>'
        f"{inner}"
        f"</article>"
    )


def plaque_mini_html(ns: dict) -> str:
    """Stage 3 — Python sibling of window.plaque.renderMini(ns).

    HoH track plate field set: orb · slug · handle · rank stars.
    """
    inner = (
        _field_orb(ns)
        + _field_slug(ns)
        + _field_handle_row(ns)
        + _field_rank(ns, "stars")
    )
    return _plaque_shell("mini", ns, inner)


def plaque_tile_html(ns: dict) -> str:
    """Stage 3 — Python sibling of window.plaque.renderTile(ns).

    Explorer grid card: header(orb+chip+origin+gh) · slug · title ·
    handle · description · tags(3) · install row.
    """
    header = (
        '<div class="plaque__header plaque-header">'
        + _field_orb(ns)
        + _field_rank(ns, "chip")
        + _field_origin_star(ns)
        + _field_gh_link(ns)
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
    skill_id = ns.get("id", "")
    skill_id_short = skill_id.split("/")[-1] if "/" in skill_id else skill_id
    skill_name = ns.get("title", "") or ns.get("name", "") or skill_id_short

    # Share button — always rendered (OG PNG may be generated later)
    share_btn_html = ""
    if handle and skill_id_short:
        og_rel = f"../../og/{handle}/{skill_id_short}.png"
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

    claim_href = f'../../badges/?u={html.escape(handle)}' if handle else '../../badges/'
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
        + _field_origin_star(ns)
        + _field_gh_link(ns)
        + "</div>"
    )
    inner = (
        header
        + _field_slug(ns)
        + _field_title(ns)
        + _field_handle_row(ns)
        + _field_description(ns)
        + _field_tags(ns, 5)
        + _field_rank(ns, "stars")
        + f'<div class="plaque__evidence plaque-evidence">{html.escape(evidence_class(ns.get("level", "")))}</div>'
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


NAV_HTML = f"""<nav>
  <a href="../../" class="nav-logo" aria-label="Gaia home">
    <svg class="ico nav-seal" aria-hidden="true" focusable="false"><use href="{ICON_SPRITE_REL}#seal-diamond"/></svg>
    <span class="nav-wordmark">Gaia</span>
    </a>
    <button type="button" class="nav-search-back" id="navSearchBack" aria-label="Back">
      <svg class="ico" width="20" height="20" aria-hidden="true"><use href="{ICON_SPRITE_REL}#arrow-back"/></svg>
    </button>
    <input type="search" id="navMobileSearch" class="nav-mobile-search" placeholder="Search skills…" autocomplete="off" aria-label="Search skills">
    <button class="nav-menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false">    <span></span>
    <span></span>
    <span></span>
  </button>
  <ul>
    <li><a href="../../#paths">Registry</a></li>
    <li><a href="../../#hall-of-heroes">Hall of Heroes</a></li>
    <li><a href="../../codex.html">The Codex</a></li>
    <li><a href="../../badges/" style="color: var(--honor-red);">Badges</a></li>
    <li><a href="../../#tree" class="nav-tree">Tree</a></li>
    <li><a href="../../#search" class="nav-search-btn" aria-label="Search skills"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="{ICON_SPRITE_REL}#search"/></svg></a></li>
  </ul>
</nav>"""

FOOTER_HTML = f"""<footer>
  <div class="footer-mark">
    <svg class="ico footer-seal" aria-hidden="true" focusable="false"><use href="{ICON_SPRITE_REL}#seal-diamond"/></svg>
    <span class="footer-wordmark">Gaia</span>
  </div>
  <p>
    <a href="https://github.com/mbtiongson1/gaia-skill-tree" target="_blank">GitHub</a> ·
    MIT ·
    <a href="../../codex.html">The Codex</a>
  </p>
</footer>"""


SIDEBAR_HTML = """<aside class="profile-sidebar" id="profileSidebar" aria-label="Filters">
  <!-- Search -->
  <div class="profile-sidebar-section">
    <label class="profile-filter-legend" for="profileSearch" style="float:none; display:block; margin-bottom:0.5rem;">Search</label>
    <input type="search" id="profileSearch" class="sidebar-search-input" placeholder="Search implementations…" autocomplete="off" aria-label="Search skills">
  </div>

  <!-- Type -->
  <fieldset class="profile-filter-group" data-filter-type="type">
    <legend class="profile-filter-legend">Type</legend>
    <div style="display:flex; flex-wrap:wrap; gap:0.4rem; width:100%;">
      <button class="profile-filter-chip" type="button" data-value="basic" aria-pressed="false">Basic</button>
      <button class="profile-filter-chip" type="button" data-value="extra" aria-pressed="false">Extra</button>
      <button class="profile-filter-chip" type="button" data-value="unique" aria-pressed="false">Unique</button>
      <button class="profile-filter-chip" type="button" data-value="ultimate" aria-pressed="false">Ultimate</button>
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
        <option value="type">Type</option>
      </select>
    </div>
  </div>

  <!-- Reset -->
  <button class="profile-filter-reset" type="button" style="width:100%; text-align:center; padding:0.5rem; background:var(--bg); border:1px solid var(--border); border-radius:6px; color:var(--muted); font-family:var(--font-mono); font-size:0.72rem; cursor:pointer; transition:color 0.15s, border-color 0.15s;">Reset Filters</button>
</aside>"""


def _build_share_modal() -> str:
    """Build the one-per-page share modal markup."""
    icon_base = ICON_SPRITE_REL
    return f"""<div class="share-modal" hidden role="dialog" aria-modal="true" aria-labelledby="share-modal-title">
  <div class="share-modal__backdrop" data-share-close></div>
  <div class="share-modal__panel" role="document">
    <button class="share-modal__close" type="button" data-share-close aria-label="Close">×</button>
    <h2 id="share-modal-title" class="share-modal__title">Share</h2>
    <p class="share-modal__caption" data-share-caption></p>
    <img class="share-modal__preview" data-share-preview alt="OG card preview">
    <div class="share-modal__actions">
      <a class="share-action share-action--download" data-share-action="download" download>
        <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{icon_base}#download"></use></svg> Download
      </a>
      <button class="share-action share-action--copy" type="button" data-share-action="copy">
        <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{icon_base}#link"></use></svg> Copy link
      </button>
      <a class="share-action share-action--x" data-share-action="x" target="_blank" rel="noopener">
        <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{icon_base}#x"></use></svg> X
      </a>
      <button class="share-action share-action--instagram" type="button" data-share-action="instagram">
        <svg class="ico" width="16" height="16" aria-hidden="true"><use href="{icon_base}#instagram"></use></svg> Instagram
      </button>
    </div>
    <div class="share-modal__toast" hidden role="status" data-share-toast></div>
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

    activity_section_html = build_activity_log(tree, named_index)
    timeline_section_html = _build_timeline_section(tree, named_index)
    share_modal_html = _build_share_modal()

    # OG image tag (raster PNG for social crawlers; SVG sibling exists at the same path)
    og_image_tags = "\n".join(
        f'  <meta property="og:image" content="../../og/{html.escape(handle)}/{html.escape(s["id"].split("/")[-1])}.png">'
        for s in skills[:1]  # use first skill for og:image
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
  <meta property="og:url" content="https://mbtiongson1.github.io/gaia-skill-tree/u/{html.escape(handle)}/">
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
  <!-- Stage 3 — plaque component family, loaded after rank-badge.js. -->
  <script src="../../js/plaque.js"></script>
  <script src="../../js/ui.js" defer></script>
</head>
<body class="profile-page">

  {NAV_HTML}

  <div class="profile-grid-container">
    <main class="profile-main">
      <!-- ─── PROFILE BACK ─── -->
      <div class="profile-back-row">
        <a class="profile-back" href="../" aria-label="Back" onclick="event.preventDefault(); history.back();">
          <svg class="ico" width="14" height="14" aria-hidden="true"><use href="../../assets/icons.svg#arrow-back"/></svg>
          <span>Back</span>
        </a>
      </div>

      <!-- ─── PROFILE HERO ─── -->
      <div class="profile-hero">
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

      <!-- ─── ACTIVITY LOG ─── -->
      {activity_section_html}
    </main>

    {SIDEBAR_HTML}
  </div>

  {FOOTER_HTML}

  <script src="../../js/plaque-reveal.js" defer></script>
  <script src="../../js/profile-timeline.js" defer></script>
  <script src="../../js/profile-filter.js" defer></script>
  <script src="../../js/profile-share.js" defer></script>
  <script src="../../js/profile-claim.js" defer></script>
  <script src="../../js/named-skills.js" defer></script>
  <script src="../../js/skill-explorer.js" defer></script>

  <button id="scrollToTop" class="scroll-to-top" aria-label="Scroll to top">
    <svg class="ico" width="20" height="20" aria-hidden="true"><use href="../../assets/icons.svg#arrow-up"/></svg>
  </button>

  <!-- Floating Mobile Filters Toggle -->
  <div class="profile-sidebar-backdrop" id="sidebarBackdrop"></div>
  <button class="profile-filter-toggle" id="mobileFilterToggle" aria-label="Toggle filters">
    <svg class="ico" width="14" height="14" aria-hidden="true"><use href="../../assets/icons.svg#filter"/></svg>
    <span>Filters</span>
  </button>

  {share_modal_html}

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

    NAV_DIR_HTML = f"""<nav>
  <a href="../" class="nav-logo" aria-label="Gaia home">
    <svg class="ico nav-seal" aria-hidden="true" focusable="false"><use href="../assets/icons.svg#seal-diamond"/></svg>
    <span class="nav-wordmark">Gaia</span>
    </a>
    <button type="button" class="nav-search-back" id="navSearchBack" aria-label="Back">
      <svg class="ico" width="20" height="20" aria-hidden="true"><use href="../assets/icons.svg#arrow-back"/></svg>
    </button>
    <input type="search" id="navMobileSearch" class="nav-mobile-search" placeholder="Search skills…" autocomplete="off" aria-label="Search skills">
    <button class="nav-menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false">
    <span></span>
    <span></span>
    <span></span>
  </button>
  <ul>
    <li><a href="../#paths">Registry</a></li>
    <li><a href="../#hall-of-heroes">Hall of Heroes</a></li>
    <li><a href="../codex.html">The Codex</a></li>
    <li><a href="../badges/" style="color: var(--honor-red);">Badges</a></li>
    <li><a href="../#tree" class="nav-tree">Tree</a></li>
    <li><a href="../#search" class="nav-search-btn" aria-label="Search skills"><svg class="ico" width="14" height="14" aria-hidden="true"><use href="../assets/icons.svg#search"/></svg></a></li>
  </ul>
</nav>"""

    FOOTER_DIR_HTML = f"""<footer>
  <div class="footer-mark">
    <svg class="ico footer-seal" aria-hidden="true" focusable="false"><use href="../assets/icons.svg#seal-diamond"/></svg>
    <span class="footer-wordmark">Gaia</span>
  </div>
  <p>
    <a href="https://github.com/mbtiongson1/gaia-skill-tree" target="_blank">GitHub</a> ·
    MIT ·
    <a href="../codex.html">The Codex</a>
  </p>
</footer>"""

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
  <meta property="og:url" content="https://mbtiongson1.github.io/gaia-skill-tree/u/">
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
    <a class="profile-back" href="../" aria-label="Back">
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
    global TYPE_LOOKUP
    TYPE_LOOKUP = load_type_lookup(GAIA_JSON)
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
