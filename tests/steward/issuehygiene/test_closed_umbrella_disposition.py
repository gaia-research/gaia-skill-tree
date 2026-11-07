"""Founder ruling #6 (steward-closed-umbrella-disposition): a closed upstream umbrella is a completed epic.

A repeat of that exact batch is duplicate processing and is suppressed. A genuinely new version or candidate is new
work. Unfinished children or contradicting registry evidence raise a HIGH-PRIORITY closeout discrepancy: the closure
is preserved, nothing is reopened, closed or declared complete, and the discrepancy is surfaced for explicit
reconciliation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.sensor import IssueHygieneSensor
from tests.steward.issuehygiene.test_b_reconcile import (
    BLOB,
    censusOf as baseCensusOf,
    childRow,
    item,
    mkRow,
    policyFor,
    run as baseRun,
    skill,
    umbrellaRow,
    writeNamed,
)
from tests.steward.issuehygiene.test_d1_sensor import makeManifest, stubReconcile  # noqa: F401  (shared seam)

SUITE = "obra/superpowers"


def run(census, root, policy=None, decisions=()):
    """``test_b_reconcile.run`` plus founder decision records for the lock cases."""
    from gaia_cli.steward.issuehygiene.reconcile import reconcile
    from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
    from tests.steward.issuehygiene.test_b_reconcile import NOW

    (root / "registry" / "named").mkdir(parents=True, exist_ok=True)
    return reconcile(census, buildRegistryIndex(root), policy or policyFor(), NOW, decisionRecords=tuple(decisions))
UMBRELLA_LABELS = ["upstream:release", "upstream:bootstrap"]


def historySection(rows, complete=True, reason=None):
    section = {"complete": complete, "labels": list(UMBRELLA_LABELS), "pagesFetched": 1, "items": list(rows) if complete else []}
    if reason:
        section["reason"] = reason
    return section


def censusOf(rows, closed=(), complete=True, history=None):
    """A census whose closed umbrella history is every closed umbrella row given (windowed or not), plus ``history``."""
    census = baseCensusOf(rows, closed=closed, complete=complete)
    umbrellas = [row for row in list(closed) + list(history or []) if "upstream:release" in row.get("labels", ())]
    census.document["closedUmbrellas"] = historySection({row["number"]: row for row in umbrellas}.values())
    return census


def closedUmbrella(number, version="v7.0.0", adds=(), reason="completed", skillId=SUITE):
    row = umbrellaRow(number, skillId, version, adds=adds)
    row.update({"state": "closed", "stateReason": reason, "closedAt": "2026-10-20T12:00:00Z"})
    return row


def closedChild(number, suggested, parent, url=None):
    """A recently closed child intake of a closed umbrella: the authoritative full identity of a legacy slug row."""
    row = childRow(number, suggested, url or BLOB.replace("writing-skills", suggested.split("/")[1]), parent=parent)
    row.update({"state": "closed", "stateReason": "completed", "closedAt": "2026-10-20T12:00:00Z"})
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


def test_children_of_a_repeat_batch_with_a_proven_identity_are_suppressed_too(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf(
        [umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), childRow(31, "obra/alpha", BLOB.replace("writing-skills", "alpha"), parent=30)],
        closed=[closedUmbrella(20, adds=["alpha"]), closedChild(21, "obra/alpha", parent=20)],
    )

    manifest = run(census, tmp_path)

    child = item(manifest, 31)
    assert child["authority"] == "none" and child["state"] == "held"
    assert "closed-umbrella-duplicate:#20" in child["notProven"]
    assert manifest["batches"] == []


def test_a_legacy_slug_row_without_a_known_identity_fails_closed(tmp_path: Path) -> None:
    """The closed batch lists only the slug alpha and its own child intake is no longer in the census: the full
    identity cannot be established, so the child is neither held as a duplicate nor dispatched."""
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf(
        [umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), childRow(31, "obra/alpha", BLOB.replace("writing-skills", "alpha"), parent=30)],
        closed=[closedUmbrella(20, adds=["alpha"])],
    )

    manifest = run(census, tmp_path)

    child = item(manifest, 31)
    assert child["state"] == "not-evaluated" and child["authority"] == "none"
    assert "closed-batch-candidate-identity-ambiguous:#20" in child["unknowns"]
    assert not any(reason.startswith("closed-umbrella-duplicate") for reason in child["notProven"])
    assert all(child["key"] not in batch["classB"] for batch in manifest["batches"])


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


# --------------------------------------------------------------- per-child matching (review of #2330)


def gammaChild(number, parent):
    return childRow(number, "obra/gamma", BLOB.replace("writing-skills", "gamma"), parent=parent)


def test_a_new_child_under_a_repeated_umbrella_is_new_work(tmp_path: Path) -> None:
    """Closed #20 lists alpha; open #30 repeats alpha; child #31 is obra/gamma: #30 is held, #31 is not."""
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), gammaChild(31, 30)],
                      closed=[closedUmbrella(20, adds=["alpha"])])

    manifest = run(census, tmp_path)

    assert item(manifest, 30)["state"] == "held"
    child = item(manifest, 31)
    assert child["authority"] == "B" and child["state"] != "held"
    assert not any(reason.startswith("closed-umbrella-duplicate") for reason in child["notProven"])
    assert any(child["key"] in batch["classB"] for batch in manifest["batches"])


