"""Pin the Steward clock for every issue-hygiene test (B8 H-2).

The fixtures are a census fetched at 2026-10-21T19:00Z, and the freshness gate is six hours. A test that reads the
real clock therefore turns red as soon as the window closes. Every test in this tree runs at FIXTURE_NOW instead,
through the ``setClock`` seam. Production has no environment pin: this seam is the only way to move the clock, and
only tests call it.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from gaia_cli.steward.clock import parseInstant, setClock

FIXTURE_NOW = "2026-10-21T19:30:00Z"


@pytest.fixture(autouse=True)
def pinnedSteward() -> Iterator[str]:
    previous = setClock(lambda: parseInstant(FIXTURE_NOW))
    try:
        yield FIXTURE_NOW
    finally:
        setClock(previous)
