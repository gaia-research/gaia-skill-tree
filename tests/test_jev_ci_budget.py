"""
tests/test_jev_ci_budget.py — Unit and integration tests for jev_ci_budget.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.jev_ci_budget import (
    LOCAL_DEFAULT_CAP_USD,
    MAX_CALLS_PER_RUN,
    MAX_MONTHLY_RUNS,
    MONTHLY_CI_CAP_USD,
    PER_RUN_LIMIT_USD,
    RESERVATION_USD_PER_CALL,
    UNUSED_BUFFER_USD,
    evaluate_ci_budget,
)


def _make_run(run_id: int, created_at: str, attempt: int = 1) -> dict:
    return {
        "id": run_id,
        "name": "Jev Advisory Lane",
        "created_at": created_at,
        "run_attempt": attempt,
        "status": "completed",
        "conclusion": "success",
    }


def test_budget_constants_math():
    """Verify budget math invariants: $3.60 CI + $0.50 local + $0.90 buffer = $5.00 envelope."""
    ci_calc = MAX_MONTHLY_RUNS * MAX_CALLS_PER_RUN * RESERVATION_USD_PER_CALL
    assert round(ci_calc, 2) == round(MONTHLY_CI_CAP_USD, 2)
    assert round(PER_RUN_LIMIT_USD, 4) == round(MAX_CALLS_PER_RUN * RESERVATION_USD_PER_CALL, 4)
    total_envelope = MONTHLY_CI_CAP_USD + LOCAL_DEFAULT_CAP_USD + UNUSED_BUFFER_USD
    assert round(total_envelope, 2) == 5.00


def test_approved_run():
    """Approved run within monthly ceiling, first attempt, same month."""
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    current_run_id = 12345
    runs_data = {
        "total_count": 10,
        "workflow_runs": [
            _make_run(current_run_id, "2026-10-15T11:55:00Z", attempt=1),
            _make_run(12344, "2026-10-14T08:00:00Z", attempt=1),
        ],
    }

    res = evaluate_ci_budget(
        runs_data=runs_data,
        current_run_id=current_run_id,
        run_attempt=1,
        current_time=now,
    )

    assert res["allowed"] is True
    assert res["reason"] == "budget_approved"
    assert res["month"] == "2026-10"
    assert res["monthly_runs_count"] == 10
    assert res["max_monthly_runs"] == 60
    assert res["per_run_limit_usd"] == 0.06
    assert res["max_calls_per_run"] == 20
    assert res["estimated_spent_usd"] == 0.60
    assert len(res["limitations"]) >= 2


def test_boundary_monthly_runs():
    """Exactly 60 runs is allowed; 61 runs is blocked."""
    now = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    current_run_id = 200
    runs_at_cap = {
        "total_count": 60,
        "workflow_runs": [_make_run(current_run_id, "2026-10-20T09:00:00Z", attempt=1)],
    }
    res_at_cap = evaluate_ci_budget(runs_at_cap, current_run_id, 1, current_time=now)
    assert res_at_cap["allowed"] is True

    runs_over_cap = {
        "total_count": 61,
        "workflow_runs": [_make_run(current_run_id, "2026-10-20T09:00:00Z", attempt=1)],
    }
    res_over = evaluate_ci_budget(runs_over_cap, current_run_id, 1, current_time=now)
    assert res_over["allowed"] is False
    assert res_over["reason"] == "monthly_run_limit_exceeded"
    assert res_over["monthly_runs_count"] == 61


def test_rerun_not_permitted():
    """Run attempts > 1 must fail closed to prevent duplicate paid execution."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    current_run_id = 300
    runs_data = {
        "total_count": 5,
        "workflow_runs": [_make_run(current_run_id, "2026-10-01T09:00:00Z", attempt=2)],
    }

    # Caller passes attempt=2
    res = evaluate_ci_budget(runs_data, current_run_id, run_attempt=2, current_time=now)
    assert res["allowed"] is False
    assert res["reason"] == "rerun_not_permitted"

    # Caller passes attempt=1 but GitHub run record indicates attempt=2
    res2 = evaluate_ci_budget(runs_data, current_run_id, run_attempt=1, current_time=now)
    assert res2["allowed"] is False
    assert res2["reason"] == "rerun_not_permitted"


