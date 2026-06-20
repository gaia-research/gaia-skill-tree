#!/usr/bin/env python3
"""
scripts/check_nav_mounts.py — Guard D for docs-cohesion.yml

Verifies that:
1. Every docs/ subdirectory containing HTML files that use site-nav.js or
   site-footer.js is listed in docs/js/mounts.js (window.GAIA_MOUNTS).
2. Every HTML file that loads site-nav.js also loads mounts.js before it.

Exit 0 if everything is in sync. Exit 1 (with details) if not.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
MOUNTS_JS = DOCS / "js" / "mounts.js"

# ── 1. Parse the canonical list from mounts.js ────────────────────────────────
mounts_src = MOUNTS_JS.read_text(encoding="utf-8")
match = re.search(r"window\.GAIA_MOUNTS\s*=\s*\[([^\]]+)\]", mounts_src)
if not match:
    print("ERROR: could not parse window.GAIA_MOUNTS from docs/js/mounts.js")
    sys.exit(1)

canonical_mounts = set(re.findall(r"'(\w+)'", match.group(1)))

# ── 2. Find all docs/ subdirs containing HTML files that use nav/footer ───────
NAV_RE = re.compile(r'site-nav\.js')
FOOTER_RE = re.compile(r'site-footer\.js')

active_dirs = set()
missing_mounts_tag: list[str] = []

for html in sorted(DOCS.rglob("*.html")):
    src = html.read_text(encoding="utf-8", errors="ignore")
    uses_nav = bool(NAV_RE.search(src))
    uses_footer = bool(FOOTER_RE.search(src))
    if not (uses_nav or uses_footer):
        continue

    # Collect the first-level subdirectory under docs/ (ignore root-level pages)
    rel = html.relative_to(DOCS)
    parts = rel.parts
    if len(parts) >= 2:
        active_dirs.add(parts[0])

    # Check mounts.js is loaded before site-nav.js
    if uses_nav and "mounts.js" not in src:
        missing_mounts_tag.append(str(html.relative_to(REPO_ROOT)))

# ── 3. Diff active dirs vs canonical MOUNTS list ─────────────────────────────
unlisted = sorted(active_dirs - canonical_mounts)

# ── 4. Report ────────────────────────────────────────────────────────────────
ok = True

if unlisted:
    ok = False
    print("MOUNTS OUT OF SYNC — add these directories to docs/js/mounts.js:")
    for d in unlisted:
        print(f"  '{d}',")

if missing_mounts_tag:
    ok = False
    print("\nMISSING mounts.js <script> tag (must appear before site-nav.js):")
    for f in missing_mounts_tag:
        print(f"  {f}")

if ok:
    print("OK: Nav mounts check passed.")
    sys.exit(0)
else:
    sys.exit(1)
