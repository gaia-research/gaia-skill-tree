import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "steward_report_inputs.py"


def run(*args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)


def test_a_missing_input_is_warned_and_never_shown_as_ok(tmp_path):
    result = run("--item", "ci-runs=ok", "--item", "test-history=missing:first run")
    assert result.returncode == 0
    assert "::warning title=steward input test-history missing::first run" in result.stdout
    assert "| ci-runs | ok | - |" in result.stdout
    assert "::warning title=steward input ci-runs" not in result.stdout


def test_a_failed_suite_stays_visible(tmp_path):
    result = run("--item", "test-suite=failed:pytest exit 1")
    assert "::warning title=steward input test-suite failed::pytest exit 1" in result.stdout


def test_one_run_of_history_is_reported_as_incomplete(tmp_path):
    history = tmp_path / "h.json"
    history.write_text(json.dumps({"runs": [{"runId": "1"}]}))
    result = run("--history", str(history))
    assert "| test-history size | partial |" in result.stdout and "INCOMPLETE" in result.stdout


def test_an_unreadable_history_is_not_evaluated(tmp_path):
    result = run("--history", str(tmp_path / "absent.json"))
    assert "NOT EVALUATED" in result.stdout and "| test-history size | missing |" in result.stdout


def test_two_runs_are_complete_enough(tmp_path):
    history = tmp_path / "h.json"
    history.write_text(json.dumps({"runs": [{"runId": "1"}, {"runId": "2"}]}))
    result = run("--history", str(history))
    assert "| test-history size | ok | 2 run(s) in history |" in result.stdout


def test_a_bad_state_is_refused():
    assert run("--item", "x=great").returncode != 0
