"""Unit coverage for the Steward Full runner (`gaia_cli.steward.fullrun`).

Every test builds a real fixture repository with a local bare remote in
``tmp_path``; nothing here can reach a real origin or the real ``steward/*``
refs. Sensors are stubs or the real mirror sensors, so a test controls exactly
what the runner observes.
"""

from __future__ import annotations

import json
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
    FullRunConfig,
    FullRunner,
    RecordRefused,
    validateAgent,
)
from gaia_cli.steward.ledger import FileLedgerStore
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH

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


BUILD = {"agentId": "builder-1", "model": "claude-haiku-5-5", "effort": "high",
         "tokensIn": 1200, "tokensOut": 300, "costUsd": 0.01, "noChange": False,
         "summary": "added scripts/fix.py"}
VERIFY = {"agentId": "verifier-1", "model": "claude-sonnet-5-5", "effort": "high",
          "verdict": "accept", "rationale": "diff resolves the finding; proof is genuine"}


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


@pytest.mark.parametrize("model", ["gpt-5", "claude-opus-5", "", None])
def test_model_must_be_in_the_allowed_set(model: Any) -> None:
    with pytest.raises(RecordRefused, match="not permitted"):
        validateAgent({**BUILD, "model": model}, BUILDERMODELS, "builder")


def test_negative_cost_is_refused() -> None:
    with pytest.raises(RecordRefused, match="costUsd"):
        validateAgent({**BUILD, "costUsd": -1}, BUILDERMODELS, "builder")


def test_valid_agent_passes() -> None:
    validateAgent(BUILD, BUILDERMODELS, "builder")
