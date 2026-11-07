"""Closed-issue census completeness (founder ruling steward-census-empty-page-crosschecks).

A durable last-known verified closed-issue count is a diagnostic baseline, never proof. These tests pin: empty-200
pages, a count drop explained by a reopen, an auth failure, baseline preservation across a failed scan, bounded
retries with telemetry, and that only closure operations (not the rest of Steward) fail closed on missing closed history.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from gaia_cli.steward.issuehygiene import closedbaseline as rules
from gaia_cli.steward.issuehygiene.census import closedOnlyIncomplete, loadCensus
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, IssueHygieneSensor
from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable
from scripts.steward_issue_census import CLOSED_ATTEMPTS, FetchError, Response, collectCensus, main
from tests.steward.issuehygiene.e_fakes import NOW, NOW_TEXT, REPO, makeCheckout

BASE_TIME = "2026-10-20T00:00:00Z"
BASELINE = rules.Baseline(10, BASE_TIME, "gh-api", rules.SCOPE)


def noSleep(_seconds: float) -> None:
    return None


class Repo:
    """A repository whose open listing is empty and whose closed-history surfaces are scripted per test."""

    def __init__(self, *, total=10, closedPage=None, searchStatus=200, events=(), searchBody=None) -> None:
        self.total = total
        self.closedPage = closedPage
        self.searchStatus = searchStatus
        self.searchBody = searchBody
        self.events = list(events)
        self.requests: list[str] = []

    def fetch(self, url: str) -> Response:
        self.requests.append(url)
        parts = urlparse(url)
        if parts.path == f"/repos/{REPO}":
            return Response(200, {}, json.dumps({"open_issues_count": 0}))
        if "/actions/workflows" in url:
            return Response(200, {}, json.dumps({"total_count": 0, "workflows": []}))
        if parts.path == "/search/issues":
            if self.searchStatus != 200:
                return Response(self.searchStatus, {}, "{}")
            body = self.searchBody if self.searchBody is not None else {"total_count": self.total, "incomplete_results": False, "items": []}
            return Response(200, {}, json.dumps(body))
        if parts.path.endswith("/issues/events"):
            return Response(200, {}, json.dumps(self.events))
        if "state=closed" in url:
            if self.closedPage is not None:
                return self.closedPage(url)
            return Response(200, {}, "[]")
        return Response(200, {}, "[]")  # the open listing: empty and complete

    def searches(self) -> int:
        return sum(1 for url in self.requests if urlparse(url).path == "/search/issues")


def census(repo: Repo, baseline=BASELINE, **kwargs) -> dict:
    kwargs.setdefault("authenticated", True)
    kwargs.setdefault("verifyClosedCount", True)
    return collectCensus(REPO, NOW, repo.fetch, 30, baseline=baseline, sleep=noSleep, **kwargs)


def history(document: dict) -> dict:
    return document["closedHistory"]


def reopenedEvent(number: int, when: str = "2026-10-21T00:00:00Z", pull: bool = False) -> dict:
    issue = {"number": number, **({"pull_request": {}} if pull else {})}
    return {"event": "reopened", "created_at": when, "issue": issue}


# --- the rules -------------------------------------------------------------------------------


def test_the_first_verified_count_creates_the_baseline_with_count_time_source_and_scope() -> None:
    judgement = rules.judge(None, 7, NOW_TEXT, "gh-api", None)

    assert judgement.update == "created"
    assert judgement.next is not None and judgement.next.summary() == {
        "count": 7, "observedAt": NOW_TEXT, "source": "gh-api", "scope": rules.SCOPE,
    }


@pytest.mark.parametrize(("count", "direction", "update"), [(10, "same", "unchanged"), (14, "up", "updated")])
def test_a_level_or_rising_count_replaces_the_baseline(count: int, direction: str, update: str) -> None:
    judgement = rules.judge(BASELINE, count, NOW_TEXT, "gh-api", None)

    assert (judgement.direction, judgement.update) == (direction, update)
    assert judgement.next is not None and judgement.next.count == count


def test_a_drop_no_larger_than_the_reopened_issues_is_explained_and_adopted() -> None:
    judgement = rules.judge(BASELINE, 8, NOW_TEXT, "gh-api", 2)

    assert (judgement.direction, judgement.explained, judgement.update) == ("down", True, "updated")
    assert judgement.delta == -2
    assert "2 issue(s) reopened" in judgement.explanation
    assert judgement.next is not None and judgement.next.count == 8


def test_an_unexplained_drop_is_kept_as_a_diagnostic_and_the_baseline_is_not_lowered() -> None:
    judgement = rules.judge(BASELINE, 4, NOW_TEXT, "gh-api", 1)

    assert (judgement.explained, judgement.update) == (False, "kept-unexplained-lower")
    assert judgement.next is not None and judgement.next.count == 10 and judgement.next.observedAt == BASE_TIME
    assert judgement.next.unexplainedLower["count"] == 4 and judgement.next.unexplainedLower["consecutive"] == 1


def test_an_unexplained_lower_count_is_never_adopted_however_often_it_is_seen() -> None:
    held = BASELINE
    for run in range(1, 8):
        judgement = rules.judge(held, 4, f"2026-10-{20 + run:02d}T00:00:00Z", "gh-api", 0)
        held = judgement.next
        assert judgement.update == "kept-unexplained-lower"
        assert held.count == 10
        assert held.unexplainedLower["consecutive"] == run


def test_a_different_lower_count_restarts_the_diagnostic_and_a_recovery_clears_it() -> None:
    held = rules.judge(BASELINE, 4, NOW_TEXT, "gh-api", 0).next
    assert rules.judge(held, 5, NOW_TEXT, "gh-api", 0).next.unexplainedLower["consecutive"] == 1
    recovered = rules.judge(held, 11, NOW_TEXT, "gh-api", 0)
    assert recovered.update == "updated" and recovered.next.unexplainedLower is None


def test_reopening_evidence_that_arrives_later_explains_and_adopts_the_lower_count() -> None:
    held = rules.judge(BASELINE, 4, NOW_TEXT, "gh-api", 0).next
    explained = rules.judge(held, 4, "2026-10-22T00:00:00Z", "gh-api", 6)
    assert explained.explained is True and explained.next.count == 4 and explained.next.unexplainedLower is None


def test_unavailable_reopen_events_leave_a_drop_unexplained() -> None:
    judgement = rules.judge(BASELINE, 8, NOW_TEXT, "gh-api", None, "http-500")

    assert judgement.explained is False and "reopen events unavailable (http-500)" in judgement.explanation


def test_the_baseline_file_round_trips_and_untrustworthy_files_are_reported_not_trusted(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    assert rules.loadBaseline(path, REPO) == (None, None)
    rules.saveBaseline(path, REPO, BASELINE)
    assert rules.loadBaseline(path, REPO) == (BASELINE, None)
    assert rules.loadBaseline(path, "other/repo") == (None, "baseline-other-repository")
    path.write_text("{broken", encoding="utf-8")
    assert rules.loadBaseline(path, REPO) == (None, "baseline-unreadable")
    path.write_text(json.dumps({"schemaVersion": rules.SCHEMA, "repo": REPO, "count": -1}), encoding="utf-8")
    assert rules.loadBaseline(path, REPO)[1] == "baseline-malformed"


# --- the census: a verified count, and what it says ------------------------------------------


def test_a_verified_count_is_recorded_with_provider_scope_and_a_baseline_to_write() -> None:
    document = census(Repo(total=12), baseline=None)

    section = history(document)
    assert section["provider"] == "gh-api" and section["scope"] == rules.SCOPE
    assert section["count"] == {"value": 12, "verified": True, "checked": True}
    assert section["refusal"] is None and section["auth"] == "token"
    assert section["baseline"]["update"] == "created"
    assert section["baseline"]["after"]["count"] == 12
    assert document["completeness"]["open"]["complete"] is True
    assert document["completeness"]["closed"]["complete"] is True


def test_a_count_drop_explained_by_a_reopen_updates_the_baseline_and_says_why() -> None:
    repo = Repo(total=8, events=[reopenedEvent(31), reopenedEvent(32), reopenedEvent(33, pull=True),
                                 {"event": "closed", "created_at": "2026-10-21T00:00:00Z", "issue": {"number": 5}},
                                 reopenedEvent(34, when="2026-10-01T00:00:00Z")])

    section = history(census(repo))

    # two issues reopened after the baseline; the pull request and the pre-baseline reopen do not count
    assert section["change"]["reopenedSince"] == 2
    assert section["change"] == {
        "direction": "down", "delta": -2, "reopenedSince": 2, "explained": True,
        "explanation": section["change"]["explanation"],
    }
    assert section["baseline"]["update"] == "updated" and section["baseline"]["after"]["count"] == 8


def test_a_count_drop_nothing_explains_is_reported_and_does_not_lower_the_baseline() -> None:
    document = census(Repo(total=4, events=[reopenedEvent(31)]))

    section = history(document)
    assert section["change"]["explained"] is False
    assert section["baseline"]["update"] == "kept-unexplained-lower"
    assert section["baseline"]["after"]["count"] == 10  # still the verified baseline
    assert section["baseline"]["after"]["unexplainedLower"]["count"] == 4
    # a diagnostic, not a refusal: the inventory itself is complete
    assert document["completeness"]["closed"]["complete"] is True and document["completeness"]["issues"]["complete"] is True


def test_a_complete_reopening_to_zero_is_explained_by_the_reopen_events() -> None:
    baseline = rules.Baseline(3, BASE_TIME, "gh-api", rules.SCOPE)
    events = [reopenedEvent(31), reopenedEvent(32), reopenedEvent(33)]

    document = census(Repo(total=0, events=events), baseline=baseline)

    section = history(document)
    assert section["count"] == {"value": 0, "verified": True, "checked": True} and section["refusal"] is None
    assert section["change"]["explained"] is True and section["baseline"]["after"]["count"] == 0
    assert document["completeness"]["closed"]["complete"] is True


def test_a_partial_reopening_does_not_explain_a_zero() -> None:
    baseline = rules.Baseline(3, BASE_TIME, "gh-api", rules.SCOPE)

    document = census(Repo(total=0, events=[reopenedEvent(31)]), baseline=baseline)

    assert history(document)["refusal"] == "false-empty-suspect"
    assert document["completeness"]["closed"]["complete"] is False


# --- empty 200 pages and bounded retries ------------------------------------------------------


def emptyLinkedClosed(url: str) -> Response:
    """A closed window that names a next page and then serves it empty: a false empty."""

    if "page=2" in url:
        return Response(200, {}, "[]")
    row = {"number": 7, "state": "closed", "title": "t", "body": "", "labels": [], "user": {"login": "u"},
           "created_at": "2026-10-10T00:00:00Z", "updated_at": "2026-10-10T00:00:00Z", "closed_at": "2026-10-11T00:00:00Z", "comments": 0}
    link = f'<https://api.github.com/repos/{REPO}/issues?state=closed&per_page=100&page=2>; rel="next"'
    return Response(200, {"link": link}, json.dumps([row] * 100))


def test_persistently_empty_closed_pages_are_retried_within_the_bound_then_reported_incomplete() -> None:
    repo = Repo(closedPage=emptyLinkedClosed)

    document = census(repo)

    section = history(document)
    reads = [item for item in section["attempts"] if item["read"] == "closed-window"]
    assert len(reads) == CLOSED_ATTEMPTS and all(item["reason"] == "empty-linked-page" for item in reads)
    assert section["refusal"] == "empty-linked-page"
    assert section["pagination"]["reason"] == "empty-linked-page"
    # closed history is incomplete; the open inventory is not
    assert document["completeness"]["closed"]["complete"] is False
    assert document["completeness"]["closed"]["reason"] == "empty-linked-page"
    assert document["completeness"]["open"]["complete"] is True
    # and a failed scan never offers a baseline to store
    assert section["baseline"]["after"] is None and section["baseline"]["update"] == "preserved"
    assert repo.searches() == 0  # no count is read, so nothing could be verified from an incomplete window


def test_an_empty_count_against_a_non_empty_baseline_is_a_suspected_false_empty_and_closed_is_incomplete() -> None:
    document = census(Repo(total=0))

    section = history(document)
    counts = [item for item in section["attempts"] if item["read"] == "closed-count"]
    assert len(counts) == CLOSED_ATTEMPTS and all(item["reason"] == "false-empty-suspect" for item in counts)
    assert section["refusal"] == "false-empty-suspect" and section["count"]["verified"] is False
    assert section["baseline"]["after"] is None
    closed = document["completeness"]["closed"]
    assert closed == {"complete": False, "reason": "false-empty-suspect"}
    assert document["completeness"]["open"]["complete"] is True
    assert document["completeness"]["issues"]["complete"] is False and "closed-inventory-unverified:false-empty-suspect" in document["completeness"]["issues"]["reason"]


def test_an_empty_count_on_a_first_run_is_a_genuine_empty_history() -> None:
    section = history(census(Repo(total=0), baseline=None))

    assert section["count"] == {"value": 0, "verified": True, "checked": True}
    assert section["baseline"]["after"]["count"] == 0


def test_a_window_holding_more_issues_than_the_total_makes_closed_incomplete() -> None:
    def crowded(url: str) -> Response:
        rows = [{"number": n, "state": "closed", "title": "t", "body": "", "labels": [], "user": {"login": "u"},
                 "created_at": "2026-10-10T00:00:00Z", "updated_at": "2026-10-10T00:00:00Z",
                 "closed_at": "2026-10-11T00:00:00Z", "comments": 0} for n in range(1, 6)]
        return Response(200, {}, json.dumps([] if "page=2" in url else rows))

    document = census(Repo(total=3, closedPage=crowded))

    section = history(document)
    assert section["refusal"] == "window-exceeds-count" and section["count"]["verified"] is False
    assert section["baseline"]["after"] is None
    assert document["completeness"]["closed"] == {"complete": False, "reason": "window-exceeds-count"}
    assert document["completeness"]["open"]["complete"] is True


def test_an_unreadable_count_makes_closed_incomplete_not_merely_noted() -> None:
    document = census(Repo(searchBody={"total_count": "many"}))

    assert history(document)["refusal"] == "count-unreadable"
    assert document["completeness"]["closed"] == {"complete": False, "reason": "count-unreadable"}


def test_without_the_cross_check_the_closed_inventory_is_not_judged_by_a_count() -> None:
    repo = Repo(total=0)
    document = census(repo, verifyClosedCount=False)

    assert repo.searches() == 0
    assert history(document)["count"] == {"value": None, "verified": False, "checked": False}
    assert document["completeness"]["closed"]["complete"] is True


def test_a_transient_server_error_is_retried_and_a_later_good_read_verifies() -> None:
    answers = [Response(502, {}, "{}"), Response(200, {}, json.dumps({"total_count": 11, "incomplete_results": False}))]
    repo = Repo()
    original = repo.fetch
    slept: list[float] = []

    def flaky(url: str) -> Response:
        if urlparse(url).path == "/search/issues":
            repo.requests.append(url)
            return answers.pop(0)
        return original(url)

    document = collectCensus(REPO, NOW, flaky, 30, baseline=BASELINE, sleep=slept.append, authenticated=True, verifyClosedCount=True)

    section = history(document)
    counts = [item["reason"] for item in section["attempts"] if item["read"] == "closed-count"]
    assert counts == ["http-502", None]
    assert section["count"] == {"value": 11, "verified": True, "checked": True}
    assert len(slept) == 1  # one backoff, between the two attempts


# --- auth failure -------------------------------------------------------------------------------


def test_an_auth_failure_is_not_retried_is_reported_as_auth_and_leaves_the_baseline_alone() -> None:
    repo = Repo(searchStatus=401)

    section = history(census(repo))

    counts = [item for item in section["attempts"] if item["read"] == "closed-count"]
    assert len(counts) == 1  # a rejected credential will not improve on a second try
    assert section["auth"] == "rejected" and section["refusal"] == "http-401"
    assert section["count"]["verified"] is False and section["baseline"]["after"] is None


def test_a_rate_limited_read_is_not_retried_either() -> None:
    repo = Repo()
    original = repo.fetch

    def limited(url: str) -> Response:
        if urlparse(url).path == "/search/issues":
            raise FetchError("rate-limited")
        return original(url)

    section = history(collectCensus(REPO, NOW, limited, 30, baseline=BASELINE, sleep=noSleep, authenticated=False, verifyClosedCount=True))

    assert section["auth"] == "anonymous" and section["refusal"] == "rate-limited"
    assert len([item for item in section["attempts"] if item["read"] == "closed-count"]) == 1


def test_telemetry_never_carries_a_token_or_a_host() -> None:
    text = json.dumps(history(census(Repo(searchStatus=401))))

    assert "Bearer" not in text and "api.github.com" not in text


# --- baseline preservation, end to end through the script ---------------------------------------


def run(tmp_path: Path, repo: Repo, monkeypatch: pytest.MonkeyPatch) -> tuple[int, Path, Path]:
    out = tmp_path / "inputs" / "github-issues.json"
    monkeypatch.setenv("GH_TOKEN", "test-token-not-real")
    monkeypatch.setattr("scripts.steward_issue_census.time.sleep", noSleep)
    code = main(["--repo", REPO, "--out", str(out), "--closed-window-days", "30", "--now", NOW_TEXT], fetch=repo.fetch)
    return code, out, out.parent / "closed-issue-baseline.json"


def test_a_failed_scan_never_overwrites_a_verified_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    baselinePath = tmp_path / "inputs" / "closed-issue-baseline.json"
    rules.saveBaseline(baselinePath, REPO, BASELINE)
    before = baselinePath.read_bytes()

    code, _out, path = run(tmp_path, Repo(closedPage=emptyLinkedClosed, total=999), monkeypatch)

    assert code == 3  # the census is incomplete, as it always was
    assert path.read_bytes() == before


def test_a_refused_cross_check_fails_the_census_and_never_overwrites_the_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    baselinePath = tmp_path / "inputs" / "closed-issue-baseline.json"
    rules.saveBaseline(baselinePath, REPO, BASELINE)
    before = baselinePath.read_bytes()

    code, out, path = run(tmp_path, Repo(searchStatus=401), monkeypatch)

    assert code == 3
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["completeness"]["closed"]["complete"] is False
    assert path.read_bytes() == before


def test_a_malformed_closed_row_after_a_verified_count_does_not_write_the_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def malformed(url: str) -> Response:
        return Response(200, {}, json.dumps([] if "page=2" in url else [{"title": "no number"}]))

    baselinePath = tmp_path / "inputs" / "closed-issue-baseline.json"
    rules.saveBaseline(baselinePath, REPO, BASELINE)
    before = baselinePath.read_bytes()

    code, out, path = run(tmp_path, Repo(total=25, closedPage=malformed), monkeypatch)

    document = json.loads(out.read_text(encoding="utf-8"))
    assert code == 3
    assert document["closedHistory"]["count"]["verified"] is True  # the count was fine; the inventory around it was not
    assert document["closedHistory"]["baseline"]["after"] is None
    assert document["completeness"]["closed"] == {"complete": False, "reason": "malformed-rows:1"}
    assert path.read_bytes() == before


def test_a_restore_failure_never_writes_a_new_baseline_and_reports_it_not_evaluated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "inputs" / "github-issues.json"
    monkeypatch.setenv("GH_TOKEN", "test-token-not-real")
    repo = Repo(total=12)

    code = main(["--repo", REPO, "--out", str(out), "--closed-window-days", "30", "--now", NOW_TEXT,
                 "--baseline-state", "restore-failed"], fetch=repo.fetch)

    document = json.loads(out.read_text(encoding="utf-8"))
    baseline = document["closedHistory"]["baseline"]
    assert code == 0
    assert baseline["update"] == "not-evaluated" and baseline["problem"] == "baseline-restore-failed" and baseline["after"] is None
    assert not (out.parent / "closed-issue-baseline.json").exists()


def test_a_restore_failure_leaves_a_stray_local_file_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stray = tmp_path / "inputs" / "closed-issue-baseline.json"
    rules.saveBaseline(stray, REPO, BASELINE)
    before = stray.read_bytes()
    monkeypatch.setenv("GH_TOKEN", "test-token-not-real")

    main(["--repo", REPO, "--out", str(tmp_path / "inputs" / "github-issues.json"), "--closed-window-days", "30",
          "--now", NOW_TEXT, "--baseline-state", "restore-failed"], fetch=Repo(total=99).fetch)

    assert stray.read_bytes() == before


def test_a_first_run_creates_the_baseline_only_from_a_verified_complete_census(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "inputs" / "github-issues.json"
    monkeypatch.setenv("GH_TOKEN", "test-token-not-real")

    code = main(["--repo", REPO, "--out", str(out), "--closed-window-days", "30", "--now", NOW_TEXT,
                 "--baseline-state", "first-run"], fetch=Repo(total=12).fetch)

    assert code == 0 and rules.loadBaseline(out.parent / "closed-issue-baseline.json", REPO)[0].count == 12


def test_an_unexplained_lower_count_leaves_the_stored_baseline_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    baselinePath = tmp_path / "inputs" / "closed-issue-baseline.json"
    rules.saveBaseline(baselinePath, REPO, BASELINE)

    for _ in range(3):  # three consecutive runs see the same lower count
        code, out, path = run(tmp_path, Repo(total=4), monkeypatch)
        assert code == 0

    stored = rules.loadBaseline(path, REPO)[0]
    assert stored.count == 10 and stored.unexplainedLower["count"] == 4 and stored.unexplainedLower["consecutive"] == 3


def test_a_verified_scan_writes_and_the_next_run_reads_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out, path = run(tmp_path, Repo(total=12), monkeypatch)
    assert code == 0
    saved, problem = rules.loadBaseline(path, REPO)
    assert problem is None and saved is not None and saved.count == 12 and saved.source == "gh-api"

    code, out, path = run(tmp_path, Repo(total=15), monkeypatch)
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["closedHistory"]["baseline"]["before"]["count"] == 12
    assert document["closedHistory"]["change"]["direction"] == "up"
    assert rules.loadBaseline(path, REPO)[0].count == 15


def test_a_corrupt_baseline_is_reported_and_replaced_only_by_a_verified_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "inputs" / "closed-issue-baseline.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")

    code, out, _ = run(tmp_path, Repo(total=5), monkeypatch)

    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["closedHistory"]["baseline"]["problem"] == "baseline-unreadable"
    assert rules.loadBaseline(path, REPO)[0].count == 5


# --- only operations that depend on closed history fail closed ------------------------------------


def failingClosedDocument() -> dict:
    return census(Repo(closedPage=emptyLinkedClosed))


def test_a_closed_only_failure_is_identified_as_closed_only() -> None:
    document = failingClosedDocument()
    # The legacy sections stay conservative, so the census is still incomplete for any consumer that does not know better.
    assert document["completeness"]["issues"]["complete"] is False

    loaded = loadCensusFrom(document)
    assert closedOnlyIncomplete(loaded) is True


def loadCensusFrom(document: dict):
    from gaia_cli.steward.issuehygiene.census import Census, validateCensus

    return Census(document, validateCensus(document, NOW, 21600), "test")


def test_an_open_inventory_failure_is_not_closed_only() -> None:
    def brokenOpen(url: str) -> Response:
        return Response(500, {}, "{}")

    repo = Repo()
    original = repo.fetch

    def fetch(url: str) -> Response:
        if "state=open" in url:
            return brokenOpen(url)
        return original(url)

    document = collectCensus(REPO, NOW, fetch, 30, sleep=noSleep)

    assert document["completeness"]["open"]["complete"] is False
    assert closedOnlyIncomplete(loadCensusFrom(document)) is False


def test_a_stale_census_is_never_closed_only() -> None:
    document = failingClosedDocument()
    stale = loadCensusFrom(document)
    from gaia_cli.steward.issuehygiene.census import Census, validateCensus

    old = datetime(2026, 10, 22, 19, 30, tzinfo=timezone.utc)
    assert closedOnlyIncomplete(Census(document, validateCensus(document, old, 21600), "test")) is False
    assert stale.status.status == "incomplete"


def degrade(document: dict, reason: str = "count-unreadable") -> dict:
    """The census shape a closed-only failure leaves: open complete, closed not, legacy sections conservative."""

    degraded = json.loads(json.dumps(document))
    for section in ("issues", "pulls"):
        degraded["completeness"][section]["complete"] = False
        degraded["completeness"][section]["reason"] = f"closed-inventory-unverified:{reason}"
    degraded["completeness"]["open"] = {"complete": True}
    degraded["completeness"]["closed"] = {"complete": False, "reason": reason}
    return degraded


def closableSetup(tmp_path: Path):
    from scripts.steward_issue_census import writeAtomic
    from tests.steward.issuehygiene.e_fakes import FakeGitHub, loadFixture, seedFromDocument
    from tests.steward.issuehygiene.test_e_steward_full_e2e import curatedRegistry, eligibleFromFixture

    gh = FakeGitHub()
    seedFromDocument(gh, loadFixture())
    picks = eligibleFromFixture(3)
    root = makeCheckout(tmp_path, named=curatedRegistry(picks))
    return gh, root, writeAtomic


def test_a_closed_only_failure_keeps_open_observations_and_fails_only_closure_operations_closed(tmp_path: Path) -> None:
    gh, root, writeAtomic = closableSetup(tmp_path)
    whole = gh.census(NOW)
    writeAtomic(root / CENSUS_INPUT, whole)

    healthy = IssueHygieneSensor().scan_detailed(root, NOW_TEXT)
    healthyKinds = {o.kind for o in healthy.observations}
    plans = [plan for o in healthy.observations if o.kind == "issue_closure_ready" for plan in o.observed_state.get("plans", [])]
    assert plans and {"issue_suite_review", "issue_founder_decision"} <= healthyKinds  # something is closable when history is whole

    writeAtomic(root / CENSUS_INPUT, degrade(whole))
    scan = IssueHygieneSensor().scan_detailed(root, NOW_TEXT)  # no exception: Steward is not blinded

    kinds = {o.kind for o in scan.observations}
    assert "issue_closure_ready" not in kinds  # no closure rule is reported healthy on a missing inventory
    assert {"issue_suite_review", "issue_founder_decision"} <= kinds  # open-inventory observations continue
    (skipped,) = [item for item in scan.skipped if item["subjectId"] == "closure-operations"]
    assert "closed history is incomplete (count-unreadable)" in skipped["reason"]
    assert "issue closure operations are NOT EVALUATED" in skipped["reason"]
    assert "provider gh-api" in skipped["reason"] or "no closed-history telemetry recorded" in skipped["reason"]


def test_nothing_is_proven_closable_without_closed_history(tmp_path: Path) -> None:
    from gaia_cli.steward.issuehygiene.census import loadCensus
    from gaia_cli.steward.issuehygiene.sensor import _hygienePolicy, reconcileCensus
    from scripts.steward_issue_census import writeAtomic as write

    gh, root, writeAtomic = closableSetup(tmp_path)
    whole = gh.census(NOW)
    hygiene = _hygienePolicy(root)
    writeAtomic(root / CENSUS_INPUT, whole)
    full = reconcileCensus(loadCensus(root / CENSUS_INPUT, now=NOW), root, hygiene, NOW)
    writeAtomic(root / CENSUS_INPUT, degrade(whole))
    census = loadCensus(root / CENSUS_INPUT, now=NOW)
    degraded = reconcileCensus(census, root, hygiene, NOW, closedHistoryUnavailable=True)

    assert full["stats"]["classA"] > 0
    assert degraded["stats"]["classA"] == 0 and degraded["closedHistory"] == "unavailable"
    assert all(item["authority"] != "A" for item in degraded["items"])
    assert "closedHistory" not in full  # a normal manifest is unchanged
    # and without the explicit flag the old conservative behaviour holds: nothing is evaluated
    assert reconcileCensus(census, root, hygiene, NOW)["coverage"]["unknown"]


def test_the_closure_planner_has_nothing_to_plan_without_closed_history(tmp_path: Path) -> None:
    from gaia_cli.steward.issuehygiene.census import loadCensus
    from gaia_cli.steward.issuehygiene.closure import planClosures
    from gaia_cli.steward.issuehygiene.sensor import _hygienePolicy, reconcileCensus

    gh, root, writeAtomic = closableSetup(tmp_path)
    hygiene = _hygienePolicy(root)
    writeAtomic(root / CENSUS_INPUT, degrade(gh.census(NOW)))
    manifest = reconcileCensus(loadCensus(root / CENSUS_INPUT, now=NOW), root, hygiene, NOW, closedHistoryUnavailable=True)

    assert planClosures(dict(manifest), hygiene) == []


def test_a_stale_closed_only_census_is_not_degraded_but_blinds_steward(tmp_path: Path) -> None:
    gh, root, writeAtomic = closableSetup(tmp_path)
    writeAtomic(root / CENSUS_INPUT, degrade(gh.census(NOW - timedelta(hours=7))))
    with pytest.raises(SensorUnavailable):
        IssueHygieneSensor().scan_detailed(root, NOW_TEXT)


def test_the_sensor_still_blinds_steward_for_an_incomplete_open_inventory(tmp_path: Path) -> None:
    repo = Repo()
    original = repo.fetch

    def fetch(url: str) -> Response:
        return Response(502, {}, "{}") if "state=open" in url else original(url)

    document = collectCensus(REPO, NOW, fetch, 30, sleep=noSleep)
    root = makeCheckout(tmp_path, census=document)

    with pytest.raises(SensorUnavailable, match="incomplete"):
        IssueHygieneSensor().scan_detailed(root, NOW_TEXT)


def test_the_scheduled_workflow_restores_collects_and_persists_the_baseline_in_order() -> None:
    import yaml

    workflow = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "steward.yml"
    steps = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]["full-observe"]["steps"]
    names = [step.get("name", "") for step in steps]
    restore = names.index("Restore the closed-issue baseline")
    collect = next(i for i, step in enumerate(steps) if "steward_issue_census.py" in step.get("run", ""))
    persist = names.index("Persist the closed-issue baseline for the next run")
    assert restore < collect < persist
    assert steps[persist]["with"]["path"] == ".gaia/steward/inputs/closed-issue-baseline.json"
    assert steps[persist]["if"] == "always() && steps.baseline.outputs.state != 'restore-failed'"


def test_the_restore_step_distinguishes_a_first_run_from_a_restore_failure_and_passes_the_state_on() -> None:
    import yaml

    workflow = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "steward.yml"
    steps = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]["full-observe"]["steps"]
    restore = next(step for step in steps if step.get("name") == "Restore the closed-issue baseline")
    collect = next(step for step in steps if "steward_issue_census.py" in step.get("run", ""))
    script = restore["run"]

    assert restore["id"] == "baseline"
    for state in ("first-run", "restored", "restore-failed"):
        assert state in script
    assert "total_count" in script and "expired == false" in script  # only expired baselines is a failure, not a first run
    assert "STEWARD_CLOSED_BASELINE_RESEED" in restore["env"]["RESEED"]
    assert '--baseline-state "$BASELINE_STATE"' in collect["run"]
    assert collect["env"]["BASELINE_STATE"] == "${{ steps.baseline.outputs.state }}"


def test_loading_a_written_census_keeps_the_closed_history_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out, _ = run(tmp_path, Repo(total=3), monkeypatch)

    loaded = loadCensus(out, now=NOW)
    assert loaded.status.status == "complete"
    assert loaded.document["closedHistory"]["count"]["value"] == 3
    assert CENSUS_INPUT.name == out.name
