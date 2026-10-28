"""Lane B5 closure blockers: B4, D3, D7, D9, M1, M2, M3, M4, M7.

Nothing here reaches GitHub. ``Forge`` is an in-memory ``IssueForge`` with an author per comment,
a closer identity (``whoami``), crash points and a write log. ``GhForge`` is driven through an
injected transport that answers with the statuses and bodies api.github.com would send.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import (
    COMMENT_LIMIT,
    itemDigest,
    ForgeBlockedError,
    ForgeItemError,
    ForgeIdentityError,
    closureCommentsFor,
    closureProven,
    _executeProvenClosure as executeClosure,
    _historyBaselinePath, _historyDigest, _readOrCreateHistoryBaseline,
    planClosures,
    resumeState,
)
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import observedDigest
from scripts.steward_issue_close import EXIT_OK, EXIT_REFUSED, main as closeMain
from scripts.steward_issue_reconcile import GhForge
from tests.steward.issuehygiene.e_fakes import SimulatedCrash
from tests.steward.issuehygiene.e_fakes import censusOf as censusOfDocument
from tests.steward.issuehygiene.test_b_closure import a1Scenario, liveOf, planFor, scenarioRow
from tests.steward.issuehygiene.test_b_reconcile import (
    BLOB,
    BOT,
    NOW,
    childRow,
    censusOf,
    mkRow,
    policyFor,
    skill,
    umbrellaRow,
    writeNamed,
)

REPO = "gaia-research/gaia-skill-tree"
CLOSER = "steward-bot"


class Forge:
    """In-memory ``IssueForge``. Comments carry an author; ``whoami`` names the closer."""

    def __init__(self, issues: dict, comments: dict | None = None, login: str | None = CLOSER,
                 delay: float = 0.0, crashAfter: set | None = None, failures: dict | None = None):
        self.issues = {number: dict(value) for number, value in issues.items()}
        self.comments = {number: list(value) for number, value in (comments or {}).items()}
        self.login = login
        self.delay = delay
        self.crashAfter = set(crashAfter or ())
        self.failures = dict(failures or {})
        self.calls: list[tuple] = []
        self.lock = threading.Lock()

    def _fail(self, method: str, number: int | None) -> None:
        exc = self.failures.pop((method, number), None)
        if exc is not None:
            raise exc

    def getIssue(self, number: int) -> dict:
        self.calls.append(("get", number))
        self._fail("get", number)
        return dict(self.issues[number])

    def listComments(self, number: int) -> list[dict]:
        self.calls.append(("list", number))
        return [dict(comment) for comment in self.comments.get(number, [])]

    def addComment(self, number: int, body: str):
        with self.lock:
            self.calls.append(("comment", number))
            self._fail("comment", number)
            time.sleep(self.delay)
            count = len(self.comments.get(number, [])) + 1
            url = f"https://github.com/{REPO}/issues/{number}#issuecomment-{number * 100 + count}"
            self.comments.setdefault(number, []).append({"body": body, "url": url, "author": self.login})
            self.issues[number]["updatedAt"] = f"2026-10-21T19:2{count}:00Z"
            if ("addComment", number) in self.crashAfter:
                self.crashAfter.discard(("addComment", number))
                raise SimulatedCrash(f"addComment #{number}")
            return url

    def closeIssue(self, number: int, stateReason: str, duplicateOf: int | None = None) -> None:
        with self.lock:
            self.calls.append(("close", number, stateReason, duplicateOf))
            self._fail("close", number)
            time.sleep(self.delay)
            self.issues[number]["state"] = "closed"
            self.issues[number]["stateReason"] = stateReason

    def whoami(self) -> str:
        self.calls.append(("whoami",))
        if self.login is None:
            raise ForgeItemError("whoami: no login")
        return self.login

    def writes(self) -> list[tuple]:
        return [call for call in self.calls if call[0] in ("comment", "close")]


def receiptsOf(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def markerFor(plan: dict, sha8: str, author: str = CLOSER) -> dict:
    body = plan["comment"].replace(plan["closureSha8"], sha8)
    return {"body": body, "url": "https://github.com/x/y/issues/1#issuecomment-900", "author": author}


def seedHistoryBaseline(receiptsPath: Path, plan: dict, history: list[dict] | None = None,
                        repo: str | None = None) -> None:
    baseline = _historyBaselinePath(receiptsPath, repo, plan["key"], plan["issue"], plan["closureSha8"])
    _readOrCreateHistoryBaseline(baseline, _historyDigest(history or [], plan["comments"], CLOSER))


def sha8Of(plan: dict, manifest: dict) -> str:
    return manifest["manifestSha256"][:8]


def a1Forge(manifest: dict, **kwargs) -> tuple[Forge, dict]:
    plan = planFor(manifest)
    return Forge({10: liveOf(scenarioRow(10))}, **kwargs), plan


# ---------------------------------------------------------------- D3: one proof, GitHub-shaped


def test_a_closed_outcome_needs_exactly_one_proof() -> None:
    url = f"https://github.com/{REPO}/issues/10#issuecomment-1001"
    assert closureProven({"outcome": "closed", "commentUrl": url}, 10, REPO)
    assert closureProven({"outcome": "closed", "commentId": 1001}, 10, REPO)
    assert closureProven({"outcome": "closed", "markerVerified": True}, 10, REPO)
    assert not closureProven({"outcome": "closed", "commentUrl": url, "commentId": 1001}, 10, REPO)
    assert not closureProven({"outcome": "closed", "commentUrl": url, "markerVerified": True}, 10, REPO)
    assert not closureProven({"outcome": "closed", "commentId": 1001, "markerVerified": True}, 10, REPO)
    assert not closureProven({"outcome": "closed"}, 10, REPO)


@pytest.mark.parametrize("url", [
    f"https://github.com/{REPO}/issues/11#issuecomment-1001",
    "https://github.com/other/repo/issues/10#issuecomment-1001",
    "https://github.test/10/comment/1",
    f"https://github.com/{REPO}/pull/10#issuecomment-1001",
    f"https://github.com/{REPO}/issues/10#discussion-1001",
    "https://github.com/" + REPO + "/issues/10",
])
def test_a_comment_url_must_name_this_issue_and_repo(url: str) -> None:
    assert not closureProven({"outcome": "closed", "commentUrl": url}, 10, REPO)


# ---------------------------------------------------------------- B4: the executor is gated, not trusted


def checkout(tmp_path: Path, policy: dict | None = None, census: dict | None = None):
    from tests.steward.issuehygiene.e_fakes import makeCheckout

    childNamed = skill("obra/writing-skills", github=BLOB)
    document = census or censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)]).document
    root = makeCheckout(tmp_path, census=document, named={"obra/writing-skills": childNamed}, policy=policy)
    return root, document


def actionFor(root: Path, document: dict, planOverrides: dict | None = None, **changes) -> Path:
    from gaia_cli.steward.issuehygiene.census import validateCensus  # noqa: F401 - the same census the script reads

    manifest = reconcile(censusOfDocument(document), buildRegistryIndex(root), policyFor(), NOW)
    plan = planClosures(manifest, policyFor())[0]
    action = {
        **plan, "receiptPath": ".gaia/steward/issue-hygiene/receipts/R1.jsonl",
        "manifestSha256": observedDigest(manifest), "itemSha256": itemDigest(plan), "repo": REPO,
        **(planOverrides or {}), **changes,
    }
    target = root / "action.json"
    target.write_text(json.dumps(action, sort_keys=True), encoding="utf-8")
    return target


def runClose(root: Path, action: Path, capsys, factory=None) -> tuple[int, list[str]]:
    constructed: list[str] = []

    def spy(repo, token):
        constructed.append(repo)
        return factory() if factory else Forge({10: liveOf(scenarioRow(10))})

    code = closeMain(["--root", str(root), "--action", str(action), "--run-id", "R1", "--now", "2026-10-21T19:30:00Z"],
                     forgeFactory=spy)
    capsys.readouterr()
    return code, constructed


def test_the_executor_closes_a_proven_issue_when_every_gate_holds(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True})
    action = actionFor(root, document)

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_OK
    assert constructed == [REPO]


def test_writes_disabled_refuses_before_any_forge_is_built(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": False})
    action = actionFor(root, document)

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED
    assert constructed == []
    assert not (root / ".gaia" / "steward" / "issue-hygiene" / "receipts" / "R1.jsonl").exists()


def test_a_rule_missing_from_enabled_rules_is_refused(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True, "enabledRules": ["A2-umbrella-synced"]})
    action = actionFor(root, document)

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []


def test_an_action_the_census_does_not_prove_is_refused(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True})
    action = actionFor(root, document)
    # A child whose registry record is missing is not A1-proven. The forged action must still be refused.
    (root / "registry" / "named" / "obra" / "writing-skills.md").unlink()

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []


def test_the_per_run_cap_counts_this_runs_closures(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True, "maxClosuresPerRun": 1})
    receipts = root / ".gaia" / "steward" / "issue-hygiene" / "receipts" / "R1.jsonl"
    receipts.parent.mkdir(parents=True)
    receipts.write_text(json.dumps({"outcome": "closed", "key": "other", "issue": 99, "runId": "R1"}) + "\n", encoding="utf-8")
    action = actionFor(root, document)

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []


def test_a_receipts_directory_symlinked_outside_the_store_is_refused(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True})
    outside = tmp_path / "outside"
    outside.mkdir()
    store = root / ".gaia" / "steward" / "issue-hygiene"
    store.mkdir(parents=True)
    (store / "receipts").symlink_to(outside, target_is_directory=True)
    action = actionFor(root, document)

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []
    assert not list(outside.iterdir())


def test_a_stale_census_refuses_the_action(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True})
    action = actionFor(root, document)
    stale = dict(document, fetchedAt="2026-10-20T00:00:00Z")
    (root / ".gaia" / "steward" / "inputs" / "github-issues.json").write_text(json.dumps(stale), encoding="utf-8")

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []


def test_an_incomplete_census_refuses_the_action(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True})
    action = actionFor(root, document)
    broken = json.loads(json.dumps(document))
    broken["completeness"]["issues"]["complete"] = False
    (root / ".gaia" / "steward" / "inputs" / "github-issues.json").write_text(json.dumps(broken), encoding="utf-8")

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []


def test_a_closures_own_evidence_that_moved_since_emission_refuses_the_action(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True})
    action = actionFor(root, document, itemSha256="0" * 64)

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []


def test_a_comment_that_does_not_match_the_re_derived_comment_is_refused(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path, policy={"writesEnabled": True})
    action = actionFor(root, document, comment="<!-- gaia-steward-closure:forged -->\nplease close")

    code, constructed = runClose(root, action, capsys)

    assert code == EXIT_REFUSED and constructed == []


def test_the_executor_documents_its_exit_codes() -> None:
    import scripts.steward_issue_close as script

    assert (script.EXIT_OK, script.EXIT_FAILED, script.EXIT_REFUSED, script.EXIT_BLOCKED) == (0, 1, 2, 3)
    assert "Exit codes" in script.__doc__ and "2  refused" in script.__doc__


# ---------------------------------------------------------------- M1, M2: GhForge is strict


def transportOf(responses: list[tuple[int, dict, str]]):
    calls: list[tuple] = []

    def transport(method, url, headers, body):
        calls.append((method, url))
        return responses.pop(0)

    transport.calls = calls
    return transport


def issueJson(issueNumber: int, **changes) -> str:
    data = {"number": issueNumber, "title": "t", "state": "open", "state_reason": None, "updated_at": "2026-10-21T10:00:00Z",
            "body": "b", "labels": [], "locked": False, "html_url": f"https://github.com/{REPO}/issues/{issueNumber}"}
    data.update(changes)
    return json.dumps(data)


@pytest.mark.parametrize("status", [301, 304, 307, 404, 422, 500])
def test_non_2xx_or_unfollowed_redirect_is_an_error(status: int) -> None:
    forge = GhForge(REPO, "tok", transportOf([(status, {}, "{}")]))

    with pytest.raises(ForgeItemError):
        forge.getIssue(10)


def test_close_is_confirmed_only_when_the_response_says_closed_with_the_reason() -> None:
    open_ = transportOf([(200, {}, issueJson(10, state="open"))])
    with pytest.raises(ForgeItemError):
        GhForge(REPO, "tok", open_).closeIssue(10, "completed")

    wrongReason = transportOf([(200, {}, issueJson(10, state="closed", state_reason="not_planned"))])
    with pytest.raises(ForgeItemError):
        GhForge(REPO, "tok", wrongReason).closeIssue(10, "completed")

    good = transportOf([(200, {}, issueJson(10, state="closed", state_reason="completed"))])
    GhForge(REPO, "tok", good).closeIssue(10, "completed")


@pytest.mark.parametrize(("changes", "reason"), [
    ({"locked": True}, "locked"),
    ({"number": 11}, "number"),
    ({"html_url": "https://github.com/other/transferred/issues/10"}, "transferred"),
    ({"pull_request": {"url": "x"}}, "pull request"),
])
def test_getissue_refuses_locked_pulls_renumbered_and_transferred_issues(changes: dict, reason: str) -> None:
    forge = GhForge(REPO, "tok", transportOf([(200, {}, issueJson(10, **changes))]))

    with pytest.raises(ForgeIdentityError):
        forge.getIssue(10)


def test_getissue_returns_the_identity_fields_it_checks() -> None:
    forge = GhForge(REPO, "tok", transportOf([(200, {}, issueJson(10))]))

    live = forge.getIssue(10)

    assert live["locked"] is False and live["number"] == 10
    assert live["htmlUrl"] == f"https://github.com/{REPO}/issues/10"


def test_an_identity_refusal_is_blocked_identity_with_no_write(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)

    class Renamed(Forge):
        def getIssue(self, number):
            raise ForgeIdentityError("transferred")

    forge = Renamed({10: liveOf(scenarioRow(10))})
    receipts = tmp_path / "r.jsonl"
    receipt = executeClosure(plan, forge, receipts, NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert forge.writes() == []
    assert receiptsOf(receipts)[0]["outcome"] == "blocked-identity"


def test_a_live_locked_issue_is_blocked_identity(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    live = {**liveOf(scenarioRow(10)), "locked": True}
    forge = Forge({10: live})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert forge.writes() == []


# ---------------------------------------------------------------- M3: only our own marker is proof


def ownMarkerPlan(tmp_path: Path):
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)
    return manifest, plan


def test_a_foreign_marker_blocks_the_closure_and_no_second_marker_is_posted(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, comments={10: [markerFor(plan, plan["closureSha8"], author="someone")]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert forge.writes() == [], "a marker by another author is neither proof nor a reason to post a second one"
    assert forge.issues[10]["state"] == "open"


def test_a_marker_for_another_manifest_is_not_proof(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, comments={10: [markerFor(plan, "deadbeef", author=CLOSER)]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "closed"
    assert any(call[0] == "comment" for call in forge.writes())


def test_existing_own_marker_without_trusted_baseline_fails_closed(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, comments={10: [markerFor(plan, plan["closureSha8"], author=CLOSER)]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert "no trusted history baseline" in receipt["failure"]
    assert forge.writes() == []


def test_when_the_closer_identity_is_unknown_an_existing_marker_blocks_and_nothing_is_written(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, login=None,
                  comments={10: [markerFor(plan, plan["closureSha8"], author=CLOSER)]})

    receipt = executeClosure(plan, forge, tmp_path / "r.jsonl", NOW, "R1")

    assert receipt["outcome"] == "blocked-identity"
    assert forge.writes() == []
    assert forge.issues[10]["state"] == "open"


def plan_sha8(manifest: dict) -> str:
    return manifest["manifestSha256"][:8]


# ---------------------------------------------------------------- D7: crash between comment and close


def test_a_crash_between_comment_and_close_resumes_on_the_same_action(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, crashAfter={("addComment", 10)})
    receipts = tmp_path / "r.jsonl"

    with pytest.raises(SimulatedCrash):
        executeClosure(plan, forge, receipts, NOW, "R1")
    assert forge.issues[10]["state"] == "open"
    assert forge.issues[10]["updatedAt"] != liveOf(scenarioRow(10))["updatedAt"]

    receipt = executeClosure(plan, forge, receipts, NOW, "R1")

    assert receipt["outcome"] == "closed"
    assert forge.issues[10]["state"] == "closed"
    assert len([c for c in forge.comments[10] if "gaia-steward-closure" in c["body"]]) == 1
    assert receiptsOf(receipts)[-1]["outcome"] == "closed"


def test_a_real_title_change_still_stale_skips_even_with_our_own_comment(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    live = {**liveOf(scenarioRow(10)), "title": "edited by a human"}
    receipts = tmp_path / "r.jsonl"
    forge = Forge({10: live}, comments={10: [markerFor(plan, plan["closureSha8"], author=CLOSER)]})
    baseline = _historyBaselinePath(receipts, None, plan["key"], plan["issue"], plan["closureSha8"])
    _readOrCreateHistoryBaseline(baseline, _historyDigest([], plan["comments"], CLOSER))

    receipt = executeClosure(plan, forge, receipts, NOW, "R1")

    assert receipt["outcome"] == "stale-skip"
    assert forge.writes() == []


# ---------------------------------------------------------------- M4: two closers, one comment, one close


def test_two_concurrent_closers_post_one_comment_and_one_close(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))}, delay=0.05)
    receipts = tmp_path / "r.jsonl"
    barrier = threading.Barrier(2)
    results: list[dict] = []

    def closer() -> None:
        barrier.wait()
        results.append(executeClosure(plan, forge, receipts, NOW, "R1"))

    threads = [threading.Thread(target=closer) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert len([call for call in forge.writes() if call[0] == "comment"]) == 1
    assert len([call for call in forge.writes() if call[0] == "close"]) == 1
    outcomes = [result["outcome"] for result in results]
    assert "closed" in outcomes
    assert set(outcomes) <= {"closed", "already-closed", "resumed-done"}
    assert sum(1 for receipt in receiptsOf(receipts) if receipt["outcome"] == "closed") == 1


def test_a_resumed_pair_writes_no_second_receipt(tmp_path: Path) -> None:
    manifest, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))})
    receipts = tmp_path / "r.jsonl"
    executeClosure(plan, forge, receipts, NOW, "R1")
    assert resumeState(receipts).isDone(plan["key"], plan["issue"])
    before = len(receiptsOf(receipts))
    writesBefore = len(forge.writes())

    receipt = executeClosure(plan, forge, receipts, NOW, "R1")

    assert receipt["outcome"] == "resumed-done"
    assert len(receiptsOf(receipts)) == before
    assert len(forge.writes()) == writesBefore


# ---------------------------------------------------------------- D9: scrubbed and capped


def test_a_token_shaped_title_is_scrubbed_and_capped_in_the_comment_and_the_plan(tmp_path: Path) -> None:
    token = "ghp_" + "A" * 36
    row = mkRow(10, "[intake] obra/writing-skills " + "x" * 400 + " " + token, childRow(10, "obra/writing-skills", BLOB)["body"],
                labels=("upstream:child",))
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB))
    census = censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), row])
    manifest = reconcile(census, buildRegistryIndex(tmp_path), policyFor(), NOW)
    plan = planClosures(manifest, policyFor())[0]

    assert token not in json.dumps(plan)
    assert len(plan["original"]["title"]) <= 200
    assert all(token not in comment for comment in plan["comments"])


# ---------------------------------------------------------------- M7: full candidate preservation


def preservedTextOf(plan: dict) -> str:
    """The exact text the closing comments carry: the plan's original payload, pretty-printed."""
    return json.dumps(plan["original"], indent=2, sort_keys=True, ensure_ascii=False)


