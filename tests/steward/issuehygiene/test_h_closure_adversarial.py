"""Adversarial closure cases for the fail-closed comment and marker rules (B8 follow-through, PR #2133).

Nothing here reaches GitHub. ``Forge`` is the in-memory ``IssueForge`` from the B5 lane. Every case asserts that a
maintainer, a foreign marker or an unreadable comment history stops the closure before any write, and that a
receipt never counts a refused attempt as done.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import (
    _executeProvenClosure as executeClosure,
    _historyBaselinePath,
    planClosures,
    resumeState,
)
from tests.steward.issuehygiene.e_fakes import SimulatedCrash
from tests.steward.issuehygiene.test_b5_closure_guard import (
    CLOSER,
    Forge,
    bigUmbrella,
    liveUmbrella,
    markerFor,
    ownMarkerPlan,
    receiptsOf,
    seedHistoryBaseline,
)
from tests.steward.issuehygiene.test_b_closure import liveOf, scenarioRow
from tests.steward.issuehygiene.test_b_reconcile import NOW, policyFor

MAINTAINER = "maintainer"
DRIFTED = "2026-10-21T19:45:00Z"


class RawForge(Forge):
    """Returns comment rows exactly as stored, so a malformed row reaches the closure unchanged."""

    def listComments(self, number: int) -> list:
        self.calls.append(("list", number))
        return list(self.comments.get(number, []))


def objection(text: str = "please don't close this", author: str = MAINTAINER, n: int = 900) -> dict:
    return {"body": text, "url": f"https://github.com/gaia-research/gaia-skill-tree/issues/10#issuecomment-{n}",
            "author": author}


def drifted(row: dict) -> dict:
    return {**liveOf(row), "updatedAt": DRIFTED}


# --- a maintainer objection after our own marker ----------------------------------------------------------


def test_a_maintainer_objection_after_our_marker_stale_skips_with_no_writes(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    own = markerFor(plan, plan["closureSha8"], author=CLOSER)
    receiptPath = tmp_path / "r.jsonl"
    forge = Forge({10: drifted(scenarioRow(10))}, comments={10: [own, objection()]})
    seedHistoryBaseline(receiptPath, plan)

    receipt = executeClosure(plan, forge, receiptPath, NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert "comment-after-closure-marker" in receipt["failure"]
    assert forge.writes() == [], "no second comment and no close"
    assert forge.issues[10]["state"] == "open"


def test_same_account_objection_after_existing_marker_stale_skips(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    own = markerFor(plan, plan["closureSha8"], author=CLOSER)
    receiptPath = tmp_path / "r.jsonl"
    forge = Forge({10: liveOf(scenarioRow(10))}, comments={10: [own, objection(author=CLOSER)]})
    seedHistoryBaseline(receiptPath, plan)

    receipt = executeClosure(plan, forge, receiptPath, NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert "comment-after-closure-marker" in receipt["failure"]
    assert forge.writes() == []


@pytest.mark.parametrize("author", [MAINTAINER, CLOSER], ids=["maintainer", "same-account"])
def test_comment_arriving_during_initial_history_read_is_not_absorbed_into_baseline(
    tmp_path: Path, author: str,
) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    receipts = tmp_path / "r.jsonl"
    baseline = _historyBaselinePath(receipts, None, plan["key"], plan["issue"], plan["closureSha8"])
    forge = Forge({10: liveOf(scenarioRow(10))})

    def objectionDuringHistoryRead() -> None:
        forge.comments.setdefault(10, []).append(objection(author=author, n=903))
        forge.issues[10]["updatedAt"] = DRIFTED

    originalList = forge.listComments

    def listWithRace(number: int) -> list[dict]:
        if not forge.comments.get(number):
            objectionDuringHistoryRead()
        return originalList(number)

    forge.listComments = listWithRace  # type: ignore[method-assign]

    first = executeClosure(plan, forge, receipts, NOW, "R1")

    assert first["outcome"] == "stale-skip"
    assert "updatedAt-during-initial-history" in first["failure"]
    assert forge.writes() == [], "the race must stop before marker POST and close"
    assert not baseline.exists(), "unbracketed history must never become the immutable baseline"
    assert forge.issues[10]["state"] == "open"

    second = executeClosure(plan, forge, receipts, NOW, "R1")

    assert second["outcome"] == "stale-skip"
    assert forge.writes() == []
    assert not baseline.exists()
    assert forge.issues[10]["state"] == "open"


def test_same_account_comment_added_before_marker_post_is_detected(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)

    class RacingForge(Forge):
        def addComment(self, number: int, body: str):
            self.comments.setdefault(number, []).append(objection(author=CLOSER, n=901))
            return super().addComment(number, body)

    forge = RacingForge({10: liveOf(scenarioRow(10))})
    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert "comment-history-changed" in receipt["failure"]
    assert not any(call[0] == "close" for call in forge.calls)
    assert forge.issues[10]["state"] == "open"


def test_same_account_comment_added_after_marker_before_close_is_detected(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)

    class RacingForge(Forge):
        def addComment(self, number: int, body: str):
            url = super().addComment(number, body)
            self.comments[number].append(objection(author=CLOSER, n=902))
            return url

    forge = RacingForge({10: liveOf(scenarioRow(10))})
    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert "comment-after-closure-marker" in receipt["failure"]
    assert not any(call[0] == "close" for call in forge.calls)
    assert forge.issues[10]["state"] == "open"


def test_a_crash_then_a_maintainer_objection_before_the_resume_never_closes(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, crashAfter={("addComment", 10)})
    receipts = tmp_path / "r.jsonl"
    with pytest.raises(SimulatedCrash):
        executeClosure(plan, forge, receipts, NOW, "R1")
    forge.comments[10].append(objection())

    receipt = executeClosure(plan, forge, receipts, NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert not any(call[0] == "close" for call in forge.calls)
    assert forge.issues[10]["state"] == "open"
    assert len([c for c in forge.comments[10] if "gaia-steward-closure" in c["body"]]) == 1


def test_a_maintainer_objection_between_chunks_of_a_closure_stops_the_resume(tmp_path: Path) -> None:
    manifest, _, row = bigUmbrella(tmp_path)
    plan = planClosures(manifest, policyFor())[0]
    assert len(plan["comments"]) > 1
    forge = Forge({20: liveUmbrella(row)}, crashAfter={("addComment", 20)})
    receipts = tmp_path / "r.jsonl"
    with pytest.raises(SimulatedCrash):
        executeClosure(plan, forge, receipts, NOW, "R1")
    forge.comments[20].append(objection(author=MAINTAINER, n=901))
    writesBefore = len(forge.writes())

    receipt = executeClosure(plan, forge, receipts, NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert len(forge.writes()) == writesBefore, "the missing chunks are not posted past the objection"
    assert not any(call[0] == "close" for call in forge.calls)


# --- unreadable or unknown comment rows: fail closed ----------------------------------------------------


@pytest.mark.parametrize("row", [None, "not-a-comment-object", 42], ids=["null", "string", "number"])
def test_an_unreadable_comment_row_after_our_marker_blocks_and_writes_nothing(tmp_path: Path, row) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    own = markerFor(plan, plan["closureSha8"], author=CLOSER)
    forge = RawForge({10: liveOf(scenarioRow(10))}, comments={10: [own, row]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert "unreadable comment" in receipt["failure"]
    assert forge.writes() == []


@pytest.mark.parametrize("row", [None, "not-a-comment-object"], ids=["null", "string"])
def test_an_unreadable_comment_row_with_no_marker_blocks_rather_than_closing(tmp_path: Path, row) -> None:
    """A row the closer cannot read may be a maintainer's objection, so no comment may be written beside it."""
    _, plan = ownMarkerPlan(tmp_path)
    forge = RawForge({10: liveOf(scenarioRow(10))}, comments={10: [row]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert "unreadable comment" in receipt["failure"]
    assert forge.writes() == []
    assert forge.issues[10]["state"] == "open"


# --- our own marker, drift it explains, and a resume ----------------------------------------------------


def test_our_marker_explains_updatedAt_drift_and_the_resume_posts_nothing_and_closes(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    own = markerFor(plan, plan["closureSha8"], author=CLOSER)
    receiptPath = tmp_path / "r.jsonl"
    forge = Forge({10: drifted(scenarioRow(10))}, comments={10: [own]})
    seedHistoryBaseline(receiptPath, plan)

    receipt = executeClosure(plan, forge, receiptPath, NOW, "R1")

    assert receipt["outcome"] == "closed"
    assert receipt["markerVerified"] is True and receipt["closer"] == CLOSER
    assert [call[0] for call in forge.writes()] == ["close"]


def test_two_own_markers_reuse_the_first_and_post_nothing(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    own = markerFor(plan, plan["closureSha8"], author=CLOSER)
    receiptPath = tmp_path / "r.jsonl"
    forge = Forge({10: liveOf(scenarioRow(10))}, comments={10: [own, dict(own)]})
    seedHistoryBaseline(receiptPath, plan)

    receipt = executeClosure(plan, forge, receiptPath, NOW, "R1")

    assert receipt["outcome"] == "closed"
    assert [call[0] for call in forge.writes()] == ["close"]


def test_our_marker_beside_a_foreign_marker_blocks_and_writes_nothing(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    own = markerFor(plan, plan["closureSha8"], author=CLOSER)
    foreign = markerFor(plan, plan["closureSha8"], author=MAINTAINER)
    forge = Forge({10: liveOf(scenarioRow(10))}, comments={10: [own, foreign]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert forge.writes() == []


# --- identity unknown with nothing to prove ownership ---------------------------------------------------


def test_no_marker_and_an_unknown_closer_writes_no_comment(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, login=None)

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert receipt["closer"] is None and receipt["markerVerified"] is False and receipt["commentUrl"] is None
    assert forge.writes() == []


# --- no false proof from a different digest, and receipts never count a refusal as done -----------------


def test_a_different_digest_marker_with_drift_is_not_proof_and_stale_skips(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    other = markerFor(plan, "deadbeef", author=CLOSER)
    forge = Forge({10: drifted(scenarioRow(10))}, comments={10: [other]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert receipt["markerVerified"] is False
    assert forge.writes() == []


def test_refused_attempts_are_not_done_so_the_pair_is_emitted_again(tmp_path: Path) -> None:
    _, plan = ownMarkerPlan(tmp_path)
    receipts = tmp_path / "r.jsonl"
    own = markerFor(plan, plan["closureSha8"], author=CLOSER)
    forge = Forge({10: drifted(scenarioRow(10))}, comments={10: [own, objection()]})
    seedHistoryBaseline(receipts, plan)

    executeClosure(plan, forge, receipts, NOW, "R1")

    state = resumeState(receipts)
    assert not state.isDone(plan["key"], plan["issue"])
    assert [row["outcome"] for row in receiptsOf(receipts)] == ["stale-skip"]
