#!/usr/bin/env python3
"""
injectJsonLd.py — post-render JSON-LD injector for gaia.tiongson.co.

Injects a <script type="application/ld+json" data-injector="gaia-json-ld"> block
into each HTML page's <head> based on its path pattern.  Idempotent: any block
already carrying data-injector="gaia-json-ld" is REPLACED, not duplicated.

Schema.org type mapping (FROZEN per W5 spec):
  Home (docs/index.html)                  -> WebSite + SearchAction
  Contributor pages (docs/u/<handle>/)    -> Person
  Named-skill pages (docs/named/x/y.html) -> SoftwareApplication + Article
  Reports (docs/reports/*/index.html)     -> Article + NewsArticle
  Benchmarks (docs/benchmarks/**/*.html)  -> Dataset + TechArticle
  Generic                                 -> WebPage

Usage:
    python scripts/injectJsonLd.py           # inject into docs/**/*.html
    python scripts/injectJsonLd.py --check   # exit 1 if any page would change
    python scripts/injectJsonLd.py --dry-run # print which pages would be updated
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
BASE_URL = "https://gaia.tiongson.co"

# Regex to find an existing injected block (replaces it) or the </head> tag (inserts before it).
_RE_EXISTING = re.compile(
    r'<script[^>]+data-injector="gaia-json-ld"[^>]*>.*?</script>',
    re.DOTALL,
)
_RE_HEAD_CLOSE = re.compile(r'(</head>)', re.IGNORECASE)

# ── JSON-LD builders ──────────────────────────────────────────────────────────

def _ld_website() -> list[dict]:
    """WebSite + SearchAction for the home page."""
    return [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Gaia Skill Tree",
            "url": BASE_URL + "/",
            "description": "An evidence-backed atlas of AI agent capabilities.",
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": BASE_URL + "/named/?q={search_term_string}",
                },
                "query-input": "required name=search_term_string",
            },
        }
    ]


def _ld_contributor(handle: str) -> list[dict]:
    """Person schema for a contributor profile page."""
    return [
        {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": handle,
            "url": f"{BASE_URL}/u/{handle}/",
            "sameAs": f"https://github.com/{handle}",
        }
    ]


def _ld_named_skill(contributor: str, slug: str) -> list[dict]:
    """SoftwareApplication + Article for a per-skill named page."""
    name = slug.replace("-", " ").title()
    url = f"{BASE_URL}/named/{contributor}/{slug}.html"
    return [
        {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": name,
            "url": url,
            "applicationCategory": "AI Agent Skill",
            "author": {
                "@type": "Person",
                "name": contributor,
                "url": f"{BASE_URL}/u/{contributor}/",
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": name,
            "url": url,
            "author": {
                "@type": "Person",
                "name": contributor,
            },
        },
    ]


def _ld_report(week_id: str) -> list[dict]:
    """Article + NewsArticle for a weekly report."""
    url = f"{BASE_URL}/reports/{week_id}/"
    headline = f"Gaia Weekly Report — {week_id}"
    return [
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": headline,
            "url": url,
            "publisher": {
                "@type": "Organization",
                "name": "Gaia Skill Tree",
                "url": BASE_URL + "/",
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": headline,
            "url": url,
        },
    ]


def _ld_benchmark(title: str, url_path: str) -> list[dict]:
    """Dataset + TechArticle for a benchmark page."""
    url = BASE_URL + url_path
    return [
        {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": title,
            "url": url,
            "publisher": {
                "@type": "Organization",
                "name": "Gaia Skill Tree",
                "url": BASE_URL + "/",
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": title,
            "url": url,
        },
    ]


def _ld_webpage(title: str, url_path: str) -> list[dict]:
    """Generic WebPage fallback."""
    return [
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "url": BASE_URL + url_path,
        }
    ]


# ── path classifier ───────────────────────────────────────────────────────────

def _classify(rel: Path) -> list[dict]:
    """Return the appropriate JSON-LD payload for a docs-relative HTML path."""
    parts = rel.parts  # e.g. ('u', 'addy-osmani', 'index.html')

    # Home
    if rel == Path("index.html"):
        return _ld_website()

    # Contributor profile: u/<handle>/index.html
    if len(parts) == 3 and parts[0] == "u" and parts[2] == "index.html":
        return _ld_contributor(parts[1])

    # Named-skill page: named/<contributor>/<slug>.html  (NOT index.html)
    if len(parts) == 3 and parts[0] == "named" and parts[2] != "index.html":
        slug = parts[2].removesuffix(".html")
        return _ld_named_skill(parts[1], slug)

    # Reports sub-page: reports/<week>/index.html
    if len(parts) == 3 and parts[0] == "reports" and parts[2] == "index.html":
        return _ld_report(parts[1])

    # Benchmarks: benchmarks/**/*.html
    if len(parts) >= 2 and parts[0] == "benchmarks":
        title = parts[-1].removesuffix(".html").replace("-", " ").title()
        url_path = "/" + "/".join(parts)
        if url_path.endswith("/index.html"):
            url_path = url_path[: -len("index.html")]
        return _ld_benchmark(title, url_path)

    # Fallback
    title = parts[-1].removesuffix(".html").replace("-", " ").title()
    url_path = "/" + "/".join(parts)
    if url_path.endswith("/index.html"):
        url_path = url_path[: -len("index.html")]
    return _ld_webpage(title, url_path)


# ── injection logic ───────────────────────────────────────────────────────────

def _render_block(payloads: list[dict]) -> str:
    """Render one or more JSON-LD payloads into a single injectable <script> block."""
    parts: list[str] = []
    for payload in payloads:
        parts.append(json.dumps(payload, indent=2, ensure_ascii=False))
    inner = "\n".join(parts)
    return f'<script type="application/ld+json" data-injector="gaia-json-ld">\n{inner}\n</script>'


def inject_file(html_path: Path, check: bool) -> bool:
    """
    Inject (or replace) JSON-LD in an HTML file.
    Returns True if the file changed (or would change in check mode).
    """
    rel = html_path.relative_to(DOCS_DIR)
    original = html_path.read_text(encoding="utf-8")
    payloads = _classify(rel)
    if not payloads:
        return False

    block = _render_block(payloads)

    # Replace existing injected block
    if _RE_EXISTING.search(original):
        updated = _RE_EXISTING.sub(block, original, count=1)
    else:
        # Insert before </head>
        if not _RE_HEAD_CLOSE.search(original):
            return False  # malformed / fragment — skip
        updated = _RE_HEAD_CLOSE.sub(block + "\n</head>", original, count=1)

    if updated == original:
        return False

    if not check:
        html_path.write_text(updated, encoding="utf-8")
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inject JSON-LD into docs/**/*.html")
    parser.add_argument("--check", action="store_true", help="Exit 1 if any page would change")
    parser.add_argument("--dry-run", action="store_true", help="Print pages that would change")
    args = parser.parse_args(argv)

    changed_files: list[str] = []
    for html_path in sorted(DOCS_DIR.rglob("*.html")):
        # Skip non-public dirs
        rel = html_path.relative_to(DOCS_DIR)
        first = rel.parts[0] if rel.parts else ""
        if first in {"samples", "archive", "audits", "og", "assets"}:
            continue
        changed = inject_file(html_path, check=True)
        if changed:
            changed_files.append(str(rel))
            if not args.check and not args.dry_run:
                inject_file(html_path, check=False)

    if args.dry_run or args.check:
        for f in changed_files:
            print(f"  json-ld: would update {f}")

    if args.check and changed_files:
        print(f"JSON-LD is stale in {len(changed_files)} file(s) — run injectJsonLd.py to update")
        return 1

    if not args.check and not args.dry_run:
        print(f"[OK] JSON-LD injected/updated in {len(changed_files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
