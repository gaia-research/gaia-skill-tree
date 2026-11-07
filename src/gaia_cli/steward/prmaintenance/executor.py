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
import re
import secrets
import socket
import ssl
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from gaia_cli.steward import ledger
from gaia_cli.steward.policy import PolicyError, StewardPolicy
from gaia_cli.steward.prmaintenance import collect, coordination as core, gate, proofs, state
from gaia_cli.steward.prmaintenance.policy import WriteCoordination, prAuthorityApproved
from gaia_cli.steward.prmaintenance.producers import loadRegistry

# Sanitized post-entry uncertainty causes reported by ``execute``. The first four
# are protocol causes; "inspection" means the shared report could not be read
# after a possible effect. None of them claims the invocation had no effect.
UNCERTAINTY_CAUSES = core.InvocationUncertain.CAUSES + ("inspection",)


@dataclass(frozen=True, repr=False)
class HttpReply:
    status: int
    headers: dict = field(repr=False)
    body: Any = field(repr=False)


TRUST_OVERRIDES = ("SSL_CERT_FILE", "SSL_CERT_DIR")
REQUEST_DEADLINE_SECONDS = 30.0
CONNECT_TIMEOUT_SECONDS = 20


def refuseTrustOverrides() -> None:
    """An environment CA override would silently choose who the credential is trusted to reach."""
    if any(os.environ.get(key) for key in TRUST_OVERRIDES):
        raise core.CoordinationError("inherited TLS trust overrides (SSL_CERT_FILE/SSL_CERT_DIR) are not critical authority")


