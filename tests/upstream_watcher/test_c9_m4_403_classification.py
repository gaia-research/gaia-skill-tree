"""#2131 round-5 verifier MEDIUM, M-4: a 403 is permanent only when the repository itself refuses.

Before this change every 403 without a rate-limit signal skipped the suite for good, so a token or App
permission problem ("Resource not accessible by integration") silently removed a suite from every run.

Now only 451, 410, and a repo-specific 403 (a DMCA, blocked or disabled repository message) are permanent and skip
the suite. A 403 that names a permission problem, and a bare 403, are not permanent: they are a visible hard error
(unknown evidence, exit 3). The message names the permission problem, and nothing is retried.
"""

from __future__ import annotations

import json

import pytest

from scripts.lib.github_api import GitHubFetchError, is_permanent_unavailable
from scripts.upstream_watcher import live, liveness, watcher
from scripts.upstream_watcher.live import SuiteUnavailable, UnknownEvidenceError
from scripts.upstream_watcher.liveness import fetch_component_diff

PERMISSION_BODY = json.dumps({"message": "Resource not accessible by integration", "status": "403"})
FM = {
    "id": "o/r",
    "level": "3★",
    "suiteComponents": ["o/alpha"],
    "links": {"github": "https://github.com/o/r/blob/main/skills"},
    "upstream": {"version": "v0"},
}


@pytest.mark.parametrize(
    "exc",
    [
        GitHubFetchError("HTTP 451 (fake blocked)", status=451),
        GitHubFetchError("HTTP 410 (fake gone)", status=410),
        GitHubFetchError("HTTP 403 (fake)", status=403, body="Repository access blocked"),
        GitHubFetchError("HTTP 403 (fake)", status=403, body='{"message": "Repository was disabled by DMCA takedown"}'),
    ],
)
def test_only_451_410_and_a_repo_refusal_403_are_permanent(exc):
    assert is_permanent_unavailable(exc) is True


@pytest.mark.parametrize(
    "exc",
    [
        GitHubFetchError("HTTP 403 (fake)", status=403, body=PERMISSION_BODY),
        GitHubFetchError("HTTP 403 (fake)", status=403),  # a bare 403 says nothing about the repository
        GitHubFetchError("HTTP 403 (fake)", status=403, body="Must have admin rights to Repository."),
        GitHubFetchError("HTTP 403 (fake)", status=403, headers={"x-ratelimit-remaining": "0"}, body="rate limit"),
    ],
)
def test_a_permission_or_bare_403_is_not_permanent(exc):
    assert is_permanent_unavailable(exc) is False


def test_the_release_read_with_a_permission_403_is_a_visible_hard_error_naming_the_permission(monkeypatch):
    def denied(url, **kwargs):
        raise GitHubFetchError("GitHub API HTTP 403 for releases/latest", status=403, body=PERMISSION_BODY)

    monkeypatch.setattr(watcher, "fetch_json", denied)
    with pytest.raises(UnknownEvidenceError) as info:
        watcher._poll_suite(FM, {}, verbose=False)
    assert not isinstance(info.value, SuiteUnavailable)
    text = str(info.value)
    assert "Resource not accessible by integration" in text
    assert "permission" in text.lower()


def test_the_tree_read_with_a_permission_403_is_unknown_evidence_naming_the_permission(monkeypatch):
    def denied(url, **kwargs):
        raise GitHubFetchError("GitHub API HTTP 403 for trees", status=403, body=PERMISSION_BODY)

    monkeypatch.setattr(liveness, "fetch_json", denied)
    with pytest.raises(UnknownEvidenceError) as info:
        fetch_component_diff("o", "r", "v1", "skills", ["o/alpha"])
    assert "Resource not accessible by integration" in str(info.value)


def test_a_permission_403_is_not_retried(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(live, "RETRY_SLEEP", sleeps.append)
    calls: list[str] = []

    def denied(url, **kwargs):
        calls.append(url)
        raise GitHubFetchError("HTTP 403", status=403, body=PERMISSION_BODY)

    monkeypatch.setattr(watcher, "fetch_json", denied)
    with pytest.raises(UnknownEvidenceError):
        watcher._poll_suite(FM, {}, verbose=False)
    assert len(calls) == 1 and sleeps == []


def test_a_bare_403_on_the_release_read_is_unknown_evidence_not_a_skip(monkeypatch):
    def bare(url, **kwargs):
        raise GitHubFetchError("HTTP 403 (fake)", status=403)

    monkeypatch.setattr(watcher, "fetch_json", bare)
    with pytest.raises(UnknownEvidenceError):
        watcher._poll_suite(FM, {}, verbose=False)


def test_a_repo_refusal_403_still_skips_the_suite(monkeypatch):
    def blocked(url, **kwargs):
        raise GitHubFetchError("HTTP 403 (fake)", status=403, body="Repository access blocked")

    monkeypatch.setattr(watcher, "fetch_json", blocked)
    with pytest.raises(SuiteUnavailable):
        watcher._poll_suite(FM, {}, verbose=False)
