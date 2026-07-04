"""Tests for scripts/contentEngine/synthesizer.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG_DIR = ROOT / "scripts" / "contentEngine"
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

import synthesizer  # noqa: E402


def _validReport() -> dict:
    return {
        "sections": {
            "trending": {"entries": [{"id": "a/x", "name": "X"}]},
            "ascended": {"entries": []},
            "contested": {"entries": []},
        }
    }


def test_L1_returns_none_without_env(monkeypatch):
    """L1 must silently return None when the LLM env gate is unset.

    The MVP default path relies on this — the guard behind None is
    NotImplementedError, so any accidental False-negative here would
    crash every cron invocation.
    """
    monkeypatch.delenv("GAIA_CONTENT_ENGINE_LLM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert synthesizer.synthesizeL1(_validReport()) is None
    assert synthesizer.synthesizeL2(_validReport()) is None


def test_L1_still_none_when_only_flag_set(monkeypatch):
    """Only-one-of-two guard: flag alone shouldn't switch on the LLM path."""
    monkeypatch.setenv("GAIA_CONTENT_ENGINE_LLM", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert synthesizer.synthesizeL1(_validReport()) is None


def test_L3_mechanical_deterministic():
    """L3 is a pure function — the SAME input must produce the SAME output
    bit-for-bit. No timestamps, no non-determinism inside L3.
    """
    a = synthesizer.synthesizeL3Mechanical(_validReport())
    b = synthesizer.synthesizeL3Mechanical(_validReport())
    assert a == b
    assert a["salvageLayer"] == "L3"


def test_synthesize_layer_flag_is_L3_without_env(monkeypatch):
    monkeypatch.delenv("GAIA_CONTENT_ENGINE_LLM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _, layer = synthesizer.synthesize(_validReport())
    assert layer == "L3"


def test_synthesize_raises_on_all_empty():
    empty = {"sections": {"trending": {"entries": []},
                          "ascended": {"entries": []},
                          "contested": {"entries": []}}}
    with pytest.raises(ValueError, match="empty sections"):
        synthesizer.synthesize(empty)
