"""Workflow-timeout route: the no-history default (#2283).

Decision steward-workflow-timeout-no-history-2283 (R4): a job whose read history
has no successful run gets a deterministic, conservative timeout from its own
steps; unreadable history still stops.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.workflowproof import (
    NO_HISTORY_BASE_MINUTES,
    _main,
    history_timeout,
    no_history_timeout,
    prove_workflow_edit,
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


def test_cli_prints_the_value_or_stops(capsys: pytest.CaptureFixture[str]) -> None:
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "600"]) == 0
    assert capsys.readouterr().out.strip() == "30"
    assert _main(["no-history", "--class", "install-build-test", "--declared-wait-seconds", "1200"]) == 3
    assert "no default" in capsys.readouterr().out
    assert _main(["history", "--successful-seconds", "3", "4", "14"]) == 0
    assert capsys.readouterr().out.strip() == "5"


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
