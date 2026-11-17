"""Programmatic import, validation, and replay for the Arbor sidecar."""

import sys

from gaia_cli.arbor import (
    ArborError,
    checkStore,
    importSource,
    pinSubject,
    recordObservation,
    replay,
    upstreamCheck,
)


def arborCommand(args):
    try:
        if args.arbor_command == "import":
            path, digest, created = importSource(args.input, args.registry)
            verb = "Imported" if created else "Already present"
            print(f"{verb} Arbor source sha256:{digest} -> {path}")
            return 0
        if args.arbor_command == "check":
            count = checkStore(
                args.registry, args.input, getattr(args, "require_history", False)
            )
            print(f"Arbor check passed ({count} record{'s' if count != 1 else ''})")
            return 0
        if args.arbor_command == "replay":
            paths = replay(args.registry)
            print(f"Replayed {len(paths)} Arbor profile{'s' if len(paths) != 1 else ''}")
            for path in paths:
                print(path)
            return 0
        if args.arbor_command == "pin":
            path, created = pinSubject(
                args.skill_id, args.registry, args.content_sha256, args.from_git
            )
            print(f"{'Pinned' if created else 'Already pinned'} {args.skill_id} -> {path}")
            return 0
        if args.arbor_command == "observe-instruction":
            path, record, created = recordObservation(
                args.registry,
                args.skill_id,
                args.content_sha256,
                "baseline",
                args.commit,
                expectedSha256=args.expect_sha256,
            )
            verb = "Recorded" if created else "Already recorded"
            print(f"{verb} baseline sha256:{record['observed']['sha256']} -> {path}")
            return 0
        if args.arbor_command == "upstream-check":
            report = upstreamCheck(args.registry, record=args.record)
            drift = [entry for entry in report if entry["status"] != "unchanged"]
            for entry in report:
                suffix = f" (recorded {entry['recorded']})" if "recorded" in entry else ""
                if entry.get("error"):
                    suffix += f" ({entry['error']})"
                print(f"{entry['status']:<11} {entry['skill']}@{entry['contentSha256'][:12]}{suffix}")
            print(f"{len(report)} observed subject(s), {len(drift)} drifted")
            errors = [entry for entry in report if entry["status"] == "error"]
            if errors or (drift and not args.record):
                return 1
            return 0
        print(
            "ERROR: choose an Arbor operation: import, check, replay, pin, "
            "observe-instruction, or upstream-check",
            file=sys.stderr,
        )
        return 1
    except ArborError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