def test_missing_current_run():
    """If current run ID does not appear in fetched runs, fail closed."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    runs_data = {
        "total_count": 2,
        "workflow_runs": [_make_run(999, "2026-10-01T09:00:00Z")],
    }
    res = evaluate_ci_budget(runs_data, current_run_id=404, run_attempt=1, current_time=now)
    assert res["allowed"] is False
    assert res["reason"] == "current_run_not_found"


def test_created_month_mismatch():
    """If run was created in a previous month, fail closed."""
    now = datetime(2026, 10, 1, 0, 5, 0, tzinfo=timezone.utc)
    current_run_id = 500
    runs_data = {
        "total_count": 1,
        # Created in September
        "workflow_runs": [_make_run(current_run_id, "2026-09-30T23:59:59Z")],
    }
    res = evaluate_ci_budget(runs_data, current_run_id, 1, current_time=now)
    assert res["allowed"] is False
    assert res["reason"] == "created_month_mismatch"


def test_missing_or_invalid_run_id():
    """Missing or non-integer run ID fails closed."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    runs_data = {"total_count": 1, "workflow_runs": []}

    res_none = evaluate_ci_budget(runs_data, None, 1, current_time=now)
    assert res_none["allowed"] is False
    assert res_none["reason"] == "missing_run_id"

    res_str = evaluate_ci_budget(runs_data, "abc", 1, current_time=now)
    assert res_str["allowed"] is False
    assert res_str["reason"] == "invalid_run_id"


def test_api_error_and_malformed_payload():
    """API errors, missing fields, or negative counts fail closed."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)

    # None payload
    res_none = evaluate_ci_budget(None, 100, 1, current_time=now)
    assert res_none["allowed"] is False
    assert res_none["reason"] == "api_error"

    # Missing total_count
    res_missing_count = evaluate_ci_budget({"workflow_runs": []}, 100, 1, current_time=now)
    assert res_missing_count["allowed"] is False
    assert res_missing_count["reason"] == "malformed_payload"

    # Missing workflow_runs
    res_missing_runs = evaluate_ci_budget({"total_count": 1}, 100, 1, current_time=now)
    assert res_missing_runs["allowed"] is False
    assert res_missing_runs["reason"] == "malformed_payload"

    # Negative total_count
    res_neg = evaluate_ci_budget({"total_count": -1, "workflow_runs": []}, 100, 1, current_time=now)
    assert res_neg["allowed"] is False
    assert res_neg["reason"] == "malformed_payload"


def test_cli_execution_with_fixture(tmp_path: Path):
    """Test CLI invoking scripts/jev_ci_budget.py with --runs-json and $GITHUB_OUTPUT."""
    fixture_path = tmp_path / "runs.json"
    gh_output_path = tmp_path / "github_output.txt"

    fixture_data = {
        "total_count": 12,
        "workflow_runs": [
            _make_run(9876, "2026-10-05T12:00:00Z", attempt=1),
        ],
    }
    fixture_path.write_text(json.dumps(fixture_data), encoding="utf-8")

    env = dict(os.environ)
    env["GITHUB_OUTPUT"] = str(gh_output_path)

    cmd = [
        sys.executable,
        "scripts/jev_ci_budget.py",
        "--runs-json",
        str(fixture_path),
        "--run-id",
        "9876",
        "--run-attempt",
        "1",
        "--current-time",
        "2026-10-05T12:30:00Z",
        "--strict",
        "--json",
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    assert proc.returncode == 0
    parsed = json.loads(proc.stdout)
    assert parsed["allowed"] is True
    assert parsed["reason"] == "budget_approved"

    # Check GITHUB_OUTPUT was written
    output_content = gh_output_path.read_text(encoding="utf-8")
    assert "allowed=true" in output_content
    assert "reason=budget_approved" in output_content
    assert "month=2026-10" in output_content
    assert "per_run_limit_usd=0.06" in output_content
    assert "max_calls=20" in output_content


def test_cli_strict_exit_code_on_block(tmp_path: Path):
    """Test that --strict exits 1 when run is blocked."""
    fixture_path = tmp_path / "runs_blocked.json"
    fixture_data = {
        "total_count": 65,  # Exceeded cap
        "workflow_runs": [_make_run(555, "2026-10-01T10:00:00Z")],
    }
    fixture_path.write_text(json.dumps(fixture_data), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/jev_ci_budget.py",
        "--runs-json",
        str(fixture_path),
        "--run-id",
        "555",
        "--run-attempt",
        "1",
        "--current-time",
        "2026-10-01T11:00:00Z",
        "--strict",
        "--json",
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 1
    parsed = json.loads(proc.stdout)
    assert parsed["allowed"] is False
    assert parsed["reason"] == "monthly_run_limit_exceeded"


def test_bool_total_count_fails_closed():
    """Verify boolean total_count (True/False) is rejected as malformed."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    for bad_count in [True, False]:
        data = {
            "total_count": bad_count,
            "workflow_runs": [_make_run(100, "2026-10-01T09:00:00Z")],
        }
        res = evaluate_ci_budget(data, 100, 1, current_time=now)
        assert res["allowed"] is False
        assert res["reason"] == "malformed_payload"


