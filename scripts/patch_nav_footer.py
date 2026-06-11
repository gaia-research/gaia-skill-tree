"""
One-shot script to:
1. Replace inline <nav> blocks with <nav id="site-nav"></nav> + site-nav.js
2. Replace inline footer HTML with <div id="site-footer-mount"></div> + site-footer.js
3. Fix all stale ?v= version strings to 4.7.5
4. Fix missing plaque.css / alpha-rail.css stylesheet refs where needed

Target pages (docs root depth=0):
  about.html, codex.html, meta.html, privacy.html, starless.html

Target pages (depth=1):
  named/index.html, badges/index.html

Already correct: index.html (we'll only fix version string there)

NOT touched: docs/u/* (generated), docs/en/* (different nav type)
"""

import re, pathlib

DOCS = pathlib.Path("docs")
TARGET_VERSION = "4.7.5"

# ── Helpers ────────────────────────────────────────────────────────────────

def fix_versions(html: str) -> str:
    """Replace all ?v=X.Y.Z with the current version."""
    return re.sub(r'\?v=[\d.]+', f'?v={TARGET_VERSION}', html)

def replace_nav(html: str, depth: int) -> str:
    """Replace the hand-coded <nav> block (not footer-cols) with the mount point."""
    # Match <nav> ... </nav> that is NOT a footer nav and NOT docs-nav
    # We look for <nav> (no class, or class without footer/docs)
    pattern = re.compile(
        r'([ \t]*)<!--\s*[─\-]*\s*NAV\s*[─\-]*\s*-->\s*\n'  # optional comment
        r'([ \t]*)<nav>.*?</nav>',
        re.DOTALL
    )
    root = '' if depth == 0 else '../' * depth
    replacement = (
        f'  <!-- ─── NAV ─── -->\n'
        f'  <nav id="site-nav"></nav>\n'
        f'  <script src="{root}js/site-nav.js?v={TARGET_VERSION}"></script>'
    )
    result, n = pattern.subn(replacement, html)
    if n:
        return result
    # Fallback: match bare <nav> block without comment
    pattern2 = re.compile(r'([ \t]*)<nav>\s*\n.*?</nav>', re.DOTALL)
    result, n = pattern2.subn(
        f'  <nav id="site-nav"></nav>\n'
        f'  <script src="{root}js/site-nav.js?v={TARGET_VERSION}"></script>',
        html
    )
    return result

def replace_footer(html: str, depth: int) -> str:
    """Replace the hand-coded <footer class="footer-v2"> block with the mount point."""
    root = '' if depth == 0 else '../' * depth
    pattern = re.compile(r'<footer class="footer-v2">.*?</footer>', re.DOTALL)
    replacement = (
        f'<div id="site-footer-mount"></div>\n'
        f'  <script src="{root}js/site-footer.js?v={TARGET_VERSION}"></script>'
    )
    result, n = pattern.subn(replacement, html)
    return result

def ensure_styles(html: str, depth: int) -> str:
    """Make sure styles.css, plaque.css, alpha-rail.css are present and up to date."""
    root = '' if depth == 0 else '../' * depth
    prefix = root + 'css/'

    def has(name):
        return name in html

    inserts = []
    # styles.css is always required; fix version handled by fix_versions above
    if not has('styles.css'):
        inserts.append(f'  <link rel="stylesheet" href="{prefix}styles.css?v={TARGET_VERSION}">')
    if not has('plaque.css'):
        inserts.append(f'  <link rel="stylesheet" href="{prefix}plaque.css?v={TARGET_VERSION}">')

    if inserts:
        html = html.replace('</head>', '\n'.join(inserts) + '\n</head>', 1)
    return html

# ── Pages to patch ─────────────────────────────────────────────────────────

PAGES = [
    # (relative path, depth)
    ("index.html",         0),
    ("about.html",         0),
    ("codex.html",         0),
    ("meta.html",          0),
    ("privacy.html",       0),
    ("starless.html",      0),
    ("named/index.html",   1),
    ("badges/index.html",  1),
    ("u/index.html",       1),
]

for rel, depth in PAGES:
    path = DOCS / rel
    if not path.exists():
        print(f"SKIP (not found): {rel}")
        continue

    original = path.read_text(encoding='utf-8')
    html = original

    # 1. Fix version strings everywhere
    html = fix_versions(html)

    # Skip nav/footer replacement for index.html (already has site-nav.js)
    # and for u/index.html (generated, different structure)
    if rel not in ('index.html',):
        html = replace_nav(html, depth)
        html = replace_footer(html, depth)

    # 2. Ensure stylesheet refs exist
    html = ensure_styles(html, depth)

    if html != original:
        path.write_text(html, encoding='utf-8')
        print(f"PATCHED: {rel}")
    else:
        print(f"NO CHANGE: {rel}")

print("Done.")
