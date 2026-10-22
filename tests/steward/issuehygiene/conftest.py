"""Pin the Steward clock for every issue-hygiene test (B7).

The fixtures are a census fetched at 2026-10-21T19:00Z, and the freshness gate is six hours. A test
that reads the real clock therefore turns red as soon as the window closes. Every test in this tree
runs at FIXTURE_NOW instead, which sits inside the window. The pin is read through
``gaia_cli.steward.clock.utcNow``, which honours it only under pytest, so the outcome does not depend
on the wall-clock date.
"""

from __future__ import annotations

import pytest

from gaia_cli.steward.clock import PIN_ENV

FIXTURE_NOW = "2026-10-21T19:30:00Z"


@pytest.fixture(autouse=True)
def pinnedSteward(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(PIN_ENV, FIXTURE_NOW)
    return FIXTURE_NOW
