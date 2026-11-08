"""Tests for Founder-Ruled Reverification under Ruling 1 (Issue #2283).

Covers:
- Decision record schema & validation with authorizedDebtIds / authorizedWorkItems
- FullRunner.reverify_escalated fail-closed gates (unauthorized, not escalated, missing diff/proof)
- Preservation of append-only history and attempt counters
- Emission of fresh agent.verify action with forbiddenAgentIds
- CLI subcommands (gaia steward full reverify & gaia steward reverify)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from gaia_cli.main import main
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.desk import (
    DECISIONS_RELATIVE_DIR,
    _RECORD_OPTIONAL_KEYS,
    _check_record,
)
from gaia_cli.steward.fullrun import (
    FullRunConfig,
    FullRunError,
    FullRunner,
    _hash12,
)
from gaia_cli.steward.lane import (
    load_lane,
)
from gaia_cli.steward.ledger import FileLedgerStore, update
from gaia_cli.steward.models import (
    Observation,
    Subject,
)
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.routing import (
    render_dispatch,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# --- 1. Decision record & schema tests ---------------------------------------


def test_record_optional_keys_contains_authorization_fields() -> None:
    assert "authorizedDebtIds" in _RECORD_OPTIONAL_KEYS
    assert "authorizedWorkItems" in _RECORD_OPTIONAL_KEYS


def test_check_record_validates_authorization_fields() -> None:
    base = {
        "schemaVersion": "steward-decision-v1",
        "id": "test-record",
        "status": "decided",
        "decision": "Test decision?",
        "whyItMatters": "Why it matters.",
        "evidence": ["Some evidence."],
        "recommended": "Recommended.",
        "alternative": "Alternative.",
        "unblocks": "Unblocks something.",
        "links": ["https://example.com"],
        "resolution": "approved",
    }
    # Valid with both lists
    valid = {
        **base,
        "authorizedDebtIds": ["debt:test:1", "debt:test:2"],
        "authorizedWorkItems": ["288be108ed47"],
    }
    assert _check_record(valid) is None

    # Invalid authorizedDebtIds (not a list)
    assert "authorizedDebtIds" in (
        _check_record({**base, "authorizedDebtIds": "not a list"}) or ""
    )
    # Invalid authorizedWorkItems (empty string item)
    assert "authorizedWorkItems" in (
        _check_record({**base, "authorizedWorkItems": [""]}) or ""
    )


def test_canonical_reverify_decision_record() -> None:
    record_path = REPO_ROOT / DECISIONS_RELATIVE_DIR / "steward-verification-reverify-2283.json"
    assert record_path.is_file()
    data = json.loads(record_path.read_text(encoding="utf-8"))
    data["_source"] = f"{DECISIONS_RELATIVE_DIR}/{record_path.name}"
    assert _check_record(data) is None
    assert data["status"] == "decided"
    assert data["resolution"] == "approved"
    assert len(data["authorizedDebtIds"]) == 7
    assert len(data["authorizedWorkItems"]) == 7
    assert "debt:unused_import:scripts-jev-advisory-py:2e2799e7eedfcd5a" in data["authorizedDebtIds"]
    assert "288be108ed47" in data["authorizedWorkItems"]


def test_canonical_founder_authorization_record() -> None:
    record_path = REPO_ROOT / DECISIONS_RELATIVE_DIR / "steward-founder-authorization-2026-11-08.json"
    assert record_path.is_file()
    data = json.loads(record_path.read_text(encoding="utf-8"))
    data["_source"] = f"{DECISIONS_RELATIVE_DIR}/{record_path.name}"
    assert _check_record(data) is None
    assert data["status"] == "decided"
    assert data["resolution"] == "approved"


# --- 2. FullRunner Reverification API tests ----------------------------------


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test Steward"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    # Copy policy
    dst_policy = repo / POLICY_RELATIVE_PATH
    dst_policy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, dst_policy)

    # Copy decision records
    dst_decisions = repo / DECISIONS_RELATIVE_DIR
    dst_decisions.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        REPO_ROOT / DECISIONS_RELATIVE_DIR / "steward-verification-reverify-2283.json",
        dst_decisions / "steward-verification-reverify-2283.json",
    )
    shutil.copyfile(
        REPO_ROOT / DECISIONS_RELATIVE_DIR / "steward-founder-authorization-2026-11-08.json",
        dst_decisions / "steward-founder-authorization-2026-11-08.json",
    )

    # Bind the fixture's authorization to its synthetic run.
    decision = dst_decisions / "steward-verification-reverify-2283.json"
    data = json.loads(decision.read_text(encoding="utf-8"))
    for target in data["authorizedTargets"]:
        target["runId"] = "run-test-2283"
    decision.write_text(json.dumps(data), encoding="utf-8")

    # Base commit
    file_py = repo / "scripts" / "jev_advisory.py"
    file_py.parent.mkdir(parents=True, exist_ok=True)
    file_py.write_text("import os\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    return repo


class SimpleSensor:
    id = "dead-code"
    resolution_scope = "exhaustive"

    def scan(self, path: Path, observed_at: str) -> list[Observation]:
        return [
            Observation(
                source="dead-code",
                kind="unused_import",
                status="drift",
                subject=Subject(type="source-file", id="scripts/jev_advisory.py"),
                confidence=0.8,
                observed_at=observed_at,
                current_state={"unusedImports": 0},
                observed_state={
                    "findingCount": 1,
                    "findings": [
                        {
                            "line": 15,
                            "name": "os",
                            "sideEffectPossible": True,
                            "statement": "import os",
                        }
                    ],
                    "findingsCapped": False,
                    "path": "scripts/jev_advisory.py",
                },
            )
        ]


def _setup_runner_and_escalated_item(tmp_path: Path) -> tuple[FullRunner, str, str, Path, Path]:
    repo = _init_repo(tmp_path)
    store = FileLedgerStore(repo / ".gaia" / "steward" / "full" / "ledger.json")
    sensor = SimpleSensor()
    config = FullRunConfig(
        repo_root=repo,
        store=store,
        integration_branch="main",
        remote="origin",
        holder="test",
    )
    config.controller_factory = lambda: StewardController(sensors=(sensor,))
    runner = FullRunner(config)

    # First dispatch debt so dispatch receipt is generated
    controller = StewardController(sensors=(sensor,))
    debt_id = "debt:unused_import:scripts-jev-advisory-py:2e2799e7eedfcd5a"
    dispatch_res = render_dispatch(repo, debt_id, controller=controller)

    # Create diff and proof
    diff_path = repo / ".gaia" / "inputs" / "patch.diff"
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(
        "--- a/scripts/jev_advisory.py\n+++ b/scripts/jev_advisory.py\n@@ -1 +0,0 @@\n-import os\n",
        encoding="utf-8",
    )
    proof_path = repo / ".gaia" / "inputs" / "proof.json"
    proof_path.write_text(
        json.dumps({
            "schemaVersion": "steward-proof-transcript-v1",
            "entries": [
                {"contractIndex": i, "command": f"check {i}", "exitCode": 0, "output": f"ok {i}"}
                for i in range(1, len(dispatch_res.artifact.proof) + 1)
            ],
        }),
        encoding="utf-8",
    )

    # Initialize run and work item in store
    run_id = "run-test-2283"
    now = "2026-11-08T00:00:00Z"

    def init_doc(doc: dict[str, Any]) -> None:
        doc["runs"][run_id] = {
            "runId": run_id,
            "mode": "run",
            "status": "awaiting-action",
            "phase": "verify",
            "actions": [],
            "steps": [],
            "phases": {"observe": {"scanReceiptId": "receipt-test"}},
            "unresolvedWork": [],
            "agentAssignments": [], "modelIds": [], "thinkingEfforts": [],
            "tokensIn": 0, "tokensOut": 0, "costUsd": 0.0,
            "startedAt": now,
        }
        lane_doc = {
            "schemaVersion": "steward-lane-v1",
            "maxInFlight": 4,
            "maxAttempts": 2,
            "cooldownSeconds": 300,
            "entries": [
                {
                    "schemaVersion": "steward-lane-entry-v1",
                    "debtId": debt_id,
                    "rule": dispatch_res.artifact.rule,
                    "state": "escalated",
                    "attempts": 2,
                    "priority": 0.5,
                    "firstQueuedAt": now,
                    "lastTransitionAt": now,
                    "lastVerdict": "escalate",
                    "history": [
                        {"at": now, "from": "queued", "to": "dispatched", "reason": "dispatch"},
                        {"at": now, "from": "dispatched", "to": "escalated", "reason": "verification escalated"},
                    ],
                }
            ],
        }
        doc["lane"] = lane_doc
        doc["work"][debt_id] = {
            "debtId": debt_id,
            "state": "escalated",
            "attempt": 2,
            "authority": "B",
            "kind": "unused_import",
            "source": "dead-code",
            "runId": run_id,
            "dispatchId": dispatch_res.artifact.dispatch_id,
            "assignments": [
                {
                    "agentId": "builder-opus",
                    "role": "builder",
                    "model": "pi",
                    "effort": "high",
                    "stepId": "build:288be108ed47:2",
                    "at": now,
                }
            ],
            "build": {
                "dispatchId": dispatch_res.artifact.dispatch_id,
                "attempt": 2,
                "diffPath": str(diff_path),
                "proofPath": str(proof_path),
                "noChange": False,
                "agentId": "builder-opus",
                "recordedAt": now,
            },
            "verification": {
                "stage": "mechanical",
                "verdict": "escalate",
                "reasons": ["concurrent merge new debt"],
                "recordedAt": now,
            },
            "history": [
                {"at": now, "from": "queued", "to": "building", "reason": "dispatched"},
                {"at": now, "from": "building", "to": "escalated", "reason": "mechanical verification: escalate"},
            ],
            "notes": [],
            "updatedAt": now,
        }

    update(store, init_doc, message="init test run")
    return runner, run_id, debt_id, diff_path, proof_path


def test_reverify_fails_closed_if_decision_record_missing(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    with pytest.raises(FullRunError, match="decision record not found"):
        runner.reverify_escalated(run_id, [debt_id], ruling="nonexistent-ruling")


def test_reverify_fails_closed_if_record_not_approved(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    # Mutate decision file to status open
    rec_file = runner.root / DECISIONS_RELATIVE_DIR / "steward-verification-reverify-2283.json"
    data = json.loads(rec_file.read_text())
    data["status"] = "open"
    rec_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(FullRunError, match="not decided and approved"):
        runner.reverify_escalated(run_id, [debt_id])


def test_reverify_fails_closed_if_item_not_authorized(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    with pytest.raises(FullRunError, match="not authorized by decision record"):
        runner.reverify_escalated(run_id, ["debt:unauthorized:random:123"])


def test_reverify_fails_closed_if_item_not_escalated(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    # Transition item to queued
    def set_queued(doc: dict[str, Any]) -> None:
        doc["work"][debt_id]["state"] = "queued"

    update(runner.config.store, set_queued, message="set queued")
    with pytest.raises(FullRunError, match="is in state 'queued', not 'escalated'"):
        runner.reverify_escalated(run_id, [debt_id])


def test_reverify_fails_closed_if_diff_missing(tmp_path: Path) -> None:
    runner, run_id, debt_id, diff_path, _ = _setup_runner_and_escalated_item(tmp_path)
    diff_path.unlink()
    with pytest.raises(FullRunError, match="diff file .* does not exist"):
        runner.reverify_escalated(run_id, [debt_id])


def test_reverify_success_reopens_item_and_emits_verify_action(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    res = runner.reverify_escalated(run_id, [debt_id])

    assert res["runId"] == run_id
    assert res["ruling"] == "steward-verification-reverify-2283"
    assert res["reopened"] == [debt_id]
    assert len(res["results"]) == 1
    assert res["results"][0]["result"] == "awaiting-verifier"
    assert res["results"][0]["forbiddenAgentIds"] == ["builder-opus"]

    # Verify ledger state in store
    doc, _ = runner.config.store.load()
    work = doc["work"][debt_id]
    assert work["state"] == "building"
    assert work["attempt"] == 2  # NOT reset
    assert work["verification"]["stage"] == "awaiting-verifier"
    assert work["verification"]["verdict"] == "pending"

    # Verify append-only history preserved
    hist = work["history"]
    assert len(hist) == 3
    assert hist[-1]["from"] == "escalated"
    assert hist[-1]["to"] == "building"
    assert "ruling steward-verification-reverify-2283" in hist[-1]["reason"]

    # Verify lane entry was reopened to dispatched
    lane = load_lane(doc["lane"], runner._policyLoaded().lane)
    entry = lane.by_id(debt_id)
    assert entry is not None
    assert entry.state == "dispatched"
    assert entry.attempts == 2  # NOT reset
    assert entry.last_verdict == "pending"
    assert entry.history[-1].from_state == "escalated"
    assert entry.history[-1].to_state == "dispatched"

    # Verify run actions has the emitted agent.verify action
    run = doc["runs"][run_id]
    actions = [a for a in run["actions"] if a["type"] == "agent.verify"]
    assert len(actions) == 1
    action = actions[0]
    assert action["debtId"] == debt_id
    assert action["status"] == "pending"
    assert action["params"]["forbiddenAgentIds"] == ["builder-opus"]
    assert action["params"]["attempt"] == 2


# --- 3. CLI Tests -----------------------------------------------------------


def test_cli_full_reverify(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    repo = runner.root

    monkeypatch.setattr(
        "gaia_cli.steward.fullrun.StewardController",
        lambda **kwargs: StewardController(sensors=(SimpleSensor(),)),
    )
    monkeypatch.setattr(
        "gaia_cli.steward.routing.StewardController",
        lambda **kwargs: StewardController(sensors=(SimpleSensor(),)),
    )
    monkeypatch.setattr(
        "gaia_cli.steward.controller.StewardController",
        lambda **kwargs: StewardController(sensors=(SimpleSensor(),)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gaia",
            "--registry",
            str(repo),
            "steward",
            "full",
            "reverify",
            run_id,
            debt_id,
            "--ruling",
            "steward-verification-reverify-2283",
            "--ledger",
            "local",
        ],
    )
    code = 0
    try:
        main()
    except SystemExit as exc:
        code = int(exc.code or 0)
    out, err = capsys.readouterr()
    assert code == 0
    assert "Steward reverify: run run-test-2283 under ruling steward-verification-reverify-2283" in out
    assert f"Reopened 1 item(s) for independent verification" in out


def test_cli_direct_reverify(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    repo = runner.root

    monkeypatch.setattr(
        "gaia_cli.steward.fullrun.StewardController",
        lambda **kwargs: StewardController(sensors=(SimpleSensor(),)),
    )
    monkeypatch.setattr(
        "gaia_cli.steward.routing.StewardController",
        lambda **kwargs: StewardController(sensors=(SimpleSensor(),)),
    )
    monkeypatch.setattr(
        "gaia_cli.steward.controller.StewardController",
        lambda **kwargs: StewardController(sensors=(SimpleSensor(),)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gaia",
            "--registry",
            str(repo),
            "steward",
            "reverify",
            run_id,
            debt_id,
            "--ruling",
            "steward-verification-reverify-2283",
            "--ledger",
            "local",
            "--json",
        ],
    )
    code = 0
    try:
        main()
    except SystemExit as exc:
        code = int(exc.code or 0)
    out, err = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert data["runId"] == run_id
    assert data["ruling"] == "steward-verification-reverify-2283"
    assert data["reopened"] == [debt_id]


def test_reverify_fails_closed_on_cross_run_item(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    # Set work item runId to a different run
    def mutate(doc: dict[str, Any]) -> None:
        doc["work"][debt_id]["runId"] = "run-different"

    update(runner.config.store, mutate, message="change runId")
    with pytest.raises(FullRunError, match="belongs to run 'run-different', not run-test-2283"):
        runner.reverify_escalated(run_id, [debt_id])


def test_reverify_preserves_prior_verifications_and_unique_step_and_prompt(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    # Put an initial prompt file to prove it is not overwritten
    slug = _hash12(debt_id)
    initial_prompt = runner._runDirectory(run_id) / f"verify-{slug}.prompt.md"
    initial_prompt.parent.mkdir(parents=True, exist_ok=True)
    initial_prompt.write_text("original verifier prompt", encoding="utf-8")

    res = runner.reverify_escalated(run_id, [debt_id])
    assert res["reopened"] == [debt_id]

    doc, _ = runner.config.store.load()
    work = doc["work"][debt_id]
    # Prior verification preserved in priorVerifications list
    assert "priorVerifications" in work
    assert len(work["priorVerifications"]) == 1
    assert work["priorVerifications"][0]["verdict"] == "escalate"
    assert work["priorVerifications"][0]["reasons"] == ["concurrent merge new debt"]

    # Initial prompt file untouched
    assert initial_prompt.read_text(encoding="utf-8") == "original verifier prompt"
    # New reverify prompt file written separately
    new_prompt = runner._runDirectory(run_id) / f"verify-{slug}-reverify-2-1.prompt.md"
    assert new_prompt.is_file()

    # Step ID is unique with :reverify suffix
    action = [a for a in doc["runs"][run_id]["actions"] if a["debtId"] == debt_id][0]
    assert action["stepId"] == f"verify:{slug}:2:reverify:1"



def test_missing_dispatch_receipt_never_redispatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import gaia_cli.steward.routing as routing

    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    def missing(*args: Any, **kwargs: Any) -> Any:
        raise routing.RoutingError("no dispatch receipt")
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("must not create a replacement dispatch")
    monkeypatch.setattr(routing, "_dispatch_receipt_for", missing)
    monkeypatch.setattr(routing, "render_dispatch", forbidden)
    with pytest.raises(FullRunError, match="verification failed.*no dispatch receipt"):
        runner.reverify_escalated(run_id, [debt_id])


def test_authorization_is_bound_to_run(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    decision = runner.root / DECISIONS_RELATIVE_DIR / "steward-verification-reverify-2283.json"
    data = json.loads(decision.read_text(encoding="utf-8"))
    data["authorizedTargets"][0]["runId"] = "another-run"
    decision.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(FullRunError, match="not authorized for run"):
        runner.reverify_escalated(run_id, [debt_id])


def test_reverify_fails_closed_without_dispatch_id(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)

    def mutate(doc: dict[str, Any]) -> None:
        doc["work"][debt_id].pop("dispatchId")
        doc["work"][debt_id]["build"].pop("dispatchId")

    update(runner.config.store, mutate, message="remove dispatch authorization")
    with pytest.raises(FullRunError, match="missing dispatchId"):
        runner.reverify_escalated(run_id, [debt_id])


def test_ruling_remains_consumed_after_independent_escalation(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    runner.reverify_escalated(run_id, [debt_id])
    doc, _ = runner.config.store.load()
    item = doc["work"][debt_id]
    release = dict(item["verification"])
    action = next(a for a in doc["runs"][run_id]["actions"] if a["type"] == "agent.verify")
    runner.record(run_id, action["stepId"], {
        "agentId": "independent-verifier", "model": "pi", "effort": "high",
        "verdict": "escalate", "rationale": "Independent uncertainty remains.",
    })
    doc, _ = runner.config.store.load()
    item = doc["work"][debt_id]
    assert item["verification"]["verdict"] == "escalate"
    assert release in item["priorVerifications"]
    assert release["ruling"] in item["consumedRulings"]
    with pytest.raises(FullRunError, match="consumable once"):
        runner.reverify_escalated(run_id, [debt_id])


@pytest.mark.parametrize("field", ["consumedRulings", "verification", "priorVerifications"])
def test_recorded_ruling_filename_is_consumed(tmp_path: Path, field: str) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    filename = "steward-verification-reverify-2283.json"

    def mutate(doc: dict[str, Any]) -> None:
        work = doc["work"][debt_id]
        if field == "consumedRulings":
            work[field] = [filename]
        elif field == "verification":
            work[field]["ruling"] = filename
        else:
            work[field] = [{"ruling": filename}]

    update(runner.config.store, mutate, message="record consumed ruling filename")
    with pytest.raises(FullRunError, match="consumable once"):
        runner.reverify_escalated(run_id, [debt_id], ruling="steward-verification-reverify-2283")


def test_ruling_is_consumable_once(tmp_path: Path) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    runner.reverify_escalated(run_id, [debt_id])
    with pytest.raises(FullRunError, match="consumable once"):
        runner.reverify_escalated(run_id, [debt_id])


@pytest.mark.parametrize("alias", [
    "steward-verification-reverify-2283.json",
    "other/path/steward-verification-reverify-2283.json",
])
def test_ruling_alias_cannot_bypass_consumption(tmp_path: Path, alias: str) -> None:
    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    runner.reverify_escalated(run_id, [debt_id], ruling="steward-verification-reverify-2283")
    with pytest.raises(FullRunError, match="consumable once"):
        runner.reverify_escalated(run_id, [debt_id], ruling=alias)


def test_batch_compatibility_mandate_in_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import gaia_cli.steward.fullrun as fullrun

    runner, run_id, debt_id, _, _ = _setup_runner_and_escalated_item(tmp_path)
    # Exercise the batch slug branch using a fully authenticated fixture dispatch.
    real_hash = fullrun._hash12
    monkeypatch.setattr(fullrun, "_hash12", lambda value: "01bdcf8a1d9c" if value == debt_id else real_hash(value))
    result = runner.reverify_escalated(run_id, [debt_id])
    prompt = runner.root / result["results"][0]["verifierPromptPath"]
    content = prompt.read_text(encoding="utf-8")
    assert "Founder Ruling 1 Mandate: Module API & Consumer Contract Compatibility Check" in content
    assert "batch.re" in content and "Stop on any remaining uncertainty" in content


# --- Legacy receipts: authenticated runner baseline; only decided outcomes consume ---


def _make_legacy(runner: FullRunner, run_id: str, debt_id: str, diff_path: Path,
                 monkeypatch: pytest.MonkeyPatch, *, record_baseline: bool = True) -> str:
    """Strip headCommit from the dispatch receipt and record the runner's own integration head."""
    from gaia_cli.steward import routing

    repo = runner.root
    git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    head = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", head)
    old_blob = subprocess.run(["git", "hash-object", "--stdin"], cwd=repo, input="import os\n",
                              check=True, capture_output=True, text=True).stdout.strip()
    diff_path.write_text(
        "diff --git a/scripts/jev_advisory.py b/scripts/jev_advisory.py\n"
        f"index {old_blob[:12]}..e69de29bb2d1 100644\n"
        "--- a/scripts/jev_advisory.py\n+++ b/scripts/jev_advisory.py\n@@ -1 +0,0 @@\n-import os\n",
        encoding="utf-8",
    )
    original = routing._dispatch_receipt_for

    def legacy_receipt(*args: Any, **kwargs: Any) -> Any:
        receipt = dict(original(*args, **kwargs))
        receipt["artifact"] = dict(receipt["artifact"])
        for field in ("headCommit", "gitHead"):
            receipt.pop(field, None)
            receipt["artifact"].pop(field, None)
        return receipt

    monkeypatch.setattr(routing, "_dispatch_receipt_for", legacy_receipt)

    def mutate(doc: dict[str, Any]) -> None:
        run = doc["runs"][run_id]
        dispatch_id = doc["work"][debt_id]["dispatchId"]
        run["integrationBranch"] = "main"
        run["integrationHead"] = head if record_baseline else "unknown"
        run["actions"].append({
            "stepId": "build:x:2", "type": "agent.build", "debtId": debt_id, "status": "done",
            "params": {"debtId": debt_id, "dispatchId": dispatch_id, "attempt": 2},
        })
        doc["work"][debt_id]["baseBranch"] = "main"

    update(runner.config.store, mutate, message="legacy dispatch")
    return head


