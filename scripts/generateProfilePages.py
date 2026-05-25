#!/usr/bin/env python3
"""Gaia Skill Registry — Contributor Profile Page Generator.

Reads registry/named-skills.json and generates static HTML contributor
profile pages at docs/u/{handle}/index.html.

Each page shows:
  - Contributor handle (honor red)
  - Origin contributor badge (SVG #1 laurel badge) + skill count
  - Sortable grid of settled plaque cards (one per named skill)
  - Ascension log with real dates from createdAt
  - Interactive JS progression timeline

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
import re
from pathlib import Path
import datetime

REPO_ROOT   = Path(__file__).resolve().parent.parent
NAMED_JSON  = REPO_ROOT / "registry" / "named-skills.json"
GAIA_JSON   = REPO_ROOT / "registry" / "gaia.json"
DOCS_DIR    = REPO_ROOT / "docs"
OUT_DIR     = DOCS_DIR / "u"
ICON_BASE   = "../../assets/icons.svg"   # relative from docs/u/{handle}/


# ── helpers ───────────────────────────────────────────────────────────

def _read_version() -> str:
    pyproject = REPO_ROOT / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.startswith("version = "):
                return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def _apply_cache_busting(text: str, version: str) -> str:
    cache_meta = (
        '\n  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n'
        '  <meta http-equiv="Pragma" content="no-cache">\n'
        '  <meta http-equiv="Expires" content="0">'
    )
    if 'http-equiv="Cache-Control"' not in text:
        text = text.replace("<head>", f"<head>{cache_meta}", 1)

    version_script = f'\n  <script>window.GAIA_VERSION = "{version}";</script>'
    if "window.GAIA_VERSION" in text:
        text = re.sub(
            r'<script>\s*window\.GAIA_VERSION\s*=\s*"[^"]*";\s*</script>',
            f'<script>window.GAIA_VERSION = "{version}";</script>', text,
        )
    else:
        text = text.replace("<head>", f"<head>{version_script}", 1)

    text = re.sub(
        r'href="((?:\.\./)*)css/([^"?]+\.css)(?:\?v=[^"]*)?"',
        fr'href="\1css/\2?v={version}"', text,
    )
    text = re.sub(
        r'src="((?:\.\./)*)js/([^"?]+\.js)(?:\?v=[^"]*)?"',
        fr'src="\1js/\2?v={version}"', text,
    )
    return text


def load_type_lookup(gaia_path: Path) -> dict:
    if not gaia_path.exists():
        return {}
    with open(gaia_path, encoding="utf-8") as f:
        data = json.load(f)
    return {s.get("id"): s.get("type", "basic") for s in data.get("skills", [])}


TYPE_LOOKUP: dict = {}


def resolve_type(entry: dict) -> str:
    ref = entry.get("genericSkillRef", "")
    t   = TYPE_LOOKUP.get(ref) or TYPE_LOOKUP.get(entry.get("id", ""))
    if not t:
        t = entry.get("type", "basic")
    return t or "basic"


def level_num(level: str) -> int:
    if not level:
        return 0
    m = re.search(r"(\d+)", str(level))
    return int(m.group(1)) if m else 0


def evidence_class(level: str) -> str:
    n = level_num(level)
    if n >= 4:
        return "CLASS A"
    if n == 3:
        return "CLASS B"
    if n == 2:
        return "CLASS C"
    return "AWAITED"


def fmt_date(iso: str) -> str:
    """Format ISO date string as 'Apr 2026'."""
    if not iso or iso == "—":
        return "—"
    try:
        d = datetime.date.fromisoformat(iso[:10])
        return d.strftime("%b %Y")
    except ValueError:
        return iso[:7] if len(iso) >= 7 else iso


def _icon(icon_id: str, size: int) -> str:
    return (
        f'<svg class="ico" width="{size}" height="{size}" aria-hidden="true" focusable="false">'
        f'<use href="{ICON_BASE}#{icon_id}"/></svg>'
    )


# ── field builders (match plaque.js exactly) ──────────────────────────

TAG_PALETTE = [
    ("#38bdf8", "rgba(56,189,248,.12)",  "rgba(56,189,248,.3)"),
    ("#c084fc", "rgba(192,132,252,.12)", "rgba(192,132,252,.3)"),
    ("#63cab7", "rgba(99,202,183,.12)",  "rgba(99,202,183,.3)"),
    ("#a78bfa", "rgba(167,139,250,.12)", "rgba(167,139,250,.3)"),
    ("#f59e0b", "rgba(245,158,11,.12)",  "rgba(245,158,11,.3)"),
    ("#e879f9", "rgba(232,121,249,.12)", "rgba(232,121,249,.3)"),
]

RANK_COLORS = {
    0: ("#94a3b8", "rgba(100,116,139,.15)", "rgba(100,116,139,.4)"),
    1: ("#38bdf8", "rgba(56,189,248,.15)",  "rgba(56,189,248,.4)"),
    2: ("#63cab7", "rgba(99,202,183,.15)",  "rgba(99,202,183,.4)"),
    3: ("#a78bfa", "rgba(167,139,250,.15)", "rgba(167,139,250,.4)"),
    4: ("#e879f9", "rgba(232,121,249,.15)", "rgba(232,121,249,.4)"),
    5: ("#fbbf24", "rgba(251,191,36,.15)",  "rgba(251,191,36,.4)"),
    6: ("#fbbf24", "rgba(251,191,36,.22)",  "rgba(251,191,36,.55)"),
}


def _tag_color(tag: str) -> tuple:
    h = 0
    for c in tag:
        h = (h * 31 + ord(c)) % len(TAG_PALETTE)
    return TAG_PALETTE[h]


def _field_orb(ns: dict) -> str:
    typ = resolve_type(ns)
    return f'<div class="plaque-orb" data-type="{html.escape(typ)}"></div>'


def _field_rank_chip(ns: dict) -> str:
    n = level_num(ns.get("level", ""))
    c, bg, bd = RANK_COLORS.get(n, RANK_COLORS[0])
    return (
        f'<span class="rank-chip" style="color:{c};background:{bg};border:1px solid {bd}">'
        f'{n}★</span>'
    )


def _field_rank_stars(ns: dict) -> str:
    n = level_num(ns.get("level", ""))
    stars = "".join(
        f'<span class="rank-star{" filled" if i <= n else ""}">★</span>'
        for i in range(1, 7)
    )
    return f'<span class="rank-stars">{stars}</span>'


def _field_origin_badge(ns: dict) -> str:
    """Render the #1 laurel SVG origin badge — matches plaque.js _fieldOriginBadge()."""
    if not ns.get("origin"):
        return ""
    icon_svg  = _icon("origin-badge", 16)
    info_svg  = (
        f'<span class="origin-info" style="margin-left:2px;color:var(--muted);opacity:.65">'
        f'{_icon("info", 10)}</span>'
    )
    return (
        f'<span class="plaque__origin" '
        f'data-tooltip="Origin contributor: The creator of the first skill version" '
        f'aria-label="Origin contributor">{icon_svg}{info_svg}</span>'
    )


