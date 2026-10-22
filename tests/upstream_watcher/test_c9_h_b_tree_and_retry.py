"""#2131 round-5 verifier FAIL, H-B: one truncated tree must not wedge every suite.

Before this change ``fetch_component_diff`` raised UnknownEvidenceError for ``truncated: true``. That made
``watcher.main`` return 3 before any write for ALL suites, every day, until upstream published a new tag.

Now:
- a truncated recursive tree is a per-suite condition. The component root is walked one directory at a time
  (GET git/trees/<sha>, no recursion), within a budget of 200 requests per suite. The diff equals the full
  recursive diff. If the budget runs out, or any sub-call still fails after its retries, the suite becomes
  ``unavailable: tree-truncated``: a notice, an entry in report.unavailable, no removals, other suites proceed.
- a transient failure (network, 5xx, 429, a rate-limited 403) is retried: 3 attempts, waits of 1s then 2s between
  them (the sleep is injectable). Only a failure that survives all three attempts is unknown evidence (exit 3).
- a permanent refusal (451, 410, or a repo-refusal 403) is never retried; it skips the suite.
"""

from __future__ import annotations

import json
from urllib.parse import unquote

import pytest

from scripts.lib.github_api import GitHubFetchError, GitHubNotFound
from scripts.upstream_watcher import live, liveness, watcher
from scripts.upstream_watcher.live import SuiteUnavailable, UnknownEvidenceError
from scripts.upstream_watcher.liveness import fetch_component_diff

REPO_API = "https://api.github.com/repos/o/r"
TREE_BUDGET = 200


class FakeTree:
    """A git-trees stand-in for one tag of ``o/r``.

    A recursive request is answered with a truncated listing (truncated=True, the first items only) unless
    ``truncated`` is False. A per-directory request is always complete, as GitHub's non-recursive listing is.
    """

    def __init__(self, files, truncated=True, tag="v1"):
        self.tag = tag
        self.truncated = truncated
        self.entries: dict[str, dict[str, str]] = {"": {}}
        for path in files:
            parts = path.split("/")
            for depth, name in enumerate(parts):
                parent = "/".join(parts[:depth])
                kind = "blob" if depth == len(parts) - 1 else "tree"
                self.entries.setdefault(parent, {})[name] = kind
                if kind == "tree":
                    self.entries.setdefault("/".join(parts[: depth + 1]), {})
        self.files = list(files)
        self.calls: list[str] = []

    @staticmethod
    def sha_of(path):
        return f"sha:{path}"

    def listing(self, path):
        items = []
        for name, kind in sorted(self.entries[path].items()):
            child = f"{path}/{name}" if path else name
            if kind == "tree":
                items.append({"path": name, "type": "tree", "sha": self.sha_of(child)})
            else:
                items.append({"path": name, "type": "blob", "sha": f"blob:{child}"})
        return items

    def full_recursive(self):
        items = []
        for path in sorted(self.entries):
            if path:
                items.append({"path": path, "type": "tree", "sha": self.sha_of(path)})
        items += [{"path": path, "type": "blob", "sha": "b"} for path in self.files]
        return items

    def fetch(self, url, **kwargs):
        self.calls.append(url)
        if "?recursive=1" in url:
            items = self.full_recursive()
            if self.truncated:
                return {"sha": "root", "tree": items[:2], "truncated": True}
            return {"sha": "root", "tree": items, "truncated": False}
        ref = unquote(url.split("/git/trees/", 1)[1])
        path = "" if ref == self.tag else ref[len("sha:"):]
        if path not in self.entries:
            raise GitHubNotFound(f"GitHub API HTTP 404 for {url}", status=404)
        return {"sha": ref, "tree": self.listing(path), "truncated": False}

    def non_recursive_calls(self):
        return [url for url in self.calls if "?recursive=1" not in url]


def slugs_files(count):
    return [f"skills/s{number:03d}/SKILL.md" for number in range(count)]


FILES = [
    "skills/eng/alpha/SKILL.md",
    "skills/eng/alpha/refs/notes.md",
    "skills/beta/SKILL.md",
    "skills/deprecated/old/README.md",
    "skills/gamma/SKILL.md",
    "skills/SKILL.md",
    "README.md",
]
CURRENT = ["x/alpha", "x/beta", "x/gone"]


def diff(monkeypatch, tree, current=CURRENT):
    monkeypatch.setattr(liveness, "fetch_json", tree.fetch)
    return fetch_component_diff("o", "r", "v1", "skills", current)


