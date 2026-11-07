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


def test_the_decision_record_separates_current_status_from_history() -> None:
    record = json.loads((REPO_ROOT / DECISION_PATH).read_text(encoding="utf-8"))

    assert record["status"] == "decided" and record["resolution"] == "approved"
    assert record["whyItMatters"].startswith("CURRENT STATUS: decided, resolution approved")
    historical = [item for item in record["evidence"] if item.startswith("HISTORICAL")]
    assert len(historical) == 2
    assert any("unratified" in item or "OPEN" in item or "not resolved here" in item for item in historical)
    # Nothing outside the labelled history still says the authority is unratified or open.
    current = [item for item in record["evidence"] if not item.startswith("HISTORICAL")]
    assert not any("remains an unratified" in item or "claimed founder authorization" in item for item in current)


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


def test_an_already_closed_receipt_records_the_live_observed_after_state(tmp_path, capsys) -> None:
    live = liveOf(scenarioRow(10))
    live.update({"state": "closed", "stateReason": "not_planned", "updatedAt": "2026-10-21T19:20:00Z"})
    forge = FakeForge({10: live})

    code, outcome, _ = runClose(tmp_path, forge, capsys)

    assert code == EXIT_OK and outcome["outcome"] == "already-closed"
    receipt = receiptLines(tmp_path)[-1]
    assert receipt["after"] == {"state": "closed", "stateReason": "not_planned", "updatedAt": "2026-10-21T19:20:00Z",
                                "verified": True, "source": "live-read"}
    assert receipt["stewardOwner"] == "steward-owner-test" and receipt["closureProof"]["itemSha256"]
    assert [call for call in forge.calls if call[0] in ("comment", "close")] == []


def test_a_failed_post_close_read_records_unknown_never_closed(tmp_path, capsys) -> None:
    from gaia_cli.steward.issuehygiene.closure import ForgeItemError

    class BlindAfterClose(FakeForge):
        def getIssue(self, number):
            if self.issues[number]["state"] == "closed":
                raise ForgeItemError("read failed after close")
            return super().getIssue(number)

    forge = BlindAfterClose({10: liveOf(scenarioRow(10))})

    code, outcome, _ = runClose(tmp_path, forge, capsys)

    assert code == EXIT_OK and outcome["outcome"] == "closed"  # the closure happened; only the observation failed
    after = receiptLines(tmp_path)[-1]["after"]
    assert after["state"] is None and after["verified"] is False and "re-read failed" in after["note"]


def test_a_post_close_read_that_still_shows_open_is_recorded_as_observed(tmp_path, capsys) -> None:
    class StaleAfterClose(FakeForge):
        def getIssue(self, number):
            issue = super().getIssue(number)
            if ("close", number) in [call[:2] for call in self.calls]:
                issue["state"] = "open"
            return issue

    forge = StaleAfterClose({10: liveOf(scenarioRow(10))})

    runClose(tmp_path, forge, capsys)

    after = receiptLines(tmp_path)[-1]["after"]
    assert after["state"] == "open" and after["verified"] is False


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


def settleWithout(runner, runId, action, outcome, **changes) -> None:
    """Write a receipt with the given fields changed or removed (``None`` removes), then record the outcome."""
    from tests.steward.issuehygiene.test_d1_runner import receiptEntry

    params = action["params"]
    receipt = runner.root / params["receiptPath"]
    receipt.parent.mkdir(parents=True, exist_ok=True)
    entry = receiptEntry(params, outcome, runId)
    for field, value in changes.items():
        if value is None:
            entry.pop(field, None)
        else:
            entry[field] = value
    receipt.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")
    runner.record(runId, action["stepId"], outcome)


@pytest.mark.parametrize("missing", [
    {"stewardOwner": None, "worker": None}, {"stewardOwner": None}, {"worker": None},
    {"worker": "bad\nname"},
])
def test_the_runner_refuses_a_closed_receipt_without_owner_and_worker(tmp_path, monkeypatch, missing) -> None:
    from tests.steward.issuehygiene.test_d1_runner import runnerFor

    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)

    with pytest.raises(RecordRefused, match="fully proven receipt"):
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


# ---------------------------------------------------------------- terminal receipt verification (proof, before, after)


