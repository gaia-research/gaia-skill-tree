"""Workflow-timeout route: the no-history default (#2283).

Decision steward-workflow-timeout-no-history-2283 (R4): a job whose read history
has no successful run gets a deterministic, conservative timeout from its own
steps; unreadable history still stops.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.workflowproof import (
    NO_HISTORY_BASE_MINUTES,
    _main,
    history_timeout,
    no_history_from_rows,
    no_history_timeout,
    prove_workflow_edit,
    select_job_history,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# --- the value rules ---------------------------------------------------------


@pytest.mark.parametrize(
    "seconds, expected",
    [
        ([3, 4, 14], 5),  # auto-triage siblings: seconds-long jobs get the 5-minute floor
        ([600, 900], 30),  # p95 = 900 s -> 2 x 15 = 30 > 1.5 x 15
        ([60] * 20, 5),
        ([14400], 360),  # capped at the platform maximum
    ],
)
def test_history_rule(seconds: list[float], expected: int) -> None:
    assert history_timeout(seconds) == expected


def test_history_rule_never_applies_without_history() -> None:
    with pytest.raises(ValueError):
        history_timeout([])


def test_the_batch_9_jobs_get_their_documented_defaults() -> None:
    # auto-label-bot-prs.yml label-bots: one github-script call, never executed.
    assert no_history_timeout("api-script", declared_wait_seconds=0, longest_observed_seconds=None) == 10
    # auto-triage.yml auto-merge: gh/jq steps, declared poll 60 rounds x 10 s.
    assert no_history_timeout("api-script", declared_wait_seconds=600, longest_observed_seconds=None) == 30


def test_never_shorter_than_any_observed_execution() -> None:
    # The job once ran 30 minutes (and failed): 1.5 x 30 = 45 beats the 10-minute base.
    assert no_history_timeout("api-script", declared_wait_seconds=0, longest_observed_seconds=1800) == 45


@pytest.mark.parametrize(
    "step_class, wait, observed",
    [
        ("deploy", 0, None),  # not one of the three classes
        ("install-build-test", 1200, None),  # 30 + 40 = 70 > 60
        ("api-script", 0, 3000),  # 1.5 x 50 = 75 > 60: needs real history
        ("api-script", -1, None),
        ("api-script", 0, -5),
    ],
)
def test_no_default_means_stop(step_class: str, wait: float, observed: float | None) -> None:
    assert no_history_timeout(step_class, declared_wait_seconds=wait, longest_observed_seconds=observed) is None


def test_defaults_stay_inside_the_floor_and_ceiling() -> None:
    for step_class in NO_HISTORY_BASE_MINUTES:
        for wait in (0, 60, 300, 600, 900):
            value = no_history_timeout(step_class, declared_wait_seconds=wait, longest_observed_seconds=None)
            assert value is None or (10 <= value <= 60 and value % 5 == 0)


def _rows(tmp_path: Path, rows: list, name: str = "history.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(rows), encoding="utf-8")
    return str(path)


def _run(conclusion: str, seconds: float | None, start: str = "2026-11-01T00:00:00Z") -> dict:
    if seconds is None:
        return {"conclusion": conclusion, "started_at": None, "completed_at": None}
    started = datetime.fromisoformat(start.replace("Z", "+00:00"))
    done = started + timedelta(seconds=seconds)
    return {"conclusion": conclusion, "started_at": start, "completed_at": done.isoformat().replace("+00:00", "Z")}


def test_review_case_cancelled_and_timed_out_executions_are_never_ignored(tmp_path: Path, capsys) -> None:
    # #2382 review P1: no success, a 2700 s cancelled run, a 3600 s timed_out run and
    # a skipped row. Both executed: 1.5 x 3600 s = 90 min > 60, so there is no default.
    rows = [_run("cancelled", 2700), _run("timed_out", 3600), _run("skipped", None)]
    value, selection, reason = no_history_from_rows("api-script", declared_wait_seconds=0, rows=rows)
    assert value is None and "no default" in reason
    assert [item["conclusion"] for item in selection["executed"]] == ["cancelled", "timed_out"]
    assert selection["skipped"] == 1 and selection["successful"] == []
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "0",
                  "--history", _rows(tmp_path, rows)]) == 3
    out = capsys.readouterr().out
    assert '"conclusion": "timed_out"' in out and "no default" in out


def test_a_short_cancelled_execution_still_sets_the_floor(tmp_path: Path, capsys) -> None:
    rows = [_run("cancelled", 1800), _run("skipped", None)]
    assert select_job_history(rows)["executed"][0]["seconds"] == 1800
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "0",
                  "--history", _rows(tmp_path, rows)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "45"


def test_all_skipped_history_gives_the_class_default(tmp_path: Path, capsys) -> None:
    rows = [_run("skipped", None)] * 50  # auto-label-bot-prs.yml label-bots
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "0",
                  "--history", _rows(tmp_path, rows)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "10"
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "600",
                  "--history", _rows(tmp_path, rows, "b.json")]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "30"  # auto-triage.yml auto-merge


@pytest.mark.parametrize(
    "rows, reason",
    [
        ([_run("success", 60), _run("skipped", None)], "history rule"),
        ([{"conclusion": "failure", "started_at": "2026-11-01T00:00:00Z"}], "no usable times"),
        ([{"conclusion": "cancelled", "started_at": "2026-11-01T00:10:00Z", "completed_at": "2026-11-01T00:00:00Z"}],
         "no usable times"),
    ],
)
def test_no_history_stops_when_rows_do_not_permit_it(rows: list, reason: str) -> None:
    value, _selection, why = no_history_from_rows("api-script", declared_wait_seconds=0, rows=rows)
    assert value is None and reason in why


def test_history_cli_selects_successful_rows_itself(tmp_path: Path, capsys) -> None:
    rows = [_run("success", 3), _run("success", 4), _run("success", 14), _run("failure", 9000), _run("skipped", None)]
    assert _main(["history", "--history", _rows(tmp_path, rows)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "5"
    assert _main(["history", "--history", _rows(tmp_path, [_run("skipped", None)], "s.json")]) == 3
    assert "does not apply" in capsys.readouterr().out


def test_unreadable_history_file_stops(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "0", "--history", str(bad)]) == 3
    assert "stop" in capsys.readouterr().out
    assert _main(["history", "--history", str(tmp_path / "missing.json")]) == 3


def test_jobs_api_envelope_is_accepted(tmp_path: Path, capsys) -> None:
    payload = {"jobs": [_run("skipped", None), _run("failure", 120)]}
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "0", "--history", str(path)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "10"


# --- the envelope is unchanged: out-of-envelope edits are still rejected ----

LABEL_BOTS = (
    "name: Auto-label bot PRs\n"
    "on:\n  pull_request:\n    types: [opened]\n"
    "jobs:\n"
    "  label-bots:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - uses: actions/github-script@v7\n"
)


def _insert(line: str, at: int = 7) -> tuple:
    return ((at, 0, (("+", line, False),)),)


def test_the_no_history_value_passes_the_structural_proof() -> None:
    assert prove_workflow_edit(LABEL_BOTS, _insert("    timeout-minutes: 10")) == []


@pytest.mark.parametrize(
    "line",
    [
        "    timeout-minutes: 10 # no-history default",  # comment
        "    timeout-minutes: 0",
        "    timeout-minutes: 361",
        "    timeout-minutes: '10'",
        "      timeout-minutes: 10",  # wrong indentation (not the job's own key)
    ],
)
def test_out_of_envelope_insertions_are_still_rejected(line: str) -> None:
    assert prove_workflow_edit(LABEL_BOTS, _insert(line)) != []


def test_policy_carries_the_no_history_contract() -> None:
    rule = StewardPolicy.load(REPO_ROOT).dispatch_rule_for("workflow_hygiene")
    assert rule is not None
    assert any("workflowproof no-history" in command for command in rule.allowed_commands)
    assert any("no-history default" in condition for condition in rule.stop_conditions)
    assert any("no-history" in item for item in rule.proof)
    assert rule.allowed_paths == (".github/workflows/*.yml",)


# --- #2382 re-review: unusable or empty history never yields a value --------


@pytest.mark.parametrize(
    "bad",
    [
        {"conclusion": "success", "started_at": "not-a-time", "completed_at": "2026-11-01T00:01:00Z"},
        {"conclusion": "success", "started_at": "2026-11-01T00:10:00Z", "completed_at": "2026-11-01T00:00:00Z"},
        {"conclusion": "success", "started_at": "2026-11-01T00:00:00", "completed_at": "2026-11-01T00:01:00Z"},
    ],
    ids=["malformed", "reversed", "naive-vs-aware"],
)
@pytest.mark.parametrize("rule", ["history", "no-history"])
def test_an_unusable_success_row_stops_both_rules(tmp_path: Path, capsys, bad: dict, rule: str) -> None:
    rows = [_run("success", 60), bad]
    args = ["history"] if rule == "history" else ["no-history", "--class", "api-script", "--declared-wait-seconds", "0"]
    assert _main(args + ["--history", _rows(tmp_path, rows)]) == 3
    out = capsys.readouterr().out
    assert out.startswith("selection: ") and "no usable times" in out


@pytest.mark.parametrize("rule", ["history", "no-history"])
def test_an_empty_history_stops(tmp_path: Path, capsys, rule: str) -> None:
    args = ["history"] if rule == "history" else ["no-history", "--class", "api-script", "--declared-wait-seconds", "0"]
    assert _main(args + ["--history", _rows(tmp_path, [])]) == 3
    assert "no sampled history" in capsys.readouterr().out
    value, _selection, reason = no_history_from_rows("api-script", declared_wait_seconds=0, rows=[])
    assert value is None and "no sampled history" in reason
