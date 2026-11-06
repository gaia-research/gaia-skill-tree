"""Read-only Frontier lead tooling: advisory registry match and ledger dedupe."""
import json
import sys
from pathlib import Path


def configureFrontier(parser):
    sub = parser.add_subparsers(dest="frontier_command", required=True)
    match = sub.add_parser("match", help="Rank registry targets for a challenger lead (advisory, read-only)")
    match.add_argument("--lead", required=True, help="Challenger lead JSON; a target block is optional")
    match.add_argument("--top", type=int, default=5, help="Number of ranked candidates (1-50, default 5)")
    match.add_argument("--repo-root", help="Checkout root holding registry/ (default: the resolved registry path, which is the checkout root)")
    dedupe = sub.add_parser("dedupe", help="Check a lead against committed evidence/frontier-challenges leads (read-only)")
    dedupe.add_argument("--lead", required=True, help="Challenger lead JSON")
    dedupe.add_argument("--repo-root", help="Checkout root holding evidence/ (default: the resolved registry path, which is the checkout root)")
    dedupe.add_argument("--fail-on-duplicate", action="store_true", help="Exit 2 when an exact duplicate is found")
    meta = sub.add_parser("meta-validate", help="Structurally validate a Meta verification record (read-only; not verification)")
    meta.add_argument("--record", required=True, help="frontier-meta-verification-v1 JSON")
    meta.add_argument("--receipt", help="experiment receipt JSON the record assesses (verification stage)")
    meta.add_argument("--request", help="verification request JSON; re-validates the receipt and pins the protocol re-execution artifacts must parse under (verification stage)")
    meta.add_argument("--lead", help="challenger lead JSON (triage stage: the lead that was rejected or deferred before any receipt)")
    meta.add_argument("--match", help="raw `frontier match` output the triage reviewer read (triage stage)")
    meta.add_argument("--dedupe", help="raw `frontier dedupe` output the triage reviewer read (triage stage)")
    meta.add_argument("--repo-root", help="Checkout root used to verify artifact bytes (default: the resolved registry path, which is the checkout root)")
    meta.add_argument("--artifact-root", default="generated-output/frontier", help="generated-output/frontier (default) or evidence/frontier-challenges/<id>/artifacts")
    lead = sub.add_parser("lead-validate", help="Validate a challenger lead's schema and timestamps (future, and later than its committing commit when in git; read-only)")
    lead.add_argument("--lead", required=True, help="Challenger lead JSON")
    lead.add_argument("--repo-root", help="Checkout root (default: the resolved registry path); enables the committing-commit timestamp check")
    event = sub.add_parser("event", help="Append one event to <caseDir>/events.jsonl as it happens (O_APPEND, seq + prev-hash chain)")
    event.add_argument("caseDir", help="Case directory holding (or about to hold) events.jsonl")
    event.add_argument("--type", required=True, dest="eventType", help="Event type, e.g. runner-started (a-z 0-9 . _ -)")
    event.add_argument("--note", required=True, help="What happened (plain text, no secrets)")
    event.add_argument("--field", action="append", default=[], metavar="KEY=VALUE", help="Extra string field, repeatable (e.g. artifact=artifacts/native.json)")
    events = sub.add_parser("events-validate", help="Validate an events.jsonl chain and timestamps (warns when all events share one timestamp)")
    events.add_argument("caseDir", help="Case directory holding events.jsonl")


def _repoRoot(args):
    """Checkout root: explicit --repo-root, else the resolved registry path (a checkout root)."""
    if getattr(args, "repo_root", None):
        return Path(args.repo_root).expanduser().resolve(), True
    root = Path(args.registry).resolve()
    if (root / "registry" / "nodes").is_dir():
        return root, False
    if root.name == "registry" and (root / "nodes").is_dir():
        return root.parent, False  # tolerate a path naming the registry directory itself
    raise ValueError(f"no registry/nodes under {root}; run from a checkout or pass --repo-root <checkout>")


def frontierCommand(args):
    # Lazy import keeps parser construction dependency-free.
    from gaia_cli import frontierMatch as fm
    try:
        root, explicitRoot = (None, False) if args.frontier_command in {"event", "events-validate"} else _repoRoot(args)
        if args.frontier_command == "event":
            from gaia_cli import frontier
            extra = {}
            for pair in args.field:
                key, sep, value = pair.partition("=")
                if not sep:
                    raise ValueError(f"--field expects KEY=VALUE, got {pair!r}")
                extra[key] = value
            print(json.dumps(frontier.append_event(args.caseDir, args.eventType, args.note, extra=extra), ensure_ascii=False))
            return 0
        if args.frontier_command == "events-validate":
            from gaia_cli import frontier
            errors, warnings = frontier.validate_events(Path(args.caseDir) / frontier.EVENTS_FILE)
            print(json.dumps({"schemaVersion": "frontier-events-validation-v1", "valid": not errors, "errors": errors, "warnings": warnings}, indent=2))
            return 1 if errors else 0
        if args.frontier_command == "lead-validate":
            from gaia_cli import frontier
            leadData = fm.loadLeadFile(args.lead)
            warnings = []
            errors = frontier.validate_lead(leadData) + frontier.validate_lead_timestamps(leadData, repo_root=root, lead_path=args.lead, warnings=warnings)
            print(json.dumps({"schemaVersion": "frontier-lead-validation-v1", "valid": not errors, "errors": errors, "warnings": warnings}, indent=2))
            return 1 if errors else 0
        if args.frontier_command == "meta-validate":
            from gaia_cli import frontier
            record = fm.loadJsonFile(args.record, "record")
            warnings = []
            if isinstance(record, dict) and record.get("stage") == "triage":
                if not (args.lead and args.match and args.dedupe):
                    raise ValueError("a triage-stage record needs --lead, --match and --dedupe")
                errors = frontier.validate_triage_record(record, fm.loadJsonFile(args.lead, "lead"), Path(args.match).read_bytes(), Path(args.dedupe).read_bytes(),
                                                         repo_root=root, record_path=args.record, warnings=warnings)
            else:
                if not (args.receipt and args.request):
                    raise ValueError("a verification-stage record needs --receipt and --request")
                receipt, request = fm.loadJsonFile(args.receipt, "receipt"), fm.loadJsonFile(args.request, "request")
                errors = frontier.validate_meta_verification(record, receipt, request, repo_root=root, artifact_root=args.artifact_root,
                                                             record_path=args.record, warnings=warnings)
            print(json.dumps({"schemaVersion": "frontier-meta-validation-v1", "structurallyValid": not errors, "errors": errors, "warnings": warnings,
                              "authority": "structural check only; run ids, rerun traces, timestamps, session separation and independence are declared and unauthenticated; not verification, approval or admission"}, indent=2))
            return 1 if errors else 0
        lead = fm.loadLeadFile(args.lead)
        if args.frontier_command == "match":
            result = fm.match_candidates(lead, root, top=args.top)
        else:
            result = fm.dedupe_against_ledger(lead, root, exclude=args.lead)
            if not explicitRoot and (not result["ledger"]["present"] or result["ledger"]["scanned"] == 0):
                raise ValueError("ledger evidence/frontier-challenges is absent or empty under " + str(root) + "; refusing to report 'not a duplicate' from a ledger that was not read. Pass --repo-root <checkout> to confirm an empty ledger.")
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        if args.frontier_command == "dedupe" and args.fail_on_duplicate and result["isDuplicate"]:
            return 2
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        print(f"Frontier {args.frontier_command} refused: {exc}", file=sys.stderr)
        return 1
