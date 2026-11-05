"""Explicit Routine 19 execution. Importing/constructing this module sends nothing.

Production requires a separately provisioned policy binding, protected canonical
Git history, drained old writers, and a trustworthy nonce-bound HTTPS clock.
Tests inject transports/services; no production namespace is initialized here.
"""

from __future__ import annotations

import base64
import copy
import http.client
import json
import math
import os
import secrets
import ssl
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from gaia_cli.steward import ledger
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.prmaintenance import collect, coordination as core, gate, proofs, state
from gaia_cli.steward.prmaintenance.policy import WriteCoordination, prAuthorityApproved
from gaia_cli.steward.prmaintenance.producers import loadRegistry


@dataclass(frozen=True, repr=False)
class HttpReply:
    status: int
    headers: dict = field(repr=False)
    body: Any = field(repr=False)


class HttpsTransport:
    """One HTTPS request per call, no retry/redirect, bounded response, no logs.

    The credential is in memory only and is sent only to this pinned origin.
    New connections avoid library pool retry behavior. Errors never include
    request/response values or credentials. 3xx is returned, never followed.
    """

    def __init__(self, origin: str, token: str | None = None):
        url = urlsplit(origin)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise core.CoordinationError("invalid pinned HTTPS origin")
        self.host, self.port, self.prefix = url.hostname, url.port, url.path.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, body: dict | None = None) -> HttpReply:
        if not path.startswith("/") or path.startswith("//") or ".." in path or "\r" in path or "\n" in path:
            raise core.CoordinationError("invalid bounded HTTP route")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "gaia-steward-r19",
                   "Cache-Control": "no-cache, no-store", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None if body is None else core.canonical(body)
        if data is not None:
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPSConnection(self.host, self.port, timeout=20, context=ssl.create_default_context())
        try:
            connection.request(method, self.prefix + path, body=data, headers=headers)
            response = connection.getresponse()
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("oversized response")
            payload = json.loads(raw) if raw else None
            return HttpReply(response.status, {k.lower(): v for k, v in response.getheaders()}, payload)
        except Exception:
            raise core.CoordinationError("HTTPS invocation failed or response unavailable") from None
        finally:
            connection.close()


class BoundedClock:
    """Concrete fresh-clock protocol, not host UTC or HTTPS Date alone.

    Provisioning MUST attest the endpoint's UTC error bound (maxSkewSeconds)
    and precision. Each GET carries a fresh nonce; the authenticated HTTPS body
    must echo it with integer unixSeconds and uncertaintySeconds. Cache-Control
    must contain no-store and Age must be absent/zero. No cached time is reused.
    Round trip and local monotonic progression are bounded; network delay is
    included in the upper bound. Provider skew/precision are mandatory external
    assumptions, NOT verified merely by receiving a response. Unconfigured or
    unverifiable endpoints are an activation gate, never a host-time fallback.
    """

    def __init__(self, contract: dict, transport=None, monotonic=time.monotonic):
        self.contract = dict(contract)
        url = urlsplit(contract["url"])
        self.transport = transport or HttpsTransport(f"https://{url.netloc}")
        self.path = url.path or "/"
        self.monotonic = monotonic
        self.last = None
        self.lastEnd = None

    def sample(self) -> core.TimeBounds:
        nonce = secrets.token_hex(24)
        start = self.monotonic()
        response = self.transport.request("GET", self.path + "?" + urlencode({"nonce": nonce}))
        end = self.monotonic()
        elapsed = end - start
        if (not math.isfinite(elapsed) or elapsed < 0 or elapsed > self.contract["maxRoundTripSeconds"]
                or (self.lastEnd is not None and start < self.lastEnd)):
            raise core.CoordinationError("clock network/freshness/monotonic contract failed")
        try:
            core.exact(response.body, {"nonce", "unixSeconds", "uncertaintySeconds"})
            instant, uncertainty = response.body["unixSeconds"], response.body["uncertaintySeconds"]
            core.integer(instant)
            core.integer(uncertainty, 0, self.contract["maxSkewSeconds"] + self.contract["precisionSeconds"])
            if (response.status != 200 or response.body["nonce"] != nonce
                    or "no-store" not in response.headers.get("cache-control", "").lower()
                    or response.headers.get("age", "0") != "0"):
                raise ValueError("stale/cache response")
            error = self.contract["maxSkewSeconds"] + self.contract["precisionSeconds"]
            sample = core.TimeBounds(instant - error, instant + error + math.ceil(elapsed), "nonce-bound-https-clock-v1")
            sample.validate()
        except (KeyError, TypeError, ValueError, core.CoordinationError):
            raise core.CoordinationError("clock source response failed its provisioned contract") from None
        if self.last is not None and (sample.lower < self.last.lower or sample.upper < self.last.upper
                or sample.lower > self.last.upper + math.ceil(end - self.lastEnd)):
            raise core.CoordinationError("authoritative clock regressed/future-inconsistent")
        self.last, self.lastEnd = sample, end
        return sample


