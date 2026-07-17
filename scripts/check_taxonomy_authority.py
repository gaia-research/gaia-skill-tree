#!/usr/bin/env python3
"""
check_taxonomy_authority.py — Yggdrasil II taxonomy-authority grep guard
                              (PR1 — WARN-ONLY until PR3b)

Scans the production content surface for READ-TIME branch derivation that
should route through the taxonomy authority (src/gaia_cli/taxonomy.py) instead
of re-deriving the branch inline from `type` or from branch-word literals.

  §Ygg-II rubric E1: branch MUST be derived at read-time through the single
  authority — NEVER from `skill.type === 'ultimate'|'unique'|'extra'|'basic'`
  and NEVER from a stored/inlined branch/tier literal.

==============================================================================
WARN-ONLY IN THIS PR (exit 0 always).  The four live resolvers still exist
everywhere (skill-semantics.js, world-tree-layout.js, trustMagnitude.py,
formatting.py) and every consumer still derives inline — so this guard CANNOT
hard-fail yet without RED-building the whole tree.  It emits warnings so the
migration surface is visible and tracked.

  >>> It FLIPS TO HARD-FAIL in PR3b <<<  (once consumers migrate onto
  taxonomy.py and the inline resolvers are deleted).  When flipping: change
  `HARD_FAIL = False` to True below and wire it into the docs-cohesion / guard
  workflow the way check_rank_vocabulary.py is.
==============================================================================

WHAT IT FLAGS  (read-time derivation signatures)
  - `type ===` / `type ==` compared against a branch/type word
    ('unique' | 'suite' | 'ultimate' | 'extra' | 'basic' | 'fusion')
  - branch-word derivation literals used as a resolved branch value:
    'suite' / 'unique' / 'standard' string literals, and the rank words
    Extra / Ultimate / Apex / Unique used as branch derivation.

SCAN SCOPE  (production surfaces only)
  docs/**/*.js
  docs/**/*.html   (INCLUDING inline <script> blocks)
  src/**/*.py
  scripts/**/*.py

EXCLUSIONS
  docs/experiments/**  — sample/experiment surfaces still derive from dead type;
  docs/samples/**         out of scope for the authority cut — tracking issue TBD.
  The authority module + its tests/harness are self-referential and excluded:
  src/gaia_cli/taxonomy.py, tests/**.

Force UTF-8 output on Windows (repo has cp1252 glyphs).
"""

import re
import sys
import fnmatch
from pathlib import Path

# Force UTF-8 output on Windows so unicode chars in print() don't crash.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Warn-only switch — FLIP TO True IN PR3b (see module docstring)
# ---------------------------------------------------------------------------
HARD_FAIL = False


# ---------------------------------------------------------------------------
# Derivation signatures
# ---------------------------------------------------------------------------

# `type === 'unique'` / `type == "extra"` / `type===basic` etc.
BRANCH_TYPE_WORDS = r"(?:unique|suite|ultimate|extra|basic|fusion|standard)"
TYPE_COMPARE = re.compile(
    r"type\s*={2,3}\s*['\"]?" + BRANCH_TYPE_WORDS + r"['\"]?",
    re.IGNORECASE,
)

# Branch-word string literals used as a resolved branch value. We flag the
# quoted branch strings ('suite'|'unique'|'standard') and the rank-word literals
# (Extra|Ultimate|Apex|Unique) that indicate inline branch derivation.
BRANCH_STRING_LITERAL = re.compile(r"""['"](?:suite|unique|standard)['"]""")
RANK_WORD_DERIVATION = re.compile(r"\b(?:Extra|Ultimate|Apex|Unique)\b")

DERIVATION_PATTERNS = [
    (TYPE_COMPARE, "type-compare",
     "read-time branch derivation from `type` — route through taxonomy.resolveDisplayBranch()"),
    (BRANCH_STRING_LITERAL, "branch-literal",
     "inline branch string literal — the resolved branch must come from the authority"),
    (RANK_WORD_DERIVATION, "rank-word-literal",
     "inline rank/branch word — rank words come from taxonomy.rankWord()"),
]


