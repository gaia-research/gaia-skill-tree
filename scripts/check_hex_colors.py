#!/usr/bin/env python3
"""
scripts/check_hex_colors.py — Guard A hex-colour enforcement for docs-cohesion.yml

Rejects hardcoded hex colour literals from the banned set in LIVE CODE, failing
(exit 1) if any remain. This replaces the inline grep Guard A used to run, fixing
two gaps that grep could not close:

  1. NUL-byte binary skip — GNU grep silently skips any file containing a NUL
     byte ('\\0'). docs/js/skill-graph.js carried a literal NUL as an edge-key
     separator, so grep never scanned it and two banned hexes hid there in `//`
     comments. Python reads every file as text regardless of control bytes, so
     no source file is ever silently skipped. (A separate NUL detector step in
     docs-cohesion.yml, and scripts/check_no_binary_sources.py, guard against a
     NUL ever being reintroduced.)

  2. No comment exclusion — grep could not tell a hex in a `//` comment
     (documentation) from a hex in live code. This script strips `//` line
     comments and `/* */` block comments before matching, so a documented hex in
     a comment no longer trips the guard while a live-code literal still does.

Allowed forms (not flagged):
  - Hexes inside `//` or `/* */` comments (documentation).
  - The self-documenting `var(--token, #hex)` fallback form — the token is
    authoritative; the hex is an inline default. Any line that references a CSS
    custom-property fallback (`var(--x, ...)`) is treated as token-anchored, the
    same allowance the original inline grep encoded with `grep -v 'var(--[^,]*,'`.

Scanned scope: docs/js/**/*.js and docs/css/**/*.css — the live design-system
code Guard A has always enforced. Two categories are exempt:
  - docs/css/tokens.css — the GENERATED token-definition source (built by
    scripts/generateCssTokens.py from registry/gaia.json). It is *supposed* to
    contain every raw hex; it is the single place they are allowed to live.
  - docs/**/archive/** — historical snapshots (matched the original
    --exclude-dir='archive').

NOTE on HTML: inline `<style>` blocks and SVG fills across docs/**/*.html carry a
large body of pre-existing hex literals that predate this guard and were never in
its scope. Bringing them under enforcement is a separate content-migration effort,
not part of hardening the guard mechanism, so HTML is intentionally out of scope
here — matching the JS/CSS-only surface Guard A actually gated.

Run locally: python scripts/check_hex_colors.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

# Banned hex set — the exact literals the original Guard A inline grep rejected.
BANNED_HEXES = [
    "38bdf8", "c084fc", "f59e0b", "7c3aed", "fbbf24",
    "94a3b8", "63cab7", "a78bfa", "e879f9",
]
BANNED_RE = re.compile(r"#(?:" + "|".join(BANNED_HEXES) + r")\b", re.IGNORECASE)

# Path parts that exclude a file from scanning.
EXCLUDED_DIR_PARTS = {"archive"}

# Generated token-definition source — the one file allowed to hold raw hexes.
EXEMPT_FILES = {(DOCS / "css" / "tokens.css").resolve()}

# A line that anchors a hex to a CSS custom property via the var() fallback form
# is token-derived and allowed (original grep: `grep -v 'var(--[^,]*,'`).
VAR_FALLBACK_LINE_RE = re.compile(r"var\(\s*--[^,]*,")


def strip_comments(text: str) -> str:
    """Blank out // line comments and /* */ block comments, preserving newlines
    so reported line numbers stay accurate. A pragmatic stripper (not a full
    JS/CSS parser): it treats // and /* */ as comments wherever they appear. The
    goal is to stop flagging a documented hex; any banned hex that survives
    stripping is a genuine live-code literal."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        two = text[i:i + 2]
        if two == "//":
            j = text.find("\n", i)
            if j == -1:
                out.append(" " * (n - i))
                i = n
            else:
                out.append(" " * (j - i))
                i = j
        elif two == "/*":
            j = text.find("*/", i + 2)
            end = (j + 2) if j != -1 else n
            for ch in text[i:end]:
                out.append("\n" if ch == "\n" else " ")
            i = end
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def scan_file(path: Path):
    """Return [(lineno, matched_hex), ...] for banned hexes in live code."""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = strip_comments(text)
    hits = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if VAR_FALLBACK_LINE_RE.search(line):
            continue  # token-anchored via var() fallback — allowed
        for m in BANNED_RE.finditer(line):
            hits.append((lineno, m.group(0)))
    return hits


def iter_target_files():
    for pattern in ("js/**/*.js", "css/**/*.css"):
        for path in DOCS.glob(pattern):
            if not path.is_file():
                continue
            if EXCLUDED_DIR_PARTS & set(path.parts):
                continue
            if path.resolve() in EXEMPT_FILES:
                continue
            yield path


def main() -> int:
    failures = []
    for path in sorted(set(iter_target_files())):
        for lineno, hexval in scan_file(path):
            rel = path.relative_to(REPO_ROOT).as_posix()
            failures.append(f"{rel}:{lineno}: {hexval}")

    if failures:
        print("Guard A FAIL: hardcoded hex colour literals found in live code.")
        print("Use design tokens from docs/css/tokens.css instead "
              "(or the var(--token, #hex) fallback form).")
        print()
        for line in failures:
            print(f"  {line}")
        return 1

    print("Guard A OK: no banned hex literals in live JS/CSS code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
