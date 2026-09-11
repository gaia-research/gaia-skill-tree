#!/usr/bin/env python3
"""Run the lightweight PR guards in one pass.

Six single-script guards used to be six workflows, each paying ~30s of
checkout and setup for 0-2s of work. This runner is the one job that replaced
them (.github/workflows/pr-guards.yml), and the same command runs locally
before a push:

    python scripts/pr_guards.py              # guards touched since origin/main
    python scripts/pr_guards.py --all        # every guard
    python scripts/pr_guards.py --dry-run    # list what would run

Each guard keeps the path globs its old workflow triggered on, so a PR runs the
same guards it ran before. Touching this file or the workflow runs all of them.
Every selected guard runs even after an earlier one fails, so one push surfaces
every failure. tests/test_pr_guards.py keeps the workflow's `paths:` equal to
the union of the globs below.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# Changing the runner itself re-runs every guard.
RUNNER = ["scripts/pr_guards.py", ".github/workflows/pr-guards.yml"]


def checkPickleRefs() -> Optional[str]:
    """Safe weight format check, carried over from license-check.yml."""
    for rel in ("registry/gaia.json", "docs/graph/gaia.json"):
        path = ROOT / rel
        if not path.is_file():
            continue
        if re.search(r"\.(pkl|pickle)", path.read_text(encoding="utf-8", errors="replace"), re.IGNORECASE):
            return f"::error::Pickle format detected in {rel}"
    print("All model weight references are in safe formats.")
    return None


Step = Union[list, Callable[[], Optional[str]]]


@dataclass
class Guard:
    name: str
    title: str
    steps: list
    paths: list
    node: bool = False


GUARDS = [
    Guard(
        "html-sink",
        "HTML sink guard (pre-CodeQL DOM-XSS, warn-only) + classifier self-tests",
        [[PY, "scripts/check_html_sinks.py"], [PY, "scripts/check_html_sinks.py", "--selftest"]],
        ["docs/**/*.js", "docs/**/*.html", "scripts/check_html_sinks.py"],
    ),
    Guard(
        "rank-vocabulary",
        "Yggdrasil II banned-synonym check (Refs #999)",
        [[PY, "scripts/check_rank_vocabulary.py"]],
        ["registry/**", "*.md", "docs/**/*.md", "founder/handovers/**/*.md", "scripts/check_rank_vocabulary.py"],
    ),
    Guard(
        "taxonomy-authority",
        "Yggdrasil II branch-authority check (Refs #999)",
        [[PY, "scripts/check_taxonomy_authority.py"]],
        ["docs/**/*.js", "docs/**/*.html", "src/**/*.py", "scripts/**/*.py", "scripts/check_taxonomy_authority.py"],
    ),
    Guard(
        "version-stamp",
        "Version stamp guard (literal-semver GAIA_VERSION)",
        [[PY, "scripts/check_version_stamps.py"]],
        ["src/**", "registry/render/**", "scripts/check_version_stamps.py"],
    ),
    # Ratified V5-8 (issue #1337). check-lexicon.ts is vendored byte-identical
    # from gaia-research; the self-tests run first because a broken gate that
    # reports "clean" is worse than no gate, and they pin the vendored sha256.
    Guard(
        "lexicon",
        "Vocabulary gate + self-tests (federated lexicon)",
        [
            ["npx", "--yes", "tsx", "scripts/lexicon/check-lexicon.test.ts"],
            ["npx", "--yes", "tsx", "scripts/lexicon/check-lexicon.ts"],
        ],
        [
            "founder/**", "docs/agents/**", "docs/*.md", "packages/*/README.md", "scripts/lexicon/**",
            "CLAUDE.md", "CONTEXT.md", "CONTRIBUTING.md", "DEV.md", "README.md",
        ],
        node=True,
    ),
    Guard(
        "license",
        "License compatibility + safe weight format",
        [["npx", "--yes", "tsx", "scripts/validate-licenses.ts"], checkPickleRefs],
        ["registry/gaia.json", "docs/graph/gaia.json", "scripts/validate-licenses.ts", "scripts/license-matrix.json"],
        node=True,
    ),
]


def globToRegex(pattern: str) -> re.Pattern:
    """Translate a GitHub Actions `paths:` glob. `*` stops at `/`; `**` does not."""
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(path: str, globs: list) -> bool:
    return any(globToRegex(g).match(path) for g in globs)


def selectGuards(files: Optional[list], runAll: bool = False) -> list:
    if runAll or files is None or any(f in RUNNER for f in files):
        return list(GUARDS)
    return [g for g in GUARDS if any(matches(f, g.paths) for f in files)]


def workflowPaths() -> set:
    """Every path that should trigger the workflow: all guard globs plus the runner."""
    return {p for g in GUARDS for p in g.paths} | set(RUNNER)


def changedFiles(base: str) -> Optional[list]:
    """Files changed since the merge base with `base`, including uncommitted and untracked files."""

    def git(*cmd: str) -> str:
        return subprocess.run(["git", *cmd], cwd=ROOT, capture_output=True, text=True, check=True).stdout

    try:
        mergeBase = git("merge-base", base, "HEAD").strip()
        listing = git("diff", "--name-only", mergeBase) + git("ls-files", "--others", "--exclude-standard")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return sorted({line for line in listing.splitlines() if line})


def runStep(step: Step, env: dict) -> Optional[str]:
    if callable(step):
        return step()
    code = subprocess.run(step, cwd=ROOT, env=env).returncode
    label = " ".join(["python", *step[1:]] if step[0] == PY else step)
    return None if code == 0 else f"`{label}` exited {code}"


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="run every guard regardless of changed files")
    parser.add_argument("--files-from", help="file listing changed paths, one per line (CI passes the PR diff)")
    parser.add_argument("--base", default="origin/main", help="ref to diff against locally (default: origin/main)")
    parser.add_argument("--dry-run", action="store_true", help="print the selected guards and exit")
    args = parser.parse_args(argv)

    if args.files_from:
        files = [line.strip() for line in Path(args.files_from).read_text(encoding="utf-8").splitlines() if line.strip()]
    elif args.all:
        files = None
    else:
        files = changedFiles(args.base)
        if files is None:
            print(f"Could not diff against {args.base}; running every guard.")

    selected = selectGuards(files, runAll=args.all)
    if args.dry_run:
        for g in selected:
            print(f"{g.name}: {g.title}")
        return 0
    if not selected:
        print("No guard paths changed; nothing to run.")
        return 0

    inCi = os.environ.get("GITHUB_ACTIONS") == "true"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    results = []
    for g in selected:
        if g.node and shutil.which("npx") is None:
            if inCi:
                results.append((g, "FAIL", "npx not found"))
            else:
                results.append((g, "SKIP", "npx not found; install Node to run it locally"))
            continue
        print(f"::group::{g.title}" if inCi else f"\n=== {g.title}", flush=True)
        errors = [e for e in (runStep(s, env) for s in g.steps) if e]
        for e in errors:
            print(e)
        if inCi:
            print("::endgroup::", flush=True)
        results.append((g, "FAIL" if errors else "PASS", "; ".join(errors)))

    lines = [f"{status}  {g.name}{f'  ({note})' if note else ''}" for g, status, note in results]
    print("\n" + "\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("### PR guards\n\n| Guard | Result |\n|---|---|\n")
            fh.writelines(f"| {g.title} | {status}{f' — {note}' if note else ''} |\n" for g, status, note in results)
    return 1 if any(status == "FAIL" for _, status, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
