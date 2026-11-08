"""Offline baseline tests for the current CI churn calculator."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ci_churn.py"
spec = importlib.util.spec_from_file_location("ci_churn_baseline", MODULE_PATH)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Implement widget", "feature"),
        ("Address review feedback", "review-fix"),
        ("FIX CI after review feedback", "ci-fix"),
        ("Feature\n\nFix import chain", "ci-fix"),
        ("Add import documentation", "feature"),
    ],
)
def test_classification(message, expected):
    assert ci.classify_commit(message) == expected


def test_session_log_parsing(tmp_path):
    log = tmp_path / "session.jsonl"
    log.write_text(
        '\nnot json\n'
        '{"type":"assistant","durationMs":1200}\n'
        '{"type":"tool_result","duration_ms":350}\n'
        '{"type":"user","durationMs":800}\n'
        '{"type":"assistant","durationMs":0}\n', encoding="utf-8"
    )
    assert ci.parse_session_log(str(log)) == [
        {"type": "assistant", "duration_ms": 1200},
        {"type": "tool_result", "duration_ms": 350},
    ]
    assert ci.parse_session_log(str(tmp_path / "missing")) == []


def test_commit_and_run_api_parsing(monkeypatch):
    paths = []

    def fake_gh(path):
        paths.append(path)
        if "/pulls/" in path:
            return [{"sha": "123456789abc", "commit": {"message": "Subject\nBody"}}]
        return {"workflow_runs": [
            {"name": "tests", "conclusion": "failure", "id": 4,
             "run_started_at": "2026-01-01T00:00:00Z",
             "updated_at": "2026-01-01T00:01:05Z"},
            {"status": "queued", "run_started_at": "invalid", "updated_at": "invalid"},
            {"run_started_at": "2026-01-01T00:01:00Z",
             "updated_at": "2026-01-01T00:00:00Z"},
        ]}

    monkeypatch.setattr(ci, "_gh", fake_gh)
    assert ci.get_pr_commits(7, "org", "repo") == [
        {"sha": "123456789abc", "short": "123456789", "message": "Subject"}
    ]
    runs = ci.get_runs_for_sha("abc", "org", "repo")
    assert [r["duration_s"] for r in runs] == [65, 0, 0]
    assert runs[0] == {"name": "tests", "conclusion": "failure", "duration_s": 65,
                       "run_id": 4, "html_url": ""}
    assert runs[1]["conclusion"] == "queued"
    assert paths == ["repos/org/repo/pulls/7/commits",
                     "repos/org/repo/actions/runs?head_sha=abc&per_page=50"]


def test_gh_json_and_error_without_subprocess(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout='[{"id":1}]', stderr="")

    monkeypatch.setattr(ci.subprocess, "run", run)
    assert ci._gh("repos/o/r") == [{"id": 1}]
    assert calls == [(["gh", "api", "--paginate", "repos/o/r"],
                      {"capture_output": True, "text": True, "check": False})]
    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=2, stdout="", stderr=" denied \n"))
    with pytest.raises(RuntimeError, match=r"gh api failed \(2\): denied"):
        ci._gh("repos/o/r")


def test_churn_accounting_and_report():
    commits = [
        {"sha": "a", "short": "a", "message": "Feature"},
        {"sha": "b", "short": "b", "message": "Fix import"},
        {"sha": "c", "short": "c", "message": "Per review"},
    ]
    runs = {
        "a": [{"duration_s": 20, "conclusion": "failure"}],
        "b": [{"duration_s": 60, "conclusion": "success"},
              {"duration_s": 10, "conclusion": "timed_out"}],
        "c": [{"duration_s": 30, "conclusion": "error"}],
    }
    metrics = ci.calculate_churn(commits, runs, [{"duration_ms": 200000}])
    assert (metrics["feature_count"], metrics["ci_fix_count"], metrics["review_fix_count"]) == (1, 1, 1)
    assert (metrics["avoidable_count"], metrics["churn_ratio"], metrics["churn_pct"]) == (2, 0.667, 66.7)
    assert (metrics["avoidable_ci_s"], metrics["failed_ci_s"]) == (100, 60)
    assert (metrics["agent_wait_min_s"], metrics["agent_wait_full_s"]) == (60, 100)
    assert [(c["total_ci_s"], c["failure_count"], c["failure_s"]) for c in metrics["commits"]] == [
        (20, 1, 20), (70, 1, 10), (30, 1, 30)
    ]
    report = ci.format_text(7, "org", "repo", metrics)
    assert "CI Churn Report — PR #7  (org/repo)" in report
    assert "Churn ratio: 66.7%" in report
    assert "CI compute burned on avoidable commits : 1m 40s" in report
    assert "Agent blocked-wait estimate (min / max): 1m 00s / 1m 40s" in report
    assert "churn ≈ 50% of session" in report
    assert "⚠ ci-fix" in report and "△ review-fix" in report
    assert "import chain smoke test" in report


def test_empty_churn_and_hint_deduplication():
    metrics = ci.calculate_churn([], {}, [])
    assert metrics["churn_ratio"] == 0
    assert metrics["avoidable_ci_s"] == metrics["failed_ci_s"] == 0
    report = ci.format_text(1, "o", "r", metrics)
    assert "No churn detected" in report
    assert "Suggested local pre-push checks" not in report
    hints = ci._root_cause_hints([{"message": "Fix import"}, {"message": "Lazy import"}])
    assert sum("import chain smoke test" in hint for hint in hints) == 1
    assert any("pyyaml" in hint for hint in hints)


@pytest.mark.parametrize(("seconds", "expected"), [
    (0, "0s"), (59, "59s"), (60, "1m 00s"), (3601, "1h 00m 01s"),
])
def test_duration_format(seconds, expected):
    assert ci._fmt_duration(seconds) == expected