def _field_gh_link(ns: dict) -> str:
    links = ns.get("links", {})
    url = links.get("github") or links.get("npm") or ""
    if not url:
        return ""
    icon_svg = _icon("github", 14)
    return (
        f'<a class="plaque__gh-link" href="{html.escape(url)}" target="_blank" '
        f'rel="noopener" onclick="event.stopPropagation()" title="View on GitHub">'
        f'{icon_svg}</a>'
    )


def _field_share_btn(ns: dict) -> str:
    icon_svg = _icon("share", 14)
    skill_id = html.escape(ns.get("id", ""))
    name     = html.escape(ns.get("name", ns.get("id", "")))
    return (
        f'<button class="plaque__share-btn" type="button" '
        f'aria-label="Share {name}" data-skill-id="{skill_id}" '
        f'onclick="event.stopPropagation();profileShare.open(this)">'
        f'{icon_svg}</button>'
    )


def _field_slug(ns: dict) -> str:
    slug = "/" + html.escape(str(ns.get("id", "")).split("/")[-1])
    return f'<div class="plaque__slug">{slug}</div>'


def _field_title(ns: dict) -> str:
    name = html.escape(ns.get("name") or str(ns.get("id", "")).split("/")[-1])
    return f'<div class="plaque__title">{name}</div>'


def _field_handle(ns: dict) -> str:
    h = html.escape(ns.get("contributor", ""))
    return f'<div class="plaque__handle">by <a href="../../u/{h}/">@{h}</a></div>'


def _field_description(ns: dict) -> str:
    desc = ns.get("description", "")
    if not desc:
        return ""
    short = desc[:220] + ("…" if len(desc) > 220 else "")
    return f'<p class="plaque__description">{html.escape(short)}</p>'


