"""Founder ruling #10 (steward-issue-closure-authority): A1-A5 ratified as policy, with attributable receipts.

Closures carry receipts naming both the Steward owner and the worker, the ratified authority record, the exact
closure proof, and the issue's state before and after. A reopened issue is respected and never re-closed. A closure
with no attributable owner or worker is not performed. Nothing here switches writes on: the shipped policy keeps
``writesEnabled: false`` and the kill switch is untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.fullrun import RecordRefused
from gaia_cli.steward.issuehygiene.authority import DECISION_PATH, authorityReceipt, closureAuthorityApproved
from gaia_cli.steward.issuehygiene.closure import ActionRefused, attributionProblem, resolveAttribution
from gaia_cli.steward.issuehygiene.hygienepolicy import loadHygienePolicy
from scripts.steward_issue_close import EXIT_OK, EXIT_REFUSED, main
from tests.steward.issuehygiene.test_b_closure import FakeForge, liveOf, planFor, scenarioRow
from tests.steward.issuehygiene.test_d1_runner import closeActions, closureItems, closureRows, outcomeFor, settle
from tests.steward.issuehygiene.test_d1_sensor import makeCensus, makeManifest, stubReconcile, writeCensus
from tests.steward.issuehygiene.test_d2_close_script import RECEIPT, REPO_NAME, scenario, writeAction
from tests.steward.test_fullrun import makeRunner  # noqa: F401  (shared seam)

REPO_ROOT = Path(__file__).resolve().parents[3]


def runClose(tmp_path: Path, forge: FakeForge, capsys, *extra: str) -> tuple[int, dict | None, str]:
    manifest, _ = scenario(tmp_path)
    action = writeAction(tmp_path, manifest, planFor(manifest))
    code = main(["--root", str(tmp_path), "--action", str(action), "--run-id", "R1", *extra],
                forgeFactory=lambda repo, token: forge)
    captured = capsys.readouterr()
    out = captured.out.strip()
    return code, (json.loads(out.splitlines()[-1]) if out else None), captured.err


def receiptLines(tmp_path: Path) -> list[dict]:
    return [json.loads(line) for line in (tmp_path / RECEIPT).read_text(encoding="utf-8").splitlines()]


# ---------------------------------------------------------------- the ratification is recorded, writes stay off


def test_the_allowlist_is_recorded_as_founder_ratified() -> None:
    record = json.loads((REPO_ROOT / DECISION_PATH).read_text(encoding="utf-8"))

    assert record["status"] == "decided" and record["resolution"] == "approved"
    assert closureAuthorityApproved(REPO_ROOT)
    assert authorityReceipt(REPO_ROOT)["decision"] == "steward-issue-closure-authority"
    policyText = (REPO_ROOT / "founder/steward/POLICY.yaml").read_text(encoding="utf-8")
    assert "UNRATIFIED" not in policyText and "ratified" in policyText


def test_ratification_does_not_switch_writes_on() -> None:
    raw = yaml.safe_load((REPO_ROOT / "founder/steward/POLICY.yaml").read_text(encoding="utf-8"))["issueHygiene"]

    policy = loadHygienePolicy(raw)

    assert raw["writesEnabled"] is False and policy.writesEnabled is False
    assert policy.enabledRules == (
        "A1-child-curated", "A2-umbrella-synced", "A3-umbrella-superseded", "A4-duplicate-child", "A5-botreport-superseded",
    )
    assert raw["a5Disabled"] == []  # A5 stays unprovable until a workflow is listed
    assert raw["maxClosuresPerRun"] == 10


# ---------------------------------------------------------------- the closure path records the receipt fields


def test_a_closed_receipt_names_owner_worker_authority_proof_and_both_states(tmp_path, capsys) -> None:
    forge = FakeForge({10: liveOf(scenarioRow(10))})

    code, outcome, _ = runClose(tmp_path, forge, capsys)

    assert code == EXIT_OK and outcome["outcome"] == "closed"
    assert outcome["stewardOwner"] == "steward-owner-test" and outcome["worker"] == "steward-worker-test"
    closed = receiptLines(tmp_path)[-1]
    assert closed["outcome"] == "closed"
    assert closed["stewardOwner"] == "steward-owner-test" and closed["worker"] == "steward-worker-test"
    assert closed["authority"]["decision"] == "steward-issue-closure-authority"
    assert closed["authority"]["resolution"] == "approved" and len(closed["authority"]["recordSha256"]) == 64
    proof = closed["closureProof"]
    assert proof["ruleId"] == closed["ruleId"] and proof["itemSha256"] and proof["preservedSha256"]
    assert proof["commentUrl"] == closed["commentUrl"] and proof["evidenceRefs"]
    assert closed["before"]["snapshot"]["state"] == "open"
    assert closed["after"]["state"] == "closed" and closed["after"]["verified"] is True
    assert closed["after"]["stateReason"] == closed["stateReason"] or closed["after"]["stateReason"] is None


def test_flags_name_the_owner_and_worker_over_the_environment(tmp_path, capsys) -> None:
    forge = FakeForge({10: liveOf(scenarioRow(10))})

    code, _, _ = runClose(tmp_path, forge, capsys, "--steward-owner", "Marco", "--worker", "steward-drive")

    assert code == EXIT_OK
    closed = receiptLines(tmp_path)[-1]
    assert (closed["stewardOwner"], closed["worker"]) == ("Marco", "steward-drive")


def test_a_failed_closure_is_attributable_too(tmp_path, capsys) -> None:
    live = liveOf(scenarioRow(10))
    live["title"] = "moved since the manifest"
    forge = FakeForge({10: live})

    code, outcome, _ = runClose(tmp_path, forge, capsys)

    assert outcome["outcome"] == "stale-skip"
    last = receiptLines(tmp_path)[-1]
    assert last["stewardOwner"] == "steward-owner-test" and last["worker"] == "steward-worker-test"
    assert "after" not in last  # nothing was closed, so there is no after-state


@pytest.mark.parametrize("missing", ["GAIA_STEWARD_OWNER", "GAIA_STEWARD_WORKER"])
def test_no_attributable_owner_or_worker_means_no_write(tmp_path, capsys, monkeypatch, missing) -> None:
    monkeypatch.delenv(missing)
    forge = FakeForge({10: liveOf(scenarioRow(10))})

    code, outcome, err = runClose(tmp_path, forge, capsys)

    assert code == EXIT_REFUSED
    assert outcome["outcome"] == "refused" and outcome["reason"] == "attribution-missing"
    assert forge.calls == [] and forge.issues[10]["state"] == "open"
    assert not (tmp_path / RECEIPT).exists()
    assert "attributable" in err


@pytest.mark.parametrize("bad", ["", "   ", "line\nbreak", "<script>", "x" * 200, "-leading", "tok" + "en=abc"])
def test_an_invalid_name_is_refused_before_a_forge_is_built(bad) -> None:
    with pytest.raises(ActionRefused) as raised:
        resolveAttribution({"stewardOwner": bad, "worker": "steward-drive"}, environ={})

    assert raised.value.code in ("attribution-missing", "attribution-invalid")


def test_resolution_prefers_the_argument_then_the_environment() -> None:
    environ = {"GAIA_STEWARD_OWNER": "env-owner", "GAIA_STEWARD_WORKER": "env-worker"}

    assert resolveAttribution(None, environ) == {"stewardOwner": "env-owner", "worker": "env-worker"}
    assert resolveAttribution({"worker": "arg-worker"}, environ) == {"stewardOwner": "env-owner", "worker": "arg-worker"}


def test_attribution_problem_reads_a_receipt_entry() -> None:
    assert attributionProblem({"stewardOwner": "Marco", "worker": "steward-drive"}) is None
    assert "stewardOwner" in attributionProblem({"worker": "steward-drive"})
    assert "worker" in attributionProblem({"stewardOwner": "Marco", "worker": 7})


def test_a_reopened_issue_is_respected_and_never_closed_again(tmp_path, capsys) -> None:
    forge = FakeForge({10: liveOf(scenarioRow(10))})
    code, outcome, _ = runClose(tmp_path, forge, capsys)
    assert outcome["outcome"] == "closed"
    forge.issues[10]["state"] = "open"  # a person reopens it
    callsBefore = len(forge.calls)
    manifest, _ = scenario(tmp_path)
    action = writeAction(tmp_path, manifest, planFor(manifest))

    code = main(["--root", str(tmp_path), "--action", str(action), "--run-id", "R1"], forgeFactory=lambda repo, token: forge)

    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == EXIT_OK and printed["outcome"] == "closed"  # the recorded outcome is replayed, not redone
    assert len(forge.calls) == callsBefore
    assert forge.issues[10]["state"] == "open"
    assert [line["outcome"] for line in receiptLines(tmp_path)].count("closed") == 1


# ---------------------------------------------------------------- the runner trusts only attributable receipts


def settleWithout(runner, runId, action, outcome, **missing) -> None:
    params = action["params"]
    receipt = runner.root / params["receiptPath"]
    receipt.parent.mkdir(parents=True, exist_ok=True)
    entry = {"schemaVersion": "steward-issue-closure-receipt-v1", "runId": runId, "key": params["key"],
             "issue": params["issue"], "ruleId": params["ruleId"], "outcome": outcome["outcome"],
             "commentUrl": outcome.get("commentUrl"), "commentId": outcome.get("commentId"),
             "markerVerified": outcome.get("markerVerified", False), "closedAt": "2026-10-21T19:30:00Z", **missing}
    receipt.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")
    runner.record(runId, action["stepId"], outcome)


@pytest.mark.parametrize("missing", [
    {}, {"worker": "steward-drive"}, {"stewardOwner": "Marco"}, {"stewardOwner": "Marco", "worker": "bad\nname"},
])
def test_the_runner_refuses_a_closed_receipt_without_owner_and_worker(tmp_path, monkeypatch, missing) -> None:
    from tests.steward.issuehygiene.test_d1_runner import runnerFor

    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)

    with pytest.raises(RecordRefused, match="attributable owner and worker"):
        settleWithout(runner, view.runId, action, outcomeFor(action), **missing)


def test_the_runner_stores_the_owner_and_worker_with_the_outcome(tmp_path, monkeypatch) -> None:
    from gaia_cli.steward.issuehygiene.outcomes import loadOutcomes
    from tests.steward.issuehygiene.test_d1_runner import runnerFor

    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)

    settle(runner, view.runId, action, outcomeFor(action))

    (entry,) = loadOutcomes(runner.root).values()
    assert entry["stewardOwner"] == "steward-owner-test" and entry["worker"] == "steward-worker-test"


def test_the_drive_script_passes_the_worker_and_owner_to_the_close_script() -> None:
    text = (REPO_ROOT / "scripts/steward_drive.py").read_text(encoding="utf-8")

    assert '"--worker", DRIVERACTOR' in text and "--steward-owner" in text