def verifiedEntry(**changes) -> tuple[dict, dict]:
    from tests.steward.issuehygiene.test_d1_runner import receiptEntry

    params = {"key": "k", "issue": 10, "ruleId": "A1-child-curated", "closureSha8": "abcd1234",
              "itemSha256": "b" * 64, "preservedSha256": "c" * 64}
    entry = receiptEntry(params, {"outcome": "closed", "commentUrl": "u"}, "R1")
    for field, value in changes.items():
        entry[field] = value
    return entry, params


def test_a_complete_receipt_verifies() -> None:
    from gaia_cli.steward.issuehygiene.closure import receiptProblem

    entry, params = verifiedEntry()

    assert receiptProblem(entry, params) is None


@pytest.mark.parametrize("changes, fragment", [
    ({"authority": None}, "approved closure authority"),
    ({"authority": {"decision": "steward-issue-closure-authority", "resolution": "rejected"}}, "approved closure authority"),
    ({"closureProof": None}, "no closureProof"),
    ({"closureProof": {"ruleId": "A1-child-curated", "closureSha8": "abcd1234", "itemSha256": "x", "preservedSha256": "c" * 64}},
     "itemSha256"),
    ({"closureProof": {"ruleId": "A2-umbrella-synced", "closureSha8": "abcd1234", "itemSha256": "b" * 64,
                       "preservedSha256": "c" * 64}}, "ruleId"),
    ({"before": None}, "before state"),
    ({"before": {"snapshot": {"state": "closed"}}}, "before state"),
    ({"after": None}, "no after state"),
    ({"after": {"state": "closed"}}, "no after state"),
    ({"after": {"state": "closed", "verified": False}}, "must be null"),
    ({"after": {"state": "open", "verified": True}}, "not closed"),
])
def test_a_receipt_missing_proof_or_state_fields_does_not_verify(changes, fragment) -> None:
    from gaia_cli.steward.issuehygiene.closure import receiptProblem

    entry, params = verifiedEntry(**changes)

    assert fragment in receiptProblem(entry, params)


def test_an_unobserved_after_state_verifies_only_as_null() -> None:
    from gaia_cli.steward.issuehygiene.closure import receiptProblem

    entry, params = verifiedEntry(after={"state": None, "stateReason": None, "updatedAt": None, "verified": False})

    assert receiptProblem(entry, params) is None


@pytest.mark.parametrize("changes", [
    {"authority": None}, {"closureProof": None}, {"before": None}, {"after": None},
    {"after": {"state": "closed", "verified": False}},
])
def test_the_runner_refuses_a_closed_receipt_missing_proof_or_state(tmp_path, monkeypatch, changes) -> None:
    from tests.steward.issuehygiene.test_d1_runner import runnerFor

    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)

    with pytest.raises(RecordRefused, match="fully proven receipt"):
        settleWithout(runner, view.runId, action, outcomeFor(action), **{k: (v if v is not None else None) for k, v in changes.items()})


# ---------------------------------------------------------------- the CLI boundaries run the same receipt validation


def rewriteClosedReceipt(tmp_path: Path, **changes) -> None:
    """Rewrite the closed line of the receipts file; a ``None`` value removes the field (a legacy receipt)."""
    path = tmp_path / RECEIPT
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for entry in lines:
        if entry.get("outcome") == "closed":
            for field, value in changes.items():
                if value is None:
                    entry.pop(field, None)
                else:
                    entry[field] = value
    path.write_text("".join(json.dumps(entry, sort_keys=True) + "\n" for entry in lines), encoding="utf-8")


def replay(tmp_path: Path, forge: FakeForge, capsys) -> tuple[int, dict, str]:
    manifest, _ = scenario(tmp_path)
    action = writeAction(tmp_path, manifest, planFor(manifest))
    code = main(["--root", str(tmp_path), "--action", str(action), "--run-id", "R1"], forgeFactory=lambda repo, token: forge)
    captured = capsys.readouterr()
    return code, json.loads(captured.out.strip().splitlines()[-1]), captured.err


LEGACY = {"stewardOwner": None, "worker": None, "authority": None, "closureProof": None, "after": None}