def tokenFrom(operation: dict) -> core.Token:
    return core.tokenFor(operation)


def reported(operation: dict) -> dict:
    """Bounded public diagnostic; never include proof text, HTTP data or tokens."""
    action = operation["subject"]["action"]
    stateName = operation["state"]
    status = {"completed-effect": "merged" if action == "merge" else "closed",
              "observed-terminal": "already-merged", "completed-no-effect": "failed",
              "canceled-unsent": "aborted"}.get(stateName, stateName)
    return {"operationId": operation["operationId"], "state": status, "coordinationState": stateName,
            "number": operation["subject"]["number"], "headSha": operation["subject"]["headSha"],
            "action": action, "evidenceSha256": core.digest(operation["evidence"]) if operation["evidence"] else None}


class ProductionServices:
    def __init__(self, root: Path, binding: WriteCoordination, http, clock: BoundedClock, snapshot=None, currentTip=None):
        self.root, self.binding, self.http, self.time = root, binding, http, clock
        self.namespace = core.Namespace(binding.forgeHost, binding.repositoryId, binding.repositoryName, binding.epoch, binding.protocol)
        self.snapshot = snapshot or self.liveSnapshot
        self.currentTip = currentTip or self.canonicalTip
        self.coordinator = None
        self.responses: dict[str, HttpReply] = {}
        self.authorized = None

    def clock(self):
        return self.time.sample()

    def api(self, path, params=None):
        query = {**(params or {}), "steward_nonce": secrets.token_hex(16)}
        route = "/" + path.lstrip("/") + "?" + urlencode(query)
        response = self.http.request("GET", route)
        if (not 200 <= response.status < 300 or response.headers.get("age", "0") != "0"
                or response.headers.get("warning", "").startswith(("110", "111", "113"))):
            raise collect.CollectError("required live GET failed")
        return response.body, ""  # consumers use explicit paging; no mutation/header receipt authority

    def canonicalTip(self):
        result = proofs.git(self.root, "-c", f"remote.origin.url={self.binding.canonicalUrl}",
                            "ls-remote", "origin", f"refs/heads/{self.binding.authorityBranch}")
        if result.returncode:
            raise core.CoordinationError("canonical current authority ref unavailable")
        rows = [line.split() for line in result.stdout.decode().splitlines()]
        matches = [row[0] for row in rows if len(row) == 2 and row[1] == f"refs/heads/{self.binding.authorityBranch}"]
        if len(matches) != 1:
            raise core.CoordinationError("canonical current authority ref missing/ambiguous")
        core.sha(matches[0], git=True)
        return matches[0]

    def sourceTexts(self):
        repo = self.binding.repositoryName
        info, _ = self.api(f"repos/{repo}")
        if str(info.get("id")) != self.binding.repositoryId or info.get("full_name") != repo:
            raise core.CoordinationError("canonical forge repository identity changed")
        branch = f"repos/{repo}/git/ref/heads/{quote(self.binding.authorityBranch, safe='')}"
        ref, _ = self.api(branch)
        commit = ref.get("object", {}).get("sha")
        core.sha(commit, git=True)
        if self.currentTip() != commit:
            raise core.CoordinationError("API authority ref is not the current canonical Git ref")
        texts = {}
        for key, path in zip(("policy", "producerRegistry", "authority"), gate.AUTHORITY_FILES):
            content, _ = self.api(f"repos/{repo}/contents/{path}", {"ref": commit})
            try:
                if content.get("encoding") != "base64":
                    raise ValueError("unbounded/unsupported source encoding")
                raw = base64.b64decode(content["content"], validate=False)
                core.text(raw.decode("utf-8"), core.MAX_SOURCE_BYTES)
                local = (self.root / path).read_bytes()
                head = proofs.blob(self.root, "HEAD", path)
                if raw != local or raw != head:
                    raise ValueError("stale/dirty local source")
                texts[key] = raw.decode("utf-8")
            except (KeyError, TypeError, ValueError, OSError):
                raise core.CoordinationError("current committed authority source unavailable or different") from None
        again, _ = self.api(branch)
        if again.get("object", {}).get("sha") != commit or self.currentTip() != commit:
            raise core.CoordinationError("canonical authority changed during read")
        dirty = proofs.git(self.root, "status", "--porcelain", "--untracked-files=all", "--", *gate.AUTHORITY_FILES)
        policy = StewardPolicy.load(self.root)
        if (dirty.returncode or dirty.stdout.strip() or policy.pr_maintenance_error
                or policy.pr_maintenance.writeCoordination != self.binding or not prAuthorityApproved(self.root)):
            raise core.CoordinationError("current authority/configuration invalid or revoked")
        return texts, policy, commit

    def limits(self):
        _, policy, _ = self.sourceTexts()
        pol = policy.pr_maintenance
        return core.Limits(min(2, pol.maxMergesPerRun), min(2, pol.maxClosuresPerRun), min(10, pol.hourlyWriteCap))

    def liveSnapshot(self, number):
        def fetch(n):
            # Fetch objects from the exact canonical transport, never a local
            # alternate authority ref or a credential-bearing argv URL.
            for refspec in (f"+refs/pull/{n}/head:refs/steward/pr/{n}",
                            f"+refs/heads/{self.binding.authorityBranch}:refs/steward/pr-authority-current"):
                result = proofs.git(self.root, "-c", f"remote.origin.url={self.binding.canonicalUrl}", "fetch", "--quiet", "--no-tags", "origin", refspec)
                if result.returncode:
                    raise core.CoordinationError("required canonical git objects unavailable")
        return collect.liveSnapshot(self.api, self.binding.repositoryName, number, fetch)

    def verificationRecord(self, subject, bindingProof, now, policy):
        try:
            detail = json.loads(bindingProof["verification"]["detail"])
            core.exact(detail, {"record", "dispatch"})
            record, dispatch = detail["record"], detail["dispatch"]
            at = datetime.strptime(record["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            if (at > now.lower or now.upper - at > policy.pr_maintenance.verificationTtlSeconds
                    or record["headSha"] != subject["headSha"] or record["baseSha"] != subject["baseSha"]
                    or record["verdict"] != "pass" or record["action"] != subject["action"]
                    or record["number"] != subject["number"] or record["repo"] != self.binding.repositoryName
                    or record["policySha256"] != gate.policyDigest(self.root)
                    or not record["builders"] or record["verifier"]["agentId"] in record["builders"]
                    or bindingProof["verification"]["verifier"] != record["verifier"]["agentId"]
                    or bindingProof["verification"]["builder"] != core.digest(record["builders"])
                    or not set(dispatch["builders"]).issubset(set(record["builders"]))
                    or record["verifier"].get("effort") in gate.BADEFFORTS or not record["verifier"].get("profileId")
                    or not record["proofs"] or any(p["state"] != "pass" for p in record["proofs"])
                    or dispatch["dispatchId"] != record["dispatchId"] or dispatch["role"] != "verifier"
                    or dispatch["status"] != "started" or dispatch["agentId"] != record["verifier"]["agentId"]
                    or dispatch["effort"] != record["verifier"]["effort"] or dispatch["runId"] != record["runId"]
                    or dispatch["subject"] != {"repo": record["repo"], "number": record["number"], "headSha": record["headSha"]}):
                raise ValueError("verification binding/independence/freshness failed")
            # A newer local FAIL is an additional stop, never an admission source.
            for recent in state.readRecords(self.root, "verifications"):
                if (recent.get("headSha") == subject["headSha"] and recent.get("number") == subject["number"]
                        and recent.get("action") == subject["action"] and recent.get("repo") == self.binding.repositoryName
                        and recent.get("at", "") >= record["at"] and recent.get("verdict") != "pass"):
                    raise ValueError("verification revoked")
            return record
        except (ValueError, TypeError, KeyError):
            raise core.CoordinationError("durable independent verification invalid/stale/revoked") from None

    def authorize(self, namespace, subject, bindingProof):
        if namespace != self.namespace:
            raise core.CoordinationError("wrong immutable namespace")
        texts, policy, _ = self.sourceTexts()
        if any(bindingProof[key] != value for key, value in texts.items()):
            raise core.CoordinationError("exact current authority source changed")
        now = self.clock()
        record = self.verificationRecord(subject, bindingProof, now, policy)
        snap = self.snapshot(subject["number"])
        if str(snap.row.get("prId")) != subject["prId"] or str(snap.row.get("repositoryId")) != namespace.repositoryId:
            raise core.CoordinationError("immutable PR/repository identity mismatch")
        request = {"repo": namespace.repositoryName, "number": subject["number"], "expectedHeadSha": subject["headSha"],
                   "baseRef": subject["baseRef"], "producerId": subject["producerId"], "method": "merge",
                   "reason": subject["reason"], "replacement": (subject["replacement"] or {}).get("number")}
        if snap.tips.get(subject["baseRef"]) != subject["baseSha"]:
            raise core.CoordinationError("destination moved since independent verification")
        gate.validateWrite(self.root, request, snap, datetime.fromtimestamp(now.upper, timezone.utc), subject["action"],
                           policy=policy, registry=loadRegistry(self.root), verification=record, currentAuthority=True)
        self.authorized = (copy.deepcopy(subject), copy.deepcopy(bindingProof))

    def invoke(self, request, invocationId):
        if self.coordinator is None or self.authorized is None:
            raise core.CoordinationError("no live executor control flow")
        current = self.coordinator.inspect()
        operation = next((op for op in current["operations"].values() if op["invocationId"] == invocationId), None)
        if operation is None or operation["request"] != request or operation["state"] not in core.PENDING:
            raise core.CoordinationError("exact claimed invocation unavailable")
        # Re-read every authority, policy, independent proof, live gate and kill
        # after claim and immediately before the sole HTTP mutation. A refusal
        # here conservatively pins the claim; it never refunds/resends.
        self.authorize(self.namespace, operation["subject"], operation["proof"])
        response = self.http.request(request["method"], request["path"], copy.deepcopy(request["body"]))
        self.responses[invocationId] = response
        return response

    def pullFact(self, operation):
        repo = self.binding.repositoryName
        info, _ = self.api(f"repos/{repo}")
        pull, _ = self.api(f"repos/{repo}/pulls/{operation['subject']['number']}")
        if (str(info.get("id")) != self.namespace.repositoryId or info.get("full_name") != repo
                or str(pull.get("id")) != operation["subject"]["prId"]):
            raise core.CoordinationError("independent outcome identity mismatch")
        return pull

    def mergeFact(self, operation, pull):
        commit = pull.get("merge_commit_sha")
        if not pull.get("merged") or (pull.get("head") or {}).get("sha") != operation["subject"]["headSha"] or not commit:
            return False
        core.sha(commit, git=True)
        parents = collect.mergeParents(self.api, self.binding.repositoryName, commit)
        return operation["subject"]["headSha"] in parents and len(parents) == 2

    def evidence(self, operation, kind, observedState, detail):
        return {"kind": kind, **{key: operation[key] for key in ("operationId", "attemptId", "requestDigest", "invocationId")},
                "headSha": operation["subject"]["headSha"], "source": "authenticated-sole-response+independent-forge-read-v1",
                "detail": json.dumps(detail, sort_keys=True), "observedState": observedState}

    def completion(self, operation, invocationId, response):
        if self.responses.pop(invocationId, None) is not response or not isinstance(response, HttpReply):
            raise core.CoordinationError("not an authentic completion of this sole invocation")
        if response.status in {401, 403, 404, 405, 409, 422}:
            return self.evidence(operation, "completed-no-effect", "rejected", {"responseStatus": response.status, "senderFinished": True})
        if response.status != 200 or not isinstance(response.body, dict):
            raise core.CoordinationError("response does not prove a completed effect or definite rejection")
        pull = self.pullFact(operation)
        if operation["subject"]["action"] == "merge":
            if (response.body.get("merged") is not True or not self.mergeFact(operation, pull)
                    or response.body.get("sha") != pull.get("merge_commit_sha")):
                raise core.CoordinationError("matching independently verified merge/parent proof unavailable")
            return self.evidence(operation, "completed-effect", "merged", {"responseStatus": 200, "senderFinished": True,
                                 "mergeCommitSha": pull["merge_commit_sha"], "parentsVerified": True})
        if (str(response.body.get("id")) != operation["subject"]["prId"] or response.body.get("state") != "closed"
                or response.body.get("merged") is True or not response.body.get("closed_at")):
            raise core.CoordinationError("close response does not prove sole invocation completion")
        return self.evidence(operation, "completed-effect", "reopened" if pull.get("state") == "open" else "closed",
                             {"responseStatus": 200, "senderFinished": True, "conditionalHead": False,
                              "responseHeadChanged": (response.body.get("head") or {}).get("sha") != operation["subject"]["headSha"],
                              "observedHeadChanged": (pull.get("head") or {}).get("sha") != operation["subject"]["headSha"],
                              "laterMerged": bool(pull.get("merged"))})

    def observation(self, operation):
        pull = self.pullFact(operation)
        if operation["subject"]["action"] == "merge" and self.mergeFact(operation, pull):
            return self.evidence(operation, "observed-terminal", "merged", {"causation": "unknown", "parentsVerified": True,
                                 "mergeCommitSha": pull["merge_commit_sha"]})
        return None  # closed/open/reopened is never proof a delayed PATCH is dead


class Executor:
    def __init__(self, coordinator: core.PrWriteCoordinator):
        self.coordinator = coordinator
        self.services = coordinator.services
        if isinstance(self.services, ProductionServices):
            self.services.coordinator = coordinator

    def prepare(self, request, snap, found, runId):
        service = self.services
        texts, _, sourceCommit = service.sourceTexts()
        action = request["action"]
        replacement = None
        if action == "close":
            number = int(request["replacement"])
            row, _ = service.api(f"repos/{service.binding.repositoryName}/pulls/{number}")
            if not row.get("merged"):
                raise core.CoordinationError("replacement no longer merged")
            replacement = {"repositoryId": service.namespace.repositoryId, "prId": str(row["id"]), "number": number,
                           "headSha": row["head"]["sha"]}
        subject = {"number": int(request["number"]), "prId": str(snap.row.get("prId") or ""), "action": action,
                   "headSha": snap.row["headSha"], "baseRef": snap.row["baseRef"], "baseSha": snap.tips[snap.row["baseRef"]],
                   "producerId": request["producerId"], "reason": str(request.get("reason") or ""), "replacement": replacement}
        dispatch = next((d for d in reversed(state.readRecords(service.root, "dispatches")) if d.get("dispatchId") == found.get("dispatchId")), None)
        if dispatch is None:
            raise core.CoordinationError("independent dispatch proof missing")
        selected = {key: found[key] for key in ("at", "runId", "dispatchId", "builders", "verifier", "policySha256", "action", "repo", "number", "headSha", "baseSha", "verdict")}
        # Do not persist candidate snippets/free-form verifier notes. Keep the
        # genuine verifier verdict, named checks and bounded content commitments.
        selected["proofs"] = [{"name": core.digest(str(p.get("name"))), "state": p.get("state"),
                               "evidenceSha256": core.digest(p.get("detail"))} for p in found["proofs"]]
        named = {"repo": found["repo"], "number": found["number"], "headSha": found["headSha"]}
        if named not in (dispatch.get("envelope") or {}).get("subjects", []):
            raise core.CoordinationError("independent dispatch does not name the exact subject")
        attestation = {"record": selected, "dispatch": {key: dispatch.get(key) for key in ("dispatchId", "role", "status", "agentId", "effort", "runId", "builders")}}
        attestation["dispatch"]["subject"] = named
        bindingProof = {**texts, "justification": f"{action}: independently verified registered routine; reason={subject['reason']}; replacement={(replacement or {}).get('number')}",
                        "verification": {"builder": core.digest(found["builders"]), "verifier": found["verifier"]["agentId"], "result": "PASS",
                                         "headSha": subject["headSha"], "baseSha": subject["baseSha"], "source": f"canonical-current@{sourceCommit}",
                                         "detail": json.dumps(attestation, separators=(",", ":"), sort_keys=True)}}
        operationId = core.logicalId(service.namespace, subject)
        transition = core.digest([operationId, "reserve", runId])
        owner = core.digest([runId, operationId, "prepared-owner"])
        result = self.coordinator.reserve(subject, bindingProof, runId, owner, transition)
        if result.status == core.CommitStatus.UNRESOLVED or result.token is None:
            raise core.CoordinationError("shared reservation unresolved; no invocation authorized")
        self.coordinator.recordIntent(result.token, core.exactRequest(service.namespace, subject), core.digest([transition, "intent"]))
        return {**reported(self.coordinator.inspect()["operations"][operationId]), "repo": service.namespace.repositoryName,
                "runId": runId, "method": "merge" if action == "merge" else "close"}

    def execute(self, operationId):
        operation = self.coordinator.inspect()["operations"].get(operationId)
        if operation is None:
            raise core.Refused("unknown operation")
        if operation["state"] not in core.PREPARED:
            return reported(operation)  # persisted claim/terminal is inspection, NEVER a send grant
        result = self.coordinator.invoke(tokenFrom(operation), core.digest([operation["attemptId"], "sole-send"]))
        if result.status == core.CommitStatus.UNRESOLVED:
            return {**reported(self.coordinator.inspect()["operations"][operationId]), "commitStatus": result.status.value}
        return reported(self.coordinator.inspect()["operations"][operationId])

    def recover(self, operationId):
        operation = self.coordinator.inspect()["operations"].get(operationId)
        if operation is None:
            raise core.Refused("unknown operation")
        if operation["state"] in core.PENDING:
            self.coordinator.recover(operationId)
        return reported(self.coordinator.inspect()["operations"][operationId])

    def abort(self, operationId, reason):
        operation = self.coordinator.inspect()["operations"].get(operationId)
        if operation is None:
            raise core.Refused("unknown operation")
        self.coordinator.cancelPrepared(tokenFrom(operation), "operator canceled unsent preparation", core.digest([operation["attemptId"], "cancel"]))
        return reported(self.coordinator.inspect()["operations"][operationId])


def makeExecutor(root: Path, *, http=None, clock=None, store=None, snapshot=None) -> Executor:
    """Explicit factory. Missing binding refuses BEFORE auth/network/store access.

    Injection parameters are trusted test/application seams, not CLI flags or
    receipts. Normal construction always uses the canonical GitRef transport.
    """
    policy = StewardPolicy.load(root)
    binding = policy.pr_maintenance.writeCoordination
    if policy.pr_maintenance_error or binding is None:
        raise core.CoordinationError("writeCoordination unconfigured; separately verified provisioning/clock contract required")
    if http is None:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            result = subprocess.run(["gh", "auth", "token", "--hostname", binding.forgeHost], capture_output=True, timeout=20, check=False)
            if result.returncode:
                raise core.CoordinationError("in-memory forge authentication unavailable")
            token = result.stdout.decode().strip()
        apiHost = "api.github.com" if binding.forgeHost == "github.com" else binding.forgeHost
        http = HttpsTransport(f"https://{apiHost}" + ("" if binding.forgeHost == "github.com" else "/api/v3"), token)
    services = ProductionServices(root, binding, http, clock or BoundedClock(dict(binding.clock)), snapshot)
    namespace = services.namespace
    coordinator = core.PrWriteCoordinator(store or ledger.GitRefLedgerStore(root, ref=core.REF),
                                         core.Binding(namespace, binding.genesis, binding.historyPin, binding.canonicalUrl), services)
    return Executor(coordinator)
