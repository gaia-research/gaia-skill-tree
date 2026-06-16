#!/usr/bin/env python3
"""add_post.py — Programmatic post creation for the Gaia registry site.

Usage:
  python scripts/add_post.py announcement "Title" "Summary text" [options]
  python scripts/add_post.py link "Title" "Summary text" --url URL [options]
  python scripts/add_post.py report "Title" "Summary text" --source PATH [options]

Options:
  --date YYYY-MM-DD   Publication date (default: today)
  --label TEXT        Badge label shown in the queue card
                        default: "New" | "Link" | "Audit"
  --author NAME       Author for reports (default: Marcus Rafael Tiongson)
  --url URL           Required for link type; optional override for report
  --source PATH       Markdown source file (required for report type)
  --chart PATH        JSON chart-data file relative to docs/meta/reports/
                        (report type only; triggers Chart.js section)
  --hero / --no-hero  Force or suppress hero-audit-btn update
                        (default: auto-update for report type)
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
POSTS_FILE = ROOT / "docs" / "meta" / "posts.json"
INDEX_FILE = ROOT / "docs" / "index.html"
META_FILE = ROOT / "docs" / "meta.html"
REPORTS_DIR = ROOT / "docs" / "meta" / "reports"

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

DEFAULT_AUTHOR = "Marcus Rafael Tiongson"
DEFAULT_LABELS = {"announcement": "New", "link": "Link", "report": "Audit"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text)


def fmt_date_display(iso: str) -> str:
    """'2026-05-25' → 'May 25, 2026'"""
    try:
        y, m, d = iso.split("-")
        return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"
    except Exception:
        return iso


def load_posts() -> list:
    if POSTS_FILE.exists():
        with open(POSTS_FILE, encoding="utf-8") as f:
            return json.load(f).get("posts", [])
    return []


def save_posts(posts: list) -> None:
    POSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"posts": posts}, f, indent=2, ensure_ascii=False)
    print(f"  [ok] Updated {POSTS_FILE.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# index.html patching
# ---------------------------------------------------------------------------

def _pmq_card(post: dict) -> str:
    label = post.get("label", "Post")
    title = post.get("title", "")
    summary = post.get("summary", "")
    url = post.get("url", "#")
    target = ' target="_blank"' if url.startswith("http") else ""
    return (
        f'          <a href="{url}" class="pmq-post"{target}>\n'
        f'            <span class="pmq-label">{label}</span>\n'
        f'            <h4 class="pmq-title">{title}'
        f' <span class="meta-peek-arrow" style="float: right;">↗</span></h4>\n'
        f'            <p class="pmq-summary">{summary}</p>\n'
        f'          </a>'
    )


def patch_index(posts: list, hero_url: str | None, hero_label: str | None) -> None:
    html = INDEX_FILE.read_text(encoding="utf-8")

    # --- path-meta-queue posts ---
    cards = "\n".join(_pmq_card(p) for p in posts[:3])
    zone = (
        "<!-- gaia-posts-start -->\n"
        + cards
        + "\n          <!-- gaia-posts-end -->"
    )
    html, n = re.subn(
        r"<!-- gaia-posts-start -->.*?<!-- gaia-posts-end -->",
        zone,
        html,
        flags=re.DOTALL,
    )
    if n:
        print("  [ok] Patched path-meta-queue in index.html")
    else:
        print("  [warn] gaia-posts markers not found in index.html -- skipping queue patch")

    # --- hero-audit-btn ---
    if hero_url:
        btn = (
            "<!-- gaia-hero-post-start -->\n"
            f'    <a href="{hero_url}" class="hero-audit-btn" target="_blank"'
            f' aria-label="View {hero_label}">\n'
            f'      <svg class="ico" width="14" height="14" aria-hidden="true">'
            f'<use href="assets/icons.svg#info"/></svg>\n'
            f'      <span>{hero_label}</span>\n'
            f'      <span class="hero-audit-btn-arrow">↗</span>\n'
            f'    </a>\n'
            f'    <!-- gaia-hero-post-end -->'
        )
        html, n = re.subn(
            r"<!-- gaia-hero-post-start -->.*?<!-- gaia-hero-post-end -->",
            btn,
            html,
            flags=re.DOTALL,
        )
        if n:
            print("  [ok] Patched hero-audit-btn in index.html")
        else:
            print("  [warn] gaia-hero-post markers not found in index.html -- skipping hero patch")

    INDEX_FILE.write_text(html, encoding="utf-8")


def _meta_card(post: dict) -> str:
    title = post.get("title", "")
    summary = post.get("summary", "")
    url = post.get("url", "#")
    fname = url.rsplit("/", 1)[-1]
    date_disp = fmt_date_display(post.get("date", ""))
    return (
        f'      <article class="meta-report-card">\n'
        f'        <div class="meta-report-date">{date_disp}</div>\n'
        f'        <h3 class="meta-report-title">{title}</h3>\n'
        f'        <p class="meta-report-summary">{summary}</p>\n'
        f'        <div class="meta-report-footer">\n'
        f'          <a href="{url}" class="btn btn-ghost meta-report-link">Read Full Report →</a>\n'
        f'          <button type="button" class="meta-report-action" aria-label="Share report"'
        f' data-report-url="{url}" data-report-title="{title}" onclick="metaReportShare(this)">'
        f'<svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#share"/></svg></button>\n'
        f'          <a href="{url}" download="{fname}" class="meta-report-action" aria-label="Download report">'
        f'<svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#download"/></svg></a>\n'
        f'          <button type="button" class="meta-report-action" aria-label="Copy link"'
        f' data-report-url="{url}" onclick="metaReportCopyLink(this)">'
        f'<svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#link"/></svg></button>\n'
        f'        </div>\n'
        f'      </article>'
    )


def patch_meta_html(posts: list) -> None:
    if not META_FILE.exists():
        print("  [warn] meta.html not found -- skipping meta cards patch")
        return
    html = META_FILE.read_text(encoding="utf-8")
    reports = [p for p in posts if p.get("type") == "report"]
    cards = "\n".join(_meta_card(p) for p in reports)
    zone = "<!-- gaia-meta-cards-start -->\n" + cards + "\n      <!-- gaia-meta-cards-end -->"
    html, n = re.subn(
        r"<!-- gaia-meta-cards-start -->.*?<!-- gaia-meta-cards-end -->",
        zone, html, flags=re.DOTALL,
    )
    if n:
        print("  [ok] Patched meta-report cards in meta.html")
    else:
        print("  [warn] gaia-meta-cards markers not found in meta.html -- skipping")
    META_FILE.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# Markdown → HTML (for academic report template)
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Inline markdown: code, bold, italic, links."""
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{_esc(m.group(1))}</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__",
                  lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
    text = re.sub(r"\*(.+?)\*|_(.+?)_",
                  lambda m: f"<em>{m.group(1) or m.group(2)}</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    return text


def md_to_html(md: str) -> str:
    """Convert markdown body to inner HTML for the academic paper template."""
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_list = False

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def open_list() -> None:
        nonlocal in_list
        if not in_list:
            out.append("<ul>")
            in_list = True

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            flush_list()
            lang = line.strip()[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(_esc(lines[i]))
                i += 1
            i += 1  # consume closing ```
            out.append(f'<pre><code class="language-{lang}">' + "\n".join(code_lines) + "</code></pre>")
            continue

        # H2 — section heading
        m = re.match(r"^## (.+)$", line)
        if m:
            flush_list()
            title = m.group(1).strip()
            lower = title.lower()
            if lower == "abstract":
                # Abstract section is injected from frontmatter; skip body abstract heading
                i += 1
                continue
            if lower in ("references", "references & contributions"):
                # References get the .references / .ref-item treatment
                out.append('<div class="references">')
                out.append(
                    f'  <div class="abstract-title" style="text-align: left; margin-bottom: 1.5rem;">'
                    f"{title}</div>"
                )
                i += 1
                while i < len(lines):
                    ref = lines[i].strip()
                    i += 1
                    if not ref:
                        continue
                    if re.match(r"^#", ref):
                        i -= 1  # rewind so outer loop handles it
                        break
                    out.append(f'  <div class="ref-item">{_inline(ref)}</div>')
                out.append("</div>")
                continue
            out.append(f"<h2>{_inline(title)}</h2>")
            i += 1
            continue

        # H3 — subsection
        m = re.match(r"^### (.+)$", line)
        if m:
            flush_list()
            out.append(f"<h3>{_inline(m.group(1).strip())}</h3>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$", line.strip()):
            flush_list()
            out.append("<hr>")
            i += 1
            continue

        # Table parsing
        if line.strip().startswith("|"):
            flush_list()
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            
            if len(table_lines) >= 1:
                def split_row(row: str) -> list[str]:
                    cells = row.split("|")
                    if len(cells) > 0 and not cells[0].strip():
                        cells = cells[1:]
                    if len(cells) > 0 and not cells[-1].strip():
                        cells = cells[:-1]
                    return [c.strip() for c in cells]

                header_cells = split_row(table_lines[0])
                
                # Check if second line is a separator row
                is_separator = False
                if len(table_lines) > 1:
                    second_row = split_row(table_lines[1])
                    is_separator = all(re.match(r"^:?-+:?$", cell) for cell in second_row) if second_row else False
                
                start_row_idx = 2 if is_separator else 1
                
                thead = "<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header_cells) + "</tr></thead>"
                
                tbody_rows = []
                for row_line in table_lines[start_row_idx:]:
                    cells = split_row(row_line)
                    while len(cells) < len(header_cells):
                        cells.append("")
                    tbody_rows.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells[:len(header_cells)]) + "</tr>")
                
                tbody = "<tbody>" + "".join(tbody_rows) + "</tbody>"
                out.append(f"<table>{thead}{tbody}</table>")
            continue

        # Blockquote parsing
        if line.strip().startswith(">"):
            flush_list()
            bq_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                l = lines[i].strip()
                if l.startswith("> "):
                    bq_lines.append(l[2:])
                else:
                    bq_lines.append(l[1:])
                i += 1
            bq_content = " ".join(bq_lines)
            out.append(f"<blockquote><p>{_inline(bq_content)}</p></blockquote>")
            continue

        # List item
        m = re.match(r"^[-*] (.+)$", line)
        if m:
            open_list()
            out.append(f"  <li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # Blank line — ends a list or paragraph
        if not line.strip():
            flush_list()
            i += 1
            continue

        # Paragraph (consume until blank line or block-level marker)
        flush_list()
        para: list[str] = []
        while i < len(lines):
            l = lines[i]
            if not l.strip():
                break
            if re.match(r"^#{1,6} ", l) or re.match(r"^[-*] ", l):
                break
            if l.strip().startswith("```") or l.strip().startswith("|") or l.strip().startswith(">"):
                break
            if re.match(r"^-{3,}$", l.strip()):
                break
            para.append(_inline(l))
            i += 1
        if para:
            out.append(f'<p>{" ".join(para)}</p>')

    flush_list()
    return "\n".join(out)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    try:
        import yaml
    except ImportError:
        return {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                meta = yaml.safe_load(text[3:end].strip()) or {}
                return meta, text[end + 4:].strip()
            except Exception:
                pass
    return {}, text


# ---------------------------------------------------------------------------
# Report HTML template
# ---------------------------------------------------------------------------

# CSS is extracted once so the template stays readable.
_REPORT_CSS = """\
    :root {
      --paper-bg: #ffffff;
      --paper-text: #111111;
      --paper-muted: #666666;
      --accent: #ef4444;
      --font-serif: 'EB Garamond', Georgia, serif;
      --font-sans: 'Bricolage Grotesque', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; }
    body {
      background: #f4f4f2;
      color: var(--paper-text);
      font-family: var(--font-serif);
      font-variant-numeric: oldstyle-nums;
      line-height: 1.6;
      margin: 0;
      padding: 6rem 1rem;
      -webkit-font-smoothing: antialiased;
    }
    .paper {
      background: var(--paper-bg);
      max-width: 820px;
      margin: 0 auto;
      padding: 6rem 7rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 10px 40px rgba(0,0,0,0.02);
      position: relative;
      counter-reset: section;
    }
    header { text-align: center; margin-bottom: 5rem; }
    .paper-journal-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 1.5rem;
      margin-bottom: 3rem;
      border-bottom: 1px solid #e0e0dc;
    }}
    .paper-journal-logo {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      text-decoration: none;
      color: #c8a84b;
      font-family: var(--font-sans);
      font-weight: 600;
      font-size: 0.9rem;
      letter-spacing: 0.04em;
    }}
    .paper-journal-logo img {{
      filter: invert(72%) sepia(40%) saturate(600%) hue-rotate(5deg) brightness(95%);
    }}
    .paper-journal-series {{
      font-family: var(--font-sans);
      font-size: 0.75rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: #999;
    }}
    h1 {
      font-family: var(--font-serif);
      font-size: 2.6rem;
      font-weight: 500;
      margin-bottom: 1.5rem;
      line-height: 1.1;
      letter-spacing: -0.01em;
    }
    .authors {
      font-family: var(--font-serif);
      font-variant-caps: small-caps;
      font-size: 1.2rem;
      margin-bottom: 0.5rem;
      letter-spacing: 0.02em;
    }
    .date { font-family: var(--font-serif); font-size: 1.1rem; color: var(--paper-text); }
    .abstract { margin: 4rem 0; padding: 0 3rem; }
    .abstract-title {
      font-family: var(--font-sans);
      font-weight: 700;
      text-align: center;
      margin-bottom: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.75rem;
      color: var(--paper-muted);
    }
    .abstract-content { font-style: italic; text-align: justify; hyphens: auto; font-size: 1.05rem; line-height: 1.5; }
    h2 {
      font-family: var(--font-sans);
      font-size: 0.9rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-top: 4rem;
      margin-bottom: 1.5rem;
      counter-increment: section;
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }
    h2::before { content: counter(section) ". "; }
    h3 { font-family: var(--font-serif); font-size: 1.3rem; font-weight: 600; margin-top: 2.5rem; margin-bottom: 1rem; }
    p { text-align: justify; margin-bottom: 1.5rem; hyphens: auto; }
    .two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 3rem; margin: 2.5rem 0; }
    ul { padding-left: 1.2rem; list-style-type: square; }
    li { margin-bottom: 0.6rem; }
    code { font-family: var(--font-mono); background: #f7f7f7; padding: 0.15rem 0.35rem; font-size: 0.85em; border: 1px solid #eee; }
    pre { background: #f7f7f7; border: 1px solid #eee; padding: 1.2rem 1.5rem; overflow-x: auto; margin: 2rem 0; }
    pre code { background: none; border: none; padding: 0; font-size: 0.85rem; }
    blockquote { border-left: 3px solid #c8a84b; margin: 2rem 0; padding: 1rem 1.5rem; background: #fafaf8; color: #444; font-style: italic; }
    table { width: 100%; border-collapse: collapse; margin: 3rem 0; font-family: var(--font-serif); font-size: 1rem; }
    thead tr { border-top: 2px solid var(--paper-text); border-bottom: 1px solid var(--paper-text); }
    th { font-weight: 600; text-align: left; padding: 0.8rem 0.5rem; font-variant-caps: small-caps; }
    td { padding: 0.8rem 0.5rem; border-bottom: 0.5px solid #eee; vertical-align: top; }
    tbody tr:last-child { border-bottom: 2px solid var(--paper-text); }
    .chart-container { margin: 4.5rem -2rem; padding: 2.5rem; background: #ffffff; border: 1px solid #eee; }
    .chart-caption { text-align: center; font-size: 0.85rem; color: var(--paper-muted); margin-top: 1.5rem; line-height: 1.4; }
    .references { margin-top: 6rem; padding-top: 3rem; border-top: 1px solid #eee; }
    .ref-item { font-size: 0.9rem; margin-bottom: 1.2rem; text-indent: -1.8rem; padding-left: 1.8rem; text-align: left; }
    .footer-nav { margin-top: 5rem; text-align: center; font-family: var(--font-sans); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; }
    .footer-nav a { color: var(--paper-text); text-decoration: none; border-bottom: 1px solid #ddd; padding-bottom: 2px; transition: border-color 0.2s; }
    .footer-nav a:hover { border-color: var(--accent); }
    .floating-cluster {
      position: fixed; top: 2rem; right: 2rem; z-index: 1000;
      display: flex; align-items: center; gap: 0.5rem;
    }
    .pja-btn {
      background: #fff; border: 1px solid #d0d0cc; border-radius: 0; color: #888;
      cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
      width: 2rem; height: 2rem; padding: 0; text-decoration: none;
      transition: color 0.15s, border-color 0.15s; flex-shrink: 0;
    }
    .pja-btn:hover { color: #111; border-color: #111; }
    .pja-btn.copied { color: #16a34a; border-color: #16a34a; }
    .pja-btn svg { width: 15px; height: 15px; display: block; }
    .floating-changelog-btn {
      background: #000; color: #fff; border: none;
      padding: 0.8rem 1.4rem;
      font-family: var(--font-sans); font-weight: 700; font-size: 0.7rem;
      text-transform: uppercase; letter-spacing: 0.15em; cursor: pointer;
      box-shadow: 0 10px 30px rgba(0,0,0,0.15);
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .floating-changelog-btn:hover { transform: translateY(-2px); box-shadow: 0 15px 40px rgba(0,0,0,0.2); background: #111; }
    .meta-sidebar {
      position: fixed; top: 0; right: 0; bottom: 0; width: 400px;
      background: #000; color: #fff; z-index: 2000;
      transform: translateX(100%); transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex; flex-direction: column; border-left: 1px solid #222;
    }
    .meta-sidebar.open { transform: translateX(0); }
    .ms-header { padding: 1.5rem; border-bottom: 1px solid #222; display: flex; justify-content: space-between; align-items: center; }
    .ms-header h2 { margin: 0 !important; border: none !important; font-size: 1.2rem !important; font-family: 'EB Garamond', serif !important; counter-reset: none !important; }
    .ms-header h2::before { content: none !important; }
    .ms-body { flex: 1; overflow-y: auto; padding: 1.5rem; font-family: 'Bricolage Grotesque', sans-serif; }
    .ms-close { background: none; border: none; color: #666; font-size: 1.5rem; cursor: pointer; }
    @media (max-width: 768px) {
      .paper { padding: 3rem 2rem; }
      body { padding: 1rem 0; }
      .floating-cluster { top: 0.75rem; right: 0.75rem; }
      .floating-changelog-btn { padding: 0.4rem 0.8rem; font-size: 0.7rem; }
      .meta-sidebar { width: 100%; }
    }"""

_CHANGELOG_JS = """\
    const sidebar = document.getElementById('metaSidebar');
    const openBtn = document.getElementById('viewChangelogBtn');
    const closeBtn = document.getElementById('closeChangelogBtn');
    if (openBtn) openBtn.addEventListener('click', () => sidebar.classList.add('open'));
    if (closeBtn) closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));
    async function loadChangelog() {
      try {
        const res = await fetch('../../graph/gaia.json');
        const gaia = await res.json();
        const body = document.getElementById('changelogBody');
        body.innerHTML = '';
        let events = [];
        gaia.skills.forEach(s => {
          if (s.timeline) s.timeline.forEach(e => events.push({ ...e, skillName: s.name }));
        });
        events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        events.slice(0, 50).forEach(ev => {
          const item = document.createElement('div');
          item.style.cssText = 'margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid #111';
          item.innerHTML = `<div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#666;margin-bottom:0.3rem">${new Date(ev.timestamp).toLocaleDateString()} · ${ev.action.toUpperCase()}</div><div style="font-weight:500;font-size:0.9rem;color:#fff">${ev.skillName}</div><div style="font-size:0.8rem;color:#aaa;margin-top:0.2rem">${ev.details}</div>`;
          body.appendChild(item);
        });
      } catch (e) { console.error('Failed to load changelog', e); }
    }
    loadChangelog();

    (function() {
      var shareBtn = document.getElementById('reportShareBtn');
      var copyBtn = document.getElementById('reportCopyLinkBtn');
      function flashBtn(b) { b.classList.add('copied'); setTimeout(function() { b.classList.remove('copied'); }, 1500); }
      if (shareBtn) shareBtn.addEventListener('click', function() {
        var url = location.href, title = document.title;
        if (navigator.share) { navigator.share({ title: title, url: url }).catch(function() {}); }
        else if (navigator.clipboard) { navigator.clipboard.writeText(url).then(function() { flashBtn(shareBtn); }); }
      });
      if (copyBtn) copyBtn.addEventListener('click', function() {
        if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(function() { flashBtn(copyBtn); });
      });
    })();"""


def render_report_html(
    title: str,
    author: str,
    display_date: str,
    abstract: str,
    body_html: str,
    back_href: str = "../../index.html",
    chart_data_file: str | None = None,
    download_name: str = "",
) -> str:
    chart_script_tag = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>' if chart_data_file else ""

    chart_section = ""
    chart_init = ""
    if chart_data_file:
        chart_section = (
            '<div class="chart-container">'
            '<canvas id="timelineChart"></canvas>'
            '<div class="chart-caption" id="chartCaption">Figure 1</div>'
            "</div>"
        )
        chart_init = f"""\
    async function initChart() {{
      try {{
        const res = await fetch('{chart_data_file}');
        const data = await res.json();
        const ctx = document.getElementById('timelineChart').getContext('2d');
        if (data.caption) {{
          const cap = document.getElementById('chartCaption');
          if (cap) cap.textContent = data.caption;
        }}
        new Chart(ctx, {{
          type: data.type || 'line',
          data: {{
            labels: data.labels,
            datasets: data.datasets.map(ds => {{
              const isDoughnut = (data.type === 'doughnut');
              return {{
                label: ds.label,
                data: ds.data,
                borderColor: isDoughnut ? '#ffffff' : ds.color,
                backgroundColor: isDoughnut ? ds.color : (ds.color + '22'),
                borderWidth: 2,
                fill: !isDoughnut,
                tension: 0.3,
                pointRadius: isDoughnut ? undefined : 0,
                pointHoverRadius: isDoughnut ? undefined : 5
              }};
            }})
          }},
          options: {{
            responsive: true,
            plugins: {{
              legend: {{
                position: (data.type === 'doughnut') ? 'right' : 'bottom',
                labels: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
              }},
              tooltip: {{
                mode: (data.type === 'doughnut') ? 'average' : 'index',
                intersect: (data.type === 'doughnut')
              }}
            }},
            scales: (data.type === 'doughnut') ? {{}} : {{
              x: {{ grid: {{ display: false }}, ticks: {{ font: {{ family: 'JetBrains Mono', size: 9 }} }} }},
              y: {{ beginAtZero: true, grid: {{ color: '#eee' }}, ticks: {{ font: {{ family: 'JetBrains Mono', size: 9 }} }} }}
            }}
          }}
        }});
      }} catch (e) {{ console.error('Chart failed', e); }}
    }}
    initChart();"""

    abstract_html = (
        f'    <section class="abstract">\n'
        f'      <div class="abstract-title">Abstract</div>\n'
        f'      <div class="abstract-content">{abstract}</div>\n'
        f'    </section>'
        if abstract
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Gaia</title>
  <link rel="icon" type="image/svg+xml" href="../../assets/marks/diamond-seal.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  {chart_script_tag}
  <style>
{_REPORT_CSS}
  </style>
</head>
<body>

  <div class="floating-cluster">
    <button type="button" class="pja-btn" id="reportShareBtn" aria-label="Share report">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="15" cy="5" r="2"/><circle cx="5" cy="10" r="2"/><circle cx="15" cy="15" r="2"/>
        <line x1="7" y1="9" x2="13" y2="6"/><line x1="7" y1="11" x2="13" y2="14"/>
      </svg>
    </button>
    <a href="{download_name}" download="{download_name}" class="pja-btn" aria-label="Download report">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M10 3v9m0 0l-3.5-3.5M10 12l3.5-3.5"/><path d="M4 15h12"/>
      </svg>
    </a>
    <button type="button" class="pja-btn" id="reportCopyLinkBtn" aria-label="Copy link">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M8.5 11.5a4.5 4.5 0 006.364 0l2-2a4.5 4.5 0 00-6.364-6.364L9 4.636"/>
        <path d="M11.5 8.5a4.5 4.5 0 00-6.364 0l-2 2a4.5 4.5 0 006.364 6.364L11 15.364"/>
      </svg>
    </button>
    <button type="button" class="floating-changelog-btn" id="viewChangelogBtn">View Changelog</button>
  </div>

  <aside id="metaSidebar" class="meta-sidebar">
    <div class="ms-header">
      <h2>Meta Changelog</h2>
      <button type="button" class="ms-close" id="closeChangelogBtn">✕</button>
    </div>
    <div class="ms-body" id="changelogBody">
      <div style="color:#666;font-size:0.9rem">Loading registry changelog…</div>
    </div>
  </aside>

  <article class="paper">
    <div class="paper-journal-header">
      <a href="../../index.html" class="paper-journal-logo" aria-label="Gaia Registry">
        <img src="../../assets/marks/diamond-seal.svg" alt="Gaia" width="28" height="28">
        <span>Gaia Registry</span>
      </a>
      <span class="paper-journal-series">Meta Audit Series</span>
    </div>
    <header>
      <h1>{title}</h1>
      <div class="authors">{author}</div>
      <div class="date">{display_date}</div>
    </header>

{abstract_html}
{chart_section}
    {body_html}

    <div class="footer-nav">
      <a href="{back_href}">← Back to Gaia</a>
    </div>
  </article>

  <script>
{_CHANGELOG_JS}
{chart_init}
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Post creation logic
# ---------------------------------------------------------------------------

def create_announcement(args) -> dict:
    post_date = args.date or str(date.today())
    label = args.label or DEFAULT_LABELS["announcement"]
    post_id = f"{post_date}-{slugify(args.title)}"
    return {
        "id": post_id,
        "type": "announcement",
        "date": post_date,
        "title": args.title,
        "summary": args.summary,
        "label": label,
        "url": args.url or "#",
    }


def create_link(args) -> dict:
    if not args.url:
        sys.exit("error: --url is required for link type")
    post_date = args.date or str(date.today())
    label = args.label or DEFAULT_LABELS["link"]
    post_id = f"{post_date}-{slugify(args.title)}"
    return {
        "id": post_id,
        "type": "link",
        "date": post_date,
        "title": args.title,
        "summary": args.summary,
        "label": label,
        "url": args.url,
    }


def create_report(args) -> dict:
    if not args.source:
        sys.exit("error: --source is required for report type")

    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    if not source_path.exists():
        sys.exit(f"error: source file not found: {source_path}")

    raw = source_path.read_text(encoding="utf-8")
    fm, body_md = parse_frontmatter(raw)

    post_date = args.date or fm.get("date") or str(date.today())
    post_date = str(post_date)  # yaml may parse dates as date objects

    title = args.title or fm.get("title", "Untitled Report")
    summary = args.summary or fm.get("summary", "")
    label = args.label or fm.get("label") or DEFAULT_LABELS["report"]
    author = args.author or fm.get("author") or DEFAULT_AUTHOR
    abstract = fm.get("abstract") or summary
    chart_file = args.chart or fm.get("chart")

    slug = slugify(title)
    filename = f"{post_date}-{slug}.html"
    out_path = REPORTS_DIR / filename
    rel_url = f"meta/reports/{filename}"

    body_html = md_to_html(body_md)
    html = render_report_html(
        title=title,
        author=author,
        display_date=fmt_date_display(post_date),
        abstract=abstract,
        body_html=body_html,
        chart_data_file=chart_file,
        download_name=filename,
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"  [ok] Rendered report -> {out_path.relative_to(ROOT)}")

    return {
        "id": f"{post_date}-{slug}",
        "type": "report",
        "date": post_date,
        "title": title,
        "summary": summary,
        "label": label,
        "url": rel_url,
        "author": author,
        "source": str(source_path.relative_to(ROOT)).replace("\\", "/"),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add a new post (announcement / link / report) to the Gaia site.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("type", choices=["announcement", "link", "report"],
                        help="Post type")
    parser.add_argument("title", help="Post title")
    parser.add_argument("summary", help="Short summary shown in the queue card")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="Publication date (default: today)")
    parser.add_argument("--label", metavar="TEXT", help="Badge label")
    parser.add_argument("--author", metavar="NAME", help="Author name (reports only)")
    parser.add_argument("--url", metavar="URL", help="URL (required for link; optional for report)")
    parser.add_argument("--source", metavar="PATH", help="Markdown source file (reports only)")
    parser.add_argument("--chart", metavar="PATH", help="Chart JSON file path relative to reports/ dir")
    hero_grp = parser.add_mutually_exclusive_group()
    hero_grp.add_argument("--hero", action="store_true", default=None,
                          help="Update hero-audit-btn to this post")
    hero_grp.add_argument("--no-hero", dest="hero", action="store_false",
                          help="Skip hero-audit-btn update")
    args = parser.parse_args()

    print(f"\n> Creating {args.type} post: {args.title!r}")

    creators = {
        "announcement": create_announcement,
        "link": create_link,
        "report": create_report,
    }
    post = creators[args.type](args)

    # Prepend (newest first)
    posts = load_posts()
    posts = [p for p in posts if p.get("id") != post["id"]]  # replace if same id
    posts.insert(0, post)
    save_posts(posts)

    # Decide whether to update hero button
    update_hero = args.hero
    if update_hero is None:
        update_hero = args.type == "report"

    hero_url = post.get("url") if update_hero else None
    hero_label = post.get("label") if update_hero else None

    patch_index(posts, hero_url=hero_url, hero_label=hero_label)
    patch_meta_html(posts)
    print(f"\n[done] Post id: {post['id']}\n")


if __name__ == "__main__":
    main()
