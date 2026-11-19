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


def test_normal_batch_dry_run_accepts_mixed_inventory_without_issue_writes(monkeypatch, tmp_path, capsys):
    from scripts.lib import named_iterator
    from scripts.upstream_watcher import watcher
    from scripts.upstream_watcher.batch import plan_suite
    from scripts.upstream_watcher import envelope
    import socket
    import urllib.request

    # Configure a real on-disk named registry, not a replacement iterator/index.
    named = tmp_path / "named"
    named.mkdir()
    (named / "suite.md").write_text(
        '---\nid: garrytan/gbrain\nname: Gbrain\nlevel: "2★"\n'
        'suiteComponents: [garrytan/component]\n'
        'links:\n  github: https://github.com/garrytan/gbrain\n'
        'upstream:\n  repo: garrytan/gbrain\n  version: v0\n---\n', encoding="utf-8")
    # A pending bootstrap is an explicit per-named envelope finding, not a
    # separate single-ID writer. Its planned create must remain in the metrics.
    (named / "pending.md").write_text(
        '---\nid: garrytan/pending\nname: Pending\nlevel: "2★"\n'
        'suiteComponents: [garrytan/component]\n'
        'links:\n  github: https://github.com/garrytan/pending\n---\n', encoding="utf-8")
    monkeypatch.setattr(named_iterator, "_DEFAULT_NAMED_DIR", named)

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected network/transport")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    release_reads = []

    def release_response(url, **kwargs):
        repo = url.removeprefix("https://api.github.com/repos/").removesuffix("/releases/latest")
        assert repo in ("garrytan/gbrain", "garrytan/pending")
        assert url == f"https://api.github.com/repos/{repo}/releases/latest"
        assert kwargs == {"strict": True}
        release_reads.append(url)
        return {"tag_name": "v1", "published_at": "2026-10-21T10:00:00Z",
                "html_url": f"https://github.com/{repo}/releases/tag/v1"}

    monkeypatch.setattr(watcher, "fetch_json", release_response)
    # A real update finding (v0 -> v1), already represented by an open umbrella:
    # plan it as noop, not an empty-registry/zero-findings pass. Report metrics
    # count *planned* creates/updates too, so fresh work would not report zero.
    fm = watcher._build_registry_map()["garrytan/gbrain"]
    finding = watcher._poll_suite(fm, watcher._build_registry_map(), False)
    plan = plan_suite(finding, {"issues": [], "closedUmbrellas": []}, {})
    rows = mixedRows()
    native = envelope.build("garrytan/gbrain", [plan["payload"]], watcher._build_registry_map())
    rows[0].update(title=envelope.title(native), body=envelope.render(native), labels=[{"name": "upstream:release"}])
    # This PR masquerades as an unfinished release umbrella. If read_live fails
    # to exclude it, it becomes a duplicate/identity candidate in the real plan.
    rows[-1].update(title=plan["title"], body="", labels=[{"name": "upstream:release"}])
    runner = ConnectionRunner(rows, open_count=226)
    mutations = []

    def transport(args, **kwargs):
        assert args[:2] == ["gh", "api"] or args[1:3] in (
            ["issue", "create"], ["issue", "edit"], ["issue", "comment"])
        query = next((arg for arg in args if arg.startswith("query=")), "")
        method_flag = next((flag for flag in ("--method", "-X") if flag in args), None)
        method = args[args.index(method_flag) + 1] if method_flag else "GET"
        graphql_read = args[2] == "graphql" and query.removeprefix("query=").lstrip().startswith("query")
        has_fields = any(flag in args for flag in ("-f", "-F", "--field", "--raw-field", "--input"))
        if args[1] != "api" or "mutation" in query.lower() or (
                (method != "GET" or has_fields) and not graphql_read):
            mutations.append(args)
            raise AssertionError("dry-run attempted a mutation")
        return runner(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", transport)
    # Undo only conftest's default fake constructor; retain the real LiveGh,
    # pagination/count guard, read_live PR filtering, planner and dry-run logic.
    monkeypatch.setattr(watcher, "LiveGh", LiveGh)
    report_path = tmp_path / "report.json"
    assert watcher.main(["--child-mode", "batch", "--dry-run", "--verbose", "--report", str(report_path)]) == 0
    report = json.loads(report_path.read_text())
    assert report["dryRun"] is True
    assert report["unknownEvidence"] == []
    assert (report["issuesCreated"], report["issuesUpdated"]) == (1, 0)
    assert len(report["suites"]) == 2
    suite = next(row for row in report["suites"] if row["skillId"] == "garrytan/gbrain")
    assert (suite["suite"], suite["umbrella"], suite["outcome"]) == (
        "garrytan/gbrain", rows[0]["number"], "noop")
    assert report["duplicateOpenUmbrellas"] == []
    output = capsys.readouterr()
    assert "2 finding(s)" in output.err
    assert "garrytan/pending" in output.out and "Bootstrap" in output.out
    pending = next(p for p in report["repositories"] if p["repository"] == "garrytan/pending")
    assert pending["payload"]["findings"][0]["findingType"] == "bootstrap"
    assert pending["outcome"] == "planned"
    assert len(release_reads) == 3  # fixture preparation + two real normal polls
    assert runner.graphql == 2  # exact typed (218 issues, 5 PRs) before/after the shared complete inventory
    assert mutations == runner.writes == []


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
