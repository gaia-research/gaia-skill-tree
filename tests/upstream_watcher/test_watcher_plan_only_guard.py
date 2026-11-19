"""Offline CLI routing proofs for the plan-only watcher guard.

Exercises real ``watcher.main`` routing with ``LiveGh`` and read-only fake
``subprocess.run`` transport (zero mutating calls, zero network).
"""
import copy
import json
import socket
import subprocess
import urllib.request

import pytest

from scripts.lib import named_iterator
from scripts.upstream_watcher import repository_batch as rb
from scripts.upstream_watcher import watcher
from scripts.upstream_watcher.live import LiveGh
from test_count_2278 import ConnectionRunner, mixedRows
from upstream_fakes import FakeGh


def _setup_cli_world(monkeypatch, tmp_path, *, rows=None, counts=None, fail_release=False):
    named = tmp_path / "named"
    named.mkdir(parents=True, exist_ok=True)
    (named / "suite.md").write_text(
        '---\nid: garrytan/gbrain\nname: Gbrain\nlevel: "2★"\n'
        'suiteComponents: [garrytan/component]\n'
        'links:\n  github: https://github.com/garrytan/gbrain\n'
        'upstream:\n  repo: garrytan/gbrain\n  version: v0\n---\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(named_iterator, "_DEFAULT_NAMED_DIR", named)

    def forbidden(*args, **kwargs):
        raise AssertionError("offline guard test attempted network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)

    def release(url, **kwargs):
        if fail_release:
            from scripts.lib.github_api import GitHubFetchError
            raise GitHubFetchError("synthetic release read failure", status=503)
        assert url == "https://api.github.com/repos/garrytan/gbrain/releases/latest"
        assert kwargs == {"strict": True}
        return {
            "tag_name": "v1",
            "published_at": "2026-11-20T00:00:00Z",
            "html_url": "https://github.com/garrytan/gbrain/releases/tag/v1",
        }

    monkeypatch.setattr(watcher, "fetch_json", release)

    issue_rows = mixedRows() if rows is None else rows
    runner = ConnectionRunner(issue_rows, counts=counts, open_count=226)
    mutations = []

    def transport(args, **kwargs):
        query = next((arg for arg in args if arg.startswith("query=")), "")
        method_flag = next((flag for flag in ("--method", "-X") if flag in args), None)
        method = args[args.index(method_flag) + 1] if method_flag else "GET"
        graphql_read = len(args) > 2 and args[2] == "graphql" and query.removeprefix("query=").lstrip().startswith("query")
        has_fields = any(flag in args for flag in ("-f", "-F", "--field", "--raw-field", "--input"))
        if args[:2] != ["gh", "api"] or "mutation" in query.lower() or (
            (method != "GET" or has_fields) and not graphql_read
        ):
            mutations.append(args)
            raise AssertionError(f"plan-only watcher attempted mutating transport: {args}")
        return runner(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", transport)
    monkeypatch.setattr(watcher, "LiveGh", LiveGh)
    return runner, mutations


def test_native_unstaged_batch_apply_is_fenced_plan_only_exit_4(monkeypatch, tmp_path):
    runner, mutations = _setup_cli_world(monkeypatch, tmp_path)
    report_path = tmp_path / "report.json"

    code = watcher.main(["--child-mode", "batch", "--apply", "--report", str(report_path)])

    assert code == 4
    assert mutations == [] and runner.writes == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["dryRun"] is False
    assert report["writeReadiness"] is False
    assert report["executionHold"] == "watcher-plan-only-guard-blocks-envelope-apply"
    assert report["unknownEvidence"] == []
    assert report["actualIssuesCreated"] == 0 and report["actualIssuesUpdated"] == 0
    assert report["issuesCreated"] == 1
    assert report["repositories"][0]["outcome"] == "held"


def test_native_unstaged_batch_dry_run_retains_normal_planning(monkeypatch, tmp_path):
    runner, mutations = _setup_cli_world(monkeypatch, tmp_path)
    report_path = tmp_path / "report.json"

    code = watcher.main(["--child-mode", "batch", "--dry-run", "--report", str(report_path)])

    assert code == 0
    assert mutations == [] and runner.writes == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["dryRun"] is True
    assert report["writeReadiness"] is False
    assert report["executionHold"] == "watcher-plan-only-guard-blocks-envelope-apply"
    assert report["unknownEvidence"] == []
    assert report["issuesCreated"] == 1
    assert report["actualIssuesCreated"] == 0 and report["actualIssuesUpdated"] == 0
    assert report["repositories"][0]["outcome"] == "planned"
    assert report["repositories"][0]["writeReadiness"] is False
    assert report["repositories"][0]["executionHold"] == "watcher-plan-only-guard-blocks-envelope-apply"


@pytest.mark.parametrize("extra_args", [
    ["--child-mode", "fanout", "--apply"],
    ["--child-mode", "batch", "--staging", "weekly", "--staging-bootstrap", "--apply"],
    ["--child-mode", "batch", "--reset-records", "garrytan/gbrain", "--apply"],
])
def test_all_held_envelope_apply_routes_exit_4_with_zero_mutators(monkeypatch, tmp_path, extra_args):
    runner, mutations = _setup_cli_world(monkeypatch, tmp_path)
    report_path = tmp_path / "report.json"
    if "--staging" in extra_args:
        monkeypatch.setenv("STEWARD_ISSUE_HYGIENE_V2", "true")
        extra_args = [*extra_args, "--staging-journal", str(tmp_path / "journal.json")]

    code = watcher.main([*extra_args, "--report", str(report_path)])

    assert code == 4
    assert mutations == [] and runner.writes == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["writeReadiness"] is False
    assert report["executionHold"]
    assert report["actualIssuesCreated"] == 0 and report["actualIssuesUpdated"] == 0


def test_escalate_apply_stays_read_only_exit_3(monkeypatch, tmp_path, capsys):
    runner, mutations = _setup_cli_world(monkeypatch, tmp_path)

    code = watcher.main(["--escalate", "garrytan/gbrain:ask-user", "--apply"])

    assert code == 3
    assert mutations == [] and runner.writes == []
    out = json.loads(capsys.readouterr().out)
    assert out["outcome"] == "unknown" and out["writeReadiness"] is False


def test_rejection_and_unknown_precedence_over_exit_4_hold(monkeypatch, tmp_path):
    # 1. Missing STEWARD_ISSUE_HYGIENE_V2 gate rejects with exit 1 before polling/hold.
    monkeypatch.delenv("STEWARD_ISSUE_HYGIENE_V2", raising=False)
    _setup_cli_world(monkeypatch, tmp_path)
    assert watcher.main([
        "--child-mode", "batch", "--staging", "weekly",
        "--staging-journal", str(tmp_path / "journal.json"), "--apply",
    ]) == 1

    # 2. Lost staging journal fails closed with exit 3 before exit 4 hold.
    monkeypatch.setenv("STEWARD_ISSUE_HYGIENE_V2", "true")
    journal_report = tmp_path / "journal-report.json"
    assert watcher.main([
        "--child-mode", "batch", "--staging", "weekly", "--staging-initialized",
        "--staging-journal", str(tmp_path / "missing-journal.json"),
        "--apply", "--report", str(journal_report),
    ]) == 3
    assert json.loads(journal_report.read_text(encoding="utf-8"))["unknownEvidence"][0]["source"] == "staging-journal"

    # 3. Poll failure fails closed with exit 3 before exit 4 hold.
    runner, mutations = _setup_cli_world(monkeypatch, tmp_path, fail_release=True)
    poll_report = tmp_path / "poll-report.json"
    assert watcher.main(["--child-mode", "batch", "--apply", "--report", str(poll_report)]) == 3
    assert mutations == [] and runner.writes == []
    assert json.loads(poll_report.read_text(encoding="utf-8"))["unknownEvidence"][0]["source"] == "github-poll"

    # 4. #2278 inventory count mismatch fails closed with exit 3 before exit 4 hold.
    runner, mutations = _setup_cli_world(monkeypatch, tmp_path, counts=[(217, 6)] * 20)
    inv_report = tmp_path / "inv-report.json"
    assert watcher.main(["--child-mode", "batch", "--apply", "--report", str(inv_report)]) == 3
    assert mutations == [] and runner.writes == []
    assert json.loads(inv_report.read_text(encoding="utf-8"))["unknownEvidence"][0]["source"] == "repository-plan"


def test_challenge_only_separation_preserved(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(
        watcher,
        "runChallengeWatchStep",
        lambda args, rm, verbose: called.append(True) or watcher.ChallengeWatchResult(
            summaries=[], packets=[], active_count=0, resolved_count=0,
            rejected_unverified_count=0, unavailable_count=0,
        ),
    )
    code = watcher.main(["--challenge-only", "--challenge-ledger", str(tmp_path / "ledger.json")])
    assert code == 0 and called == [True]


def test_direct_repository_batch_writer_harness_remains_testable_offline():
    authority = {"owner/a": {"id": "owner/a", "suiteRef": "owner/a", "links": {"github": "https://github.com/owner/repo"}}}
    finding = {
        "finding_type": "update", "skillId": "owner/a", "currentVersion": "v0", "newVersion": "v1",
        "sourceUrl": "https://github.com/owner/repo/releases/tag/v1",
        "releasedAt": "2026-11-20T00:00:00Z", "mode": "components",
        "componentAdds": ["same"], "componentRemoves": [], "linkLiveness": [], "nameDrift": [],
    }
    gh = FakeGh()
    report, code = rb.run_repository_batch(
        [finding], gh, True, authority, index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
    )
    assert code == 0 and len(gh.writes) == 1 and report["actualIssuesCreated"] == 1
