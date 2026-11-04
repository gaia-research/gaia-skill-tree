"""The one gate for PR-maintenance writes (``forge.merge_pr`` and ``forge.close_pr``).

A stored action is only a claim. ``gateMerge`` and ``gateClose`` re-derive eligibility from a *fresh* live snapshot
and refuse unless every one of these holds, in this order:

 1. the route is not revoked (kill switch: policy, a local file or an environment flag), and the authority files
    (POLICY.yaml, the producer registry, the decided authority record) are committed, unmodified, and - when
    GAIA_STEWARD_PR_AUTHORITY_REF names the destination tip - identical to it;
 2. the policy is well formed, the founder authority record is decided and approved, and the action is enabled;
 3. the repository is enabled (a deferred repository is refused by name);
 4. no terminal outcome is already recorded, and no live reservation exists (exactly once, never concurrent);
 5. the pull request is open and not already merged (an already-merged PR is reported, not re-merged);
 6. the head SHA is exactly the one the action names and the one that was verified;
 7. the destination is allowed by policy and equals the producer's destination;
 8. the registered producer re-proves provenance, scope, holds, approvals, CI at the head, currency, conflicts, content;
 9. GitHub's own protection is satisfied (required checks passed, mergeable state clean) - Steward never bypasses it;
10. an independent verification receipt exists for this head, base, policy and registry revision, from an agent other
    than the builder, within its time to live;
11. the GitHub trail exists (pickup and verification receipts for this head; for a closure, the justification itself);
12. the per-run and hourly budgets allow it. The reservation is written before the forge is called.

Passing the gate produces an ``Authorization`` for exactly one forge call. It never performs the call.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from gaia_cli.steward.models import stable_json
from gaia_cli.steward.policy import PolicyError, StewardPolicy
from gaia_cli.steward.prmaintenance import receipts, state
from gaia_cli.steward.prmaintenance.evaluate import KIND_CLOSURE, KIND_MERGE, evaluate
from gaia_cli.steward.prmaintenance.policy import prAuthorityApproved
from gaia_cli.steward.prmaintenance.producers import Registry, RegistryError, loadRegistry

BADEFFORTS = frozenset({"", "default", "inherit"})
SHA = "0123456789abcdef"
AUTH_TTL_SECONDS = 600


class GateRefused(Exception):
    """The write is refused. ``code`` is machine-readable and stable; nothing was written to GitHub."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


class AlreadyDone(GateRefused):
    """GitHub already shows the intended end state. The outcome is reported; nothing is performed again."""

    def __init__(self, code: str, message: str, detail: Mapping[str, Any] | None = None) -> None:
        super().__init__(code, message)
        self.detail = dict(detail or {})


@dataclass(frozen=True)
class Snapshot:
    """Live GitHub state at gate time, in census row shape. Built by ``collect.liveSnapshot`` or a test fake."""

    row: Mapping[str, Any]
    tips: Mapping[str, str]
    protection: Mapping[str, Any]
    siblings: Sequence[Mapping[str, Any]]
    closed: Sequence[Mapping[str, Any]]
    merged: bool = False
    mergeCommitSha: str | None = None


AUTHORITY_FILES = ("founder/steward/POLICY.yaml", "founder/steward/pr-producers.json",
                   "founder/steward/decisions/steward-pr-maintenance-authority.json")
AUTHORITY_REF = "GAIA_STEWARD_PR_AUTHORITY_REF"


AUTHORITY_LOCAL = "GAIA_STEWARD_PR_AUTHORITY_LOCAL"


