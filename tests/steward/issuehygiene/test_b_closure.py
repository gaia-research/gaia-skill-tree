from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import (
    ForgeBlockedError,
    ForgeItemError,
    RECEIPT_SCHEMA,
    appendReceipt,
    buildClosureComment,
    executeClosure,
    executeClosures,
    planClosures,
    resumeState,
)
from gaia_cli.steward.issuehygiene.census import bodySha256
from gaia_cli.steward.issuehygiene.hygienepolicy import KNOWN_RULE_IDS
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from tests.steward.issuehygiene.test_b_reconcile import (
    BLOB,
    NOW,
    childRow,
    censusOf,
    dupRows,
    item,
    policyFor,
    skill,
    supersedeRows,
    umbrellaRow,
    writeNamed,
)


class FakeForge:
    """Records every call. ``failures`` maps (method, issue) to an exception to raise once."""

    def __init__(self, issues: dict, comments: dict | None = None, failures: dict | None = None):
        self.issues = {number: dict(value) for number, value in issues.items()}
        self.comments = {number: list(value) for number, value in (comments or {}).items()}
        self.failures = dict(failures or {})
        self.calls: list[tuple] = []

    def _maybeFail(self, method: str, number: int) -> None:
        exc = self.failures.pop((method, number), None)
        if exc is not None:
            raise exc

    def getIssue(self, number: int) -> dict:
        self.calls.append(("get", number))
        self._maybeFail("get", number)
        return dict(self.issues[number])

    def listComments(self, number: int) -> list[dict]:
        self.calls.append(("list", number))
        return list(self.comments.get(number, []))

    def addComment(self, number: int, body: str):
        self.calls.append(("comment", number))
        self._maybeFail("comment", number)
        url = f"https://github.test/{number}/comment/{len(self.comments.get(number, [])) + 1}"
        self.comments.setdefault(number, []).append({"body": body, "url": url})
        return url

    def closeIssue(self, number: int, stateReason: str, duplicateOf: int | None = None) -> None:
        self.calls.append(("close", number, stateReason, duplicateOf))
        self._maybeFail("close", number)
        self.issues[number]["state"] = "closed"

    def writes(self) -> list[tuple]:
        return [call for call in self.calls if call[0] in ("comment", "close")]


def liveOf(row: dict) -> dict:
    return {
        "number": row["number"], "title": row["title"], "state": row["state"], "updatedAt": row["updatedAt"],
        "body": row["body"], "labels": [label if isinstance(label, str) else label["name"] for label in row["labels"]],
    }


def a1Scenario(tmp_path: Path, policy=None):
    """Child 10 is A1-closable. Umbrella 20 stays open with that child, so it is not closable."""
    umbrella = umbrellaRow(20, "obra/superpowers", "v7.0.0")
    child = childRow(10, "obra/writing-skills", BLOB)
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB))
    census = censusOf([umbrella, child])
    manifest = reconcile(census, buildRegistryIndex(tmp_path), policy or policyFor(), NOW)
    return manifest, census


def twoPlanScenario(tmp_path: Path):
    """Two A1-closable children under two different registry records."""
    second = "https://github.com/obra/superpowers/blob/main/skills/other-skill/SKILL.md"
    rows = [
        umbrellaRow(20, "obra/superpowers", "v7.0.0"),
        childRow(10, "obra/writing-skills", BLOB),
        childRow(11, "obra/other-skill", second),
    ]
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB))
    writeNamed(tmp_path, "obra/other-skill", skill("obra/other-skill", github=second))
    census = censusOf(rows)
    return reconcile(census, buildRegistryIndex(tmp_path), policyFor(), NOW)


def planFor(manifest: dict, policy=None) -> dict:
    plans = planClosures(manifest, policy or policyFor())
    assert len(plans) == 1
    return plans[0]


def test_plans_only_for_authority_a_under_enabled_rule_with_writes_and_complete_census(tmp_path: Path):
    manifest, _census = a1Scenario(tmp_path)
    plans = planClosures(manifest, policyFor())
    assert [plan["issue"] for plan in plans] == [10]
    assert plans[0]["authority"] == "A"
    assert "Nothing was deleted" in plans[0]["comment"]


def test_no_plans_when_writes_disabled(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path, policyFor(writesEnabled=False))
    assert planClosures(manifest, policyFor(writesEnabled=False)) == []


def test_no_plans_when_census_incomplete_or_stale(tmp_path: Path):
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB))
    census = censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)], complete=False)
    manifest = reconcile(census, buildRegistryIndex(tmp_path), policyFor(), NOW)
    assert planClosures(manifest, policyFor()) == []
    stale = censusOf([childRow(10, "obra/writing-skills", BLOB)], fetchedAt="2026-09-01T00:00:00Z")
    stale_manifest = reconcile(stale, buildRegistryIndex(tmp_path), policyFor(), NOW)
    assert planClosures(stale_manifest, policyFor()) == []


