"""``gaia steward pr``: the operator and driver surface for routine PR maintenance.

Exit codes: 0 prepared / terminal; 2 refused, unknown or bad input; 3 already-observed diagnostic (not shared settlement);
5 not evaluated. Only explicit ``execute --operation-id`` may invoke the one-shot adapter. Gate output is preparation,
recover/finalize never resend, and abort cancels only unsent preparation (its reason is recorded in the shared cancel
event). ``takeover`` re-owns an EXPIRED unsent preparation only. Unknown may include an already-sent effect.
"""

from __future__ import annotations

import argparse
import subprocess
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import collect, coordination, gate, proofs, receipts, reconcile, roster, state
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
    dis.add_argument("--subject", action="append", default=[], metavar="REPO#N@SHA",
                     help="the exact pull request head(s) this dispatch may judge; a verification outside them is refused")
    fin = rsub.add_parser("finish", help="close a dispatch record")
    fin.add_argument("--dispatch-id", required=True, dest="dispatchId")
    fin.add_argument("--result", required=True)
    fin.add_argument("--cost")
    fin.add_argument("--receipt", action="append", default=[])

    ver = sub.add_parser("verification", help="store an independent verification receipt")
    ver.add_argument("--input", required=True)

    for name in ("merge", "close"):
        g = sub.add_parser(f"gate-{name}", help=f"re-prove eligibility and prepare shared {name} intent (not a send grant)")
        g.add_argument("--repo", required=True)
        g.add_argument("--number", type=int, required=True)
        g.add_argument("--head", required=True, help="the exact head SHA the action names")
        g.add_argument("--run-id", required=True, dest="runId")
        g.add_argument("--producer", required=True)
        if name == "close":
            g.add_argument("--reason", required=True)
            g.add_argument("--replacement", type=int, required=True)
    fz = sub.add_parser("finalize", help="reconcile a shared operation using independent evidence; never resend")
    fz.add_argument("--operation-id")
    fz.add_argument("--auth", help="deprecated operation-identity file; raw authorization JSON is refused")
    ab = sub.add_parser("abort", help="cancel unsent shared preparation only; never cancel a claimed sender")
    ab.add_argument("--operation-id")
    ab.add_argument("--auth", help="deprecated operation-identity file")
    ab.add_argument("--reason", required=True, help="1-256 printable ASCII characters; recorded in the shared cancel event")
    tk = sub.add_parser("takeover", help="re-own an EXPIRED (lease 120 s) unsent preparation under a newer fence; never a claimed sender")
    tk.add_argument("--operation-id", required=True)
    for command in ("execute", "recover"):
        execution = sub.add_parser(command, help="invoke once explicitly" if command == "execute" else "reconcile without resend")
        execution.add_argument("--operation-id", required=True)

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

    refresh = sub.add_parser("reconcile-refresh", help="bring an open, Steward-owned replacement up to a destination tip that moved (local only)")
    refresh.add_argument("--number", type=int, required=True, help="the ORIGINAL pull request number")
    refresh.add_argument("--run-id", required=True, dest="runId")
    refresh.add_argument("--worktree", required=True, help="the replacement's existing worktree")

    retired = sub.add_parser("reconcile-retired", help="record that a replacement pull request was withdrawn so a new one may be built")
    retired.add_argument("--number", type=int, required=True, help="the ORIGINAL pull request number")
    retired.add_argument("--head", required=True, help="the original head SHA the replacement was built from")
    retired.add_argument("--replacement", type=int, required=True)
    retired.add_argument("--reason", required=True)
    retired.add_argument("--run-id", required=True, dest="runId")

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
            envelope = json.loads(args.envelope)
            subjects = []
            for item in args.subject:
                repoPart, _, rest = item.partition("#")
                numberPart, _, headPart = rest.partition("@")
                subjects.append({"repo": repoPart, "number": int(numberPart), "headSha": headPart})
            envelope["subjects"] = subjects
            record = roster.recordDispatch(root, profile, selection, runId=args.runId, dispatchId=args.dispatchId,
                                           envelope=envelope, role=args.role,
                                           laneMaxInFlight=policy.lane.max_in_flight, laneMaxPerRun=policy.max_dispatches_per_run,
                                           builders=args.builder)
            out(record, args.json, f"dispatch {args.dispatchId} recorded ({args.role}: {args.agent} @ {args.effort})")
            return 0
    except roster.RosterError as exc:
        out({"refused": exc.code, "message": exc.message}, args.json, f"refused: {exc}")
        return 2
    return 2


