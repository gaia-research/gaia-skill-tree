"""Read-only Frontier lead tooling: advisory registry match and ledger dedupe."""
import json
import sys
from pathlib import Path


def configureFrontier(parser):
    sub = parser.add_subparsers(dest="frontier_command", required=True)
    match = sub.add_parser("match", help="Rank registry targets for a challenger lead (advisory, read-only)")
    match.add_argument("--lead", required=True, help="Challenger lead JSON; a target block is optional")
    match.add_argument("--top", type=int, default=5, help="Number of ranked candidates (1-50, default 5)")
    match.add_argument("--repo-root", help="Checkout root holding registry/ (default: parent of the resolved registry)")
    dedupe = sub.add_parser("dedupe", help="Check a lead against committed evidence/frontier-challenges leads (read-only)")
    dedupe.add_argument("--lead", required=True, help="Challenger lead JSON")
    dedupe.add_argument("--repo-root", help="Checkout root holding evidence/ (default: parent of the resolved registry)")
    dedupe.add_argument("--fail-on-duplicate", action="store_true", help="Exit 2 when an exact duplicate is found")


def _repoRoot(args):
    if getattr(args, "repo_root", None):
        return Path(args.repo_root).expanduser().resolve()
    return Path(args.registry).resolve().parent


def frontierCommand(args):
    # Lazy import keeps parser construction dependency-free.
    from gaia_cli import frontierMatch as fm
    try:
        lead = fm.loadLeadFile(args.lead)
        root = _repoRoot(args)
        if args.frontier_command == "match":
            result = fm.match_candidates(lead, root, top=args.top)
        else:
            result = fm.dedupe_against_ledger(lead, root, exclude=args.lead)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        if args.frontier_command == "dedupe" and args.fail_on_duplicate and result["isDuplicate"]:
            return 2
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Frontier {args.frontier_command} refused: {exc}", file=sys.stderr)
        return 1