def _field_tags(ns: dict, max_tags: int = 5) -> str:
    raw = ns.get("tags") or []
    tags = list(raw) if not isinstance(raw, list) else raw
    tags = tags[:max_tags]
    if not tags:
        return ""
    spans = []
    for t in tags:
        c, bg, bd = _tag_color(t)
        spans.append(
            f'<span class="plaque__tag" style="color:{c};background:{bg};border-color:{bd}">'
            f'{html.escape(t)}</span>'
        )
    return f'<div class="plaque__tags">{"".join(spans)}</div>'


def _field_evidence(ns: dict) -> str:
    return f'<div class="plaque__evidence">{evidence_class(ns.get("level", ""))}</div>'


def _field_install(ns: dict) -> str:
    skill_id = ns.get("id", "")
    if not skill_id:
        return ""
    cmd = f"gaia install {skill_id}"
    copy_click = (
        "event.stopPropagation();"
        "if(typeof window.nsInstCopy==='function'){window.nsInstCopy(this);}"
        "else{navigator.clipboard.writeText(this.dataset.cmd);}"
    )
    return (
        f'<div class="plaque__install-row">'
        f'<span class="plaque__install-prompt">$</span>'
        f'<span class="plaque__install-cmd">{html.escape(cmd)}</span>'
        f'<button class="plaque__install-copy" type="button" aria-label="Copy" '
        f'title="Copy install command" data-cmd="{html.escape(cmd)}" '
        f'onclick="{html.escape(copy_click)}">{_icon("copy", 13)}</button>'
        f'</div>'
    )


# ── plaque shell ───────────────────────────────────────────────────────

def _plaque_shell(variant: str, ns: dict, inner: str) -> str:
    n      = level_num(ns.get("level", ""))
    apex   = " plaque--apex-vi" if n >= 6 else ""
    typ    = html.escape(resolve_type(ns))
    sid    = html.escape(ns.get("id", ""))
    return (
        f'<article class="plaque plaque--{variant}{apex}" '
        f'data-skill-id="{sid}" data-type="{typ}" data-level="{n}">'
        f'{inner}</article>'
    )


def plaque_settled_html(ns: dict) -> str:
    """Settled profile trophy card — mirrors plaque.js renderSettled()."""
    header = (
        '<div class="plaque__header">'
        + _field_orb(ns)
        + _field_rank_chip(ns)
        + _field_origin_badge(ns)
        + _field_gh_link(ns)
        + _field_share_btn(ns)
        + "</div>"
    )
    inner = (
        header
        + _field_slug(ns)
        + _field_title(ns)
        + _field_handle(ns)
        + _field_description(ns)
        + _field_tags(ns, 5)
        + _field_rank_stars(ns)
        + _field_evidence(ns)
        + _field_install(ns)
        + '<div class="plaque__underline"></div>'
    )
    return _plaque_shell("settled", ns, inner)


# ── ascension log ──────────────────────────────────────────────────────

def build_ascension_log(skills: list) -> str:
    def sort_key(s):
        created = s.get("createdAt", "")
        return (created, -level_num(s.get("level", "")))

    sorted_skills = sorted(skills, key=sort_key, reverse=True)
    rows = []
    for skill in sorted_skills:
        skill_id = html.escape(skill.get("id", ""))
        level    = html.escape(skill.get("level", "—"))
        date_str = fmt_date(skill.get("createdAt", ""))
        status   = skill.get("status", "named").upper()
        rows.append(
            f'<div class="ascension-log-row">'
            f'<span class="al-date">{html.escape(date_str)}</span>'
            f'<span class="al-action">{html.escape(status)}</span>'
            f'<span class="al-skill">{skill_id}</span>'
            f'<span class="al-level">{level}</span>'
            f'</div>'
        )
    if not rows:
        return '<div class="ascension-log-row"><span style="color:var(--muted);font-size:.85rem">No entries yet.</span></div>'
    return "\n".join(rows)


# ── nav / footer ───────────────────────────────────────────────────────

def _nav_html() -> str:
    return """<nav>
  <a class="nav-logo" href="../../">◆ GAIA</a>
  <ul>
    <li><a href="../../#what">What</a></li>
    <li><a href="../../#ranks">Ranks</a></li>
    <li><a href="../../#start">Start</a></li>
    <li><a href="../../#named" class="nav-named-explorer">Named Skills</a></li>
  </ul>
</nav>"""


