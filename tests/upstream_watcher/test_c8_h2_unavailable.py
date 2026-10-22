"""#2131 round-4 verifier FAIL, H2: one permanently unavailable upstream skips that suite, it does not zero the run.

Before this change every poll failure was unknown evidence, so a single HTTP 451 (blocked), 410 (gone) or a
403 that is not rate limiting stopped every suite, every run, forever.

The fix classifies per suite.
- Permanent (451, 410, and a repo-refusal 403) => the suite is SKIPPED with a
  ::notice::, listed under ``unavailable`` in the run report, and it neither blocks nor changes the exit code.
  Other suites proceed and write. A skipped suite has no finding, so it can never produce a removal or an
  approval change.
- Transient (5xx, 429, a rate-limited 403, a timeout, a network error, an unparseable body) keeps the M1
  rule: unknown evidence, exit 3, zero writes.
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.lib import github_api
from scripts.lib.github_api import GitHubFetchError, GitHubNotFound, fetch_json, is_permanent_unavailable, is_rate_limited
from scripts.upstream_watcher import batch, liveness, watcher
from scripts.upstream_watcher.batch import layout, new_report, run_batch
from scripts.upstream_watcher.live import SuiteUnavailable, UnknownEvidenceError
from scripts.upstream_watcher.liveness import fetch_component_diff
from upstream_fakes import FakeGh, index_from_entries

INDEX = index_from_entries([])

SUITE_A = {
    "id": "garrytan/gbrain",
    "level": "3★",
    "suiteComponents": ["garrytan/caveman"],
    "links": {"github": "https://github.com/garrytan/gbrain/blob/main/skills"},
    "upstream": {"version": "v1"},
}
SUITE_B = {
    "id": "mattpocock/skills",
    "level": "3★",
    "suiteComponents": ["mattpocock/caveman"],
    "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills"},
    "upstream": {"version": "v1.0.0"},
}
RATE_HEADERS = {"x-ratelimit-remaining": "0"}


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(github_api.time, "sleep", lambda _s: None)


def _http_error(code, headers=None, body=b""):
    return urllib.error.HTTPError(
        "https://api.github.com/repos/o/r/releases/latest", code, f"HTTP {code}", headers or {}, io.BytesIO(body)
    )


def _urlopen_raising(exc):
    def fake(req, timeout=None):  # noqa: ARG001
        raise exc

    return fake


def _poll_with(monkeypatch, exc):
    def fetch(endpoint, **kwargs):  # noqa: ARG001
        raise exc

    monkeypatch.setattr(watcher, "fetch_json", fetch)
    return watcher._poll_suite(SUITE_A, {}, verbose=False)


# ---------------------------------------------------------------------------
# lib: the strict GET keeps the status, the headers and the body, so the poll can classify the failure
# ---------------------------------------------------------------------------


def test_strict_fetch_keeps_the_rate_limit_headers_of_a_403():
    headers = {"X-RateLimit-Remaining": "0"}
    with patch.object(github_api.urllib.request, "urlopen", _urlopen_raising(_http_error(403, headers))):
        with pytest.raises(GitHubFetchError) as info:
            fetch_json("https://api.github.com/repos/o/r/releases/latest", strict=True)
    assert info.value.status == 403
    assert is_rate_limited(info.value) and not is_permanent_unavailable(info.value)


def test_strict_fetch_keeps_the_body_of_a_403_so_a_rate_limit_message_is_seen():
    body = b'{"message": "API rate limit exceeded for 1.2.3.4."}'
    with patch.object(github_api.urllib.request, "urlopen", _urlopen_raising(_http_error(403, body=body))):
        with pytest.raises(GitHubFetchError) as info:
            fetch_json("https://api.github.com/repos/o/r/releases/latest", strict=True)
    assert is_rate_limited(info.value)


def test_strict_fetch_451_is_a_permanent_unavailable():
    with patch.object(github_api.urllib.request, "urlopen", _urlopen_raising(_http_error(451))):
        with pytest.raises(GitHubFetchError) as info:
            fetch_json("https://api.github.com/repos/o/r/releases/latest", strict=True)
    assert info.value.status == 451
    assert is_permanent_unavailable(info.value) and not is_rate_limited(info.value)


# ---------------------------------------------------------------------------
# Classification: permanent statuses skip the suite, transient ones stay unknown evidence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        GitHubFetchError("HTTP 451 (fake blocked)", status=451),
        GitHubFetchError("HTTP 410 (fake gone)", status=410),
        GitHubFetchError("HTTP 403 (fake)", status=403, headers={}, body="Repository access blocked"),
    ],
)
def test_permanent_poll_errors_skip_the_suite(monkeypatch, exc):
    with pytest.raises(SuiteUnavailable):
        _poll_with(monkeypatch, exc)


@pytest.mark.parametrize(
    "exc",
    [
        GitHubFetchError("HTTP 500 (fake)", status=500),
        GitHubFetchError("HTTP 502 (fake)", status=502),
        GitHubFetchError("HTTP 429 (fake)", status=429),
        GitHubFetchError("HTTP 403 (fake forbidden)", status=403),  # C9 M-4: a bare 403 is not a repository refusal
        GitHubFetchError("HTTP 403 (fake)", status=403, headers=RATE_HEADERS),
        GitHubFetchError("HTTP 403 (fake)", status=403, headers={"Retry-After": "60"}),
        GitHubFetchError("HTTP 403 (fake)", status=403, body="API rate limit exceeded for 1.2.3.4"),
        GitHubFetchError("request failed: timed out", status=None),
        GitHubFetchError("unparseable JSON", status=None),
    ],
)
def test_transient_poll_errors_stay_unknown_evidence(monkeypatch, exc):
    with pytest.raises(UnknownEvidenceError):
        _poll_with(monkeypatch, exc)


def test_a_suite_unavailable_is_not_an_unknown_evidence_error():
    # main() must be able to tell the two apart, so the skip never reads as unknown evidence (or the reverse).
    assert not issubclass(SuiteUnavailable, UnknownEvidenceError)


def test_permanent_tree_error_skips_the_suite_too(monkeypatch):
    def gone(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubFetchError("HTTP 410 (fake tree gone)", status=410)

    monkeypatch.setattr(liveness, "fetch_json", gone)
    with pytest.raises(SuiteUnavailable):
        fetch_component_diff("garrytan", "gbrain", "v1", "skills", ["garrytan/caveman"])


def test_transient_tree_error_stays_unknown_evidence(monkeypatch):
    def broken(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubFetchError("HTTP 500 (fake)", status=500)

    monkeypatch.setattr(liveness, "fetch_json", broken)
    with pytest.raises(UnknownEvidenceError):
        fetch_component_diff("garrytan", "gbrain", "v1", "skills", ["garrytan/caveman"])


# ---------------------------------------------------------------------------
# The run: a permanent suite is listed as unavailable and skipped; the others proceed; exit is unaffected
# ---------------------------------------------------------------------------


def _main(monkeypatch, tmp_path, suites, fetch, run_batch_fn=None, poll=None, gh=None):
    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda root=None: iter([(Path("s.md"), fm) for fm in suites]))
    if fetch is not None:
        monkeypatch.setattr(watcher, "fetch_json", fetch)
    if poll is not None:
        monkeypatch.setattr(watcher, "_poll_suite", poll)
    if gh is not None:
        monkeypatch.setattr(watcher, "LiveGh", lambda *a, **k: gh)
    if run_batch_fn is not None:
        monkeypatch.setattr(watcher, "run_batch", run_batch_fn)
    report_path = tmp_path / "report.json"
    code = watcher.main(["--child-mode", "batch", "--apply", "--report", str(report_path)])
    return code, json.loads(report_path.read_text(encoding="utf-8"))


def test_permanent_suite_is_skipped_with_a_notice_and_listed_and_the_run_exits_0(monkeypatch, tmp_path, capsys):
    def fetch(endpoint, **kwargs):  # noqa: ARG001
        if "garrytan" in endpoint:
            raise GitHubFetchError("HTTP 451 (fake blocked)", status=451)
        raise GitHubNotFound("HTTP 404 (fake: no releases)", status=404)

    seen = []

    def fake_run_batch(findings, gh, apply, **kwargs):  # noqa: ARG001
        seen.append(findings)
        return new_report(), 0

    code, report = _main(monkeypatch, tmp_path, [SUITE_A, SUITE_B], fetch, run_batch_fn=fake_run_batch)
    assert code == 0
    assert seen == [[]], "the batch still runs, with no findings from the skipped suite"
    assert [row["suite"] for row in report["unavailable"]] == ["garrytan/gbrain"]
    assert report["unavailable"][0]["status"] == 451
    assert report["unknownEvidence"] == []
    assert "::notice::" in capsys.readouterr().err


def test_a_transient_error_on_one_suite_still_exits_3_with_zero_writes(monkeypatch, tmp_path):
    def fetch(endpoint, **kwargs):  # noqa: ARG001
        if "garrytan" in endpoint:
            raise GitHubFetchError("HTTP 451 (fake blocked)", status=451)
        raise GitHubFetchError("HTTP 502 (fake)", status=502)

    writes = []
    code, report = _main(monkeypatch, tmp_path, [SUITE_A, SUITE_B], fetch,
                         run_batch_fn=lambda *a, **k: writes.append(a) or (new_report(), 0))
    assert code == 3
    assert writes == []
    assert [row["suite"] for row in report["unknownEvidence"]] == ["mattpocock/skills"]
    assert [row["suite"] for row in report["unavailable"]] == ["garrytan/gbrain"]


def test_a_rate_limited_403_is_unknown_evidence_not_a_skip(monkeypatch, tmp_path):
    def fetch(endpoint, **kwargs):  # noqa: ARG001
        raise GitHubFetchError("HTTP 403 (fake)", status=403, headers=RATE_HEADERS)

    code, report = _main(monkeypatch, tmp_path, [SUITE_A], fetch)
    assert code == 3
    assert report["unavailable"] == []
    assert report["unknownEvidence"][0]["source"] == "github-poll"


def test_the_report_always_carries_an_unavailable_list(monkeypatch, tmp_path):
    code, report = _main(monkeypatch, tmp_path, [], None)
    assert code == 0
    assert report["unavailable"] == []


# ---------------------------------------------------------------------------
# A skipped suite never produces a removal or an approval change. The other suite still writes.
# ---------------------------------------------------------------------------


def _finding(skill, version, adds, source):
    return {
        "finding_type": "update",
        "skillId": skill,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T00:00:00Z",
        "sourceUrl": source,
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "linkLivenessUnknown": [],
        "nameDrift": [],
    }


A_SOURCE = "https://github.com/garrytan/gbrain/releases/tag/v1"
B_SOURCE = "https://github.com/mattpocock/skills/releases/tag/v1"


def test_a_skipped_suite_keeps_its_approved_umbrella_and_the_other_suite_still_writes(monkeypatch, tmp_path):
    gh = FakeGh()
    # Run 1 (both suites healthy) creates one umbrella per suite. A reviewer then approves A's umbrella.
    first = [_finding("garrytan/gbrain", "v1", ["ask-user"], A_SOURCE),
             _finding("mattpocock/skills", "v1", ["grill"], B_SOURCE)]
    batch.run_batch(first, gh, apply=True, index_loader=lambda: INDEX)
    a_number = next(n for n, row in gh.issues.items() if row["title"].startswith("[upstream] garrytan/gbrain"))
    gh.edit_labels(a_number, add=["upstream:approved"])
    a_before = dict(gh.issues[a_number])
    a_writes_before = [w for w in gh.writes if w[1] == a_number]

    # Run 2: A's release is permanently unavailable (skipped); B has a new release.
    def poll(fm, registry_map, verbose):  # noqa: ARG001
        if fm["id"] == "garrytan/gbrain":
            raise SuiteUnavailable("releases/latest for garrytan/gbrain is HTTP 451 (fake blocked)")
        return _finding("mattpocock/skills", "v2", ["grill", "tdd"], B_SOURCE.replace("v1", "v2"))

    def run_batch_fixed(findings, g, apply, **kwargs):  # noqa: ARG001
        return batch.run_batch(findings, g, apply=apply, index_loader=lambda: INDEX)

    code, report = _main(monkeypatch, tmp_path, [SUITE_A, SUITE_B], None, run_batch_fn=run_batch_fixed,
                         poll=poll, gh=gh)
    assert code == 0
    assert [row["suite"] for row in report["unavailable"]] == ["garrytan/gbrain"]
    a_after = gh.issues[a_number]
    assert a_after["labels"] == a_before["labels"], "the skipped suite's approval is untouched"
    assert a_after["body"] == a_before["body"]
    assert [w for w in gh.writes if w[1] == a_number] == a_writes_before, "no write touched the skipped suite"
    b_number = next(n for n, row in gh.issues.items() if row["title"].startswith("[upstream] mattpocock/skills"))
    assert any(w[1] == b_number for w in gh.writes[len(a_writes_before):]), "the healthy suite still writes"