def authorityDrift(root: Path) -> tuple[str, str] | None:
    """``(code, reason)`` when authority cannot be trusted right now, or ``None``.

    Authority must come from reviewed, committed bytes AND the operator must name where they come from. Fail closed by default:
    set GAIA_STEWARD_PR_AUTHORITY_REF to the destination tip (every unattended or post-merge run), or knowingly set
    GAIA_STEWARD_PR_AUTHORITY_LOCAL=1 to run under the committed local head (a campaign staged from a not-yet-merged pull request).
    Either way an uncommitted edit to an authority file is refused, and the authorization records which source it ran under.
    """

    from gaia_cli.steward.prmaintenance import proofs

    dirty = proofs.git(root, "status", "--porcelain", "--untracked-files=all", "--", *AUTHORITY_FILES)
    if dirty.returncode != 0:
        return "authority-drift", "git could not report the state of the authority files"
    if dirty.stdout.strip():
        return "authority-drift", "authority files have uncommitted changes: " + ", ".join(line[3:].decode() for line in dirty.stdout.splitlines()[:3])
    ref = os.environ.get(AUTHORITY_REF, "").strip()
    if ref:
        named = proofs.git(root, "rev-parse", "--symbolic-full-name", ref)
        if named.returncode != 0 or not named.stdout.decode().startswith("refs/remotes/"):
            return "authority-ref-invalid", f"{AUTHORITY_REF}={ref!r} must name a remote-tracking ref such as origin/main (not HEAD or a local branch)"
        for relative in AUTHORITY_FILES:
            there = proofs.blob(root, ref, relative)
            here = (root / relative).read_bytes() if (root / relative).is_file() else None
            if there is None or here is None or there != here:
                return "authority-drift", f"{relative} differs from {ref}"
        return None
    if os.environ.get(AUTHORITY_LOCAL, "").strip() == "1":
        return None
    return "authority-source-unset", (f"no authority source is named: set {AUTHORITY_REF} to the destination tip, or knowingly set "
                                      f"{AUTHORITY_LOCAL}=1 to run under the committed local head")


def authorityInfo(root: Path) -> dict[str, str]:
    from gaia_cli.steward.prmaintenance import proofs

    head = proofs.git(root, "rev-parse", "HEAD").stdout.decode().strip()
    ref = os.environ.get(AUTHORITY_REF, "").strip()
    return {"mode": "ref" if ref else "local-head", "source": ref or "HEAD", "commit": head}


def policyDigest(root: Path) -> str:
    data = (root / "founder/steward/POLICY.yaml").read_bytes() + (root / "founder/steward/pr-producers.json").read_bytes()
    return hashlib.sha256(data).hexdigest()


