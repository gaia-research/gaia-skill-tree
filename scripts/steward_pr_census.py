#!/usr/bin/env python3
"""Collect the read-only GitHub pull-request census that routine 19 (PR maintenance) observes.

Writes ``.gaia/steward/inputs/github-prs.json`` (schema steward-pr-census-v1). Only GET requests are made.
Each open pull request's head is fetched into the local object store as ``refs/steward/pr/<n>`` so the sensor can
prove the content from git objects without touching the network. Exit 0: complete. Exit 3: written but incomplete
(the sensor then reports coverage unknown). Any other exit: nothing usable was written.

Only repositories enabled in founder/steward/pr-producers.json are collected; deferred repositories are refused.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.steward.prmaintenance.census import CENSUS_INPUT, loadPrCensus  # noqa: E402
from gaia_cli.steward.prmaintenance.collect import CollectError, collectCensus, ghApi, writeCensus  # noqa: E402
from gaia_cli.steward.prmaintenance.producers import RegistryError, loadRegistry  # noqa: E402


def fetchHead(root: Path, remote: str):
    def fetch(number: int) -> None:
        subprocess.run(["git", "-C", str(root), "fetch", "--quiet", remote, f"+refs/pull/{number}/head:refs/steward/pr/{number}"],
                       capture_output=True, text=True, timeout=180, check=False)
    return fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="gaia-research/gaia-skill-tree")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--out", default=None, help="override the output path (default: the sensor's input)")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        registry = loadRegistry(root)
    except RegistryError as exc:
        print(f"producer registry unusable: {exc}", file=sys.stderr)
        return 2
    if args.repo not in registry.enabledRepos:
        deferred = registry.deferredFor(args.repo)
        print(f"refusing to collect {args.repo}: " + (f"deferred ({deferred.reason})" if deferred else "not an enabled repository"),
              file=sys.stderr)
        return 2
    try:
        document = collectCensus(ghApi, args.repo, fetchHead(root, args.remote))
    except (CollectError, KeyError) as exc:
        print(f"census collection failed: {exc}", file=sys.stderr)
        return 4
    target = writeCensus(root, document, Path(args.out) if args.out else CENSUS_INPUT)
    status = loadPrCensus(target, maxAgeSeconds=3600).status
    print(f"census {status.status}: {len(document['pulls'])} open pull request(s) in {args.repo} -> {target}")
    if not status.complete:
        print("reasons: " + ", ".join(status.reasons[:6]), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