def test_only_the_matching_children_of_a_repeated_umbrella_are_held(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf(
        [umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]),
         childRow(31, "obra/alpha", BLOB.replace("writing-skills", "alpha"), parent=30), gammaChild(32, 30)],
        closed=[closedUmbrella(20, adds=["alpha"]), closedChild(21, "obra/alpha", parent=20)],
    )

    manifest = run(census, tmp_path)

    assert item(manifest, 31)["state"] == "held" and "closed-umbrella-duplicate:#20" in item(manifest, 31)["notProven"]
    assert item(manifest, 32)["authority"] == "B"


def test_a_child_named_by_the_closed_batch_rows_is_a_positive_match(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    payload = {"skillId": SUITE, "newVersion": "v7.0.0", "payloadVersion": 2,
               "candidates": [{"id": f"{SUITE}:delta", "suggestedId": "obra/delta", "slug": "delta", "child": 41}]}
    body = "<!-- gaia-upstream-payload\n" + json.dumps(payload) + "\n-->\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    closed = closedUmbrella(20)
    closed.update(body=body, bodySha256=digest)
    openRow = umbrellaRow(30, SUITE, "v7.0.0")
    openRow.update(body=body, bodySha256=digest)
    census = censusOf([openRow, childRow(41, "obra/delta", BLOB.replace("writing-skills", "delta"), parent=30)], closed=[closed])

    manifest = run(census, tmp_path)

    assert item(manifest, 30)["state"] == "held"
    assert item(manifest, 41)["state"] == "held"


# --------------------------------------------------------------- the closed history has no age window


def oldClosedUmbrella(number, version="v7.0.0", adds=()):
    row = closedUmbrella(number, version=version, adds=adds)
    row["closedAt"] = "2026-06-01T12:00:00Z"  # far outside the 30-day window
    return row


def test_an_older_closure_with_an_outstanding_child_is_reported(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v7.0.0")
    census = censusOf([childRow(31, "obra/alpha", BLOB, parent=20)], history=[oldClosedUmbrella(20, adds=["alpha"])])
    assert census.document["recentlyClosed"] == []  # the window never saw it

    manifest = run(census, tmp_path)

    [finding] = manifest["closeoutDiscrepancies"]
    assert finding["umbrella"] == 20 and finding["openChildren"] == [31] and finding["closedAt"] == "2026-06-01T12:00:00Z"
    assert "closeout-discrepancy:#20" in item(manifest, 31)["notProven"]
    assert manifest["closeoutEvaluation"] == {"status": "evaluated", "reasons": []}


def test_a_repeat_of_an_older_closed_batch_is_still_suppressed(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"])], history=[oldClosedUmbrella(20, adds=["alpha"])])

    assert item(run(census, tmp_path), 30)["state"] == "held"


def test_an_older_closed_batch_with_a_registry_contradiction_is_reported(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([], history=[oldClosedUmbrella(20, version="v7.0.0")])

    [finding] = run(census, tmp_path)["closeoutDiscrepancies"]

    assert finding["reasons"][0].startswith("registry-behind-closure")


def breakHistory(kind, document):
    section = document.get("closedUmbrellas")
    if kind == "absent":
        document.pop("closedUmbrellas")
    elif kind == "incomplete":
        document["closedUmbrellas"] = historySection([], complete=False, reason="release:rate-limited")
    elif kind == "labels":
        section["labels"] = ["upstream:release"]
    elif kind == "digest":
        section["items"][0]["bodySha256"] = "0" * 64
    elif kind == "open":
        section["items"][0]["state"] = "open"


@pytest.mark.parametrize("kind, reason", [
    ("absent", "closed-umbrella-history-absent"),
    ("incomplete", "closed-umbrella-history-incomplete:release:rate-limited"),
    ("labels", "closed-umbrella-history-labels-differ"),
    ("digest", "closed-umbrella-history-body-mismatch:#20"),
    ("open", "closed-umbrella-history-row-invalid:#20"),
])
def test_an_unusable_history_leaves_only_the_umbrella_decisions_not_evaluated(tmp_path: Path, kind, reason) -> None:
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB))
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf(
        [umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), childRow(10, "obra/writing-skills", BLOB, parent=30),
         childRow(31, "obra/alpha", BLOB, parent=20),
         childRow(12, "obra/standalone", BLOB.replace("writing-skills", "standalone"), parent=None)],
        history=[oldClosedUmbrella(20, adds=["alpha"])],
    )
    breakHistory(kind, census.document)

    manifest = run(census, tmp_path)

    assert manifest["closeoutEvaluation"] == {"status": "not-evaluated", "reasons": [reason]}
    assert manifest["closeoutDiscrepancies"] == []
    # Fail closed: every umbrella and every child that names a parent is not-evaluated, including the A1-proven child.
    # Only work that cannot depend on a closed umbrella (a child with no umbrella) proceeds.
    for number in (10, 30, 31):
        entry = item(manifest, number)
        assert entry["state"] == "not-evaluated" and entry["authority"] == "none" and entry["ruleId"] is None
        assert "closed-umbrella-history-not-evaluated" in entry["unknowns"]
        assert entry["proposedTransition"]["action"] == "keep"
    assert item(manifest, 12)["authority"] == "B" and item(manifest, 12)["state"] != "not-evaluated"
    assert sorted(manifest["coverage"]["notEvaluated"]) == [10, 30, 31]
    assert manifest["coverage"]["unknown"] == [] and manifest["censusStatus"] == "complete"


# ------------------------------------------------ the guard runs before proofs, disabled rules, locks and questions


def noHistory(census):
    census.document.pop("closedUmbrellas")
    return census


def test_an_a1_proven_parented_child_is_not_closable_while_history_is_missing(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB))
    rows = [umbrellaRow(30, SUITE, "v7.0.0"), childRow(10, "obra/writing-skills", BLOB, parent=30)]
    suiteRecord(tmp_path, "v6.0.0")
    proven = item(run(censusOf(rows), tmp_path), 10)
    assert proven["authority"] == "A" and proven["ruleId"] == "A1-child-curated"  # closable once the history is read

    manifest = run(noHistory(censusOf(rows)), tmp_path)

    child = item(manifest, 10)
    assert (child["state"], child["authority"], child["ruleId"]) == ("not-evaluated", "none", None)
    assert child["proposedTransition"]["action"] == "keep"
    from gaia_cli.steward.issuehygiene.closure import planClosures

    assert planClosures(manifest, policyFor()) == []


