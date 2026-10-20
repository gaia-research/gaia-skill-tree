"""The deterministic, zero-model, resumable runner behind `/gaia-steward-full`.

Skills own *how*; this module owns *order, scheduling, reconciliation and
completion*. It never calls a model and never talks to a forge. Whatever needs
one of those becomes an **action** in the run record - `agent.build`,
`agent.verify`, `forge.open_pr`, `lead.integrate` - for a driver (the Claude
skill session, or the scheduled workflow's driver step) to perform, and the
driver reports back with `record`.

Every state change goes through `ledger.update`, so a run is a sequence of
compare-and-swap commits on one shared document:

    recover -> reconcile -> observe -> triage -> class_a -> class_b -> verify
            -> reobserve -> retro -> report -> done

Properties the rest of the design leans on:

* **One active run per ledger.** Lease `run`, held by the run id. A second
  invocation reports the holder and does nothing else.
* **Intent before effect.** A branch push is recorded as an intent step first;
  a resumed run re-runs the *idempotent* landing (which reports
  `already-exists`) instead of creating a second branch.
* **Phases are re-entrant.** A phase commits its results and the move to the
  next phase in one write, so a crash replays at most the phase it died in.
* **Never claim without re-observation.** Work becomes `resolved` only after a
  fresh scan shows its debt no longer open, and only from `landed`,
  `no_change`, or a Class A `proposed` whose branch the scanned checkout
  contains.
* **Unknown is not healthy.** Unknown sensor coverage refuses Class A and
  Class B, and the retro table never counts an unexecuted sensor as healthy.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from gaia_cli.steward.controller import ScanResult, StewardController
from gaia_cli.steward.ledger import (
    LedgerConflict,
    LedgerUnavailable,
    acquire_lease,
    formatTime,
    leaseHolder,
    parseTime,
    release_lease,
    set_lane,
    transition_work,
    update,
    upsert_work,
)
from gaia_cli.steward.lane import (
    Lane,
    LaneError,
    lane_document,
    load_lane,
    mark_dispatched,
    next_dispatchable,
    reconcile,
    record_verdict,
)
from gaia_cli.steward.models import AuthorityClass, Debt, stable_json
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.receipts import ensure_local_state_path

PHASES = (
    "recover", "reconcile", "observe", "triage", "class_a", "class_b",
    "verify", "reobserve", "retro", "report", "done",
)

# Contract section 6: which phases each mode runs, in order.
MODEPHASES: dict[str, tuple[str, ...]] = {
    "full": PHASES[:-1],
    "observe": ("recover", "reconcile", "observe", "report"),
    "triage": ("recover", "reconcile", "observe", "triage", "report"),
    "verify": ("recover", "verify", "reobserve", "report"),
    "retro": ("recover", "retro", "report"),
}

# Work states in which a debt is already being worked and must not be queued
# again, and the states that hold a debt out of re-dispatch until something
# outside the runner (a human, a merge, a re-observation) moves it.
ACTIVEWORK = ("queued", "building", "proposed", "verified")
HELDWORK = ("escalated", "no_change", "landed")
OPENRUNSTATES = ("active", "awaiting-action")
TERMINALRUNSTATES = ("completed", "blocked", "failed", "abandoned")

BUILDERMODELS = ("claude-haiku-5-5", "claude-sonnet-5-5")
VERIFIERMODELS = ("claude-sonnet-5-5",)
BADEFFORTS = frozenset({"", "default", "inherit"})

RUNLEASE = "run"
RETAINEDRUNS = 25
CONTENDEDRETRIES = 80
STATEDIRECTORY = Path(".gaia/steward/full")


class FullRunError(RuntimeError):
    """A runner precondition failed; nothing was changed."""


class RecordRefused(FullRunError):
    """A driver-supplied outcome was refused. Input error; exit code 2."""


class UnknownRun(FullRunError):
    """The named run does not exist in the ledger."""


class LeaseLost(FullRunError):
    """This run no longer holds the `run` lease; another run owns the ledger."""


def _checkpoint(name: str) -> None:
    """Named crash-injection point. A no-op in production; tests patch it."""


def _utcNow() -> datetime:
    return datetime.now(timezone.utc)


def _hash12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _git(root: Path, *args: str, timeout: float = 90.0) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}}
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            env=env, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


@dataclass
class FullRunConfig:
    repo_root: Path
    store: Any
    integration_branch: str | None = None
    remote: str = "origin"
    push: bool = False
    trigger: str = "manual"
    agents: bool = True
    holder: str = "steward"
    lease_ttl_seconds: int = 1800
    clock: Callable[[], datetime] = _utcNow
    controller_factory: Callable[[], StewardController] | None = None

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).resolve()
        if self.trigger not in {"manual", "scheduled"}:
            raise ValueError("trigger must be manual or scheduled")
        if self.lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be positive")


@dataclass
class RunView:
    """What a caller (human or driver) needs after any runner call."""

    runId: str | None
    mode: str | None
    status: str
    phase: str | None
    nextAction: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    unresolvedWork: list[dict[str, Any]] = field(default_factory=list)
    coverageUnknown: list[str] = field(default_factory=list)
    notEvaluated: list[dict[str, Any]] = field(default_factory=list)
    holder: str | None = None
    holderPhase: str | None = None
    desk: dict[str, Any] | None = None
    ledger: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def exitCode(self) -> int:
        if self.status in {"completed", "awaiting-action", "observing-existing"}:
            return 0
        if self.status == "blocked":
            return 3
        return 1

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schemaVersion": "steward-full-run-view-v1",
            "runId": self.runId,
            "mode": self.mode,
            "status": self.status,
            "phase": self.phase,
            "nextAction": self.nextAction,
            "actions": self.actions,
            "summary": self.summary,
            "unresolvedWork": self.unresolvedWork,
            "coverageUnknown": self.coverageUnknown,
            "notEvaluated": self.notEvaluated,
            "ledger": self.ledger,
        }
        if self.holder is not None:
            data["holder"] = self.holder
            data["holderPhase"] = self.holderPhase
        if self.desk is not None:
            data["desk"] = self.desk
        if self.error is not None:
            data["error"] = self.error
        return data


@dataclass
class StatusView:
    ledger: dict[str, Any]
    holder: str | None
    holderPhase: str | None
    holderExpiresAt: str | None
    activeRuns: list[dict[str, Any]]
    workCounts: dict[str, int]
    work: list[dict[str, Any]]
    lane: dict[str, Any] | None
    lastScheduledRunAt: str | None
    recentRuns: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "steward-full-status-v1",
            "ledger": self.ledger,
            "holder": self.holder,
            "holderPhase": self.holderPhase,
            "holderExpiresAt": self.holderExpiresAt,
            "activeRuns": self.activeRuns,
            "workCounts": self.workCounts,
            "work": self.work,
            "lane": self.lane,
            "lastScheduledRunAt": self.lastScheduledRunAt,
            "recentRuns": self.recentRuns,
        }


def validateAgent(outcome: Mapping[str, Any], allowed: Sequence[str], role: str) -> None:
    """Common model/effort/identity checks for any recorded agent outcome."""

    agentId = outcome.get("agentId")
    if not isinstance(agentId, str) or not agentId.strip():
        raise RecordRefused(f"{role} outcome needs a non-empty agentId")
    model = outcome.get("model")
    if model not in allowed:
        raise RecordRefused(
            f"{role} model {model!r} is not permitted; allowed models: {', '.join(allowed)}"
        )
    effort = outcome.get("effort")
    if not isinstance(effort, str) or effort.strip().lower() in BADEFFORTS:
        raise RecordRefused(
            f"{role} outcome must record an explicit thinking effort; {effort!r} is not one"
        )
    for key in ("tokensIn", "tokensOut", "costUsd"):
        value = outcome.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise RecordRefused(f"{key} must be a non-negative number when supplied")


class FullRunner:
    def __init__(self, config: FullRunConfig) -> None:
        self.config = config
        self.root = config.repo_root
        self._policy: StewardPolicy | None = None
        self._controller: StewardController | None = None
        self._scans: dict[str, ScanResult] = {}
        self._handlers: dict[str, Callable[[str], bool]] = {
            "reconcile": self._phaseReconcile,
            "observe": self._phaseObserve,
            "triage": self._phaseTriage,
            "class_a": self._phaseClassA,
            "class_b": self._phaseClassB,
            "verify": self._phaseVerify,
            "reobserve": self._phaseReobserve,
            "retro": self._phaseRetro,
            "report": self._phaseReport,
        }

    # ------------------------------------------------------------------
    # small helpers
    # ------------------------------------------------------------------

    def _now(self) -> str:
        return formatTime(self.config.clock())

    def _policyLoaded(self) -> StewardPolicy:
        if self._policy is None:
            self._policy = StewardPolicy.load(self.root)
        return self._policy

    def _controllerInstance(self) -> StewardController:
        if self._controller is None:
            factory = self.config.controller_factory or StewardController
            self._controller = factory()
        return self._controller

    def _update(self, mutate: Callable[[dict[str, Any]], Any], message: str = "steward full") -> Any:
        result, _version = update(
            self.config.store, mutate, retries=CONTENDEDRETRIES,
            clock=self.config.clock, message=message,
        )
        return result

    def _load(self) -> dict[str, Any]:
        document, _ = self.config.store.load()
        return document

    def _ledgerInfo(self, version: str | None = None) -> dict[str, Any]:
        info: dict[str, Any] = {
            "transport": self.config.store.transport,
            "shared": bool(self.config.store.shared),
        }
        if not info["shared"]:
            info["warning"] = "ledger_local_only"
        return info

    def _runDirectory(self, runId: str) -> Path:
        path = self.root / STATEDIRECTORY / runId
        ensure_local_state_path(self.root, self.root / ".gaia/steward", path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(path)

    def _resolvePath(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.root / path

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return _git(self.root, *args)

    def _mutateRun(
        self, runId: str, apply: Callable[[dict[str, Any], dict[str, Any]], Any], *,
        holdsLease: bool = True, message: str = "steward full",
    ) -> Any:
        """Apply `apply(doc, run)` as one compare-and-swap commit.

        When `holdsLease`, the commit also renews the run lease and refuses to
        proceed if another run holds it: a run that lost its lease must stop,
        not keep writing over the run that replaced it.
        """

        def mutate(doc: dict[str, Any]) -> Any:
            run = doc["runs"].get(runId)
            if run is None:
                raise UnknownRun(f"unknown run {runId}")
            if holdsLease:
                now = self._now()
                held = leaseHolder(doc, RUNLEASE, now)
                if run["status"] == "abandoned" or (held is not None and held != runId):
                    raise LeaseLost(f"run {runId} no longer holds the run lease")
                acquire_lease(doc, RUNLEASE, runId, now, self.config.lease_ttl_seconds)
            return apply(doc, run)

        return self._update(mutate, message)

    def _loadRun(self, runId: str) -> dict[str, Any]:
        run = self._load()["runs"].get(runId)
        if run is None:
            raise UnknownRun(f"unknown run {runId}")
        return run

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def start(
        self, mode: str, *, routine: int | None = None, debt: str | None = None, afk: bool = False,
    ) -> RunView:
        if mode not in MODEPHASES:
            raise FullRunError(f"unknown mode {mode!r}; choose from {', '.join(MODEPHASES)}")
        if routine is not None and not 1 <= int(routine) <= 17:
            raise FullRunError("routine must be between 1 and 17")
        now = self._now()
        runId = f"run-{self.config.clock().astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        phases = MODEPHASES[mode]
        options = {
            "routine": routine, "debt": debt, "afk": bool(afk),
            "push": bool(self.config.push), "agents": bool(self.config.agents),
        }

        def mutate(doc: dict[str, Any]) -> dict[str, Any]:
            held = leaseHolder(doc, RUNLEASE, now)
            if held is not None:
                other = doc["runs"].get(held, {})
                return {
                    "existing": True, "holder": held, "phase": other.get("phase"),
                    "expiresAt": doc["leases"][RUNLEASE]["expiresAt"],
                }
            for other in doc["runs"].values():
                if other.get("status") in OPENRUNSTATES:
                    other["status"] = "abandoned"
                    other["abandonedAt"] = now
                    other["abandonedBy"] = runId
                    other["nextAction"] = "abandoned: lease expired; its unfinished work was adopted"
            unresolved = [
                {"debtId": item["debtId"], "state": item["state"], "previousRun": item.get("runId")}
                for item in sorted(doc["work"].values(), key=lambda value: value["debtId"])
                if item["state"] in ACTIVEWORK
            ]
            for entry in unresolved:
                doc["work"][entry["debtId"]]["adoptedBy"] = runId
            self._compact(doc)
            doc["runs"][runId] = {
                "runId": runId, "mode": mode, "trigger": self.config.trigger,
                "actor": self.config.holder, "startedAt": now, "finishedAt": None,
                "sourceHead": None, "integrationBranch": self.config.integration_branch,
                "integrationHead": None, "phase": phases[1], "status": "active",
                "options": options,
                "steps": [{"stepId": "phase:recover", "kind": "phase", "status": "done", "at": now}],
                "actions": [], "phases": {},
                "agentAssignments": [], "leases": [{"key": RUNLEASE, "holder": runId, "acquiredAt": now}],
                "branches": [], "pullRequests": [], "proofArtifacts": [], "ciResults": [],
                "receipts": [], "decisions": [], "unresolvedWork": unresolved,
                "modelIds": [], "thinkingEfforts": [], "tokensIn": 0, "tokensOut": 0, "costUsd": 0.0,
                "mutated": False, "nextAction": "",
            }
            acquire_lease(doc, RUNLEASE, runId, now, self.config.lease_ttl_seconds)
            return {"existing": False, "unresolved": len(unresolved)}

        outcome = self._update(mutate, "steward full start")
        if outcome["existing"]:
            return RunView(
                runId=None, mode=mode, status="observing-existing", phase=None,
                holder=outcome["holder"], holderPhase=outcome["phase"],
                nextAction=(
                    f"run {outcome['holder']} (phase {outcome['phase']}) holds the run lease until "
                    f"{outcome['expiresAt']}; nothing was started. Watch it with "
                    "`gaia steward full status`, or resume it with "
                    f"`gaia steward full run --resume {outcome['holder']}` if it is yours."
                ),
                ledger=self._ledgerInfo(),
            )
        return self.advance(runId)

    def resume(self, runId: str) -> RunView:
        now = self._now()

        def mutate(doc: dict[str, Any]) -> dict[str, Any]:
            run = doc["runs"].get(runId)
            if run is None:
                raise UnknownRun(f"unknown run {runId}")
            if run["status"] not in OPENRUNSTATES:
                return {"state": run["status"]}
            held = leaseHolder(doc, RUNLEASE, now)
            if held is not None and held != runId:
                other = doc["runs"].get(held, {})
                return {"state": "other", "holder": held, "phase": other.get("phase")}
            acquire_lease(doc, RUNLEASE, runId, now, self.config.lease_ttl_seconds)
            return {"state": "acquired"}

        outcome = self._update(mutate, "steward full resume")
        if outcome["state"] == "acquired":
            return self.advance(runId)
        if outcome["state"] == "other":
            return RunView(
                runId=runId, mode=None, status="observing-existing", phase=None,
                holder=outcome["holder"], holderPhase=outcome["phase"],
                nextAction=f"run {outcome['holder']} holds the run lease; {runId} cannot be resumed until it ends",
                ledger=self._ledgerInfo(),
            )
        return self._view(self._load(), runId)

    def advance(self, runId: str) -> RunView:
        """Run phases from the recorded phase until done or a driver is needed."""

        try:
            while True:
                run = self._loadRun(runId)
                if run["phase"] == "done" and run["status"] == "awaiting-action":
                    self._settleDone(runId)
                    break
                if run["status"] not in OPENRUNSTATES or run["phase"] == "done":
                    break
                handler = self._handlers.get(run["phase"])
                if handler is None:
                    raise FullRunError(f"run {runId} is at unknown phase {run['phase']!r}")
                if run["status"] != "active":
                    self._setStatus(runId, "active", "")
                _checkpoint(f"phase:{run['phase']}")
                if not handler(runId):
                    self._markAwaiting(runId)
                    break
        except LeaseLost as exc:
            doc = self._load()
            view = self._view(doc, runId)
            view.status = "abandoned"
            view.error = str(exc)
            view.nextAction = "this run lost the run lease; start a new run"
            return view
        except (LedgerConflict, LedgerUnavailable):
            raise
        except Exception as exc:  # noqa: BLE001 - a failing phase fails the run, loudly
            self._failRun(runId, f"{type(exc).__name__}: {exc}")
        return self._view(self._load(), runId)

    def _settleDone(self, runId: str) -> None:
        """A finished run that was waiting on the driver completes once nothing is pending."""

        now = self._now()

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            if run["status"] != "awaiting-action" or self._pending(run):
                return
            run["status"] = "completed"
            run["finishedAt"] = now
            run["nextAction"] = "nothing further for this run"
            release_lease(doc, RUNLEASE, runId)

        self._mutateRun(runId, apply, message="steward full settle")

    def _setStatus(self, runId: str, status: str, nextAction: str) -> None:
        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            if run["status"] in OPENRUNSTATES:
                run["status"] = status
                run["nextAction"] = nextAction

        self._mutateRun(runId, apply, message=f"steward full {status}")

    def _markAwaiting(self, runId: str) -> None:
        run = self._loadRun(runId)
        pending = self._pending(run)
        if not pending or run["status"] not in OPENRUNSTATES:
            return
        self._setStatus(
            runId, "awaiting-action",
            f"perform {len(pending)} pending action(s) ({', '.join(sorted({a['type'] for a in pending}))}), "
            f"record each with `gaia steward full record {runId} <stepId> --input FILE`, then "
            f"`gaia steward full run --resume {runId}`",
        )

    @staticmethod
    def _observationOf(run: Mapping[str, Any]) -> dict[str, Any]:
        phases = run["phases"]
        for name in ("reobserve", "observe"):
            if name in phases:
                return phases[name]
        retro = phases.get("retro")
        if retro:
            return {"coverageUnknown": retro.get("unknown", []), "notEvaluated": retro.get("notEvaluated", [])}
        return {}

    def status(self) -> StatusView:
        doc = self._load()
        now = self._now()
        held = leaseHolder(doc, RUNLEASE, now)
        holderRun = doc["runs"].get(held, {}) if held else {}
        counts: dict[str, int] = {}
        for item in doc["work"].values():
            counts[item["state"]] = counts.get(item["state"], 0) + 1
        lane = None
        try:
            policy = self._policyLoaded()
            lane = load_lane(doc["lane"], policy.lane).summary()
        except Exception:  # noqa: BLE001 - status is read-only and must not fail on policy
            lane = None
        runs = sorted(doc["runs"].values(), key=lambda value: value["startedAt"], reverse=True)
        scheduled = [r["startedAt"] for r in runs if r.get("trigger") == "scheduled" and r.get("status") != "abandoned"]
        return StatusView(
            ledger=self._ledgerInfo(),
            holder=held,
            holderPhase=holderRun.get("phase"),
            holderExpiresAt=doc["leases"][RUNLEASE]["expiresAt"] if held else None,
            activeRuns=[
                {"runId": r["runId"], "mode": r["mode"], "phase": r["phase"], "status": r["status"]}
                for r in runs if r["status"] in OPENRUNSTATES
            ],
            workCounts=dict(sorted(counts.items())),
            work=[
                {"debtId": i["debtId"], "state": i["state"], "authority": i.get("authority"),
                 "branch": i.get("branch"), "runId": i.get("runId")}
                for i in sorted(doc["work"].values(), key=lambda value: value["debtId"])
            ],
            lane=lane,
            lastScheduledRunAt=max(scheduled) if scheduled else None,
            recentRuns=[
                {"runId": r["runId"], "mode": r["mode"], "status": r["status"], "startedAt": r["startedAt"]}
                for r in runs[:10]
            ],
        )

    # ------------------------------------------------------------------
    # record(): driver outcomes
    # ------------------------------------------------------------------

    def record(self, runId: str, stepId: str, outcome: Mapping[str, Any]) -> RunView:
        if not isinstance(outcome, Mapping):
            raise RecordRefused("outcome must be a JSON object")
        outcome = copy.deepcopy(dict(outcome))
        run = self._load()["runs"].get(runId)
        if run is None:
            raise UnknownRun(f"unknown run {runId}")
        action = next((a for a in run["actions"] if a["stepId"] == stepId), None)
        if action is None:
            raise RecordRefused(f"run {runId} has no action with step id {stepId!r}")
        handlers = {
            "agent.build": self._recordBuild,
            "agent.verify": self._recordVerify,
            "forge.open_pr": self._recordPullRequest,
            "lead.integrate": self._recordIntegrate,
        }
        handler = handlers.get(action["type"])
        if handler is None:
            raise RecordRefused(f"this runner does not take outcomes for {action['type']}")
        prepared = handler(runId, action, outcome)  # validates, returns the mutation
        return self._applyRecord(runId, stepId, action, outcome, prepared)

    def _applyRecord(
        self, runId: str, stepId: str, action: dict[str, Any], outcome: dict[str, Any],
        prepared: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None],
    ) -> RunView:
        normalized = stable_json(outcome)

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> str:
            live = next((a for a in run["actions"] if a["stepId"] == stepId), None)
            if live is None:
                raise RecordRefused(f"run {runId} has no action with step id {stepId!r}")
            if live["status"] != "pending":
                if live["status"] == "done" and stable_json(live.get("outcome")) == normalized:
                    return "repeat"
                raise RecordRefused(
                    f"step {stepId} is already {live['status']}; a different outcome cannot replace it"
                )
            now = self._now()
            prepared(doc, run, live)
            live["status"] = "done" if live.get("heldOnly") is not True else "held"
            live["outcome"] = outcome
            live["recordedAt"] = now
            for step in run["steps"]:
                if step["stepId"] == stepId:
                    step["status"] = "done"
                    step["at"] = now
            run["mutated"] = True
            run["updatedAt"] = now
            return "recorded"

        # Recording is data from a driver, not a phase of ours: it does not need
        # (and must not fight over) the run lease.
        self._mutateRun(runId, apply, holdsLease=False, message=f"steward full record {stepId}")
        view = self._view(self._load(), runId)
        if view.status in OPENRUNSTATES or view.status == "awaiting-action":
            view.nextAction = f"outcome recorded; resume with `gaia steward full run --resume {runId}`"
        return view

    # -- agent.build -----------------------------------------------------

    def _recordBuild(self, runId: str, action: dict[str, Any], outcome: dict[str, Any]) -> Callable:
        validateAgent(outcome, BUILDERMODELS, "builder")
        noChange = outcome.get("noChange")
        if not isinstance(noChange, bool):
            raise RecordRefused("builder outcome needs a boolean noChange")
        summary = outcome.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise RecordRefused("builder outcome needs a non-empty summary")
        if not noChange:
            for key in ("diffPath", "proofPath"):
                value = outcome.get(key)
                if not isinstance(value, str) or not value.strip():
                    raise RecordRefused(f"builder outcome with noChange false needs {key}")
                path = self._resolvePath(value)
                if not path.is_file():
                    raise RecordRefused(f"{key} {value!r} is not a file")
            if not self._resolvePath(outcome["diffPath"]).read_bytes().strip():
                raise RecordRefused("diffPath is empty; a build that changed nothing must set noChange true")
        debtId = action["debtId"]
        params = action["params"]

        def prepared(doc: dict[str, Any], run: dict[str, Any], live: dict[str, Any]) -> None:
            item = doc["work"].get(debtId)
            if item is None or item["state"] != "building":
                raise RecordRefused(f"work for {debtId} is not building; refusing the build outcome")
            if item.get("dispatchId") != params["dispatchId"]:
                raise RecordRefused("build outcome belongs to a different dispatch than the work item holds")
            if item.get("build") and item["build"].get("dispatchId") == params["dispatchId"]:
                raise RecordRefused("a build outcome is already recorded for this dispatch")
            now = self._now()
            self._noteAgent(doc, run, debtId, "builder", live["stepId"], outcome, now)
            item["build"] = {
                "dispatchId": params["dispatchId"], "noChange": noChange,
                "diffPath": str(self._resolvePath(outcome["diffPath"])) if outcome.get("diffPath") else None,
                "proofPath": str(self._resolvePath(outcome["proofPath"])) if outcome.get("proofPath") else None,
                "summary": summary, "agentId": outcome["agentId"], "recordedAt": now,
            }
            item["verification"] = None
            item["updatedAt"] = now
            if outcome.get("proofPath"):
                run["proofArtifacts"].append({"debtId": debtId, "stepId": live["stepId"],
                                              "diffPath": item["build"]["diffPath"], "proofPath": item["build"]["proofPath"]})

        return prepared

    def _noteAgent(
        self, doc: dict[str, Any], run: dict[str, Any], debtId: str, role: str, stepId: str,
        outcome: Mapping[str, Any], now: str,
    ) -> None:
        entry = {
            "role": role, "agentId": outcome["agentId"], "model": outcome["model"],
            "effort": outcome["effort"], "tokensIn": outcome.get("tokensIn"),
            "tokensOut": outcome.get("tokensOut"), "costUsd": outcome.get("costUsd"),
        }
        doc["work"][debtId].setdefault("assignments", []).append(dict(entry, stepId=stepId, at=now))
        run["agentAssignments"].append(dict(entry, debtId=debtId, stepId=stepId, at=now))
        run["modelIds"] = sorted(set(run["modelIds"]) | {entry["model"]})
        run["thinkingEfforts"] = sorted(set(run["thinkingEfforts"]) | {entry["effort"]})
        run["tokensIn"] += entry["tokensIn"] or 0
        run["tokensOut"] += entry["tokensOut"] or 0
        run["costUsd"] = round(run["costUsd"] + (entry["costUsd"] or 0.0), 6)

    # -- agent.verify ----------------------------------------------------

    def _recordVerify(self, runId: str, action: dict[str, Any], outcome: dict[str, Any]) -> Callable:
        validateAgent(outcome, VERIFIERMODELS, "verifier")
        verdict = outcome.get("verdict")
        if verdict not in {"accept", "reject", "escalate"}:
            raise RecordRefused("verifier verdict must be accept, reject, or escalate")
        rationale = outcome.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise RecordRefused("verifier outcome needs a non-empty rationale")
        debtId = action["debtId"]
        policy = self._policyLoaded()

        def prepared(doc: dict[str, Any], run: dict[str, Any], live: dict[str, Any]) -> None:
            item = doc["work"].get(debtId)
            if item is None or item["state"] != "building" or not item.get("build"):
                raise RecordRefused(f"work for {debtId} is not awaiting verification")
            builders = {a["agentId"] for a in item.get("assignments", []) if a["role"] == "builder"}
            builders |= set(action["params"].get("forbiddenAgentIds", []))
            if outcome["agentId"] in builders:
                raise RecordRefused(
                    f"verifier {outcome['agentId']!r} built this work; verification must be independent"
                )
            now = self._now()
            lane = load_lane(doc["lane"], policy.lane)
            if lane.by_id(debtId) is None:
                raise RecordRefused(f"the shared lane is not tracking {debtId}")
            note = f"independent verification by {outcome['agentId']} ({outcome['model']}, effort {outcome['effort']})"
            try:
                lane = record_verdict(lane, debtId, verdict, now=now, note=note)
            except LaneError as exc:
                raise RecordRefused(f"the lane refused the verdict: {exc}") from exc
            set_lane(doc, lane_document(lane))
            self._noteAgent(doc, run, debtId, "verifier", live["stepId"], outcome, now)
            item["verification"] = {
                "stage": "judged", "verdict": verdict, "rationale": rationale,
                "agentId": outcome["agentId"], "recordedAt": now,
            }
            escalated = lane.by_id(debtId).state == "escalated"
            if verdict == "accept":
                if item["build"]["noChange"]:
                    self._setState(doc, debtId, "no_change", now, f"{note}: finding does not reproduce")
                else:
                    self._setState(doc, debtId, "verified", now, note)
                    self._emitIntegrate(run, item, now)
            elif escalated or verdict == "escalate":
                self._setState(doc, debtId, "escalated", now, f"{note}: {verdict}")
            else:
                item["build"] = None
                self._setState(doc, debtId, "blocked", now, f"{note}: rejected - {rationale[:160]}")
            item["updatedAt"] = now

        return prepared

    # -- forge.open_pr ---------------------------------------------------

    def _recordPullRequest(self, runId: str, action: dict[str, Any], outcome: dict[str, Any]) -> Callable:
        pr = outcome.get("pullRequest")
        if not isinstance(pr, Mapping) or not (pr.get("number") or pr.get("url")):
            raise RecordRefused("forge.open_pr outcome needs pullRequest with a number or url")
        merged = outcome.get("merged", False)
        if not isinstance(merged, bool):
            raise RecordRefused("merged must be a boolean")
        if merged and not isinstance(outcome.get("mergedSha"), str):
            raise RecordRefused("a merged pull request needs mergedSha")
        debtId = action["debtId"]

        def prepared(doc: dict[str, Any], run: dict[str, Any], live: dict[str, Any]) -> None:
            item = doc["work"].get(debtId)
            if item is None:
                raise RecordRefused(f"no work item for {debtId}")
            item["pullRequest"] = dict(pr)
            if merged:
                item["mergedSha"] = outcome["mergedSha"]
            item["updatedAt"] = self._now()
            run["pullRequests"].append(dict(pr, debtId=debtId, merged=merged))

        return prepared

    # -- lead.integrate --------------------------------------------------

    def _recordIntegrate(self, runId: str, action: dict[str, Any], outcome: dict[str, Any]) -> Callable:
        decision = outcome.get("decision")
        if decision not in {"integrate", "hold", "reject"}:
            raise RecordRefused("lead.integrate decision must be integrate, hold, or reject")
        by = outcome.get("by")
        if not isinstance(by, str) or not by.strip():
            raise RecordRefused("lead.integrate outcome needs by (who decided)")
        debtId = action["debtId"]

        def prepared(doc: dict[str, Any], run: dict[str, Any], live: dict[str, Any]) -> None:
            item = doc["work"].get(debtId)
            if item is None or item["state"] != "verified":
                raise RecordRefused(f"work for {debtId} is not verified; nothing to integrate")
            now = self._now()
            run["decisions"].append({"type": "integrate", "debtId": debtId, "decision": decision, "by": by, "at": now})
            if decision == "integrate":
                if outcome.get("pullRequest"):
                    item["pullRequest"] = dict(outcome["pullRequest"])
                    run["pullRequests"].append(dict(outcome["pullRequest"], debtId=debtId, merged=True))
                if outcome.get("mergedSha"):
                    item["mergedSha"] = outcome["mergedSha"]
                self._setState(doc, debtId, "landed", now, f"integrated by {by}")
            elif decision == "reject":
                self._setState(doc, debtId, "blocked", now, f"integration rejected by {by}")
            else:
                live["heldOnly"] = True
                self._note(item, now, f"integration held by {by}")
            item["updatedAt"] = now

        return prepared

    # ------------------------------------------------------------------
    # work item and run record mutation helpers (pure, inside `update`)
    # ------------------------------------------------------------------

    @staticmethod
    def _note(item: dict[str, Any], now: str, text: str) -> None:
        notes = item.setdefault("notes", [])
        if notes and notes[-1]["note"] == text:
            return
        notes.append({"at": now, "note": text})
        del notes[:-8]

    @staticmethod
    def _setState(doc: dict[str, Any], debtId: str, to: str, now: str, reason: str) -> None:
        item = doc["work"][debtId]
        if item["state"] == to:
            FullRunner._note(item, now, reason)
            return
        transition_work(doc, debtId, to, now, reason)
        item["updatedAt"] = now

    def _ensureWork(self, doc: dict[str, Any], run: dict[str, Any], debt: Debt, now: str, **fields: Any) -> dict[str, Any]:
        base = {
            "debtId": debt.id, "kind": debt.kind, "authority": debt.authority.value,
            "source": debt.source, "runId": run["runId"], "updatedAt": now,
        }
        base.update(fields)
        if debt.id in doc["work"]:
            return upsert_work(doc, base)
        base.update({"state": "queued", "assignments": [], "createdAt": now, "notes": [],
                     "build": None, "verification": None, "pullRequest": None})
        return upsert_work(doc, base)

    def _addStep(self, run: dict[str, Any], step: dict[str, Any]) -> None:
        for existing in run["steps"]:
            if existing["stepId"] == step["stepId"]:
                existing.update(step)
                return
        run["steps"].append(step)

    @staticmethod
    def _stepStatus(run: dict[str, Any], stepId: str) -> str | None:
        for step in run["steps"]:
            if step["stepId"] == stepId:
                return step["status"]
        return None

    def _addAction(self, run: dict[str, Any], stepId: str, kind: str, debtId: str, key: str,
                   params: dict[str, Any], now: str) -> bool:
        """Emit an action once. Returns False when this run already has it."""

        if any(a["stepId"] == stepId for a in run["actions"]):
            return False
        run["actions"].append({
            "stepId": stepId, "type": kind, "debtId": debtId, "idempotencyKey": key,
            "status": "pending", "emittedAt": now, "params": params,
        })
        self._addStep(run, {"stepId": stepId, "kind": kind, "status": "awaiting",
                            "idempotencyKey": key, "debtId": debtId, "at": now})
        return True

    @staticmethod
    def _pending(run: dict[str, Any], kind: str | None = None) -> list[dict[str, Any]]:
        return [a for a in run["actions"] if a["status"] == "pending" and (kind is None or a["type"] == kind)]

    def _emitIntegrate(self, run: dict[str, Any], item: dict[str, Any], now: str) -> None:
        build = item.get("build") or {}
        stepId = f"integrate:{_hash12(item['debtId'])}:{item.get('dispatchId', '')[-8:]}"
        self._addAction(
            run, stepId, "lead.integrate", item["debtId"], f"integrate:{item.get('dispatchId')}",
            {"debtId": item["debtId"], "branch": item.get("branch"), "base": run.get("integrationBranch"),
             "diffPath": build.get("diffPath")}, now,
        )

    @staticmethod
    def _compact(doc: dict[str, Any]) -> None:
        """Bound ledger growth: old terminal runs keep their summary, not their detail."""

        terminal = sorted(
            (r for r in doc["runs"].values() if r.get("status") in TERMINALRUNSTATES),
            key=lambda value: value["startedAt"], reverse=True,
        )
        for run in terminal[RETAINEDRUNS:]:
            for key in ("steps", "actions", "phases", "proofArtifacts", "ciResults", "agentAssignments"):
                if run.get(key):
                    run[key] = []
            run["compacted"] = True

    def _failRun(self, runId: str, reason: str) -> None:
        now = self._now()

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            run["status"] = "failed"
            run["error"] = reason
            run["finishedAt"] = now
            run["nextAction"] = f"run failed: {reason}"
            release_lease(doc, RUNLEASE, runId)

        try:
            self._mutateRun(runId, apply, holdsLease=False, message="steward full failed")
        except LeaseLost:
            pass

    # ------------------------------------------------------------------
    # view
    # ------------------------------------------------------------------

    def _view(self, doc: dict[str, Any], runId: str) -> RunView:
        run = doc["runs"].get(runId)
        if run is None:
            raise UnknownRun(f"unknown run {runId}")
        observe = self._observationOf(run)
        return RunView(
            runId=runId, mode=run["mode"], status=run["status"], phase=run["phase"],
            nextAction=run.get("nextAction", ""),
            actions=copy.deepcopy(self._pending(run)),
            summary=copy.deepcopy(run["phases"]),
            unresolvedWork=copy.deepcopy(run["unresolvedWork"]),
            coverageUnknown=list(observe.get("coverageUnknown", [])),
            notEvaluated=copy.deepcopy(observe.get("notEvaluated", [])),
            desk=copy.deepcopy(run.get("desk")),
            ledger=self._ledgerInfo(),
            error=run.get("error"),
        )

    # ------------------------------------------------------------------
    # phase plumbing
    # ------------------------------------------------------------------

    def _finish(self, runId: str, phase: str, summary: dict[str, Any] | None = None,
                updates: Callable[[dict[str, Any], dict[str, Any]], None] | None = None) -> bool:
        """Commit a phase's results and the move to the next phase atomically."""

        now = self._now()

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            if run["phase"] != phase:
                return  # a replayed phase that already committed
            if summary is not None:
                run["phases"][phase] = summary
            if updates is not None:
                updates(doc, run)
            self._addStep(run, {"stepId": f"phase:{phase}", "kind": "phase", "status": "done", "at": now})
            order = MODEPHASES[run["mode"]]
            index = order.index(phase) + 1
            run["phase"] = order[index] if index < len(order) else "done"

        self._mutateRun(runId, apply, message=f"steward full {phase}")
        return True

    def _scanFor(self, runId: str) -> ScanResult:
        if runId not in self._scans:
            self._scans[runId] = self._controllerInstance().scan(self.root)
        return self._scans[runId]

    # ------------------------------------------------------------------
    # phases
    # ------------------------------------------------------------------

    def _phaseReconcile(self, runId: str) -> bool:
        sourceHead = self._git("rev-parse", "HEAD")
        source = sourceHead.stdout.strip() if sourceHead.returncode == 0 else "unknown"
        branch = self.config.integration_branch
        integration, reason = "unknown", None
        if not branch:
            reason = "integration branch not configured"
        else:
            refspec = f"+refs/heads/{branch}:refs/remotes/{self.config.remote}/{branch}"
            fetched = self._git("fetch", "--quiet", self.config.remote, refspec)
            if fetched.returncode != 0:
                reason = f"cannot fetch {self.config.remote}/{branch}: {(fetched.stderr or '').strip()[-160:]}"
            else:
                head = self._git("rev-parse", "--verify", f"refs/remotes/{self.config.remote}/{branch}^{{commit}}")
                if head.returncode == 0:
                    integration = head.stdout.strip()
                else:
                    reason = f"{self.config.remote}/{branch} did not resolve after fetch"
        doc = self._load()
        run = doc["runs"][runId]
        followUp = [e for e in run["unresolvedWork"] if doc["work"].get(e["debtId"], {}).get("state") in ACTIVEWORK]
        summary = {
            "sourceHead": source, "integrationHead": integration, "integrationBranch": branch,
            "unresolvedWork": len(followUp),
        }
        if reason:
            summary["integrationHeadUnknown"] = reason

        def updates(_doc: dict[str, Any], record: dict[str, Any]) -> None:
            record["sourceHead"] = source
            record["integrationHead"] = integration
            record["unresolvedWork"] = followUp

        return self._finish(runId, "reconcile", summary, updates)

    @staticmethod
    def _normNotEvaluated(raw: Sequence[Any]) -> list[dict[str, Any]]:
        result = []
        for item in raw or ():
            if isinstance(item, Mapping):
                result.append({"sensor": str(item.get("sensor")), "reason": str(item.get("reason", ""))})
            elif hasattr(item, "sensor"):
                result.append({"sensor": str(item.sensor), "reason": str(getattr(item, "reason", ""))})
            else:
                sensor, _, reason = item if isinstance(item, tuple) and len(item) == 3 else (item[0], None, item[1])
                result.append({"sensor": str(sensor), "reason": str(reason)})
        return sorted(result, key=lambda value: value["sensor"])

    def _observationSummary(self, scan: ScanResult) -> dict[str, Any]:
        bySensor: dict[str, dict[str, int]] = {}
        for observation in scan.observations:
            if observation.kind == "sensor_coverage_unknown":
                continue
            counts = bySensor.setdefault(observation.source, {"drift": 0, "healthy": 0})
            counts[observation.status] += 1
        receipt = scan.receipt
        notEvaluated = self._normNotEvaluated(getattr(receipt, "not_evaluated", ()))
        fresh = sorted(scan.fresh_open_debt_ids & {d.id for d in scan.open_debts})
        return {
            "scanReceiptId": receipt.run_id,
            "observations": receipt.observations_collected,
            "openDebt": len(receipt.open_debt),
            "openDebtIds": list(receipt.open_debt),
            "freshOpenDebt": fresh,
            "created": len(receipt.debt_created),
            "resolved": list(receipt.debt_resolved),
            "authorityCounts": dict(receipt.authority_counts),
            "coverageUnknown": list(receipt.coverage_unknown),
            "notEvaluated": notEvaluated,
            "observationsBySensor": dict(sorted(bySensor.items())),
        }

    def _phaseObserve(self, runId: str) -> bool:
        scan = self._controllerInstance().scan(self.root)
        self._scans[runId] = scan
        summary = self._observationSummary(scan)
        receiptId = summary["scanReceiptId"]

        def updates(_doc: dict[str, Any], run: dict[str, Any]) -> None:
            run["receipts"].append({"kind": "scan", "id": receiptId})

        return self._finish(runId, "observe", summary, updates)

    # -- triage ----------------------------------------------------------

    def _routineBindings(self) -> dict[int, dict[str, set[str]]]:
        path = self.root / "founder/steward/routine-coverage.json"
        table: dict[int, dict[str, set[str]]] = {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return table
        for routine in data.get("routines", []):
            entry = table.setdefault(int(routine["number"]), {"sensors": set(), "kinds": set()})
            for binding in routine.get("bindings", []):
                if binding.get("sensorId"):
                    entry["sensors"].add(binding["sensorId"])
                if binding.get("debtKind"):
                    entry["kinds"].add(binding["debtKind"])
        return table

    def _routinesFor(self, debt: Debt) -> set[int]:
        found: set[int] = set()
        for sensor in self._controllerInstance().sensors:
            if sensor.id == debt.source:
                found |= {int(n) for n in getattr(sensor, "routine_ids", ())}
        for number, entry in self._routineBindings().items():
            if debt.source in entry["sensors"] or debt.kind in entry["kinds"]:
                found.add(number)
        return found

    def _triageSets(self, scan: ScanResult, run: dict[str, Any], work: Mapping[str, Any]) -> dict[str, Any]:
        policy = self._policyLoaded()
        options = run["options"]
        routine, only = options.get("routine"), options.get("debt")
        freshIds = scan.fresh_open_debt_ids
        fresh = sorted((d for d in scan.open_debts if d.id in freshIds), key=lambda d: (-d.priority.score, d.id))
        result: dict[str, Any] = {
            "classA": [], "classB": [], "reportOnly": [], "classC": [],
            "skippedActive": [], "held": [], "filtered": 0,
            "carried": len(scan.open_debts) - len(fresh),
        }
        debts: dict[str, Debt] = {}
        for debt in fresh:
            if only and debt.id != only:
                result["filtered"] += 1
                continue
            if routine and int(routine) not in self._routinesFor(debt):
                result["filtered"] += 1
                continue
            state = work.get(debt.id, {}).get("state")
            if state in HELDWORK:
                result["held"].append(debt.id)
                continue
            if state in ACTIVEWORK:
                result["skippedActive"].append(debt.id)
                continue
            debts[debt.id] = debt
            if debt.authority is AuthorityClass.A and policy.executor_for(debt.kind) is not None:
                result["classA"].append(debt.id)
            elif debt.authority is AuthorityClass.B and policy.dispatch_rule_for(debt.kind) is not None:
                result["classB"].append(debt.id)
            elif debt.authority is AuthorityClass.C:
                result["classC"].append(debt.id)
            else:
                result["reportOnly"].append(debt.id)
        result["debts"] = debts
        return result

    def _phaseTriage(self, runId: str) -> bool:
        scan = self._scanFor(runId)
        doc = self._load()
        sets = self._triageSets(scan, doc["runs"][runId], doc["work"])
        summary = {key: value for key, value in sets.items() if key != "debts"}
        summary["counts"] = {
            "A": len(sets["classA"]), "B": len(sets["classB"]),
            "B-report-only": len(sets["reportOnly"]), "C": len(sets["classC"]),
        }
        return self._finish(runId, "triage", summary)

    # -- class A ---------------------------------------------------------

    def _blockedByCoverage(self, scan: ScanResult) -> list[str]:
        return list(scan.receipt.coverage_unknown)

    def _phaseClassA(self, runId: str) -> bool:
        from gaia_cli.steward.landing import LandingError, execute_class_a_landing, plan_class_a_landing

        scan = self._scanFor(runId)
        policy = self._policyLoaded()
        unknown = self._blockedByCoverage(scan)
        if unknown:
            summary = {"status": "blocked", "reason": "sensor coverage is unknown; refusing Class A landing",
                       "coverageUnknown": unknown}

            def refuse(_doc: dict[str, Any], run: dict[str, Any]) -> None:
                run["coverageBlocked"] = True

            return self._finish(runId, "class_a", summary, refuse)

        doc = self._load()
        run = doc["runs"][runId]
        sets = self._triageSets(scan, run, doc["work"])
        branch = self.config.integration_branch
        pushing = bool(run["options"]["push"])
        outcomes: list[dict[str, Any]] = []
        landings = sum(1 for s in run["steps"] if s["kind"] == "landing")

        # Adoption: a proposed Class A branch with no PR action in this run.
        for item in sorted(doc["work"].values(), key=lambda value: value["debtId"]):
            if (item["state"] == "proposed" and item.get("authority") == "A" and item.get("pushed")
                    and not item.get("pullRequest") and branch):
                self._emitPullRequestAction(runId, item, branch)
                outcomes.append({"debtId": item["debtId"], "result": "adopted", "branch": item.get("branch")})

        for debtId in sets["classA"]:
            debt = sets["debts"][debtId]
            if not branch:
                self._blockWork(runId, debt, "landing target not configured",
                                decision={"type": "landing-target", "debtId": debtId,
                                          "question": "Choose the integration branch Class A repairs land on "
                                                      "(--integration-branch or GAIA_STEWARD_INTEGRATION_BRANCH)."})
                outcomes.append({"debtId": debtId, "result": "blocked", "reason": "landing target not configured"})
                continue
            if landings >= policy.max_repairs_per_run:
                outcomes.append({"debtId": debtId, "result": "deferred", "reason": "policy repair budget for this run is exhausted"})
                continue
            try:
                plan = plan_class_a_landing(self.root, policy, debt, base_branch=branch, remote=self.config.remote)
            except LandingError as exc:
                self._blockWork(runId, debt, f"landing refused: {exc}")
                outcomes.append({"debtId": debtId, "result": "blocked", "reason": str(exc)})
                continue
            stepId = f"landing:{plan.branch}"
            if self._stepStatus(self._loadRun(runId), stepId) == "done":
                continue
            landings += 1
            self._recordIntent(runId, debt, plan, stepId)
            _checkpoint("class_a.intent")
            try:
                result = execute_class_a_landing(self.root, policy, plan, push=pushing)
            except LandingError as exc:
                self._failLanding(runId, debt, stepId, f"landing refused: {exc}")
                outcomes.append({"debtId": debtId, "result": "blocked", "reason": str(exc)})
                continue
            _checkpoint("class_a.executed")
            outcomes.append(self._confirmLanding(runId, debt, plan, stepId, result, pushing, branch))
        summary = {"status": "ok", "landings": outcomes}
        return self._finish(runId, "class_a", summary)

    def _blockWork(self, runId: str, debt: Debt, reason: str, decision: dict[str, Any] | None = None) -> None:
        now = self._now()

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            self._ensureWork(doc, run, debt, now, routine=self._routineLabel(debt))
            self._setState(doc, debt.id, "blocked", now, reason)
            if decision and decision not in run["decisions"]:
                run["decisions"].append(decision)

        self._mutateRun(runId, apply, message="steward full blocked")

    def _routineLabel(self, debt: Debt) -> str:
        policy = self._policyLoaded()
        rule = policy.dispatch_rule_for(debt.kind)
        if rule is not None:
            return rule.routine
        executor = policy.executor_for(debt.kind)
        return executor.id if executor is not None else debt.kind

    def _recordIntent(self, runId: str, debt: Debt, plan: Any, stepId: str) -> None:
        now = self._now()

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            self._ensureWork(doc, run, debt, now, routine=self._routineLabel(debt),
                             branch=plan.branch, baseBranch=plan.base_branch, pushed=False)
            if doc["work"][debt.id]["state"] != "queued":
                self._setState(doc, debt.id, "queued", now, f"landing {plan.branch} (re)attempted")
            self._addStep(run, {
                "stepId": stepId, "kind": "landing", "status": "intent", "idempotencyKey": plan.branch,
                "debtId": debt.id, "branch": plan.branch, "base": plan.base_branch, "at": now,
            })

        self._mutateRun(runId, apply, message="steward full class_a intent")

    def _failLanding(self, runId: str, debt: Debt, stepId: str, reason: str) -> None:
        now = self._now()

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            for step in run["steps"]:
                if step["stepId"] == stepId:
                    step.update(status="failed", reason=reason, at=now)
            self._setState(doc, debt.id, "blocked", now, reason)

        self._mutateRun(runId, apply, message="steward full class_a blocked")

    def _emitPullRequestAction(self, runId: str, item: dict[str, Any], base: str) -> None:
        now = self._now()
        bodyPath = self._writePrBody(runId, item)

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            self._addAction(run, f"open_pr:{item['branch']}", "forge.open_pr", item["debtId"], item["branch"], {
                "head": item["branch"], "base": base,
                "title": f"chore(steward): repair {item.get('kind', 'drift')}",
                "bodyPath": bodyPath, "idempotencyKey": item["branch"], "ifExists": "record-existing",
            }, now)

        self._mutateRun(runId, apply, message="steward full open_pr")

    def _writePrBody(self, runId: str, item: dict[str, Any]) -> str:
        path = self._runDirectory(runId) / f"{_hash12(item['branch'])}.pr.md"
        path.write_text(
            f"Gaia Steward Class A mechanical repair of `{item.get('kind')}`.\n\n"
            f"- Debt: `{item['debtId']}`\n- Branch: `{item['branch']}`\n"
            f"- Run: `{runId}`\n\nOpened by the zero-model Steward runner; the diff is the\n"
            "executor's writable path only and parity was proven by the observing sensor.\n",
            encoding="utf-8",
        )
        return self._relative(path)

    def _confirmLanding(self, runId: str, debt: Debt, plan: Any, stepId: str, result: Any,
                        pushing: bool, base: str) -> dict[str, Any]:
        now = self._now()
        status = result.status
        remote = status == "branch-pushed" or (status == "already-exists" and pushing)
        bodyPath = self._writePrBody(runId, {"kind": debt.kind, "debtId": debt.id, "branch": plan.branch}) if remote else None
        record = {"debtId": debt.id, "result": status, "branch": plan.branch, "commit": result.commit,
                  "reason": result.reason}

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            item = doc["work"][debt.id]
            for step in run["steps"]:
                if step["stepId"] == stepId:
                    step.update(status="done" if status != "blocked" else "failed", at=now, result=result.to_dict())
            if status == "blocked":
                self._setState(doc, debt.id, "blocked", now, result.reason)
                return
            if status == "no_change":
                item["branch"] = None
                self._setState(doc, debt.id, "no_change", now,
                               f"{result.reason}; this checkout lags {base} or already matches canonical")
                return
            item["branchHead"] = result.commit
            item["pushed"] = remote
            self._setState(doc, debt.id, "proposed", now,
                           f"branch {plan.branch} {'pushed' if remote else 'committed locally (not pushed)'}")
            run["branches"].append({"branch": plan.branch, "debtId": debt.id, "commit": result.commit, "pushed": remote})
            run["mutated"] = True
            if remote:
                self._addAction(run, f"open_pr:{plan.branch}", "forge.open_pr", debt.id, plan.branch, {
                    "head": plan.branch, "base": base,
                    "title": f"chore(steward): repair {debt.kind}",
                    "bodyPath": bodyPath, "idempotencyKey": plan.branch, "ifExists": "record-existing",
                }, now)

        self._mutateRun(runId, apply, message="steward full class_a confirmed")
        return record

    # -- class B ---------------------------------------------------------

    def _dispatchView(self, lane: Lane, eligible: set[str]) -> Lane:
        entries = tuple(e for e in lane.entries if e.state != "queued" or e.debt_id in eligible)
        return Lane(entries=entries, policy=lane.policy)

    def _chooseCandidate(self, doc: dict[str, Any], scan: ScanResult, eligible: set[str], now: str) -> tuple[Lane, Any, str]:
        policy = self._policyLoaded()
        lane = load_lane(doc["lane"], policy.lane)
        kinds = {rule.debt_kind: rule.id for rule in policy.dispatch_rules.values()}
        fresh = tuple(d for d in scan.open_debts if d.id in scan.fresh_open_debt_ids)
        lane = reconcile(lane, open_debts=fresh, dispatchable_kinds=kinds, now=now)
        for entry in lane.escalated:
            item = doc["work"].get(entry.debt_id)
            if item is not None and item["state"] not in {"escalated", "resolved"}:
                self._setState(doc, entry.debt_id, "escalated", now, "the shared lane escalated this debt")
        entry, reason = next_dispatchable(self._dispatchView(lane, eligible), now=now)
        return lane, entry, reason

    def _phaseClassB(self, runId: str) -> bool:
        from gaia_cli.steward.routing import RoutingError, render_dispatch_prompt

        run = self._loadRun(runId)
        if self._pending(run, "agent.build"):
            return False
        if not run["options"]["agents"]:
            return self._finish(runId, "class_b", {"status": "skipped", "reason": "agents disabled (--no-agents)"})
        scan = self._scanFor(runId)
        policy = self._policyLoaded()
        unknown = self._blockedByCoverage(scan)
        if unknown:
            def refuse(_doc: dict[str, Any], record: dict[str, Any]) -> None:
                record["coverageBlocked"] = True

            return self._finish(runId, "class_b", {
                "status": "blocked", "reason": "sensor coverage is unknown; refusing Class B dispatch",
                "coverageUnknown": unknown}, refuse)
        builds = sum(1 for s in run["steps"] if s["kind"] == "agent.build")
        if builds >= policy.max_dispatches_per_run:
            return self._finish(runId, "class_b", {
                "status": "ok", "dispatched": None,
                "reason": f"this run already dispatched {builds} (maxDispatchesPerRun {policy.max_dispatches_per_run})"})

        doc = self._load()
        sets = self._triageSets(scan, run, doc["work"])
        eligible = set(sets["classB"])
        now = self._now()

        # Adoption: building work whose build outcome never arrived (abandoned run).
        for item in sorted(doc["work"].values(), key=lambda value: value["debtId"]):
            if item["state"] == "building" and not item.get("build") and item.get("authority") == "B" and item.get("dispatchId"):
                self._reemitBuild(runId, item)
                return False

        lane, candidate, reason = self._chooseCandidate(doc, scan, eligible, now)
        if candidate is None:
            def keepLane(d: dict[str, Any]) -> None:
                _lane, _entry, _reason = self._chooseCandidate(d, scan, eligible, now)
                set_lane(d, lane_document(_lane))

            self._update(keepLane, "steward full lane")
            return self._finish(runId, "class_b", {"status": "ok", "dispatched": None, "reason": reason})

        debt = sets["debts"][candidate.debt_id]
        try:
            result, prompt = render_dispatch_prompt(self.root, debt.id, controller=self._controllerInstance())
        except RoutingError as exc:
            return self._finish(runId, "class_b", {"status": "ok", "dispatched": None,
                                                   "reason": f"dispatch not rendered: {exc}"})
        packet = result.artifact
        rule = policy.dispatch_rule_for(debt.kind)
        assert rule is not None
        slug = _hash12(debt.id)
        promptPath = self._runDirectory(runId) / f"build-{slug}.prompt.md"
        promptPath.write_text(prompt, encoding="utf-8")
        branchName = f"steward/b/{debt.kind.replace('_', '-')}-{slug}"
        attempt = candidate.attempts + 1
        outcome: dict[str, Any] = {}

        def commit(d: dict[str, Any]) -> None:
            outcome.clear()
            laneNow, chosen, why = self._chooseCandidate(d, scan, eligible, now)
            if chosen is None or chosen.debt_id != debt.id:
                set_lane(d, lane_document(laneNow))
                outcome.update(dispatched=None, reason=f"the lane changed during rendering: {why}")
                return
            laneNow = mark_dispatched(laneNow, laneNow.by_id(debt.id), dispatch_id=packet.dispatch_id, now=now)
            set_lane(d, lane_document(laneNow))
            record = d["runs"][runId]
            self._ensureWork(d, record, debt, now, routine=rule.routine, branch=branchName,
                             dispatchId=packet.dispatch_id, promptPath=self._relative(promptPath),
                             baseBranch=self.config.integration_branch, attempt=attempt)
            d["work"][debt.id]["build"] = None
            d["work"][debt.id]["verification"] = None
            self._setState(d, debt.id, "building", now, f"dispatched as {packet.dispatch_id} (attempt {attempt})")
            stepId = f"build:{slug}:{attempt}"
            self._addAction(record, stepId, "agent.build", debt.id, f"{packet.dispatch_id}:{attempt}", {
                "debtId": debt.id, "dispatchId": packet.dispatch_id,
                "promptPath": self._relative(promptPath), "base": self.config.integration_branch,
                "branch": branchName, "allowedModels": list(BUILDERMODELS), "effortRequired": True,
                "outputs": {"diffPath": f".gaia/steward/full/{runId}/build-{slug}.diff",
                            "proofPath": f".gaia/steward/full/{runId}/build-{slug}.proof.json"},
            }, now)
            outcome.update(dispatched=debt.id, dispatchId=packet.dispatch_id, stepId=stepId)

        def apply(d: dict[str, Any], record: dict[str, Any]) -> None:
            commit(d)
            record["phases"]["class_b"] = {"status": "awaiting-build", **outcome}
            if outcome.get("dispatched") is None:
                self._addStep(record, {"stepId": "phase:class_b", "kind": "phase", "status": "done", "at": now})
                order = MODEPHASES[record["mode"]]
                record["phase"] = order[order.index("class_b") + 1]

        self._mutateRun(runId, apply, message="steward full class_b dispatch")
        _checkpoint("class_b.dispatched")
        return outcome.get("dispatched") is None

    def _reemitBuild(self, runId: str, item: dict[str, Any]) -> None:
        now = self._now()
        slug = _hash12(item["debtId"])
        promptPath = item.get("promptPath")
        if not promptPath or not (self.root / promptPath).is_file():
            from gaia_cli.steward.routing import RoutingError, render_dispatch_prompt

            try:
                _result, prompt = render_dispatch_prompt(self.root, item["debtId"], controller=self._controllerInstance())
            except RoutingError:
                prompt = None
            if prompt is None:
                return
            path = self._runDirectory(runId) / f"build-{slug}.prompt.md"
            path.write_text(prompt, encoding="utf-8")
            promptPath = self._relative(path)

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            self._addAction(run, f"build:{slug}:{item.get('attempt', 1)}:adopted", "agent.build", item["debtId"],
                            f"{item['dispatchId']}:{item.get('attempt', 1)}", {
                "debtId": item["debtId"], "dispatchId": item["dispatchId"], "promptPath": promptPath,
                "base": self.config.integration_branch, "branch": item.get("branch"),
                "allowedModels": list(BUILDERMODELS), "effortRequired": True,
                "outputs": {"diffPath": f".gaia/steward/full/{runId}/build-{slug}.diff",
                            "proofPath": f".gaia/steward/full/{runId}/build-{slug}.proof.json"},
            }, now)
            run["phases"]["class_b"] = {"status": "awaiting-build", "dispatched": item["debtId"], "adopted": True}
            doc["work"][item["debtId"]]["runId"] = runId

        self._mutateRun(runId, apply, message="steward full class_b adopt")

    # -- verify ----------------------------------------------------------

    def _verifierPromptNoChange(self, item: dict[str, Any], debt: dict[str, Any] | None) -> str:
        evidence = json.dumps(debt or {"id": item["debtId"], "kind": item.get("kind")}, indent=2, sort_keys=True)
        return (
            "# Steward independent verification - no-change claim\n\n"
            "A builder reports that the finding below does **not** reproduce, so it changed nothing.\n"
            "You have not seen the builder's reasoning, on purpose. Independently check, from current\n"
            "repository state, whether the condition the sensor reported is real.\n\n"
            f"Finding:\n\n```json\n{evidence}\n```\n\n"
            "Reply with `accept` (the finding does not reproduce), `reject` (it reproduces; the builder\n"
            "missed it) or `escalate`, plus a rationale citing what you ran and observed.\n"
        )

    def _phaseVerify(self, runId: str) -> bool:
        doc = self._load()
        run = doc["runs"][runId]
        policy = self._policyLoaded()
        deferred: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        for item in sorted(doc["work"].values(), key=lambda value: value["debtId"]):
            debtId = item["debtId"]
            if item.get("authority") != "B":
                continue
            if item["state"] == "verified":
                held = any(a["debtId"] == debtId and a["type"] == "lead.integrate" for a in run["actions"])
                if not held:
                    self._mutateRun(runId, lambda d, r, _i=item: self._emitIntegrate(r, d["work"][_i["debtId"]], self._now()),
                                    message="steward full integrate")
                continue
            if item["state"] != "building" or not item.get("build"):
                continue
            if any(a["debtId"] == debtId and a["type"] == "agent.verify" and a["status"] == "pending" for a in run["actions"]):
                continue
            results.append(self._verifyOne(runId, item, deferred, policy))
        run = self._loadRun(runId)
        if self._pending(run, "agent.verify"):
            self._mutateRun(runId, lambda d, r: r["phases"].__setitem__(
                "verify", {"status": "awaiting-verifier", "results": results, "deferred": deferred}),
                message="steward full verify awaiting")
            return False
        return self._finish(runId, "verify", {"status": "ok", "results": results, "deferred": deferred})

    def _verifyOne(self, runId: str, item: dict[str, Any], deferred: list[dict[str, Any]], policy: StewardPolicy) -> dict[str, Any]:
        from gaia_cli.steward.routing import RoutingError, _latest_dispatch_receipt, render_dispatch, render_verification
        from gaia_cli.steward.models import DispatchPacket
        from gaia_cli.steward.prompt import render_verifier_prompt

        debtId = item["debtId"]
        build = item["build"]
        now = self._now()
        slug = _hash12(debtId)
        if build["noChange"]:
            prompt = self._verifierPromptNoChange(item, None)
            return self._emitVerify(runId, item, prompt, slug, {"verdict": "pending", "mode": "no-change"})
        diff, proof = Path(build["diffPath"]), Path(build["proofPath"])
        if not diff.is_file() or not proof.is_file():
            deferred.append({"debtId": debtId, "reason": "diff or proof file is not present on this machine"})
            return {"debtId": debtId, "result": "deferred"}
        controller = self._controllerInstance()
        try:
            try:
                result, diffText, outputs = render_verification(
                    self.root, debtId, diff_path=diff, proof_path=proof, controller=controller)
            except RoutingError as exc:
                if "no dispatch receipt" not in str(exc):
                    raise
                render_dispatch(self.root, debtId, controller=controller)
                result, diffText, outputs = render_verification(
                    self.root, debtId, diff_path=diff, proof_path=proof, controller=controller)
        except RoutingError as exc:
            deferred.append({"debtId": debtId, "reason": str(exc)})
            return {"debtId": debtId, "result": "deferred"}
        except Exception as exc:  # VerificationError and friends: the evidence itself is bad
            if type(exc).__name__ != "VerificationError":
                raise
            return self._applyMechanical(runId, item, "reject", [f"verification input refused: {exc}"], None)
        verdict = result.artifact
        if verdict.verdict in {"reject", "escalate"}:
            return self._applyMechanical(runId, item, verdict.verdict, list(verdict.reasons), result.receipt.run_id)
        receipts = self.root / policy.state_directory / policy.receipts_directory
        packet = DispatchPacket.from_dict(_latest_dispatch_receipt(receipts, debtId)["artifact"])
        rule = policy.dispatch_rules[packet.rule]
        prompt = render_verifier_prompt(packet, verdict, prompt_guide=rule.prompt_guide, diff_text=diffText,
                                        proof_outputs=outputs, receipt=result.receipt.to_dict())
        return self._emitVerify(runId, item, prompt, slug, {"verdict": "pending", "receipt": result.receipt.run_id})

    def _applyMechanical(self, runId: str, item: dict[str, Any], verdict: str, reasons: list[str], receipt: str | None) -> dict[str, Any]:
        policy = self._policyLoaded()
        debtId = item["debtId"]
        now = self._now()
        result = {"debtId": debtId, "result": f"mechanical-{verdict}", "reasons": reasons}

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            lane = load_lane(doc["lane"], policy.lane)
            entry = lane.by_id(debtId)
            work = doc["work"][debtId]
            note = f"mechanical verification ({receipt or 'input refusal'})"
            escalated = verdict == "escalate"
            if entry is not None and entry.state == "dispatched":
                lane = record_verdict(lane, debtId, verdict, now=now, note=note)
                set_lane(doc, lane_document(lane))
                escalated = lane.by_id(debtId).state == "escalated"
            else:
                self._note(work, now, "shared lane entry is not dispatched; verdict recorded on work only")
            work["verification"] = {"stage": "mechanical", "verdict": verdict, "reasons": reasons, "recordedAt": now}
            if escalated:
                self._setState(doc, debtId, "escalated", now, f"{note}: {'; '.join(reasons)[:200]}")
            else:
                work["build"] = None
                self._setState(doc, debtId, "blocked", now, f"{note}: rejected - {'; '.join(reasons)[:200]}")
            run["mutated"] = True

        self._mutateRun(runId, apply, message="steward full verify mechanical")
        return result

    def _emitVerify(self, runId: str, item: dict[str, Any], prompt: str, slug: str, detail: dict[str, Any]) -> dict[str, Any]:
        debtId = item["debtId"]
        now = self._now()
        path = self._runDirectory(runId) / f"verify-{slug}.prompt.md"
        path.write_text(prompt, encoding="utf-8")
        promptPath = self._relative(path)

        def apply(doc: dict[str, Any], run: dict[str, Any]) -> None:
            work = doc["work"][debtId]
            builders = sorted({a["agentId"] for a in work.get("assignments", []) if a["role"] == "builder"})
            work["verification"] = {"stage": "awaiting-verifier", **detail, "verifierPromptPath": promptPath}
            self._addAction(run, f"verify:{slug}:{work.get('attempt', 1)}", "agent.verify", debtId,
                            f"verify:{work.get('dispatchId')}:{work.get('attempt', 1)}", {
                "debtId": debtId, "verifierPromptPath": promptPath, "forbiddenAgentIds": builders,
                "allowedModels": list(VERIFIERMODELS), "effortRequired": True,
            }, now)

        self._mutateRun(runId, apply, message="steward full verify emit")
        return {"debtId": debtId, "result": "awaiting-verifier", **detail}

    # -- reobserve -------------------------------------------------------

    def _phaseReobserve(self, runId: str) -> bool:
        run = self._loadRun(runId)
        observed = run["phases"].get("observe")
        if observed is not None and not run.get("mutated"):
            summary = dict(observed)
            summary["reused"] = "no state-changing step ran this run; the observe scan is the re-observation"
        else:
            scan = self._controllerInstance().scan(self.root)
            self._scans[runId] = scan
            summary = self._observationSummary(scan)
        openIds = set(summary["openDebtIds"])
        known = not summary["coverageUnknown"]
        policy = self._policyLoaded()
        now = self._now()

        def apply(doc: dict[str, Any], record: dict[str, Any]) -> None:
            if record["phase"] != "reobserve":
                return
            resolvedNow: list[str] = []
            notes: list[dict[str, str]] = []
            lane = load_lane(doc["lane"], policy.lane)
            if lane.entries:
                # Free lane capacity held by debt that is no longer observed.
                set_lane(doc, lane_document(self._closeVanished(lane, openIds, now)))
            for debtId, item in sorted(doc["work"].items()):
                state = item["state"]
                if state == "resolved":
                    continue
                if debtId in openIds:
                    text = None
                    if state == "landed":
                        text = ("landed on the integration branch and this checkout contains it, but the debt is still open"
                                if self._mergedInto(item)
                                else "landed on integration branch; this checkout does not contain it yet")
                    elif state == "proposed" and item.get("authority") == "A":
                        text = ("branch is in this checkout but the debt is still open" if self._mergedInto(item)
                                else "awaiting merge of the proposed branch; debt still open")
                    if text:
                        self._note(item, now, text)
                        notes.append({"debtId": debtId, "note": text})
                    continue
                if not known:
                    text = "debt not open, but sensor coverage is unknown; not claiming resolved"
                    self._note(item, now, text)
                    notes.append({"debtId": debtId, "note": text})
                    continue
                evidence = f"re-observation {summary['scanReceiptId']}: debt no longer open"
                if state in {"landed", "no_change"}:
                    self._setState(doc, debtId, "resolved", now, evidence)
                    resolvedNow.append(debtId)
                elif state == "proposed" and item.get("authority") == "A" and self._mergedInto(item):
                    self._setState(doc, debtId, "resolved", now, evidence + "; proposed branch is in this checkout")
                    resolvedNow.append(debtId)
                else:
                    text = (f"debt no longer open, but work is {state}"
                            + ("; the proposed branch is not in this checkout" if state == "proposed" else "")
                            + "; not claiming resolved")
                    self._note(item, now, text)
                    notes.append({"debtId": debtId, "note": text})
            record["phases"]["reobserve"] = dict(summary, resolvedWork=resolvedNow, notes=notes)
            self._addStep(record, {"stepId": "phase:reobserve", "kind": "phase", "status": "done", "at": now})
            order = MODEPHASES[record["mode"]]
            record["phase"] = order[order.index("reobserve") + 1]

        self._mutateRun(runId, apply, message="steward full reobserve")
        return True

    @staticmethod
    def _closeVanished(lane: Lane, openIds: set[str], now: str) -> Lane:
        for entry in lane.entries:
            if entry.live and entry.debt_id not in openIds:
                lane = lane.replaced(entry.moved(to="closed", at=now, reason="the condition is no longer observed"))
        return lane

    def _mergedInto(self, item: Mapping[str, Any]) -> bool:
        for sha in (item.get("branchHead"), item.get("mergedSha")):
            if sha and self._git("merge-base", "--is-ancestor", sha, "HEAD").returncode == 0:
                return True
        return False

    # -- retro -----------------------------------------------------------

    def _phaseRetro(self, runId: str) -> bool:
        run = self._loadRun(runId)
        observed = run["phases"].get("observe") or run["phases"].get("reobserve")
        if observed is None:
            scan = self._controllerInstance().scan(self.root)
            self._scans[runId] = scan
            observed = self._observationSummary(scan)
        executed = True
        unknown = set(observed["coverageUnknown"])
        notEvaluated = {item["sensor"]: item["reason"] for item in observed["notEvaluated"]}
        counts = observed["observationsBySensor"]
        sensors = []
        for sensor in self._controllerInstance().sensors:
            if sensor.id in unknown:
                state = "unknown"
            elif sensor.id in notEvaluated:
                state = "not-evaluated"
            elif executed:
                state = "executed"
            else:
                state = "not-run"
            entry: dict[str, Any] = {
                "id": sensor.id, "registered": True, "state": state,
                "executed": state == "executed", "unknown": state == "unknown",
                "notEvaluated": state == "not-evaluated",
                "observations": counts.get(sensor.id, {"drift": 0, "healthy": 0}),
                "routine_ids": [int(n) for n in getattr(sensor, "routine_ids", ())],
            }
            if state == "not-evaluated":
                entry["reason"] = notEvaluated[sensor.id]
            sensors.append(entry)
        byId = {entry["id"]: entry for entry in sensors}
        routines = []
        bindings = self._routineBindings()
        for number in range(1, 18):
            ids = {e["id"] for e in sensors if number in e["routine_ids"]} | {
                s for s in bindings.get(number, {"sensors": set()})["sensors"] if s in byId}
            detectors = [{"sensor": s, "state": byId[s]["state"]} for s in sorted(ids)]
            if not detectors:
                state = "no-detector"
            elif any(d["state"] == "executed" for d in detectors):
                state = "observed"
            elif any(d["state"] == "unknown" for d in detectors):
                state = "unknown"
            else:
                state = "not-evaluated"
            routines.append({"routine": number, "state": state, "detectors": detectors})
        summary = {
            "sensors": sensors, "routines": routines,
            "registered": len(sensors), "executed": sum(1 for e in sensors if e["executed"]),
            "unknown": sorted(unknown), "notEvaluated": [{"sensor": k, "reason": v} for k, v in sorted(notEvaluated.items())],
        }

        return self._finish(runId, "retro", summary)

    # -- report ----------------------------------------------------------

    def _phaseReport(self, runId: str) -> bool:
        now = self._now()
        doc = self._load()
        run = doc["runs"][runId]
        desk = self._buildDesk(runId, doc, run, now)

        def apply(d: dict[str, Any], record: dict[str, Any]) -> None:
            if record["phase"] != "report":
                return
            pending = self._pending(record)
            blocked = record.get("coverageBlocked")
            if blocked:
                status = "blocked"
                action = "sensor coverage is unknown; fix the failing sensor(s) and start a new run"
            elif pending:
                status = "awaiting-action"
                action = (f"perform {len(pending)} pending action(s) "
                          f"({', '.join(sorted({a['type'] for a in pending}))}), record each with "
                          f"`gaia steward full record {runId} <stepId> --input FILE`, then "
                          f"`gaia steward full run --resume {runId}`")
            else:
                status = "completed"
                action = "nothing further for this run"
            record["status"] = status
            record["desk"] = desk
            record["nextAction"] = action
            record["finishedAt"] = now
            self._addStep(record, {"stepId": "phase:report", "kind": "phase", "status": "done", "at": now})
            record["phase"] = "done"
            if status != "awaiting-action":
                release_lease(d, RUNLEASE, runId)

        self._mutateRun(runId, apply, message="steward full report")
        return True

    def _founderQueue(self, debts: Sequence[Debt]) -> Any:
        """Group open Class C debt by its founder rule and exact decision target.

        Mirrors `routing.render_founder_queue` without a second scan or receipt.
        A debt whose target cannot be read is left to the desk's per-kind group.
        """

        from gaia_cli.steward.models import FounderDecision, FounderQueue, normalize_decision_target

        policy = self._policyLoaded()
        groups: dict[tuple[str, str], list[Debt]] = {}
        for debt in debts:
            if debt.authority is not AuthorityClass.C:
                continue
            rule = policy.founder_rule_for(debt.kind)
            if rule is None:
                continue
            try:
                target = normalize_decision_target(debt.observed_state.get(rule.decision_target_field))
            except ValueError:
                continue
            groups.setdefault((rule.id, target), []).append(debt)
        decisions = []
        for (ruleId, target), members in sorted(groups.items()):
            ordered = sorted(members, key=lambda item: item.id)
            decisions.append(FounderDecision.create(
                rule=ruleId, decision_target=target, objective=policy.founder_rules[ruleId].objective,
                debt_ids=tuple(d.id for d in ordered),
                evidence=tuple({"debtId": d.id, "source": d.source, "subject": d.subject.to_dict(),
                                "currentState": dict(d.current_state), "observedState": dict(d.observed_state),
                                "lastObservedAt": d.last_observed_at, "confidence": d.confidence} for d in ordered),
            ))
        return FounderQueue.create(tuple(decisions))

    def _buildDesk(self, runId: str, doc: dict[str, Any], run: dict[str, Any], now: str) -> dict[str, Any]:
        from gaia_cli.steward.desk import build_desk, load_decision_records

        scheduled = [r["startedAt"] for r in doc["runs"].values()
                     if r.get("trigger") == "scheduled" and r.get("status") != "abandoned"]
        scan = self._scanFor(runId)
        policy = self._policyLoaded()
        observed = self._observationOf(run)
        records = list(load_decision_records(self.root))
        landing = sorted(i["debtId"] for i in doc["work"].values()
                         if i["state"] == "blocked" and any(
                             n["note"] == "landing target not configured" for n in i.get("notes", [])))
        if landing:
            records.append({
                "schemaVersion": "steward-decision-v1", "id": "landing-target-not-configured", "status": "open",
                "decision": "Choose the integration branch that Class A repairs land on.",
                "whyItMatters": "Without a landing target the runner finds Class A drift but must not repair it; "
                                "it refuses main and the default branch in code, so a dev/* branch is needed.",
                "evidence": [f"{len(landing)} Class A debt(s) blocked: " + ", ".join(landing[:5])],
                "recommended": "Set GAIA_STEWARD_INTEGRATION_BRANCH (or pass --integration-branch) to a dev/* branch.",
                "alternative": "Leave it unset and keep fixing Class A drift by hand.",
                "unblocks": "Automatic Class A landing branches and their pull requests.",
                "links": [],
            })
        failed = [
            {"subject": i["debtId"], "detail": (i.get("notes") or [{"note": "blocked"}])[-1]["note"]}
            for i in sorted(doc["work"].values(), key=lambda value: value["debtId"])
            if i["state"] == "blocked" and i["debtId"] not in landing
        ]
        desk = build_desk(
            open_debts=scan.open_debts,
            founder_queue=self._founderQueue(scan.open_debts),
            lane=load_lane(doc["lane"], policy.lane) if doc["lane"] is not None else None,
            coverage_unknown=observed.get("coverageUnknown", []),
            not_evaluated=observed.get("notEvaluated", []),
            decision_records=records,
            ledger_shared=bool(self.config.store.shared),
            last_scheduled_run_at=max(scheduled) if scheduled else None,
            now=now,
            failed_dispatches=failed,
        )
        return desk.to_dict()
