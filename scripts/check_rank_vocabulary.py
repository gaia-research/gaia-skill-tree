#!/usr/bin/env python3
"""
check_rank_vocabulary.py — Yggdrasil II banned-synonym CI guard  (Refs #999)

Scans the canonical content surface for banned rank/taxonomy vocabulary that
was valid under Yggdrasil I but must not appear in new canonical content under
Yggdrasil II (ratified 2026-07-07).

EXIT CODES
  0  — clean (zero hard violations outside the documented allowlist)
  1  — one or more hard violations found in non-allowlisted files

BANNED PATTERNS
  \\bTranscendent\\b      — old 5★ rank name; now "Ultimate" (Suite) / "Unique Ultimate" (Unique)
  \\bHardened\\b          — old 4★ rank name; now "Extra" (Suite) / "Unique" (Unique branch)
  \\bExtra\\s+Skill\\b    — old taxonomy type label; now "Fusion Skill" / type=fusion
  \\bUltimate\\s+Skill\\b — old taxonomy type label; same replacement

  NOTE: "Extra" alone and "Ultimate" alone are VALID Yggdrasil II rank words and
  are NOT banned.  The regexes above use word-boundary matching so a bare "Ultimate"
  in "5★ Ultimate" passes, while "Ultimate Skill" fails.

ALLOWED (v2 vocabulary — never flagged)
  1★ Awakened · 2★ Named · 3★ Evolved
  Suite: 4★ Extra · 5★ Ultimate · 6★ Apex
  Unique: 4★ Unique · 5★ Unique Ultimate · 6★ Unique Impossible
  Types (field value): basic · fusion

SCAN SCOPE  (content surface only)
  registry/**              — registry data files
  *.md                     — root-level canonical prose docs
  docs/**/*.md             — site docs
  founder/handovers/**/*.md — handover docs

HARD EXCLUSIONS  (never scanned — see inline comments for each)
  scripts/**               — blocked; scripts need #996 CLI branch-awareness first
  docs/assets/**           — generated image/data artifacts; out of scope
  docs/badges/**           — generated badge SVGs; out of scope
  **/*.html                — HTML files; out of scope per task spec
  registry/schema/**       — schema definitions; require coordinated #996 CLI work
  registry/render/**       — generated render artifacts
  registry/real-skills.*   — generated catalog dump
  registry/similarity.json — generated similarity index

PRE-EXISTING VIOLATIONS (allowlist — warn, do NOT fail CI)
  All files listed in ALLOWLIST_PATHS below are confirmed to contain old
  vocabulary as of 2026-07-14.  They are tracked for cleanup under issue #994.
  The guard REPORTS them but does NOT fail CI on them, so the guard is green
  today while still catching any NEW violations introduced on future PRs.
"""

import re
import sys
import os
import fnmatch
from pathlib import Path

# Force UTF-8 output on Windows so unicode chars in print() don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Banned patterns (compiled once)
# ---------------------------------------------------------------------------

BANNED_PATTERNS = [
    # Pattern,  human label,  rationale
    (re.compile(r'\bTranscendent\b'),     'Transcendent',    'old 5★ rank name — use Ultimate / Unique Ultimate'),
    (re.compile(r'\bHardened\b'),         'Hardened',        'old 4★ rank name — use Extra (Suite) / Unique (Unique branch)'),
    (re.compile(r'\bExtra\s+Skill\b'),    'Extra Skill',     'old taxonomy type label — use Fusion Skill / type=fusion'),
    (re.compile(r'\bUltimate\s+Skill\b'), 'Ultimate Skill',  'old taxonomy type label — use Fusion Skill / type=fusion'),
]

# ---------------------------------------------------------------------------
# Hard exclusions — globs relative to repo root; matching files are NEVER scanned
# ---------------------------------------------------------------------------

HARD_EXCLUDE_GLOBS = [
    # Scripts: require #996 CLI branch-awareness before vocabulary clean-up
    'scripts/**',
    # Generated image / data artifacts
    'docs/assets/**',
    'docs/badges/**',
    # HTML files (*.html at any depth)
    '**/*.html',
    # Schema definitions — coordinated with #996 CLI work
    'registry/schema/**',
    # Generated render artifacts
    'registry/render/**',
    # Generated catalog dumps (root-level)
    'registry/real-skills.*',
    'registry/similarity.json',
]