# ---------------------------------------------------------------------------
# Scope / exclusions
# ---------------------------------------------------------------------------

SCAN_GLOBS = [
    "docs/**/*.js",
    "docs/**/*.html",
    "src/**/*.py",
    "scripts/**/*.py",
]

EXCLUDE_GLOBS = [
    # sample/experiment surfaces still derive from dead type; out of scope for
    # the authority cut — tracking issue TBD.
    "docs/experiments/**",
    "docs/samples/**",
    # the authority module + its tests/harness are self-referential.
    "src/gaia_cli/taxonomy.py",
    "tests/**",
    # generated / vendored
    "**/__pycache__/**",
    "docs/assets/**",
]

# Inline <script> extraction for .html files.
SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def isExcluded(relPath: str) -> bool:
    norm = relPath.replace("\\", "/")
    for pattern in EXCLUDE_GLOBS:
        if fnmatch.fnmatch(norm, pattern):
            return True
    return False


def collectFiles(repoRoot: Path):
    seen = set()
    for globPattern in SCAN_GLOBS:
        for p in repoRoot.glob(globPattern):
            if not p.is_file():
                continue
            rel = p.relative_to(repoRoot).as_posix()
            if rel in seen or isExcluded(rel):
                continue
            seen.add(rel)
            yield p, rel


def scanText(text: str, isHtml: bool):
    """Yield (lineno, snippet, label, rationale). For HTML, scan only inline
    <script> blocks (line numbers are relative to the whole file)."""
    if isHtml:
        # Map script-block content back to file line numbers.
        for m in SCRIPT_BLOCK.finditer(text):
            startLine = text.count("\n", 0, m.start(1)) + 1
            block = m.group(1)
            for offset, line in enumerate(block.splitlines()):
                for pattern, label, rationale in DERIVATION_PATTERNS:
                    if pattern.search(line):
                        yield startLine + offset, line.strip()[:120], label, rationale
    else:
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label, rationale in DERIVATION_PATTERNS:
                if pattern.search(line):
                    yield lineno, line.strip()[:120], label, rationale


def scan(repoRoot: Path):
    findings = []  # (rel, lineno, snippet, label, rationale)
    for filePath, rel in collectFiles(repoRoot):
        try:
            text = filePath.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError) as exc:
            print(f"  [SKIP] {rel}: {exc}", file=sys.stderr)
            continue
        isHtml = rel.lower().endswith(".html")
        for lineno, snippet, label, rationale in scanText(text, isHtml):
            findings.append((rel, lineno, snippet, label, rationale))
    return findings


def main():
    repoRoot = Path(__file__).resolve().parent.parent

    print("=== Yggdrasil II Taxonomy-Authority Guard  (PR1 — WARN-ONLY) ===")
    print(f"Repo root : {repoRoot}")
    print("Flags     : read-time branch derivation (type-compare / branch-literal / rank-word-literal)")
    print("Authority : route branch/rank through src/gaia_cli/taxonomy.py")
    print(f"Mode      : {'HARD-FAIL' if HARD_FAIL else 'WARN-ONLY (flips to hard-fail in PR3b)'}")
    print("Excluded  : docs/experiments/**, docs/samples/** (sample surfaces; tracking issue TBD)")
    print()

    findings = scan(repoRoot)

    if findings:
        byFile = {}
        for entry in findings:
            byFile.setdefault(entry[0], []).append(entry)
        severity = "FAIL" if HARD_FAIL else "WARN"
        print(f"-- READ-TIME DERIVATION SITES ({len(findings)} hit(s) across {len(byFile)} file(s)) --")
        for path, entries in sorted(byFile.items()):
            print(f"  [{severity}] {path}  ({len(entries)} hit(s))")
        print()
        if HARD_FAIL:
            print(f"RESULT: FAIL — {len(findings)} derivation site(s) must migrate to taxonomy.py")
            return 1
        print(f"RESULT: PASS (warn-only) — {len(findings)} derivation site(s) tracked for PR3b migration")
        return 0

    print("RESULT: PASS — 0 read-time derivation sites.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
