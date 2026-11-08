"""Pin the Steward clock for every PR-maintenance test. Fixtures are fetched at FIXTURE_NOW, the freshness gate is one hour."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from gaia_cli.steward.clock import parseInstant, setClock

FIXTURE_NOW = "2026-11-04T18:30:00Z"

_PROOF_CACHE: dict[tuple[str, str, str, str], list] = {}


@pytest.fixture(autouse=True)
def memoizedContentEngineProofs(monkeypatch):
    """Memoize deterministic git-commit content proofs per repository instance."""
    from gaia_cli.steward.prmaintenance import proofs
    original = proofs.contentEngineProofs
    def memoized(root, baseSha, headSha, label):
        key = (str(root.resolve()), baseSha, headSha, label)
        if key not in _PROOF_CACHE:
            _PROOF_CACHE[key] = original(root, baseSha, headSha, label)
        return [proofs.Proof(p.name, p.state, p.detail) for p in _PROOF_CACHE[key]]
    monkeypatch.setattr(proofs, "contentEngineProofs", memoized)


@pytest.fixture(autouse=True)
def pinnedSteward() -> Iterator[str]:
    previous = setClock(lambda: parseInstant(FIXTURE_NOW))
    try:
        yield FIXTURE_NOW
    finally:
        setClock(previous)
