#!/usr/bin/env python3
"""
generateSitemap.py — deterministic sitemap generator for gaia.tiongson.co.

Usage:
    python scripts/generateSitemap.py          # write docs/sitemap.xml
    python scripts/generateSitemap.py --check  # exit 0 if up-to-date, 1 if stale
    python scripts/generateSitemap.py --out /path/to/sitemap.xml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

# ── constants ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
BASE_URL = "https://gaia.tiongson.co"
# Frozen canonical date — avoids timestamp drift on unrelated PRs (CLAUDE.md §Decorative).
LAST_MOD = "2026-07-05"

# ── URL catalogue ─────────────────────────────────────────────────────────────

def _static_urls() -> list[tuple[str, float]]:
    """Hard-coded high-priority pages."""
    return [
        # (path, priority)
        ("/",              1.0),
        ("/about.html",    0.6),
        ("/codex.html",    0.7),
        ("/starless.html", 0.5),
        ("/meta.html",     0.6),
    ]


def _directory_landings() -> list[tuple[str, float]]:
    """Known top-level directory landing pages."""
    return [
        ("/named/",      0.9),
        ("/badges/",     0.8),
        ("/u/",          0.7),
        ("/graph/",      0.6),
        ("/evidence/",   0.7),
        ("/trust/",      0.7),
        ("/share/",      0.6),
        ("/api/",        0.7),
        ("/trending/",   0.7),
        ("/heroes/",     0.7),
        ("/reports/",    0.7),
        ("/benchmarks/", 0.7),
        ("/skills/",     0.8),  # NEW — W5
        ("/en/",         0.7),
    ]


def _en_docs_urls() -> list[tuple[str, float]]:
    """Enumerate all docs/en/*.html pages."""
    en_dir = DOCS_DIR / "en"
    if not en_dir.is_dir():
        return []
    urls: list[tuple[str, float]] = []
    for html_path in sorted(en_dir.glob("*.html")):
        # Skip index.html — already covered by /en/ landing
        if html_path.name == "index.html":
            continue
        urls.append((f"/en/{html_path.name}", 0.6))
    return urls


def _contributor_profile_urls() -> list[tuple[str, float]]:
    """docs/u/<handle>/index.html — one entry per contributor."""
    u_dir = DOCS_DIR / "u"
    if not u_dir.is_dir():
        return []
    urls: list[tuple[str, float]] = []
    for handle_dir in sorted(u_dir.iterdir()):
        if not handle_dir.is_dir():
            continue
        # Skip utility pages (index.html at root, report.html)
        if (handle_dir / "index.html").exists():
            urls.append((f"/u/{handle_dir.name}/", 0.7))
    return urls


def _named_skill_urls() -> list[tuple[str, float]]:
    """
    Per-skill pages under docs/named/<contributor>/<slug>.html — if they exist.

    At W5 writing time named skill pages are NOT pre-rendered as individual
    HTML files; they are rendered in-browser from a JSON index. If pre-rendered
    files appear in a future Sprint (sprint-E follow-up), this function will
    pick them up automatically.
    """
    named_dir = DOCS_DIR / "named"
    if not named_dir.is_dir():
        return []
    urls: list[tuple[str, float]] = []
    for contributor_dir in sorted(named_dir.iterdir()):
        if not contributor_dir.is_dir():
            continue
        for html_path in sorted(contributor_dir.glob("*.html")):
            # index.html is the contributor landing — skip
            if html_path.name == "index.html":
                continue
            urls.append((f"/named/{contributor_dir.name}/{html_path.name}", 0.7))
    return urls


# ── assembly ──────────────────────────────────────────────────────────────────

def collect_urls() -> list[tuple[str, float]]:
    """Return a deduplicated, sorted list of (path, priority) pairs."""
    seen: set[str] = set()
    result: list[tuple[str, float]] = []
    for path, priority in (
        _static_urls()
        + _directory_landings()
        + _en_docs_urls()
        + _contributor_profile_urls()
        + _named_skill_urls()
    ):
        if path not in seen:
            seen.add(path)
            result.append((path, priority))
    return result


def render_sitemap(urls: list[tuple[str, float]]) -> str:
    """Render a well-formed sitemap XML string."""
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, priority in urls:
        loc = BASE_URL + path
        lines += [
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{LAST_MOD}</lastmod>",
            f"    <priority>{priority:.1f}</priority>",
            "  </url>",
        ]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate docs/sitemap.xml")
    parser.add_argument("--check", action="store_true", help="Exit 1 if sitemap is stale")
    parser.add_argument("--out", default=str(DOCS_DIR / "sitemap.xml"), help="Output path")
    args = parser.parse_args(argv)

    urls = collect_urls()
    rendered = render_sitemap(urls)
    out_path = Path(args.out)

    if args.check:
        if not out_path.exists():
            print("docs/sitemap.xml missing — run generateSitemap.py to create it")
            return 1
        existing = out_path.read_text(encoding="utf-8")
        if existing == rendered:
            return 0
        print("docs/sitemap.xml is stale — run generateSitemap.py to regenerate")
        return 1

    # Write mode
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] Sitemap written -> {out_path} ({len(urls)} URLs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
