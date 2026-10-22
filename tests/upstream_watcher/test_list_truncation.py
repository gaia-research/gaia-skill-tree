"""Known defect, pinned (PR #2133 audit): the watcher's list reader trusts a short or empty page as the end of a list.

``LiveGh.list_issues`` ends pagination at the first page shorter than per_page. A page that comes back empty or short
while more issues exist therefore returns a truncated list with no error. The planner then reads a missing open
canonical umbrella as "none open" (a duplicate create) or a missing closed umbrella as "no evidence" (a re-create).

The test is strict xfail: it asserts the correct behaviour (refuse the truncated read, exit unknown evidence) and
fails today. Remove the marker when the reader cross-checks its total (for example a repository count plus Link
continuation, as the census does). Until then, a daily --apply run can act on a truncated list.
"""

import pytest

from scripts.upstream_watcher.live import GhError, LiveGh
from upstream_fakes import RestGhRunner


def open_rows(count):
    return [
        {"number": 1000 + index, "title": f"t{index}", "state": "open", "labels": [], "body": "",
         "updated_at": "2026-10-21T00:00:00Z"}
        for index in range(count)
    ]


@pytest.mark.xfail(strict=True, reason="defect: a short or empty page is trusted as the end of the list")
def test_an_empty_page_while_more_issues_exist_is_refused_not_returned_as_the_whole_list():
    # 150 open issues: page 1 is full (100), page 2 is answered empty although 50 more exist.
    runner = RestGhRunner(open_rows(150), empty_pages={("open", "", 2)})
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)

    with pytest.raises(GhError):
        gh.list_issues("open")


def test_the_reader_returns_every_issue_when_every_page_is_served():
    runner = RestGhRunner(open_rows(150))
    gh = LiveGh(repo="gaia-research/gaia-skill-tree", runner=runner)

    assert len(gh.list_issues("open")) == 150