def test_malformed_run_record_attempt():
    """Verify malformed run_record_attempt in GitHub record fails closed."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    for bad_attempt in ["invalid", True, False, -1, 0]:
        data = {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": 100,
                    "created_at": "2026-10-01T09:00:00Z",
                    "run_attempt": bad_attempt,
                }
            ],
        }
        res = evaluate_ci_budget(data, 100, 1, current_time=now)
        assert res["allowed"] is False
        assert res["reason"] == "malformed_payload"


def test_missing_or_invalid_cap():
    """Verify missing, boolean, non-integer, or <= 0 cap fails closed."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    data = {
        "total_count": 1,
        "workflow_runs": [_make_run(100, "2026-10-01T09:00:00Z")],
    }
    for bad_cap in [None, True, False, "abc", 0, -5]:
        res = evaluate_ci_budget(data, 100, 1, current_time=now, max_monthly_runs=bad_cap)
        assert res["allowed"] is False
        assert res["reason"] == "invalid_cap"


def test_hard_cap_ceiling_never_relaxes_budget():
    """Verify max_monthly_runs > 60 is clamped hard to 60 and never relaxes budget."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    # Total count 61 with requested cap 100 must fail closed because cap is clamped to 60
    data_61 = {
        "total_count": 61,
        "workflow_runs": [_make_run(100, "2026-10-01T09:00:00Z")],
    }
    res = evaluate_ci_budget(data_61, 100, 1, current_time=now, max_monthly_runs=100)
    assert res["allowed"] is False
    assert res["reason"] == "monthly_run_limit_exceeded"
    assert res["max_monthly_runs"] == 60


def test_mismatched_total_count_and_list_length_incl0():
    """Verify mismatched total_count vs list length (including 0) fails closed."""
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)

    # total_count == 0 but list is non-empty
    res_zero_count = evaluate_ci_budget(
        {"total_count": 0, "workflow_runs": [_make_run(100, "2026-10-01T09:00:00Z")]},
        100,
        1,
        current_time=now,
    )
    assert res_zero_count["allowed"] is False
    assert res_zero_count["reason"] == "malformed_payload"

    # total_count > 0 but list is empty
    res_empty_list = evaluate_ci_budget(
        {"total_count": 5, "workflow_runs": []},
        100,
        1,
        current_time=now,
    )
    assert res_empty_list["allowed"] is False
    assert res_empty_list["reason"] == "malformed_payload"

    # total_count < list length
    res_smaller_count = evaluate_ci_budget(
        {
            "total_count": 1,
            "workflow_runs": [
                _make_run(100, "2026-10-01T09:00:00Z"),
                _make_run(101, "2026-10-01T09:01:00Z"),
            ],
        },
        100,
        1,
        current_time=now,
    )
    assert res_smaller_count["allowed"] is False
    assert res_smaller_count["reason"] == "malformed_payload"

    # Non-dict in list
    res_nondict = evaluate_ci_budget(
        {"total_count": 1, "workflow_runs": ["invalid_item"]},
        100,
        1,
        current_time=now,
    )
    assert res_nondict["allowed"] is False
    assert res_nondict["reason"] == "malformed_payload"


def test_fetch_workflow_runs_gh_forces_get(monkeypatch):
    """Verify fetch_workflow_runs_gh uses --method GET to prevent gh api defaulting to POST with -F."""
    from scripts.jev_ci_budget import fetch_workflow_runs_gh

    captured_cmd = None

    def fake_run(cmd, *args, **kwargs):
        nonlocal captured_cmd
        captured_cmd = cmd
        proc = subprocess.CompletedProcess(args=cmd, returncode=0, stdout='{"total_count": 0, "workflow_runs": []}')
        return proc

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = fetch_workflow_runs_gh("owner/repo", "workflow.yml", "2026-10-01..2026-10-31")

    assert captured_cmd is not None
    assert captured_cmd[0] == "gh"
    assert captured_cmd[1] == "api"
    assert "--method" in captured_cmd
    method_idx = captured_cmd.index("--method")
    assert captured_cmd[method_idx + 1] == "GET"
    assert res == {"total_count": 0, "workflow_runs": []}
