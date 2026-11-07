"""Closed-issue census completeness (founder ruling steward-census-empty-page-crosschecks).

A durable last-known verified closed-issue count is a diagnostic baseline, never proof. These tests pin: empty-200
pages, a count drop explained by a reopen, an auth failure, baseline preservation across a failed scan, bounded
retries with telemetry, and that only closure operations (not the rest of Steward) fail closed on missing closed history.
"""

from __future__ import annotations

import json
import shutil
import sys
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


def test_the_cross_check_runs_by_default_and_the_count_endpoint_is_exercised() -> None:
    repo = Repo(total=7)

    document = collectCensus(REPO, NOW, repo.fetch, 30, sleep=noSleep)  # no verification argument at all

    assert repo.searches() == 1
    assert history(document)["count"] == {"value": 7, "verified": True, "checked": True}
    assert document["completeness"]["closed"]["complete"] is True


def test_a_deliberately_unverified_census_marks_closed_operations_incomplete() -> None:
    repo = Repo(total=0)

    document = census(repo, verifyClosedCount=False)

    assert repo.searches() == 0
    assert history(document)["count"] == {"value": None, "verified": False, "checked": False}
    assert history(document)["refusal"] == "count-not-verified"
    assert document["completeness"]["closed"] == {"complete": False, "reason": "count-not-verified"}
    assert document["completeness"]["open"]["complete"] is True
    assert history(document)["baseline"]["after"] is None


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


SEEDED_EMPTY = "seeded (no prior baseline retrievable)"
SEEDED_INVALID = "seeded (prior baseline invalid)"


def evidenceOf(path: Path) -> Path:
    return path.with_name("closed-issue-baseline.restore-invalid.json")


@pytest.mark.parametrize(
    "content",
    ["{broken", json.dumps({"schemaVersion": rules.SCHEMA, "repo": "someone/else", "count": 4, "observedAt": BASE_TIME,
                            "source": "gh-api", "scope": rules.SCOPE})],
    ids=["corrupt", "wrong-repository"],
)
def test_an_invalid_restored_baseline_is_preserved_as_evidence_and_seeded_only_from_a_verified_complete_scan(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, content: str) -> None:
    path = tmp_path / "inputs" / "closed-issue-baseline.json"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")

    code, out, _ = run(tmp_path, Repo(total=5), monkeypatch)

    document = json.loads(out.read_text(encoding="utf-8"))
    baseline = document["closedHistory"]["baseline"]
    assert code == 0
    assert baseline["state"] == "restore-invalid" and baseline["problem"] in {"baseline-unreadable", "baseline-other-repository"}
    assert baseline["seeded"] == SEEDED_INVALID  # the re-seed is visible in the telemetry ...
    assert f"closed-issue baseline: {SEEDED_INVALID}" in capsys.readouterr().out  # ... and in the census output
    assert evidenceOf(path).read_text(encoding="utf-8") == content  # the invalid file is kept, byte for byte
    assert rules.loadBaseline(path, REPO)[0].count == 5  # and only a verified complete scan produced the new one


def test_an_invalid_restored_baseline_is_never_replaced_by_a_failed_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "inputs" / "closed-issue-baseline.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")

    code, out, _ = run(tmp_path, Repo(searchStatus=401), monkeypatch)

    assert code == 3
    assert not path.exists()  # nothing was seeded
    assert evidenceOf(path).read_text(encoding="utf-8") == "{broken"
    assert json.loads(out.read_text(encoding="utf-8"))["closedHistory"]["baseline"]["after"] is None


