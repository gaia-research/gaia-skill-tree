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

from gaia_cli.commands.steward import StewardCommand
from gaia_cli.main import main
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.desk import (
    DECISIONS_RELATIVE_DIR,
    _RECORD_OPTIONAL_KEYS,
    _check_record,
    load_decision_records,
)
from gaia_cli.steward.fullrun import (
    FullRunConfig,
    FullRunError,
    FullRunner,
    _hash12,
)
from gaia_cli.steward.lane import (
    lane_document,
    load_lane,
)
from gaia_cli.steward.ledger import FileLedgerStore, transition_work, update, upsert_work
from gaia_cli.steward.models import (
    AuthorityClass,
    Debt,
    DispatchPacket,
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
            "status": "awaiting-action",
            "phase": "verify",
            "actions": [],
            "steps": [],
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
    new_prompt = runner._runDirectory(run_id) / f"verify-{slug}-reverify-2.prompt.md"
    assert new_prompt.is_file()

    # Step ID is unique with :reverify suffix
    action = [a for a in doc["runs"][run_id]["actions"] if a["debtId"] == debt_id][0]
    assert action["stepId"] == f"verify:{slug}:2:reverify"


def test_debt_reconciliation_records_repair_linkage() -> None:
    from gaia_cli.steward.debt import reconcile_debt
    from gaia_cli.steward.models import (
        AuthorityClass,
        Debt,
        Priority,
        Subject,
    )
    from gaia_cli.steward.policy import StewardPolicy

    policy = StewardPolicy.load(REPO_ROOT)
    debt_id = "debt:unused_import:scripts-jev-advisory-py:2e2799e7eedfcd5a"
    existing_debt = Debt(
        id=debt_id,
        kind="unused_import",
        subject=Subject(type="source-file", id="scripts/jev_advisory.py"),
        source="dead-code",
        current_state={"unusedImports": 1},
        observed_state={"unusedImports": 1},
        confidence=0.9,
        priority=Priority(
            importance=1.0,
            decision_impact=1.0,
            exposure=1.0,
            freshness_need=1.0,
            expected_cost=1.0,
            score=1.0,
        ),
        authority=AuthorityClass.B,
        status="open",
        first_observed_at="2026-11-08T00:00:00Z",
        last_observed_at="2026-11-08T00:00:00Z",
        observation_count=1,
    )

    # 1. Without repair_linkages: condition_not_reobserved
    res_vanished = reconcile_debt(
        [],
        {debt_id: existing_debt},
        policy,
        exhaustive_sources=("dead-code",),
        observed_at="2026-11-08T01:00:00Z",
    )
    resolved_debt = [d for d in res_vanished.debts if d.id == debt_id][0]
    assert resolved_debt.status == "resolved"
    assert resolved_debt.resolution == "condition_not_reobserved"
    assert resolved_debt.resolution_receipt is None

    # 2. With repair_linkages: linked to lane repair
    res_repaired = reconcile_debt(
        [],
        {debt_id: existing_debt},
        policy,
        exhaustive_sources=("dead-code",),
        observed_at="2026-11-08T01:00:00Z",
        repair_linkages={debt_id: {"receipt": "receipt-verify-1234", "runId": "run-20261108"}},
    )
    repaired_debt = [d for d in res_repaired.debts if d.id == debt_id][0]
    assert repaired_debt.status == "resolved"
    assert repaired_debt.resolution == "lane_repair:receipt-verify-1234"
    assert repaired_debt.resolution_receipt == "receipt-verify-1234"
    assert repaired_debt.to_dict()["resolutionReceipt"] == "receipt-verify-1234"

