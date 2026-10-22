"""Lane B8 H-2: no environment variable can move the Steward clock of a production run.

``GAIA_STEWARD_NOW`` and ``PYTEST_CURRENT_TEST`` used to pin the clock together, so a stale census passed
freshness whenever both were set. The clock is now an injectable seam that only tests set. Nothing here
reaches the network: the closure scripts run on fakes and a checkout built in a temporary directory.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from gaia_cli.steward import clock
from gaia_cli.steward.clock import getClock, setClock, utcNow
from scripts.steward_issue_close import EXIT_REFUSED, main as closeMain
from scripts.steward_issue_reconcile import main as reconcileMain
from tests.steward.issuehygiene.e_fakes import REPO
from tests.steward.issuehygiene.test_b5_closure_guard import Forge, actionFor, checkout

PINNED = "2026-10-21T19:30:00Z"
STALE_FETCH = "2020-01-01T00:00:00Z"


def test_the_production_clock_is_the_real_clock_whatever_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("GAIA_STEWARD_NOW", "2001-01-01T00:00:00Z")
    previous = getClock()
    setClock(None)
    try:
        delta = abs((utcNow() - datetime.now(timezone.utc)).total_seconds())
    finally:
        setClock(previous)
    assert delta < 60, "a pinned environment must not move the production clock"


def test_the_clock_module_reads_no_environment_variable() -> None:
    source = Path(clock.__file__).read_text(encoding="utf-8")
    assert "GAIA_STEWARD_NOW" not in source
    assert "PYTEST_CURRENT_TEST" not in source
    assert "os.environ" not in source and "getenv" not in source


def test_the_seam_is_settable_and_restorable() -> None:
    fixed = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    previous = setClock(lambda: fixed)
    try:
        assert utcNow() == fixed
    finally:
        setClock(previous)
    assert utcNow() != fixed
    assert getClock() is previous


def test_a_stale_census_is_refused_by_the_close_script_even_with_both_variables_set(
        tmp_path: Path, monkeypatch, capsys) -> None:
    """Both variables set, census fetched in 2020: the real clock refuses it (old code: the pin made it fresh)."""
    root, document = checkout(tmp_path)
    actionFile = actionFor(root, document)
    census = root / ".gaia" / "steward" / "inputs" / "github-issues.json"
    stale = json.loads(census.read_text(encoding="utf-8"))
    stale["fetchedAt"] = STALE_FETCH
    census.write_text(json.dumps(stale), encoding="utf-8")
    monkeypatch.setenv("GAIA_STEWARD_NOW", PINNED)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_b8_clock.py::pinned")
    previous = getClock()
    setClock(None)
    calls: list[str] = []
    try:
        code = closeMain(["--root", str(root), "--action", str(actionFile), "--repo", REPO],
                         forgeFactory=lambda repo, token: calls.append(repo) or Forge({}))
    finally:
        setClock(previous)
    err = capsys.readouterr().err
    assert code == EXIT_REFUSED
    assert calls == [], "no forge may be built for a stale census"
    assert "census" in err


def test_a_stale_census_is_refused_by_reconcile_apply_closures_with_both_variables_set(
        tmp_path: Path, monkeypatch, capsys) -> None:
    root, document = checkout(tmp_path)
    census = root / ".gaia" / "steward" / "inputs" / "github-issues.json"
    stale = json.loads(census.read_text(encoding="utf-8"))
    stale["fetchedAt"] = STALE_FETCH
    census.write_text(json.dumps(stale), encoding="utf-8")
    monkeypatch.setenv("GAIA_STEWARD_NOW", PINNED)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_b8_clock.py::pinned")
    previous = getClock()
    setClock(None)
    calls: list[str] = []
    receipts = root / ".gaia" / "steward" / "issue-hygiene" / "receipts" / "R1.jsonl"
    try:
        code = reconcileMain(["--root", str(root), "--apply-closures", "--i-understand-writes",
                              "--receipts", str(receipts), "--repo", REPO],
                             forgeFactory=lambda name, token: calls.append(name) or Forge({}))
    finally:
        setClock(previous)
    capsys.readouterr()
    assert code == EXIT_REFUSED
    assert calls == [] and not receipts.exists()