# ---------------------------------------------------------------------------
# Pre-existing violation allowlist
# Paths (relative to repo root) that are known to contain old vocabulary as of
# the initial guard deploy (2026-07-14).  Tracked for cleanup under #994.
# The guard WARNS on these but does NOT fail CI.
# ---------------------------------------------------------------------------

ALLOWLIST_PATHS = {
    # ── Guard reference doc (documents the banned terms by definition) ─────
    'docs/rank-vocabulary-guard.md',  # This IS the guard ref doc; must name the banned terms

    # ── Root canonical docs (pre-Yggdrasil-II prose still in flight) ────────
    'CONTEXT.md',           # Lexicon entries explicitly documenting deprecated terms
    'DESIGN.md',            # Legacy rank colour/animation table; refs old rank names
    'GOVERNANCE.md',        # Old "4★ Hardened" threshold + Ultimate/Extra Skill tier names
    'META.md',              # Old rank table (§1.1) + taxonomy table (§1.2)
    'PRODUCT.md',           # Product copy referencing old 6★ "Transcendent ★" label

    # ── Registry data (cannot modify schema/data; tracked under #994) ────────
    'registry/combinations.md',   # 124 "Extra Skill" taxonomy labels in combination rows
    'registry/registry.md',       # Mirror of combinations.md

    # ── docs/** pre-Yggdrasil-II docs ────────────────────────────────────────
    'docs/agent.md',                                         # Old taxonomy definitions
    'docs/agents/frontend-known-issues.md',                  # Historical "Transcendent ★" ref
    'docs/archive/CONTEXT.2026-05-16.md',                    # Frozen snapshot
    'docs/archive/DESIGN.2026-05-16.md',                     # Frozen snapshot
    'docs/archive/META_AUDIT_HANDOVER.md',                   # Frozen handover
    'docs/archive/PLAN.2026-05-18.md',                       # Frozen plan
    'docs/archive/SPEC.md',                                   # Frozen spec
    'docs/archive/TIMELINE_HANDOVER.md',                     # Frozen handover
    'docs/audits/2026-05-07-openai-named-and-level-iv-plus.md',  # Pre-Yggdrasil-II audit
    'docs/audits/2026-05-17-meta-audit.md',                  # Pre-Yggdrasil-II audit
    'docs/en/DOCS.md',                                        # Legacy taxonomy table
    'docs/en/MEMORY.md',                                      # Historical session memory
    'docs/en/ROUTINE_PROMPT.md',                              # Old-vocabulary prompt
    'docs/examples/example_extra_skill.md',                   # Legacy example doc
    'docs/meta/2026-05-31-starless-skills-update.md',         # Pre-Yggdrasil-II meta post
    'docs/meta/2026-06-curate-chain-starless.md',             # Pre-Yggdrasil-II curate post
    'docs/meta/2026-06-trust-methodology.md',                 # Historical methodology
    'docs/okf/index.md',                                      # OKF index: old tier section headers
    'docs/okf/skills/extra/index.md',                         # OKF "Extra Skills" index
    'docs/okf/skills/ultimate/index.md',                      # OKF "Ultimate Skills" index
    'docs/plans/firecrawl-skills-suite.md',                   # Plan doc pre-Yggdrasil-II
    'docs/superpowers/plans/2026-05-14-hunters-atlas-redesign.md',  # Design plan with old labels

    # ── founder/handovers/** ─────────────────────────────────────────────────
    # AOV/ascension-overdrive design docs — hard-excluded from content review per task spec
    'founder/handovers/design-v6.1.1-ascension-overdrive-commissions.md',
    'founder/handovers/design-v6.1.1-ascension-overdrive-commissions-v2.md',
    'founder/handovers/design-v6.1.1-ascension-overdrive-commissions-v3.md',
    'founder/handovers/design-v6.1.1-ascension-overdrive-shape.md',
    'founder/handovers/design-v6.1.1-ascension-overdrive-shape-v2.md',
    'founder/handovers/design-v6.1.1-ascension-overdrive-shape-v3.md',
    'founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md',  # Ratification doc references both old and new terms
    'founder/handovers/done/TRUST_METHODOLOGY_REPORT.md',         # Historical report
    'founder/handovers/done/g7-mattpocock-audit/_workflow_notes.md',  # Historical workflow notes
    'founder/handovers/phase-1.5/issues/I8.md',                   # Historical issue doc
}