def snapshotFor(root: Path, repo: str, number: int) -> gate.Snapshot:
    def fetch(n: int) -> None:
        # The pull request head AND the destination tip: the gate proves "already published on the base" from git objects, so an
        # unfetched tip must never be possible (it would read as "not published" and refuse, safely but wrongly).
        for refspec in (f"+refs/pull/{n}/head:refs/steward/pr/{n}", "+refs/heads/main:refs/remotes/origin/main"):
            proofs.git(root, "fetch", "--quiet", "origin", refspec, timeout=180)

    return collect.liveSnapshot(collect.ghApi, repo, number, fetch)


SHARED_UNAVAILABLE = {"refused": "shared-route-unavailable",
                      "message": "coordination/current authority/clock/evidence unavailable; no replay or refund"}


def doGate(root: Path, args: argparse.Namespace, action: str) -> int:
    request = {"action": action, "repo": args.repo, "number": args.number, "expectedHeadSha": args.head,
               "producerId": args.producer, "runId": args.runId}
    try:
        execution = gate.makeExecutor(root)  # unconfigured route refuses before live collection
        instant = datetime.fromtimestamp(execution.services.clock().upper, timezone.utc)
        snap = snapshotFor(root, args.repo, args.number)
        request["baseRef"] = snap.row["baseRef"]
        if action == "close":
            request.update(reason=args.reason, replacement=args.replacement)
        found = gate.validateWrite(root, request, snap, instant, action)
        auth = execution.prepare(request, snap, found, args.runId)
    except gate.AlreadyDone as exc:
        out({"alreadyDone": exc.code, "message": exc.message, "detail": exc.detail}, args.json, f"already done: {exc}")
        return 3
    except gate.GateRefused as exc:
        out({"refused": exc.code, "message": exc.message}, args.json, f"refused: {exc}")
        return 2
    except ledger.LedgerUnavailable:
        out(SHARED_UNAVAILABLE, args.json, f"refused: {SHARED_UNAVAILABLE['message']}")
        return 2
    except (collect.CollectError, KeyError, state.StoreError) as exc:
        out({"refused": "live-read-failed", "message": str(exc)}, args.json, f"refused: live state could not be read ({exc})")
        return 2
    out(auth, args.json, f"{auth['state']} {action} #{args.number}: operation {auth['operationId']} (not a send grant)")
    return 0 if auth["state"] in {"intent", "reserved", "merged", "closed", "already-merged"} else 2


def doFinalize(root: Path, args: argparse.Namespace) -> int:
    from gaia_cli.steward.prmaintenance.executor import makeExecutor
    operationId = operationIdentity(args)
    outcome = makeExecutor(root).recover(operationId)
    out(outcome, args.json)
    return 0 if outcome["state"] in ("merged", "closed", "already-merged") else 2


def operationIdentity(args) -> str:
    from gaia_cli.steward.prmaintenance import coordination
    value = getattr(args, "operation_id", None)
    if value is None and getattr(args, "auth", None):
        identity = readJson(args.auth)
        gate.checkAuthorization(Path("."), identity)
        value = identity["operationId"]
    coordination.sha(value)
    return value


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
        lines = [line for line in state.readRecords(root, "outcomes")
                 if line.get("action") == "reconcile" and line.get("repo") == repo and line.get("number") == args.number
                 and line.get("originalHead") == found.headSha]
        retired = {line.get("replacement") for line in lines if line.get("state") == "retired"}
        for line in lines:
            if line.get("state") == "opened" and line.get("replacement") not in retired:
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
                                              "baseSha": tip, "worktree": str(made.worktree),
                                              "builders": ["reconciler:content-engine-cachebust", os.environ.get("GAIA_STEWARD_LEAD_ID", "lead-session")]})
    out({**reconcile.asMapping(made), "body": made.body, "baseSha": tip}, args.json,
        f"built {made.branch} @ {made.commit[:12]} on {tip[:12]} in {made.worktree}")
    return 0


