"""Unit coverage for the Steward Full runner (`gaia_cli.steward.fullrun`).

Every test builds a real fixture repository with a local bare remote in
``tmp_path``; nothing here can reach a real origin or the real ``steward/*``
refs. Sensors are stubs or the real mirror sensors, so a test controls exactly
what the runner observes.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

import pytest

import gaia_cli.steward.fullrun as fullrun
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.fullrun import (
    BUILDERMODELS,
    MODEPHASES,
    VERIFIERMODELS,
    FullRunConfig,
    FullRunError,
    FullRunner,
    RecordRefused,
    UnknownRun,
    validateAgent,
)
from gaia_cli.steward.ledger import FileLedgerStore
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.primitives import SensorUnavailable

REPO_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = "dev/integration"


# --- fixtures and helpers (shared with the scenario and CLI test modules) -----


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def commitAll(root: Path, message: str = "update") -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", message)


def initRepo(root: Path, *, mirrorDrift: bool) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "commit.gpgsign", "false")
    policy = root / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    script = root / "scripts/sync_agent_skill_mirror.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "scripts/sync_agent_skill_mirror.py", script)
    write(root / ".gitignore", ".gaia/\n")
    write(root / ".agents/skills/x/SKILL.md", "# x canonical\n")
    write(root / ".claude/skills/x/SKILL.md", "# x stale\n" if mirrorDrift else "# x canonical\n")
    write(root / "src/app.py", "VALUE = 1\n")
    commitAll(root, "fixture base")
    return root


def makeFixture(tmp_path: Path, *, mirrorDrift: bool = False) -> tuple[Path, Path]:
    """(repo, bare remote). The checkout sits on `main`; `dev/integration` mirrors it."""

    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    repo = initRepo(tmp_path / "repo", mirrorDrift=mirrorDrift)
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "origin", "main")
    git(repo, "remote", "set-head", "origin", "main")
    git(repo, "push", "-q", "origin", f"main:refs/heads/{INTEGRATION}")
    return repo, bare


def cloneOf(bare: Path, destination: Path) -> Path:
    subprocess.run(["git", "clone", "-q", str(bare), str(destination)], check=True)
    git(destination, "config", "user.email", "fixture@example.invalid")
    git(destination, "config", "user.name", "Fixture")
    git(destination, "config", "commit.gpgsign", "false")
    return destination


class StubSensor:
    """A sensor whose findings a test controls. `subjects` may be mutated."""

    resolution_scope = "exhaustive"

    def __init__(self, sensorId: str, kind: str, subjects: Iterable[str] = (), *,
                 routines: Sequence[int] = (), raises: BaseException | None = None,
                 extra: dict[str, Any] | None = None) -> None:
        self.id = sensorId
        self.kind = kind
        self.subjects = list(subjects)
        self.routine_ids = tuple(routines)
        self.raises = raises
        self.extra = extra or {}
        self.healed: list[str] = []
        self.scans = 0

    def heal(self, subject: str) -> None:
        """The condition is fixed: stop reporting drift and report it healthy."""

        if subject in self.subjects:
            self.subjects.remove(subject)
        self.healed.append(subject)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        self.scans += 1
        if self.raises is not None:
            raise self.raises
        healthy = [
            Observation(
                kind=self.kind, subject=Subject("fixture", subject), observed_at=observed_at,
                source=self.id, status="healthy", current_state={"clean": True},
                observed_state={"finding": subject}, confidence=1.0,
            )
            for subject in self.healed
        ]
        return healthy + [
            Observation(
                kind=self.kind, subject=Subject("fixture", subject), observed_at=observed_at,
                source=self.id, status="drift", current_state={"clean": False},
                observed_state={"finding": subject, **self.extra}, confidence=1.0,
            )
            for subject in self.subjects
        ]


class Clock:
    def __init__(self, start: str = "2026-10-20T00:00:00+00:00") -> None:
        self.value = datetime.fromisoformat(start)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs: float) -> None:
        self.value += timedelta(**kwargs)


def makeRunner(repo: Path, store: Any, sensors: Sequence[Any], **overrides: Any) -> FullRunner:
    options: dict[str, Any] = dict(
        repo_root=repo, store=store, integration_branch=INTEGRATION, push=True,
        trigger="scheduled", agents=True, holder="test",
    )
    options.update(overrides)
    config = FullRunConfig(**options)
    config.controller_factory = lambda: StewardController(sensors=tuple(sensors))
    return FullRunner(config)


def fileStore(tmp_path: Path) -> FileLedgerStore:
    return FileLedgerStore(tmp_path / "ledger" / "ledger.json")


def bareBranches(bare: Path) -> list[str]:
    out = git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads")
    return sorted(line for line in out.splitlines() if line)


def actionTypes(view: Any) -> list[str]:
    return [a["type"] for a in view.actions]


def writeBuildArtifacts(repo: Path, name: str = "c1", *, proofExit: int = 0) -> tuple[Path, Path]:
    """A real diff inside the repository-hygiene envelope plus a full proof transcript."""

    diff = repo / ".gaia" / "inputs" / f"{name}.diff"
    proof = repo / ".gaia" / "inputs" / f"{name}.proof.json"
    diff.parent.mkdir(parents=True, exist_ok=True)
    diff.write_text(
        "diff --git a/scripts/fix.py b/scripts/fix.py\n"
        "new file mode 100644\n--- /dev/null\n+++ b/scripts/fix.py\n@@ -0,0 +1 @@\n+print('fixed')\n",
        encoding="utf-8",
    )
    proof.write_text(json.dumps({
        "schemaVersion": "steward-proof-transcript-v1",
        "entries": [
            {"contractIndex": i, "command": f"check {i}", "exitCode": proofExit, "output": f"ok {i}"}
            for i in range(1, 5)
        ],
    }), encoding="utf-8")
    return diff, proof


BUILD = {"agentId": "builder-1", "model": "haiku", "effort": "high",
         "tokensIn": 1200, "tokensOut": 300, "costUsd": 0.01, "noChange": False,
         "summary": "added scripts/fix.py"}
VERIFY = {"agentId": "verifier-1", "model": "sonnet", "effort": "high",
          "verdict": "accept", "rationale": "diff resolves the finding; proof is genuine"}


def drive(runner: FullRunner, view: Any, repo: Path, *, builderId: str = "builder-1",
          verifierId: str = "verifier-1", integrate: str = "integrate", maxRounds: int = 12) -> Any:
    """A cooperative driver: perform every pending action, record it, resume until the run settles."""

    rounds = 0
    while view.actions and rounds < maxRounds:
        rounds += 1
        for action in list(view.actions):
            kind = action["type"]
            if kind == "agent.build":
                diff, proof = writeBuildArtifacts(repo, action["stepId"].replace(":", "_"))
                outcome = {**BUILD, "agentId": builderId, "diffPath": str(diff), "proofPath": str(proof)}
            elif kind == "agent.verify":
                outcome = {**VERIFY, "agentId": verifierId}
            elif kind == "forge.open_pr":
                outcome = {"pullRequest": {"number": 7, "url": "https://example.invalid/pr/7"}}
            elif kind == "lead.integrate":
                outcome = {"decision": integrate, "by": "lead", "mergedSha": "a" * 40}
            else:
                raise AssertionError(kind)
            runner.record(view.runId, action["stepId"], outcome)
        view = runner.resume(view.runId)
    return view


def editLedger(store: Any, change: Any) -> None:
    """Edit the ledger document directly, the way a crashed or concurrent writer could."""

    from gaia_cli.steward.ledger import update

    update(store, change)


def pinMaxInFlight(repo: Path, value: int) -> None:
    """Set the lane's maxInFlight in the fixture's own policy copy (policy allows 1-4).

    The shipped policy may move (it is 2 as of 2026-10-21), so this rewrites whatever
    value the fixture currently carries rather than assuming a particular one. Tests that
    exercise the single-slot cap pin 1; tests that exercise concurrency pin 2.
    """

    path = repo / POLICY_RELATIVE_PATH
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(r"maxInFlight: \d+", f"maxInFlight: {value}", text)
    assert count == 1, "the fixture policy must declare exactly one routing.lane.maxInFlight"
    path.write_text(updated, encoding="utf-8")
    commitAll(repo, f"maxInFlight {value}")


# --- mode to phase mapping (contract section 6) --------------------------------


def test_mode_phase_table_matches_the_contract() -> None:
    assert MODEPHASES["full"] == (
        "recover", "reconcile", "observe", "triage", "class_a", "class_b",
        "verify", "reobserve", "retro", "report",
    )
    assert MODEPHASES["observe"] == ("recover", "reconcile", "observe", "report")
    assert MODEPHASES["triage"] == ("recover", "reconcile", "observe", "triage", "report")
    assert MODEPHASES["verify"] == ("recover", "verify", "reobserve", "report")
    assert MODEPHASES["retro"] == ("recover", "retro", "report")


@pytest.mark.parametrize("mode", sorted(MODEPHASES))
def test_each_mode_executes_exactly_its_phases_in_order(tmp_path: Path, mode: str) -> None:
    repo, _ = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    runner = makeRunner(repo, store, [StubSensor("repository-hygiene", "repository_hygiene")])
    view = runner.start(mode)
    assert view.status == "completed", view.to_dict()
    doc, _version = store.load()
    run = doc["runs"][view.runId]
    done = [s["stepId"].split(":")[1] for s in run["steps"] if s["kind"] == "phase" and s["status"] == "done"]
    assert done == list(MODEPHASES[mode])
    assert run["phase"] == "done"


def test_unknown_mode_is_refused(tmp_path: Path) -> None:
    repo, _ = makeFixture(tmp_path)
    runner = makeRunner(repo, fileStore(tmp_path), [])
    with pytest.raises(fullrun.FullRunError):
        runner.start("everything")


# --- model and effort validation ------------------------------------------------


@pytest.mark.parametrize("effort", ["", "default", "inherit", "DEFAULT", "  "])
def test_effort_must_be_explicit(effort: str) -> None:
    with pytest.raises(RecordRefused, match="effort"):
        validateAgent({**BUILD, "effort": effort}, BUILDERMODELS, "builder")


def test_effort_missing_is_refused() -> None:
    outcome = {k: v for k, v in BUILD.items() if k != "effort"}
    with pytest.raises(RecordRefused, match="effort"):
        validateAgent(outcome, BUILDERMODELS, "builder")


@pytest.mark.parametrize("model", ["gpt-5", "opus", "", None])
def test_model_must_be_in_the_allowed_set(model: Any) -> None:
    with pytest.raises(RecordRefused, match="not permitted"):
        validateAgent({**BUILD, "model": model}, BUILDERMODELS, "builder")


def test_negative_cost_is_refused() -> None:
    with pytest.raises(RecordRefused, match="costUsd"):
        validateAgent({**BUILD, "costUsd": -1}, BUILDERMODELS, "builder")


def test_valid_agent_passes() -> None:
    validateAgent(BUILD, BUILDERMODELS, "builder")


@pytest.mark.parametrize("model", ["copilot", "codex", "pi"])
def test_other_agent_engines_are_accepted_as_builders(model: str) -> None:
    validateAgent({**BUILD, "model": model}, BUILDERMODELS, "builder")


@pytest.mark.parametrize("model", ["copilot", "codex", "pi"])
def test_other_agent_engines_are_accepted_as_verifiers(model: str) -> None:
    validateAgent({**VERIFY, "model": model}, VERIFIERMODELS, "verifier")


def test_haiku_is_not_a_verifier_family() -> None:
    with pytest.raises(RecordRefused, match="not permitted"):
        validateAgent({**VERIFY, "model": "haiku"}, VERIFIERMODELS, "verifier")


@pytest.mark.parametrize("model", ["opus", "gpt5"])
def test_unlisted_families_are_refused_for_builders_and_verifiers(model: str) -> None:
    with pytest.raises(RecordRefused, match="not permitted"):
        validateAgent({**BUILD, "model": model}, BUILDERMODELS, "builder")
    with pytest.raises(RecordRefused, match="not permitted"):
        validateAgent({**VERIFY, "model": model}, VERIFIERMODELS, "verifier")


# --- landing target, idempotency keys, phases ---------------------------------------


def ledgerDoc(store: Any) -> dict[str, Any]:
    document, _version = store.load()
    return document


def test_class_a_is_refused_without_a_landing_target(tmp_path: Path) -> None:
    from gaia_cli.steward.sensors import AgentSkillMirrorSensor

    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    store = fileStore(tmp_path)
    runner = makeRunner(repo, store, [AgentSkillMirrorSensor()], integration_branch=None)

    view = runner.start("full")

    assert view.status == "completed" and view.actions == []
    doc = ledgerDoc(store)
    (item,) = doc["work"].values()
    assert item["state"] == "blocked" and item["blockedReason"] == "landing target not configured"
    assert item.get("branch") is None
    assert not [b for b in git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()
                if b.startswith("steward/")]
    assert view.summary["reconcile"]["integrationHead"] == "unknown"
    assert "not configured" in view.summary["reconcile"]["integrationHeadUnknown"]
    assert [d["decisionId"] for d in view.desk["decisions"]] == ["landing-target-not-configured"]


def test_class_a_never_targets_the_default_branch(tmp_path: Path) -> None:
    from gaia_cli.steward.sensors import AgentSkillMirrorSensor

    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    store = fileStore(tmp_path)
    for target in ("main", "master"):
        view = makeRunner(repo, store, [AgentSkillMirrorSensor()], integration_branch=target).start("full")
        assert view.actions == [], view.to_dict()
        (item,) = ledgerDoc(store)["work"].values()
        reason = item["blockedReason"]
        assert item["state"] == "blocked", target
        assert reason.startswith("landing target refused:"), reason
        assert "protected branch" in reason or "default branch" in reason, reason
    assert not [b for b in git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()
                if b.startswith("steward/a/")]


def test_step_ids_and_idempotency_keys_are_deterministic_across_independent_runs(tmp_path: Path) -> None:
    from gaia_cli.steward.sensors import AgentSkillMirrorSensor

    keys = []
    for name in ("one", "two"):
        base = tmp_path / name
        base.mkdir()
        repo, _bare = makeFixture(base, mirrorDrift=True)
        view = makeRunner(repo, fileStore(base), [AgentSkillMirrorSensor()]).start("full")
        (action,) = view.actions
        keys.append((action["stepId"], action["idempotencyKey"], action["params"]["head"]))
    assert keys[0] == keys[1]
    stepId, key, head = keys[0]
    assert stepId == f"open_pr:{head}" and key == head


def test_build_idempotency_key_binds_dispatch_and_attempt(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    view = makeRunner(repo, fileStore(tmp_path), [sensor]).start("full")
    (action,) = view.actions
    assert action["idempotencyKey"] == f"{action['params']['dispatchId']}:1"
    assert action["stepId"].startswith("build:") and action["stepId"].endswith(":1")


def test_second_start_while_leased_does_nothing_at_all(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    holder = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    first = makeRunner(repo, store, [holder]).start("full")
    assert first.status == "awaiting-action"
    before = ledgerDoc(store)
    watcher = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])

    view = makeRunner(repo, store, [watcher]).start("full")

    assert view.status == "observing-existing" and view.holder == first.runId
    assert view.holderPhase == "class_b" and "gaia steward full status" in view.nextAction
    assert watcher.scans == 0
    assert ledgerDoc(store) == before, "not one byte of ledger state changed"


def test_clean_repository_with_no_debt_creates_nothing(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    view = makeRunner(repo, store, [StubSensor("repository-hygiene", "repository_hygiene")]).start("full")
    assert view.status == "completed" and view.actions == [] and view.unresolvedWork == []
    doc = ledgerDoc(store)
    assert doc["work"] == {} and doc["lane"] is not None or doc["lane"] is None
    assert view.summary["triage"]["counts"] == {"A": 0, "B": 0, "B-report-only": 0, "C": 0}
    assert view.summary["class_b"]["dispatched"] is None
    assert view.summary["reobserve"]["reused"].startswith("no state-changing step")


def test_no_agents_flag_means_no_dispatch(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    view = makeRunner(repo, store, [sensor], agents=False).start("full")
    assert view.status == "completed" and view.actions == []
    assert view.summary["class_b"]["status"] == "skipped"
    assert ledgerDoc(store)["work"] == {}


def test_triage_filters_by_debt_and_by_routine(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    hygiene = StubSensor("repository-hygiene", "repository_hygiene", ["a", "b"], routines=(12,))
    mapping = StubSensor("discovery-generic-mapping", "generic_mapping", ["m"], routines=(11,),
                         extra={"decisionTarget": "alpha"})
    sensors = [hygiene, mapping]
    everything = makeRunner(repo, fileStore(tmp_path / "x"), sensors).start("triage")
    assert everything.summary["triage"]["counts"] == {"A": 0, "B": 2, "B-report-only": 0, "C": 1}
    first = everything.summary["triage"]["classB"][0]

    one = makeRunner(repo, fileStore(tmp_path / "y"), sensors).start("triage", debt=first)
    assert one.summary["triage"]["classB"] == [first] and one.summary["triage"]["filtered"] == 2

    eleven = makeRunner(repo, fileStore(tmp_path / "z"), sensors).start("triage", routine=11)
    assert eleven.summary["triage"]["counts"] == {"A": 0, "B": 0, "B-report-only": 0, "C": 1}
    twelve = makeRunner(repo, fileStore(tmp_path / "w"), sensors).start("triage", routine=12)
    assert twelve.summary["triage"]["counts"]["B"] == 2 and twelve.summary["triage"]["counts"]["C"] == 0


def test_triage_order_is_priority_then_id(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["c", "a", "b"])
    ids = makeRunner(repo, fileStore(tmp_path), [sensor]).start("triage").summary["triage"]["classB"]
    assert ids == sorted(ids), "equal-priority debts are ordered by id, deterministically"


def test_not_evaluated_is_reported_without_blocking_anything(tmp_path: Path) -> None:
    from gaia_cli.steward.primitives import SensorNotEvaluated

    repo, _bare = makeFixture(tmp_path, mirrorDrift=True)
    optional = StubSensor("optional-input", "ci_failure", raises=SensorNotEvaluated("no CI history supplied"))
    from gaia_cli.steward.sensors import AgentSkillMirrorSensor

    view = makeRunner(repo, fileStore(tmp_path), [AgentSkillMirrorSensor(), optional]).start("full")

    assert view.status == "awaiting-action", "Class A still proceeds"
    assert view.coverageUnknown == []
    assert view.notEvaluated == [{"sensor": "optional-input", "reason": "no CI history supplied"}]
    assert any(op["kind"] == "not_evaluated" for op in view.desk["operations"])


def test_retro_never_counts_an_unexecuted_sensor_as_healthy(tmp_path: Path) -> None:
    from gaia_cli.steward.primitives import SensorNotEvaluated

    repo, _bare = makeFixture(tmp_path)
    good = StubSensor("good", "repository_hygiene", routines=(12,))
    broken = StubSensor("broken", "registry_integrity_failed", routines=(7,), raises=SensorUnavailable("unreadable"))
    optional = StubSensor("optional", "ci_failure", routines=(13,), raises=SensorNotEvaluated("not supplied"))
    view = makeRunner(repo, fileStore(tmp_path), [good, broken, optional]).start("retro")

    retro = view.summary["retro"]
    states = {s["id"]: s for s in retro["sensors"]}
    assert (states["good"]["state"], states["good"]["executed"]) == ("executed", True)
    assert (states["broken"]["state"], states["broken"]["executed"], states["broken"]["unknown"]) == ("unknown", False, True)
    assert states["optional"]["state"] == "not-evaluated" and states["optional"]["reason"] == "not supplied"
    assert states["broken"]["routine_ids"] == [7] and all(s["registered"] for s in states.values())
    assert retro["registered"] == 3 and retro["executed"] == 1
    byRoutine = {r["routine"]: r for r in retro["routines"]}
    assert len(byRoutine) == 17
    assert byRoutine[12]["state"] == "observed"
    assert byRoutine[7]["state"] == "unknown", "an unknown detector is not coverage"
    assert byRoutine[13]["state"] == "not-evaluated"
    assert byRoutine[2]["state"] == "no-detector"
    assert view.coverageUnknown == ["broken"]


def test_old_terminal_runs_are_compacted_but_keep_their_summary() -> None:
    document = {"runs": {}}
    for index in range(fullrun.RETAINEDRUNS + 3):
        document["runs"][f"run-{index:03d}"] = {
            "runId": f"run-{index:03d}", "status": "completed", "startedAt": f"2026-10-{index % 28 + 1:02d}T00:00:00Z",
            "steps": [{"stepId": "x"}], "actions": [], "phases": {"observe": {"openDebt": 1}}, "mode": "full",
        }
    document["runs"]["run-live"] = {"runId": "run-live", "status": "active", "startedAt": "2026-01-01T00:00:00Z",
                                    "steps": [{"stepId": "x"}], "phases": {}}
    FullRunner._compact(document)
    compacted = [r for r in document["runs"].values() if r.get("compacted")]
    assert len(compacted) == 3 and all(r["steps"] == [] and r["mode"] == "full" for r in compacted)
    assert document["runs"]["run-live"]["steps"] == [{"stepId": "x"}]


def test_status_reports_lease_work_and_last_scheduled_run(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    view = makeRunner(repo, store, [sensor], trigger="scheduled").start("full")

    status = makeRunner(repo, store, [sensor]).status()

    assert status.holder == view.runId and status.holderPhase == "class_b"
    assert status.workCounts == {"building": 1}
    assert status.lastScheduledRunAt is not None
    assert status.activeRuns[0]["status"] == "awaiting-action"
    assert status.ledger["shared"] is False
    assert status.to_dict()["lane"]["counts"]["dispatched"] == 1


def test_an_abandoned_runs_pending_actions_are_superseded_at_adoption(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    first = makeRunner(repo, store, [sensor], clock=clock).start("full")
    old = first.actions[0]
    clock.advance(hours=2)
    second = makeRunner(repo, store, [sensor], clock=clock).start("full")

    doc = ledgerDoc(store)
    assert doc["runs"][first.runId]["status"] == "abandoned"
    assert [a["status"] for a in doc["runs"][first.runId]["actions"]] == ["superseded"]
    # The old step can no longer be recorded against: the adopting run's copy is the live one.
    runner = makeRunner(repo, store, [sensor], clock=clock)
    with pytest.raises(RecordRefused, match="superseded"):
        runner.record(first.runId, old["stepId"], {**BUILD, "noChange": True, "summary": "late but valid"})
    (new,) = second.actions
    assert new["type"] == "agent.build" and new["params"]["dispatchId"] == old["params"]["dispatchId"]
    assert new["params"]["attempt"] == old["params"]["attempt"] == 1

    runner.record(second.runId, new["stepId"], {**BUILD, "noChange": True, "summary": "re-recorded on the live step"})
    resumed = runner.resume(second.runId)
    assert [a["type"] for a in resumed.actions] == ["agent.verify"]


# --- partial coverage, and a missing target that blocks nothing -----------------------------


class PartialSensor(StubSensor):
    """A sensor that completed but could not evaluate some subjects (`SensorScan.skipped`)."""

    def scan_detailed(self, repo_root: Path, observed_at: str) -> Any:
        from gaia_cli.steward.models import SensorScan

        return SensorScan(
            observations=tuple(self.scan(repo_root, observed_at)),
            skipped=({"subjectType": "file", "subjectId": "src/odd.py", "reason": "syntax error"},
                     {"subjectType": "file", "subjectId": "src/odder.py", "reason": "too large"}),
        )


def test_partial_coverage_is_reported_never_healthy_and_does_not_block_class_a(tmp_path: Path) -> None:
    from gaia_cli.steward.sensors import AgentSkillMirrorSensor

    repo, _bare = makeFixture(tmp_path, mirrorDrift=True)
    partial = PartialSensor("code-ish", "repository_hygiene", routines=(1,))

    view = makeRunner(repo, fileStore(tmp_path), [AgentSkillMirrorSensor(), partial]).start("full")

    assert view.status == "awaiting-action" and actionTypes(view) == ["forge.open_pr"], "Class A still lands"
    assert view.coverageUnknown == []
    observed = view.summary["reobserve"]
    assert [p["sensor"] for p in observed["partialCoverage"]] == ["code-ish"]
    assert observed["partialCoverage"][0]["skippedCount"] == 2
    retro = {s["id"]: s for s in view.summary["retro"]["sensors"]}
    assert retro["code-ish"]["state"] == "partially-covered" and retro["code-ish"]["executed"] is False
    assert retro["agent-skill-mirror"]["state"] == "executed"
    routine1 = next(r for r in view.summary["retro"]["routines"] if r["routine"] == 1)
    assert routine1["state"] == "partial", "partial coverage is never reported as observed"
    assert any(op["kind"] == "not_evaluated" and op["subject"] == "code-ish" and "partially covered" in op["detail"]
               for op in view.desk["operations"])


def test_a_clean_repository_without_a_landing_target_asks_the_founder_nothing(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    view = makeRunner(repo, store, [StubSensor("repository-hygiene", "repository_hygiene")],
                      integration_branch=None).start("full")
    assert view.status == "completed" and view.desk["decisions"] == []
    assert ledgerDoc(store)["runs"][view.runId]["decisions"] == []
    assert ledgerDoc(store)["runs"][view.runId]["floor"]["ok"] is False


def test_handoff_is_replaced_not_stacked_when_a_build_is_re_emitted() -> None:
    from gaia_cli.steward.fullrun import withHandoff

    first = withHandoff("# packet\n", base="dev/x", branch="steward/b/k-1", diffPath="a.diff", proofPath="a.json")
    second = withHandoff(first, base="dev/x", branch="steward/b/k-1", diffPath="b.diff", proofPath="b.json")
    assert second.count("## Steward hand-off") == 1
    assert "b.diff" in second and "b.json" in second and "a.diff" not in second
    assert second.startswith("# packet\n")


def test_retained_runs_beyond_the_newest_keep_headlines_not_payloads() -> None:
    document = {"runs": {}}
    for index in range(fullrun.DETAILEDRUNS + 2):
        document["runs"][f"run-{index:03d}"] = {
            "runId": f"run-{index:03d}", "status": "completed", "startedAt": f"2026-10-{index + 1:02d}T00:00:00Z",
            "steps": [{"stepId": "x"}], "actions": [], "mode": "full", "desk": {"quiet": True},
            "phases": {"observe": {"status": "ok", "openDebt": 3, "openDebtIds": ["a", "b", "c"]}},
        }
    FullRunner._compact(document)
    oldest = document["runs"]["run-000"]
    assert oldest["trimmed"] and "desk" not in oldest and not oldest.get("compacted")
    assert oldest["phases"]["observe"] == {"status": "ok", "openDebt": 3, "openDebtIds": 3}
    newest = document["runs"][f"run-{fullrun.DETAILEDRUNS + 1:03d}"]
    assert newest["phases"]["observe"]["openDebtIds"] == ["a", "b", "c"] and newest["desk"] == {"quiet": True}


# --- lost task packets, operator disposition, and stale desk reporting ------------------------


def pendingBuild(view: Any) -> dict[str, Any]:
    (build,) = [a for a in view.actions if a["type"] == "agent.build"]
    return build


def test_a_lost_task_packet_is_rendered_again_on_resume(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    runner = makeRunner(repo, store, [sensor])
    first = runner.start("full")
    packet = repo / pendingBuild(first)["params"]["promptPath"]
    packet.unlink()

    resumed = runner.resume(first.runId)

    assert packet.is_file()
    assert pendingBuild(resumed)["stepId"] == pendingBuild(first)["stepId"]
    assert "recoveredAt" in ledgerDoc(store)["runs"][first.runId]["actions"][0]


def test_a_lost_packet_for_a_debt_that_is_gone_releases_the_work_instead_of_blocking(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    runner = makeRunner(repo, store, [sensor])
    first = runner.start("full")
    (repo / pendingBuild(first)["params"]["promptPath"]).unlink()
    sensor.heal("leak")

    runner.resume(first.runId)

    doc = ledgerDoc(store)
    assert doc["runs"][first.runId]["actions"][0]["status"] == "superseded"
    assert doc["work"][first.actions[0]["debtId"]]["state"] != "building"


def test_abandon_is_terminal_audited_and_releases_unbuilt_work(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    runner = makeRunner(repo, store, [sensor])
    first = runner.start("full")

    view = runner.abandon(first.runId, "task packet lost with the ephemeral container")

    run = ledgerDoc(store)["runs"][first.runId]
    assert view.status == run["status"] == "abandoned"
    assert run["abandonReason"] == "task packet lost with the ephemeral container"
    assert run["abandonedBy"].startswith("operator:") and run["abandonedAt"]
    assert [a["status"] for a in run["actions"]] == ["superseded"]
    assert runner.status().holder is None
    with pytest.raises(FullRunError, match="only an open run"):
        runner.abandon(first.runId, "again")
    with pytest.raises(FullRunError, match="needs a reason"):
        runner.abandon(first.runId, "  ")


def test_abandon_touches_only_the_named_run(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    runner = makeRunner(repo, store, [sensor])
    done = runner.start("full")
    runner.abandon(done.runId, "first")
    with pytest.raises(UnknownRun):
        runner.abandon("run-does-not-exist", "nope")
    assert ledgerDoc(store)["runs"][done.runId]["status"] == "abandoned"


def test_status_drops_stored_record_decisions_that_are_no_longer_open(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    directory = repo / "founder" / "steward" / "decisions"
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "schemaVersion": "steward-decision-v1", "id": "old-ruling", "status": "open",
        "decision": "Merge it?", "whyItMatters": "w", "evidence": ["e"], "recommended": "r",
        "alternative": "a", "unblocks": "u", "links": ["https://example.test/pull/1"],
    }
    (directory / "old-ruling.json").write_text(json.dumps(record), encoding="utf-8")
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    runner = makeRunner(repo, store, [sensor])
    runner.start("full")
    assert "old-ruling" in [d["decisionId"] for d in runner.status().desk["decisions"]]

    (directory / "old-ruling.json").write_text(json.dumps({**record, "status": "decided"}), encoding="utf-8")
    desk = runner.status().desk

    assert "old-ruling" not in [d["decisionId"] for d in desk["decisions"]]
    assert desk["retiredFromSnapshot"] == ["old-ruling"]