# Also allowlist entire docs/archive/ subtree (all are frozen pre-Yggdrasil snapshots)
ALLOWLIST_SUBTREES = [
    'docs/archive/',
]

# ---------------------------------------------------------------------------
# File collection helpers
# ---------------------------------------------------------------------------

def is_hard_excluded(rel_path: str) -> bool:
    """Return True if this path matches any hard-exclude glob."""
    for pattern in HARD_EXCLUDE_GLOBS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Also check against the path with forward slashes normalised
        if fnmatch.fnmatch(rel_path.replace('\\', '/'), pattern):
            return True
    return False


def is_allowlisted(rel_path: str) -> bool:
    """Return True if this path is in the documented pre-existing allowlist."""
    norm = rel_path.replace('\\', '/')
    if norm in ALLOWLIST_PATHS:
        return True
    for subtree in ALLOWLIST_SUBTREES:
        if norm.startswith(subtree):
            return True
    return False


def collect_files(repo_root: Path):
    """Yield (Path, rel_path_str) for every file in the scan scope."""

    def _yield(pattern_iter):
        for p in pattern_iter:
            if not p.is_file():
                continue
            rel = p.relative_to(repo_root).as_posix()
            if is_hard_excluded(rel):
                continue
            yield p, rel

    # 1. registry/** — all files
    yield from _yield(repo_root.glob('registry/**/*'))

    # 2. *.md at root
    yield from _yield(repo_root.glob('*.md'))

    # 3. docs/**/*.md
    yield from _yield(repo_root.glob('docs/**/*.md'))

    # 4. founder/handovers/**/*.md
    yield from _yield(repo_root.glob('founder/handovers/**/*.md'))


# ---------------------------------------------------------------------------
# Main scan logic
# ---------------------------------------------------------------------------

def scan(repo_root: Path):
    hard_violations: list[tuple[str, int, str, str, str]] = []  # (rel_path, lineno, match, label, rationale)
    soft_violations: list[tuple[str, int, str, str, str]] = []  # same, but in allowlist

    seen_files: set[str] = set()

    for file_path, rel_path in collect_files(repo_root):
        if rel_path in seen_files:
            continue
        seen_files.add(rel_path)

        try:
            text = file_path.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError) as exc:
            print(f'  [SKIP] {rel_path}: {exc}', file=sys.stderr)
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label, rationale in BANNED_PATTERNS:
                if pattern.search(line):
                    entry = (rel_path, lineno, line.strip()[:120], label, rationale)
                    if is_allowlisted(rel_path):
                        soft_violations.append(entry)
                    else:
                        hard_violations.append(entry)

    return hard_violations, soft_violations


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_violations(violations, *, severity: str):
    for rel_path, lineno, snippet, label, rationale in violations:
        print(f'  [{severity}] {rel_path}:{lineno}  [{label}]  {snippet!r}')
        print(f'           → {rationale}')


def main():
    repo_root = Path(__file__).resolve().parent.parent

    print('=== Yggdrasil II Rank Vocabulary Guard  (Refs #999) ===')
    print(f'Repo root : {repo_root}')
    print(f'Banned    : Transcendent, Hardened, "Extra Skill", "Ultimate Skill"')
    print(f'Allowed   : Extra, Ultimate, (all other Yggdrasil II rank words)')
    print()

    hard, soft = scan(repo_root)

    # ── Allowlisted / pre-existing violations (warn) ─────────────────────────
    if soft:
        # Group by file for readability
        from itertools import groupby
        print(f'-- PRE-EXISTING VIOLATIONS (allowlisted, pending #994 cleanup) --')
        by_file = {}
        for entry in soft:
            by_file.setdefault(entry[0], []).append(entry)
        for path, entries in sorted(by_file.items()):
            print(f'  [WARN] {path}  ({len(entries)} hit(s))')
        print(f'  Total pre-existing: {len(soft)} hit(s) across {len(by_file)} file(s)')
        print()

    # ── Hard violations ───────────────────────────────────────────────────────
    if hard:
        print(f'-- HARD VIOLATIONS (must fix before merging) --')
        print_violations(hard, severity='FAIL')
        print()
        print(f'RESULT: FAIL — {len(hard)} hard violation(s) in {len({h[0] for h in hard})} file(s)')
        return 1

    print(f'RESULT: PASS — 0 hard violations.')
    if soft:
        print(f'         ({len(soft)} pre-existing allowlisted hits in {len({s[0] for s in soft})} file(s) — tracked under #994)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
