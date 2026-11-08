"""Non-destructive Steward memory on the ledger's shared Git transport.

Only explicit migration removes phase payloads from terminal runs. All other
fields (notably actions/outcomes, steps, desks, decisions, work and lane) stay
hot. Unknown or unsettled lifecycles are ineligible. The original run AND exact
source ledger bytes are kept indefinitely; the snapshot commit parents the
original ledger commit, retaining its ancestry including pre-migration pruning.

Objects live on immutable, content-addressed root branches. Publication uses
ordinary non-forced pushes, read-back verification, then the existing hot CAS.
A failed CAS can leave harmless, retrievable orphans, never a dangling hot
pointer. No GC, expiry, branch deletion, force-push or global config is used.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Callable

from gaia_cli.steward.ledger import (
    GitRefLedgerStore, LedgerConflict, LedgerUnavailable, formatTime,
    parseTime, serialize, utcNow, validate_ledger, ledgerByteLimit, ARCHIVE_LEDGER_SCHEMA, nextGeneration,
    WORK_STATES,
)

SCHEMA = "steward-archive-v1"
MEMORY = "steward.archive.v1"
POINTER = "_stewardArchive"
PREFIX = "steward/archive/v1"
FILENAME = "payload"
# Every run that fits the supported 64 MiB configured hot ceiling must fit a
# bounded envelope. Pretty source JSON is larger than compact envelope JSON;
# leave 1 MiB for provenance/descriptor overhead.
MAX_SEGMENT_BYTES = 65 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
MAX_INDEX_BYTES = 256 * 1024
MAX_PAGE_ENTRIES = 32
LIMITS = {"run": MAX_SEGMENT_BYTES, "snapshot": MAX_SNAPSHOT_BYTES, "index": MAX_INDEX_BYTES, "anchor": 16 * 1024}
HEX = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def packed(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise LedgerUnavailable(f"archive is not JSON: {exc}") from exc


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(reason: str) -> LedgerUnavailable:
    return LedgerUnavailable(f"Steward archive refused: {reason}")


def descriptor(kind: str, data: bytes) -> dict[str, Any]:
    return {"kind": kind, "sha256": digest(data), "size": len(data)}


def check_descriptor(ref: Any, kind: str | None = None) -> dict[str, Any]:
    if not isinstance(ref, dict) or set(ref) != {"kind", "sha256", "size"}:
        raise fail("invalid object descriptor")
    if not isinstance(ref["kind"], str) or ref["kind"] not in LIMITS or (kind is not None and ref["kind"] != kind):
        raise fail("wrong object kind")
    if not isinstance(ref["sha256"], str) or not HEX.fullmatch(ref["sha256"]):
        raise fail("invalid checksum")
    size = ref["size"]
    if type(size) is not int or not 0 < size <= LIMITS[ref["kind"]]:
        raise fail("object size outside bounded read limit")
    return ref


def decoded(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        if not isinstance(value, dict):
            raise ValueError("not an object")
        return value
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise fail(f"invalid JSON: {exc}") from exc


def validate_object(kind: str, data: bytes) -> dict[str, Any]:
    value = decoded(data)
    if kind == "snapshot":
        return validate_ledger(value)
    if value.get("schemaVersion") != SCHEMA or value.get("kind") != kind:
        raise fail("unknown object schema/kind")
    if kind == "run":
        if not isinstance(value.get("runId"), str) or not isinstance(value.get("run"), dict):
            raise fail("invalid run envelope")
        if value["run"].get("runId") != value["runId"] or POINTER in value["run"]:
            raise fail("run identity mismatch or nested archive")
        check_descriptor(value.get("source"), "snapshot")
        check_descriptor(value.get("sourceAnchor"), "anchor")
        if not isinstance(value.get("sourceCommit"), str) or not COMMIT.fullmatch(value["sourceCommit"]):
            raise fail("invalid source commit")
        if not isinstance(value.get("ledgerRef"), str):
            raise fail("missing source ledger ref")
    elif kind == "anchor":
        check_descriptor(value.get("source"), "snapshot")
        if not isinstance(value.get("sourceCommit"), str) or not COMMIT.fullmatch(value["sourceCommit"]):
            raise fail("invalid anchor source commit")
    elif kind == "index":
        previous = value.get("previous")
        if previous is not None:
            check_descriptor(previous, "index")
        rows = value.get("entries")
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_PAGE_ENTRIES:
            raise fail("index page outside entry bound")
        for row in rows:
            if not isinstance(row, dict) or row.get("event") not in {"archive", "rollback"}:
                raise fail("invalid index event")
            if not isinstance(row.get("runId"), str):
                raise fail("invalid indexed identity")
            check_descriptor(row.get("segment"), "run")
            for key in ("debtIds", "routines"):
                if not isinstance(row.get(key), list) or not all(isinstance(x, str) for x in row[key]):
                    raise fail("invalid index search keys")
            for key in ("at", "startedAt", "finishedAt"):
                try:
                    parseTime(row.get(key))
                except ValueError as exc:
                    raise fail(f"invalid index timestamp {key}") from exc
    return value


class GitArchive:
    """Immutable objects, sharing GitRefLedgerStore's safe subprocess plumbing."""

    def __init__(self, ledger: GitRefLedgerStore):
        if not isinstance(ledger, GitRefLedgerStore) or not ledger.shared:
            raise fail("durable memory requires an explicit shared Git ledger")
        self.ledger = ledger

    def store(self, ref: dict[str, Any]) -> GitRefLedgerStore:
        check_descriptor(ref)
        base = self.ledger
        return GitRefLedgerStore(base.repo_root, base.remote,
                                 f"{PREFIX}/{ref['kind']}/{ref['sha256']}",
                                 localTimeout=base.localTimeout, remoteTimeout=base.remoteTimeout)

    def read(self, ref: dict[str, Any]) -> bytes:
        """Always fetch/read back from transport, not an unverified local cache."""
        store = self.store(ref)
        commit = store.fetchRemote()
        if commit is None:
            raise fail(f"missing {ref['kind']} {ref['sha256']}")
        spec = f"{commit}:{FILENAME}"
        result = store.git(["cat-file", "-p", spec], timeout=store.localTimeout)
        data = result.stdout
        if result.returncode:
            raise fail("archive checksum/readback mismatch")
        if len(data) != ref["size"] or len(data) > LIMITS[ref["kind"]]:
            raise fail("archive byte count mismatch")
        if digest(data) != ref["sha256"]:
            raise fail("archive checksum/readback mismatch")
        validate_object(ref["kind"], data)
        return data

    def publish(self, kind: str, data: bytes, *, parent: str | None = None) -> dict[str, Any]:
        ref = check_descriptor(descriptor(kind, data))
        validate_object(kind, data)
        store = self.store(ref)
        existing = store.fetchRemote()
        if existing is not None:
            if self.read(ref) != data:
                raise fail("content-addressed object collision")
            return ref
        blob = store.plumb(["hash-object", "-w", "--stdin"], stdin=data)
        tree = store.plumb(["mktree"], stdin=f"100644 blob {blob}\t{FILENAME}\n".encode())
        args = ["-c", "commit.gpgsign=false", "commit-tree", tree]
        if parent is not None:
            if not COMMIT.fullmatch(parent):
                raise fail("invalid provenance parent")
            args += ["-p", parent]
        args += ["-m", f"Steward immutable {kind} sha256:{ref['sha256']}"]
        commit = store.plumb(args, identity=True)
        _, url = store.resolveUrls()
        result = store.git(["push", "--no-verify", "--porcelain", store.ephemeralRemote,
                            f"{commit}:refs/heads/{store.ref}"], timeout=store.remoteTimeout,
                           env=store._remoteEnv(url))
        if result.returncode:
            # Concurrent identical publication is fine ONLY after remote readback;
            # any other failure (including an immutable-ref collision) is fatal.
            if store.remoteTip() is None:
                raise fail(f"publication failed: {store.outputText(result).strip()[:300]}")
        if self.read(ref) != data:
            raise fail("publication readback mismatch")
        return ref


