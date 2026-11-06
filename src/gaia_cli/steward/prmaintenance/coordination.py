"""Dormant, single-slot Routine 19 critical-write protocol (not execution authority).

Only a pinned, append-only GitRefLedgerStore is supported. Administrators must
separately provision/protect the canonical ref and retire bypassing writers.
Genesis/history pins and immutable forge identity come from trusted deployment
configuration, never from the fetched document. A cold client cannot detect a
server rollback to an otherwise valid ancestor of its configured history pin;
no-delete/no-reset server protection is a required assumption, not a CAS feature.

Services is a TRUSTED application boundary, not a caller receipt interface. No
production clock, forge adapter, policy loader or proof verifier is supplied by
this module. In particular this core does not establish later HTTP capture,
live authorization, branch protection or kill-switch correctness. Ordinary
sensors must not instantiate/use this coordinator.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol

from gaia_cli.steward import ledger

REF = "steward/pr-write-coordination-v1"
KEY = "routine19CriticalWritesV1"
SCHEMA = "steward-pr-writes-v1"
MAX_OPERATIONS = 128
MAX_EVENTS_PER_OPERATION = 12
MAX_HISTORY = MAX_OPERATIONS * MAX_EVENTS_PER_OPERATION + 1
MAX_BYTES = 512 * 1024  # historical boundary-test profile; runtime uses ResourceProfile
# Full exact source bindings (not fragments/digests); this is a raw UTF-8
# per-source bound. JSON escaping counts against the selected resource ceiling.
MAX_SOURCE_BYTES = 64 * 1024
OUTCOME_HEADROOM = 16 * 1024


@dataclass(frozen=True)
class ResourceProfile:
    """Finite retained-full-record budget, never a quota or authority setting.

    Production uses 8 MiB (128 current full proofs fit); focused historical
    boundary fixtures explicitly select 512 KiB. A smaller transport limit wins.
    No pruning or widening past the accepted transport default is permitted.
    """

    byteLimit: int = 8 * 1024 * 1024

    def validate(self) -> None:
        integer(self.byteLimit, 1024, 8 * 1024 * 1024)


PREPARATION_SECONDS = 120
HOUR_SECONDS = 3600
MAX_CLOCK_WIDTH = 30
MAX_INTEGER = 2**53 - 1
PREPARED = {"reserved", "intent"}
PENDING = {"possibly-sent", "unknown", "quarantined"}
TERMINAL = {"completed-effect", "completed-no-effect", "observed-terminal", "canceled-unsent", "canceled-after-claim"}


class CoordinationError(ledger.LedgerUnavailable):
    """Fail closed; never initialize, refund or grant on this error."""


class Refused(CoordinationError):
    """A valid protocol state does not permit the requested transition."""


class CapacityRefused(Refused):
    """A valid transition cannot be persisted within the bounded record size."""


class NotSent(CoordinationError):
    """Raised ONLY by the trusted mutation adapter when it can PROVE nothing was sent.

    Qualifying proof: the adapter's request was never written to any socket (entry refused, live re-check refused,
    or the connection failed before the first request byte). It is never raised once a byte may have been written.
    The coordinator answers it with ``canceled-after-claim``: the slot is released but the attempt and its charge
    stay counted and the logical operation stays spent. It is never a refund and never a replay right.
    """


class CompletionInvalid(CoordinationError):
    """The sole response or its evidence did not match the invocation/proof."""


class CompletionUnavailable(CoordinationError):
    """The sole response could not be authenticated as a definite outcome."""


class InvocationUncertain(CoordinationError):
    """The sole adapter was entered; no definite outcome can be reported.

    ``cause`` is a bounded, sanitized classification of what failed after
    adapter entry. It records why the protocol cannot settle; it never asserts
    whether the forge acted, never retires or refunds the sender and never
    authorizes a replay or a synthetic settlement. The underlying exception is
    retained as ``__cause__`` for in-process diagnosis and is never published.
    """

    CAUSES = ("capacity", "completion-failed", "persistence", "transport")

    def __init__(self, cause: str):
        if cause not in self.CAUSES:
            raise CoordinationError("invalid post-entry uncertainty cause")
        self.cause = cause
        super().__init__("sole invocation outcome unavailable")


class CommitStatus(str, Enum):
    NEW = "newly-committed"
    ALREADY = "already-applied"
    UNRESOLVED = "unresolved"


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise CoordinationError("invalid finite protocol JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def exact(value: Any, keys: set[str]) -> None:
    if type(value) is not dict or set(value) != keys:
        raise CoordinationError("unsupported/malformed protocol fields")


def text(value: Any, maximum: int = 256, *, empty: bool = False) -> None:
    if type(value) is not str or (not value and not empty) or len(value.encode("utf-8")) > maximum:
        raise CoordinationError("invalid bounded text")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise CoordinationError("invalid control character")


def integer(value: Any, minimum: int = 0, maximum: int = MAX_INTEGER) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise CoordinationError("invalid bounded integer")


def sha(value: Any, *, git: bool = False) -> None:
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{40}" if git else r"[0-9a-f]{64}", value):
        raise CoordinationError("invalid full digest")


@dataclass(frozen=True)
class Namespace:
    forgeHost: str
    repositoryId: str
    repositoryName: str
    epoch: str
    protocol: str = SCHEMA

    def validate(self) -> None:
        for value in asdict(self).values():
            text(value)
        if not re.fullmatch(r"[a-z0-9.-]+", self.forgeHost):
            raise CoordinationError("invalid forge host")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repositoryName):
            raise CoordinationError("invalid repository name")
        if self.protocol != SCHEMA or not re.fullmatch(r"[0-9a-f]{32}", self.epoch):
            raise CoordinationError("unsupported protocol/epoch")


@dataclass(frozen=True)
class Binding:
    namespace: Namespace
    genesis: str
    historyPin: str
    canonicalUrl: str


@dataclass(frozen=True)
class TimeBounds:
    lower: int
    upper: int
    source: str

    def validate(self) -> None:
        integer(self.lower)
        integer(self.upper)
        text(self.source, 128)
        if not self.lower <= self.upper <= self.lower + MAX_CLOCK_WIDTH:
            raise CoordinationError("invalid clock uncertainty bounds")


@dataclass(frozen=True)
class Limits:
    mergesPerRun: int = 2
    closuresPerRun: int = 2
    writesPerHour: int = 10

    def validate(self) -> None:
        integer(self.mergesPerRun, 0, 2)
        integer(self.closuresPerRun, 0, 2)
        integer(self.writesPerHour, 0, 10)


@dataclass(frozen=True)
class Token:
    operationId: str
    attemptId: str
    ownerId: str
    fence: int


@dataclass(frozen=True)
class Result:
    status: CommitStatus
    operationId: str
    token: Token | None = None
    state: str | None = None
    operation: dict | None = None  # copy of the operation exactly as folded from the committed events


class Services(Protocol):
    """Trusted injected implementations; no production implementations yet.

    clock MUST return fresh authoritative current bounds, fail on missing/stale
    or cached samples, and account for source skew, precision, network delay,
    freshness and monotonic elapsed time. Date from arbitrary HTTPS responses,
    host wall time and Git author time do NOT satisfy this contract themselves.
    Core checks finite width and durable non-regression as additional guards.

    limits/authorize MUST read designated CURRENT authoritative sources, bind
    the remote's immutable forge/repository identity and check genuine durable
    proof, policy and authority bytes; caller digests are insufficient. Future
    executor additionally owns final live checks and all existing kill switches.

    invoke is the configured, non-retrying sole mutation adapter. Concrete
    adapters must consume _consumeAdapter at entry (it returns the committed
    claim, so no ledger read sits between claim and send): persisted claims must
    not make their publicly callable Services methods into bearer authorizations.
    An adapter that can prove no request byte reached a socket raises NotSent;
    any other failure is post-entry uncertainty and is never cancelled.
    completion is called ONLY with its actual returned value, after that single invocation has
    finished. It must authenticate that response and independently check exact
    outcome bindings. observation independently checks fresh forge evidence;
    only a matching irreversible merge can retire an unknown sender. These
    trusted hooks are not intended as an API for untrusted plugins/callers.
    """

    def clock(self) -> TimeBounds: ...
    def limits(self) -> Limits: ...
    def authorize(self, namespace: Namespace, subject: dict, proof: dict) -> None: ...
    def invoke(self, request: dict, invocationId: str) -> Any: ...
    def completion(self, operation: dict, invocationId: str, response: Any) -> dict: ...
    def observation(self, operation: dict) -> dict | None: ...


def validateSubject(subject: dict) -> None:
    exact(subject, {"number", "prId", "action", "headSha", "baseRef", "baseSha", "producerId",
                    "reason", "replacement"})
    integer(subject["number"], 1)
    for key in ("prId", "baseRef", "producerId"):
        text(subject[key])
    for key in ("headSha", "baseSha"):
        sha(subject[key], git=True)
    text(subject["reason"], 2048, empty=True)
    if subject["action"] not in {"merge", "close"}:
        raise CoordinationError("unsupported critical action")
    if subject["action"] == "close" and not subject["reason"]:
        raise CoordinationError("closure requires durable reason")
    replacement = subject["replacement"]
    if replacement is not None:
        exact(replacement, {"repositoryId", "prId", "number", "headSha"})
        text(replacement["repositoryId"])
        text(replacement["prId"])
        integer(replacement["number"], 1)
        sha(replacement["headSha"], git=True)


def validateProof(subject: dict, proof: dict) -> None:
    exact(proof, {"policy", "producerRegistry", "authority", "verification", "justification"})
    for key in ("policy", "producerRegistry", "authority"):
        text(proof[key], MAX_SOURCE_BYTES)
    text(proof["justification"], 2048)
    verification = proof["verification"]
    exact(verification, {"builder", "verifier", "result", "headSha", "baseSha", "source", "detail"})
    for key in ("builder", "verifier", "source"):
        text(verification[key])
    text(verification["detail"], 2048)
    if (verification["builder"] == verification["verifier"] or verification["result"] != "PASS"
            or verification["headSha"] != subject["headSha"]
            or verification["baseSha"] != subject["baseSha"]):
        raise CoordinationError("independent exact-subject verification required")


def logicalId(namespace: Namespace, subject: dict) -> str:
    namespace.validate()
    validateSubject(subject)
    return digest({"namespace": asdict(namespace), "subject": subject})


def exactRequest(namespace: Namespace, subject: dict) -> dict:
    return {
        "method": "PUT" if subject["action"] == "merge" else "PATCH",
        "path": f"/repos/{namespace.repositoryName}/pulls/{subject['number']}"
                + ("/merge" if subject["action"] == "merge" else ""),
        "body": {"sha": subject["headSha"], "merge_method": "merge"}
                if subject["action"] == "merge" else {"state": "closed"},
    }


def validateToken(value: dict) -> Token:
    exact(value, {"operationId", "attemptId", "ownerId", "fence"})
    sha(value["operationId"])
    sha(value["attemptId"])
    text(value["ownerId"], 128)
    integer(value["fence"], 1)
    return Token(**value)


def tokenFor(operation: dict) -> Token:
    return Token(**{key: operation[key] for key in ("operationId", "attemptId", "ownerId", "fence")})


def validateEvidence(evidence: dict, operation: dict, *, observed: bool) -> None:
    exact(evidence, {"kind", "operationId", "attemptId", "requestDigest", "headSha", "invocationId",
                     "source", "detail", "observedState"})
    for key in ("operationId", "attemptId", "requestDigest", "invocationId"):
        sha(evidence[key])
        if evidence[key] != operation[key]:
            raise CoordinationError("evidence does not bind the exact invocation")
    if evidence["headSha"] != operation["subject"]["headSha"]:
        raise CoordinationError("evidence head mismatch")
    text(evidence["source"], 256)
    text(evidence["detail"], 2048)
    if observed:
        if (evidence["kind"] != "observed-terminal" or operation["subject"]["action"] != "merge"
                or evidence["observedState"] != "merged"):
            raise CoordinationError("only independently checked matching absorbing merge retires unknown sender")
    elif evidence["kind"] == "completed-no-effect":
        if evidence["observedState"] != "rejected":
            raise CoordinationError("no-effect completion needs a definite rejection")
    elif evidence["kind"] == "completed-effect":
        states = {"merged"} if operation["subject"]["action"] == "merge" else {"closed", "reopened"}
        if evidence["observedState"] not in states:
            raise CoordinationError("completion outcome/action mismatch")
    else:
        raise CoordinationError("unsupported completion evidence")


def initialState() -> dict:
    return {"operations": {}, "activeOperationId": None, "nextFence": 1,
            "limits": asdict(Limits()), "clock": None}


def actionHourly(state: dict, now: TimeBounds, action: str) -> int:
    """Charges of one action inside the trailing hour, across ALL run identifiers."""
    count = 0
    for operation in state["operations"].values():
        if operation["state"] == "canceled-unsent" or operation["subject"]["action"] != action:
            continue
        upper = operation["completionUpper"]
        if upper is None or now.lower <= upper + HOUR_SECONDS:
            count += 1
    return count


def usage(state: dict, now: TimeBounds, runId: str, action: str) -> tuple[int, int]:
    hourly = 0
    inRun = 0
    for operation in state["operations"].values():
        if operation["state"] == "canceled-unsent":
            continue
        if operation["runId"] == runId and operation["subject"]["action"] == action:
            inRun += 1
        upper = operation["completionUpper"]
        if upper is None or now.lower <= upper + HOUR_SECONDS:
            hourly += 1
    return inRun, hourly


def checkCapacity(state: dict, now: TimeBounds, runId: str, action: str, *, claiming: bool) -> None:
    inRun, hourly = usage(state, now, runId, action)
    cap = state["limits"]["mergesPerRun" if action == "merge" else "closuresPerRun"]
    increment = 0 if claiming else 1
    # The per-run ceiling is also a per-action trailing-hour ceiling, so a fresh run identifier cannot evade it.
    if (inRun + increment > cap or hourly + increment > state["limits"]["writesPerHour"]
            or actionHourly(state, now, action) + increment > cap):
        raise Refused("critical write run/hour ceiling exhausted or lowered")


def applyEvent(state: dict, event: dict, namespace: Namespace) -> None:
    """Pure, strict replay; never invokes services or emits a grant."""
    exact(event, {"id", "kind", "operationId", "args", "time", "limits"})
    text(event["id"], 128)
    sha(event["operationId"])
    exact(event["time"], {"lower", "upper", "source"})
    now = TimeBounds(**event["time"])
    now.validate()
    previous = state["clock"]
    if previous and (now.lower < previous["lower"] or now.upper < previous["upper"]):
        raise CoordinationError("regressing/future-inconsistent authoritative clock")
    state["clock"] = asdict(now)
    kind = event["kind"]
    args = event["args"]
    if kind in {"reserve", "claim"}:
        exact(event["limits"], set(asdict(Limits())))
        Limits(**event["limits"]).validate()
        state["limits"] = {key: min(value, event["limits"][key])
                           for key, value in state["limits"].items()}
    elif event["limits"] is not None:
        raise CoordinationError("unexpected limits")
    operationId = event["operationId"]
    operations = state["operations"]
    if kind == "reserve":
        exact(args, {"subject", "proof", "runId", "ownerId"})
        validateSubject(args["subject"])
        validateProof(args["subject"], args["proof"])
        text(args["runId"], 128)
        text(args["ownerId"], 128)
        if logicalId(namespace, args["subject"]) != operationId:
            raise CoordinationError("logical operation identity mismatch")
        if operationId in operations or state["activeOperationId"] is not None:
            raise Refused("logical replay or global critical slot occupied")
        if len(operations) >= MAX_OPERATIONS:
            raise Refused("full-record anti-replay capacity exhausted; no pruning")
        checkCapacity(state, now, args["runId"], args["subject"]["action"], claiming=False)
        operations[operationId] = {
            "operationId": operationId, **copy.deepcopy(args), "proofDigest": digest(args["proof"]),
            "attemptId": digest([operationId, event["id"]]), "fence": state["nextFence"],
            "leaseUpper": now.upper + PREPARATION_SECONDS, "state": "reserved", "takeovers": 0,
            "request": None, "requestDigest": None, "claimId": None, "invocationId": None,
            "evidence": None, "completionUpper": None,
        }
        state["activeOperationId"] = operationId
        state["nextFence"] += 1
        return
    if operationId not in operations:
        raise Refused("unknown operation")
    operation = operations[operationId]
    if kind in {"intent", "takeover", "cancel", "claim", "unknown", "cancel-claimed", "complete"}:
        if type(args) is not dict or "token" not in args or validateToken(args["token"]) != tokenFor(operation):
            raise Refused("stale ownership/fence/attempt")
    if kind == "intent":
        exact(args, {"token", "request"})
        if operation["state"] != "reserved" or args["request"] != exactRequest(namespace, operation["subject"]):
            raise Refused("intent requires reserved owner and exact request")
        operation.update(state="intent", request=copy.deepcopy(args["request"]), requestDigest=digest(args["request"]))
    elif kind == "takeover":
        exact(args, {"token", "newOwnerId"})
        text(args["newOwnerId"], 128)
        if (operation["state"] not in PREPARED or now.lower <= operation["leaseUpper"]
                or operation["takeovers"] >= 3 or args["newOwnerId"] == operation["ownerId"]):
            raise Refused("only expired unsent preparation can transfer (bounded)")
        operation.update(ownerId=args["newOwnerId"], fence=state["nextFence"],
                         leaseUpper=now.upper + PREPARATION_SECONDS, takeovers=operation["takeovers"] + 1)
        state["nextFence"] += 1
    elif kind == "cancel":
        exact(args, {"token", "reason"})
        text(args["reason"], 1024)
        if operation["state"] not in PREPARED:
            raise Refused("claimed sender cannot be canceled/refunded")
        operation["state"] = "canceled-unsent"
        state["activeOperationId"] = None
    elif kind == "claim":
        exact(args, {"token"})
        if operation["state"] != "intent" or now.upper > operation["leaseUpper"]:
            raise Refused("send requires live preparation and intent")
        checkCapacity(state, now, operation["runId"], operation["subject"]["action"], claiming=True)
        operation.update(state="possibly-sent", claimId=event["id"],
                         invocationId=digest([operation["attemptId"], event["id"], operation["requestDigest"]]))
    elif kind == "unknown":
        exact(args, {"token", "detail"})
        text(args["detail"], 1024)
        if operation["state"] != "possibly-sent":
            raise Refused("unknown transition requires outstanding claim")
        operation["state"] = "unknown"
    elif kind == "cancel-claimed":
        exact(args, {"token", "detail"})
        text(args["detail"], 1024)
        if operation["state"] != "possibly-sent":
            raise Refused("claim cancellation requires the just-committed, unsettled claim")
        # Slot released; the attempt, run charge and hour charge are KEPT (completionUpper starts the hour window).
        operation.update(state="canceled-after-claim", completionUpper=now.upper)
        state["activeOperationId"] = None
    elif kind == "quarantine":
        exact(args, {"reason"})
        if args["reason"] != "inconclusive-reconciliation" or operation["state"] not in {"possibly-sent", "unknown"}:
            raise Refused("quarantine requires outstanding sender")
        operation["state"] = "quarantined"
    elif kind in {"complete", "merge-terminal"}:
        exact(args, {"token", "evidence"} if kind == "complete" else {"evidence"})
        if operation["state"] not in PENDING:
            raise Refused("completion cannot replay or undo a terminal record")
        validateEvidence(args["evidence"], operation, observed=kind == "merge-terminal")
        operation.update(state=args["evidence"]["kind"], evidence=copy.deepcopy(args["evidence"]),
                         completionUpper=now.upper)
        state["activeOperationId"] = None
    else:
        raise CoordinationError("unsupported transition")


def fold(events: list, namespace: Namespace) -> dict:
    if type(events) is not list or len(events) >= MAX_HISTORY:
        raise CoordinationError("bounded event history exhausted/malformed")
    state = initialState()
    ids: set[str] = set()
    counts: dict[str, int] = {}
    for event in events:
        if type(event) is not dict:
            raise CoordinationError("malformed event")
        eventId = event.get("id")
        text(eventId, 128)
        if eventId in ids:
            raise CoordinationError("duplicate transition id")
        ids.add(eventId)
        applyEvent(state, event, namespace)
        operationId = event["operationId"]
        counts[operationId] = counts.get(operationId, 0) + 1
        if counts[operationId] > MAX_EVENTS_PER_OPERATION:
            raise CoordinationError("operation event bound exceeded")
    return state


class _Grant:
    """Never returned/persisted; instance registry, thread and PID guarded."""

    __slots__ = ("pid", "thread", "token", "requestDigest", "invocationId", "operation")

    def __init__(self, operation: dict):
        self.operation = copy.deepcopy(operation)
        self.pid = os.getpid()
        self.thread = threading.get_ident()
        self.token = tokenFor(operation)
        self.requestDigest = operation["requestDigest"]
        self.invocationId = operation["invocationId"]

    def __copy__(self):
        raise TypeError("send grants cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("send grants cannot be copied")

    def __reduce__(self):
        raise TypeError("send grants cannot be serialized")


class PrWriteCoordinator:
    def __init__(self, store: ledger.GitRefLedgerStore, binding: Binding, services: Services,
                 resources: ResourceProfile = ResourceProfile()):
        if not isinstance(store, ledger.GitRefLedgerStore) or store.ref != REF or store.remote != "origin":
            raise CoordinationError("canonical origin Git ref required; no local fallback")
        binding.namespace.validate()
        sha(binding.genesis, git=True)
        sha(binding.historyPin, git=True)
        text(binding.canonicalUrl, 2048)
        if store.resolveUrls() != (binding.canonicalUrl, binding.canonicalUrl):
            raise CoordinationError("fetch/push destinations differ from trusted canonical binding")
        resources.validate()
        self.resources = resources
        self.store = store
        self.binding = binding
        self.services = services
        self.lastTip: str | None = None
        self.historyGuard = threading.Lock()  # protects cache only; Git CAS is cross-host authority
        self.verified: dict[str, str] = {}  # commit -> immutable event-prefix digest
        self.pid = os.getpid()
        self.grantGuard = threading.Lock()
        self.grants: dict[int, _Grant] = {}
        self.adapterEntries: dict[str, _Grant] = {}  # live control flow only, never persisted

    def byteLimit(self) -> int:
        self.resources.validate()
        return min(self.resources.byteLimit, ledger.ledgerByteLimit())

    def _payload(self, document: dict) -> dict:
        exact(document, {"schemaVersion", "generation", "runs", "leases", "work", "lane", "operations"})
        if (document["schemaVersion"] != ledger.LEDGER_SCHEMA or document["runs"] != {}
                or document["leases"] != {} or document["work"] != {} or document["lane"] is not None):
            raise CoordinationError("unrelated/legacy ledger cannot coordinate critical writes")
        exact(document["operations"], {KEY})
        payload = document["operations"][KEY]
        exact(payload, {"schemaVersion", "namespace", "events"})
        if payload["schemaVersion"] != SCHEMA or payload["namespace"] != asdict(self.binding.namespace):
            raise CoordinationError("unsupported schema or namespace/epoch/immutable identity mismatch")
        return payload

    def _readCommit(self, commit: str) -> dict:
        spec = f"{commit}:{ledger.LEDGER_FILENAME}"
        if int(self.store.plumb(["cat-file", "-s", spec])) > self.byteLimit():
            raise CoordinationError("coordination payload over byte bound")
        raw = self.store.plumb(["cat-file", "-p", spec]).encode("utf-8")
        return ledger.deserialize(raw)

    def _load(self) -> tuple[dict, str, dict]:
        with self.historyGuard:
            document, tip = self.store.load()
            if tip is None:
                raise CoordinationError("missing provisioned coordination ref/genesis")
            rows = self.store.plumb(["rev-list", "--reverse", "--parents", f"--max-count={MAX_HISTORY + 1}", tip]).splitlines()
            chain = [row.split() for row in rows]
            commits = [row[0] for row in chain]
            if (not chain or len(chain) > MAX_HISTORY or chain[0] != [self.binding.genesis]
                    or self.binding.historyPin not in commits
                    or (self.lastTip is not None and self.lastTip not in commits)):
                raise CoordinationError("missing pinned genesis/history or reset/non-descendant canonical tip")
            tipEvents = self._payload(document)["events"]
            state = fold(tipEvents, self.binding.namespace)
            if document["generation"] != len(chain) or len(tipEvents) != len(chain) - 1:
                raise CoordinationError("inconsistent generation or missing transition history")
            prefixes = [digest([])]
            for event in tipEvents:
                prefixes.append(digest([prefixes[-1], event]))
            previous = None
            for index, row in enumerate(chain):
                commit = row[0]
                if row[1:] != ([] if previous is None else [previous]):
                    raise CoordinationError("coordination history must be an unbroken single-parent chain")
                if commit in self.verified and self.verified[commit] != prefixes[index]:
                    raise CoordinationError("cached commit disagrees with canonical transition history")
                if commit not in self.verified or commit == tip:
                    current = document if commit == tip else self._readCommit(commit)
                    payload = self._payload(current)
                    if current["generation"] != index + 1 or payload["events"] != tipEvents[:index]:
                        raise CoordinationError("inconsistent generation or rewritten transition history")
                    self.verified[commit] = prefixes[index]
                previous = commit
            if len(ledger.serialize(document)) > self.byteLimit():
                raise CoordinationError("coordination document over byte bound")
            self.lastTip = tip
            return document, tip, state

    def inspect(self) -> dict:
        """Fresh canonical reachable history, never local receipt authority."""
        return copy.deepcopy(self._load()[2])

    def _result(self, status: CommitStatus, operationId: str, state: dict | None) -> Result:
        operation = None if state is None else state["operations"].get(operationId)
        return Result(status, operationId, tokenFor(operation) if operation else None,
                      operation["state"] if operation else None, copy.deepcopy(operation) if operation else None)

    def _transition(self, kind: str, operationId: str, args: dict, transitionId: str) -> Result:
        text(transitionId, 128)
        command = {"id": transitionId, "kind": kind, "operationId": operationId, "args": copy.deepcopy(args)}
        for _ in range(8):
            document, tip, state = self._load()
            events = self._payload(document)["events"]
            existing = next((event for event in events if event["id"] == transitionId), None)
            if existing is not None:
                if {key: existing[key] for key in command} != command:
                    raise Refused("transition id reused for a different immutable command")
                return self._result(CommitStatus.ALREADY, operationId, state)
            now = self.services.clock()
            if type(now) is not TimeBounds:
                raise CoordinationError("trusted clock provider unavailable/malformed")
            now.validate()
            limits = self.services.limits() if kind in {"reserve", "claim"} else None
            if limits is not None:
                if type(limits) is not Limits:
                    raise CoordinationError("trusted policy limits unavailable/malformed")
                limits.validate()
            event = {**command, "time": asdict(now), "limits": asdict(limits) if limits is not None else None}
            candidate = copy.deepcopy(document)
            self._payload(candidate)["events"].append(event)
            nextState = fold(self._payload(candidate)["events"], self.binding.namespace)
            # CAS persists nextGeneration(candidate), not candidate. Measure the
            # exact same bytes without incrementing the document passed to CAS.
            persisted = ledger.nextGeneration(candidate)
            size = len(ledger.serialize(persisted))
            # Reserve event/outcome space AND all possible future decimal-width
            # growth up to the bounded history generation. Source JSON escaping
            # is already included in size; no raw-text size approximation.
            generationHeadroom = max(0, len(str(MAX_HISTORY)) - len(str(persisted["generation"])))
            limit = self.byteLimit()
            if size > limit or (kind == "reserve" and size + OUTCOME_HEADROOM + generationHeadroom > limit):
                raise CapacityRefused("critical record capacity exhausted; settlement headroom retained")
            try:
                self.store.compare_and_swap(tip, candidate, f"critical {kind} {transitionId}")
            except ledger.LedgerConflict:
                continue  # discard all decisions/results from failed snapshot
            except ledger.LedgerUnavailable:
                # Never issue a grant after an ambiguous push, even if our claim is visible.
                try:
                    reloadedDocument, _, reloaded = self._load()
                    canonicalEvents = self._payload(reloadedDocument)["events"]
                    found = next((item for item in canonicalEvents if item["id"] == transitionId), None)
                    if found is not None:
                        if {key: found[key] for key in command} != command:
                            raise Refused("ambiguous transition id collision")
                        return self._result(CommitStatus.ALREADY, operationId, reloaded)
                except ledger.LedgerUnavailable:
                    pass
                return self._result(CommitStatus.UNRESOLVED, operationId, None)
            return self._result(CommitStatus.NEW, operationId, nextState)
        return self._result(CommitStatus.UNRESOLVED, operationId, None)

    def reserve(self, subject: dict, proof: dict, runId: str, ownerId: str, transitionId: str) -> Result:
        subject, proof = copy.deepcopy(subject), copy.deepcopy(proof)
        operationId = logicalId(self.binding.namespace, subject)
        validateProof(subject, proof)
        self.services.authorize(self.binding.namespace, copy.deepcopy(subject), copy.deepcopy(proof))
        return self._transition("reserve", operationId,
                                {"subject": subject, "proof": proof, "runId": runId, "ownerId": ownerId}, transitionId)

    def recordIntent(self, token: Token, request: dict, transitionId: str) -> Result:
        return self._transition("intent", token.operationId, {"token": asdict(token), "request": request}, transitionId)

    def takeover(self, token: Token, newOwnerId: str, transitionId: str) -> Result:
        return self._transition("takeover", token.operationId, {"token": asdict(token), "newOwnerId": newOwnerId}, transitionId)

    def cancelPrepared(self, token: Token, reason: str, transitionId: str) -> Result:
        return self._transition("cancel", token.operationId, {"token": asdict(token), "reason": reason}, transitionId)

    def _consume(self, grant: _Grant, operation: dict) -> None:
        # Check PID before acquiring an inherited lock (fork may inherit it held).
        if os.getpid() != self.pid or grant.pid != self.pid or grant.thread != threading.get_ident():
            raise Refused("grant is process/thread/control-flow local")
        with self.grantGuard:
            if (type(grant) is not _Grant or self.grants.pop(id(grant), None) is not grant
                    or grant.token != tokenFor(operation) or grant.requestDigest != operation["requestDigest"]
                    or grant.invocationId != operation["invocationId"]):
                raise Refused("grant is not authentic, bound, live and unconsumed")

    def _consumeAdapter(self, service: Services, request: dict, invocationId: str) -> dict:
        """Private one-shot entry check for concrete mutation adapters.

        A persisted claim plus a public Services method is NOT authorization.
        Only the still-live core call can register this exact consumed grant;
        copied services, other threads, fork/restart and reentry cannot reuse it.
        """
        if os.getpid() != self.pid:
            raise Refused("forked process has no adapter entry")
        with self.grantGuard:
            grant = self.adapterEntries.get(invocationId)
            if (type(grant) is not _Grant or service is not self.services or grant.pid != self.pid
                    or grant.thread != threading.get_ident() or grant.invocationId != invocationId
                    or grant.requestDigest != digest(request)):
                raise Refused("no authentic live one-shot adapter entry")
            del self.adapterEntries[invocationId]  # burn BEFORE live checks/network/callbacks
            return copy.deepcopy(grant.operation)  # the committed claim: no ledger read between claim and send

    def _cancelClaimed(self, token: Token, transitionId: str, detail: str) -> Result:
        """Record a PROVEN-unsent claim as canceled-after-claim: slot released, attempt and charge kept."""
        try:
            return self._transition("cancel-claimed", token.operationId, {"token": asdict(token), "detail": detail},
                                    digest([transitionId, "cancel-claimed"]))
        except CapacityRefused as exc:
            raise InvocationUncertain("capacity") from exc
        except Exception as exc:
            raise InvocationUncertain("persistence") from exc

    def invoke(self, token: Token, transitionId: str) -> Result:
        """Claim and consume a non-exported one-shot grant BEFORE adapter entry.

        A replay/restart/copy can inspect a persisted claim but cannot obtain a
        grant. Ambiguous claim acknowledgements are deliberately quarantinable,
        not recoverable send rights. No arbitrary caller response can settle.

        The claim result is built from the committed CAS itself, so no ledger
        read sits between the claim and the adapter. A failure that PROVES
        nothing was sent (the adapter was never entered, or it raised NotSent)
        settles as canceled-after-claim: the slot is released but the attempt
        and its charge stay counted. Everything after possible adapter entry
        stays unknown/uncertain and is never cancelled, refunded or replayed.
        """
        if os.getpid() != self.pid:
            raise Refused("forked coordinator cannot invoke")
        operation = self.inspect()["operations"].get(token.operationId)
        if operation is None:
            raise Refused("unknown operation")
        self.services.authorize(self.binding.namespace, copy.deepcopy(operation["subject"]), copy.deepcopy(operation["proof"]))
        result = self._transition("claim", token.operationId, {"token": asdict(token)}, transitionId)
        if result.status != CommitStatus.NEW:
            return result
        operation = result.operation
        invocationId = None
        entered = False
        try:
            if (operation is None or operation["claimId"] != transitionId or tokenFor(operation) != token
                    or operation["state"] != "possibly-sent"):
                raise Refused("claim/control-flow binding changed")
            invocationId = operation["invocationId"]
            grant = _Grant(operation)
            with self.grantGuard:
                self.grants[id(grant)] = grant
            self._consume(grant, operation)
            with self.grantGuard:
                self.adapterEntries[invocationId] = grant
            entered = True  # from here the adapter may have written; only NotSent can prove otherwise
            response = self.services.invoke(copy.deepcopy(operation["request"]), invocationId)
        except NotSent:
            return self._cancelClaimed(token, transitionId, "adapter proved no request byte was sent")
        except Exception:
            if not entered:
                return self._cancelClaimed(token, transitionId, "adapter was never entered")
            # Once adapter entry was attempted, no definite outcome can be
            # reported. A failure to even record the unknown transition is also
            # post-entry uncertainty, never a pre-send refusal.
            try:
                return self._transition("unknown", token.operationId,
                                        {"token": asdict(token), "detail": "sole adapter invocation lost/unknown response"},
                                        digest([transitionId, "unknown"]))
            except CapacityRefused as exc:
                raise InvocationUncertain("capacity") from exc
            except Exception as exc:
                raise InvocationUncertain("persistence") from exc
        finally:
            with self.grantGuard:
                if invocationId is not None:
                    self.adapterEntries.pop(invocationId, None)
        # Completion authentication, independent-evidence validation and shared
        # settlement each run only AFTER the sole adapter was entered. Any of
        # them failing proves no safe settlement, never that the forge had no
        # effect, so the cause is retained as a bounded classification.
        try:
            evidence = self.services.completion(copy.deepcopy(operation), invocationId, response)
        except CompletionUnavailable as exc:
            raise InvocationUncertain("transport") from exc
        except Exception as exc:
            raise InvocationUncertain("completion-failed") from exc
        try:
            validateEvidence(evidence, operation, observed=False)
        except Exception as exc:
            raise InvocationUncertain("completion-failed") from exc
        try:
            return self._transition("complete", token.operationId, {"token": asdict(token), "evidence": evidence},
                                    digest([transitionId, "complete"]))
        except CapacityRefused as exc:
            raise InvocationUncertain("capacity") from exc
        except Exception as exc:
            raise InvocationUncertain("persistence") from exc

    def recover(self, operationId: str) -> Result:
        """One bounded observation; repeated inconclusive recovery adds no events.

        A closed/open GET, TTL, lost receipt or local run supersession cannot
        retire a close sender. A trusted authentic completion may still arrive
        through its original live invoke call after quarantine or reopening.
        """
        operation = self.inspect()["operations"].get(operationId)
        if operation is None or operation["state"] not in PENDING:
            raise Refused("no outstanding sender to reconcile")
        evidence = self.services.observation(copy.deepcopy(operation))
        if evidence is not None:
            validateEvidence(evidence, operation, observed=True)
            return self._transition("merge-terminal", operationId, {"evidence": evidence},
                                    digest([operation["attemptId"], "merge-terminal"]))
        if operation["state"] == "quarantined":
            return self._result(CommitStatus.ALREADY, operationId, {"operations": {operationId: operation}})
        return self._transition("quarantine", operationId, {"reason": "inconclusive-reconciliation"},
                                digest([operation["attemptId"], "quarantine"]))
