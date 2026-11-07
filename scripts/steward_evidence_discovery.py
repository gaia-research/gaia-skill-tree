#!/usr/bin/env python3
"""Bounded, read-only evidence discovery for trust_evidence_gap findings (#2201).

An empty effective evidence pool is a gap, not a demotion. This driver does the
two things Steward may do about it and nothing else:

    python scripts/steward_evidence_discovery.py plan
        List the named skills with an open evidence gap, the rating that is
        preserved, and the bounded search plan for each. Writes nothing.

    python scripts/steward_evidence_discovery.py record SEARCH-LOG.json
        Validate the search log a driver (an agent with web access, or an
        operator) produced, annotate every candidate with freshness, duplicate
        and admissibility, and write one immutable receipt under the ignored
        .gaia/steward/discovery/. Positive AND negative searches are recorded.

It never searches the network, never admits evidence, never edits registry/ and
never changes a rating. Admitting a discovered row is a separate, governed
`gaia dev evidence` call by an authorized Verifier. See
founder/steward/routines/trust-evidence-gap.md for the search-log shape.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.steward.evidencediscovery import (  # noqa: E402
    DiscoveryError,
    buildDiscoveryReceipt,
    discoveryTargets,
    nowIso,
    writeDiscoveryReceipt,
)


def planCommand(args: argparse.Namespace) -> int:
    targets = discoveryTargets(args.repoRoot, args.now or nowIso())
    if args.json:
        print(json.dumps([item.toDict() for item in targets], indent=2, ensure_ascii=False))
        return 0
    if not targets:
        print("No open trust_evidence_gap findings.")
        return 0
    for item in targets:
        print(
            f"{item.skillId}: rating {item.preservedLevel} preserved; {item.evidenceBasis} "
            f"({item.effectiveRowCount} effective row(s)); search {', '.join(item.suggestedChannels)}"
        )
    return 0


def recordCommand(args: argparse.Namespace) -> int:
    try:
        log = json.loads(Path(args.log).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Error: cannot read search log: {exc}", file=sys.stderr)
        return 2
    try:
        receipt = buildDiscoveryReceipt(log, repoRoot=args.repoRoot, generatedAt=args.now or nowIso())
    except DiscoveryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    path, created = writeDiscoveryReceipt(args.repoRoot, receipt)
    coverage = receipt["coverage"]
    print(
        f"{'Wrote' if created else 'Already recorded'} {path.relative_to(args.repoRoot.resolve())}: "
        f"{receipt['outcome']}; {coverage['searchesAttempted']} search(es) "
        f"({coverage['positive']} positive, {coverage['negative']} negative); "
        f"rating {receipt['preservedLevel']} preserved; nothing admitted."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", dest="repoRoot", type=Path, default=ROOT)
    parser.add_argument("--now", help="ISO 8601 timestamp to stamp the receipt (default: current UTC)")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="List evidence gaps and the bounded search plan (read-only)")
    plan.add_argument("--json", action="store_true")
    record = commands.add_parser("record", help="Validate a search log and write an immutable discovery receipt")
    record.add_argument("log", help="Path to the search log JSON")
    args = parser.parse_args(argv)
    args.repoRoot = args.repoRoot.resolve()
    return planCommand(args) if args.command == "plan" else recordCommand(args)


if __name__ == "__main__":
    raise SystemExit(main())