def _footer_html() -> str:
    return """<footer style="text-align:center;padding:3rem 1.5rem;color:var(--muted);font-size:.82rem">
  <p>◆ Gaia ·
  <a href="https://github.com/mbtiongson1/gaia-skill-tree" target="_blank" style="color:var(--muted)">GitHub</a> ·
  MIT License</p>
</footer>"""


# ── profile data for JS ────────────────────────────────────────────────

def _profile_skills_json(skills: list) -> str:
    """Serialize minimal skill data as JSON for profile-share.js + profile-timeline.js."""
    data = []
    for s in skills:
        data.append({
            "id":          s.get("id", ""),
            "name":        s.get("name") or s.get("id", "").split("/")[-1],
            "contributor": s.get("contributor", ""),
            "level":       s.get("level", ""),
            "levelNum":    level_num(s.get("level", "")),
            "type":        resolve_type(s),
            "origin":      bool(s.get("origin")),
            "description": (s.get("description") or "")[:200],
            "tags":        (list(s.get("tags") or []))[:5],
            "createdAt":   s.get("createdAt", ""),
        })
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


# ── full page builder ──────────────────────────────────────────────────

def build_profile_page(handle: str, skills: list) -> str:
    safe_handle  = html.escape(handle)
    skill_count  = len(skills)
    origin_count = sum(1 for s in skills if s.get("origin"))
    max_n        = max((level_num(s.get("level", "")) for s in skills), default=0)
    highest      = f"{max_n}★" if max_n else "—"

    plaques_html = "\n".join(plaque_settled_html(s) for s in skills)
    log_html     = build_ascension_log(skills)
    skills_json  = _profile_skills_json(skills)

    page_title   = f"@{safe_handle} — Gaia Skill Registry"
    og_desc      = (
        f"Contributor profile for @{safe_handle} on the Gaia Skill Registry. "
        f"{skill_count} named skill{'s' if skill_count != 1 else ''}, "
        f"highest rank {highest}."
    )

    # origin badge in hero
    if origin_count:
        icon_svg  = (
            f'<svg class="ico" width="16" height="16" aria-hidden="true">'
            f'<use href="{ICON_BASE}#origin-badge"/></svg>'
        )
        hero_origin = (
            f'<span class="profile-origin-badge">'
            f'{icon_svg}'
            f'◆ Origin Contributor · {origin_count} origin{"s" if origin_count != 1 else ""}'
            f'</span>'
        )
    else:
        hero_origin = ""

    version = _read_version()

    page = f"""<!DOCTYPE html>
<html lang="en" data-icon-base="../../assets/icons.svg">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title}</title>
  <meta name="description" content="{html.escape(og_desc)}">
  <meta property="og:type" content="profile">
  <meta property="og:title" content="{html.escape(page_title)}">
  <meta property="og:description" content="{html.escape(og_desc)}">
  <meta property="og:url" content="https://mbtiongson1.github.io/gaia-skill-tree/u/{html.escape(handle)}/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="../../css/styles.css">
  <link rel="stylesheet" href="../../css/plaque.css">
  <script>window.PROFILE_SKILLS = {skills_json};</script>
  <script src="../../js/icons.js"></script>
  <script src="../../js/rank-badge.js"></script>
  <script src="../../js/plaque.js"></script>
  <script src="../../js/profile-sort.js" defer></script>
  <script src="../../js/profile-share.js" defer></script>
  <script src="../../js/profile-timeline.js" defer></script>
</head>
<body class="profile-page">

  {_nav_html()}

  <!-- ─── PROFILE HERO ─── -->
  <div class="profile-hero">
    <h1 class="profile-handle">{safe_handle}</h1>
    <div class="profile-meta">
      {skill_count} named skill{"s" if skill_count != 1 else ""} · highest rank {highest}
    </div>
    {hero_origin}
  </div>

  <!-- ─── NAMED SKILLS ─── -->
  <section class="profile-section">
    <h2 class="profile-section-title">Named Skills</h2>
    <p class="profile-section-sub">All named implementations attributed to @{safe_handle} in the Gaia registry.</p>
    <div class="profile-sort-bar" role="group" aria-label="Sort skills">
      <button class="profile-sort-btn active" type="button" data-sort="rank"
        aria-pressed="true">
        <svg class="ico" width="13" height="13" aria-hidden="true"><use href="{ICON_BASE}#sort-rank"/></svg>
        Rank
      </button>
      <button class="profile-sort-btn" type="button" data-sort="alpha" aria-pressed="false">
        <svg class="ico" width="13" height="13" aria-hidden="true"><use href="{ICON_BASE}#sort-alpha"/></svg>
        A – Z
      </button>
      <button class="profile-sort-btn" type="button" data-sort="type" aria-pressed="false">
        <svg class="ico" width="13" height="13" aria-hidden="true"><use href="{ICON_BASE}#sort-type"/></svg>
        Type
      </button>
    </div>
    <div class="plaque-grid">
      {plaques_html}
    </div>
  </section>

  <!-- ─── ASCENSION LOG ─── -->
  <section class="profile-section">
    <h2 class="profile-section-title">Ascension Log</h2>
    <p class="profile-section-sub">Registry events attributed to this contributor, most recent first.</p>
    <div class="ascension-log">
      <div class="ascension-log-header">
        <span>Date</span><span>Action</span><span>Skill ID</span><span>Level</span>
      </div>
      {log_html}
    </div>
  </section>

  <!-- ─── PROGRESSION TIMELINE ─── -->
  <section class="profile-section">
    <h2 class="profile-section-title">Progression Timeline</h2>
    <p class="profile-section-sub">Skill rank progression over time — hover chips for details.</p>
    <div id="profile-timeline" class="profile-timeline"></div>
  </section>

  {_footer_html()}

  <button id="scrollToTop" class="scroll-to-top" aria-label="Scroll to top"
    style="position:fixed;bottom:1.5rem;right:1.5rem;width:40px;height:40px;
           border-radius:50%;background:var(--surface);border:1px solid var(--border);
           color:var(--muted);cursor:pointer;display:flex;align-items:center;
           justify-content:center;transition:color .15s,border-color .15s;z-index:90"
    onclick="window.scrollTo({{top:0,behavior:'smooth'}})">
    <svg class="ico" width="18" height="18" aria-hidden="true"><use href="{ICON_BASE}#arrow-up"/></svg>
  </button>

</body>
</html>"""

    return _apply_cache_busting(page, version)