def test_legacy_receipt_reverifies_from_runner_recorded_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner, run_id, debt_id, diff_path, _ = _setup_runner_and_escalated_item(tmp_path)
    head = _make_legacy(runner, run_id, debt_id, diff_path, monkeypatch)
    res = runner.reverify_escalated(run_id, [debt_id])
    assert res["results"][0]["result"] == "awaiting-verifier"
    doc, _ = runner.config.store.load()
    work = doc["work"][debt_id]
    assert work["verification"]["ruling"] == "steward-verification-reverify-2283"
    assert not work.get("consumedRulings")  # reserved, not yet decided
    with pytest.raises(FullRunError, match="consumable once"):
        runner.reverify_escalated(run_id, [debt_id])
    action = next(a for a in doc["runs"][run_id]["actions"] if a["type"] == "agent.verify")
    runner.record(run_id, action["stepId"], {
        "agentId": "independent-verifier", "model": "pi", "effort": "high",
        "verdict": "accept", "rationale": "Independent check passed.",
    })
    doc, _ = runner.config.store.load()
    assert doc["work"][debt_id]["consumedRulings"] == ["steward-verification-reverify-2283"]
    assert head


def test_mechanical_escalation_does_not_consume_ruling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner, run_id, debt_id, diff_path, _ = _setup_runner_and_escalated_item(tmp_path)
    _make_legacy(runner, run_id, debt_id, diff_path, monkeypatch, record_baseline=False)
    for attempt in (1, 2):
        res = runner.reverify_escalated(run_id, [debt_id])
        assert res["results"][0]["result"] == "mechanical-escalate"
        assert any("runner baseline rejected" in r for r in res["results"][0]["reasons"])
        doc, _ = runner.config.store.load()
        work = doc["work"][debt_id]
        assert work["state"] == "escalated"
        assert not work.get("consumedRulings")
        assert work["verification"]["rulingAttempt"] == "steward-verification-reverify-2283"
        assert work["verification"]["rulingConsumed"] is False
        assert "ruling" not in work["verification"]
        assert len(work["priorVerifications"]) == attempt


