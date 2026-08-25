"""Programmatic import, validation, and replay for the Arbor sidecar."""

import sys

from gaia_cli.arbor import ArborError, checkStore, importSource, replay


def arborCommand(args):
    try:
        if args.arbor_command == "import":
            path, digest, created = importSource(args.input, args.registry)
            verb = "Imported" if created else "Already present"
            print(f"{verb} Arbor source sha256:{digest} -> {path}")
            return 0
        if args.arbor_command == "check":
            count = checkStore(args.registry, args.input)
            print(f"Arbor check passed ({count} record{'s' if count != 1 else ''})")
            return 0
        if args.arbor_command == "replay":
            paths = replay(args.registry)
            print(f"Replayed {len(paths)} Arbor profile{'s' if len(paths) != 1 else ''}")
            for path in paths:
                print(path)
            return 0
        print("ERROR: choose an Arbor operation: import, check, or replay", file=sys.stderr)
        return 1
    except ArborError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
