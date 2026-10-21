"""Regression tests for M6 (#2131 verifier FAIL): rejection memory must not expire.

A rejected intake child closed more than 30 days ago must still suppress its candidate
(priorDisposition rejected:#N). The planner now reads the full labelled closed child
history with list pagination, not the 30-day recently-closed window. A pagination failure
on that read is unknown evidence (GhError), so the run writes nothing.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess

import pytest

from scripts.upstream_watcher import batch
from scripts.upstream_watcher.batch import plan_suite
from scripts.upstream_watcher.live import GhError, LiveGh, read_live
from upstream_fakes import FakeGh, RestGhRunner, index_from_entries

INDEX = index_from_entries([])
OLD = "2026-01-01T00:00:00Z"  # far outside the 30-day window used by the planner
NOW = dt.datetime(2026, 10, 21, tzinfo=dt.timezone.utc)


def child(number, slug, state="open", labels=("intake", "upstream:child"), updated=None):
    return {
        "number": number,
        "title": f"[intake] garrytan/{slug}",
        "state": state,
        "labels": [{"name": name} for name in labels],
        "body": f"> Umbrella: #5000.\n\n**Suggested ID:** `garrytan/{slug}`\n",
        "updated_at": updated or "2026-10-20T00:00:00Z",
        "pull_request": None,
    }


def finding(adds):
    return {
        "finding_type": "update",
        "skillId": "garrytan/gbrain",
        "currentVersion": "v1",
        "newVersion": "v2",
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": "https://github.com/garrytan/gbrain/releases/tag/v2",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
    }


def test_rejection_older_than_the_window_still_suppresses_the_candidate():
    gh = FakeGh()
    gh.add(child(41, "ask-user", state="closed", labels=("intake", "upstream:child", "upstream:rejected"), updated=OLD))
    plan = plan_suite(finding(["ask-user"]), read_live(gh, now=NOW), INDEX)
    row = plan["payload"]["candidates"][0]
    assert row["precheck"]["priorDisposition"] == "rejected:#41"
    assert row["status"] == "rejected"
    assert plan["suppressed"] == ["garrytan/gbrain:ask-user"]


def test_closed_children_older_than_the_window_are_in_the_snapshot():
    gh = FakeGh()
    gh.add(child(41, "ask-user", state="closed", labels=("intake", "upstream:child", "upstream:rejected"), updated=OLD))
    numbers = {issue["number"] for issue in read_live(gh, now=NOW)["issues"]}
    assert 41 in numbers


def test_rejection_on_a_later_page_of_the_closed_history_is_still_found():
    """150 closed children: the rejected one is number 150, which only page 2 holds."""
    rows = [
        {
            "number": number,
            "title": f"[intake] garrytan/slug-{number}",
            "state": "closed",
            "labels": [{"name": "intake"}, {"name": "upstream:child"}]
            + ([{"name": "upstream:rejected"}] if number == 150 else []),
            "body": f"**Suggested ID:** `garrytan/slug-{number}`\n",
            "updated_at": OLD,
        }
        for number in range(1, 151)
    ]
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=RestGhRunner(rows))
    live = read_live(gh, now=NOW)
    plan = plan_suite(finding(["slug-150"]), live, INDEX)
    assert plan["payload"]["candidates"][0]["precheck"]["priorDisposition"] == "rejected:#150"


def test_pagination_failure_on_the_closed_child_history_is_unknown_evidence():
    rows = [child(7, "ask-user", state="closed", labels=("upstream:child", "upstream:rejected"), updated=OLD)]
    runner = RestGhRunner(rows, fail_pages=[("closed", "upstream:child", 1)])
    with pytest.raises(GhError):
        read_live(LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner), now=NOW)


def test_a_closed_child_without_the_rejected_label_is_not_a_rejection():
    gh = FakeGh()
    gh.add(child(42, "ask-user", state="closed", labels=("intake", "upstream:child"), updated=OLD))
    plan = plan_suite(finding(["ask-user"]), read_live(gh, now=NOW), INDEX)
    assert plan["payload"]["candidates"][0]["precheck"]["priorDisposition"] == "none"