# ---------------------------------------------------------------------------
# Truncated tree: the directory walk
# ---------------------------------------------------------------------------


def test_a_truncated_tree_falls_back_to_a_directory_walk_and_gives_the_full_diff(monkeypatch):
    tree = FakeTree(FILES, truncated=True)
    adds, removes = diff(monkeypatch, tree)
    assert (adds, removes) == (["gamma"], ["gone"])
    full = FakeTree(FILES, truncated=False)
    assert diff(monkeypatch, full) == (adds, removes), "the walk and the recursive read agree"


def test_the_walk_asks_per_directory_and_never_recurses_again(monkeypatch):
    tree = FakeTree(FILES, truncated=True)
    diff(monkeypatch, tree)
    recursive = [url for url in tree.calls if "?recursive=1" in url]
    assert len(recursive) == 1
    assert all("recursive" not in url for url in tree.non_recursive_calls())
    assert len(tree.non_recursive_calls()) <= TREE_BUDGET


@pytest.mark.parametrize("count", [1, 60, 150])
def test_a_truncated_tree_within_the_budget_is_walked_completely(monkeypatch, count):
    files = slugs_files(count)
    tree = FakeTree(files, truncated=True)
    adds, removes = diff(monkeypatch, tree, current=["x/s000"])
    assert removes == []
    assert adds == sorted(f"s{number:03d}" for number in range(1, count))
    assert len(tree.non_recursive_calls()) <= TREE_BUDGET


def test_exhausting_the_budget_makes_the_suite_unavailable_not_unknown(monkeypatch):
    # 1 request for the tag, 1 for skills/, then one per slug directory: 252 > 200.
    tree = FakeTree(slugs_files(250), truncated=True)
    monkeypatch.setattr(liveness, "fetch_json", tree.fetch)
    with pytest.raises(SuiteUnavailable) as info:
        fetch_component_diff("o", "r", "v1", "skills", ["x/s000"])
    assert info.value.reason == "tree-truncated"
    assert "budget" in str(info.value)
    assert len(tree.non_recursive_calls()) <= TREE_BUDGET, "the walk stops at the budget"


def test_a_failed_subcall_after_its_retries_makes_the_suite_unavailable(monkeypatch):
    tree = FakeTree(FILES, truncated=True)
    sleeps: list[float] = []
    monkeypatch.setattr(live, "RETRY_SLEEP", sleeps.append)

    def flaky(url, **kwargs):
        if unquote(url).endswith("sha:skills/beta"):
            raise GitHubFetchError("HTTP 500 (fake)", status=500)
        return tree.fetch(url, **kwargs)

    monkeypatch.setattr(liveness, "fetch_json", flaky)
    with pytest.raises(SuiteUnavailable) as info:
        fetch_component_diff("o", "r", "v1", "skills", CURRENT)
    assert info.value.reason == "tree-truncated"
    assert sleeps == [1, 2], "the failing sub-call was retried twice before the suite was skipped"


def test_a_missing_subdirectory_during_the_walk_is_unavailable_not_a_partial_diff(monkeypatch):
    tree = FakeTree(FILES, truncated=True)

    def gone(url, **kwargs):
        if unquote(url).endswith("sha:skills/eng"):
            raise GitHubNotFound("HTTP 404 (fake)", status=404)
        return tree.fetch(url, **kwargs)

    monkeypatch.setattr(liveness, "fetch_json", gone)
    with pytest.raises(SuiteUnavailable) as info:
        fetch_component_diff("o", "r", "v1", "skills", CURRENT)
    assert info.value.reason == "tree-truncated"


def test_a_truncated_tree_whose_root_is_absent_is_still_version_only(monkeypatch):
    tree = FakeTree(["docs/SKILL.md"], truncated=True)
    assert diff(monkeypatch, tree, current=["x/alpha"]) == ([], [])


# ---------------------------------------------------------------------------
# Transient failures are retried; only what survives the retries is unknown evidence
# ---------------------------------------------------------------------------


def scripted(responses):
    queue = list(responses)
    calls: list[str] = []

    def fetch(url, **kwargs):
        calls.append(url)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return fetch, calls


RESOLVED = {"sha": "9f1c2d3e", "tree": [{"path": "skills", "type": "tree", "sha": "s"}, {"path": "skills/alpha/SKILL.md", "type": "blob"}], "truncated": False}


