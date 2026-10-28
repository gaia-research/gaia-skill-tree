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
    meta = sub.add_parser("meta-validate", help="Structurally validate a Meta verification record against its receipt (read-only; not verification)")
    meta.add_argument("--record", required=True, help="frontier-meta-verification-v1 JSON")
    meta.add_argument("--receipt", required=True, help="experiment receipt JSON the record assesses")
    meta.add_argument("--request", required=True, help="verification request JSON; re-validates the receipt and pins the protocol re-execution artifacts must parse under")
    meta.add_argument("--repo-root", help="Checkout root used to verify artifact bytes (default: the resolved registry path, which is the checkout root)")
    meta.add_argument("--artifact-root", default="generated-output/frontier", help="generated-output/frontier (default) or evidence/frontier-challenges/<id>/artifacts")


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
        root, explicitRoot = _repoRoot(args)
        if args.frontier_command == "meta-validate":
            from gaia_cli import frontier
            record, receipt = fm.loadJsonFile(args.record, "record"), fm.loadJsonFile(args.receipt, "receipt")
            request = fm.loadJsonFile(args.request, "request")
            errors = frontier.validate_meta_verification(record, receipt, request, repo_root=root, artifact_root=args.artifact_root)
            print(json.dumps({"schemaVersion": "frontier-meta-validation-v1", "structurallyValid": not errors, "errors": errors,
                              "authority": "structural check only; run ids, session separation and independence are declared and unauthenticated; not verification, approval or admission"}, indent=2))
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