def references(run: dict[str, Any]) -> dict[str, list[str]]:
    """Keep reference-bearing values hot, including unknown future ID keys.

    These are search/dedup keys, NOT evidence or claims that work was settled.
    All desks, decisions, actions, work and lane remain verbatim alongside them.
    """
    debts: set[str] = set()
    routines: set[str] = set()
    ids: set[str] = set()
    def visit(value: Any, key: str = "") -> None:
        lowered = key.lower()
        if isinstance(value, dict):
            for name, item in value.items():
                if "debt" in lowered:
                    debts.add(str(name))
                visit(item, name)
        elif isinstance(value, list):
            for item in value:
                visit(item, "routine" if lowered == "routines" else key)
        elif value is not None:
            text = str(value)
            if "debt" in lowered or lowered in {"classa", "classb", "classc", "reportonly", "held", "skippedactive", "issueclosure", "resolvedwork", "freshopendebt", "opendebtids", "resolved"}:
                if isinstance(value, str):
                    debts.add(text)
            # Canonical retro.routines was once a COUNT, later a list of
            # {routine, state, detectors}. Never index a count as a routine ID.
            if lowered == "routine" or (lowered == "routines" and isinstance(value, str)):
                routines.add(text)
            if "id" in lowered or "decision" in lowered or "idempotency" in lowered:
                if isinstance(value, str):
                    ids.add(text)
    visit(run)
    return {"debtIds": sorted(debts), "routines": sorted(routines), "identities": sorted(ids)}


# Eligibility schemas are deliberately narrower than the ledger's JSON schema.
# No catch-all JSON/string walker: every field, map key, array element and scalar
# has a declared meaning. New producer fields require review before migration.
PhaseCheck = Callable[[Any], bool]


def phaseObject(fields: dict[str, PhaseCheck], required: tuple[str, ...] = ()) -> PhaseCheck:
    return lambda value: (
        type(value) is dict and all(name in value for name in required)
        and all(type(name) is str and name in fields and fields[name](item)
                for name, item in value.items())
    )


def phaseList(check: PhaseCheck) -> PhaseCheck:
    return lambda value: type(value) is list and all(check(item) for item in value)


def phaseMap(check: PhaseCheck, keyCheck: PhaseCheck | None = None) -> PhaseCheck:
    # Dynamic keys have a declared ID type, never unchecked filenames or URLs.
    keyCheck = keyCheck or phaseIdentity
    return lambda value: type(value) is dict and all(
        keyCheck(name) and check(item) for name, item in value.items())


def phaseEither(*checks: PhaseCheck) -> PhaseCheck:
    return lambda value: any(check(value) for check in checks)


def phaseEnum(*choices: str) -> PhaseCheck:
    return lambda value: type(value) is str and value in choices


def phaseIdentity(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]+", value) is not None


def phaseDebtIdentity(value: Any) -> bool:
    # Canonical Observation.debt_id, plus legacy simple IDs. Colons are safe
    # only in this typed reference slot, never arbitrary text or unknown keys.
    return phaseIdentity(value) or (type(value) is str and re.fullmatch(
        r"debt:[A-Za-z0-9_-]+:[A-Za-z0-9_-]+:[0-9a-f]{16}", value) is not None)