def test_a_second_invalid_file_does_not_destroy_the_first_piece_of_evidence_unless_replaced_by_the_same_name(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "inputs" / "closed-issue-baseline.json"
    path.parent.mkdir(parents=True)
    path.write_text("{first", encoding="utf-8")
    run(tmp_path, Repo(total=5), monkeypatch)
    assert evidenceOf(path).read_text(encoding="utf-8") == "{first"
    assert path.is_file() and path.read_text(encoding="utf-8") != "{first"


def failEvidenceMove(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    """Make preserving the invalid file fail, and only that: every other os.replace (the census itself) works."""

    import os

    real = os.replace

    def replace(src, dst, *args, **kwargs):
        if "restore-invalid" in str(dst):
            raise error
        return real(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replace)


def test_when_the_invalid_baseline_cannot_be_preserved_nothing_is_seeded_over_it_and_the_step_fails(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    path = tmp_path / "inputs" / "closed-issue-baseline.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")
    failEvidenceMove(monkeypatch, PermissionError("read-only"))

    code, out, _ = run(tmp_path, Repo(total=5), monkeypatch)  # a fully verified, complete scan

    captured = capsys.readouterr()
    document = json.loads(out.read_text(encoding="utf-8"))
    baseline = document["closedHistory"]["baseline"]
    assert code == 4  # the baseline step fails
    assert path.read_text(encoding="utf-8") == "{broken"  # the original is untouched, never overwritten
    assert not evidenceOf(path).exists()
    assert baseline["update"] == "not-evaluated" and baseline["after"] is None and "seeded" not in baseline
    assert baseline["state"] == "restore-invalid-unpreserved"
    assert baseline["problem"] == "restore-invalid-unpreserved:PermissionError"
    assert "NOT EVALUATED" in captured.err and "seeded" not in captured.out
    assert document["completeness"]["issues"]["complete"] is True  # the census itself is sound and was still written


def test_a_failed_move_together_with_an_incomplete_census_carries_both_conditions(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    path = tmp_path / "inputs" / "closed-issue-baseline.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")
    failEvidenceMove(monkeypatch, PermissionError("read-only"))

    code, out, _ = run(tmp_path, Repo(searchStatus=401), monkeypatch)  # the closed count is refused: the census is incomplete

    captured = capsys.readouterr()
    document = json.loads(out.read_text(encoding="utf-8"))
    assert code == 5  # not 4: the exit code carries BOTH conditions
    assert document["completeness"]["issues"]["complete"] is False
    assert document["completeness"]["closed"] == {"complete": False, "reason": "http-401"}
    assert "census INCOMPLETE" in captured.err and "closed-issue baseline: NOT EVALUATED" in captured.err
    assert path.read_text(encoding="utf-8") == "{broken" and not evidenceOf(path).exists()


def test_the_exit_codes_are_unchanged_without_a_baseline_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    complete = run(tmp_path / "a", Repo(total=5), monkeypatch)[0]
    incomplete = run(tmp_path / "b", Repo(searchStatus=401), monkeypatch)[0]
    assert (complete, incomplete) == (0, 3)


STUB = """\
import os, shutil, sys
from pathlib import Path
target = Path(".gaia/steward/inputs/github-issues.json")
target.parent.mkdir(parents=True, exist_ok=True)
if os.environ.get("STUB_DOC"):
    shutil.copy(os.environ["STUB_DOC"], target)
sys.exit(int(os.environ["STUB_CODE"]))
"""


def runCensusStep(tmp_path: Path, code: int, document: dict | None):
    """Execute the workflow's real census reporting step in bash against a stub collector that exits `code`."""

    import os
    import subprocess

    work = tmp_path / "work"
    (work / "scripts").mkdir(parents=True)
    (work / "scripts" / "steward_issue_census.py").write_text(STUB, encoding="utf-8")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "python").symlink_to(sys.executable)
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "RUNNER_TEMP": str(tmp_path), "GITHUB_REPOSITORY": REPO,
           "BASELINE_STATE": "restored", "STUB_CODE": str(code), "GH_TOKEN": "x"}
    if document is not None:
        (tmp_path / "doc.json").write_text(json.dumps(document), encoding="utf-8")
        env["STUB_DOC"] = str(tmp_path / "doc.json")
    step = next(step for step in jobSteps() if step.get("id") == "census")
    result = subprocess.run(["bash", "-e", "-c", step["run"]], cwd=work, env=env, capture_output=True, text=True, check=False)

    def report(name: str):
        return (tmp_path / name).read_text().strip() if (tmp_path / name).exists() else None

    return result, report("inputs-census.txt"), report("inputs-baseline.txt")


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not installed")
class TestCensusReportingStep:
    @staticmethod
    def whole() -> dict:
        return census(Repo(total=5), baseline=None)

    @staticmethod
    def broken() -> dict:
        return census(Repo(searchStatus=401))

    def test_exit_four_with_an_incomplete_census_is_reported_partial_not_ok(self, tmp_path: Path) -> None:
        result, censusLine, baselineLine = runCensusStep(tmp_path, 4, self.broken())  # inconsistent code: the file decides
        assert censusLine.startswith("issue-census=partial") and censusLine != "issue-census=ok"
        assert baselineLine.startswith("closed-baseline=failed") and result.returncode == 4

    def test_exit_five_reports_both_conditions(self, tmp_path: Path) -> None:
        result, censusLine, baselineLine = runCensusStep(tmp_path, 5, self.broken())
        assert censusLine.startswith("issue-census=partial") and "NOT EVALUATED" in censusLine
        assert baselineLine.startswith("closed-baseline=failed") and result.returncode == 5
        assert "::error" in result.stdout

    def test_exit_four_with_a_complete_census_is_ok_and_still_reports_the_baseline_failure(self, tmp_path: Path) -> None:
        result, censusLine, baselineLine = runCensusStep(tmp_path, 4, self.whole())
        assert censusLine == "issue-census=ok" and baselineLine.startswith("closed-baseline=failed") and result.returncode == 4

    def test_exit_zero_is_ok_only_because_the_file_says_complete(self, tmp_path: Path) -> None:
        result, censusLine, baselineLine = runCensusStep(tmp_path, 0, self.whole())
        assert (result.returncode, censusLine, baselineLine) == (0, "issue-census=ok", None)

    def test_exit_zero_with_an_incomplete_file_is_never_reported_ok(self, tmp_path: Path) -> None:
        _result, censusLine, _ = runCensusStep(tmp_path, 0, self.broken())
        assert censusLine.startswith("issue-census=partial")

    def test_exit_three_with_a_complete_looking_file_is_partial(self, tmp_path: Path) -> None:
        _result, censusLine, _ = runCensusStep(tmp_path, 3, self.whole())
        assert censusLine.startswith("issue-census=partial")

    def test_a_missing_or_unusable_census_file_is_failed(self, tmp_path: Path) -> None:
        for number, code in enumerate((4, 5, 3, 2)):
            _result, censusLine, _ = runCensusStep(tmp_path / str(number), code, None)
            assert censusLine.startswith("issue-census=failed"), code

    def test_an_unexpected_exit_code_is_failed_even_with_a_complete_looking_file(self, tmp_path: Path) -> None:
        _result, censusLine, _ = runCensusStep(tmp_path, 2, self.whole())
        assert censusLine.startswith("issue-census=failed")