def test_a_disabled_rule_proof_does_not_return_as_b_actionable_without_history(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB))
    suiteRecord(tmp_path, "v6.0.0")
    rows = [umbrellaRow(30, SUITE, "v7.0.0"), childRow(10, "obra/writing-skills", BLOB, parent=30)]
    policy = policyFor(enabledRules=["A2-umbrella-synced"])
    withHistory = item(run(censusOf(rows), tmp_path, policy), 10)
    assert withHistory["authority"] == "B" and "rule-disabled:A1-child-curated" in withHistory["notProven"]

    manifest = run(noHistory(censusOf(rows)), tmp_path, policy)

    child = item(manifest, 10)
    assert (child["state"], child["authority"]) == ("not-evaluated", "none")
    assert all(child["key"] not in batch["classB"] for batch in manifest["batches"])


def test_a_founder_locked_b_item_is_not_dispatched_without_history(tmp_path: Path) -> None:
    from gaia_cli.steward.issuehygiene.questions import loadIssueDecisions
    from tests.steward.issuehygiene.test_founder_locks_2283 import ROOT, rows

    records = loadIssueDecisions(ROOT)
    (tmp_path / "registry/named").mkdir(parents=True, exist_ok=True)
    withHistory = run(censusOf(rows()), tmp_path, decisions=records)
    assert item(withHistory, 1833)["authority"] == "B"  # technical-reconciliation-only stays bounded Class B

    manifest = run(noHistory(censusOf(rows())), tmp_path, decisions=records)

    locked = item(manifest, 1833)
    assert (locked["state"], locked["authority"]) == ("not-evaluated", "none")
    assert all(locked["key"] not in batch["classB"] for batch in manifest["batches"])
    assert item(manifest, 9999)["state"] == "not-evaluated"  # an ordinary umbrella is history-dependent too
    # Locked holds stay inert holds; bots and the like are unrelated work and proceed.
    assert item(manifest, 2002)["state"] == "held"
    assert item(manifest, 2126)["state"] == "held"


