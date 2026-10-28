"""Lane B8 H-1: a closure the steward performed is never repeated, even when a person reopens the issue.

A pair the receipts store records as done (in ANY receipts file of the checkout) is refused before the cap and
before any close. The own-marker ``updatedAt`` tolerance never applies to a done pair. A reopened issue surfaces
as one founder-visible Class C note, never as a new closure.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from gaia_cli.steward.issuehygiene.closure import _executeProvenClosure as executeClosure, _executeProvenClosures as executeClosures, planClosures, storeDonePairs
from gaia_cli.steward.issuehygiene.executor import RECEIPTDIR, ActionRefused, gateClosure
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, IssueHygieneSensor
from tests.steward.issuehygiene.e_fakes import censusOf as censusOfDocument, makeCheckout
from tests.steward.issuehygiene.test_b5_closure_guard import Forge, REPO
from tests.steward.issuehygiene.test_b_closure import liveOf
from tests.steward.issuehygiene.test_b_reconcile import BLOB, NOW, censusOf, childRow, policyFor, skill, umbrellaRow

BLOB2 = "https://github.com/obra/superpowers/blob/main/skills/testing-skills/SKILL.md"
REOPENED = "2026-10-21T19:45:00Z"
LATER = datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc)
LATER_FETCH = "2026-10-21T19:59:00Z"


def twoChildren(tmp_path: Path):
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"),
            childRow(10, "obra/writing-skills", BLOB),
            childRow(11, "obra/testing-skills", BLOB2)]
    document = censusOf(rows).document
    named = {"obra/writing-skills": skill("obra/writing-skills", github=BLOB),
             "obra/testing-skills": skill("obra/testing-skills", github=BLOB2)}
    root = makeCheckout(tmp_path, census=document, named=named)
    return root, document


def liveMap(document: dict) -> dict:
    return {row["number"]: liveOf(row) for row in document["issues"]}


def reopenedCopy(document: dict) -> dict:
    """What the next census shows after a person reopened issue 10: open again, updatedAt after our closure."""
    later = copy.deepcopy(document)
    later["fetchedAt"] = LATER_FETCH
    for row in later["issues"]:
        if row["number"] == 10:
            row.update({"state": "open", "stateReason": None, "closedAt": None, "updatedAt": REOPENED})
    return later


def firstRun(root: Path, document: dict, forge: Forge, store: Path):
    policy = policyFor()
    manifest = reconcile(censusOfDocument(document, NOW), buildRegistryIndex(root), policy, NOW)
    plans = planClosures(manifest, policy)
    results = executeClosures(plans, forge, store / "R1.jsonl", NOW, "R1", REPO)
    return plans, results


def test_run_one_closes_both_and_run_two_in_a_new_file_closes_nothing_for_the_reopened_issue(tmp_path: Path) -> None:
    root, document = twoChildren(tmp_path)
    store = root / RECEIPTDIR
    forge = Forge(liveMap(document))
    plans, results = firstRun(root, document, forge, store)
    assert [result["outcome"] for result in results] == ["closed", "closed"]

    forge.issues[10].update({"state": "open", "updatedAt": REOPENED})
    later = reopenedCopy(document)
    policy = policyFor()
    manifest = reconcile(censusOfDocument(later, LATER), buildRegistryIndex(root), policy, LATER)
    done = storeDonePairs(store)
    plan10 = next(plan for plan in plans if plan["issue"] == 10)
    assert (plan10["key"], 10) in done
    planned = planClosures(manifest, policy, done=done)
    assert 10 not in [plan["issue"] for plan in planned], "a reopened, previously closed issue is never planned again"

    writesBefore = list(forge.writes())
    run2 = store / "R2.jsonl"
    receipt = executeClosure(plan10, forge, run2, LATER, "R2", REPO)
    assert receipt["outcome"] == "resumed-done"
    assert forge.writes() == writesBefore, "no comment and no close for a pair already recorded as done"
    assert not run2.exists(), "a done pair writes no receipt in a new file either"


def test_the_gate_refuses_a_reopened_pair_recorded_done_in_another_receipts_file(tmp_path: Path) -> None:
    root, document = twoChildren(tmp_path)
    store = root / RECEIPTDIR
    forge = Forge(liveMap(document))
    plans, _ = firstRun(root, document, forge, store)
    later = reopenedCopy(document)
    (root / CENSUS_INPUT).write_text(json.dumps(later), encoding="utf-8")
    plan10 = next(plan for plan in plans if plan["issue"] == 10)
    action = {**{k: v for k, v in plan10.items() if k not in ("reconciliationSha256",)},
              "receiptPath": (RECEIPTDIR / "R2.jsonl").as_posix(), "manifestSha256": "0" * 64, "repo": REPO,
              "itemSha256": "0" * 64}
    try:
        gateClosure(root, action, root / RECEIPTDIR / "R2.jsonl", "R2", LATER, REPO)
    except ActionRefused as exc:
        assert exc.code == "already-recorded", exc.code
    else:
        raise AssertionError("the gate must refuse a pair recorded as done")


def test_the_sensor_reports_a_reopened_issue_as_a_founder_note_and_never_as_a_closure(tmp_path: Path) -> None:
    root, document = twoChildren(tmp_path)
    store = root / RECEIPTDIR
    forge = Forge(liveMap(document))
    firstRun(root, document, forge, store)
    (root / CENSUS_INPUT).write_text(json.dumps(reopenedCopy(document)), encoding="utf-8")

    scan = IssueHygieneSensor().scan_detailed(root, LATER.strftime("%Y-%m-%dT%H:%M:%SZ"))
    closures = [obs for obs in scan.observations if obs.kind == "issue_closure_ready"]
    planned = [plan["issue"] for obs in closures for plan in obs.observed_state.get("plans", [])]
    assert 10 not in planned

    notes = [obs for obs in scan.observations
             if obs.kind == "issue_founder_decision" and obs.subject.id == "reopened-after-closure"]
    assert len(notes) == 1, "one Class C note for the reopened issues"
    assert notes[0].observed_state["affected"] == [10]
    assert "closed" in notes[0].observed_state["question"].lower()
    assert notes[0].observed_state["decisionTarget"] == "issue-question/reopened-after-closure"