@pytest.mark.parametrize("changes, fragment", [
    (LEGACY, "stewardOwner"),
    ({"authority": None}, "approved closure authority"),
    ({"closureProof": None}, "no closureProof"),
    ({"before": None}, "before state"),
    ({"after": None}, "no after state"),
    ({"after": {"state": "open", "verified": False}}, "must be null"),
    ({"after": {"state": "open", "verified": True}}, "not closed"),
])
def test_a_malformed_or_contradictory_receipt_is_never_replayed_as_a_close(tmp_path, capsys, changes, fragment) -> None:
    forge = FakeForge({10: liveOf(scenarioRow(10))})
    code, outcome, _ = runClose(tmp_path, forge, capsys)
    assert code == EXIT_OK and outcome["outcome"] == "closed"
    rewriteClosedReceipt(tmp_path, **changes)
    callsBefore = len(forge.calls)

    code, printed, err = replay(tmp_path, forge, capsys)

    assert code == EXIT_REFUSED
    assert printed["outcome"] == "refused" and printed["reason"] == "receipt-invalid"
    assert fragment in printed["failure"] and "does not prove the closure" in err
    assert len(forge.calls) == callsBefore  # replay never re-closes and never re-reads


def test_a_valid_receipt_still_replays_as_the_recorded_close(tmp_path, capsys) -> None:
    forge = FakeForge({10: liveOf(scenarioRow(10))})
    runClose(tmp_path, forge, capsys)

    code, printed, _ = replay(tmp_path, forge, capsys)

    assert code == EXIT_OK and printed["outcome"] == "closed" and printed["stewardOwner"] == "steward-owner-test"


def test_an_after_observation_of_open_is_not_reported_as_a_close_by_the_direct_cli(tmp_path, capsys) -> None:
    class StaleAfterClose(FakeForge):
        def getIssue(self, number):
            issue = super().getIssue(number)
            if ("close", number) in [call[:2] for call in self.calls]:
                issue["state"] = "open"
            return issue

    forge = StaleAfterClose({10: liveOf(scenarioRow(10))})

    code, outcome, err = runClose(tmp_path, forge, capsys)

    assert code == EXIT_REFUSED
    assert outcome["outcome"] == "refused" and outcome["reason"] == "receipt-invalid"
    assert "closed" not in {outcome.get("outcome")} and "does not prove the closure" in err
    assert receiptLines(tmp_path)[-1]["after"]["state"] == "open"  # the observation is still on the record


def test_an_already_closed_receipt_is_validated_at_replay_too(tmp_path, capsys) -> None:
    live = liveOf(scenarioRow(10))
    live["state"] = "closed"
    forge = FakeForge({10: live})
    code, outcome, _ = runClose(tmp_path, forge, capsys)
    assert code == EXIT_OK and outcome["outcome"] == "already-closed"
    path = tmp_path / RECEIPT
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for entry in lines:
        if entry.get("outcome") == "already-closed":
            entry.pop("after")
    path.write_text("".join(json.dumps(entry, sort_keys=True) + "\n" for entry in lines), encoding="utf-8")

    code, printed, _ = replay(tmp_path, forge, capsys)

    assert code == EXIT_REFUSED and printed["reason"] == "receipt-invalid"


def test_the_apply_closures_path_refuses_to_report_an_unproven_close(tmp_path, capsys) -> None:
    from scripts.steward_issue_reconcile import main as reconcileMain
    from tests.steward.issuehygiene.test_b5_pilot import liveForges, pilotReceipts, twoChildCheckout
    from tests.steward.issuehygiene.test_b_reconcile import censusOf, umbrellaRow

    class StaleAfterClose(type(liveForges())):
        def getIssue(self, number):
            issue = super().getIssue(number)
            if any(call[0] == "close" and call[1] == number for call in self.calls):
                issue["state"] = "open"
            return issue

    root = twoChildCheckout(tmp_path, policy={"writesEnabled": True})
    forge = StaleAfterClose(liveForges().issues)
    repo = censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0")]).document["repo"]

    code = reconcileMain(
        ["--root", str(root), "--apply-closures", "--receipts", str(pilotReceipts(root)), "--i-understand-writes",
         "--repo", repo, "--max-closures", "1"],
        forgeFactory=lambda name, secret: forge,
    )
    captured = capsys.readouterr()

    assert code == EXIT_REFUSED
    assert "refusing to report" in captured.err and '"closed"' not in captured.out
