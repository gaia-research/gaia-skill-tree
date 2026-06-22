"""Tests for ``scripts/generateBadges.py`` data-assembly redaction.

Pins the invariant that entirely pre-named/demoted contributors (every named
entry ≤1★, including ``awaitingClassification`` rows) never reach the public
badge pipeline. See ``scripts/validate_redaction.py`` Section D and CLAUDE.md
"Known Badges Issues" for the broader rule.

The 2026-06-22 regen loop (PRs #800, #802) traced to ``collect_contributors``
silently importing 1★ awaiting entries; this guard breaks the loop at the
collection layer rather than relying on the per-call short-circuit inside
``write_user_badges``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "generateBadges.py"


def _load() -> object:
    """Import ``generateBadges`` by path (the script is not in a package)."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    spec = importlib.util.spec_from_file_location("generateBadges", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def gb(tmp_path, monkeypatch):
    """Load the generator and re-point ``NAMED_JSON`` at a per-test fixture."""
    mod = _load()
    fixture = tmp_path / "named-skills.json"
    monkeypatch.setattr(mod, "NAMED_JSON", fixture)
    return mod, fixture


def _write(fixture: Path, payload: dict) -> None:
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# ── collect_contributors() ───────────────────────────────────────────────────

def test_collect_contributors_drops_prenamed_only_handles(gb):
    """A contributor whose every entry is ≤1★ — including awaiting rows — is
    excluded from the returned mapping. A contributor with a 2★+ entry is kept,
    even if they also have a 1★ sibling."""
    mod, fixture = gb
    _write(fixture, {
        "buckets": {
            "automated-testing": [
                # entirely-prenamed (only entry is 1★)
                {"id": "prenamed/foo", "contributor": "prenamed",
                 "level": "1★", "type": "basic"},
                # mixed — has a 2★ here and (below) a 1★ as well; kept
                {"id": "mixed/bar", "contributor": "mixed",
                 "level": "2★", "type": "basic"},
            ],
            "browser-automation": [
                {"id": "mixed/baz", "contributor": "mixed",
                 "level": "1★", "type": "basic"},
                # fully-named
                {"id": "named/qux", "contributor": "named",
                 "level": "3★", "type": "basic"},
            ],
        },
        "awaitingClassification": [
            # awaiting-only — must NOT lift the handle out of redaction
            {"id": "awaiting/only", "contributor": "awaitingOnly",
             "level": "1★", "type": "basic"},
        ],
    })

    out = mod.collect_contributors()

    assert set(out) == {"mixed", "named"}, (
        "prenamed-only and awaitingClassification-only contributors must be "
        "filtered out of collect_contributors()"
    )
    assert out["mixed"]["top_rank"] == 2
    assert out["named"]["top_rank"] == 3
    # Mixed retains both its 1★ and 2★ entries for per-skill rendering — only
    # the contributor-level gate fires here.
    assert {s["id"] for s in out["mixed"]["named_skills"]} == {
        "mixed/bar", "mixed/baz"
    }


def test_collect_contributors_handles_empty_payload(gb):
    """Missing ``buckets`` / ``awaitingClassification`` keys do not crash."""
    mod, fixture = gb
    _write(fixture, {})
    assert mod.collect_contributors() == {}


def test_collect_contributors_missing_file(gb):
    """Missing fixture file is tolerated (mirrors a fresh registry)."""
    mod, fixture = gb
    # do not create fixture
    assert not fixture.exists()
    assert mod.collect_contributors() == {}


# ── prenamed_contributor_handles() ────────────────────────────────────────────

def test_prenamed_contributor_handles_covers_awaiting_only(gb):
    """The helper is the gate the ``main()`` scan-only loop consults — it must
    include both bucket-only-≤1★ and awaitingClassification-only contributors."""
    mod, fixture = gb
    _write(fixture, {
        "buckets": {
            "auto": [
                {"id": "prenamed/foo", "contributor": "prenamed", "level": "1★"},
                {"id": "named/foo", "contributor": "named", "level": "4★"},
            ],
        },
        "awaitingClassification": [
            {"id": "awaiting/only", "contributor": "awaitingOnly", "level": "1★"},
        ],
    })
    assert mod.prenamed_contributor_handles() == {"prenamed", "awaitingOnly"}


def test_prenamed_contributor_handles_max_rank_wins(gb):
    """A 2★ entry in any bucket lifts the contributor out of redaction even when
    other entries are 1★ — matches ``validate_redaction.py`` Section D."""
    mod, fixture = gb
    _write(fixture, {
        "buckets": {
            "a": [{"id": "mixed/a", "contributor": "mixed", "level": "1★"}],
            "b": [{"id": "mixed/b", "contributor": "mixed", "level": "2★"}],
        },
        "awaitingClassification": [
            {"id": "mixed/c", "contributor": "mixed", "level": "1★"},
        ],
    })
    assert mod.prenamed_contributor_handles() == set()
