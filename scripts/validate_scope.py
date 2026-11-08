#!/usr/bin/env python3
"""Decide whether a pull request touches paths that need heavy validation.

Used by the `changes` job in `.github/workflows/validate.yml` so the required
check "Schema + DAG + Integrity Checks" can report on every PR while heavy
validation still only runs when `on.push.paths` (the single source of truth)
matches the PR diff.

Prints exactly one line, `relevant=true` or `relevant=false`, on stdout. It
fails CLOSED: any error (missing SHA, git failure, YAML failure, unsupported
path pattern) prints `relevant=true` so full validation still runs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Iterable, List, Pattern

SHAPATTERN = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
SUPPORTEDCHARS = re.compile(r"[A-Za-z0-9._/*-]+")


class ScopeError(Exception):
    """Raised for anything that must make the caller fail closed."""


def compileSegment(segment: str) -> str:
    return "".join("[^/]*" if char == "*" else re.escape(char) for char in segment)


def compilePattern(pattern: str) -> Pattern[str]:
    """Compile a GitHub `paths:` glob (supported subset only) to a regex.

    Supported: literal characters `A-Za-z0-9._-`, `/` separators, `*` (zero or
    more characters except `/`) inside a segment, and `**` as a whole segment.
    A `**` segment followed by `/` matches zero or more directories, and a
    trailing `**` matches everything below. Anything else (`?`, `[]`, `!`,
    `+`, backslashes, a leading `/`, empty segments, `**` mixed into a
    segment) raises ScopeError so the caller fails closed.
    """
    if not pattern or not SUPPORTEDCHARS.fullmatch(pattern):
        raise ScopeError(f"unsupported path pattern: {pattern!r}")
    segments = pattern.split("/")
    if any(segment == "" for segment in segments):
        raise ScopeError(f"unsupported path pattern (empty segment): {pattern!r}")
    out = ""
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        if segment == "**":
            out += ".*" if last else "(?:.*/)?"
            continue
        if "**" in segment:
            raise ScopeError(f"unsupported path pattern (** inside segment): {pattern!r}")
        out += compileSegment(segment)
        if not last:
            out += "/"
    return re.compile(out, re.DOTALL)


def loadPatterns(workflowPath: str) -> List[str]:
    import yaml  # PyYAML; an ImportError makes the caller fail closed

    with open(workflowPath, encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True.
    triggers = doc["on"] if "on" in doc else doc[True]
    patterns = triggers["push"]["paths"]
    if not isinstance(patterns, list) or not patterns:
        raise ScopeError("on.push.paths is missing or empty")
    for pattern in patterns:
        if not isinstance(pattern, str):
            raise ScopeError(f"non-string path pattern: {pattern!r}")
    return patterns


def matches(patterns: Iterable[str], path: str) -> bool:
    compiled = [compilePattern(pattern) for pattern in patterns]
    return any(regex.fullmatch(path) for regex in compiled)


def runGit(repo: str, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise ScopeError(
            f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return result.stdout


def changedPaths(repo: str, baseSha: str, headSha: str) -> List[str]:
    """Exact raw paths changed on the PR side of merge-base(base, head)..head."""
    for sha in (baseSha, headSha):
        if not sha or not SHAPATTERN.match(sha):
            raise ScopeError(f"missing or malformed commit SHA: {sha!r}")
        runGit(repo, "cat-file", "-e", f"{sha}^{{commit}}")
    mergeBase = runGit(repo, "merge-base", baseSha, headSha).decode("ascii").strip()
    if not SHAPATTERN.match(mergeBase):
        raise ScopeError(f"no merge base for {baseSha} and {headSha}")
    raw = runGit(
        repo, "diff", "--name-only", "--no-renames", "-z", mergeBase, headSha
    )
    # NUL-delimited, no stripping: names may contain spaces, tabs, newlines.
    return [os.fsdecode(entry) for entry in raw.split(b"\0") if entry]


def evaluate(workflowPath: str, repo: str, baseSha: str, headSha: str) -> bool:
    patterns = loadPatterns(workflowPath)
    compiled = [compilePattern(pattern) for pattern in patterns]
    paths = changedPaths(repo, baseSha, headSha)
    hits = [p for p in paths if any(regex.fullmatch(p) for regex in compiled)]
    # json.dumps escapes control characters so untrusted names cannot inject
    # runner workflow commands into the log.
    print(
        f"matched {len(hits)} of {len(paths)} changed paths; "
        f"first matches: {json.dumps(hits[:10])}",
        file=sys.stderr,
    )
    return bool(hits)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", default=".github/workflows/validate.yml")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="")
    args = parser.parse_args(argv)
    try:
        relevant = evaluate(args.workflow, args.repo, args.base, args.head)
    except Exception as error:  # fail closed on ANY detection failure
        print(f"scope detection failed, failing closed: {json.dumps(str(error))}", file=sys.stderr)
        relevant = True
    print("relevant=" + ("true" if relevant else "false"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