def test_a_transient_tree_error_is_retried_then_succeeds(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(live, "RETRY_SLEEP", sleeps.append)
    fetch, calls = scripted([GitHubFetchError("HTTP 502", status=502), GitHubFetchError("timed out", status=None), RESOLVED])
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    assert fetch_component_diff("o", "r", "v1", "skills", ["x/alpha"]) == ([], [])
    assert len(calls) == 3
    assert sleeps == [1, 2]


def test_a_transient_error_surviving_three_attempts_is_unknown_evidence(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(live, "RETRY_SLEEP", sleeps.append)
    fetch, calls = scripted([GitHubFetchError("HTTP 503", status=503)] * 3)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    with pytest.raises(UnknownEvidenceError):
        fetch_component_diff("o", "r", "v1", "skills", ["x/alpha"])
    assert len(calls) == 3
    assert sleeps == [1, 2]


def test_a_permanent_refusal_is_not_retried(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(live, "RETRY_SLEEP", sleeps.append)
    fetch, calls = scripted([GitHubFetchError("HTTP 451 (fake)", status=451)])
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    with pytest.raises(SuiteUnavailable):
        fetch_component_diff("o", "r", "v1", "skills", ["x/alpha"])
    assert len(calls) == 1 and sleeps == []


def test_a_rate_limited_403_is_retried_as_transient(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(live, "RETRY_SLEEP", sleeps.append)
    limited = GitHubFetchError("HTTP 403 (fake)", status=403, headers={"x-ratelimit-remaining": "0"})
    fetch, calls = scripted([limited, RESOLVED])
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    assert fetch_component_diff("o", "r", "v1", "skills", ["x/alpha"]) == ([], [])
    assert len(calls) == 2 and sleeps == [1]


def test_the_release_read_is_retried_too(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(live, "RETRY_SLEEP", sleeps.append)
    fm = {"id": "o/r", "level": "3★", "suiteComponents": ["o/alpha"], "links": {"github": "https://github.com/o/r/blob/main/skills"}, "upstream": {"version": "v0"}}
    fetch, calls = scripted([GitHubFetchError("HTTP 502", status=502), {"tag_name": "v1", "published_at": "t", "html_url": "u"}, RESOLVED])
    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    finding = watcher._poll_suite(fm, {}, verbose=False)
    assert finding is not None and finding["newVersion"] == "v1"
    assert sleeps == [1]


# ---------------------------------------------------------------------------
# Watcher level: one unavailable suite does not block the run
# ---------------------------------------------------------------------------


def suite_fm(skill, version):
    return {
        "id": skill,
        "level": "3★",
        "suiteComponents": [f"{skill.split('/')[0]}/s000"],
        "links": {"github": f"https://github.com/{skill}/blob/main/skills"},
        "upstream": {"version": version},
    }


def route(big_tree, healthy_suite_tag):
    def fetch(url, **kwargs):
        if "/repos/o/small/releases/latest" in url:
            return {"tag_name": healthy_suite_tag, "published_at": "t", "html_url": "u"}
        if "/repos/o/big/releases/latest" in url:
            return {"tag_name": "v1", "published_at": "t", "html_url": "u"}
        if "/repos/o/small/" in url:
            raise AssertionError("an up-to-date suite must not read a tree")
        return big_tree.fetch(url, **kwargs)

    return fetch


def test_a_truncated_suite_is_skipped_and_the_other_suites_proceed(tmp_path, monkeypatch, capsys):
    big = FakeTree(slugs_files(250), truncated=True)
    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda root=None: iter([
        (None, suite_fm("o/big", "v0")),
        (None, suite_fm("o/small", "v1")),
    ]))
    fetch = route(big, healthy_suite_tag="v1")
    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    report_path = tmp_path / "report.json"
    code = watcher.main(["--report", str(report_path)])
    assert code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknownEvidence"] == []
    assert [row["suite"] for row in report["unavailable"]] == ["o/big"]
    assert report["unavailable"][0]["reason"] == "tree-truncated"
    assert "::notice::o/big skipped" in capsys.readouterr().err


def test_a_transient_failure_that_outlasts_its_retries_still_exits_3_with_zero_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda root=None: iter([(None, suite_fm("o/big", "v0"))]))

    def down(url, **kwargs):
        raise GitHubFetchError("HTTP 503 (fake outage)", status=503)

    monkeypatch.setattr(watcher, "fetch_json", down)
    report_path = tmp_path / "report.json"
    code = watcher.main(["--apply", "--report", str(report_path)])
    assert code == 3
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknownEvidence"][0]["source"] == "github-poll"
    assert report["issuesCreated"] == 0 and report["issuesUpdated"] == 0