def isoNow(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def context(root: Path, policy: StewardPolicy | None, registry: Registry | None) -> tuple[StewardPolicy, Registry]:
    try:
        return policy or StewardPolicy.load(root), registry or loadRegistry(root)
    except (PolicyError, RegistryError) as exc:
        raise GateRefused("policy-unreadable", f"policy or producer registry is unusable: {exc}") from exc


def recordVerification(root: Path, record: Mapping[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Validate and store an independent verification receipt.

    Independence is *derived*, never self-declared: a PASS is stored only against a recorded ``role=verifier`` dispatch for
    this run and agent, the builders are the union of the dispatch's and the caller's and must be non-empty, the verifier is
    never one of them, and the policy digest is computed here, not taken from the caller.
    """

    need = ("repo", "number", "action", "headSha", "baseSha", "verdict", "verifier", "builders", "proofs", "runId")
    missing = [key for key in need if key not in record]
    if missing:
        raise GateRefused("verification-malformed", f"missing {missing}")
    if record["action"] not in ("merge", "close") or record["verdict"] not in ("pass", "fail"):
        raise GateRefused("verification-malformed", "action must be merge or close and verdict pass or fail")
    for key in ("headSha", "baseSha"):
        if not (isinstance(record[key], str) and len(record[key]) == 40 and set(record[key]) <= set(SHA)):
            raise GateRefused("verification-malformed", f"{key} must be a full SHA")
    verifier = record["verifier"]
    if not isinstance(verifier, Mapping) or not verifier.get("agentId") or not verifier.get("profileId"):
        raise GateRefused("verification-malformed", "verifier needs agentId and profileId")
    if str(verifier.get("effort", "")) in BADEFFORTS:
        raise GateRefused("verification-malformed", "verifier effort must be explicit")
    dispatched = [d for d in state.readRecords(root, "dispatches")
                  if d.get("kind") == "dispatch" and d.get("status") == "started" and d.get("role") == "verifier"
                  and d.get("runId") == record["runId"] and d.get("agentId") == verifier["agentId"]]
    if not dispatched:
        raise GateRefused("verification-not-dispatched", "no recorded verifier dispatch exists for this run and agent")
    subject = {"repo": record["repo"], "number": record["number"], "headSha": record["headSha"]}
    dispatched = [d for d in dispatched if subject in (d.get("envelope") or {}).get("subjects", [])]
    if not dispatched:
        raise GateRefused("verification-not-dispatched",
                          "the verifier dispatch does not name this repository, pull request and head in its envelope subjects")
    dispatch = dispatched[-1]
    if str(dispatch.get("effort")) != str(verifier.get("effort")):
        raise GateRefused("verification-malformed", "the verifier's effort differs from its recorded dispatch")
    built = {str(who) for line in state.readRecords(root, "outcomes")
             if line.get("action") == "reconcile" and line.get("state") == "built" and line.get("headSha") == record["headSha"]
             for who in line.get("builders") or []}  # who built the replacement comes from the store, not the caller
    builders = sorted({str(item) for item in record["builders"]} | {str(item) for item in dispatch.get("builders") or []} | built)
    if not builders:
        raise GateRefused("verification-malformed", "builders must name who built the work; an empty list proves nothing")
    if str(verifier["agentId"]) in builders:
        raise GateRefused("verification-not-independent", "the verifier is also a builder of this work")
    if record["verdict"] == "pass":
        proofs = [p for p in record["proofs"] if isinstance(p, Mapping)]
        if not proofs or any(p.get("state") != "pass" for p in proofs):
            raise GateRefused("verification-malformed", "a pass verdict needs at least one proof and none that is not pass")
    stored = {**record, "builders": builders, "dispatchId": dispatch.get("dispatchId"),
              "at": isoNow(now or datetime.now(timezone.utc)), "policySha256": policyDigest(root)}
    with state.lock(root):
        state.appendRecord(root, "verifications", stored)
    return stored


def verificationFor(root: Path, request: Mapping[str, Any], row: Mapping[str, Any], tip: str, now: datetime,
                    ttl: int, action: str) -> Mapping[str, Any]:
    for found in reversed(state.readRecords(root, "verifications")):
        if (found.get("repo"), found.get("number"), found.get("action")) != (request["repo"], request["number"], action):
            continue
        if found.get("headSha") != row["headSha"]:
            continue  # a head change invalidates every earlier verification
        at = datetime.strptime(found["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if now - at > timedelta(seconds=ttl):
            raise GateRefused("verification-stale", f"the verification for this head is older than {ttl}s")
        if found.get("baseSha") != tip:
            raise GateRefused("verification-stale", "the destination moved since verification; verify again")
        if found.get("verdict") != "pass":
            raise GateRefused("verification-failed", "the independent verification of this head did not pass")
        if found.get("policySha256") != policyDigest(root):
            raise GateRefused("policy-revision-moved", "POLICY.yaml or the producer registry changed since verification")
        if str(found["verifier"]["agentId"]) in [str(b) for b in found.get("builders") or []]:
            raise GateRefused("verification-not-independent", "the verifier is also a builder of this work")
        return found
    raise GateRefused("no-verification", "no independent verification receipt exists for this exact head")


def commonChecks(root: Path, request: Mapping[str, Any], snap: Snapshot, now: datetime, action: str,
                 policy: StewardPolicy, registry: Registry) -> None:
    pol = policy.pr_maintenance
    reason = state.killSwitchActive(root, pol.killSwitch)
    if reason:
        raise GateRefused("kill-switch", f"PR maintenance writes are revoked: {reason}")
    drift = authorityDrift(root)
    if drift:
        raise GateRefused(drift[0], drift[1])
    if policy.pr_maintenance_error:
        raise GateRefused("policy-malformed", policy.pr_maintenance_error)
    if not prAuthorityApproved(root):
        raise GateRefused("authority-unratified", "steward-pr-maintenance-authority is not a decided, approved record")
    if not pol.actionEnabled(action):
        raise GateRefused("action-disabled", f"policy does not enable {action}")
    repo = str(request["repo"])
    deferred = registry.deferredFor(repo)
    if deferred is not None:
        raise GateRefused("repo-deferred", deferred.reason)
    if repo not in registry.enabledRepos:
        raise GateRefused("repo-not-enabled", f"{repo} is not an enabled repository")
    number = int(request["number"])
    prior = state.terminalFor(root, repo, number, action)
    if prior is not None:
        raise AlreadyDone("already-recorded", f"outcome already recorded: {prior['state']}", prior)
    live = snap.row
    if int(live["number"]) != number:
        raise GateRefused("snapshot-mismatch", "the live snapshot is for a different pull request")
    if snap.merged or live.get("merged"):
        raise AlreadyDone("already-merged", "GitHub shows this pull request merged", {"mergeCommitSha": snap.mergeCommitSha})
    if live.get("state") != "open":
        if action == "close":
            raise AlreadyDone("already-closed", "GitHub shows this pull request closed", {})
        raise GateRefused("closed-unmerged", "the pull request is closed without being merged")
    if live["headSha"] != request["expectedHeadSha"]:
        raise GateRefused("head-moved", f"head is {live['headSha'][:12]}, the action names {str(request['expectedHeadSha'])[:12]}")
    if live["baseRef"] != request["baseRef"] or live["baseRef"] not in pol.destinations:
        raise GateRefused("destination-not-allowed", f"destination {live['baseRef']!r} is not authorized by policy")
    if str(request["repo"]) != str(request.get("evaluatedRepo", request["repo"])):
        raise GateRefused("repo-mismatch", "the action and the snapshot name different repositories")


def reserveWrite(root: Path, request: Mapping[str, Any], runId: str, action: str, row: Mapping[str, Any], now: datetime,
                 policy: StewardPolicy, digest: str) -> None:
    pol = policy.pr_maintenance
    repo, number = str(request["repo"]), int(request["number"])
    ceiling = pol.maxMergesPerRun if action == "merge" else pol.maxClosuresPerRun
    with state.lock(root):
        prior = state.terminalFor(root, repo, number, action)
        if prior is not None:
            raise AlreadyDone("already-recorded", f"outcome already recorded: {prior['state']}", prior)
        held = state.openReservation(root, repo, number, action, now)
        if held is not None and not held["stale"]:
            raise GateRefused("concurrent-attempt", f"run {held.get('runId')} holds a live reservation for this pull request")
        if state.writesInRun(root, runId, action) >= ceiling:
            raise GateRefused("run-budget-exhausted", f"this run already spent its {ceiling} {action} budget; the queue resumes next run")
        if state.writesWithin(root, now) >= pol.hourlyWriteCap:
            raise GateRefused("hourly-budget-exhausted", f"{pol.hourlyWriteCap} merges and closures already spent in the last hour")
        state.appendRecord(root, "outcomes", {
            "at": isoNow(now), "runId": runId, "repo": repo, "number": number, "action": action,
            "headSha": row["headSha"], "state": "reserved", "authorizationSha256": digest})


def authorization(request: Mapping[str, Any], row: Mapping[str, Any], evaluationSha: str, verification: Mapping[str, Any],
                  action: str, method: str, now: datetime, runId: str, authority: Mapping[str, str] | None = None) -> dict[str, Any]:
    body = {"action": action, "repo": request["repo"], "number": int(request["number"]), "headSha": row["headSha"],
            "baseRef": row["baseRef"], "baseSha": row["baseSha"], "method": method, "producerId": request["producerId"],
            "runId": runId, "evaluationSha256": evaluationSha, "verifier": verification["verifier"]["agentId"],
            "authority": dict(authority or {}), "reservedAt": isoNow(now), "expiresAt": isoNow(now + timedelta(seconds=AUTH_TTL_SECONDS))}
    return {**body, "digest": hashlib.sha256(stable_json(body).encode("utf-8")).hexdigest()}


def gateMerge(root: Path, request: Mapping[str, Any], snap: Snapshot, now: datetime, runId: str, *,
              policy: StewardPolicy | None = None, registry: Registry | None = None, requireTrail: bool = True) -> dict[str, Any]:
    policy, registry = context(root, policy, registry)
    commonChecks(root, request, snap, now, "merge", policy, registry)
    row = snap.row
    evaluation = evaluate(root, registry, str(request["repo"]), row, snap.tips, snap.protection, snap.siblings, snap.closed)
    if evaluation is None or evaluation.kind != KIND_MERGE:
        why = "; ".join(evaluation.reasons[:3]) if evaluation else "not a registered producer pull request"
        raise GateRefused("not-eligible", f"{evaluation.kind if evaluation else 'unregistered'}: {why}")
    if evaluation.producerId != request.get("producerId"):
        raise GateRefused("producer-mismatch", "the action names a different producer than the one proven")
    producer = registry.producer(evaluation.producerId)
    assert producer is not None
    method = str(request.get("method") or producer.mergeMethod)
    if method != producer.mergeMethod or method not in policy.pr_maintenance.mergeMethods:
        raise GateRefused("merge-method-not-allowed", f"{method!r} is not the producer's authorized method")
    if row.get("mergeableState") != "clean":
        raise GateRefused("branch-protection", f"GitHub reports mergeable state {row.get('mergeableState')!r}, not clean")
    if not snap.protection.get("complete"):
        raise GateRefused("branch-protection", "branch protection could not be read; refusing rather than assuming")
    found = verificationFor(root, request, row, snap.tips[row["baseRef"]], now, policy.pr_maintenance.verificationTtlSeconds, "merge")
    if requireTrail:
        head12 = row["headSha"][:12]
        comments = row.get("comments") or []
        for kind in ("pickup", "verification"):
            if receipts.findReceipt(comments, kind, int(request["number"]), head12) is None:
                raise GateRefused("trail-missing", f"no trusted {kind} receipt for head {head12} is on the pull request")
    auth = authorization(request, row, evaluation.digest(), found, "merge", method, now, runId, authorityInfo(root))
    reserveWrite(root, request, runId, "merge", row, now, policy, auth["digest"])
    return auth


def gateClose(root: Path, request: Mapping[str, Any], snap: Snapshot, now: datetime, runId: str, *,
              policy: StewardPolicy | None = None, registry: Registry | None = None) -> dict[str, Any]:
    policy, registry = context(root, policy, registry)
    commonChecks(root, request, snap, now, "close", policy, registry)
    row = snap.row
    evaluation = evaluate(root, registry, str(request["repo"]), row, snap.tips, snap.protection, snap.siblings, snap.closed)
    if evaluation is None or evaluation.kind != KIND_CLOSURE:
        raise GateRefused("closure-not-proven", (evaluation.kind + ": " + "; ".join(evaluation.reasons[:2])) if evaluation
                          else "not a registered producer pull request")
    producer = registry.producer(str(evaluation.producerId))
    assert producer is not None
    by = {g.name: g.state for g in evaluation.gates}
    blockers = [name for name in ("provenance", "draft", "holds", "reviews", "hold-comment", "review-threads") if by.get(name) != "pass"]
    if blockers:  # defense in depth: a founder hold, draft or unresolved thread is never overridden by supersession
        raise GateRefused("closure-held", f"gates not passing: {', '.join(blockers)}")
    if evaluation.closureReason not in producer.closureEligibility or evaluation.closureReason != request.get("reason"):
        raise GateRefused("closure-reason-not-eligible", f"{request.get('reason')!r} is not the proven, eligible reason")
    if not evaluation.replacement or int(request.get("replacement") or 0) != evaluation.replacement:
        raise GateRefused("replacement-missing", "the named replacement is not a merged pull request that carries this PR's marker")
    found = verificationFor(root, request, row, snap.tips[row["baseRef"]], now, policy.pr_maintenance.verificationTtlSeconds, "close")
    if receipts.findReceipt(row.get("comments") or [], "closed", int(request["number"]), row["headSha"][:12]) is None:
        raise GateRefused("justification-missing", "the closure justification must be posted before the pull request is closed")
    auth = authorization(request, row, evaluation.digest(), found, "close", "close", now, runId, authorityInfo(root))
    reserveWrite(root, request, runId, "close", row, now, policy, auth["digest"])
    return auth


def checkAuthorization(root: Path, auth: Mapping[str, Any]) -> None:
    """The authorization must be intact and match a still-open reservation. A forged, replayed or aborted one is refused."""

    body = {key: value for key, value in auth.items() if key != "digest"}
    if hashlib.sha256(stable_json(body).encode("utf-8")).hexdigest() != auth.get("digest"):
        raise GateRefused("authorization-forged", "the authorization's digest does not match its contents")
    match = None
    for line in state.readRecords(root, "outcomes"):
        if (line.get("repo"), line.get("number"), line.get("action")) != (auth["repo"], auth["number"], auth["action"]):
            continue
        if line.get("state") == "reserved":
            match = line  # the LATEST reservation for this pull request and action supersedes every earlier one
        elif line.get("state") in state.SETTLED:
            match = None
    if match is None or match.get("authorizationSha256") != auth["digest"] or match.get("headSha") != auth["headSha"]:
        raise GateRefused("unknown-authorization", "no open reservation matches this authorization (never issued, already settled or aborted)")


def finalize(root: Path, auth: Mapping[str, Any], snap: Snapshot, now: datetime, *, parents: Sequence[str] = (),
             postMerge: str = "not observed") -> dict[str, Any]:
    """Settle a reservation from GitHub's *observed* state. The driver's word is never the proof."""

    checkAuthorization(root, auth)
    row = snap.row
    base = {"at": isoNow(now), "runId": auth["runId"], "repo": auth["repo"], "number": auth["number"],
            "action": auth["action"], "headSha": auth["headSha"], "authorizationSha256": auth["digest"],
            **({"lateAuthorization": True} if isoNow(now) > str(auth.get("expiresAt")) else {})}
    if auth["action"] == "merge":
        merged = bool(snap.merged or row.get("merged"))
        headOk = row.get("headSha") == auth["headSha"]
        if merged and headOk and snap.mergeCommitSha:
            outcome = {**base, "state": "merged", "mergeCommitSha": snap.mergeCommitSha, "method": auth["method"],
                       "parentsVerified": auth["headSha"] in list(parents), "postMerge": postMerge}
        elif merged and not headOk:
            outcome = {**base, "state": "failed", "reason": "merged at a different head than the one authorized"}
        else:
            outcome = {**base, "state": "failed", "reason": "GitHub does not show the pull request merged"}
    else:
        closed = row.get("state") == "closed" and not (snap.merged or row.get("merged"))
        outcome = {**base, "state": "closed" if closed else "failed",
                   **({} if closed else {"reason": "GitHub does not show the pull request closed without merge"})}
    with state.lock(root):
        state.appendRecord(root, "outcomes", outcome)
    return outcome


def abort(root: Path, auth: Mapping[str, Any], reason: str, now: datetime) -> dict[str, Any]:
    """The driver did not perform the call (an error before it): release the reservation, recording why."""

    checkAuthorization(root, auth)
    outcome = {"at": isoNow(now), "runId": auth["runId"], "repo": auth["repo"], "number": auth["number"], "action": auth["action"],
               "headSha": auth["headSha"], "state": "aborted", "reason": reason[:300]}
    with state.lock(root):
        state.appendRecord(root, "outcomes", outcome)
    return outcome


def asJson(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)
