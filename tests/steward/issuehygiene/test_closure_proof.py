"""Proof rules for a closed outcome (#2130 exactly-once; ruling on closure proof).

A closed outcome must identify its closing comment by URL, by numeric id, or by a
marker the driver re-read. A forge that reports none of these leaves the issue open.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import (
    closureCommentFor,
    closureProven,
    commentIdFromUrl,
    executeClosure,
)
from tests.steward.issuehygiene.test_b_closure import (
    NOW,
    FakeForge,
    a1Scenario,
    liveOf,
    planFor,
    scenarioRow,
)


class SilentForge(FakeForge):
    """Posts the comment but reports no URL, as a forge may for a repeated or redacted write."""

    def addComment(self, number: int, body: str):
        self.calls.append(("comment", number))
        self.comments.setdefault(number, []).append({"body": body, "url": None})
        return None


class LostForge(FakeForge):
    """Reports no URL and does not store the comment, so no marker can be found afterwards."""

    def addComment(self, number: int, body: str):
        self.calls.append(("comment", number))
        return None


def test_comment_id_is_read_from_a_github_comment_url() -> None:
    assert commentIdFromUrl("https://github.com/o/r/issues/10#issuecomment-4567") == 4567
    assert commentIdFromUrl("https://github.test/10/comment/1") is None
    assert commentIdFromUrl(None) is None


def test_observed_plan_rebuilds_the_planned_comment_byte_for_byte(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    observed = {key: value for key, value in plan.items() if key != "comment"}
    observed["reconciliationSha256"] = manifest["manifestSha256"]
    assert closureCommentFor(observed) == plan["comment"]


def test_forge_url_closure_is_recorded_with_its_proof(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    forge = FakeForge({10: liveOf(scenarioRow(10))})
    receipt = executeClosure(planFor(manifest), forge, tmp_path / "r.jsonl", NOW, "run-1")
    assert receipt["outcome"] == "closed"
    assert receipt["commentUrl"].startswith("https://github.test/10/comment/")
    assert receipt["commentId"] is None and receipt["markerVerified"] is False
    assert closureProven(receipt)


def test_url_less_comment_is_verified_by_rereading_the_marker_before_closing(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    forge = SilentForge({10: liveOf(scenarioRow(10))})
    receipt = executeClosure(planFor(manifest), forge, tmp_path / "r.jsonl", NOW, "run-1")
    assert receipt["outcome"] == "closed"
    assert receipt["commentUrl"] is None and receipt["markerVerified"] is True
    assert closureProven(receipt)
    assert forge.issues[10]["state"] == "closed"


def test_unverifiable_comment_leaves_the_issue_open(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    forge = LostForge({10: liveOf(scenarioRow(10))})
    receipt = executeClosure(planFor(manifest), forge, tmp_path / "r.jsonl", NOW, "run-1")
    assert receipt["outcome"] == "failed"
    assert "not verifiable" in receipt["failure"]
    assert not any(call[0] == "close" for call in forge.calls)
    assert forge.issues[10]["state"] == "open"


def test_resumed_marker_without_url_still_counts_as_proof(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    marker = {"body": plan["comment"], "url": None}
    forge = FakeForge({10: liveOf(scenarioRow(10))}, comments={10: [marker]})
    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "run-1")
    assert receipt["outcome"] == "closed"
    assert receipt["markerVerified"] is True
    assert [call[0] for call in forge.writes()] == ["close"]


@pytest.mark.parametrize("outcome, proven", [
    ({"outcome": "closed"}, False),
    ({"outcome": "closed", "commentUrl": "  "}, False),
    ({"outcome": "closed", "commentUrl": "https://example.invalid/c"}, True),
    ({"outcome": "closed", "commentId": 5}, True),
    ({"outcome": "closed", "commentId": True}, False),
    ({"outcome": "closed", "commentId": 0}, False),
    ({"outcome": "closed", "markerVerified": True}, True),
    ({"outcome": "closed", "markerVerified": "yes"}, False),
])
def test_closed_outcome_proof_accepts_one_of_url_id_or_marker(outcome: dict, proven: bool) -> None:
    assert closureProven(outcome) is proven
