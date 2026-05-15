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


def build_stars(level: str) -> str:
    n = level_num(level)
    parts = []
    for i in range(1, 7):
        cls = "plaque-star" if i <= n else "plaque-star plaque-star--dim"
        parts.append(f'<span class="{cls}">★</span>')
    return "\n".join(parts)


DIAMOND_SEAL_SVG = """<svg class="plaque-seal" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true">
  <path d="M 32 4 L 60 32 L 32 60 L 4 32 Z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/>
  <text x="32" y="34" font-family="EB Garamond,Georgia,serif" font-weight="600" font-size="28" fill="currentColor" text-anchor="middle" dominant-baseline="central">G</text>
</svg>"""


def build_plaque_card(skill: dict) -> str:
    """Build a settled plaque card HTML for a named skill."""
    apex_class = " plaque--apex-vi" if level_num(skill.get("level", "")) >= 6 else ""
    skill_id = html.escape(skill.get("id", ""))
    skill_name = html.escape(skill.get("name", skill.get("id", "Unnamed")))
    title = html.escape(skill.get("title", ""))
    description = html.escape(skill.get("description", ""))
    level = skill.get("level", "")
    tier_type = resolve_type(skill)
    tags = skill.get("tags", [])
    tag_html = "\n".join(
        f'<span class="plaque-tag">{html.escape(t)}</span>'
        for t in tags[:5]
    )

    # Phase 8d — contributor mention is now a hover-underlined link to
    # the contributor's profile page. The href is relative because
    # plaque cards on profile pages live at docs/u/<handle>/index.html
    # and need to reach docs/u/<other>/. Self-links are harmless.
    contributor_link = handle_link(
        skill.get("contributor", ""),
        rel="../../u/",
        extra_class="plaque-contributor",
    )

    # Phase 8d (also Phase C) — render the slash-name slug beneath the
    # skill name in honor red. Falls back to '/<skill-id-tail>' for
    # entries without a contributor/skill split.
    slug = html.escape(named_slug(skill))

    return f"""<div class="plaque plaque--settled{apex_class}" data-skill-id="{skill_id}" data-type="{tier_type}">
  <div class="plaque-header">
    {DIAMOND_SEAL_SVG}
    <div class="plaque-skill-name">{skill_name}</div>
    <div class="plaque-tier">{tier_glyph(level)}</div>
  </div>
  <div class="plaque-named-slug named-slug" title="{skill_id}">{slug}</div>
  {contributor_link}
  {f'<div class="plaque-title">{title}</div>' if title else ''}
  <div class="plaque-stars">
    {build_stars(level)}
  </div>
  <div class="plaque-divider"></div>
  {f'<p class="plaque-description">{description}</p>' if description else ''}
  {f'<div class="plaque-tags">{tag_html}</div>' if tag_html else ''}
  <div class="plaque-evidence">{evidence_class(level)}</div>
  <div class="plaque-underline plaque-underline--settled"></div>
</div>"""


def build_ascension_log(skills: list) -> str:
    """Build ascension log rows for all skills."""
    rows = []
    for skill in sorted(skills, key=lambda s: -level_num(s.get("level", ""))):
        skill_id = html.escape(skill.get("id", ""))
        level = html.escape(skill.get("level", "—"))
        generic_ref = html.escape(skill.get("genericSkillRef", skill.get("id", "")))
        rows.append(f"""<div class="ascension-log-row">
  <span class="al-date">—</span>
  <span class="al-action">NAMED</span>
  <span class="al-skill">{skill_id}</span>
  <span class="al-level">{level}</span>
</div>""")
    if not rows:
        return '<div class="ascension-log-row"><span style="color:var(--muted);font-size:.85rem">No entries yet.</span></div>'
    return "\n".join(rows)


NAV_HTML = """<nav>
  <a href="../../" class="nav-logo" aria-label="Gaia home">
    <svg class="nav-seal" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <path d="M 32 4 L 60 32 L 32 60 L 4 32 Z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/>
      <text x="32" y="34" font-family="EB Garamond, Georgia, serif" font-weight="600" font-size="28" fill="currentColor" text-anchor="middle" dominant-baseline="central">G</text>
    </svg>
    <span class="nav-wordmark">Gaia</span>
    </a>
    <button type="button" class="nav-search-back" id="navSearchBack" aria-label="Back">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
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
    <li><a href="../../#tree" class="nav-tree">Tree</a></li>
    <li><a href="../../#search" class="nav-search-btn" aria-label="Search skills"><svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="7" cy="7" r="5"/><path d="M11 11l3.5 3.5"/></svg></a></li>
  </ul>
</nav>"""

FOOTER_HTML = """<footer>
  <div class="footer-mark">
    <svg class="footer-seal" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <path d="M 32 4 L 60 32 L 32 60 L 4 32 Z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/>
      <text x="32" y="34" font-family="EB Garamond, Georgia, serif" font-weight="600" font-size="28" fill="currentColor" text-anchor="middle" dominant-baseline="central">G</text>
    </svg>
    <span class="footer-wordmark">Gaia</span>
  </div>
  <p>
    <a href="https://github.com/mbtiongson1/gaia-skill-tree" target="_blank">GitHub</a> ·
    MIT ·
    <a href="../../codex.html">The Codex</a>
  </p>
</footer>"""


def build_profile_page(handle: str, skills: list) -> str:
    """Build the full HTML for a contributor profile page."""
    safe_handle = html.escape(handle)
    skill_count = len(skills)
    origin_count = sum(1 for s in skills if s.get("origin"))
    max_level = max((level_num(s.get("level", "")) for s in skills), default=0)
    highest_level = f"{max_level}★" if max_level else "—"

    plaques_html = "\n".join(build_plaque_card(s) for s in skills)
    log_html = build_ascension_log(skills)

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

    return f"""<!DOCTYPE html>
<html lang="en">
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
  <!-- Fonts & styles -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../../css/styles.css">
  <link rel="stylesheet" href="../../css/plaque.css">
</head>
<body class="profile-page">

  {NAV_HTML}

  <!-- ─── PROFILE HERO ─── -->
  <div class="profile-hero">
    <h1 class="profile-handle">{safe_handle}</h1>
    <div class="profile-meta">
      {skill_count} named skill{'s' if skill_count != 1 else ''} · highest rank {highest_level}
    </div>
    {f'<span class="profile-origin-badge">◆ Origin Contributor · {origin_count} origin{"s" if origin_count != 1 else ""}</span>' if origin_count else ''}
  </div>

  <!-- ─── SKILL PLAQUES ─── -->
  <section class="profile-section">
    <h2 class="profile-section-title">Named Skills</h2>
    <p class="profile-section-sub">All named implementations attributed to @{safe_handle} in the Gaia registry.</p>
    <div class="plaque-grid">
      {plaques_html}
    </div>
  </section>

  <!-- ─── ASCENSION LOG ─── -->
  <section class="profile-section">
    <h2 class="profile-section-title">Ascension Log</h2>
    <p class="profile-section-sub">Registry events attributed to this contributor, in descending rank order.</p>
    <div class="ascension-log">
      <div class="ascension-log-header">Date · Action · Skill ID · Level</div>
      {log_html}
    </div>
  </section>

  {FOOTER_HTML}

  <script src="../../js/plaque-reveal.js" defer></script>

  <button id="scrollToTop" class="scroll-to-top" aria-label="Scroll to top">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6"/></svg>
  </button>

</body>
</html>
"""


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
