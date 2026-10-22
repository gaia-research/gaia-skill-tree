"""Regression tests for M1 and M2 (#2131 verifier FAIL): the watcher fails closed.

M1: a GitHub GET failure (403, 5xx, network, unparseable body) on the release or
    poll path is unknown evidence. The run exits 3 with ZERO writes; it never reads
    as "skipped, exit 0". Only a definitive HTTP 404 on /releases/latest means
    "no releases tagged" and is skipped.
M2: a component tree that cannot be read, or is truncated, is unknown evidence.
    It derives no componentRemoves and never silently becomes an empty or partial diff.
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.lib import github_api
from scripts.lib.github_api import GitHubFetchError, GitHubNotFound, fetch_json
from scripts.upstream_watcher import liveness, watcher
from scripts.upstream_watcher.batch import new_report
from scripts.upstream_watcher.live import UnknownEvidenceError
from scripts.upstream_watcher.liveness import fetch_component_diff

SUITE_FM = {
    "id": "mattpocock/skills",
    "level": "3★",
    "suiteComponents": ["mattpocock/caveman"],
    "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills"},
    "upstream": {"version": "v1.0.0"},
}


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.github.com/x", code, f"HTTP {code}", {}, io.BytesIO(b""))


def _urlopen_raising(exc: BaseException):
    def fake(req, timeout=None):  # noqa: ARG001
        raise exc

    return fake


# ---------------------------------------------------------------------------
# lib: fetch_json strict mode distinguishes 404 from every other failure
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(github_api.time, "sleep", lambda _s: None)


def test_strict_fetch_404_is_not_found_not_a_generic_error():
    with patch.object(github_api.urllib.request, "urlopen", _urlopen_raising(_http_error(404))):
        with pytest.raises(GitHubNotFound):
            fetch_json("https://api.github.com/repos/o/r/releases/latest", strict=True)


@pytest.mark.parametrize("code", [403, 429, 500, 502])
def test_strict_fetch_http_errors_raise_instead_of_returning_none(code):
    with patch.object(github_api.urllib.request, "urlopen", _urlopen_raising(_http_error(code))):
        with pytest.raises(GitHubFetchError) as info:
            fetch_json("https://api.github.com/repos/o/r/releases/latest", strict=True)
    assert not isinstance(info.value, GitHubNotFound)


def test_strict_fetch_network_error_raises():
    with patch.object(github_api.urllib.request, "urlopen", _urlopen_raising(OSError("reset"))):
        with pytest.raises(GitHubFetchError):
            fetch_json("https://api.github.com/repos/o/r/git/trees/v1", strict=True)


def test_strict_fetch_unparseable_body_raises():
    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    with patch.object(github_api.urllib.request, "urlopen", lambda req, timeout=None: Resp(b"<html>")):
        with pytest.raises(GitHubFetchError):
            fetch_json("https://api.github.com/x", strict=True)


def test_strict_fetch_does_not_cache_a_failure(monkeypatch):
    calls = {"n": 0}

    def flaky(req, timeout=None):  # noqa: ARG001
        calls["n"] += 1
        raise OSError("transient")

    monkeypatch.setattr(github_api.urllib.request, "urlopen", flaky)
    for _ in range(2):
        with pytest.raises(GitHubFetchError):
            fetch_json("https://api.github.com/repos/o/cache-probe", strict=True)
    assert calls["n"] == 2  # a cached None would have hidden the second attempt


def test_legacy_fetch_json_still_returns_none_for_callers_outside_the_watcher(monkeypatch):
    monkeypatch.setattr(github_api, "_CACHE", {})
    with patch.object(github_api.urllib.request, "urlopen", _urlopen_raising(_http_error(500))):
        assert fetch_json("https://api.github.com/repos/o/legacy") is None


# ---------------------------------------------------------------------------
# M1: the poll path
# ---------------------------------------------------------------------------


def test_poll_release_403_is_unknown_evidence_not_a_skip(monkeypatch):
    # #2131 round 4 (H2): a 403 that is rate limiting is transient, so it stays unknown evidence. A 403 with no
    # rate-limit signal is permanent and skips the suite (test_c8_h2_unavailable.py).
    def forbidden(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubFetchError("HTTP 403 for releases/latest", status=403, headers={"x-ratelimit-remaining": "0"})

    monkeypatch.setattr(watcher, "fetch_json", forbidden)
    with pytest.raises(UnknownEvidenceError, match="403"):
        watcher._poll_suite(SUITE_FM, {}, verbose=False)


def test_poll_release_404_means_no_releases_and_is_skipped(monkeypatch):
    def missing(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubNotFound("HTTP 404 for releases/latest", status=404)

    monkeypatch.setattr(watcher, "fetch_json", missing)
    assert watcher._poll_suite(SUITE_FM, {}, verbose=False) is None


def _run_main(monkeypatch, tmp_path, fetch, suites=None):
    """Run watcher.main() in dry-run over fake suites, with every write path made to fail the test."""
    suites = suites if suites is not None else [SUITE_FM]
    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda root=None: iter([(Path("s.md"), fm) for fm in suites]))
    monkeypatch.setattr(watcher, "fetch_json", fetch)
    writes = []

    def no_writes(*args, **kwargs):
        writes.append(args)
        raise AssertionError("a write was attempted on a run with unknown evidence")

    monkeypatch.setattr(watcher, "run_batch", no_writes)
    monkeypatch.setattr(watcher, "create_issues", no_writes)
    report_path = tmp_path / "report.json"
    code = watcher.main(["--child-mode", "batch", "--apply", "--report", str(report_path)])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return code, report, writes


def test_main_exits_3_with_zero_writes_when_a_release_poll_is_rate_limited(monkeypatch, tmp_path):
    def fetch(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubFetchError("HTTP 403 (fake rate limited)", status=403, headers={"x-ratelimit-remaining": "0"})

    code, report, writes = _run_main(monkeypatch, tmp_path, fetch)
    assert code == 3
    assert writes == []
    assert report["unknownEvidence"] and report["unknownEvidence"][0]["source"] == "github-poll"
    assert report["unknownEvidence"][0]["suite"] == "mattpocock/skills"


def test_one_failed_poll_blocks_writes_for_the_whole_run(monkeypatch, tmp_path):
    """A suite that polls cleanly must not be written while another suite's evidence is unknown."""
    other = {**SUITE_FM, "id": "garrytan/gbrain", "links": {"github": "https://github.com/garrytan/gbrain/blob/main/x"}}

    def fetch(endpoint, **kwargs):
        if "garrytan" in endpoint:
            raise GitHubFetchError("HTTP 502 (fake)", status=502)
        return {"tag_name": "v9", "published_at": "2026-10-21T00:00:00Z", "html_url": "u"}

    code, report, writes = _run_main(monkeypatch, tmp_path, fetch, suites=[SUITE_FM, other])
    assert code == 3
    assert writes == []


