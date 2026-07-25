#!/usr/bin/env python3
"""
scripts/check_no_binary_sources.py — standalone NUL-byte validator for docs/ sources.

A literal NUL byte ('\\0') in a text source is a footgun: GNU grep treats any file
containing one as binary and SILENTLY SKIPS it, so grep-based CI guards (notably
Guard A's hex-colour scan in .github/workflows/docs-cohesion.yml) never see the
file's contents. That is exactly how two banned hex literals hid undetected in a
`//` comment inside docs/js/skill-graph.js — the file carried a literal NUL as an
edge-key separator, so Guard A's grep skipped it entirely.

This script scans every .js, .css, and .html file under docs/ for a NUL byte and
fails (exit 1) listing the offenders, so a maintainer or agent can catch the
problem locally before pushing. Use a text escape (e.g. '\\u0000' in JS) instead
of embedding a literal NUL in source.

Usage:
    python scripts/check_no_binary_sources.py

Exit 0 if clean; exit 1 with the list of offending files if any contain a NUL.

Related: docs-cohesion.yml has a CI step ("Guard A — Detect NUL bytes in JS/CSS
sources") that enforces the same invariant for .js/.css in the pipeline; this
standalone script additionally covers .html and is runnable outside CI.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

SCANNED_SUFFIXES = {".js", ".css", ".html"}


def find_offenders():
    offenders = []
    for path in sorted(DOCS.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        if b"\x00" in path.read_bytes():
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    return offenders


def main() -> int:
    offenders = find_offenders()
    if offenders:
        print("FAIL: NUL byte found in docs/ source file(s).")
        print("A NUL makes grep treat the file as binary and silently skip it, "
              "blinding grep-based CI guards (e.g. Guard A hex scan).")
        print("Use a text escape like '\\u0000' instead of a literal NUL byte.")
        print()
        for rel in offenders:
            print(f"  {rel}")
        return 1

    print("OK: no NUL bytes in docs/ .js/.css/.html sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