def bigUmbrella(tmp_path: Path, count: int = 600):
    writeNamed(tmp_path, "obra/superpowers", skill("obra/superpowers", extra="upstream:\n  repo: obra/superpowers\n  version: v1.2\n"))
    candidates = [
        {"id": f"obra/cand-{index:04d}", "slug": f"cand-{index:04d}",
         "evidenceUrl": BLOB.replace("writing-skills", f"cand-{index:04d}"),
         "firstSeenVersion": "v1", "lastSeenVersion": "v1",
         "precheck": {"registry": "absent", "tracked": "none", "priorDisposition": "none"},
         "status": "present", "child": None, "note": "a description line of about one hundred characters " * 2}
        for index in range(count)
    ]
    payload = {"payloadVersion": 2, "skillId": "obra/superpowers", "newVersion": "v1.2", "componentAdds": [],
               "componentRemoves": [], "candidates": candidates}
    body = "## Upstream release detected\n\n<!-- gaia-upstream-payload\n" + json.dumps(payload, indent=2) + "\n-->\n"
    row = mkRow(20, "[upstream] obra/superpowers → v1.2", body, labels=("upstream:release",))
    manifest = reconcile(censusOf([row]), buildRegistryIndex(tmp_path), policyFor(), NOW)
    return manifest, candidates, row


