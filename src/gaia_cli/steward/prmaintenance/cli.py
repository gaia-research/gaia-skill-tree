"""``gaia steward pr``: the operator and driver surface for routine PR maintenance.

Exit codes: 0 done / authorized; 2 refused or bad input (nothing was written to GitHub); 3 already done (the recorded or
observed end state is reported); 5 not evaluated (a required input is missing). The command never merges, closes or
comments by itself: ``gate`` authorizes exactly one forge call and ``finalize`` records what GitHub then shows.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from gaia_cli.steward.prmaintenance import collect, gate, receipts, reconcile, roster, state
from gaia_cli.steward.prmaintenance.census import CENSUS_INPUT
from gaia_cli.steward.prmaintenance.producers import RegistryError, loadRegistry

DESCRIPTION = __doc__.splitlines()[0]


def out(value: Any, asJson: bool, text: str = "") -> None:
    print(json.dumps(value, indent=2, sort_keys=True) if asJson else (text or json.dumps(value, indent=2, sort_keys=True)))


def utc() -> datetime:
    return datetime.now(timezone.utc)


def readJson(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path != "-" else json.load(sys.stdin)


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gaia steward pr", description=DESCRIPTION)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="action", required=True)

    observe = sub.add_parser("observe", help="evaluate the current census with the producer registry (read only)")
    observe.add_argument("--collect", action="store_true", help="refresh the census first (read-only GitHub GETs)")

    rost = sub.add_parser("roster", help="environment roster profiles")
    rsub = rost.add_subparsers(dest="rosterAction", required=True)
    pre = rsub.add_parser("preflight", help="session-start preflight; records a receipt")
    pre.add_argument("--profile")
    pre.add_argument("--run-id", required=True, dest="runId")
    init = rsub.add_parser("init", help="validate and store a profile from a file (never from another environment)")
    init.add_argument("--from", required=True, dest="source")
    init.add_argument("--activate", action="store_true")
    sel = rsub.add_parser("select", help="capability-driven selection")
    sel.add_argument("--profile")
    sel.add_argument("--capability", required=True)
    sel.add_argument("--exclude", action="append", default=[])
    sel.add_argument("--operator-choice", dest="operatorChoice")
    sel.add_argument("--effort")
    esc = rsub.add_parser("escalate", help="escalate a selection for a stated unresolved need")
    esc.add_argument("--profile")
    esc.add_argument("--capability", required=True)
    esc.add_argument("--agent", required=True)
    esc.add_argument("--effort", required=True)
    esc.add_argument("--need", required=True)
    esc.add_argument("--exclude", action="append", default=[])
    dis = rsub.add_parser("dispatch", help="record a dispatch inside the profile and policy limits")
    dis.add_argument("--profile")
    dis.add_argument("--run-id", required=True, dest="runId")
    dis.add_argument("--dispatch-id", required=True, dest="dispatchId")
    dis.add_argument("--role", choices=("builder", "verifier"), required=True)
    dis.add_argument("--capability", required=True)
    dis.add_argument("--agent", required=True)
    dis.add_argument("--effort", required=True)
    dis.add_argument("--escalation-reason", dest="escalation")
    dis.add_argument("--envelope", required=True, help="JSON object describing the permitted work envelope")
    dis.add_argument("--builder", action="append", default=[], help="agent id(s) that built the work being verified")
    fin = rsub.add_parser("finish", help="close a dispatch record")
    fin.add_argument("--dispatch-id", required=True, dest="dispatchId")
    fin.add_argument("--result", required=True)
    fin.add_argument("--cost")
    fin.add_argument("--receipt", action="append", default=[])

    ver = sub.add_parser("verification", help="store an independent verification receipt")
    ver.add_argument("--input", required=True)

    for name in ("merge", "close"):
        g = sub.add_parser(f"gate-{name}", help=f"re-prove eligibility and authorize exactly one forge {name}")
        g.add_argument("--repo", required=True)
        g.add_argument("--number", type=int, required=True)
        g.add_argument("--head", required=True, help="the exact head SHA the action names")
        g.add_argument("--run-id", required=True, dest="runId")
        g.add_argument("--producer", required=True)
        if name == "close":
            g.add_argument("--reason", required=True)
            g.add_argument("--replacement", type=int, required=True)
    fz = sub.add_parser("finalize", help="settle an authorization from GitHub's observed state")
    fz.add_argument("--auth", required=True)
    ab = sub.add_parser("abort", help="release a reservation when the forge call was not made")
    ab.add_argument("--auth", required=True)
    ab.add_argument("--reason", required=True)

    rc = sub.add_parser("receipt", help="render, check or record a GitHub receipt")
    rsub2 = rc.add_subparsers(dest="receiptAction", required=True)
    for kind in receipts.KINDS:
        r = rsub2.add_parser(kind, help=f"render the {kind} receipt body")
        r.add_argument("--input", required=True, help="JSON file of the renderer's keyword arguments")
    chk = rsub2.add_parser("check", help="is a receipt already on the pull request? (idempotency)")
    chk.add_argument("--repo", required=True)
    chk.add_argument("--number", type=int, required=True)
    chk.add_argument("--kind", choices=receipts.KINDS, required=True)
    chk.add_argument("--head")
    rec = rsub2.add_parser("record", help="record that a receipt was posted")
    rec.add_argument("--repo", required=True)
    rec.add_argument("--number", type=int, required=True)
    rec.add_argument("--kind", choices=receipts.KINDS, required=True)
    rec.add_argument("--head", required=True)
    rec.add_argument("--run-id", required=True, dest="runId")
    rec.add_argument("--comment-id", type=int, required=True, dest="commentId")

    rec2 = sub.add_parser("reconcile", help="build a tracked replacement for a reconcilable content-engine pull request (local only)")
    rec2.add_argument("--number", type=int, required=True)
    rec2.add_argument("--run-id", required=True, dest="runId")
    rec2.add_argument("--worktree", required=True, help="a new, empty path for the replacement worktree")
    opened = sub.add_parser("reconcile-opened", help="record that the replacement branch was pushed and its pull request opened")
    opened.add_argument("--number", type=int, required=True, help="the ORIGINAL pull request number")
    opened.add_argument("--head", required=True, help="the original head SHA the replacement was built from")
    opened.add_argument("--replacement", type=int, required=True)
    opened.add_argument("--branch", required=True)
    opened.add_argument("--run-id", required=True, dest="runId")

    kill = sub.add_parser("kill", help="revoke or restore the route locally")
    kill.add_argument("state", choices=("on", "off", "status"))
    return parser


def doObserve(root: Path, args: argparse.Namespace) -> int:
    from gaia_cli.steward.prmaintenance.census import loadPrCensus
    from gaia_cli.steward.prmaintenance.evaluate import evaluateCensus

    if args.collect:
        document = collect.collectCensus(collect.ghApi, "gaia-research/gaia-skill-tree")
        collect.writeCensus(root, document, CENSUS_INPUT)
    census = loadPrCensus(root / CENSUS_INPUT)
    if census.document is None or not census.status.complete:
        out({"status": census.status.status, "reasons": list(census.status.reasons)}, args.json,
            f"census {census.status.status}: {', '.join(census.status.reasons[:4])}")
        return 5
    rows = [e.asState() for e in evaluateCensus(root, loadRegistry(root), census.document)]
    registry = loadRegistry(root)
    summary = {"repo": census.document["repo"], "fetchedAt": census.document["fetchedAt"], "routine": rows,
               "deferred": [d.repo for d in registry.deferred], "organisationWideDiscovery": "deferred"}
    text = "\n".join(f"#{r['number']:<5} {r['disposition']:<34} Class {r['authority']}  producer={r['producerId']}  "
                     f"reconcile={r['reconcile']}  {'; '.join(r['reasons'])[:90]}" for r in rows) or "no routine pull requests"
    out(summary, args.json, text + "\ndeferred (coverage unknown): " + ", ".join(summary["deferred"]))
    return 0


def doRoster(root: Path, args: argparse.Namespace) -> int:
    try:
        action = args.rosterAction
        if action == "preflight":
            receipt = roster.preflight(root, args.runId, args.profile)
            out(receipt, args.json, f"roster preflight ok: profile {receipt['profileId']} r{receipt['profileRevision']} "
                f"in {receipt['environment']['environmentId']}; usable agents: {', '.join(receipt['usableAgents']) or 'none'}")
            return 0
        if action == "init":
            profile = readJson(args.source)
            path = roster.saveProfile(root, profile, activate=args.activate)
            out({"stored": str(path), "profileId": profile["profileId"]}, args.json, f"stored {path}")
            return 0
        if action == "finish":
            out(roster.finishDispatch(root, args.dispatchId, args.result, cost=args.cost, receipts=args.receipt), args.json)
            return 0
        profile = roster.loadProfile(root, roster.activeProfileId(root, args.profile))
        discovered = roster.discoverEnvironment()
        if profile["environmentId"] != discovered["environmentId"]:
            raise roster.RosterError("profile-for-other-environment",
                                     f"profile {profile['profileId']!r} belongs to {profile['environmentId']!r}, this is {discovered['environmentId']!r}")
        if action == "select":
            picked = roster.select(profile, args.capability, exclude=args.exclude, operatorChoice=args.operatorChoice, effort=args.effort)
            out(picked.__dict__, args.json, f"{picked.agentId} @ {picked.effort} for {picked.capability}")
            return 0
        if action == "escalate":
            current = roster.Selection(args.agent, None, args.effort, args.capability, None, profile["profileId"],
                                       profile["environmentId"], profile["revision"])
            picked = roster.escalate(profile, current, args.need, exclude=args.exclude)
            out(picked.__dict__, args.json, f"escalated to {picked.agentId} @ {picked.effort}: {picked.escalation}")
            return 0
        if action == "dispatch":
            from gaia_cli.steward.policy import StewardPolicy

            policy = StewardPolicy.load(root)
            agent = next((a for a in profile["agents"] if a["agentId"] == args.agent), None)
            if agent is None or args.effort not in agent["efforts"]:
                raise roster.RosterError("selection-outside-profile", "the agent or effort is not in the active profile")
            if agent["capabilities"].get(args.capability) not in roster.USABLE_CAPABILITY:
                raise roster.RosterError("capability-unavailable", f"{args.agent!r} does not hold {args.capability!r}")
            selection = roster.Selection(args.agent, agent.get("modelBinding"), args.effort, args.capability, args.escalation,
                                         profile["profileId"], profile["environmentId"], profile["revision"])
            record = roster.recordDispatch(root, profile, selection, runId=args.runId, dispatchId=args.dispatchId,
                                           envelope=json.loads(args.envelope), role=args.role,
                                           laneMaxInFlight=policy.lane.max_in_flight, laneMaxPerRun=policy.max_dispatches_per_run,
                                           builders=args.builder)
            out(record, args.json, f"dispatch {args.dispatchId} recorded ({args.role}: {args.agent} @ {args.effort})")
            return 0
    except roster.RosterError as exc:
        out({"refused": exc.code, "message": exc.message}, args.json, f"refused: {exc}")
        return 2
    return 2


def snapshotFor(root: Path, repo: str, number: int) -> gate.Snapshot:
    import subprocess

    def fetch(n: int) -> None:
        subprocess.run(["git", "-C", str(root), "fetch", "--quiet", "origin", f"+refs/pull/{n}/head:refs/steward/pr/{n}"],
                       capture_output=True, timeout=180, check=False)

    return collect.liveSnapshot(collect.ghApi, repo, number, fetch)


def doGate(root: Path, args: argparse.Namespace, action: str) -> int:
    request = {"action": action, "repo": args.repo, "number": args.number, "expectedHeadSha": args.head,
               "producerId": args.producer, "runId": args.runId}
    try:
        snap = snapshotFor(root, args.repo, args.number)
        request["baseRef"] = snap.row["baseRef"]
        if action == "close":
            request.update(reason=args.reason, replacement=args.replacement)
        authorize = gate.gateMerge if action == "merge" else gate.gateClose
        auth = authorize(root, request, snap, utc(), args.runId)
    except gate.AlreadyDone as exc:
        out({"alreadyDone": exc.code, "message": exc.message, "detail": exc.detail}, args.json, f"already done: {exc}")
        return 3
    except gate.GateRefused as exc:
        out({"refused": exc.code, "message": exc.message}, args.json, f"refused: {exc}")
        return 2
    except (collect.CollectError, KeyError, state.StoreError) as exc:
        out({"refused": "live-read-failed", "message": str(exc)}, args.json, f"refused: live state could not be read ({exc})")
        return 2
    out(auth, args.json, f"authorized {action} #{args.number} at {args.head[:12]} (digest {auth['digest'][:12]}, run {args.runId})")
    return 0


def doFinalize(root: Path, args: argparse.Namespace) -> int:
    auth = readJson(args.auth)
    try:
        snap = snapshotFor(root, auth["repo"], auth["number"])
        merged = bool(snap.merged or snap.row.get("merged"))
        parents = collect.mergeParents(collect.ghApi, auth["repo"], snap.mergeCommitSha) if merged and snap.mergeCommitSha else []
        post = collect.checksAt(collect.ghApi, auth["repo"], snap.mergeCommitSha) if merged and snap.mergeCommitSha else "not observed"
        outcome = gate.finalize(root, auth, snap, utc(), parents=parents, postMerge=post)
    except (collect.CollectError, KeyError, state.StoreError) as exc:
        out({"refused": "live-read-failed", "message": str(exc)}, args.json, f"could not observe the final state: {exc}")
        return 2
    out(outcome, args.json, f"{outcome['state']}: #{outcome['number']} {outcome.get('mergeCommitSha', '')}")
    return 0 if outcome["state"] in ("merged", "closed") else 2


def doReconcile(root: Path, args: argparse.Namespace) -> int:
    from gaia_cli.steward.policy import StewardPolicy
    from gaia_cli.steward.prmaintenance.census import loadPrCensus
    from gaia_cli.steward.prmaintenance.evaluate import evaluateCensus

    policy = StewardPolicy.load(root)
    reason = state.killSwitchActive(root, policy.pr_maintenance.killSwitch)
    if reason or not policy.pr_maintenance.writesEnabled:
        out({"refused": "kill-switch" if reason else "authority-unratified", "message": reason or "PR maintenance is not enabled"}, args.json, f"refused: {reason or 'not enabled'}")
        return 2
    census = loadPrCensus(root / CENSUS_INPUT, maxAgeSeconds=policy.pr_maintenance.maxCensusAgeSeconds)
    if census.document is None or not census.status.complete:
        out({"refused": "census-unusable", "reasons": list(census.status.reasons)}, args.json, f"refused: census {census.status.status}")
        return 2
    repo = census.document["repo"]
    found = next((e for e in evaluateCensus(root, loadRegistry(root), census.document) if e.number == args.number), None)
    if found is None or found.reconcile != "content-engine-cachebust" or not found.label:
        out({"refused": "not-reconcilable", "message": "the pull request is not a proven, reconcilable content-engine report"}, args.json,
            "refused: not reconcilable")
        return 2
    with state.lock(root):
        for line in state.readRecords(root, "outcomes"):
            if line.get("action") == "reconcile" and line.get("repo") == repo and line.get("number") == args.number \
                    and line.get("originalHead") == found.headSha and line.get("state") == "opened":
                out({"alreadyDone": "replacement-opened", "detail": line}, args.json, f"already done: replacement #{line.get('replacement')} was opened")
                return 3
        built = {line.get("runId") for line in state.readRecords(root, "outcomes")
                 if line.get("action") == "reconcile" and line.get("state") == "built"}
        spent = sum(1 for line in state.readRecords(root, "outcomes")
                    if line.get("action") == "reconcile" and line.get("state") == "built" and line.get("runId") == args.runId)
        if spent >= policy.pr_maintenance.maxReplacementsPerRun:
            out({"refused": "run-budget-exhausted", "message": "this run already built its replacements; resume next run", "runs": sorted(map(str, built))},
                args.json, "refused: replacement budget for this run is spent")
            return 2
    tip = census.document["baseTips"][found.baseRef]
    try:
        made = reconcile.buildReplacement(root, repo, args.number, found.headSha, found.label, tip, Path(args.worktree).resolve())
    except reconcile.ReconcileError as exc:
        out({"refused": "reconcile-failed", "message": str(exc)}, args.json, f"refused: {exc}")
        return 2
    with state.lock(root):
        state.appendRecord(root, "outcomes", {"at": state.stamp(), "runId": args.runId, "repo": repo, "number": args.number, "action": "reconcile",
                                              "state": "built", "headSha": made.commit, "originalHead": found.headSha, "branch": made.branch,
                                              "baseSha": tip})
    out({**reconcile.asMapping(made), "body": made.body, "baseSha": tip}, args.json,
        f"built {made.branch} @ {made.commit[:12]} on {tip[:12]} in {made.worktree}")
    return 0


def doReconcileOpened(root: Path, args: argparse.Namespace) -> int:
    census = json.loads((root / CENSUS_INPUT).read_text(encoding="utf-8"))
    with state.lock(root):
        state.appendRecord(root, "outcomes", {"at": state.stamp(), "runId": args.runId, "repo": census["repo"], "number": args.number,
                                              "action": "reconcile", "state": "opened", "headSha": args.head, "originalHead": args.head,
                                              "replacement": args.replacement, "branch": args.branch})
    out({"recorded": True}, args.json, f"recorded replacement #{args.replacement} for #{args.number}")
    return 0


def doReceipt(root: Path, args: argparse.Namespace) -> int:
    action = args.receiptAction
    if action in receipts.KINDS:
        kwargs = readJson(args.input)
        print(getattr(receipts, {"verification": "verification", "pickup": "pickup", "merged": "merged", "closed": "closed",
                                 "founder": "founder"}[action])(**kwargs))
        return 0
    if action == "check":
        body, _ = collect.ghApi(f"repos/{args.repo}/issues/{args.number}/comments", {"per_page": 100})
        comments = [{"authorAssociation": c.get("author_association"), "body": c.get("body"), "id": c.get("id")} for c in body or []]
        found = receipts.findReceipt(comments, args.kind, args.number, args.head[:12] if args.head else None)
        out({"posted": bool(found), "commentId": found.get("id") if found else None}, args.json,
            f"{'posted' if found else 'absent'}: {args.kind} receipt on #{args.number}")
        return 0 if found else 3
    state.recordReceipt(root, {"at": state.stamp(), "repo": args.repo, "number": args.number, "kind": args.kind,
                               "head12": args.head[:12], "runId": args.runId, "commentId": args.commentId})
    out({"recorded": True}, args.json, "recorded")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build().parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve()
    try:
        if args.action == "observe":
            return doObserve(root, args)
        if args.action == "roster":
            return doRoster(root, args)
        if args.action == "verification":
            stored = gate.recordVerification(root, readJson(args.input))
            out(stored, args.json, f"stored {stored['verdict']} verification for #{stored['number']} at {stored['headSha'][:12]}")
            return 0
        if args.action == "gate-merge":
            return doGate(root, args, "merge")
        if args.action == "gate-close":
            return doGate(root, args, "close")
        if args.action == "finalize":
            return doFinalize(root, args)
        if args.action == "abort":
            outcome = gate.abort(root, readJson(args.auth), args.reason, utc())
            out(outcome, args.json, "reservation released")
            return 0
        if args.action == "receipt":
            return doReceipt(root, args)
        if args.action == "reconcile":
            return doReconcile(root, args)
        if args.action == "reconcile-opened":
            return doReconcileOpened(root, args)
        if args.action == "kill":
            flag = state.storeDir(root) / state.KILL_FILE
            if args.state == "on":
                flag.write_text(state.stamp() + "\n", encoding="utf-8")
            elif args.state == "off" and flag.exists():
                flag.unlink()
            active = state.killSwitchActive(root)
            out({"killSwitch": active}, args.json, f"kill switch: {active or 'inactive'}")
            return 0
    except gate.GateRefused as exc:
        out({"refused": exc.code, "message": exc.message}, args.json, f"refused: {exc}")
        return 2
    except (RegistryError, state.StoreError, KeyError, ValueError) as exc:
        out({"refused": "bad-input", "message": str(exc)}, args.json, f"refused: {type(exc).__name__}: {exc}")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