def test_disabled_rule_produces_no_plan(tmp_path: Path):
    policy = policyFor(enabledRules=[rule for rule in KNOWN_RULE_IDS if rule != "A1-child-curated"])
    manifest, _ = a1Scenario(tmp_path, policy)
    assert planClosures(manifest, policy) == []


def test_cap_is_respected(tmp_path: Path):
    manifest = twoPlanScenario(tmp_path)
    assert len(planClosures(manifest, policyFor())) == 2
    assert len(planClosures(manifest, policyFor(maxClosuresPerRun=1))) == 1
    assert planClosures(manifest, policyFor(maxClosuresPerRun=0)) == []


def test_a4_plan_names_its_canonical_as_duplicate_of(tmp_path: Path):
    manifest = reconcile(censusOf(dupRows()), buildRegistryIndex(tmp_path), policyFor(), NOW)
    plans = planClosures(manifest, policyFor())
    assert [(plan["issue"], plan["duplicateOf"]) for plan in plans] == [(51, 50)]


def test_comment_carries_marker_rule_proof_and_original_payload(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    child = item(manifest, 10)
    body = buildClosureComment(child, manifest)
    sha8 = manifest["manifestSha256"][:8]
    assert body.startswith(f"<!-- gaia-steward-closure:{child['key']}:{sha8} -->")
    assert "A1-child-curated" in body
    assert "links to the same repo and file as the evidence URL (git ref may differ)" in body
    assert "links to the same evidence URL" not in body
    assert "registry/named/obra/writing-skills.md" in body
    assert "[intake] obra/writing-skills" in body
    assert "Nothing was deleted" in body


def test_success_writes_comment_then_closes_and_records_receipt(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    forge = FakeForge({10: liveOf(scenarioRow(10))})
    receipts = tmp_path / "receipts" / "run-1.jsonl"
    receipt = executeClosure(plan, forge, receipts, NOW, "run-1")
    assert receipt["outcome"] == "closed"
    assert receipt["schemaVersion"] == RECEIPT_SCHEMA
    assert receipt["closedAt"] == "2026-10-21T19:30:00Z"
    assert [call[0] for call in forge.writes()] == ["comment", "close"]
    assert forge.calls.index(("comment", 10)) < forge.calls.index(("close", 10, "completed", None))
    assert forge.issues[10]["state"] == "closed"
    lines = receipts.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["outcome"] == "closed"


def scenarioRow(number: int) -> dict:
    """The live copy of an a1Scenario row, as the forge would return it."""
    rows = {row["number"]: row for row in [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)]}
    return rows[number]


def test_already_closed_issue_is_not_written_again(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    live = liveOf(scenarioRow(10))
    live["state"] = "closed"
    forge = FakeForge({10: live})
    receipt = executeClosure(planFor(manifest), forge, tmp_path / "r.jsonl", NOW)
    assert receipt["outcome"] == "already-closed"
    assert forge.writes() == []


@pytest.mark.parametrize("field", ["updatedAt", "body", "labels", "title"])
def test_stale_snapshot_skips_with_no_writes(tmp_path: Path, field: str):
    manifest, _ = a1Scenario(tmp_path)
    live = liveOf(scenarioRow(10))
    if field == "updatedAt":
        live["updatedAt"] = "2026-10-21T18:00:00Z"
    elif field == "body":
        live["body"] = live["body"] + "\nedited\n"
    elif field == "labels":
        live["labels"] = live["labels"] + ["P2"]
    else:
        live["title"] = "[intake] renamed"
    forge = FakeForge({10: live})
    receipt = executeClosure(planFor(manifest), forge, tmp_path / "r.jsonl", NOW)
    assert receipt["outcome"] == "stale-skip"
    assert field in receipt["failure"]
    assert forge.writes() == []
    assert forge.issues[10]["state"] == "open"


def test_crash_resume_skips_comment_when_marker_exists_and_only_closes(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    live = liveOf(scenarioRow(10))
    marker = {"body": plan["comment"], "url": "https://github.test/10/comment/prior"}
    forge = FakeForge({10: live}, comments={10: [marker]})
    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW)
    assert receipt["outcome"] == "closed"
    assert receipt["commentUrl"] == "https://github.test/10/comment/prior"
    assert [call[0] for call in forge.writes()] == ["close"]


def test_marker_from_an_earlier_manifest_still_counts_as_our_comment(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    earlier = {"body": f"<!-- gaia-steward-closure:{plan['key']}:00000000 -->\nold", "url": "https://github.test/10/old"}
    forge = FakeForge({10: liveOf(scenarioRow(10))}, comments={10: [earlier]})
    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW)
    assert receipt["outcome"] == "closed"
    assert [call[0] for call in forge.writes()] == ["close"]


def test_item_local_failure_is_recorded_and_batch_continues(tmp_path: Path):
    manifest = twoPlanScenario(tmp_path)
    plans = planClosures(manifest, policyFor())
    rows = {row["number"]: row for row in [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB), childRow(11, "obra/other-skill", "https://github.com/obra/superpowers/blob/main/skills/other-skill/SKILL.md")]}
    forge = FakeForge({number: liveOf(rows[number]) for number in (10, 11)}, failures={("close", 10): ForgeItemError("422 validation")})
    results = executeClosures(plans, forge, tmp_path / "r.jsonl", NOW, "run")
    assert [result["outcome"] for result in results] == ["failed", "closed"]
    assert "422 validation" in results[0]["failure"]
    assert results[0]["commentUrl"] is not None
    assert forge.issues[11]["state"] == "closed"


def test_auth_or_rate_failure_blocks_and_stops_the_batch(tmp_path: Path):
    manifest = twoPlanScenario(tmp_path)
    plans = planClosures(manifest, policyFor())
    rows = {row["number"]: row for row in [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB), childRow(11, "obra/other-skill", "https://github.com/obra/superpowers/blob/main/skills/other-skill/SKILL.md")]}
    forge = FakeForge({number: liveOf(rows[number]) for number in (10, 11)}, failures={("comment", 10): ForgeBlockedError("http-403")})
    results = executeClosures(plans, forge, tmp_path / "r.jsonl", NOW, "run")
    assert [result["outcome"] for result in results] == ["blocked"]
    assert all(call[1] != 11 for call in forge.calls)


