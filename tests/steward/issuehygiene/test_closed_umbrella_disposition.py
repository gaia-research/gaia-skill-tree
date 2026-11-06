"""Founder ruling #6 (steward-closed-umbrella-disposition): a closed upstream umbrella is a completed epic.

A repeat of that exact batch is duplicate processing and is suppressed. A genuinely new version or candidate is new
work. Unfinished children or contradicting registry evidence raise a HIGH-PRIORITY closeout discrepancy: the closure
is preserved, nothing is reopened, closed or declared complete, and the discrepancy is surfaced for explicit
reconciliation.
"""

from __future__ import annotations

import json
from pathlib import Path

from gaia_cli.steward.issuehygiene.sensor import IssueHygieneSensor
from tests.steward.issuehygiene.test_b_reconcile import (
    BLOB,
    censusOf,
    childRow,
    item,
    mkRow,
    policyFor,
    run,
    skill,
    umbrellaRow,
    writeNamed,
)
from tests.steward.issuehygiene.test_d1_sensor import makeManifest, stubReconcile  # noqa: F401  (shared seam)

SUITE = "obra/superpowers"


def closedUmbrella(number, version="v7.0.0", adds=(), reason="completed", skillId=SUITE):
    row = umbrellaRow(number, skillId, version, adds=adds)
    row.update({"state": "closed", "stateReason": reason, "closedAt": "2026-10-20T12:00:00Z"})
    return row


def suiteRecord(root: Path, version: str) -> None:
    writeNamed(root, SUITE, skill(SUITE, extra=f"upstream:\n  repo: {SUITE}\n  version: {version}\n"))


# --------------------------------------------------------------- suppression of the same batch


