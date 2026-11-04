"""Like-for-like count proof; no tolerance, search index or hardcoded offsets."""
import json
import subprocess

import pytest

from scripts.upstream_watcher import live
from scripts.upstream_watcher.live import GhError, LiveGh
from test_list_truncation import issues
from upstream_fakes import RestGhRunner


class ConnectionRunner(RestGhRunner):
    def __init__(self, rows, counts=None, payload=None, **knobs):
        super().__init__(rows, **knobs)
        self.counts = iter(counts or [(sum("pull_request" not in r for r in rows), sum("pull_request" in r for r in rows))] * 20)
        self.payload = payload
        self.graphql = 0

    def __call__(self, args, **kwargs):
        if args[1:3] == ["api", "graphql"]:
            self.graphql += 1
            assert "search(" not in next(a for a in args if a.startswith("query=")).lower()
            n, p = next(self.counts)
            body = self.payload if self.payload is not None else {"data": {"repository": {"issues": {"totalCount": n}, "pullRequests": {"totalCount": p}}}}
            return subprocess.CompletedProcess(args, 0, json.dumps(body), "")
        return super().__call__(args, **kwargs)


@pytest.fixture(autouse=True)
def noSleep(monkeypatch):
    monkeypatch.setattr(live, "RETRY_SLEEP", lambda _: None)


def mixedRows(n=218, p=5):
    return issues(n) + [{**r, "number": 10000 + i, "pull_request": {"url": "synthetic"}} for i, r in enumerate(issues(p))]


def test_metadata_disagreement_requires_exact_typed_counts_and_two_full_walks():
    rows = mixedRows()
    runner = ConnectionRunner(rows, open_count=226)
    assert LiveGh(runner=runner).list_issues("open") == rows
    assert runner.graphql == 2
    # Neither PRs nor the 3-item metadata discrepancy were dropped or added.
    assert len(rows) == 223
    assert runner.writes == []


def test_actual_issue_and_pr_totals_cannot_be_swapped_even_with_matching_combined_count():
    runner = ConnectionRunner(mixedRows(), counts=[(217, 6)] * 20, open_count=226)
    with pytest.raises(GhError, match="counts changed or listing disagrees"):
        LiveGh(runner=runner).list_issues("open")
    assert runner.writes == []


def test_concurrent_connection_count_changes_cannot_confirm_old_listing():
    runner = ConnectionRunner(mixedRows(), counts=[(218, 5), (219, 5)] * 3, open_count=226)
    with pytest.raises(GhError, match="not confirmed"):
        LiveGh(runner=runner).list_issues("open")


def test_transient_count_change_recovers_only_after_stable_complete_retry():
    runner = ConnectionRunner(mixedRows(), counts=[(218, 5), (219, 5), (218, 5), (218, 5)], open_count=226)
    assert len(LiveGh(runner=runner).list_issues("open")) == 223
    assert runner.graphql == 4


@pytest.mark.parametrize("payload", [
    {}, {"data": {"repository": None}},
    {"errors": [{"message": "synthetic denied"}], "data": {"repository": {"issues": {"totalCount": 218}, "pullRequests": {"totalCount": 5}}}},
    {"data": {"repository": {"issues": {"totalCount": True}, "pullRequests": {"totalCount": 5}}}},
    {"data": {"repository": {"issues": {"totalCount": -1}, "pullRequests": {"totalCount": 5}}}},
])
def test_partial_unknown_or_malformed_connection_count_never_authorizes(payload):
    runner = ConnectionRunner(mixedRows(), payload=payload, open_count=226)
    with pytest.raises(GhError, match="connection counts unavailable"):
        LiveGh(runner=runner).list_issues("open")


def test_partial_list_cannot_be_accepted_because_metadata_is_stale():
    runner = ConnectionRunner(mixedRows(215, 0), counts=[(218, 0)] * 20, open_count=218)
    with pytest.raises(GhError):
        LiveGh(runner=runner).list_issues("open")


@pytest.mark.parametrize("knobs", [
    {"empty_pages": {("open", "", 2)}},
    {"no_link_pages": {("open", "", 1)}},
    {"short_pages": {("open", "", 1)}},
    {"fail_pages": {("open", "", 2)}},
])
def test_count_fallback_never_erases_a_pagination_failure(knobs):
    runner = ConnectionRunner(mixedRows(), open_count=226, **knobs)
    with pytest.raises(GhError):
        LiveGh(runner=runner).list_issues("open")
    assert runner.writes == []


def test_duplicate_rows_are_refused_even_if_length_matches_repository_count():
    runner = ConnectionRunner(issues(100) + issues(100), open_count=200)
    with pytest.raises(GhError, match="duplicate identities"):
        LiveGh(runner=runner).list_issues("open")


def test_empty_with_unknown_count_is_not_confirmed_by_partial_graphql():
    runner = ConnectionRunner([], count_fails=True, payload={})
    with pytest.raises(GhError):
        LiveGh(runner=runner).list_issues("open")
