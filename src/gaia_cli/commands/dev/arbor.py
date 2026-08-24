"""CLI adapter for deterministic Arbor stamp ingestion and replay."""

from __future__ import annotations

import argparse
import sys

from gaia_cli.arbor import ArborError, checkProjection, importBundle, replayProjection


def arborCommand(args: argparse.Namespace) -> int:
    try:
        if args.arbor_command == "import":
            digest, count, written = importBundle(args.registry, args.bundle)
            action = "imported" if written else "already present"
            print(f"Arbor bundle {action}: sha256:{digest} ({count} projection row(s))")
            return 0
        if args.arbor_command == "replay":
            count = replayProjection(args.registry)
            print(f"Arbor projection replayed from retained bundles ({count} row(s))")
            return 0
        if args.arbor_command == "check":
            checkProjection(args.registry)
            print("Arbor retained bundles and projection are valid and byte-consistent")
            return 0
    except (ArborError, OSError) as exc:
        print(f"Arbor error: {exc}", file=sys.stderr)
        return 1
    print("Arbor error: choose import, check, or replay", file=sys.stderr)
    return 1
