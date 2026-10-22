"""The watcher's list reads are complete or refused (PR #2133, list-truncation fix).

The census walk is the single pagination contract. On top of it the watcher confirms an open listing exactly against
the repository's ``open_issues_count``, retrying a mismatch because a create or close can land between the two reads.
A closed listing has no count, so it is confirmed by its walk alone: a full last page is refused, because its end
cannot be proven. A short page before the last is refused everywhere.

The fake serves listings the way GitHub does. Every full page carries a next link, and the link names the repository by
numeric id. Each knob below injects one anomaly that the walk must refuse or recover from.
"""

import pytest

from scripts.upstream_watcher.live import GhError, LiveGh
from upstream_fakes import RestGhRunner

REPO = "gaia-research/gaia-skill-tree"


def issues(count, state="open", label=None):
    return [
        {"number": 1000 + index, "title": f"t{index}", "state": state,
         "labels": [{"name": label}] if label else [], "body": "", "updated_at": "2026-10-21T00:00:00Z"}
        for index in range(count)
    ]


def reader(rows, **knobs):
    return LiveGh(repo=REPO, runner=RestGhRunner(rows, **knobs))


# --- open listings: confirmed exactly by the repository count ----------------------------------------------------


def test_every_open_issue_is_returned_when_every_page_is_served():
    assert len(reader(issues(150)).list_issues("open")) == 150


def test_an_empty_page_while_more_issues_exist_is_refused_not_returned_as_the_whole_list():
    with pytest.raises(GhError):
        reader(issues(150), empty_pages={("open", "", 2)}).list_issues("open")


def test_an_intermittent_empty_page_that_clears_on_retry_is_recovered_and_returns_every_issue():
    listed = reader(issues(150), empty_once={("open", "", 2)}).list_issues("open")
    assert len(listed) == 150


def test_a_persistent_empty_page_is_refused_after_the_retries_are_spent():
    runner = RestGhRunner(issues(232), empty_pages={("open", "", 3)})
    with pytest.raises(GhError, match="not confirmed after"):
        LiveGh(repo=REPO, runner=runner).list_issues("open")


def test_an_exact_multiple_of_the_page_size_is_confirmed_when_the_count_agrees():
    assert len(reader(issues(100)).list_issues("open")) == 100


def test_an_exact_multiple_is_refused_when_the_count_disagrees_with_the_empty_linked_page():
    with pytest.raises(GhError):
        reader(issues(100), open_count=150).list_issues("open")


def test_an_exact_multiple_is_refused_when_the_count_cannot_be_read():
    with pytest.raises(GhError):
        reader(issues(100), count_fails=True).list_issues("open")


def test_a_short_page_before_the_last_is_refused_because_the_listing_no_longer_matches_the_count():
    with pytest.raises(GhError):
        reader(issues(150), short_pages={("open", "", 1)}).list_issues("open")


def test_a_full_page_whose_next_link_was_dropped_is_refused_when_the_listing_continues_without_it():
    with pytest.raises(GhError, match="unlinked-continuation"):
        reader(issues(150), no_link_pages={("open", "", 1)}).list_issues("open")


def test_a_full_page_without_a_link_is_accepted_only_when_the_count_confirms_the_end():
    assert len(reader(issues(100), no_link_pages={("open", "", 1)}).list_issues("open")) == 100
    with pytest.raises(GhError):
        reader(issues(100), no_link_pages={("open", "", 1)}, open_count=150).list_issues("open")


def test_a_labelled_open_list_is_taken_from_the_verified_open_listing():
    rows = issues(30, label="upstream:release") + issues(120)
    labelled = reader(rows).list_issues("open", labels="upstream:release")
    assert len(labelled) == 30


def test_a_labelled_open_list_inherits_the_refusal_of_the_open_listing():
    with pytest.raises(GhError):
        reader(issues(150), empty_pages={("open", "", 2)}).list_issues("open", labels="upstream:release")


