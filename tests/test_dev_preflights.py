"""Behavioral contract for batched ``gaia dev`` preflight checks."""

import pytest

from gaia_cli.commands.dev.helpers import (
    _fail_dev_preflight,
    _run_dev_preflights,
)


def test_all_declared_checks_run_when_some_fail():
    calls = []

    def failing_check():
        calls.append("failing")
        _fail_dev_preflight("first failure")

    def passing_check():
        calls.append("passing")

    def another_failing_check():
        calls.append("another failure")
        _fail_dev_preflight("second failure")

    with pytest.raises(SystemExit) as exc:
        _run_dev_preflights([failing_check, passing_check, another_failing_check])

    assert exc.value.code == 1
    assert calls == ["failing", "passing", "another failure"]


def test_multiple_failures_are_reported_in_declaration_order(capsys):
    def first_check():
        _fail_dev_preflight("first failure", fix="fix the first failure")

    def second_check():
        _fail_dev_preflight("second failure", fix="fix the second failure")

    with pytest.raises(SystemExit):
        _run_dev_preflights([first_check, second_check])

    assert capsys.readouterr().err.splitlines() == [
        "Error: first failure",
        "Fix: fix the first failure",
        "Error: second failure",
        "Fix: fix the second failure",
    ]


def test_single_failure_output_is_compatible(capsys):
    def failing_check():
        _fail_dev_preflight("one failure", fix="one remedy")

    with pytest.raises(SystemExit) as exc:
        _run_dev_preflights([failing_check])

    assert exc.value.code == 1
    assert capsys.readouterr().err == "Error: one failure\nFix: one remedy\n"


def test_no_failures_return_normally_without_output(capsys):
    calls = []

    _run_dev_preflights(
        [lambda: calls.append("first"), lambda: calls.append("second")]
    )

    assert calls == ["first", "second"]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_unexpected_exception_is_not_swallowed(capsys):
    expected = RuntimeError("unexpected")

    def broken_check():
        raise expected

    with pytest.raises(RuntimeError) as exc:
        _run_dev_preflights([broken_check])

    assert exc.value is expected
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
