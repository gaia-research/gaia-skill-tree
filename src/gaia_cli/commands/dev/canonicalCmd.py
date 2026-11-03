"""Native CLI adapter for domain-specific canonical transactions."""
import json
import sys
from pathlib import Path


def configureCanonical(parser):
    sub = parser.add_subparsers(dest="canonical_command", required=True)
    plan = sub.add_parser("plan", help="Prepare named/owner-tree changes; print an untrusted review plan")
    plan.add_argument("--request", required=True, help="Domain request JSON; output plan JSON to stdout")
    for name in ("validate", "apply"):
        child = sub.add_parser(name, help="Validate exact staged outputs" if name == "validate" else "Apply with a genuinely resolved canonical decision (currently unavailable)")
        child.add_argument("--plan", required=True)
    sub.add_parser("status", help="Inspect journals and exact before/after/outside-edit states")
    rollback = sub.add_parser("rollback", help="Compare-safe recovery/reversal; requires a separate resolved decision")
    rollback.add_argument("--plan", required=True)
    rollback.add_argument("--journal", required=True)


def readDocument(path):
    from gaia_cli import canonicalTransaction as tx
    path = Path(path)
    if path.stat().st_size > 4_194_304:
        raise tx.TransactionError("request/plan exceeds bounded JSON input size")
    return json.loads(path.read_bytes())


def canonicalCommand(args):
    # Lazy imports: canonicalWorkflow pulls jsonschema; parser construction must stay dependency-free.
    from gaia_cli import canonicalTransaction as tx
    from gaia_cli import canonicalWorkflow as workflow
    from gaia_cli.evidenceLifecycle import EvidenceLifecycleError
    try:
        command = args.canonical_command
        if command in {"apply", "rollback"}:
            from gaia_cli.authz import require_operator
            require_operator(f"dev canonical {command}", args.registry)
        if command == "plan":
            result = workflow.buildPlan(args.registry, readDocument(args.request))
        elif command == "validate":
            result = workflow.validatePlan(args.registry, readDocument(args.plan))
            result = {"status": "validated", "planDigest": result["planDigest"], "approval": "not evaluated; validation is not approval"}
        elif command == "apply":
            result = workflow.applyPlan(args.registry, readDocument(args.plan))
        elif command == "status":
            result = workflow.status(args.registry)
        else:
            result = workflow.rollbackPlan(args.registry, readDocument(args.plan), args.journal)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (tx.TransactionError, EvidenceLifecycleError, ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Canonical workflow refused: {exc}", file=sys.stderr)
        return 1