def test_receipts_are_append_only_and_replay_is_idempotent(tmp_path: Path):
    manifest = twoPlanScenario(tmp_path)
    plans = planClosures(manifest, policyFor())
    rows = {row["number"]: row for row in [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB), childRow(11, "obra/other-skill", "https://github.com/obra/superpowers/blob/main/skills/other-skill/SKILL.md")]}
    receipts = tmp_path / "r.jsonl"
    forge = FakeForge({number: liveOf(rows[number]) for number in (10, 11)})
    executeClosures(plans, forge, receipts, NOW, "run")
    first = receipts.read_bytes()
    assert first.count(b"\n") == 2

    replay = FakeForge({number: liveOf(rows[number]) for number in (10, 11)})
    results = executeClosures(plans, replay, receipts, NOW, "run")
    assert [result["outcome"] for result in results] == ["resumed-done", "resumed-done"]
    assert replay.calls == []
    assert receipts.read_bytes() == first


def test_already_closed_issue_recorded_in_receipts_counts_as_done_for_resume(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    receipts = tmp_path / "r.jsonl"
    live = liveOf(scenarioRow(10))
    live["state"] = "closed"
    executeClosure(plan, FakeForge({10: live}), receipts, NOW)
    state = resumeState(receipts)
    assert state.isDone(plan["key"], 10)
    assert state.keys() == frozenset({plan["key"]})


def test_resume_state_ignores_torn_last_line_and_counts_corruption(tmp_path: Path):
    receipts = tmp_path / "r.jsonl"
    receipts.write_text(
        json.dumps({"key": "k1", "issue": 1, "outcome": "closed"}) + "\nnot json\n" + '{"key": "k2", "issue": 2, "outcome": "clo',
        encoding="utf-8",
    )
    state = resumeState(receipts)
    assert state.isDone("k1", 1)
    assert not state.isDone("k2", 2)
    assert state.corrupt == 2
    assert resumeState(tmp_path / "missing.jsonl").done == frozenset()


def test_append_terminates_a_torn_line_before_writing(tmp_path: Path):
    receipts = tmp_path / "r.jsonl"
    receipts.write_text('{"torn": ', encoding="utf-8")
    appendReceipt(receipts, {"key": "k", "issue": 3, "outcome": "closed"})
    lines = receipts.read_text(encoding="utf-8").splitlines()
    assert lines[0] == '{"torn": '
    assert json.loads(lines[1])["issue"] == 3


def test_refuses_plans_that_are_not_authority_a(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    plan = dict(planFor(manifest), authority="B")
    with pytest.raises(ValueError):
        executeClosure(plan, FakeForge({}), tmp_path / "r.jsonl", NOW)


def test_duplicate_closure_passes_duplicate_of_to_forge(tmp_path: Path):
    manifest = reconcile(censusOf(dupRows()), buildRegistryIndex(tmp_path), policyFor(), NOW)
    plan = planClosures(manifest, policyFor())[0]
    rows = {row["number"]: row for row in dupRows()}
    forge = FakeForge({51: liveOf(rows[51])})
    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW)
    assert receipt["outcome"] == "closed"
    assert ("close", 51, "duplicate", 50) in forge.calls


def test_superseded_umbrella_plan_closes_not_planned(tmp_path: Path):
    manifest = reconcile(censusOf(supersedeRows()), buildRegistryIndex(tmp_path), policyFor(), NOW)
    plans = planClosures(manifest, policyFor())
    assert [plan["issue"] for plan in plans] == [30]
    rows = {row["number"]: row for row in supersedeRows()}
    forge = FakeForge({30: liveOf(rows[30])})
    receipt = executeClosure(plans[0], forge, tmp_path / "r.jsonl", NOW)
    assert receipt["outcome"] == "closed"
    assert ("close", 30, "not_planned", None) in forge.calls