# --- closed listings: no count, so the walk must prove its own end ----------------------------------------------


def test_a_closed_history_is_returned_when_its_last_page_is_partial():
    closed = reader(issues(150, state="closed", label="upstream:release"))
    assert len(closed.list_issues("closed", labels="upstream:release")) == 150


def test_a_closed_history_of_exactly_one_full_page_is_refused_because_its_end_cannot_be_confirmed():
    with pytest.raises(GhError, match="empty-linked-page"):
        reader(issues(100, state="closed", label="upstream:release")).list_issues("closed", labels="upstream:release")


def test_an_intermittent_empty_closed_page_that_clears_on_retry_returns_the_whole_history():
    closed = reader(issues(150, state="closed", label="upstream:release"),
                    empty_once={("closed", "upstream:release", 2)})
    assert len(closed.list_issues("closed", labels="upstream:release")) == 150


def test_an_empty_first_closed_page_that_clears_on_retry_returns_the_whole_history():
    """The live anomaly: a closed read came back empty while 31 closed umbrellas existed."""
    closed = reader(issues(31, state="closed", label="upstream:release"),
                    empty_once={("closed", "upstream:release", 1)})
    assert len(closed.list_issues("closed", labels="upstream:release")) == 31


def test_a_closed_history_empty_on_every_attempt_is_accepted_as_empty():
    """Nothing on the listing can tell a true empty history from one lost on every read. This is the residual."""
    empty = reader(issues(31, state="closed", label="upstream:release"),
                   empty_pages={("closed", "upstream:release", 1)})
    assert empty.list_issues("closed", labels="upstream:release") == []


def test_a_full_closed_page_whose_next_link_was_dropped_is_refused():
    with pytest.raises(GhError):
        reader(issues(100, state="closed", label="upstream:release"),
               no_link_pages={("closed", "upstream:release", 1)}).list_issues("closed", labels="upstream:release")


def test_a_closed_listing_that_fails_mid_walk_is_refused():
    with pytest.raises(GhError):
        reader(issues(150, state="closed", label="upstream:release"),
               fail_pages={("closed", "upstream:release", 2)}).list_issues("closed", labels="upstream:release")


# --- the planner refuses creation and reports the reason -------------------------------------------------------

from scripts.upstream_watcher.batch import run_batch  # noqa: E402
from upstream_fakes import index_from_entries  # noqa: E402

SUITE_FINDING = {
    "finding_type": "update", "skillId": "garrytan/gbrain", "currentVersion": "v0", "newVersion": "v1",
    "releasedAt": "2026-10-21T10:00:00Z", "sourceUrl": "https://github.com/garrytan/gbrain/releases/tag/v1",
    "mode": "components", "componentAdds": ["ask-user"], "componentRemoves": [], "linkLiveness": [], "nameDrift": [],
}


def test_an_intermittent_empty_open_listing_refuses_every_create_and_reports_the_reason():
    runner = RestGhRunner(issues(150), empty_pages={("open", "", 2)})
    gh = LiveGh(repo=REPO, runner=runner)

    report, code = run_batch([SUITE_FINDING], gh, apply=True, index_loader=lambda: index_from_entries([]))

    assert code == 3
    assert runner.writes == [], "no issue is created or edited while the open listing is unconfirmed"
    assert report["unknownEvidence"][0]["source"] == "github-list"
    assert "not confirmed" in report["unknownEvidence"][0]["detail"]


def test_an_incomplete_closed_history_refuses_the_create_and_reports_the_reason():
    runner = RestGhRunner(issues(100, state="closed", label="upstream:release"))
    gh = LiveGh(repo=REPO, runner=runner)

    report, code = run_batch([SUITE_FINDING], gh, apply=True, index_loader=lambda: index_from_entries([]))

    assert code == 3
    assert runner.writes == []
    assert "empty-linked-page" in report["unknownEvidence"][0]["detail"]