def test_mechanical_reject_consumes_ruling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner, run_id, debt_id, diff_path, proof_path = _setup_runner_and_escalated_item(tmp_path)
    _make_legacy(runner, run_id, debt_id, diff_path, monkeypatch)
    data = json.loads(proof_path.read_text(encoding="utf-8"))
    data["entries"][0]["exitCode"] = 1
    proof_path.write_text(json.dumps(data), encoding="utf-8")
    res = runner.reverify_escalated(run_id, [debt_id])
    assert res["results"][0]["result"] == "mechanical-reject"
    doc, _ = runner.config.store.load()
    assert doc["work"][debt_id]["consumedRulings"] == ["steward-verification-reverify-2283"]
    with pytest.raises(FullRunError, match="consumable once"):
        runner.reverify_escalated(run_id, [debt_id])


def test_redispatched_item_uses_run_of_recorded_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A dispatch id survives re-dispatch; the build's attempt picks the run whose head is used."""
    runner, run_id, debt_id, diff_path, _ = _setup_runner_and_escalated_item(tmp_path)
    _make_legacy(runner, run_id, debt_id, diff_path, monkeypatch)

    def mutate(doc: dict[str, Any]) -> None:
        dispatch_id = doc["work"][debt_id]["dispatchId"]
        doc["runs"]["run-earlier"] = {
            "runId": "run-earlier", "integrationBranch": "main", "integrationHead": "f" * 40,
            "actions": [{"stepId": "build:x:1", "type": "agent.build", "debtId": debt_id, "status": "done",
                         "params": {"debtId": debt_id, "dispatchId": dispatch_id, "attempt": 1}}],
        }

    update(runner.config.store, mutate, message="earlier attempt")
    res = runner.reverify_escalated(run_id, [debt_id])
    assert res["results"][0]["result"] == "awaiting-verifier"
