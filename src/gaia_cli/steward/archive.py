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
    parseTime, serialize, utcNow, validate_ledger, ledgerByteLimit, ARCHIVE_LEDGER_SCHEMA,
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
        try:
            size = int(store.plumb(["cat-file", "-s", spec]))
        except ValueError as exc:
            raise fail("unreadable archive size") from exc
        if size != ref["size"] or size > LIMITS[ref["kind"]]:
            raise fail("archive byte count mismatch")
        result = store.git(["cat-file", "-p", spec], timeout=store.localTimeout)
        data = result.stdout
        if result.returncode or len(data) != size or digest(data) != ref["sha256"]:
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
                visit(item, key)
        elif value is not None:
            text = str(value)
            if "debt" in lowered or lowered in {"classa", "classb", "classc", "reportonly", "held", "skippedactive", "issueclosure", "resolvedwork", "freshopendebt", "opendebtids", "resolved"}:
                if isinstance(value, str):
                    debts.add(text)
            if "routine" in lowered:
                routines.add(text)
            if "id" in lowered or "decision" in lowered or "idempotency" in lowered:
                if isinstance(value, str):
                    ids.add(text)
    visit(run)
    return {"debtIds": sorted(debts), "routines": sorted(routines), "identities": sorted(ids)}


def phase_hold(value: Any, key: str = "") -> str | None:
    """Conservative gate: never cold-store pending data or unbundled files.

    No local file is opened. References outside phases (proofArtifacts, action
    outcomes, receipts, etc.) remain byte-for-byte hot. Unknown phase reference
    shapes fail on reference-bearing keys or path/URI-looking strings instead
    of pretending that storing JSON makes external bytes portable.
    """
    lowered = key.lower().replace("_", "").replace("-", "")
    if value and any(token in lowered for token in ("artifact", "proof", "path", "file", "url", "uri")):
        return "phase references an unbundled artifact; payload must stay hot"
    if value and lowered in {"decisions", "pendingdecisions", "classc", "unresolvedwork", "pendingactions"}:
        return "phase contains unsettled work or decision data"
    if lowered == "debtstatus" and isinstance(value, dict) and any(state != "resolved" for state in value.values()):
        return "phase contains unresolved debt lifecycle data"
    if lowered in {"status", "state"} and (not isinstance(value, str) or value not in {
        "done", "completed", "complete", "resolved", "closed", "accepted", "rejected",
        "cancelled", "superseded", "skipped", "failed", "abandoned", "observed",
    }):
        return "phase contains an unsettled or unknown lifecycle"
    if isinstance(value, dict):
        for name, item in value.items():
            reason = phase_hold(item, name)
            if reason:
                return reason
    elif isinstance(value, list):
        for item in value:
            reason = phase_hold(item, key)
            if reason:
                return reason
    elif isinstance(value, str) and (
        re.search(r"(?:^|\s)(?:[/~]|\.\.?/|\.gaia/|[A-Za-z]:[\\\\/])", value)
        or re.search(r"[A-Za-z][A-Za-z0-9+.-]{0,31}://|\bfile:", value)
        or re.search(r"(?:^|[/\\\\\s])[\w.-]+\.(?:json|jsonl|diff|patch|zip|txt|md|log|png|pdf)(?:$|\s)", value)
    ):
        return "phase contains a path/URI; external bytes are not bundled"
    return None


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
    if run.get("unresolvedWork"):
        return False
    if any(item.get("runId") == run["runId"] and item.get("state") != "resolved"
           for item in document["work"].values()):
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
    return {"eligible": [r["runId"] for r in candidates[:max_runs]],
            "ineligible": sorted(wanted - {r["runId"] for r in candidates}),
            "remainingEligible": max(0, len(candidates) - max_runs),
            "phaseHolds": {key: reason for key in sorted(wanted)
                           if (reason := phase_hold(document["runs"][key].get("phases", {})))},
            "capacity": capacity(store, document, version),
            "version": version, "hotBytes": len(serialize(document)),
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
        source = archive.publish("snapshot", source_bytes(store, version, document), parent=version)
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
        before, after = len(serialize(document)), len(serialize(working))
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
