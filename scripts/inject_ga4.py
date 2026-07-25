#!/usr/bin/env python3
"""Inject GA4 gtag snippet into all public docs HTML files (idempotent)."""

import re
import sys
from pathlib import Path

GA_ID = "G-TS7N9T92BM"
MARKER = f'data-ga4="{GA_ID}"'

SNIPPET = f"""  <!-- Google Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}" {MARKER}></script>
  <script {MARKER}>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA_ID}');
  </script>"""

SKIP_DIRS = {"samples", "archive", "audits", "experiments"}

DOCS = Path(__file__).parent.parent / "docs"


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def inject(path: Path, check: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False  # already present
    if check:
        print(f"MISSING GA4: {path.relative_to(DOCS.parent)}")
        return True
    updated = re.sub(r"(</head>)", SNIPPET + r"\n\1", text, count=1, flags=re.IGNORECASE)
    if updated == text:
        print(f"WARNING: no </head> found in {path}", file=sys.stderr)
        return False
    path.write_text(updated, encoding="utf-8")
    print(f"injected: {path.relative_to(DOCS.parent)}")
    return True


def main():
    check = "--check" in sys.argv
    changed = []
    for html in sorted(DOCS.rglob("*.html")):
        if not should_skip(html.relative_to(DOCS)):
            if inject(html, check):
                changed.append(html)
    if check and changed:
        sys.exit(1)
    print(f"\n{'Would update' if check else 'Updated'} {len(changed)} file(s).")


if __name__ == "__main__":
    main()
