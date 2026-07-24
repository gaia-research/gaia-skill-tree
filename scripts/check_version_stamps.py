#!/usr/bin/env python3
"""
check_version_stamps.py — CI guard against stale HARDCODED version stamps

A `window.GAIA_VERSION = "4.3.12";` literal was hand-typed into
src/gaia_cli/graph.py on 2026-06-09 and rotted silently for 6 weeks (the repo
moved to 6.8.15) with nothing catching it: verify_lockstep.py checks only the
four manifests (not source), the docs `--check` normalizes the stamp away
before comparing, and the CLI's HTML output is not a tracked docs/ file. This
guard closes that gap.

THE DISCRIMINATOR — literal vs. interpolated
  VIOLATION : window.GAIA_VERSION = "4.3.12";      (a literal \\d+\\.\\d+\\.\\d+)
  PASS      : window.GAIA_VERSION = "{version}";   (Python f-string interp)
              window.GAIA_VERSION = "{{ version }}"; (Jinja interp)
  These interpolated forms have `{` where the digits would be, so a literal-
  semver regex never matches them. The guard fails ONLY on the hardcoded form.

EXIT CODES
  0  — clean (zero literal-semver GAIA_VERSION stamps in scope)
  1  — one or more literal-semver stamps found in a non-allowlisted file

SCAN SCOPE  (keeps false positives near-zero)
  src/**                   — CLI source and templates
  registry/render/**       — checked-in sample render output

  NOT scanned (each would flood false positives):
    docs/**                — build OUTPUT; fixed by regen, covered by other guards
    tests/**               — fixtures legitimately hardcode versions like "9.9.9"
    scripts/**/templates/*.j2 — Jinja {{ }} forms pass the regex anyway

ALLOWLIST_PATHS
  Intentionally EMPTY. The known offenders are FIXED in-tree, not whitelisted.
  Present for future ergonomics, matching check_rank_vocabulary.py /
  validate_redaction.py.
"""

import re
import sys
from pathlib import Path

# Force UTF-8 output on Windows so unicode chars in print() don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ---------------------------------------------------------------------------
# The literal-semver stamp pattern.
# Matches ONLY the hardcoded form (digits between the quotes); interpolated
# forms — "{version}" (f-string) or "{{ version }}" (Jinja) — never match
# because a literal-semver regex requires digits where the `{` sits.
# ---------------------------------------------------------------------------

LITERAL_STAMP = re.compile(r'''window\.GAIA_VERSION\s*=\s*["']\d+\.\d+\.\d+["']''')

# ---------------------------------------------------------------------------
# Scan scope — glob roots relative to repo root.
# ---------------------------------------------------------------------------

SCAN_GLOBS = [
    'src/**/*',
    'registry/render/**/*',
]

# ---------------------------------------------------------------------------
# Allowlist — paths (relative to repo root, POSIX) exempted from the guard.
# EMPTY: the known offenders are fixed in-tree, not whitelisted. Present for
# future ergonomics only.
# ---------------------------------------------------------------------------

ALLOWLIST_PATHS = frozenset()


def is_allowlisted(rel_path: str) -> bool:
    """Return True if this path is exempt from the guard."""
    return rel_path.replace('\\', '/') in ALLOWLIST_PATHS


def collect_files(repo_root: Path):
    """Yield (Path, rel_path_str) for every file in the scan scope."""
    seen: set[str] = set()
    for glob in SCAN_GLOBS:
        for p in repo_root.glob(glob):
            if not p.is_file():
                continue
            rel = p.relative_to(repo_root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            yield p, rel


def scan(repo_root: Path):
    hard_violations: list[tuple[str, int, str]] = []  # (rel_path, lineno, snippet)
    soft_violations: list[tuple[str, int, str]] = []  # same, but allowlisted

    for file_path, rel_path in collect_files(repo_root):
        try:
            text = file_path.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError) as exc:
            print(f'  [SKIP] {rel_path}: {exc}', file=sys.stderr)
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            if LITERAL_STAMP.search(line):
                entry = (rel_path, lineno, line.strip()[:120])
                if is_allowlisted(rel_path):
                    soft_violations.append(entry)
                else:
                    hard_violations.append(entry)

    return hard_violations, soft_violations


def main():
    print('=== Version Stamp Guard ===')
    print(f'Repo root : {REPO_ROOT}')
    print(f'Scope     : src/**, registry/render/**')
    print(f'Fails on  : literal-semver window.GAIA_VERSION = "X.Y.Z" (interpolated forms pass)')
    print()

    hard, soft = scan(REPO_ROOT)

    if soft:
        print('-- ALLOWLISTED (warn, does not fail CI) --')
        for rel_path, lineno, snippet in soft:
            print(f'  [WARN] {rel_path}:{lineno}  {snippet!r}')
        print()

    if hard:
        print('-- HARD VIOLATIONS (must fix before merging) --')
        for rel_path, lineno, snippet in hard:
            print(f'  [FAIL] {rel_path}:{lineno}  {snippet!r}')
            print(f'           → hardcoded version stamp; interpolate it dynamically instead '
                  f'(e.g. f\'window.GAIA_VERSION = "{{version}}";\'). '
                  f'See CLAUDE.md § "Decorative assets must NOT carry version metadata".')
        print()
        print(f'RESULT: FAIL — {len(hard)} literal stamp(s) in {len({h[0] for h in hard})} file(s)')
        return 1

    print('RESULT: PASS — 0 literal version stamps in scope.')
    if soft:
        print(f'         ({len(soft)} allowlisted hit(s) — warn only)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