def liveUmbrella(row: dict) -> dict:
    return {"number": row["number"], "title": row["title"], "state": "open", "updatedAt": row["updatedAt"],
            "body": row["body"], "labels": sorted(row["labels"])}


def test_a_large_umbrella_closure_preserves_every_candidate_across_chunked_comments(tmp_path: Path) -> None:
    manifest, candidates, _ = bigUmbrella(tmp_path)
    plan = planClosures(manifest, policyFor())[0]
    comments = plan["comments"]

    assert len(comments) > 1
    assert all(len(comment) <= COMMENT_LIMIT for comment in comments)
    joined = "".join(comments)
    for candidateRow in candidates:
        assert candidateRow["id"] in joined
    assert "a description line of about one hundred characters" in joined


def test_the_receipt_records_the_sha256_of_the_preserved_candidate_information(tmp_path: Path) -> None:
    manifest, _, row = bigUmbrella(tmp_path, count=5)
    plan = planClosures(manifest, policyFor())[0]
    forge = Forge({20: liveUmbrella(row)})
    receipts = tmp_path / "r.jsonl"

    receipt = executeClosure(plan, forge, receipts, NOW, "R1")

    assert receipt["outcome"] == "closed"
    assert receipt["preservedSha256"] == hashlib.sha256(preservedTextOf(plan).encode("utf-8")).hexdigest()
    assert plan["preservedSha256"] == receipt["preservedSha256"]
    assert receipt["preservedParts"] == len(plan["comments"])


def test_closure_comments_rebuild_identically_from_the_observed_plan(tmp_path: Path) -> None:
    manifest, _, _ = bigUmbrella(tmp_path, count=600)
    plan = planClosures(manifest, policyFor())[0]
    observed = {key: value for key, value in plan.items() if key not in ("comment", "comments")}
    observed["reconciliationSha256"] = manifest["manifestSha256"]

    assert closureCommentsFor(observed) == plan["comments"]


def test_a_small_closure_carries_the_preserved_information_inline(tmp_path: Path) -> None:
    manifest, _ = a1Scenario(tmp_path)
    plan = planFor(manifest)

    assert plan["comments"][0].startswith(f"<!-- gaia-steward-closure:{plan['key']}:")
    assert "Preserved candidate information" in plan["comments"][0]
    assert plan["preservedSha256"] == hashlib.sha256(preservedTextOf(plan).encode("utf-8")).hexdigest()