def doReconcileRefresh(root: Path, args: argparse.Namespace) -> int:
    from gaia_cli.steward.policy import StewardPolicy
    from gaia_cli.steward.prmaintenance.census import loadPrCensus

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
    with state.lock(root):
        lines = [line for line in state.readRecords(root, "outcomes")
                 if line.get("action") == "reconcile" and line.get("repo") == repo and line.get("number") == args.number]
        opened = [line for line in lines if line.get("state") == "opened"
                  and line.get("replacement") not in {l.get("replacement") for l in lines if l.get("state") == "retired"}]
        spent = sum(1 for line in lines if line.get("state") == "built" and line.get("runId") == args.runId)
    if not opened:
        out({"refused": "no-open-replacement", "message": "no open replacement is recorded for this original"}, args.json, "refused: no open replacement")
        return 2
    if spent >= policy.pr_maintenance.maxReplacementsPerRun:
        out({"refused": "run-budget-exhausted", "message": "this run already built its replacements"}, args.json, "refused: replacement budget for this run is spent")
        return 2
    mine = opened[-1]
    label = str(mine["branch"]).rsplit("-", 2)[-2] + "-" + str(mine["branch"]).rsplit("-", 2)[-1]
    tip = census.document["baseTips"][census.document.get("defaultBranch", "main")]
    try:
        made = reconcile.refreshReplacement(root, label, Path(args.worktree).resolve(), tip, number=args.number,
                                            originalHead=mine["originalHead"], repo=repo)
    except reconcile.ReconcileError as exc:
        out({"refused": "reconcile-failed", "message": str(exc)}, args.json, f"refused: {exc}")
        return 2
    with state.lock(root):
        state.appendRecord(root, "outcomes", {"at": state.stamp(), "runId": args.runId, "repo": repo, "number": args.number, "action": "reconcile",
                                              "state": "built", "headSha": made.commit, "originalHead": mine["originalHead"], "branch": made.branch,
                                              "baseSha": tip, "worktree": str(made.worktree), "refreshOf": mine["headSha"],
                                              "builders": ["reconciler:content-engine-cachebust", os.environ.get("GAIA_STEWARD_LEAD_ID", "lead-session")]})
    out({**reconcile.asMapping(made), "baseSha": tip}, args.json, f"refreshed {made.branch} to {made.commit[:12]} on {tip[:12]}")
    return 0


def doReconcileRetired(root: Path, args: argparse.Namespace) -> int:
    census = json.loads((root / CENSUS_INPUT).read_text(encoding="utf-8"))
    with state.lock(root):
        built = [line for line in state.readRecords(root, "outcomes")
                 if line.get("action") == "reconcile" and line.get("state") == "built" and line.get("originalHead") == args.head
                 and line.get("number") == args.number]
        for line in built[-1:]:  # clean the local worktree and branch of the withdrawn replacement so its name can be reused
            proofs.git(root, "worktree", "remove", "--force", str(line.get("worktree", "")))
            proofs.git(root, "branch", "-D", str(line.get("branch", "")))
        state.appendRecord(root, "outcomes", {"at": state.stamp(), "runId": args.runId, "repo": census["repo"], "number": args.number,
                                              "action": "reconcile", "state": "retired", "headSha": args.head, "originalHead": args.head,
                                              "replacement": args.replacement, "reason": args.reason[:300]})
    out({"recorded": True}, args.json, f"retired replacement #{args.replacement} for #{args.number}")
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
        if args.action in {"execute", "recover", "abort", "takeover"}:
            from gaia_cli.steward.prmaintenance.executor import makeExecutor
            executor = makeExecutor(root)
            operationId = operationIdentity(args)
            if args.action == "takeover":
                outcome = executor.takeover(operationId)
                out(outcome, args.json)
                return 0 if outcome["state"] in {"reserved", "intent"} and "commitStatus" not in outcome else 2
            outcome = (executor.abort(operationId, args.reason) if args.action == "abort"
                       else executor.execute(operationId) if args.action == "execute" else executor.recover(operationId))
            out(outcome, args.json)
            return 0 if outcome["state"] in {"merged", "closed", "already-merged", "aborted"} else 2
        if args.action == "receipt":
            return doReceipt(root, args)
        if args.action == "reconcile":
            return doReconcile(root, args)
        if args.action == "reconcile-opened":
            return doReconcileOpened(root, args)
        if args.action == "reconcile-retired":
            return doReconcileRetired(root, args)
        if args.action == "reconcile-refresh":
            return doReconcileRefresh(root, args)
        if args.action == "kill":
            flag = state.storeDir(root) / state.KILL_FILE
            if args.state == "on":
                flag.write_text(state.stamp() + "\n", encoding="utf-8")
            elif args.state == "off" and flag.exists():
                flag.unlink()
            active = state.killSwitchActive(root)
            out({"killSwitch": active}, args.json, f"kill switch: {active or 'inactive'}")
            return 0
    except (ledger.LedgerUnavailable, collect.CollectError):
        # CoordinationError is a LedgerUnavailable; a raw ledger fetch/CAS failure must never escape as a traceback.
        out(SHARED_UNAVAILABLE, args.json)
        return 2
    except gate.GateRefused as exc:
        out({"refused": exc.code, "message": exc.message}, args.json, f"refused: {exc}")
        return 2
    except (RegistryError, state.StoreError, KeyError, ValueError) as exc:
        out({"refused": "bad-input", "message": str(exc)}, args.json, f"refused: {type(exc).__name__}: {exc}")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