def test_main_treats_an_unexpected_poll_exception_as_unknown_not_skipped(monkeypatch, tmp_path):
    def fetch(endpoint, **kwargs):  # noqa: ARG001
        raise ValueError("surprise")

    code, report, writes = _run_main(monkeypatch, tmp_path, fetch)
    assert code == 3 and writes == []
    assert report["unknownEvidence"]


def test_main_exits_0_when_every_suite_has_no_releases(monkeypatch, tmp_path):
    def fetch(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubNotFound("HTTP 404 (fake)", status=404)

    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda root=None: iter([(Path("s.md"), SUITE_FM)]))
    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: (new_report(), 0))
    assert watcher.main(["--child-mode", "batch", "--apply"]) == 0


# ---------------------------------------------------------------------------
# M2: the component tree
# ---------------------------------------------------------------------------


def test_tree_fetch_error_is_unknown_evidence(monkeypatch):
    # H2: a rate-limited 403 on the tree is transient, so it stays unknown evidence (a plain 403 skips the suite).
    def broken(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubFetchError("HTTP 403 (fake)", status=403, headers={"x-ratelimit-remaining": "0"})

    monkeypatch.setattr(liveness, "fetch_json", broken)
    with pytest.raises(UnknownEvidenceError):
        fetch_component_diff("mattpocock", "skills", "v1.1.0", "skills", ["mattpocock/caveman"])


def test_tree_not_found_is_also_unknown_evidence(monkeypatch):
    """The tag was just returned by /releases/latest, so a 404 on its tree is not 'no components'."""

    def gone(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubNotFound("HTTP 404 (fake)", status=404)

    monkeypatch.setattr(liveness, "fetch_json", gone)
    with pytest.raises(UnknownEvidenceError):
        fetch_component_diff("mattpocock", "skills", "v1.1.0", "skills", ["mattpocock/caveman"])


def test_truncated_tree_is_unknown_evidence_not_a_partial_diff(monkeypatch):
    tree = {
        "truncated": True,
        "tree": [
            {"path": "skills", "type": "tree"},
            {"path": "skills/caveman/SKILL.md", "type": "blob"},
        ],
    }
    monkeypatch.setattr(liveness, "fetch_json", lambda endpoint, **kwargs: tree)
    with pytest.raises(UnknownEvidenceError, match="truncated"):
        fetch_component_diff("mattpocock", "skills", "v1.1.0", "skills", ["mattpocock/caveman", "mattpocock/gone"])


def test_missing_component_root_is_still_version_only_not_unknown(monkeypatch):
    """A repo with no skills/ directory is a legitimate version-only layout, not unknown evidence."""
    # A real tree response for a resolved tag carries the tree's sha (M3: an empty list needs it).
    resolved = {"sha": "9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c", "tree": [], "truncated": False}
    monkeypatch.setattr(liveness, "fetch_json", lambda endpoint, **kwargs: resolved)
    assert fetch_component_diff("o", "r", "v1", "skills", ["o/x"]) == ([], [])
