"""Pin the Steward clock for every PR-maintenance test. Fixtures are fetched at FIXTURE_NOW, the freshness gate is one hour."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from gaia_cli.steward.clock import parseInstant, setClock

FIXTURE_NOW = "2026-11-04T18:30:00Z"


@pytest.fixture(autouse=True)
def pinnedSteward() -> Iterator[str]:
    previous = setClock(lambda: parseInstant(FIXTURE_NOW))
    try:
        yield FIXTURE_NOW
    finally:
        setClock(previous)
