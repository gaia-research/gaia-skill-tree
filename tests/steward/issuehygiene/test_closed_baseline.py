"""Closed-issue census completeness (founder ruling steward-census-empty-page-crosschecks).

A durable last-known verified closed-issue count is a diagnostic baseline, never proof. These tests pin: empty-200
pages, a count drop explained by a reopen, an auth failure, baseline preservation across a failed scan, bounded
retries with telemetry, and that only closure operations (not the rest of Steward) fail closed on missing closed history.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
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


def test_an_unexplained_drop_is_held_pending_and_the_baseline_is_kept() -> None:
    judgement = rules.judge(BASELINE, 4, NOW_TEXT, "gh-api", 1)

    assert (judgement.explained, judgement.update) == (False, "pending-decrease")
    assert judgement.next is not None and judgement.next.count == 10
    assert judgement.next.pending["count"] == 4 and judgement.next.pending["consecutive"] == 1


def test_the_same_lower_count_on_a_second_run_is_adopted_but_a_different_one_restarts_the_wait() -> None:
    held = rules.judge(BASELINE, 4, NOW_TEXT, "gh-api", 0).next

    adopted = rules.judge(held, 4, "2026-10-22T00:00:00Z", "gh-api", 0)
    assert adopted.update == "adopted-decrease" and adopted.next.count == 4 and adopted.next.pending is None

    restarted = rules.judge(held, 5, "2026-10-22T00:00:00Z", "gh-api", 0)
    assert restarted.update == "pending-decrease" and restarted.next.pending["consecutive"] == 1


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
    assert section["count"] == {"value": 12, "verified": True}
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


def test_a_count_drop_nothing_explains_is_flagged_and_does_not_lower_the_baseline() -> None:
    section = history(census(Repo(total=4, events=[reopenedEvent(31)])))

    assert section["change"]["explained"] is False
    assert section["baseline"]["update"] == "pending-decrease"
    assert section["baseline"]["after"]["count"] == 10  # still the verified baseline
    assert section["baseline"]["after"]["pendingDecrease"]["count"] == 4


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


def test_an_empty_count_against_a_non_empty_baseline_is_a_suspected_false_empty() -> None:
    repo = Repo(total=0)

    section = history(census(repo))

    counts = [item for item in section["attempts"] if item["read"] == "closed-count"]
    assert len(counts) == CLOSED_ATTEMPTS and all(item["reason"] == "false-empty-suspect" for item in counts)
    assert section["refusal"] == "false-empty-suspect"
    assert section["count"]["verified"] is False
    assert section["baseline"]["after"] is None


def test_an_empty_count_on_a_first_run_is_a_genuine_empty_history() -> None:
    section = history(census(Repo(total=0), baseline=None))

    assert section["count"] == {"value": 0, "verified": True}
    assert section["baseline"]["after"]["count"] == 0


def test_a_window_holding_more_issues_than_the_total_is_not_verified() -> None:
    def crowded(url: str) -> Response:
        rows = [{"number": n, "state": "closed", "title": "t", "body": "", "labels": [], "user": {"login": "u"},
                 "created_at": "2026-10-10T00:00:00Z", "updated_at": "2026-10-10T00:00:00Z",
                 "closed_at": "2026-10-11T00:00:00Z", "comments": 0} for n in range(1, 6)]
        return Response(200, {}, json.dumps([] if "page=2" in url else rows))

    section = history(census(Repo(total=3, closedPage=crowded)))

    assert section["refusal"] == "window-exceeds-count" and section["count"]["verified"] is False
    assert section["baseline"]["after"] is None


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

    document = collectCensus(REPO, NOW, flaky, 30, baseline=BASELINE, sleep=slept.append, authenticated=True)

    section = history(document)
    counts = [item["reason"] for item in section["attempts"] if item["read"] == "closed-count"]
    assert counts == ["http-502", None]
    assert section["count"] == {"value": 11, "verified": True}
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

    section = history(collectCensus(REPO, NOW, limited, 30, baseline=BASELINE, sleep=noSleep, authenticated=False))

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


def test_an_unverified_count_never_overwrites_the_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    baselinePath = tmp_path / "inputs" / "closed-issue-baseline.json"
    rules.saveBaseline(baselinePath, REPO, BASELINE)
    before = baselinePath.read_bytes()

    code, _out, path = run(tmp_path, Repo(searchStatus=401), monkeypatch)

    assert code == 0  # the diagnostic never fails the census
    assert path.read_bytes() == before


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


def test_the_sensor_reports_missing_closed_history_as_not_evaluated_with_telemetry_and_does_not_blind_steward(tmp_path: Path) -> None:
    root = makeCheckout(tmp_path, census=failingClosedDocument())

    with pytest.raises(SensorNotEvaluated) as raised:
        IssueHygieneSensor().scan_detailed(root, NOW_TEXT)

    message = str(raised.value)
    assert "closed history is incomplete (empty-linked-page)" in message
    assert "issue closure operations are NOT EVALUATED" in message
    assert "provider gh-api" in message and "attempts 3" in message and "refusal empty-linked-page" in message
    # A person can fix a failed read, so the desk must not hide it as an absent input.
    assert raised.value.input_absent is False


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
    assert steps[persist]["if"] == "always()"


def test_loading_a_written_census_keeps_the_closed_history_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out, _ = run(tmp_path, Repo(total=3), monkeypatch)

    loaded = loadCensus(out, now=NOW)
    assert loaded.status.status == "complete"
    assert loaded.document["closedHistory"]["count"]["value"] == 3
    assert CENSUS_INPUT.name == out.name
