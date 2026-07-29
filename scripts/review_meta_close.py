#!/usr/bin/env python3
"""review_meta_close.py — mechanical hygiene for closing a review/meta branch.

This script owns the *deterministic* half of the review/meta branch-close
workflow so an agent never has to reinvent the staging allowlist, the CRLF
de-noising, or the leak guards by hand. It does NOT make curation judgments
(calibration stars, Origin, suite promotion, naming) — those are the human/
agent gates in the /gaia-review-meta-close skill.

What it does (all read-only unless --apply):

  status   Report what changed vs origin/main, split into:
             - real-content changes (survive `git diff --ignore-all-space`)
             - EOL-only churn (CRLF<->LF noise; must NOT be committed)
             - forbidden leaks (.venv*, .claude/workflows, founder/handovers)
  stage    Stage ONLY the intended artifact classes, renormalized to LF:
             - registry/named, registry/nodes, registry/suites, registry/*.md
             - docs/graph/* (Class S — Guard E)
             - docs/badges + docs/og ONLY for contributors named via --contributor
           Skips EOL-only churn and refuses to stage leaks.
  validate Run `gaia dev validate` with PYTHONIOENCODING=utf-8 (avoids the
           Windows cp1252 crash on the ✓ glyph) and report pass/fail.
  check    Full preflight: leaks, EOL noise in the index, unresolved conflicts,
           branch name sanity, and whether HEAD is on the expected branch.

Usage:
  python scripts/review_meta_close.py status
  python scripts/review_meta_close.py stage --contributor anthropics,disler --apply
  python scripts/review_meta_close.py validate
  python scripts/review_meta_close.py check

Exit codes: 0 clean / 1 problems found / 2 usage error.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Windows consoles default to cp1252 and choke on the ✓/✅ glyphs the registry
# tooling prints. Force UTF-8 on our own stdout so this script never crashes
# the way `gaia dev validate` does (which is exactly the friction it wraps).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parents[1]

# Paths that must NEVER enter a review/meta PR.
LEAK_PATTERNS = (".venv", ".claude/workflows/", "founder/handovers/")

# Artifact classes this workflow legitimately touches.
REGISTRY_PREFIXES = ("registry/named/", "registry/nodes/", "registry/suites/")
REGISTRY_TRACKED_MD = (
    "registry/combinations.md",
    "registry/real-skills.md",
    "registry/real-skills.html",
    "registry/registry.md",
    "registry/named-skills.json",
)
CLASS_S_GRAPH = "docs/graph/"


def _git(*args: str, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, text=True,
        capture_output=True, check=check,
    ).stdout


def _changed_files(base: str = "origin/main") -> list[str]:
    out = _git("diff", "--name-only", f"{base}...HEAD", check=False)
    tracked = [f for f in out.splitlines() if f.strip()]
    # include working-tree changes too (not yet committed)
    wt = _git("status", "--porcelain", check=False)
    for line in wt.splitlines():
        f = line[3:].strip()
        if f and f not in tracked:
            tracked.append(f)
    return tracked


def _is_leak(path: str) -> bool:
    return any(p in path for p in LEAK_PATTERNS)


def _leak_severity(base: str) -> tuple[list[str], list[str]]:
    """Return (committed_or_staged_leaks, untracked_leaks). Only the first list
    is a hard failure — the second is advisory (don't `git add -A`)."""
    committed = set(
        f.strip() for f in _git("diff", "--name-only", f"{base}...HEAD", check=False).splitlines()
        if f.strip()
    )
    staged = set(
        f.strip() for f in _git("diff", "--cached", "--name-only", check=False).splitlines()
        if f.strip()
    )
    in_pr = {f for f in (committed | staged) if _is_leak(f)}
    untracked = set()
    for line in _git("status", "--porcelain", check=False).splitlines():
        f = line[3:].strip()
        if f and _is_leak(f) and f not in in_pr:
            untracked.add(f)
    return sorted(in_pr), sorted(untracked)


def _real_change_set(base: str) -> set[str]:
    """Files that differ from base ignoring whitespace/EOL (committed + working
    tree + staged), plus untracked files. One batched pass — not per-file."""
    real: set[str] = set()
    # committed diff vs base, ignoring whitespace
    for f in _git("diff", "--ignore-all-space", "--name-only",
                  f"{base}...HEAD", check=False).splitlines():
        if f.strip():
            real.add(f.strip())
    # working-tree + staged, ignoring whitespace
    for extra in (["--ignore-all-space", "--name-only"],
                  ["--ignore-all-space", "--name-only", "--cached"]):
        for f in _git("diff", *extra, check=False).splitlines():
            if f.strip():
                real.add(f.strip())
    # untracked files are real by definition
    for line in _git("status", "--porcelain", check=False).splitlines():
        if line.startswith("??"):
            f = line[3:].strip()
            if f:
                real.add(f)
    return real


def _classify(base: str) -> dict[str, list[str]]:
    real_set = _real_change_set(base)
    real, eol_noise, leaks = [], [], []
    for f in _changed_files(base):
        if _is_leak(f):
            leaks.append(f)
        elif f in real_set:
            real.append(f)
        else:
            eol_noise.append(f)
    return {"real": sorted(real), "eol_noise": sorted(eol_noise), "leaks": sorted(leaks)}


def cmd_status(args) -> int:
    c = _classify(args.base)
    in_pr, untracked = _leak_severity(args.base)
    print(f"vs {args.base}:")
    print(f"  real-content changes : {len(c['real'])}")
    print(f"  EOL-only churn       : {len(c['eol_noise'])}  (do NOT commit)")
    print(f"  leaks in PR          : {len(in_pr)}  (HARD FAIL if >0)")
    print(f"  untracked leaks      : {len(untracked)}  (advisory — never `git add -A`)")
    if args.verbose:
        for k in ("real", "eol_noise"):
            if c[k]:
                print(f"\n[{k}]")
                for f in c[k][:200]:
                    print(f"  {f}")
        if untracked:
            print("\n[untracked leaks — leave alone]")
            for f in untracked:
                print(f"  {f}")
    return 1 if in_pr else 0


def _contributor_asset_globs(contribs: list[str]) -> list[str]:
    globs = []
    for c in contribs:
        globs.append(f"docs/badges/_assets/{c}/")
        globs.append(f"docs/og/{c}/")
    return globs


def cmd_stage(args) -> int:
    contribs = [c.strip() for c in (args.contributor or "").split(",") if c.strip()]
    c = _classify(args.base)

    allow = list(REGISTRY_PREFIXES) + [CLASS_S_GRAPH, "docs/badges/registry.json"]
    allow += list(REGISTRY_TRACKED_MD)
    allow += _contributor_asset_globs(contribs)

    to_stage = []
    for f in c["real"]:
        if any(f.startswith(a) or f == a for a in allow):
            to_stage.append(f)

    print(f"Would stage {len(to_stage)} real-content files "
          f"({len(contribs)} contributor(s): {', '.join(contribs) or 'none'}):")
    for f in to_stage[:200]:
        print(f"  + {f}")
    skipped = [f for f in c["real"] if f not in to_stage]
    if skipped:
        print(f"\nSkipped {len(skipped)} real changes OUTSIDE the allowlist "
              f"(review these — may be version-churn or need --contributor):")
        for f in skipped[:60]:
            print(f"  - {f}")

    if not args.apply:
        print("\n(dry-run — pass --apply to stage)")
        return 0

    for f in to_stage:
        _git("add", "--renormalize", "--", f, check=False)
    print(f"\nStaged {len(to_stage)} files (renormalized to LF).")
    return 0


def cmd_validate(args) -> int:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["GAIA_OPERATOR_OVERRIDE"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    r = subprocess.run(
        [sys.executable, "-m", "gaia_cli", "dev", "validate"],
        cwd=REPO_ROOT, env=env, text=True, capture_output=True,
        encoding="utf-8", errors="replace",
    )
    out = (r.stdout or "") + (r.stderr or "")
    tail = out.splitlines()[-12:]
    print("\n".join(tail))
    passed = "All validation checks passed" in (r.stdout or "")
    print("\nVALIDATE:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def cmd_check(args) -> int:
    problems = 0
    branch = _git("rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
    print(f"branch: {branch}")
    if not branch.startswith("review/meta/"):
        print("  WARN: not on a review/meta/ branch")
    conflicts = _git("diff", "--name-only", "--diff-filter=U", check=False).strip()
    if conflicts:
        print("  FAIL: unresolved merge conflicts:")
        for f in conflicts.splitlines():
            print(f"    {f}")
        problems += 1
    c = _classify(args.base)
    in_pr_leaks, untracked_leaks = _leak_severity(args.base)
    if in_pr_leaks:
        print(f"  FAIL: {len(in_pr_leaks)} leak(s) staged/committed in PR:")
        for f in in_pr_leaks[:40]:
            print(f"    {f}")
        problems += 1
    if untracked_leaks:
        print(f"  WARN: {len(untracked_leaks)} untracked leak file(s) present "
              f"— never `git add -A`; stage explicitly.")
    # EOL noise in the *index* (already staged) is a defect; working-tree noise is fine.
    real_set = _real_change_set(args.base)
    staged = _git("diff", "--cached", "--name-only", check=False).splitlines()
    staged_noise = [f for f in staged if f and not _is_leak(f) and f not in real_set]
    if staged_noise:
        print(f"  FAIL: {len(staged_noise)} EOL-only file(s) staged (unstage them):")
        for f in staged_noise[:40]:
            print(f"    {f}")
        problems += 1
    print("CHECK:", "CLEAN" if problems == 0 else f"{problems} problem(s)")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="review/meta branch-close hygiene")
    ap.add_argument("--base", default="origin/main", help="base ref (default origin/main)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="classify changes: real / EOL-noise / leaks")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(func=cmd_status)

    st = sub.add_parser("stage", help="stage only intended artifacts (LF-normalized)")
    st.add_argument("--contributor", help="comma-separated handles whose badges/og to include")
    st.add_argument("--apply", action="store_true", help="actually stage (default dry-run)")
    st.set_defaults(func=cmd_stage)

    v = sub.add_parser("validate", help="gaia dev validate with UTF-8 stdout")
    v.set_defaults(func=cmd_validate)

    ch = sub.add_parser("check", help="preflight: leaks, conflicts, staged EOL noise")
    ch.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
