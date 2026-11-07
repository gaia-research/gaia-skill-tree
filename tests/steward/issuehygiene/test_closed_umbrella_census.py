"""Founder ruling #6 (lead ruling on the 30-day window): the census reads closed umbrellas by label, with no window.

One bounded, label-scoped listing per umbrella label, beside the windowed ``recentlyClosed`` rows. A failure marks only
that section incomplete: the census itself stays complete, and the reconciler reports only the umbrella-dependent
decisions as not evaluated. No persistent store is added.
"""

from __future__ import annotations

from gaia_cli.steward.issuehygiene.census import COMPLETE, UMBRELLA_LABELS, closedUmbrellaHistory, validateCensus
from scripts.steward_issue_census import FetchError, Response, collectCensus, labelFilter, sameListing
from tests.steward.issuehygiene.e_fakes import NOW, FakeGitHub

OLD = "2026-05-01T12:00:00Z"  # far outside the 30-day window before NOW


def repoWithOldUmbrella() -> tuple[FakeGitHub, int]:
    gh = FakeGitHub(pageSize=2)
    old = gh.add("[upstream] obra/superpowers → v7.0.0", labels=("upstream:release",), state="closed",
                 stateReason="completed", updatedAt=OLD)
    gh.add("[upstream:bootstrap] a/b → baseline at v1", labels=("upstream:bootstrap",), state="closed", updatedAt=OLD)
    gh.add("[intake] unrelated closed issue", labels=("intake",), state="closed", updatedAt=OLD)
    gh.add("an open issue")
    return gh, old


def test_an_older_closed_umbrella_is_in_the_history_but_not_the_window() -> None:
    gh, old = repoWithOldUmbrella()

    document = gh.census(NOW)

    assert document["recentlyClosed"] == []
    section = document["closedUmbrellas"]
    assert section["complete"] is True and section["labels"] == list(UMBRELLA_LABELS)
    assert {row["number"] for row in section["items"]} >= {old}
    assert len(section["items"]) == 2  # both umbrella labels, and not the unrelated closed issue
    assert all(row["state"] == "closed" and set(row["labels"]) & set(UMBRELLA_LABELS) for row in section["items"])
    assert validateCensus(document, NOW, 21600).status == COMPLETE
    rows, reasons = closedUmbrellaHistory(document)
    assert reasons == () and {row["number"] for row in rows} == {row["number"] for row in section["items"]}


def test_the_history_is_one_label_scoped_listing_per_umbrella_label_with_no_window() -> None:
    gh, _ = repoWithOldUmbrella()
    urls: list[str] = []

    def fetch(url: str) -> Response:
        urls.append(url)
        return gh.fetch(url)

    collectCensus(gh.repo, NOW, fetch, 30)

    labelled = [url for url in urls if "labels=" in url]
    assert labelled and all("since=" not in url for url in labelled)
    assert {labelFilter(url)[0] for url in labelled} == set(UMBRELLA_LABELS)
    assert all("state=closed" in url for url in labelled)


def test_a_failed_label_query_marks_only_the_history_incomplete() -> None:
    gh, _ = repoWithOldUmbrella()

    def fetch(url: str) -> Response:
        if "labels=" in url and "bootstrap" in url:
            raise FetchError("rate-limited")
        return gh.fetch(url)

    document = collectCensus(gh.repo, NOW, fetch, 30)

    assert document["completeness"]["issues"]["complete"] is True  # the census itself is unaffected
    assert validateCensus(document, NOW, 21600).status == COMPLETE
    assert document["closedUmbrellas"]["complete"] is False and document["closedUmbrellas"]["items"] == []
    assert "upstream:bootstrap" in document["closedUmbrellas"]["reason"]
    rows, reasons = closedUmbrellaHistory(document)
    assert rows is None and reasons[0].startswith("closed-umbrella-history-incomplete:")


def test_a_skipped_open_listing_does_not_pretend_the_history_was_read() -> None:
    gh, _ = repoWithOldUmbrella()
    gh.pageFailures[("open", 1)] = 500

    document = gh.census(NOW)

    assert document["completeness"]["issues"]["complete"] is False
    assert document["closedUmbrellas"]["complete"] is False


def test_history_rows_must_match_their_digests_and_labels() -> None:
    gh, _ = repoWithOldUmbrella()
    document = gh.census(NOW)
    document["closedUmbrellas"]["items"][0]["body"] = "tampered"

    rows, reasons = closedUmbrellaHistory(document)

    assert rows is None and reasons[0].startswith("closed-umbrella-history-body-mismatch")


def test_a_next_link_with_another_label_filter_is_foreign() -> None:
    start = "https://api.github.com/repos/o/r/issues?state=closed&per_page=100&labels=upstream%3Arelease"
    same = "https://api.github.com/repos/o/r/issues?state=closed&per_page=100&labels=upstream%3Arelease&page=2"
    other = "https://api.github.com/repos/o/r/issues?state=closed&per_page=100&labels=upstream%3Abootstrap&page=2"
    unlabelled = "https://api.github.com/repos/o/r/issues?state=closed&per_page=100&page=2"
    paths = {"/repos/o/r/issues"}

    assert sameListing(same, start, paths)
    assert not sameListing(other, start, paths)
    assert not sameListing(unlabelled, start, paths)
