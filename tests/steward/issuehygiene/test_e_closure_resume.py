"""Adversarial lane E, scenarios 7, 8, 12 and 13: partial failure, races, exactly-once resume.

The closure executor runs against ``FakeForge`` over ``FakeGitHub``. Failures are raised before a
call takes effect; ``SimulatedCrash`` is raised after it, so the process is gone with the write
done. Every test here checks the forge's own write log, not the receipts alone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.census import Census, bodySha256, validateCensus
from gaia_cli.steward.issuehygiene.closure import (
    ForgeBlockedError,
    executeClosures,
    planClosures,
    resumeState,
)
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from tests.steward.issuehygiene.e_fakes import (
    NOW,
    FakeForge,
    FakeGitHub,
    ForgeFailure,
    SimulatedCrash,
    closeRound,
    defaultPolicy,
    makeCheckout,
)

REPO_SUITE = "obra/superpowers"
SLUGS = {30: "writing-skills", 31: "other-skill", 32: "third"}


def childUrl(slug: str) -> str:
    return f"https://github.com/obra/superpowers/blob/main/skills/{slug}/SKILL.md"


def record(identifier: str, url: str) -> str:
    contributor = identifier.split("/")[0]
    return f"---\nid: {identifier}\ncontributor: {contributor}\nstatus: named\nlinks:\n  github: {url}\n---\n\n## Body\n"


def childBody(suggested: str, url: str, parent: int) -> str:
    return (
        f"> Auto-populated by upstream watcher. Umbrella: #{parent}.\n\n---\n\n## New skill intake proposal\n\n"
        f"**Suggested ID:** `{suggested}`\n### Evidence\n\n- **type:** `repo`\n- **url:** {url}\n"
    )


def seedFamily(gh: FakeGitHub) -> None:
    """Umbrella #20 (v7, never synced: stays open) and three A1-curated child intakes."""

    payload = {"skillId": REPO_SUITE, "newVersion": "v7.0.0", "componentAdds": list(SLUGS.values()), "componentRemoves": []}
    umbrella = "## Upstream release detected\n\n<!-- gaia-upstream-payload\n" + json.dumps(payload, indent=2) + "\n-->\n"
    gh.add("[upstream] obra/superpowers → v7.0.0", body=umbrella, labels=("upstream:release",), number=20)
    for number, slug in SLUGS.items():
        gh.add(f"[intake] obra/{slug}", body=childBody(f"obra/{slug}", childUrl(slug), 20),
               labels=("upstream:child",), number=number)


def familyCheckout(tmp_path: Path, gh: FakeGitHub) -> Path:
    seedFamily(gh)
    named = {f"obra/{slug}": record(f"obra/{slug}", childUrl(slug)) for slug in SLUGS.values()}
    return makeCheckout(tmp_path, named=named)


def planRound(gh: FakeGitHub, root: Path):
    policy = defaultPolicy()
    document = gh.census(NOW)
    manifest = reconcile(Census(document, validateCensus(document, NOW, policy.maxCensusAgeSeconds), "fake"),
                         buildRegistryIndex(root), policy, NOW)
    return manifest, planClosures(manifest, policy)


def commentsOn(gh: FakeGitHub, number: int) -> int:
    return len(gh.comments.get(number, []))


def closesOf(forge: FakeForge, number: int) -> list[tuple]:
    return [write for write in forge.writes if write[0] == "close" and write[1] == number]


class CountingForge(FakeForge):
    """A FakeForge that also counts every forge call, so 'no forge call' is measured, not inferred."""

    def __init__(self, gh: FakeGitHub, **kwargs):
        super().__init__(gh, **kwargs)
        self.calls: list[tuple] = []

    def getIssue(self, number):
        self.calls.append(("getIssue", number))
        return super().getIssue(number)

    def listComments(self, number):
        self.calls.append(("listComments", number))
        return super().listComments(number)

    def addComment(self, number, body):
        self.calls.append(("addComment", number))
        return super().addComment(number, body)

    def closeIssue(self, number, stateReason, duplicateOf=None):
        self.calls.append(("closeIssue", number))
        return super().closeIssue(number, stateReason, duplicateOf)


# ------------------------------------------------------------------ scenario 7: partial API failure