def phaseText(value: Any) -> bool:
    # Lexical diagnostic only, NOT a portability or file-absence proof. Even
    # "proof" passes this scan and can denote an extensionless artifact. No
    # producer-unconstrained phase field may use it as an eligibility check.
    # Keep the bounded scanner and its exhaustive/large-input regressions.
    if type(value) is not str:
        return False
    # One pass with bounded neighbour checks. An unanchored greedy token
    # followed by a required dot retries every suffix of a dot-free multi-MiB
    # payload (quadratic work). Do not reintroduce a backtracking token scan.
    for index, character in enumerate(value):
        if character in "/\\~:":
            return False
        if character == "." and 0 < index < len(value) - 1:
            if all(neighbour.isalnum() or neighbour in "_.-"
                   for neighbour in (value[index - 1], value[index + 1])):
                return False
    return True


def phaseCount(value: Any) -> bool:
    return type(value) is int and value >= 0


def phaseEmpty(value: Any) -> bool:
    return type(value) is list and not value


def phaseSchemas() -> dict[str, PhaseCheck]:
    """Supported FullRunner typed summaries; ambiguous legacy text stays hot.

    Historical sensor/coverage states are observations, NOT work settlement.
    Nonempty Class C, decisions, results/landings and artifact-bearing detail
    have no portable schema here and remain hot. No referenced file is opened.
    """
    identities = phaseList(phaseIdentity)
    debts = phaseList(phaseDebtIdentity)
    # FullRunner copies sensor/exception/optional-input prose into these slots;
    # it does not constrain it to non-reference text. Reject every value, even
    # empty text/null, rather than infer meaning from filename spelling. Empty
    # collections remain supported; no unknown/uncertain text is normalized.
    ambiguous = lambda value: False
    boolean = lambda value: type(value) is bool
    nothing = lambda value: value is None
    settled = phaseEnum("ok", "done", "completed", "complete", "resolved", "closed",
                        "accepted", "rejected", "cancelled", "superseded", "skipped",
                        "failed", "abandoned", "observed")
    sensorState = phaseEnum("executed", "unknown", "not-evaluated", "partially-covered", "not-run")
    counts = phaseObject({"drift": phaseCount, "healthy": phaseCount})
    notEvaluated = phaseList(phaseObject({
        "sensor": phaseIdentity, "reason": ambiguous, "inputAbsent": boolean,
    }, ("sensor", "reason")))
    partial = phaseList(phaseObject({
        "sensor": phaseIdentity, "skippedCount": phaseCount, "reasons": phaseList(ambiguous),
    }, ("sensor", "skippedCount", "reasons")))
    observation = {
        "status": settled, "scanReceiptId": phaseIdentity,
        "observations": phaseCount, "openDebt": phaseCount, "created": phaseCount,
        "debtStatus": phaseMap(phaseEnum("open", "resolved"), phaseDebtIdentity),
        "openDebtIds": debts, "freshOpenDebt": debts, "resolved": debts,
        "authorityCounts": phaseObject({key: phaseCount for key in ("A", "B", "C")}),
        "coverageUnknown": identities, "coverageUnknownReasons": phaseMap(ambiguous),
        "notEvaluated": notEvaluated, "partialCoverage": partial,
        "observationsBySensor": phaseMap(counts),
    }
    detector = phaseObject({"sensor": phaseIdentity, "state": sensorState}, ("sensor", "state"))
    routine = phaseObject({
        "routine": lambda value: type(value) is int and 1 <= value <= 19,
        "state": phaseEnum("observed", "partial", "unknown", "not-evaluated", "no-detector"),
        "detectors": phaseList(phaseEither(detector, phaseIdentity)),
    }, ("routine", "state", "detectors"))
    sensor = phaseObject({
        "id": phaseIdentity, "registered": boolean, "state": sensorState,
        "executed": boolean, "unknown": boolean, "notEvaluated": boolean,
        "observations": counts, "routine_ids": phaseList(lambda value: type(value) is int and 1 <= value <= 19),
        "reason": ambiguous, "partial": boolean, "skippedCount": phaseCount,
    }, ("id", "state"))
    return {
        "observe": phaseObject(observation),
        "reobserve": phaseObject({**observation,
                                  # Exact non-reference literal emitted only by
                                  # FullRunner._phaseReobserve's no-mutation path.
                                  "reused": phaseEnum("no state-changing step ran this run; the observe scan is the re-observation"),
                                  "resolvedWork": debts,
                                  "notes": phaseList(phaseObject({"debtId": phaseDebtIdentity, "note": ambiguous}, ("debtId", "note")))}),
        "retro": phaseObject({
            "routines": phaseEither(phaseCount, phaseList(phaseEither(routine, lambda value: type(value) is int and 1 <= value <= 19))),
            "sensors": phaseList(phaseEither(sensor, phaseIdentity)),
            "registered": phaseCount, "executed": phaseCount, "unknown": identities,
            "notEvaluated": notEvaluated, "partiallyCovered": partial,
        }),
        "triage": phaseObject({
            **{key: debts for key in ("classA", "classB", "reportOnly", "issueClosure", "held", "skippedActive")},
            "classC": phaseEmpty,
            "carried": phaseEither(phaseCount, debts), "filtered": phaseEither(phaseCount, debts),
            "counts": phaseObject({key: phaseCount for key in ("A", "B", "B-report-only", "C")}),
        }),
        "reconcile": phaseObject({
            "sourceHead": phaseEither(lambda value: type(value) is str and COMMIT.fullmatch(value) is not None, phaseEnum("unknown")),
            "integrationHead": phaseEither(lambda value: type(value) is str and COMMIT.fullmatch(value) is not None, phaseEnum("unknown")),
            # Non-null branch references are deliberately not portable here.
            "integrationBranch": nothing, "integrationHeadUnknown": ambiguous,
            "unresolvedWork": lambda value: type(value) is int and value == 0,
        }),
        "class_a": phaseObject({"status": settled, "landings": phaseEmpty}),
        "class_b": phaseObject({"status": settled, "dispatched": nothing, "reason": ambiguous}),
        "verify": phaseObject({"status": settled, "results": phaseEmpty, "deferred": phaseEmpty, "expired": identities}),
    }