def test_an_unpreserved_baseline_is_not_replaced_by_a_later_successful_run_either_until_it_can_be_preserved(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "inputs" / "closed-issue-baseline.json"
    path.parent.mkdir(parents=True)
    wrongRepo = json.dumps({"schemaVersion": rules.SCHEMA, "repo": "someone/else", "count": 4, "observedAt": BASE_TIME,
                            "source": "gh-api", "scope": rules.SCOPE})
    path.write_text(wrongRepo, encoding="utf-8")

    with monkeypatch.context() as broken:
        failEvidenceMove(broken, OSError("disk full"))
        assert run(tmp_path, Repo(total=5), broken)[0] == 4
        assert path.read_text(encoding="utf-8") == wrongRepo

    code, _out, _ = run(tmp_path, Repo(total=5), monkeypatch)  # the move works again

    assert code == 0 and evidenceOf(path).read_text(encoding="utf-8") == wrongRepo
    assert rules.loadBaseline(path, REPO)[0].count == 5


def test_the_census_step_fails_visibly_on_exit_four_and_nothing_is_persisted_after_it() -> None:
    steps = {step.get("name"): step for step in jobSteps()}
    census = next(step for step in jobSteps() if "steward_issue_census.py" in step.get("run", ""))
    stage = steps["Stage the closed-issue baseline for upload"]

    assert census["id"] == "census" and census["continue-on-error"] is True  # visible failure, observation still runs
    assert "-eq 4" in census["run"] and "-eq 5" in census["run"] and 'exit "$code"' in census["run"]
    assert "closed-baseline=failed" in census["run"]
    assert "tostring" in census["run"]  # the census status is read from the file's completeness, not inferred from the code
    assert "steps.census.outcome != 'failure'" in stage["if"]  # the invalid file is not re-uploaded as the newest baseline


def test_an_empty_store_is_seeded_only_from_a_verified_complete_scan_and_labelled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    out = tmp_path / "inputs" / "github-issues.json"
    monkeypatch.setenv("GH_TOKEN", "test-token-not-real")

    code = main(["--repo", REPO, "--out", str(out), "--closed-window-days", "30", "--now", NOW_TEXT,
                 "--baseline-state", "empty-store"], fetch=Repo(total=12).fetch)

    baseline = json.loads(out.read_text(encoding="utf-8"))["closedHistory"]["baseline"]
    assert code == 0 and baseline["seeded"] == SEEDED_EMPTY and baseline["state"] == "empty-store"
    assert f"closed-issue baseline: {SEEDED_EMPTY}" in capsys.readouterr().out
    assert rules.loadBaseline(out.parent / "closed-issue-baseline.json", REPO)[0].count == 12


def test_an_empty_store_is_not_seeded_from_an_unverified_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "inputs" / "github-issues.json"
    monkeypatch.setenv("GH_TOKEN", "test-token-not-real")

    code = main(["--repo", REPO, "--out", str(out), "--closed-window-days", "30", "--now", NOW_TEXT,
                 "--baseline-state", "empty-store"], fetch=Repo(searchStatus=401).fetch)

    assert code == 3 and not (out.parent / "closed-issue-baseline.json").exists()


def test_a_normal_restore_is_not_labelled_as_seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    baselinePath = tmp_path / "inputs" / "closed-issue-baseline.json"
    rules.saveBaseline(baselinePath, REPO, BASELINE)

    _code, out, _ = run(tmp_path, Repo(total=11), monkeypatch)

    assert "seeded" not in json.loads(out.read_text(encoding="utf-8"))["closedHistory"]["baseline"]


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
    names = [step.get("name", "") for step in jobSteps()]
    restore = names.index("Restore the closed-issue baseline")
    collect = next(i for i, step in enumerate(jobSteps()) if "steward_issue_census.py" in step.get("run", ""))
    persist = names.index("Persist the closed-issue baseline for the next run")
    assert restore < collect < persist


WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "steward.yml"


def jobSteps() -> list[dict]:
    import yaml

    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["full-observe"]["steps"]


def stepNamed(name: str) -> dict:
    return next(step for step in jobSteps() if step.get("name") == name)


FAKE_GH = """#!/bin/bash
# a scripted `gh`: `api` answers from FAKE_API_JSON or fails; `run download` materializes FAKE_DOWNLOAD or fails
case "$1" in
  api) if [ -n "$FAKE_API_FAIL" ]; then exit 1; fi; cat "$FAKE_API_JSON" ;;
  run) if [ -n "$FAKE_DOWNLOAD_FAIL" ]; then exit 1; fi
       dir=""; while [ $# -gt 0 ]; do if [ "$1" = "--dir" ]; then dir="$2"; fi; shift; done
       mkdir -p "$dir"; if [ -n "$FAKE_DOWNLOAD" ]; then cp "$FAKE_DOWNLOAD" "$dir/closed-issue-baseline.json"; fi ;;
esac
"""


def restoreOutcome(tmp_path: Path, *, listing=None, apiFail=False, downloadFail=False, download=True) -> tuple[str, Path]:
    """Run the workflow's real restore step in bash against a fake gh and return (state, workdir)."""

    import os
    import subprocess

    work = tmp_path / "work"
    bin_ = tmp_path / "bin"
    work.mkdir()
    bin_.mkdir()
    (bin_ / "gh").write_text(FAKE_GH, encoding="utf-8")
    (bin_ / "gh").chmod(0o755)
    (tmp_path / "api.json").write_text(json.dumps(listing if listing is not None else {"total_count": 0, "artifacts": []}))
    (tmp_path / "stored.json").write_text(json.dumps({"stored": True}))
    output = tmp_path / "github-output"
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "GITHUB_REPOSITORY": REPO, "GITHUB_OUTPUT": str(output),
           "RUNNER_TEMP": str(tmp_path), "FAKE_API_JSON": str(tmp_path / "api.json"), "GH_TOKEN": "x"}
    if apiFail:
        env["FAKE_API_FAIL"] = "1"
    if downloadFail:
        env["FAKE_DOWNLOAD_FAIL"] = "1"
    if download:
        env["FAKE_DOWNLOAD"] = str(tmp_path / "stored.json")
    subprocess.run(["bash", "-e", "-c", stepNamed("Restore the closed-issue baseline")["run"]], cwd=work, env=env,
                   check=True, capture_output=True)
    return output.read_text().strip().split("=", 1)[1], work