def test_a_history_dependent_founder_question_is_not_raised_without_history(tmp_path: Path) -> None:
    writeNamed(tmp_path, "someone/alpha", skill("someone/alpha", github="https://github.com/someone/skills/blob/main/skills/alpha/SKILL.md"))
    suiteRecord(tmp_path, "v6.0.0")
    rows = [umbrellaRow(30, SUITE, "v7.0.0"), childRow(31, "obra/alpha", BLOB.replace("writing-skills", "alpha"), parent=30)]
    withHistory = run(censusOf(rows), tmp_path)
    assert item(withHistory, 31)["authority"] == "C" and withHistory["founderQuestions"]

    manifest = run(noHistory(censusOf(rows)), tmp_path)

    child = item(manifest, 31)
    assert (child["state"], child["authority"], child["questions"]) == ("not-evaluated", "none", [])
    assert manifest["founderQuestions"] == []


def test_the_sensor_reports_the_history_scope_as_skipped_and_nothing_else(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([])
    census.document.pop("closedUmbrellas")
    manifest = run(census, tmp_path)

    scan = IssueHygieneSensor()._observations(manifest, policyFor(writesEnabled=False), "2026-10-21T19:30:00Z")

    assert [(row["subjectType"], row["subjectId"]) for row in scan.skipped] == [("issue-scope", "closed-umbrella-history")]
    assert "closed-batch suppression and closeout discrepancies" in scan.skipped[0]["reason"]


def test_the_sensor_skips_nothing_when_the_history_is_evaluated(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v7.0.0")
    manifest = run(censusOf([]), tmp_path)

    scan = IssueHygieneSensor()._observations(manifest, policyFor(writesEnabled=False), "2026-10-21T19:30:00Z")

    assert scan.skipped == ()


def test_missing_history_never_dispatches_a_possible_repeat(tmp_path: Path) -> None:
    """Review repro: with the history removed, open #30 (a repeat of closed #20) must not become actionable."""
    suiteRecord(tmp_path, "v6.0.0")
    withHistory = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"])], closed=[closedUmbrella(20, adds=["alpha"])])
    assert item(run(withHistory, tmp_path), 30)["state"] == "held"
    withoutHistory = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"])], closed=[closedUmbrella(20, adds=["alpha"])])
    withoutHistory.document.pop("closedUmbrellas")

    manifest = run(withoutHistory, tmp_path)

    umbrella = item(manifest, 30)
    assert umbrella["authority"] == "none" and umbrella["state"] == "not-evaluated"
    assert manifest["batches"] == []
    scan = IssueHygieneSensor()._observations(manifest, policyFor(writesEnabled=False), "2026-10-21T19:30:00Z")
    assert not [o for o in scan.observations if o.kind == "issue_suite_review"]
    assert {row["subjectId"] for row in scan.skipped} == {"closed-umbrella-history", "unevaluated-issues"}


# --------------------------------------------------------------- full candidate identity, never a bare slug


def test_a_same_slug_candidate_from_another_repository_is_new_work(tmp_path: Path) -> None:
    """Review repro: closed #20 alpha, repeat #30 alpha, new #31 different/alpha pointing at a different repository."""
    suiteRecord(tmp_path, "v6.0.0")
    elsewhere = "https://github.com/different/unrelated/blob/main/skills/alpha/SKILL.md"
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), childRow(31, "different/alpha", elsewhere, parent=30)],
                      closed=[closedUmbrella(20, adds=["alpha"])])

    manifest = run(census, tmp_path)

    assert item(manifest, 30)["state"] == "held"
    child = item(manifest, 31)
    assert child["authority"] == "B" and child["state"] != "held"
    assert not any(reason.startswith("closed-umbrella-duplicate") for reason in child["notProven"])


def sameRepoOtherContributor(number, parent):
    return childRow(number, "different/alpha", BLOB.replace("writing-skills", "alpha"), parent=parent)


