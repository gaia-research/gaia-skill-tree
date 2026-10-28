"""Admission request binding and honest admission attempts for Frontier case bundles."""
import json
import sys


def configureChallenge(parser):
    sub = parser.add_subparsers(dest="challenge_command", required=True)
    build = sub.add_parser("build-request", help="Bind a case bundle into transcript.json and admission-request.json (writes inside the case directory)")
    build.add_argument("--case", required=True, help="Case id: evidence/frontier-challenges/<case>/")
    build.add_argument("--verifier", required=True, help="GitHub login of the approver (becomes the receipt verifier)")
    build.add_argument("--builder", required=True, help="Declared builder identity of the experiment (independence is declared, not authenticated)")
    build.add_argument("--notice-ref", required=True, help="Public https reference to the contributor notice")
    build.add_argument("--contributor", help="Contributor id (defaults to the owner of a named target)")
    build.add_argument("--material-to-origin", action="store_true", help="Declare the challenge material to the target's Origin")
    build.add_argument("--revision", type=int, default=1, help="Receipt revision n (tag challenge-receipt/<case>-r<n>)")
    build.add_argument("--method", default="cli-replay", help="reproducible-test | benchmark-replay | cli-replay")
    build.add_argument("--proof-source-sha", help="Git commit id the proof is pinned to (default: the request's protocol revision)")
    build.add_argument("--public-receipt-ref", help="Public https URL of the issued approval (default: the committed receipt path on main)")
    build.add_argument("--verified-at", help="UTC timestamp the request claims (default: now)")
    build.add_argument("--repo-root", help="Checkout root (default: the resolved registry path)")
    admit = sub.add_parser("admit", help="Attempt a real admission through the production resolver and append the outcome to events.jsonl")
    admit.add_argument("--case", required=True)
    admit.add_argument("--repo-root", help="Checkout root (default: the resolved registry path)")
    fetch = sub.add_parser("fetch-receipt", help="Verify the issuer run live, then write the committed receipt/ files the offline source reads")
    fetch.add_argument("case", help="Case id")
    fetch.add_argument("--repo-root", help="Checkout root (default: the resolved registry path)")


def challengeCommand(args):
    from gaia_cli import challengeAdmission as admission
    from gaia_cli.authz import current_operator, require_operator
    from gaia_cli.commands.dev.frontierCmd import _repoRoot
    command = args.challenge_command
    require_operator(f"dev challenge {command}", args.registry)
    try:
        root, _ = _repoRoot(args)
        actor = current_operator(args.registry)
        if command == "build-request":
            document = admission.buildRequest(
                root, args.case, verifier=args.verifier, builder=args.builder, noticeRef=args.notice_ref,
                contributor=args.contributor, materialToOrigin=args.material_to_origin, revision=args.revision,
                method=args.method, proofSourceSha=args.proof_source_sha, publicReceiptRef=args.public_receipt_ref,
                verifiedAt=args.verified_at, actor=actor)
            print(json.dumps({"caseId": args.case, "challengeId": document["challengeId"], "receiptId": document["receipt"]["receipt_id"],
                              "written": ["transcript.json", "admission-request.json"],
                              "next": f"commit, then push tag challenge-receipt/{args.case}-r{args.revision}; the founder approves the environment; then `gaia dev challenge admit` and `fetch-receipt`",
                              "authority": "a request is not an admission"}, indent=2))
            return 0
        if command == "fetch-receipt":
            event = admission.fetchReceipt(root, args.case, actor=actor)
            print(json.dumps({**event, "next": "commit evidence/frontier-challenges/<case>/receipt/ with the case; the docs build then admits it offline"}, indent=2))
            return 0
        event = admission.admit(root, args.case, actor=actor)
        print(json.dumps(event, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Challenge {command} refused: {exc}", file=sys.stderr)
        return 1