def artifacts(*expired: bool) -> dict:
    return {"total_count": len(expired), "artifacts": [{"expired": e, "workflow_run": {"id": 100 + i}} for i, e in enumerate(expired)]}


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not installed")
class TestRestoreStep:
    def test_a_listing_with_a_live_artifact_is_restored(self, tmp_path: Path) -> None:
        state, work = restoreOutcome(tmp_path, listing=artifacts(False, True))
        assert state == "restored"
        assert json.loads((work / ".gaia/steward/inputs/closed-issue-baseline.json").read_text()) == {"stored": True}

    def test_an_empty_store_is_not_a_failure(self, tmp_path: Path) -> None:
        state, work = restoreOutcome(tmp_path, listing=artifacts())
        assert state == "empty-store" and not (work / ".gaia/steward/inputs/closed-issue-baseline.json").exists()

    def test_only_expired_artifacts_is_an_empty_store_not_a_restore_failure(self, tmp_path: Path) -> None:
        state, _ = restoreOutcome(tmp_path, listing=artifacts(True, True))
        assert state == "empty-store"

    def test_an_api_failure_is_a_restore_failure_and_never_an_empty_store(self, tmp_path: Path) -> None:
        state, work = restoreOutcome(tmp_path, apiFail=True)
        assert state == "restore-failed" and not (work / ".gaia/steward/inputs/closed-issue-baseline.json").exists()

    def test_a_download_failure_is_a_restore_failure(self, tmp_path: Path) -> None:
        state, _ = restoreOutcome(tmp_path, listing=artifacts(False), downloadFail=True)
        assert state == "restore-failed"

    def test_a_download_that_yields_no_file_is_a_restore_failure(self, tmp_path: Path) -> None:
        state, _ = restoreOutcome(tmp_path, listing=artifacts(False), download=False)
        assert state == "restore-failed"

    def test_no_environment_variable_can_turn_a_failure_into_a_seed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RESEED", "true")
        monkeypatch.setenv("STEWARD_CLOSED_BASELINE_RESEED", "true")
        state, _ = restoreOutcome(tmp_path, apiFail=True)
        assert state == "restore-failed"