def test_repeat_of_a_closed_batch_is_suppressed_not_reviewed(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"])], closed=[closedUmbrella(20, adds=["alpha", "beta"])])

    manifest = run(census, tmp_path)

    umbrella = item(manifest, 30)
    assert umbrella["authority"] == "none"
    assert umbrella["state"] == "held"
    assert "closed-umbrella-duplicate:#20" in umbrella["notProven"]
    assert any(entry["ref"] == "#20" for entry in umbrella["evidence"])
    assert umbrella["proposedTransition"]["action"] == "keep"
    assert manifest["batches"] == []


def test_children_of_a_repeat_batch_are_suppressed_too(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf(
        [umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), childRow(31, "obra/alpha", BLOB, parent=30)],
        closed=[closedUmbrella(20, adds=["alpha"])],
    )

    manifest = run(census, tmp_path)

    child = item(manifest, 31)
    assert child["authority"] == "none" and child["state"] == "held"
    assert "closed-umbrella-duplicate:#20" in child["notProven"]
    assert manifest["batches"] == []


def test_a_new_version_is_new_work(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.1.0", adds=["alpha"])], closed=[closedUmbrella(20, adds=["alpha"])])

    umbrella = item(run(census, tmp_path), 30)

    assert umbrella["authority"] == "B"
    assert not any(reason.startswith("closed-umbrella-duplicate") for reason in umbrella["notProven"])


def test_a_new_candidate_in_the_same_version_is_new_work(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha", "gamma"])], closed=[closedUmbrella(20, adds=["alpha"])])

    umbrella = item(run(census, tmp_path), 30)

    assert umbrella["authority"] == "B"
    assert not any(reason.startswith("closed-umbrella-duplicate") for reason in umbrella["notProven"])


def test_an_unreadable_closed_payload_never_suppresses(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    broken = closedUmbrella(20)
    broken["body"] = "no payload"
    broken["bodySha256"] = __import__("hashlib").sha256(b"no payload").hexdigest()
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"])], closed=[broken])

    assert item(run(census, tmp_path), 30)["authority"] == "B"


def test_another_suite_with_the_same_version_is_not_a_repeat(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"])],
                      closed=[closedUmbrella(20, adds=["alpha"], skillId="obra/other")])

    assert item(run(census, tmp_path), 30)["authority"] == "B"


def test_a_proven_closure_of_a_repeat_is_not_suppressed(tmp_path: Path) -> None:
    """Suppression stops duplicate processing. It never takes away a closure the registry already proves."""
    suiteRecord(tmp_path, "v7.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"])], closed=[closedUmbrella(20, adds=["alpha"])])

    umbrella = item(run(census, tmp_path), 30)

    assert umbrella["authority"] == "A" and umbrella["ruleId"] == "A2-umbrella-synced"


# --------------------------------------------------------------- closeout discrepancy


def test_unfinished_children_of_a_closed_umbrella_are_a_high_priority_discrepancy(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v7.0.0")
    census = censusOf([childRow(31, "obra/alpha", BLOB, parent=20)], closed=[closedUmbrella(20, adds=["alpha"])])

    manifest = run(census, tmp_path)

    assert manifest["stats"]["closeoutDiscrepancies"] == 1
    [finding] = manifest["closeoutDiscrepancies"]
    assert finding["umbrella"] == 20 and finding["priority"] == "high"
    assert finding["openChildren"] == [31]
    assert finding["reasons"] == ["unfinished-children:1"]
    assert finding["disposition"] == "preserve-closure-investigate-reconcile"
    assert "closeout-discrepancy:#20" in item(manifest, 31)["notProven"]
    # The closure is preserved and completion is never fabricated: the child is not closed, accepted or reopened.
    assert item(manifest, 31)["proposedTransition"]["action"] == "keep"


def test_children_listed_by_the_closed_umbrella_count_even_without_a_parent_reference(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v7.0.0")
    closed = closedUmbrella(20, adds=["alpha"])
    closed["body"] += "\n- #31\n"
    closed["bodySha256"] = __import__("hashlib").sha256(closed["body"].encode()).hexdigest()
    census = censusOf([childRow(31, "obra/alpha", BLOB, parent=None)], closed=[closed])

    assert run(census, tmp_path)["closeoutDiscrepancies"][0]["openChildren"] == [31]


def test_a_closure_the_registry_contradicts_is_a_discrepancy(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([], closed=[closedUmbrella(20, version="v7.0.0")])

    [finding] = run(census, tmp_path)["closeoutDiscrepancies"]

    assert finding["reasons"] == ["registry-behind-closure:registry=v6.0.0,umbrella=v7.0.0"]
    assert finding["openChildren"] == []
    assert any(entry["type"] == "registry" for entry in finding["evidence"])


def test_a_merged_sync_pull_request_answers_the_registry_contradiction(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    sync = mkRow(99, f"[upstream sync] {SUITE} -> v7.0.0", "sync", isPullRequest=True, mergedAt="2026-10-20T11:00:00Z", state="closed")
    census = censusOf([], closed=[closedUmbrella(20, version="v7.0.0"), sync])

    assert run(census, tmp_path)["closeoutDiscrepancies"] == []


def test_a_closed_umbrella_the_registry_agrees_with_raises_nothing(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v7.0.0")
    census = censusOf([], closed=[closedUmbrella(20, version="v7.0.0")])

    manifest = run(census, tmp_path)

    assert manifest["closeoutDiscrepancies"] == []
    assert manifest["stats"]["closeoutDiscrepancies"] == 0


def test_a_rejected_umbrella_is_not_contradicted_by_a_registry_that_lacks_it(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([], closed=[closedUmbrella(20, version="v7.0.0", reason="not_planned")])

    assert run(census, tmp_path)["closeoutDiscrepancies"] == []


def test_an_older_closed_umbrella_than_the_registry_is_consistent(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v8.0.0")
    census = censusOf([], closed=[closedUmbrella(20, version="v7.0.0")])

    assert run(census, tmp_path)["closeoutDiscrepancies"] == []


def test_the_manifest_is_deterministic_with_discrepancies(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([childRow(31, "obra/alpha", BLOB, parent=20)], closed=[closedUmbrella(20, adds=["alpha"])])

    assert json.dumps(run(census, tmp_path), sort_keys=True) == json.dumps(run(census, tmp_path), sort_keys=True)


def test_incomplete_census_raises_no_discrepancy(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([childRow(31, "obra/alpha", BLOB, parent=20)], closed=[closedUmbrella(20, adds=["alpha"])], complete=False)

    manifest = run(census, tmp_path)

    assert manifest["closeoutDiscrepancies"] == []


# --------------------------------------------------------------- the sensor and the desk


def closeoutNotes(manifest):
    sensor = IssueHygieneSensor()
    scan = sensor._observations(manifest, policyFor(writesEnabled=False), "2026-10-21T19:30:00Z")
    return [o for o in scan.observations if o.subject.id == "closeout-discrepancy"]


def reconciledManifest(tmp_path: Path):
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([childRow(31, "obra/alpha", BLOB, parent=20)], closed=[closedUmbrella(20, adds=["alpha"])])
    return run(census, tmp_path)


def test_sensor_raises_one_high_priority_founder_note(tmp_path: Path) -> None:
    [note] = closeoutNotes(reconciledManifest(tmp_path))

    state = note.observed_state
    assert note.kind == "issue_founder_decision"
    assert state["priority"] == "high"
    assert state["decisionTarget"] == "issue-question/closeout-discrepancy"
    assert state["affected"] == [20, 31]
    assert state["recommendation"] == "reconcile-missed-work"
    assert "HIGH PRIORITY" in state["question"] and "closure is preserved" in state["question"]
    assert state["discrepancies"][0]["openChildren"] == [31]
    assert "reopen" not in " ".join(state["options"])


def test_sensor_stays_quiet_without_a_discrepancy(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v7.0.0")
    manifest = run(censusOf([], closed=[closedUmbrella(20)]), tmp_path)

    assert closeoutNotes(manifest) == []


def test_sensor_tolerates_a_manifest_without_the_section(tmp_path: Path) -> None:
    manifest = reconciledManifest(tmp_path)
    manifest.pop("closeoutDiscrepancies")

    assert closeoutNotes(manifest) == []


def test_reconcile_script_summary_and_matrix_name_the_discrepancy(tmp_path: Path) -> None:
    from scripts.steward_issue_reconcile import renderMatrix, renderSummary

    manifest = reconciledManifest(tmp_path)

    assert "HIGH PRIORITY closeout discrepancy: closed umbrella #20" in renderSummary(manifest, 0, writesEnabled=False)
    assert "Closure preserved; reconcile explicitly." in renderMatrix(manifest)


def test_desk_ranks_the_closeout_discrepancy_above_routine_class_c() -> None:
    from gaia_cli.steward import desk

    assert desk._PRIORITY_CREDENTIAL < desk._PRIORITY_CLOSEOUT < desk._PRIORITY_ESCALATED < desk._PRIORITY_CLASS_C
    assert desk.CLOSEOUT_TARGET == "issue-question/closeout-discrepancy"