def test_item_failure_on_one_closure_leaves_the_others_closed_and_a_retry_closes_it_exactly_once(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    first = CountingForge(gh, failures={("addComment", 31): ForgeFailure.item("http-502")})
    _, _, results = closeRound(gh, root, receipts, "run-1", first)
    outcomes = {row["issue"]: row["outcome"] for row in results}
    assert outcomes == {30: "closed", 31: "failed", 32: "closed"}
    assert commentsOn(gh, 31) == 0 and gh.issues[31]["state"] == "open"

    second = CountingForge(gh)
    _, _, retried = closeRound(gh, root, receipts, "run-2", second)
    assert [row["issue"] for row in retried] == [31]
    assert retried[0]["outcome"] == "closed"
    assert [commentsOn(gh, number) for number in (30, 31, 32)] == [1, 1, 1]
    assert [len(closesOf(second, number)) for number in (30, 31, 32)] == [0, 1, 0]


def test_a_blocked_auth_on_the_proof_read_stops_the_batch_with_no_write(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    blocked = CountingForge(gh, failures={("getIssue", 30): ForgeFailure.blocked("http-401")})
    _, _, results = closeRound(gh, root, receipts, "run-1", blocked)
    assert [row["outcome"] for row in results] == ["blocked"]
    assert [row["issue"] for row in results] == [30]  # 31 and 32 are never attempted
    assert all(commentsOn(gh, number) == 0 for number in (30, 31, 32))
    assert blocked.writes == []


def test_a_blocked_comment_listing_during_the_proof_writes_no_comment_and_no_close(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    forge = CountingForge(gh, failures={("listComments", 30): ForgeBlockedError("http-403")})
    _, _, results = closeRound(gh, root, tmp_path / "r.jsonl", "run-1", forge)
    assert results[0]["outcome"] == "blocked"
    assert commentsOn(gh, 30) == 0 and gh.issues[30]["state"] == "open"
    assert closesOf(forge, 30) == []


def test_a_failure_while_reading_one_live_issue_is_item_local_not_a_batch_stop(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    forge = CountingForge(gh, failures={("getIssue", 31): ForgeFailure.item("http-500")})
    _, _, results = closeRound(gh, root, tmp_path / "r.jsonl", "run-1", forge)
    assert {row["issue"]: row["outcome"] for row in results} == {30: "closed", 31: "failed", 32: "closed"}


# ------------------------------------------------------------------ scenario 12: crash and exactly-once resume


def test_crash_between_the_closing_comment_and_the_close_resumes_with_one_comment_and_one_close(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    crashing = CountingForge(gh, crashAfter={("addComment", 30)})
    with pytest.raises(SimulatedCrash):
        closeRound(gh, root, receipts, "run-1", crashing)
    assert commentsOn(gh, 30) == 1 and gh.issues[30]["state"] == "open"
    assert 30 not in {issue for _key, issue in resumeState(receipts).done}

    resumed = CountingForge(gh)
    closeRound(gh, root, receipts, "run-2", resumed)
    assert commentsOn(gh, 30) == 1  # the marker was found, so no second comment was written
    assert len(closesOf(resumed, 30)) == 1
    assert gh.issues[30]["state"] == "closed"
    assert {issue for _key, issue in resumeState(receipts).done} >= {30, 31, 32}


def test_crash_after_the_close_is_never_closed_again_when_the_old_plan_is_replayed(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    manifest, plans = planRound(gh, root)
    crashing = CountingForge(gh, crashAfter={("closeIssue", 30)})
    with pytest.raises(SimulatedCrash):
        executeClosures(plans, crashing, receipts, NOW, "run-1")
    assert gh.issues[30]["state"] == "closed"

    replay = CountingForge(gh)
    results = executeClosures(plans, replay, receipts, NOW, "run-2")
    by = {row["issue"]: row["outcome"] for row in results if "issue" in row}
    assert by.get(30) in ("already-closed", "resumed-done")
    assert ("addComment", 30) not in replay.calls and ("closeIssue", 30) not in replay.calls
    assert commentsOn(gh, 30) == 1


def test_an_old_plan_replayed_after_our_own_comment_is_a_stale_skip_and_never_a_second_comment(tmp_path: Path) -> None:
    """Our comment bumps updated_at, so the pre-crash snapshot no longer matches. A fresh census is needed to
    finish; until then the old plan must stop, not post a second marker."""

    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    _, plans = planRound(gh, root)
    crashing = CountingForge(gh, crashAfter={("addComment", 30)})
    with pytest.raises(SimulatedCrash):
        executeClosures(plans, crashing, receipts, NOW, "run-1")

    replay = CountingForge(gh)
    results = executeClosures(plans, replay, receipts, NOW, "run-2")
    (row30,) = [row for row in results if row["issue"] == 30]
    assert row30["outcome"] == "stale-skip"
    assert "updatedAt" in row30["failure"]
    assert ("addComment", 30) not in replay.calls
    assert commentsOn(gh, 30) == 1 and gh.issues[30]["state"] == "open"


def test_a_repeated_round_after_full_success_performs_no_forge_write_and_leaves_receipts_byte_identical(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    closeRound(gh, root, receipts, "run-1", CountingForge(gh))
    before = receipts.read_bytes()
    comments = {number: commentsOn(gh, number) for number in SLUGS}

    fresh = CountingForge(gh)
    _, plans, results = closeRound(gh, root, receipts, "run-2", fresh)
    assert plans == [] and results == []
    assert fresh.calls == []
    assert receipts.read_bytes() == before
    assert {number: commentsOn(gh, number) for number in SLUGS} == comments


def test_a_stale_plan_after_full_success_resumes_from_receipts_with_zero_forge_calls(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    _, plans = planRound(gh, root)
    executeClosures(plans, CountingForge(gh), receipts, NOW, "run-1")
    replay = CountingForge(gh)
    results = executeClosures(plans, replay, receipts, NOW, "run-2")
    assert {row["outcome"] for row in results} == {"resumed-done"}
    assert replay.calls == []


def test_receipts_keep_every_attempt_and_only_the_closed_pair_counts_as_done(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    receipts = tmp_path / "receipts" / "run.jsonl"
    closeRound(gh, root, receipts, "run-1", CountingForge(gh, failures={("addComment", 31): ForgeFailure.item()}))
    closeRound(gh, root, receipts, "run-2", CountingForge(gh))
    lines = [json.loads(line) for line in receipts.read_text(encoding="utf-8").splitlines() if line.strip()]
    outcomesFor31 = [line["outcome"] for line in lines if line["issue"] == 31]
    assert outcomesFor31 == ["failed", "closed"]
    assert sum(1 for line in lines if line["issue"] == 31 and line["outcome"] == "closed") == 1


# ------------------------------------------------------------------ scenario 8: watcher or human races the closure


@pytest.mark.parametrize(("mutation", "field"), [
    ("body", "bodySha256"),
    ("labels", "labels"),
    ("title", "title"),
])
def test_an_edit_between_census_and_close_is_a_stale_skip_with_zero_writes(tmp_path: Path, mutation: str, field: str) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    _, plans = planRound(gh, root)
    if mutation == "body":
        gh.edit(30, body=gh.issues[30]["body"] + "\nedited by the watcher\n")
    elif mutation == "labels":
        gh.relabel(30, add=("upstream:needs-info",))
    else:
        gh.edit(30, title="[intake] renamed by a human")
    forge = CountingForge(gh)
    results = executeClosures(plans, forge, tmp_path / "r.jsonl", NOW, "run-1")
    (row30,) = [row for row in results if row["issue"] == 30]
    assert row30["outcome"] == "stale-skip"
    assert field in row30["failure"]
    assert not [write for write in forge.writes if write[1] == 30]  # the mutated issue: no comment, no close
    assert commentsOn(gh, 30) == 0 and gh.issues[30]["state"] == "open"
    assert {row["issue"]: row["outcome"] for row in results}[31] == "closed"  # the others are unaffected


def test_an_issue_closed_by_someone_else_before_execution_is_already_closed_without_a_comment(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    _, plans = planRound(gh, root)
    gh.close(30, "completed")
    forge = CountingForge(gh)
    results = executeClosures(plans, forge, tmp_path / "r.jsonl", NOW, "run-1")
    assert {row["issue"]: row["outcome"] for row in results}[30] == "already-closed"
    assert commentsOn(gh, 30) == 0 and closesOf(forge, 30) == []


def test_a_race_that_lands_during_the_read_is_detected_by_the_snapshot_compare(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    _, plans = planRound(gh, root)
    gh.callHooks[("getIssue", 31)] = lambda g: g.edit(31, body=g.issues[31]["body"] + "\nrace\n")
    forge = CountingForge(gh)
    results = executeClosures(plans, forge, tmp_path / "r.jsonl", NOW, "run-1")
    assert {row["issue"]: row["outcome"] for row in results} == {30: "closed", 31: "stale-skip", 32: "closed"}
    assert commentsOn(gh, 31) == 0 and gh.issues[31]["state"] == "open"


def test_every_planned_closure_carries_the_snapshot_it_will_be_compared_against(tmp_path: Path) -> None:
    gh = FakeGitHub()
    root = familyCheckout(tmp_path, gh)
    _, plans = planRound(gh, root)
    assert {plan["issue"] for plan in plans} == {30, 31, 32}
    for plan in plans:
        snapshot = plan["expectedSnapshot"]
        assert set(snapshot) == {"state", "title", "updatedAt", "bodySha256", "labels"}
        assert snapshot["bodySha256"] == bodySha256(gh.issues[plan["issue"]]["body"])
        assert snapshot["updatedAt"] == gh.issues[plan["issue"]]["updated_at"]