def test_a_same_repository_same_slug_other_contributor_is_not_held_without_a_known_identity(tmp_path: Path) -> None:
    """Review repro: #31 has suggested id different/alpha with superpowers evidence. It must not be held."""
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), sameRepoOtherContributor(31, 30)],
                      closed=[closedUmbrella(20, adds=["alpha"])])

    child = item(run(census, tmp_path), 31)

    assert child["state"] == "not-evaluated" and child["authority"] == "none"
    assert not any(reason.startswith("closed-umbrella-duplicate") for reason in child["notProven"])


def test_a_known_closed_child_with_another_identity_does_not_prove_the_same_slug_is_new(tmp_path: Path) -> None:
    """The census holds only a window of closed issues, so one differently named closed child never excludes others."""
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), sameRepoOtherContributor(31, 30)],
                      closed=[closedUmbrella(20, adds=["alpha"]), closedChild(21, "obra/alpha", parent=20)])

    child = item(run(census, tmp_path), 31)

    assert child["state"] == "not-evaluated" and child["authority"] == "none"
    assert "closed-batch-candidate-identity-ambiguous:#20" in child["unknowns"]


def test_a_known_closed_child_with_the_same_identity_is_a_duplicate(tmp_path: Path) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]),
                       childRow(31, "obra/alpha", BLOB.replace("writing-skills", "alpha"), parent=30)],
                      closed=[closedUmbrella(20, adds=["alpha"]), closedChild(21, "obra/alpha", parent=20)])

    assert item(run(census, tmp_path), 31)["state"] == "held"


def v2Body(rows):
    payload = {"skillId": SUITE, "newVersion": "v7.0.0", "payloadVersion": 2, "candidates": rows}
    body = "<!-- gaia-upstream-payload\n" + json.dumps(payload) + "\n-->\n"
    return body, hashlib.sha256(body.encode()).hexdigest()


@pytest.mark.parametrize("candidate, evidence, held", [
    ("obra/delta", f"https://github.com/{SUITE}/blob/main/skills/delta/SKILL.md", True),
    ("other/delta", f"https://github.com/{SUITE}/blob/main/skills/delta/SKILL.md", False),   # another contributor
    ("obra/delta", "https://github.com/elsewhere/repo/blob/main/skills/delta/SKILL.md", False),  # another repository
    ("obra/delta", None, False),  # no evidence repository: nothing positive to match
])
def test_a_v2_row_matches_only_on_full_identity_and_repository(tmp_path: Path, candidate, evidence, held) -> None:
    suiteRecord(tmp_path, "v6.0.0")
    rows = [{"id": f"{SUITE}:delta", "suggestedId": "obra/delta", "slug": "delta"}]
    body, digest = v2Body(rows)
    closed = closedUmbrella(20)
    closed.update(body=body, bodySha256=digest)
    open30 = umbrellaRow(30, SUITE, "v7.0.0")
    open30.update(body=body, bodySha256=digest)
    child = childRow(31, candidate, evidence or "", parent=30)
    census = censusOf([open30, child], closed=[closed])

    entry = item(run(census, tmp_path), 31)

    assert (entry["state"] == "held") is held


# --------------------------------------------- the closed-batch verdict precedes proofs (round-4 review)


def provenAlphaCensus(tmp_path: Path, candidate: str, closedExtra=()):
    """Closed #20 has legacy adds alpha; #30 repeats it; child #31 carries an A1 proof from a matching registry entry."""
    evidence = BLOB.replace("writing-skills", "alpha")
    writeNamed(tmp_path, candidate, skill(candidate, github=evidence))
    suiteRecord(tmp_path, "v6.0.0")
    rows = [umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), childRow(31, candidate, evidence, parent=30)]
    return censusOf(rows, closed=[closedUmbrella(20, adds=["alpha"]), *closedExtra])


def test_an_a1_proven_child_with_an_ambiguous_legacy_identity_is_not_closable(tmp_path: Path) -> None:
    """Review repro: #31 different/alpha, suite-repository evidence, matching registry entry, no attributable closed child."""
    census = provenAlphaCensus(tmp_path, "different/alpha")

    manifest = run(census, tmp_path)

    child = item(manifest, 31)
    assert (child["state"], child["authority"], child["ruleId"]) == ("not-evaluated", "none", None)
    assert child["proposedTransition"]["action"] == "keep"
    assert "closed-batch-candidate-identity-ambiguous:#20" in child["unknowns"]
    from gaia_cli.steward.issuehygiene.closure import planClosures

    assert planClosures(manifest, policyFor()) == []
    assert all(child["key"] not in batch["classB"] for batch in manifest["batches"])


