#!/usr/bin/env python3
"""
check_taxonomy_authority.py — Yggdrasil II taxonomy-authority grep guard
                              (HARD-FAIL as of PR3b)

Scans the production content surface for READ-TIME branch derivation that
should route through the taxonomy authority (src/gaia_cli/taxonomy.py) instead
of re-deriving the branch inline from `type`, or by calling one of the deleted
legacy resolvers.

  §Ygg-II rubric E1: branch MUST be derived at read-time through the single
  authority — NEVER from `skill.type === 'ultimate'|'unique'|'extra'` and NEVER
  by calling a legacy resolver shim.

==============================================================================
HARD-FAIL (exit 1 on any finding).  PR3b migrated every consumer onto
taxonomy.py and DELETED the four inline resolvers (skill-semantics.js +
world-tree-layout.js compute mirrors kept ONLY as the frozen starless-graph
fallback; trustMagnitude.computeBranch + formatting.rank_word/format_rank_label
hard-deleted).  The guard now flips to hard-fail so a NEW type->branch read or a
resurrected shim call RED-builds.
==============================================================================

WHAT IT FLAGS  (genuine read-time derivation / deleted-shim signatures)
  - `.type === 'unique'|'ultimate'|'extra'` (or `==` / `!==` / `!=`): a direct
    `type`-property read deriving a BRANCH decision from a DEAD Yggdrasil-I
    branch-carrying type word. `type === 'basic'|'fusion'` is NOT flagged —
    those are the live type axis, not a branch derivation; `type === 'suite'`
    reads a RESOLVED branch value (the correct post-migration pattern).
  - a call to a deleted resolver shim: `trustMagnitude.computeBranch(...)`,
    `rank_word(...)`, `format_rank_label(...)` (all removed in PR3b — any live
    call is a stale reference).

WHAT IT DELIBERATELY DOES NOT FLAG  (post-migration correct patterns / noise)
  - membership checks on the RESOLVED branch var: `branch === 'unique'`,
    `skill.branch === 'suite'` — the CORRECT pattern.
  - string-key access `skill['type']` / `.get('type')` — indistinguishable from
    any dict read; branch-word string literals, CSS `var(--tier-unique)`,
    `data-branch="unique"`, object keys (`unique: tier('unique')`), and the
    `fusion-recipe` evidence-type reads are all out of the derivation signature.
  - comment / docstring lines (prose that mentions the dead words).

SCAN SCOPE  (production surfaces only)
  docs/**/*.js
  docs/**/*.html   (INCLUDING inline <script> blocks)
  src/**/*.py
  scripts/**/*.py

EXCLUSIONS  (see EXCLUDE_GLOBS for per-entry rationale)
  docs/experiments/**, docs/samples/**  — sample surfaces, out of the cut.
  the authority module + its tests/harness are self-referential.
  the two FROZEN-FALLBACK resolvers (skill-semantics.js, world-tree-layout.js)
  — their `type ===` reads live inside an explicitly-documented starless-graph
  fallback block gated behind the emitted-branch read (Task A-C retained code).
  two un-migrated docs surfaces (page-ia.js, badges/index.html) carrying dead
  Ygg-I `.type` reads owned by the frontend-migration lane — file-scoped
  exemptions (narrower than blinding the pattern; the guard still watches every
  other docs/src/scripts file for NEW derivation).
  this guard file itself (its docstring quotes the flagged signatures).

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
# Hard-fail switch — flipped True in PR3b (see module docstring)
# ---------------------------------------------------------------------------
HARD_FAIL = True


# ---------------------------------------------------------------------------
# Derivation signatures
# ---------------------------------------------------------------------------

# Dead Yggdrasil-I branch-carrying `type` values. NOT basic/fusion (live type
# axis) and NOT suite/standard (resolved branch values, read via the `branch`
# var — the correct post-migration pattern).
DEAD_TYPE_WORDS = r"(?:unique|ultimate|extra)"

# `.type === 'unique'` / `node.type == "ultimate"` / `type !== 'extra'` — a
# WHOLE-WORD `type` property (the negative lookbehind rejects normType, skType,
# skill_type, legacy_type, rawType, and the ['type']/"type" string-key forms)
# compared against a dead branch-word. This is the genuine type->branch read.
TYPE_COMPARE = re.compile(
    r"(?<![\w'\"])type['\"]?\]?\s*[=!]={1,2}\s*['\"]" + DEAD_TYPE_WORDS + r"['\"]",
    re.IGNORECASE,
)

# Calls to resolvers DELETED in PR3b. `trustMagnitude.computeBranch(...)` and the
# two formatting shims `rank_word(...)` / `format_rank_label(...)`. The
# lookbehind lets `taxonomy.rankWord(...)` (the authority) through and only
# matches a bare/dotted call form of the removed names.
SHIM_CALL = re.compile(
    r"(?:trustMagnitude\.computeBranch\s*\("
    r"|(?<![\w.])rank_word\s*\("
    r"|(?<![\w.])format_rank_label\s*\()"
)

DERIVATION_PATTERNS = [
    (TYPE_COMPARE, "type-branch",
     "read-time branch derivation from `type` — route through taxonomy.branchFor()"),
    (SHIM_CALL, "deleted-shim",
     "call to a resolver deleted in PR3b — use taxonomy.branchFor()/rankWord()"),
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
    # this guard's own docstring quotes the flagged signatures.
    "scripts/check_taxonomy_authority.py",
    # FROZEN-FALLBACK resolvers: their `type ===` reads live inside an
    # explicitly-documented starless-graph fallback block gated behind the
    # emitted-branch read. Retained by the PR3b frontend lane (Task A-C) as the
    # sole fallback for docs/graph/gaia.json generics (no emitted branch).
    "docs/js/skill-semantics.js",
    "docs/js/world-tree-layout.js",
    # Un-migrated docs surfaces carrying dead Ygg-I `.type` reads owned by the
    # frontend-migration lane; file-scoped (the guard still watches every other
    # docs/src/scripts file for NEW derivation).
    "docs/js/page-ia.js",
    "docs/badges/index.html",
    # generated / vendored
    "**/__pycache__/**",
    "docs/assets/**",
]

# Inline <script> extraction for .html files.
SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def isComment(line: str, isPython: bool) -> bool:
    """Prose comment / docstring line — the dead words appear here descriptively,
    not as a derivation. JS `//` `*` `/*`; Python `#`."""
    stripped = line.strip()
    if isPython:
        return stripped.startswith("#")
    return stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*")


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


def scanText(text: str, isHtml: bool, isPython: bool):
    """Yield (lineno, snippet, label, rationale). For HTML, scan only inline
    <script> blocks (line numbers are relative to the whole file). Comment lines
    are skipped (prose mention of the dead words is not a derivation)."""
    if isHtml:
        # Map script-block content back to file line numbers.
        for m in SCRIPT_BLOCK.finditer(text):
            startLine = text.count("\n", 0, m.start(1)) + 1
            block = m.group(1)
            for offset, line in enumerate(block.splitlines()):
                if isComment(line, isPython=False):
                    continue
                for pattern, label, rationale in DERIVATION_PATTERNS:
                    if pattern.search(line):
                        yield startLine + offset, line.strip()[:120], label, rationale
    else:
        for lineno, line in enumerate(text.splitlines(), start=1):
            if isComment(line, isPython):
                continue
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
        isPython = rel.lower().endswith(".py")
        for lineno, snippet, label, rationale in scanText(text, isHtml, isPython):
            findings.append((rel, lineno, snippet, label, rationale))
    return findings


def main():
    repoRoot = Path(__file__).resolve().parent.parent

    print("=== Yggdrasil II Taxonomy-Authority Guard  (PR3b — HARD-FAIL) ===")
    print(f"Repo root : {repoRoot}")
    print("Flags     : `.type ==/=== unique|ultimate|extra` reads + deleted-shim calls")
    print("Authority : route branch/rank through src/gaia_cli/taxonomy.py")
    print(f"Mode      : {'HARD-FAIL' if HARD_FAIL else 'WARN-ONLY'}")
    print("Excluded  : experiments/samples, frozen-fallback resolvers, un-migrated docs surfaces (see EXCLUDE_GLOBS)")
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
            for _rel, lineno, snippet, label, rationale in entries:
                print(f"      L{lineno} [{label}] {snippet}")
                print(f"        -> {rationale}")
        print()
        if HARD_FAIL:
            print(f"RESULT: FAIL — {len(findings)} derivation site(s) must migrate to taxonomy.py")
            return 1
        print(f"RESULT: PASS (warn-only) — {len(findings)} derivation site(s) tracked")
        return 0

    print("RESULT: PASS — 0 read-time derivation sites.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
