"""Routine 19 eligibility and shared preparation, never a bearer send grant.

All existing producer, content/scope, independent verification, head/base,
approval, hold, protection and kill requirements remain. Receipt POSTs are best
effort, while failed required reads refuse. Production services additionally
prove full CURRENT canonical authority and repeat these gates at adapter entry.
The coordinator alone owns global slot/fences/attempt accounting and outcomes.
Legacy local authorization/reservation APIs explicitly refuse; their old JSON
and caller-supplied snapshots cannot authorize an effect or settlement.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from gaia_cli.steward.policy import PolicyError, StewardPolicy
from gaia_cli.steward.prmaintenance import state
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
COORDINATION = "canonical-git-ref-v1"


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
    # Legacy eligibility diagnostics only; this helper is never execution authority.
    return {"mode": "ref" if ref else "local-head", "source": ref or "HEAD", "commit": head, "coordination": "none-legacy-diagnostic"}


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
                 policy: StewardPolicy, registry: Registry, *, currentAuthority: bool = False) -> None:
    pol = policy.pr_maintenance
    reason = state.killSwitchActive(root, pol.killSwitch)
    if reason:
        raise GateRefused("kill-switch", f"PR maintenance writes are revoked: {reason}")
    if not currentAuthority and pol.writeCoordination is None:
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
    raise GateRefused("legacy-route-disabled", "local reservations cannot authorize a critical write; use shared preparation")


def authorization(request: Mapping[str, Any], row: Mapping[str, Any], evaluationSha: str, verification: Mapping[str, Any],
                  action: str, method: str, now: datetime, runId: str, authority: Mapping[str, str] | None = None) -> dict[str, Any]:
    raise GateRefused("legacy-route-disabled", "authorization JSON is not a send grant")


def validateWrite(root: Path, request: Mapping[str, Any], snap: Snapshot, now: datetime, action: str, *,
                  policy: StewardPolicy | None = None, registry: Registry | None = None,
                  verification: Mapping[str, Any] | None = None, currentAuthority: bool = False) -> Mapping[str, Any]:
    """Eligibility only. No reservation, send permission, receipt or local outcome authority."""
    if action == "close":
        return validateClose(root, request, snap, now, policy=policy, registry=registry,
                             verification=verification, currentAuthority=currentAuthority)
    policy, registry = context(root, policy, registry)
    commonChecks(root, request, snap, now, "merge", policy, registry, currentAuthority=currentAuthority)
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
    return verification or verificationFor(root, request, row, snap.tips[row["baseRef"]], now, policy.pr_maintenance.verificationTtlSeconds, "merge")


def validateClose(root: Path, request: Mapping[str, Any], snap: Snapshot, now: datetime, *,
                  policy: StewardPolicy | None = None, registry: Registry | None = None,
                  verification: Mapping[str, Any] | None = None, currentAuthority: bool = False) -> Mapping[str, Any]:
    policy, registry = context(root, policy, registry)
    commonChecks(root, request, snap, now, "close", policy, registry, currentAuthority=currentAuthority)
    row = snap.row
    evaluation = evaluate(root, registry, str(request["repo"]), row, snap.tips, snap.protection, snap.siblings, snap.closed)
    if evaluation is None or evaluation.kind != KIND_CLOSURE:
        raise GateRefused("closure-not-proven", (evaluation.kind + ": " + "; ".join(evaluation.reasons[:2])) if evaluation
                          else "not a registered producer pull request")
    if evaluation.producerId != request.get("producerId"):
        raise GateRefused("producer-mismatch", "the action names a different producer than the one proven")
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
    return verification or verificationFor(root, request, row, snap.tips[row["baseRef"]], now, policy.pr_maintenance.verificationTtlSeconds, "close")


def makeExecutor(root: Path):
    from gaia_cli.steward.prmaintenance.executor import makeExecutor as factory
    return factory(root)


def gateMerge(root: Path, request: Mapping[str, Any], snap: Snapshot, now: datetime, runId: str, *,
              policy: StewardPolicy | None = None, registry: Registry | None = None, requireTrail: bool = True) -> dict[str, Any]:
    # requireTrail is compatibility-only; receipt publication is never authority.
    found = validateWrite(root, request, snap, now, "merge", policy=policy, registry=registry)
    return makeExecutor(root).prepare({**request, "action": "merge"}, snap, found, runId)


def gateClose(root: Path, request: Mapping[str, Any], snap: Snapshot, now: datetime, runId: str, *,
              policy: StewardPolicy | None = None, registry: Registry | None = None) -> dict[str, Any]:
    found = validateWrite(root, request, snap, now, "close", policy=policy, registry=registry)
    return makeExecutor(root).prepare({**request, "action": "close"}, snap, found, runId)


def checkAuthorization(root: Path, auth: Mapping[str, Any]) -> None:
    """Compatibility identity check only; legacy bearer JSON is refused, never a grant."""

    if not isinstance(auth.get("operationId"), str):
        raise GateRefused("legacy-route-disabled", "raw authorization/local terminal JSON cannot settle or authorize writes")


def finalize(root: Path, auth: Mapping[str, Any], snap: Snapshot, now: datetime, *, parents: Sequence[str] = (),
             postMerge: str = "not observed") -> dict[str, Any]:
    """Settle a reservation from GitHub's *observed* state. The driver's word is never the proof."""

    checkAuthorization(root, auth)
    # Supplied snapshots/parents and caller success/failure claims are not settlement authority.
    return makeExecutor(root).recover(auth["operationId"])


def abort(root: Path, auth: Mapping[str, Any], reason: str, now: datetime) -> dict[str, Any]:
    """Cancel only durable unsent preparation; the caller's reason is not settlement proof."""

    checkAuthorization(root, auth)
    return makeExecutor(root).abort(auth["operationId"], reason)


def asJson(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)