def test_the_same_proven_child_outside_a_repeated_batch_still_closes(tmp_path: Path) -> None:
    evidence = BLOB.replace("writing-skills", "alpha")
    writeNamed(tmp_path, "different/alpha", skill("different/alpha", github=evidence))
    suiteRecord(tmp_path, "v6.0.0")
    census = censusOf([umbrellaRow(30, SUITE, "v7.1.0", adds=["alpha"]), childRow(31, "different/alpha", evidence, parent=30)],
                      closed=[closedUmbrella(20, adds=["alpha"])])  # a new version: not a repeat

    child = item(run(census, tmp_path), 31)

    assert child["authority"] == "A" and child["ruleId"] == "A1-child-curated"


def test_a_proven_child_matching_a_known_closed_identity_may_still_be_closed(tmp_path: Path) -> None:
    census = provenAlphaCensus(tmp_path, "obra/alpha", closedExtra=[closedChild(21, "obra/alpha", parent=20)])

    child = item(run(census, tmp_path), 31)

    assert child["authority"] == "A" and child["ruleId"] == "A1-child-curated"  # a registry-proven closure is cleanup


def test_a_matched_duplicate_with_a_disabled_rule_proof_is_held_not_dispatched(tmp_path: Path) -> None:
    census = provenAlphaCensus(tmp_path, "obra/alpha", closedExtra=[closedChild(21, "obra/alpha", parent=20)])

    manifest = run(census, tmp_path, policy=policyFor(enabledRules=["A2-umbrella-synced"]))

    child = item(manifest, 31)
    assert (child["state"], child["authority"], child["ruleId"]) == ("held", "none", None)
    assert "closed-umbrella-duplicate:#20" in child["notProven"]
    assert all(child["key"] not in batch["classB"] for batch in manifest["batches"])


def test_a_v2_row_without_a_suggested_id_is_ambiguous_even_for_a_proven_child(tmp_path: Path) -> None:
    evidence = f"https://github.com/{SUITE}/blob/main/skills/delta/SKILL.md"
    writeNamed(tmp_path, "obra/delta", skill("obra/delta", github=evidence))
    suiteRecord(tmp_path, "v6.0.0")
    body, digest = v2Body([{"id": f"{SUITE}:delta", "slug": "delta"}])  # no suggestedId: identity unproven
    closed = closedUmbrella(20)
    closed.update(body=body, bodySha256=digest)
    open30 = umbrellaRow(30, SUITE, "v7.0.0")
    open30.update(body=body, bodySha256=digest)
    census = censusOf([open30, childRow(31, "obra/delta", evidence, parent=30)], closed=[closed])

    child = item(run(census, tmp_path), 31)

    assert (child["state"], child["authority"]) == ("not-evaluated", "none")


def test_a_repeated_umbrella_whose_a3_proof_is_invalidated_by_a_closed_superseder_is_held_not_dispatched(tmp_path: Path) -> None:
    """Review repro (round 5 P1): open #30 initially matches A3 superseded by newer open #40.

    When #40 is closed in the same pass (A2), #30 loses its A3 proof. Because #30 repeats closed umbrella #20,
    the duplicate hold must be re-applied: held / none / closed-umbrella-duplicate:#20, and no issue_suite_review B.
    """
    suiteRecord(tmp_path, "v8.0.0")
    census = censusOf(
        [umbrellaRow(30, SUITE, "v7.0.0", adds=["alpha"]), umbrellaRow(40, SUITE, "v8.0.0", adds=["alpha"])],
        closed=[closedUmbrella(20, adds=["alpha"])],
    )

    manifest = run(census, tmp_path)

    u40 = item(manifest, 40)
    assert (u40["state"], u40["authority"], u40["ruleId"]) == ("resolved", "A", "A2-umbrella-synced")

    u30 = item(manifest, 30)
    assert (u30["state"], u30["authority"], u30["ruleId"]) == ("held", "none", None)
    assert "closed-umbrella-duplicate:#20" in u30["notProven"]
    assert "superseder-closed-in-pass:#40" in u30["notProven"]
    assert all(u30["key"] not in batch["classB"] for batch in manifest["batches"])

    scan = IssueHygieneSensor()._observations(manifest, policyFor(writesEnabled=False), "2026-10-21T19:30:00Z")
    assert not [o for o in scan.observations if o.kind == "issue_suite_review"]
