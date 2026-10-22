"""The Steward clock: one place where issue-hygiene and runner code read the current UTC time (B7).

Production always reads the real clock. The pin is honoured only while pytest is running (the
``PYTEST_CURRENT_TEST`` variable is set), so no environment variable can move the clock of a
real run. ``tests/steward/issuehygiene/conftest.py`` pins ``GAIA_STEWARD_NOW`` to a time inside
the fixture window, which keeps every freshness check deterministic at any wall-clock date.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

PIN_ENV = "GAIA_STEWARD_NOW"


def parseInstant(text: str) -> datetime:
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def utcNow() -> datetime:
    """The current UTC instant, or the test pin when running under pytest with ``GAIA_STEWARD_NOW`` set."""
    pinned = os.environ.get(PIN_ENV)
    if pinned and os.environ.get("PYTEST_CURRENT_TEST"):
        return parseInstant(pinned)
    return datetime.now(timezone.utc)
