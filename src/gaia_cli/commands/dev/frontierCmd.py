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
        lead = fm.loadLeadFile(args.lead)
        root, explicitRoot = _repoRoot(args)
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
