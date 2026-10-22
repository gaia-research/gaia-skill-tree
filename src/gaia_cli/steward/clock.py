"""The Steward clock: the one place where issue-hygiene and runner code read the current UTC time (B8 H-2).

Production reads the real clock, and no environment variable can change it. The clock is a module-level seam:
``setClock`` installs a replacement source and returns the previous one, and ``setClock(None)`` restores the real
clock. Only tests call it. ``tests/steward/issuehygiene/conftest.py`` installs a fixed instant inside the fixture
window for every issue-hygiene test, so the suite does not depend on the wall-clock date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

Source = Callable[[], datetime]


def realClock() -> datetime:
    return datetime.now(timezone.utc)


clockSource: Source = realClock


def parseInstant(text: str) -> datetime:
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def utcNow() -> datetime:
    """The current UTC instant from the installed source (the real clock in production)."""
    return clockSource()


def getClock() -> Source:
    """The installed clock source, so a test can restore it."""
    return clockSource


def setClock(source: Source | None) -> Source:
    """Install ``source`` as the clock (tests only). ``None`` restores the real clock. Returns the previous source."""
    global clockSource
    previous = clockSource
    clockSource = source if source is not None else realClock
    return previous