class HttpsTransport:
    """One HTTPS request per call, no retry/redirect, bounded response, no logs.

    The credential is in memory only and is sent only to this pinned origin.
    New connections avoid library pool retry behavior. Errors never include
    request/response values or credentials. 3xx is returned, never followed.

    Trust is the system default store only: SSL_CERT_FILE/SSL_CERT_DIR overrides are refused (the ``context``
    parameter is a trusted test/application seam, never an environment or CLI input). Failure to connect (DNS, TCP or
    TLS handshake) is raised as ``core.NotSent`` because no request byte has been written yet; every later failure is a
    plain CoordinationError, since a byte may have reached the peer. After connect, ``deadline`` seconds bound the
    whole request/response exchange in total (a watchdog shuts the socket), not merely each socket operation. Connect is
    bounded per address attempt by CONNECT_TIMEOUT_SECONDS plus the system resolver.
    """

    def __init__(self, origin: str, token: str | None = None, *, context: ssl.SSLContext | None = None,
                 deadline: float = REQUEST_DEADLINE_SECONDS):
        url = urlsplit(origin)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise core.CoordinationError("invalid pinned HTTPS origin")
        if context is None:
            refuseTrustOverrides()
        if not isinstance(deadline, (int, float)) or isinstance(deadline, bool) or not 0 < deadline <= 120:
            raise core.CoordinationError("invalid HTTPS request deadline")
        self.host, self.port, self.prefix = url.hostname, url.port, url.path.rstrip("/")
        self.token = token
        self.context = context
        self.deadline = float(deadline)

    @staticmethod
    def abort(sock) -> None:
        # Wake the blocked reader with a raw shutdown of the RETAINED connected socket. http.client sets
        # connection.sock to None on Connection: close and HTTP/1.0 responses while the body still reads from the live
        # descriptor, so the connection attribute is never consulted. The owning thread closes everything itself:
        # closing a descriptor from another thread would race with descriptor reuse, and SSLSocket.shutdown would also
        # discard the TLS object under a read in progress, so the base-class method is called directly.
        if sock is not None:
            try:
                socket.socket.shutdown(sock, socket.SHUT_RDWR)
            except (OSError, TypeError):
                pass

    def request(self, method: str, path: str, body: dict | None = None) -> HttpReply:
        if not path.startswith("/") or path.startswith("//") or ".." in path or "\r" in path or "\n" in path:
            raise core.NotSent("invalid bounded HTTP route")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "gaia-steward-r19",
                   "Cache-Control": "no-cache, no-store", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None if body is None else core.canonical(body)
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.context is None:
            refuseTrustOverrides()
        try:
            context = self.context or ssl.create_default_context()
            connection = http.client.HTTPSConnection(self.host, self.port, timeout=CONNECT_TIMEOUT_SECONDS, context=context)
        except Exception:
            raise core.NotSent("HTTPS invocation failed or response unavailable") from None
        watchdog = None
        try:
            try:
                connection.connect()  # DNS + TCP + TLS handshake; no request byte exists yet
            except Exception:
                raise core.NotSent("HTTPS invocation failed or response unavailable") from None
            connected = getattr(connection, "sock", None)  # retained now: the body may outlive connection.sock
            watchdog = threading.Timer(self.deadline, self.abort, args=(connected,))
            watchdog.daemon = True
            watchdog.start()
            connection.request(method, self.prefix + path, body=data, headers=headers)
            response = connection.getresponse()
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("oversized response")
            payload = json.loads(raw) if raw else None
            return HttpReply(response.status, {k.lower(): v for k, v in response.getheaders()}, payload)
        except core.NotSent:
            raise
        except Exception:
            raise core.CoordinationError("HTTPS invocation failed or response unavailable") from None
        finally:
            if watchdog is not None:
                watchdog.cancel()
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
        core.exact(contract, {"url", "maxSkewSeconds", "precisionSeconds", "maxRoundTripSeconds"})
        core.integer(contract["maxSkewSeconds"], 0, 5)
        core.integer(contract["precisionSeconds"], 1, 1)  # integer Unix seconds require quantization allowance
        core.integer(contract["maxRoundTripSeconds"], 1, 5)
        core.text(contract["url"], 2048)
        if any(char.isspace() for char in contract["url"]):
            raise core.CoordinationError("invalid provisioned clock endpoint")
        self.contract = dict(contract)
        url = urlsplit(contract["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise core.CoordinationError("invalid provisioned clock endpoint")
        if url.port is not None:
            core.integer(url.port, 1, 65535)
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
                    or "no-store" not in {part.strip().lower() for part in response.headers.get("cache-control", "").split(",")}
                    or response.headers.get("age", "0") != "0"):
                raise ValueError("stale/cache response")
            error = self.contract["maxSkewSeconds"] + self.contract["precisionSeconds"]
            sample = core.TimeBounds(instant - error, instant + error + math.ceil(elapsed), "nonce-bound-https-clock-v1")
            sample.validate()
        except (KeyError, TypeError, ValueError, core.CoordinationError):
            raise core.CoordinationError("clock source response failed its provisioned contract") from None
        if self.last is not None and (sample.lower < self.last.lower or sample.upper < self.last.upper
                or sample.lower > self.last.upper + math.ceil(end - self.lastEnd)
                or sample.upper < self.last.lower + math.floor(start - self.lastEnd)):
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
              "canceled-after-claim": "failed", "canceled-unsent": "aborted"}.get(stateName, stateName)
    result = {"operationId": operation["operationId"], "state": status, "coordinationState": stateName,
              "number": operation["subject"]["number"], "headSha": operation["subject"]["headSha"],
              "action": action, "evidenceSha256": core.digest(operation["evidence"]) if operation["evidence"] else None}
    if operation["evidence"]:
        result["observedState"] = operation["evidence"]["observedState"]
        try:
            detail = json.loads(operation["evidence"]["detail"])
            if detail.get("mergeCommitSha"):
                core.sha(detail["mergeCommitSha"], git=True)
                result["mergeCommitSha"] = detail["mergeCommitSha"]
            for key in ("conditionalHead", "responseHeadChanged", "observedHeadChanged", "responseBaseChanged", "observedBaseChanged", "laterMerged"):
                if type(detail.get(key)) is bool:
                    result[key] = detail[key]
            summary = detail.get("postMergeChecks")
            if isinstance(summary, dict) and summary.get("observed") is False:
                result["postMergeChecks"] = {"observed": False}
            elif isinstance(summary, dict) and summary.get("observed") is True:
                core.exact(summary, {"observed", "total", "counts"})
                core.integer(summary["total"], 0, 1000000)
                allowed = {"queued", "in_progress", "success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "stale", "unknown"}
                if not isinstance(summary["counts"], dict) or set(summary["counts"]) - allowed:
                    raise ValueError("invalid check summary")
                for count in summary["counts"].values():
                    core.integer(count, 0, 1000000)
                if sum(summary["counts"].values()) != summary["total"]:
                    raise ValueError("invalid check total")
                result["postMergeChecks"] = copy.deepcopy(summary)
        except (ValueError, AttributeError, core.CoordinationError):
            pass  # never export free-form response/candidate values
    if stateName == "completed-no-effect":
        result["reason"] = "sole invocation completed without effect; sent attempt remains charged"
    elif stateName == "canceled-after-claim":
        result["reason"] = ("adapter proved no request byte was sent; slot released, attempt and charge remain counted, "
                            "no retry or refund")
    elif stateName == "canceled-unsent":
        result["reason"] = "unsent preparation canceled; anti-replay record retained"
    return result


class ProductionServices:
    def __init__(self, root: Path, binding: WriteCoordination, http, clock: BoundedClock, snapshot=None, currentTip=None):
        if any(os.environ.get(key) for key in (
            "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_REPLACE_REF_BASE",
            "GIT_GRAFT_FILE", "GIT_COMMON_DIR",
        )):
            raise core.CoordinationError("inherited Git object/worktree overrides are not critical authority")
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

    def remoteGit(self, *args):
        if self.coordinator is None or self.coordinator.store.repo_root.resolve() != self.root.resolve():
            raise core.CoordinationError("canonical source transport is unavailable")
        # Reuse the tested transport's noninteractive, sanitized subprocess
        # plumbing. This reads source refs/objects, never the general ledger.
        return self.coordinator.store.git(["-c", f"remote.origin.url={self.binding.canonicalUrl}", *args], timeout=60)

    def canonicalTip(self):
        result = self.remoteGit("ls-remote", "origin", f"refs/heads/{self.binding.authorityBranch}")
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
        if proofs.git(self.root, "cat-file", "-e", f"{commit}^{{commit}}").returncode:
            fetched = self.remoteGit("fetch", "--quiet", "--no-tags", "origin",
                                     f"+refs/heads/{self.binding.authorityBranch}:refs/steward/pr-authority-current")
            if fetched.returncode:
                raise core.CoordinationError("canonical authority commit objects unavailable")
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
                if raw != local or raw != head or raw != proofs.blob(self.root, commit, path):
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
                result = self.remoteGit("fetch", "--quiet", "--no-tags", "origin", refspec)
                if result.returncode:
                    raise core.CoordinationError("required canonical git objects unavailable")
        return collect.liveSnapshot(self.api, self.binding.repositoryName, number, fetch)

    def verificationRecord(self, subject, bindingProof, now, policy):
        try:
            detail = json.loads(bindingProof["verification"]["detail"])
            core.exact(detail, {"record", "dispatch"})
            record, dispatch = detail["record"], detail["dispatch"]
            at = datetime.strptime(record["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            core.integer(record["proofCount"], 1, 1024)
            core.sha(record["proofsSha256"])
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
        if subject["replacement"] is not None:
            replacement, _ = self.api(f"repos/{namespace.repositoryName}/pulls/{subject['replacement']['number']}")
            if (not replacement.get("merged") or str(replacement.get("id")) != subject["replacement"]["prId"]
                    or (replacement.get("head") or {}).get("sha") != subject["replacement"]["headSha"]
                    or subject["replacement"]["repositoryId"] != namespace.repositoryId):
                raise core.CoordinationError("exact replacement identity/head changed")
        gate.validateWrite(self.root, request, snap, datetime.fromtimestamp(now.upper, timezone.utc), subject["action"],
                           policy=policy, registry=loadRegistry(self.root), verification=record, currentAuthority=True)
        self.authorized = (copy.deepcopy(subject), copy.deepcopy(bindingProof))

    def invoke(self, request, invocationId):
        # Everything before the HTTP request is a provable no-send: the committed claim handed over by the coordinator
        # (no ledger read) and the live re-check. A refusal there is NotSent, which releases the slot as
        # canceled-after-claim while keeping the attempt and its charge counted; it never refunds or resends. An entry
        # refusal (copy, other thread, fork, re-entry) stays a plain Refused: it is not the coordinator's own flow.
        if self.coordinator is None or self.authorized is None:
            raise core.CoordinationError("no live executor control flow")
        operation = self.coordinator._consumeAdapter(self, request, invocationId)
        try:
            if (operation["request"] != request or operation["invocationId"] != invocationId
                    or operation["state"] != "possibly-sent"):
                raise core.CoordinationError("exact claimed invocation unavailable")
            # Re-read every authority, policy, independent proof, live gate and kill after claim and immediately
            # before the sole HTTP mutation.
            self.authorize(self.namespace, operation["subject"], operation["proof"])
        except Exception as exc:
            raise core.NotSent("no request byte was sent: live re-check refused") from exc
        # NotSent from the transport itself means the connection failed before the first request byte.
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
        if (not pull.get("merged") or (pull.get("head") or {}).get("sha") != operation["subject"]["headSha"]
                or (pull.get("base") or {}).get("ref") != operation["subject"]["baseRef"] or not commit):
            return False
        core.sha(commit, git=True)
        parents = collect.mergeParents(self.api, self.binding.repositoryName, commit)
        return operation["subject"]["headSha"] in parents and len(parents) == 2

    def postChecks(self, mergeCommit):
        try:
            runs = collect.listAll(self.api, f"repos/{self.binding.repositoryName}/commits/{mergeCommit}/check-runs", key="check_runs")
            counts = {}
            allowed = {"queued", "in_progress", "success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "stale"}
            for run in runs:
                status = run.get("conclusion") if run.get("status") == "completed" else run.get("status")
                key = status if isinstance(status, str) and status in allowed else "unknown"
                counts[key] = counts.get(key, 0) + 1
            return {"observed": True, "total": len(runs), "counts": counts}
        except (collect.CollectError, core.CoordinationError):
            return {"observed": False}  # post-merge diagnostics are not a pre-write gate or undo

    def evidence(self, operation, kind, observedState, detail):
        return {"kind": kind, **{key: operation[key] for key in ("operationId", "attemptId", "requestDigest", "invocationId")},
                "headSha": operation["subject"]["headSha"], "source": "authenticated-sole-response+independent-forge-read-v1",
                "detail": json.dumps(detail, sort_keys=True), "observedState": observedState}

    def completion(self, operation, invocationId, response):
        if self.responses.pop(invocationId, None) is not response or not isinstance(response, HttpReply):
            raise core.CompletionInvalid("not an authentic completion of this sole invocation")
        if response.status in {401, 403, 404, 405, 409, 422}:
            return self.evidence(operation, "completed-no-effect", "rejected", {"responseStatus": response.status, "senderFinished": True})
        if response.status != 200 or not isinstance(response.body, dict):
            # A non-200/opaque response cannot prove either an effect or a
            # definite rejection; only the transport outcome is unknown.
            raise core.CompletionUnavailable("response does not prove a completed effect or definite rejection")
        pull = self.pullFact(operation)
        if operation["subject"]["action"] == "merge":
            if (response.body.get("merged") is not True or not self.mergeFact(operation, pull)
                    or response.body.get("sha") != pull.get("merge_commit_sha")):
                raise core.CompletionInvalid("matching independently verified merge/parent proof unavailable")
            return self.evidence(operation, "completed-effect", "merged", {"responseStatus": 200, "senderFinished": True,
                                 "mergeCommitSha": pull["merge_commit_sha"], "parentsVerified": True,
                                 "postMergeChecks": self.postChecks(pull["merge_commit_sha"])})
        if (str(response.body.get("id")) != operation["subject"]["prId"] or response.body.get("state") != "closed"
                or response.body.get("merged") is True or not response.body.get("closed_at")):
            raise core.CompletionInvalid("close response does not prove sole invocation completion")
        return self.evidence(operation, "completed-effect", "reopened" if pull.get("state") == "open" else "closed",
                             {"responseStatus": 200, "senderFinished": True, "conditionalHead": False,
                              "responseHeadChanged": (response.body.get("head") or {}).get("sha") != operation["subject"]["headSha"],
                              "observedHeadChanged": (pull.get("head") or {}).get("sha") != operation["subject"]["headSha"],
                              "responseBaseChanged": (response.body.get("base") or {}).get("ref") != operation["subject"]["baseRef"],
                              "observedBaseChanged": (pull.get("base") or {}).get("ref") != operation["subject"]["baseRef"],
                              "laterMerged": bool(pull.get("merged"))})

    def observation(self, operation):
        pull = self.pullFact(operation)
        if operation["subject"]["action"] == "merge" and self.mergeFact(operation, pull):
            return self.evidence(operation, "observed-terminal", "merged", {"causation": "unknown", "parentsVerified": True,
                                 "mergeCommitSha": pull["merge_commit_sha"], "postMergeChecks": self.postChecks(pull["merge_commit_sha"])})
        return None  # closed/open/reopened is never proof a delayed PATCH is dead


class Executor:
    def __init__(self, coordinator: core.PrWriteCoordinator):
        self.coordinator = coordinator
        self.services = coordinator.services
        if isinstance(self.services, ProductionServices):
            self.services.coordinator = coordinator

    def report(self, operation):
        return {**reported(operation), "repo": self.coordinator.binding.namespace.repositoryName, "runId": operation["runId"]}

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
        safeNames = {"provenance", "scope", "holds", "reviews", "draft", "ci", "currency", "conflicts", "content", "policy",
                     "independent-review", "hold-comment", "review-threads", "approvals", "branch-protection"}
        if not found["proofs"] or any(p.get("state") != "pass" for p in found["proofs"]):
            raise core.CoordinationError("genuine complete PASS proof required")
        # Named structured checks remain readable. Free-form notes/candidate
        # snippets are committed by checksum, never copied into shared payload.
        names = sorted({str(p.get("name", "")).lower() if str(p.get("name", "")).lower() in safeNames
                        else "additional-independent-proof" for p in found["proofs"]})
        selected["proofs"] = [{"name": name, "state": "pass"} for name in names]
        selected["proofCount"] = len(found["proofs"])
        selected["proofsSha256"] = core.digest(found["proofs"])
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
        return {**self.report(self.coordinator.inspect()["operations"][operationId]), "repo": service.namespace.repositoryName,
                "runId": runId, "method": "merge" if action == "merge" else "close"}

    def execute(self, operationId):
        operation = self.coordinator.inspect()["operations"].get(operationId)
        if operation is None:
            raise core.Refused("unknown operation")
        if operation["state"] not in core.PREPARED:
            return self.report(operation)  # persisted claim/terminal is inspection, NEVER a send grant
        def uncertain(cause):
            # Bounded sanitized classification of the failed post-entry step. The
            # raw exception/message is never published. When shared state could not
            # be observed, ``state`` is a knowledge classification (possibly-sent),
            # not an observed store state; it grants no retry, refund or replay.
            if cause not in UNCERTAINTY_CAUSES:
                raise core.CoordinationError("invalid uncertainty cause")
            return {"operationId": operationId, "state": "possibly-sent", "coordinationState": "unavailable",
                    "uncertaintyCause": cause, "evidenceSha256": None,
                    "repo": self.coordinator.binding.namespace.repositoryName, "runId": operation["runId"],
                    "number": operation["subject"]["number"], "headSha": operation["subject"]["headSha"],
                    "action": operation["subject"]["action"],
                    "reason": "sole invocation or its settlement is uncertain; inspect shared state before any action"}
        try:
            result = self.coordinator.invoke(tokenFrom(operation), core.digest([operation["attemptId"], "sole-send"]))
        except core.InvocationUncertain as exc:
            return uncertain(exc.cause)
        except ledger.LedgerUnavailable:
            # Not a post-entry classification from the core. If the claim nevertheless committed, the sender is
            # outstanding: report uncertainty, never a refusal. A refusal before any claim leaves it prepared.
            try:
                after = self.coordinator.inspect()["operations"].get(operationId)
            except (ledger.LedgerUnavailable, KeyError, OSError):
                after = None
            if after is not None and after["state"] in core.PENDING:
                return uncertain("persistence")
            raise
        try:
            current = self.report(self.coordinator.inspect()["operations"][operationId])
        except (ledger.LedgerUnavailable, KeyError, OSError):
            return uncertain("inspection")
        if result.status == core.CommitStatus.UNRESOLVED:
            return {**current, "commitStatus": result.status.value}
        return current

    def recover(self, operationId):
        operation = self.coordinator.inspect()["operations"].get(operationId)
        if operation is None:
            raise core.Refused("unknown operation")
        if operation["state"] in core.PENDING:
            self.coordinator.recover(operationId)
        return self.report(self.coordinator.inspect()["operations"][operationId])

    def abort(self, operationId, reason):
        """Cancel UNSENT preparation. The operator reason is recorded verbatim in the shared cancel event."""
        if not isinstance(reason, str) or not re.fullmatch(r"[\x20-\x7e]{1,256}", reason) or not reason.strip():
            raise core.Refused("abort reason must be 1-256 printable ASCII characters")
        operation = self.coordinator.inspect()["operations"].get(operationId)
        if operation is None:
            raise core.Refused("unknown operation")
        self.coordinator.cancelPrepared(tokenFrom(operation), f"operator abort: {reason.strip()}", core.digest([operation["attemptId"], "cancel"]))
        return self.report(self.coordinator.inspect()["operations"][operationId])

    def takeover(self, operationId):
        """Move an EXPIRED unsent preparation to a new owner and a newer fence (CAS-ordered against claim).

        Allowed only after the 120 s preparation lease has expired by the trusted clock, at most 3 times, and never for a
        claimed sender. The previous token can no longer claim; the new fence is derived deterministically so a retry of
        the same takeover is idempotent.
        """
        operation = self.coordinator.inspect()["operations"].get(operationId)
        if operation is None:
            raise core.Refused("unknown operation")
        newOwner = core.digest([operationId, "takeover-owner", operation["fence"] + 1])
        result = self.coordinator.takeover(tokenFrom(operation), newOwner, core.digest([operation["attemptId"], "takeover", operation["fence"]]))
        current = self.coordinator.inspect()["operations"][operationId]
        report = self.report(current)
        # Success means the shared record now shows THIS new owner under a newer fence. An unresolved acknowledgement
        # or a transition that changed nothing is reported as such and must not look like a re-owned preparation.
        if result.status == core.CommitStatus.UNRESOLVED:
            return {**report, "commitStatus": "unresolved"}
        if current["ownerId"] != newOwner or current["fence"] <= operation["fence"]:
            return {**report, "commitStatus": "not-taken-over"}
        return report


def makeExecutor(root: Path, *, http=None, clock=None, store=None, snapshot=None) -> Executor:
    """Explicit factory. Missing binding refuses BEFORE auth/network/store access.

    Injection parameters are trusted test/application seams, not CLI flags or
    receipts. Normal construction always uses the canonical GitRef transport.
    """
    try:
        policy = StewardPolicy.load(root)
    except (PolicyError, OSError):
        raise core.CoordinationError("committed authority/configuration source unavailable") from None
    binding = policy.pr_maintenance.writeCoordination
    if policy.pr_maintenance_error or binding is None:
        raise core.CoordinationError("writeCoordination unconfigured; separately verified provisioning/clock contract required")
    # Current rollout scope is GitHub only. Never send a GitHub credential to
    # a host chosen by an unverified local config (including enterprise aliases).
    if binding.forgeHost != "github.com":
        raise core.CoordinationError("unsupported credential origin/repository scope")
    try:
        for relative in gate.AUTHORITY_FILES:
            if proofs.blob(root, "HEAD", relative) != (root / relative).read_bytes():
                raise core.CoordinationError("uncommitted authority cannot select a credential route")
    except OSError:
        raise core.CoordinationError("committed authority files unavailable") from None
    if http is None:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            try:
                result = subprocess.run(["gh", "auth", "token", "--hostname", binding.forgeHost], capture_output=True, timeout=20, check=False)
            except (OSError, subprocess.TimeoutExpired):
                raise core.CoordinationError("in-memory forge authentication unavailable") from None
            if result.returncode:
                raise core.CoordinationError("in-memory forge authentication unavailable")
            token = result.stdout.decode().strip()
            if not token:
                raise core.CoordinationError("in-memory forge authentication unavailable")
        apiHost = "api.github.com" if binding.forgeHost == "github.com" else binding.forgeHost
        http = HttpsTransport(f"https://{apiHost}" + ("" if binding.forgeHost == "github.com" else "/api/v3"), token)
    services = ProductionServices(root, binding, http, clock or BoundedClock(dict(binding.clock)), snapshot)
    namespace = services.namespace
    coordinator = core.PrWriteCoordinator(store or ledger.GitRefLedgerStore(root, ref=core.REF),
                                         core.Binding(namespace, binding.genesis, binding.historyPin, binding.canonicalUrl), services)
    return Executor(coordinator)