_WORK_STATES = frozenset(WORK_STATES)
_HISTORY_KEYS = frozenset({"at", "from", "to", "reason"})


def _is_well_formed_settled_history(item: dict[str, Any]) -> bool:
    if not isinstance(item, dict) or item.get("state") != "resolved":
        return False
    history = item.get("history")
    if not isinstance(history, list) or not history:
        return False
    if not isinstance(history[-1], dict) or history[-1].get("to") != "resolved":
        return False
    parsed_times = []
    for entry in history:
        if not isinstance(entry, dict) or set(entry) != _HISTORY_KEYS:
            return False
        if not isinstance(entry["at"], str):
            return False
        try:
            parsed_times.append(parseTime(entry["at"]))
        except Exception:
            return False
        if not isinstance(entry["from"], str) or not isinstance(entry["to"], str):
            return False
        if entry["from"] not in _WORK_STATES or entry["to"] not in _WORK_STATES:
            return False
        reason = entry["reason"]
        if not isinstance(reason, str) or not bool(reason.strip()):
            return False

    for i in range(1, len(history)):
        if history[i]["from"] != history[i - 1]["to"]:
            return False
        if parsed_times[i] < parsed_times[i - 1]:
            return False

    return True


def phase_hold(value: Any) -> str | None:
    """Fail closed without inspecting files or echoing unknown keys/values.

    Schemas validate the complete tree, including empty/false/null unknowns.
    Unsupported shapes remain hot, not dropped or coerced into healthy data.
    """
    if not phaseObject(phaseSchemas())(value):
        return "phase has unknown, nonportable or unsettled schema data; payload must stay hot"
    return None


def settled_references(document: dict[str, Any], run: dict[str, Any]) -> bool:
    """Require CURRENT hot settlement for typed debt roles, not search keys.

    FullRunner's debtStatus covers tracked work only. Receipt open lists and
    triage/record debt references can name undispatched debts (especially C).
    Historical resolved labels, absence and pointer retention prove nothing.
    Sensor/receipt/decision identities are not debt IDs and need no work item.
    Called only after the complete phase schema check; no file reads or writes.
    """
    debts: set[str] = set()
    observations = [run["phases"][name] for name in ("observe", "reobserve") if name in run["phases"]]
    for summary in observations:
        openIds = summary.get("openDebtIds", [])
        openSet = set(openIds)
        if len(openIds) != len(openSet):
            return False
        if "openDebt" in summary and summary["openDebt"] != len(openIds):
            return False  # count without a complete identity list is uncertainty
        if "openDebtIds" in summary:
            if not set(summary.get("freshOpenDebt", [])).issubset(openSet):
                return False
            if any((state == "open") != (debt in openSet) for debt, state in summary.get("debtStatus", {}).items()):
                return False
            if set(summary.get("resolved", []) + summary.get("resolvedWork", [])).intersection(openSet):
                return False
        counts = summary.get("authorityCounts")
        if counts is not None and sum(counts.values()) != len(openIds):
            return False
        debts.update(summary.get("debtStatus", {}))
        for name in ("openDebtIds", "freshOpenDebt", "resolved", "resolvedWork"):
            debts.update(summary.get(name, []))
    triage = run["phases"].get("triage", {})
    for name in ("classA", "classB", "classC", "reportOnly", "issueClosure", "held", "skippedActive", "carried", "filtered"):
        value = triage.get(name, [])
        if type(value) is list:
            debts.update(value)
        elif value:
            return False  # unidentified historical carried/filtered debt
    for authority, name in (("A", "classA"), ("B", "classB"), ("B-report-only", "reportOnly"), ("C", "classC")):
        # Producer counts each named set separately (not issueClosure).
        ids = triage.get(name, [])
        if triage.get("counts", {}).get(authority, len(ids)) != len(set(ids)):
            return False
    debts.update(run["phases"].get("verify", {}).get("expired", []))

    def record(value: Any) -> bool:
        # Explicit canonical record roles, not references()' search heuristic
        # (which intentionally indexes unknown future keys as well).
        if type(value) is list:
            return all(record(item) for item in value)
        if type(value) is dict:
            for name, item in value.items():
                if name == "debtId":
                    if not phaseDebtIdentity(item):
                        return False
                    debts.add(item)
                elif name == "debtIds":
                    if not phaseList(phaseDebtIdentity)(item):
                        return False
                    debts.update(item)
                elif not record(item):
                    return False
        return True

    for name in ("actions", "steps", "decisions", "desk", "proofArtifacts", "receipts",
                 "branches", "pullRequests", "agentAssignments", "ciResults"):
        if not record(run.get(name, [])):
            return False
    desk = run.get("desk", {})
    if type(desk) is not dict or type(desk.get("operations", [])) is not list:
        return False
    for operation in desk.get("operations", []):
        if type(operation) is not dict:
            return False
        # Desk._operations uses these subjects as debt IDs; coverage/staleness
        # operation subjects, in contrast, are sensor/schedule identities.
        if operation.get("kind") in ("exhausted_attempts", "failed_dispatch"):
            if not phaseDebtIdentity(operation.get("subject")):
                return False
            debts.add(operation["subject"])
    options = run.get("options", {})
    if type(options) is not dict:
        return False
    if options.get("debt") is not None:
        if not phaseDebtIdentity(options["debt"]):
            return False
        debts.add(options["debt"])
    work = document.get("work")
    if type(work) is not dict:
        return False
    searchDebts = set(references(run)["debtIds"])
    for debt, item in work.items():
        if type(item) is not dict:
            return False
        if item.get("runId") == run["runId"] or item.get("adoptedBy") == run["runId"] or debt in searchDebts:
            debts.add(debt)
    for debt in debts:
        item = work.get(debt)
        if (type(item) is not dict or item.get("debtId") != debt or item.get("state") != "resolved"
                or item.get("authority") not in ("A", "B", "C") or not _is_well_formed_settled_history(item)):
            return False
    for summary in observations:
        if "authorityCounts" in summary:
            actual = {key: 0 for key in ("A", "B", "C")}
            for debt in summary.get("openDebtIds", []):
                actual[work[debt]["authority"]] += 1
            if any(summary["authorityCounts"].get(key, 0) != count for key, count in actual.items()):
                return False
    for authority, names in (("A", ("classA", "issueClosure")), ("B", ("classB", "reportOnly")), ("C", ("classC",))):
        if any(work[debt]["authority"] != authority for name in names for debt in triage.get(name, [])):
            return False
    return True


