#!/usr/bin/env python3
"""Report the provenance and completeness of the Steward driver inputs.

The scheduled workflow gathers CI history, dependency advisories and test
history before it observes. Any of those can be missing, stale or incomplete,
and the sensors then report `not evaluated` instead of healthy. This script
makes the *reason* visible in the job summary and as workflow annotations so
an incomplete input is never presented as complete.

    python scripts/steward_report_inputs.py \
      --item ci-runs=ok --item advisories=ok \
      --item "test-history=missing:no prior artifact" \
      --item "test-suite=failed:exit 1" --history .gaia/steward/inputs/test-history.json

Each --item is NAME=STATE or NAME=STATE:DETAIL, STATE one of ok, missing,
failed, partial. Exit 0 always: the observation step's own exit code (3 when a
detector is blind) is what fails a job. A failed `test-suite` is evidence for
the flake detector only and never counts as a passed verification.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

STATES = ("ok", "missing", "failed", "partial")


def parseItem(text: str) -> tuple[str, str, str]:
    name, _, rest = text.partition("=")
    state, _, detail = rest.partition(":")
    if not name or state not in STATES:
        raise SystemExit(f"bad --item {text!r}: expected NAME=STATE[:DETAIL] with STATE in {STATES}")
    return name, state, detail


def historyRuns(path: Path) -> int | None:
    try:
        return len(json.loads(path.read_text(encoding="utf-8"))["runs"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--item", action="append", default=[], help="NAME=STATE[:DETAIL]")
    parser.add_argument("--history", type=Path, help="test-history.json to count runs in")
    args = parser.parse_args(argv)
    items = [parseItem(text) for text in args.item]
    lines = ["### Steward driver inputs", "", "| Input | State | Detail |", "|---|---|---|"]
    for name, state, detail in items:
        lines.append(f"| {name} | {state} | {detail or '-'} |")
    if args.history is not None:
        runs = historyRuns(args.history)
        note = "no readable history file; flake detection is NOT EVALUATED" if runs is None else (
            f"{runs} run(s) in history"
            + ("; one run cannot show flakiness (same sha, pass and fail), so this is INCOMPLETE" if runs < 2 else "")
        )
        lines.append(f"| test-history size | {'missing' if runs is None else 'ok' if runs >= 2 else 'partial'} | {note} |")
    text = "\n".join(lines) + "\n"
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    for name, state, detail in items:
        if state != "ok":
            print(f"::warning title=steward input {name} {state}::{detail or state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