# ── data loading ───────────────────────────────────────────────────────

def load_named_data(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect_by_contributor(data: dict) -> dict:
    by_handle: dict[str, list] = {}
    for bucket_skills in data.get("buckets", {}).values():
        for entry in bucket_skills:
            h = entry.get("contributor", "")
            if h:
                by_handle.setdefault(h, []).append(entry)
    for entry in data.get("awaitingClassification", []):
        h = entry.get("contributor", "")
        if h:
            by_handle.setdefault(h, []).append(entry)
    return by_handle


# ── main ───────────────────────────────────────────────────────────────

def generate_pages(named_path: Path, out_dir: Path) -> int:
    global TYPE_LOOKUP
    TYPE_LOOKUP = load_type_lookup(GAIA_JSON)
    data            = load_named_data(named_path)
    by_contributor  = collect_by_contributor(data)

    if not by_contributor:
        print("No contributors found — no pages generated.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for handle, skills in sorted(by_contributor.items()):
        # Sort by level desc, then createdAt desc for default order
        skills_sorted = sorted(
            skills,
            key=lambda s: (-level_num(s.get("level", "")), s.get("createdAt", "")),
            reverse=False,
        )
        handle_dir = out_dir / handle
        handle_dir.mkdir(parents=True, exist_ok=True)
        page_html = build_profile_page(handle, skills_sorted)
        output_path = handle_dir / "index.html"
        output_path.write_text(page_html, encoding="utf-8")
        count += 1
        try:
            rel = output_path.relative_to(REPO_ROOT)
        except ValueError:
            rel = output_path
        print(f"  wrote {rel}")

    return count


def main():
    parser = argparse.ArgumentParser(description="Generate contributor profile pages.")
    parser.add_argument("--named",   default=str(NAMED_JSON), help="Path to named-skills.json")
    parser.add_argument("--out-dir", default=str(OUT_DIR),    help="Output directory")
    args = parser.parse_args()

    named_path = Path(args.named)
    out_dir    = Path(args.out_dir)

    print(f"Reading {named_path} …")
    count = generate_pages(named_path, out_dir)
    try:
        rel_dir = out_dir.relative_to(REPO_ROOT)
    except ValueError:
        rel_dir = out_dir
    print(f"Generated {count} profile page(s) under {rel_dir}")


if __name__ == "__main__":
    main()