def test_the_restore_step_has_no_reseed_override_anywhere() -> None:
    text = WORKFLOW.read_text(encoding="utf-8") + (Path(__file__).resolve().parents[3] / "scripts" / "steward_issue_census.py").read_text(encoding="utf-8")
    assert "RESEED" not in text


def test_the_census_step_receives_the_restore_state() -> None:
    collect = next(step for step in jobSteps() if "steward_issue_census.py" in step.get("run", ""))
    assert '--baseline-state "$BASELINE_STATE"' in collect["run"]
    assert collect["env"]["BASELINE_STATE"] == "${{ steps.baseline.outputs.state }}"


def test_the_baseline_handoff_is_staged_visibly_and_a_missing_file_is_never_silent() -> None:
    steps = {step.get("name"): step for step in jobSteps()}
    stage = steps["Stage the closed-issue baseline for upload"]
    upload = steps["Persist the closed-issue baseline for the next run"]
    evidence = steps["Preserve an invalid restored baseline as evidence"]

    assert upload["with"]["path"] == "closed-baseline-handoff/" and evidence["with"]["path"] == "closed-baseline-invalid/"
    for step in (upload, evidence):
        assert not any(part.startswith(".") for part in step["with"]["path"].split("/"))  # upload-artifact@v4 skips hidden paths
        assert step["with"]["if-no-files-found"] == "error"
    assert "restore-failed" in stage["if"] and "restore-failed" in upload["if"]  # a failed restore uploads nothing
    assert "::warning" in stage["run"]
    names = [step.get("name") for step in jobSteps()]
    assert names.index(stage["name"]) < names.index(upload["name"])


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_the_baseline_staging_step_copies_the_baseline_and_the_invalid_evidence_to_visible_directories(tmp_path: Path) -> None:
    import subprocess

    inputs = tmp_path / ".gaia" / "steward" / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "closed-issue-baseline.json").write_text("{}")
    (inputs / "closed-issue-baseline.restore-invalid.json").write_text("{bad")

    subprocess.run(["bash", "-e", "-c", stepNamed("Stage the closed-issue baseline for upload")["run"]], cwd=tmp_path, check=True, capture_output=True)

    assert (tmp_path / "closed-baseline-handoff" / "closed-issue-baseline.json").is_file()
    assert (tmp_path / "closed-baseline-invalid" / "closed-issue-baseline.restore-invalid.json").read_text() == "{bad"


def test_the_staging_step_warns_instead_of_failing_when_no_baseline_exists(tmp_path: Path) -> None:
    import subprocess

    result = subprocess.run(["bash", "-e", "-c", stepNamed("Stage the closed-issue baseline for upload")["run"]], cwd=tmp_path,
                            check=True, capture_output=True, text=True)

    assert "::warning" in result.stdout and not list((tmp_path / "closed-baseline-handoff").iterdir())


def test_loading_a_written_census_keeps_the_closed_history_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out, _ = run(tmp_path, Repo(total=3), monkeypatch)

    loaded = loadCensus(out, now=NOW)
    assert loaded.status.status == "complete"
    assert loaded.document["closedHistory"]["count"]["value"] == 3
    assert CENSUS_INPUT.name == out.name