def eligible(document: dict[str, Any], run: dict[str, Any]) -> bool:
    # 'blocked' is a terminal runner state, but not settled operational work.
    if run.get("status") not in {"completed", "abandoned", "failed"} or POINTER in run:
        return False
    if not isinstance(run.get("phases"), dict) or not run["phases"] or not run.get("finishedAt"):
        return False
    if phase_hold(run["phases"]):
        return False
    if any(lease.get("holder") == run["runId"] for lease in document["leases"].values()):
        return False  # even an expired lease remains hot until normal recovery
    for action in run.get("actions", []):
        if action.get("status") not in {"done", "superseded", "cancelled"}:
            return False
    for step in run.get("steps", []):
        if step.get("status") not in {"done", "superseded", "cancelled", "failed", "skipped"}:
            return False
    for decision in run.get("decisions", []):
        if decision.get("status") not in {"closed", "resolved", "accepted", "rejected"}:
            return False
    if run.get("unresolvedWork") or run.get("deferred"):
        return False
    if not settled_references(document, run):
        return False
    try:
        parseTime(run["startedAt"])
        parseTime(run["finishedAt"])
    except (KeyError, ValueError):
        return False
    return True


def memory(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("operations", {}).get(MEMORY)
    if value is None:
        return {"schemaVersion": SCHEMA, "head": None, "pages": 0, "events": 0}
    if not isinstance(value, dict) or value.get("schemaVersion") != SCHEMA:
        raise fail("invalid hot memory metadata")
    if value.get("head") is not None:
        check_descriptor(value["head"], "index")
    if any(type(value.get(key)) is not int or value[key] < 0 for key in ("pages", "events")):
        raise fail("invalid hot index counters")
    return value


def verify_transition(store: GitRefLedgerStore, previous: dict[str, Any], candidate: dict[str, Any]) -> None:
    """Protect archive history at the ordinary hot-write boundary.

    Unchanged metadata/pointers need no transport reads. New transfers and
    forward rollbacks must extend the verified index and round-trip the exact
    old run. This is integrity checking, not authority to execute any work.
    """
    before, after = memory(previous), memory(candidate)
    archived = {key: run for key, run in previous["runs"].items() if POINTER in run}
    changed = {key for key in set(previous["runs"]) | set(candidate["runs"])
               if previous["runs"].get(key, {}).get(POINTER) != candidate["runs"].get(key, {}).get(POINTER)}
    if previous["schemaVersion"] == ARCHIVE_LEDGER_SCHEMA and candidate["schemaVersion"] != ARCHIVE_LEDGER_SCHEMA:
        raise fail("archive-aware ledger schema cannot be downgraded")
    for key, run in archived.items():
        if key not in changed and candidate["runs"].get(key) != run:
            raise fail("archived run is immutable until verified rollback")
    if before == after:
        if changed:
            raise fail("archive pointer change requires an appended index event")
        return
    if (candidate["schemaVersion"] != ARCHIVE_LEDGER_SCHEMA or
            after["pages"] != before["pages"] + 1 or
            after["events"] <= before["events"] or after["head"] is None):
        raise fail("archive metadata must append history, never discard it")
    archive = GitArchive(store)
    page = decoded(archive.read(after["head"]))
    if (page["previous"] != before["head"] or
            after["events"] != before["events"] + len(page["entries"]) or
            {row["runId"] for row in page["entries"]} != changed or
            len(page["entries"]) != len(changed)):
        raise fail("index extension does not match hot pointer changes")
    if before["head"] is not None:
        archive.read(before["head"])
    for row in page["entries"]:
        key = row["runId"]
        old, new = previous["runs"].get(key), candidate["runs"].get(key)
        if old is None or new is None:
            raise fail("archive transition cannot add/delete run identities")
        if row["event"] == "archive":
            if (not eligible(previous, old) or not eligible(candidate, old)
                    or POINTER not in new or hydrate(archive, new) != old):
                raise fail("archive transition is not an eligible lossless transfer")
            segment = new[POINTER]["segment"]
        else:
            if POINTER not in old or POINTER in new or hydrate(archive, old) != new:
                raise fail("rollback must restore exactly the verified run")
            segment = old[POINTER]["segment"]
        refs = references(old if row["event"] == "archive" else new)
        if (row["segment"] != segment or row["debtIds"] != refs["debtIds"] or
                row["routines"] != refs["routines"] or row["startedAt"] != old["startedAt"] or
                row["finishedAt"] != old["finishedAt"]):
            raise fail("index transition identity mismatch")


def source_bytes(store: GitRefLedgerStore, commit: str, document: dict[str, Any]) -> bytes:
    spec = f"{commit}:ledger.json"
    size = int(store.plumb(["cat-file", "-s", spec]))
    if not 0 < size <= MAX_SNAPSHOT_BYTES:
        raise fail("source snapshot exceeds bounded read limit")
    result = store.git(["cat-file", "-p", spec], timeout=store.localTimeout)
    if result.returncode or len(result.stdout) != size or decoded(result.stdout) != document:
        raise fail("source snapshot identity mismatch")
    return result.stdout


def projected(run: dict[str, Any], pointer: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(run)
    result["phases"] = {}  # never masquerade a count/headline as original evidence
    result[POINTER] = copy.deepcopy(pointer)
    return result


def hydrate(archive: GitArchive, run: dict[str, Any]) -> dict[str, Any]:
    """Verify schema, identity, original snapshot bytes and hot stub; no writes."""
    pointer = run.get(POINTER)
    if pointer is None:
        return copy.deepcopy(run)
    if not isinstance(pointer, dict) or pointer.get("schemaVersion") != SCHEMA:
        raise fail("invalid run pointer")
    envelope = resolve_segment(archive, check_descriptor(pointer.get("segment"), "run"))
    original = envelope["run"]
    if (envelope["runId"] != run.get("runId") or
            pointer.get("references") != references(original) or
            projected(original, pointer) != run):
        raise fail("source/segment/hot run identity mismatch")
    return copy.deepcopy(original)


def resolve_segment(archive: GitArchive, ref: dict[str, Any]) -> dict[str, Any]:
    envelope = decoded(archive.read(check_descriptor(ref, "run")))
    raw = archive.read(envelope["source"])
    source = decoded(raw)
    anchor = decoded(archive.read(envelope["sourceAnchor"]))
    anchorStore = archive.store(envelope["sourceAnchor"])
    anchorCommit = anchorStore.plumb(["rev-parse", "--verify", anchorStore.trackingRef])
    ancestry = anchorStore.git(["merge-base", "--is-ancestor", envelope["sourceCommit"], anchorCommit],
                               timeout=anchorStore.localTimeout)
    if (ancestry.returncode or anchor["sourceCommit"] != envelope["sourceCommit"] or
            anchor["source"] != envelope["source"] or envelope["ledgerRef"] != archive.ledger.ref or
            source["runs"].get(envelope["runId"]) != envelope["run"] or
            source_bytes(archive.ledger, envelope["sourceCommit"], source) != raw):
        raise fail("source bytes/commit/run provenance mismatch")
    return envelope


def snapshot(store: GitRefLedgerStore, run_id: str) -> bytes:
    document, _ = store.load()
    run = document["runs"].get(run_id)
    if run is None or POINTER not in run:
        raise fail("run has no archived source snapshot")
    archive = GitArchive(store)
    hydrate(archive, run)
    envelope = resolve_segment(archive, run[POINTER]["segment"])
    return archive.read(envelope["source"])


def capacity(store: GitRefLedgerStore, document: dict[str, Any], version: str | None) -> dict[str, Any]:
    """Bounded read-only telemetry; exact hot size, non-additive contributors.

    Sample only the immediate parent, never walk unbounded Git history. Growth
    is an observation, not a forecast guarantee (an archive can make it negative).
    Replay metadata is deliberately retained, so a hard cap still eventually
    stops writes. These thresholds are an operator stop model, not auto-pruning.
    """
    current = len(source_bytes(store, version, document)) if version else len(serialize(document))
    limit = ledgerByteLimit()
    runs = sorted(({"runId": key, "compactJsonBytes": len(packed(run)),
                    "phaseBytes": len(packed(run.get("phases", {})))}
                   for key, run in document["runs"].items()),
                  key=lambda item: (-item["compactJsonBytes"], item["runId"]))
    sections = sorted(({"section": key, "compactJsonBytes": len(packed(value))}
                       for key, value in document.items()), key=lambda item: -item["compactJsonBytes"])
    growth: dict[str, Any] = {"sample": "immediate Git parent only", "previousVersion": None,
                              "deltaBytes": None, "bytesPerGeneration": None, "bytesPerSecond": None}
    if version:
        parents = store.plumb(["rev-list", "--parents", "-n", "1", version]).split()[1:]
        if parents:
            parent = parents[0]
            spec = f"{parent}:ledger.json"
            size = int(store.plumb(["cat-file", "-s", spec]))
            if not 0 < size <= MAX_SNAPSHOT_BYTES:
                raise fail("growth sample exceeds bounded read limit")
            result = store.git(["cat-file", "-p", spec], timeout=store.localTimeout)
            if result.returncode or len(result.stdout) != size:
                raise fail("growth sample read failed")
            previous = validate_ledger(decoded(result.stdout))
            delta = current - size
            generations = document["generation"] - previous["generation"]
            growth.update(previousVersion=parent, deltaBytes=delta,
                          bytesPerGeneration=delta / generations if generations > 0 else None)
            if document.get("updatedAt") and previous.get("updatedAt"):
                seconds = (parseTime(document["updatedAt"]) - parseTime(previous["updatedAt"])).total_seconds()
                if seconds > 0:
                    growth["bytesPerSecond"] = delta / seconds
    # Reserve one observed largest hot run (compact lower bound), one positive
    # sampled write, plus 256 KiB margin. Not a promise that any next run fits.
    reserve = max([256 * 1024, max(0, growth["deltaBytes"] or 0)] +
                  [r["compactJsonBytes"] for r in runs]) + 256 * 1024
    alert = "stop-new-runs" if current >= limit * .9 or limit - current < reserve else (
        "plan-archive" if current >= limit * .7 else "normal")
    positive = growth["bytesPerGeneration"]
    return {"bytes": current, "limitBytes": limit, "headroomBytes": limit - current,
            "percent": round(current * 100 / limit, 2), "alert": alert,
            "thresholdBytes": {"plan70": (limit * 70 + 99) // 100, "stop90": (limit * 90 + 99) // 100},
            "suggestedReserveBytes": reserve, "operatorStopNewRuns": alert == "stop-new-runs",
            "generationsTo90AtSampledGrowth": max(0, (limit * .9 - current) / positive) if positive and positive > 0 else None,
            "growth": growth, "largestSections": sections, "largestRuns": runs[:10],
            "contributorUnits": "compact JSON bytes; non-additive, excludes enclosing indentation",
            "newRunControls": {"stopEnvironment": "GAIA_STEWARD_FULL_STOP_NEW_RUNS=1",
                               "minimumHeadroomEnvironment": "GAIA_STEWARD_FULL_MIN_HEADROOM_BYTES",
                               "automaticStopPercent": 90,
                               "resumeRecordRollbackAllowed": True},
            "retentionLimit": "phase-only transfer; runs/actions/steps/receipts/proofArtifacts/work/tombstones remain hot and grow; no automatic deletion"}


def plan(store: GitRefLedgerStore, *, run_ids: list[str] | None = None,
         max_runs: int = MAX_PAGE_ENTRIES) -> dict[str, Any]:
    """Read-only migration preview; does not publish even orphan objects."""
    GitArchive(store)
    if type(max_runs) is not int or not 1 <= max_runs <= MAX_PAGE_ENTRIES:
        raise ValueError(f"max_runs must be 1..{MAX_PAGE_ENTRIES}")
    document, version = store.load()
    state = memory(document)
    if state["head"] is not None:
        GitArchive(store).read(state["head"])
    wanted = set(run_ids) if run_ids is not None else set(document["runs"])
    if wanted - set(document["runs"]):
        raise fail("unknown requested run identity")
    candidates = sorted((r for r in document["runs"].values()
                         if r["runId"] in wanted and eligible(document, r)),
                        key=lambda r: (r["startedAt"], r["runId"]))
    report = capacity(store, document, version)
    return {"eligible": [r["runId"] for r in candidates[:max_runs]],
            "ineligible": sorted(wanted - {r["runId"] for r in candidates}),
            "remainingEligible": max(0, len(candidates) - max_runs),
            "phaseHolds": {key: reason for key in sorted(wanted)
                           if (reason := phase_hold(document["runs"][key].get("phases", {})))},
            "capacity": report,
            "version": version, "hotBytes": report["bytes"],
            "indexPageLimitBytes": MAX_INDEX_BYTES, "indexPageLimitEntries": MAX_PAGE_ENTRIES,
            "applyRequired": True}


def _index(archive: GitArchive, document: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    previous = memory(document)
    # Validate the current index before extending it, even after an interruption.
    if previous["head"] is not None:
        archive.read(previous["head"])
    page = {"schemaVersion": SCHEMA, "kind": "index", "previous": previous["head"], "entries": rows}
    head = archive.publish("index", packed(page))
    document["schemaVersion"] = ARCHIVE_LEDGER_SCHEMA
    document.setdefault("operations", {})[MEMORY] = {
        "schemaVersion": SCHEMA, "head": head,
        "pages": previous["pages"] + 1, "events": previous["events"] + len(rows),
    }


def migrate(store: GitRefLedgerStore, *, run_ids: list[str] | None = None,
            max_runs: int = MAX_PAGE_ENTRIES, retries: int = 5,
            checkpoint: Callable[[str], None] = lambda stage: None) -> dict[str, Any]:
    """Explicit, restartable archive migration; never run from a CAS mutator.

    Recompute eligibility from each fresh CAS generation. Publication is safe to
    repeat. On interruption objects remain durable orphans, and no hot data is
    removed until all verifications succeed. max_runs bounds one index page.
    """
    archive = GitArchive(store)
    if type(max_runs) is not int or not 1 <= max_runs <= MAX_PAGE_ENTRIES:
        raise ValueError(f"max_runs must be 1..{MAX_PAGE_ENTRIES}")
    if type(retries) is not int or not 0 <= retries <= 20:
        raise ValueError("retries must be 0..20")
    for attempt in range(retries + 1):
        document, version = store.load()
        if version is None:
            return {"archived": [], "version": None, "reason": "empty ledger"}
        state = memory(document)
        if state["head"] is not None:
            archive.read(state["head"])
        requested = set(run_ids) if run_ids is not None else None
        if requested is not None and len(requested) > MAX_PAGE_ENTRIES:
            raise ValueError(f"at most {MAX_PAGE_ENTRIES} explicit run IDs per migration")
        if requested is not None and requested - set(document["runs"]):
            raise fail("unknown requested run identity")
        candidates = [r for r in document["runs"].values()
                      if (requested is None or r["runId"] in requested) and eligible(document, r)]
        candidates.sort(key=lambda r: (r["startedAt"], r["runId"]))
        candidates = candidates[:max_runs]
        # Validate already-migrated requested records; a duplicate retry is not
        # allowed to report success when its archive is unavailable.
        for run_id in requested or ():
            run = document["runs"][run_id]
            if POINTER in run:
                hydrate(archive, run)
        if not candidates:
            return {"archived": [], "version": version, "reason": "no eligible terminal phase payloads"}
        rawSource = source_bytes(store, version, document)
        source = archive.publish("snapshot", rawSource, parent=version)
        # Equal ledger bytes at different commits deliberately share a snapshot,
        # but must NOT share the provenance anchor: every source commit remains
        # fetchable from archive refs alone after hot-ledger ref loss/replacement.
        anchor = archive.publish("anchor", packed({"schemaVersion": SCHEMA, "kind": "anchor",
                                 "source": source, "sourceCommit": version}), parent=version)
        checkpoint("snapshot-published")
        working = copy.deepcopy(document)
        rows = []
        now = formatTime(utcNow())
        for run in candidates:
            envelope = {"schemaVersion": SCHEMA, "kind": "run", "runId": run["runId"],
                        "source": source, "sourceAnchor": anchor, "sourceCommit": version, "ledgerRef": store.ref, "run": run}
            segment = archive.publish("run", packed(envelope))
            pointer = {"schemaVersion": SCHEMA, "segment": segment, "references": references(run)}
            stub = projected(run, pointer)
            if hydrate(archive, stub) != run:
                raise fail("migration hydration equality failed")
            working["runs"][run["runId"]] = stub
            rows.append({"event": "archive", "runId": run["runId"], "segment": segment,
                         "at": now, "startedAt": run["startedAt"], "finishedAt": run["finishedAt"],
                         "debtIds": pointer["references"]["debtIds"], "routines": pointer["references"]["routines"]})
        checkpoint("segments-verified")
        _index(archive, working, rows)
        checkpoint("index-verified")
        working["updatedAt"] = now
        # Exercise the authoritative configured hot bound before attempting CAS.
        before, after = len(rawSource), len(serialize(nextGeneration(working)))
        if after >= before:
            return {"archived": [], "version": version, "reason": "no hot size saving", "beforeBytes": before, "afterBytes": after}
        checkpoint("before-cas")
        try:
            result = store.compare_and_swap(version, working, "steward archive terminal phases (non-destructive)")
            checkpoint("after-cas")
            return {"archived": [r["runId"] for r in candidates], "version": result,
                    "sourceCommit": version, "source": source, "sourceAnchor": anchor, "index": memory(working)["head"],
                    "beforeBytes": before, "afterBytes": after}
        except LedgerConflict:
            if attempt == retries:
                raise
    raise AssertionError("unreachable")


def rollback(store: GitRefLedgerStore, run_id: str, *, retries: int = 5) -> dict[str, Any]:
    """Restore original run bytes semantically, retain archives and audit index.

    Never resets the whole ledger or clobbers concurrent work. The source raw
    bytes are still available through snapshot retrieval for forensic equality.
    """
    archive = GitArchive(store)
    if type(retries) is not int or not 0 <= retries <= 20:
        raise ValueError("retries must be 0..20")
    for attempt in range(retries + 1):
        document, version = store.load()
        run = document["runs"].get(run_id)
        if run is None:
            raise fail("unknown run")
        if POINTER not in run:
            # A repeated rollback still verifies its latest history evidence.
            page = memory(document)["head"]
            if page is not None:
                archive.read(page)
            return {"restored": [], "version": version}
        original = hydrate(archive, run)
        working = copy.deepcopy(document)
        working["runs"][run_id] = original
        now = formatTime(utcNow())
        refs = run[POINTER]["references"]
        _index(archive, working, [{"event": "rollback", "runId": run_id,
                                 "segment": run[POINTER]["segment"], "at": now,
                                 "startedAt": original["startedAt"], "finishedAt": original["finishedAt"],
                                 "debtIds": refs["debtIds"], "routines": refs["routines"]}])
        working["updatedAt"] = now
        serialize(working)  # fail closed if the restored hot ledger needs more capacity
        try:
            result = store.compare_and_swap(version, working, "steward archive rollback (retain evidence)")
            return {"restored": [run_id], "version": result}
        except LedgerConflict:
            if attempt == retries:
                raise
    raise AssertionError("unreachable")


def show(store: GitRefLedgerStore, run_id: str) -> dict[str, Any]:
    document, version = store.load()
    run = document["runs"].get(run_id)
    if run is None:
        raise fail("unknown run")
    return {"run": hydrate(GitArchive(store), run), "version": version,
            "archive": copy.deepcopy(run.get(POINTER)),
            "completeness": "current-snapshot; earlier pruning may exist in source Git ancestry",
            "retrievalGuarantee": "ledger JSON bytes only; external proof/receipt/artifact files are not bundled; their references remain hot"}


def history(store: GitRefLedgerStore, *, run_id: str | None = None, debt_id: str | None = None,
            routine: str | None = None, since: str | None = None, until: str | None = None,
            cursor: dict[str, Any] | None = None, pages: int = 1) -> dict[str, Any]:
    """Bounded, read-only index search. Continue using nextCursor, even on no hits.

    A page is <=256 KiB / 32 events; this call reads <=10 pages. A cursor is a
    checksum/size descriptor, not a local path, so it also works on another host.
    Search matches are index metadata, not verified proof of a resolved debt.
    """
    if type(pages) is not int or not 1 <= pages <= 10:
        raise ValueError("pages must be 1..10")
    lo = parseTime(since) if since else None
    hi = parseTime(until) if until else None
    if lo and hi and lo > hi:
        raise ValueError("since must not be after until")
    document, version = store.load()
    next_page = cursor if cursor is not None else memory(document)["head"]
    archive = GitArchive(store)
    rows: list[dict[str, Any]] = []
    visited: set[str] = set()
    for _ in range(pages):
        if next_page is None:
            break
        check_descriptor(next_page, "index")
        if next_page["sha256"] in visited:
            raise fail("cyclic index")
        visited.add(next_page["sha256"])
        page = decoded(archive.read(next_page))
        for row in page["entries"]:
            if run_id is not None and row["runId"] != run_id:
                continue
            if debt_id is not None and debt_id not in row["debtIds"]:
                continue
            if routine is not None and str(routine) not in row["routines"]:
                continue
            if lo and parseTime(row["finishedAt"]) < lo:
                continue
            if hi and parseTime(row["startedAt"]) > hi:
                continue
            envelope = resolve_segment(archive, row["segment"])
            if (envelope["runId"] != row["runId"] or
                    references(envelope["run"])["debtIds"] != row["debtIds"] or
                    references(envelope["run"])["routines"] != row["routines"] or
                    envelope["run"].get("startedAt") != row["startedAt"] or
                    envelope["run"].get("finishedAt") != row["finishedAt"]):
                raise fail("index/segment identity mismatch")
            rows.append(row)
        next_page = page["previous"]
    return {"entries": rows, "nextCursor": next_page, "version": version,
            "memory": memory(document), "scope": "archive/rollback events; hot work is unchanged"}
