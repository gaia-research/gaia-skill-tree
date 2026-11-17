#!/usr/bin/env python3
"""Verify that the shared Steward refs are protected against rewrite and deletion.

`steward/evidence` is append-only custody. Content hashes prove the stored bytes
were not altered; they cannot stop a repository writer from force-pushing history
away or deleting the ref. That protection is repository configuration, not code,
so this checker reads the repository's rulesets and answers one question: does an
ACTIVE branch ruleset with no bypass actors block deletion and non-fast-forward
updates for every protected ref?

Exit 0 only when every required ref is covered. Anything unreadable is a failure:
"could not inspect" is never "protected".

The protected namespace is `steward/evidence`, `steward/ledger` and EVERY ref matching
`steward/evidence-*`, not just the refs that exist today. Sampling a list of names cannot prove
that: a ruleset made of exact names passes for those names and leaves every future
`steward/evidence-<anything>` ref unprotected. So the namespace entry is proved by language
containment (`coversLanguage`): every string the pattern `steward/evidence-*` can match must be
matched by the union of the ruleset's include patterns, and no exclusion may reach the namespace.

    gh api repos/gaia-research/gaia-skill-tree/rulesets            # list
    python scripts/check_steward_evidence_protection.py --live     # inspects each
    python scripts/check_steward_evidence_protection.py --rulesets-file rulesets.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

REPOSITORY = "gaia-research/gaia-skill-tree"
REQUIRED_REFS = (
    "refs/heads/steward/evidence",
    "refs/heads/steward/evidence-rehearsal-2448",
    "refs/heads/steward/evidence-rehearsal-2448-v2",
    "refs/heads/steward/evidence-authz-probe-2448",
    "refs/heads/steward/ledger",
)
# Pattern namespaces: every ref the pattern matches, including refs that do not exist yet. They are
# proved by containment, never by listing names. Each is a literal prefix followed by one `*`.
NAMESPACES = ("refs/heads/steward/evidence-*",)
# The protected namespaces. An exclusion whose literal prefix can reach into one is refused.
NAMESPACE_ROOTS = ("refs/heads/steward/evidence", "refs/heads/steward/ledger")
REQUIRED_RULES = ("deletion", "non_fast_forward")


def globMatch(pattern: str, ref: str) -> bool:
    """GitHub ref_name matching, kept strict: `*` stays inside one path segment, `**` crosses them."""

    if pattern == "~ALL":
        return True
    regex = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            regex += ".*"
            index += 2
        elif pattern[index] == "*":
            regex += "[^/]*"
            index += 1
        elif pattern[index] == "?":
            regex += "[^/]"
            index += 1
        else:
            regex += re.escape(pattern[index])
            index += 1
    return re.fullmatch(regex, ref) is not None


def tokens(pattern: str) -> list[tuple[str, str]]:
    """Glob tokens, GitHub semantics: `*` = non-slash run, `**` = any run, `?` = one non-slash char."""

    if pattern == "~ALL":
        return [("deep", "")]
    out: list[tuple[str, str]] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            out.append(("deep", ""))
            index += 2
        elif pattern[index] == "*":
            out.append(("star", ""))
            index += 1
        elif pattern[index] == "?":
            out.append(("one", ""))
            index += 1
        else:
            out.append(("lit", pattern[index]))  # `[` and friends stay literal: never over-credit coverage
            index += 1
    return out


def closure(states: set[tuple[int, int]], programs: list[list[tuple[str, str]]]) -> frozenset:
    todo = list(states)
    seen = set(states)
    while todo:
        program, position = todo.pop()
        if position < len(programs[program]) and programs[program][position][0] in ("star", "deep"):
            following = (program, position + 1)
            if following not in seen:
                seen.add(following)
                todo.append(following)
    return frozenset(seen)


def advance(states: frozenset, char: str, programs: list[list[tuple[str, str]]]) -> frozenset:
    nxt: set[tuple[int, int]] = set()
    for program, position in states:
        if position >= len(programs[program]):
            continue
        kind, literal = programs[program][position]
        if kind == "lit" and char == literal:
            nxt.add((program, position + 1))
        elif kind == "one" and char != "/":
            nxt.add((program, position + 1))
        elif kind == "star" and char != "/":
            nxt.add((program, position))
        elif kind == "deep":
            nxt.add((program, position))
    return closure(nxt, programs)


def accepting(states: frozenset, programs: list[list[tuple[str, str]]]) -> bool:
    return any(position == len(programs[program]) for program, position in states)


def coversLanguage(includes: Sequence[str], namespace: str) -> bool:
    """Whether the UNION of `includes` matches every ref in `namespace` (a literal prefix plus one `*`).

    Exact: it explores every state the include patterns can be in after reading the prefix and then any
    non-slash tail, so no sampled name can fool it. An empty tail is part of the language, so a pattern
    that needs at least one more character does not cover it.
    """

    assert namespace.endswith("*") and "*" not in namespace[:-1], namespace
    prefix = namespace[:-1]
    programs = [tokens(pattern) for pattern in includes]
    if not programs:
        return False
    states = closure({(index, 0) for index in range(len(programs))}, programs)
    for char in prefix:
        states = advance(states, char, programs)
    alphabet = {literal for program in programs for kind, literal in program if kind == "lit" and literal != "/"}
    alphabet.add("\x00")  # stands for every character no pattern names
    pending, seen = [states], {states}
    while pending:
        current = pending.pop()
        if not accepting(current, programs):
            return False  # some tail string is matched by no include
        for char in alphabet:
            following = advance(current, char, programs)
            if following not in seen:
                seen.add(following)
                pending.append(following)
    return True


def matches(patterns: Sequence[str], ref: str) -> bool:
    return any(globMatch(pattern, ref) for pattern in patterns)


def excludeReaches(pattern: str) -> bool:
    """Whether an exclusion could carve something out of a protected namespace."""

    if pattern == "~ALL":
        return True
    literal = re.split(r"[*?]", pattern, maxsplit=1)[0]
    return any(root.startswith(literal) or literal.startswith(root) for root in NAMESPACE_ROOTS)


def rulesetCovers(ruleset: dict[str, Any], ref: str) -> tuple[bool, list[str]]:
    """Whether one ruleset protects `ref`; the list says what is missing."""

    problems: list[str] = []
    if ruleset.get("target") != "branch":
        problems.append("not a branch ruleset")
    if ruleset.get("enforcement") != "active":
        problems.append(f"enforcement is {ruleset.get('enforcement')!r}, not 'active'")
    conditions = (ruleset.get("conditions") or {}).get("ref_name") or {}
    includes = conditions.get("include") or []
    if ref in NAMESPACES:
        if not coversLanguage(includes, ref):
            problems.append(
                f"the include patterns do not cover every ref matching {ref!r}; "
                "exact branch names cannot protect refs that do not exist yet (add the pattern or a broader one)"
            )
    elif not matches(includes, ref) or matches(conditions.get("exclude") or [], ref):
        problems.append("the ref is not included by the ruleset's ref_name conditions")
    for pattern in conditions.get("exclude") or []:
        if excludeReaches(pattern):
            problems.append(f"exclusion {pattern!r} can carve refs out of the protected steward namespace")
    present = {rule.get("type") for rule in ruleset.get("rules") or []}
    for needed in REQUIRED_RULES:
        if needed not in present:
            problems.append(f"missing rule {needed!r}")
    if ruleset.get("bypass_actors"):
        problems.append(
            f"{len(ruleset['bypass_actors'])} bypass actor(s) can override it; an append-only guarantee needs none"
        )
    return not problems, problems


def evaluate(
    rulesets: list[dict[str, Any]], refs: Sequence[str] = REQUIRED_REFS + NAMESPACES
) -> dict[str, Any]:
    report: dict[str, Any] = {"protected": True, "refs": {}}
    for ref in refs:
        best: list[str] | None = None
        covered = False
        for ruleset in rulesets:
            ok, problems = rulesetCovers(ruleset, ref)
            if ok:
                covered = True
                break
            if best is None or len(problems) < len(best):
                best = problems
        report["refs"][ref] = {
            "covered": covered,
            "problems": [] if covered else (best if best is not None else ["no ruleset exists"]),
        }
        report["protected"] = report["protected"] and covered
    return report


def gh(*args: str) -> Any:
    result = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh api {' '.join(args)} failed: {(result.stderr or result.stdout).strip()[:300]}")
    return json.loads(result.stdout)


def loadLive(repository: str) -> list[dict[str, Any]]:
    listing = gh(f"repos/{repository}/rulesets")
    return [gh(f"repos/{repository}/rulesets/{item['id']}") for item in listing]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true", help="Read rulesets with `gh api` (needs admin read access)")
    source.add_argument("--rulesets-file", type=Path, help="JSON list of full ruleset objects")
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        rulesets = loadLive(args.repository) if args.live else json.loads(args.rulesets_file.read_text())
        if not isinstance(rulesets, list) or any(not isinstance(item, dict) for item in rulesets):
            raise ValueError("rulesets must be a JSON list of objects")
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"UNVERIFIED: could not inspect rulesets: {exc}", file=sys.stderr)
        return 2
    report = evaluate(rulesets)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for ref, item in report["refs"].items():
            note = "  (every future ref: needs the pattern, not names)" if ref in NAMESPACES else ""
            print(f"{'PROTECTED  ' if item['covered'] else 'UNPROTECTED'} {ref}{note}")
            for problem in item["problems"]:
                print(f"    - {problem}")
        print("RESULT: protected" if report["protected"] else "RESULT: NOT protected; the daily scheduler must stay disabled")
    return 0 if report["protected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
