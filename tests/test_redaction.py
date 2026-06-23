"""Tests for the universal redaction gate.

Per META.md § 1: stars live on named skills only — a skill at 1★ (Awakened) or
0★ (Basic), or one demoted down to 1★, is not yet publicly named and must have
its contributor handle withheld. These tests pin the single source of truth
(``gaia_cli.redaction``) and its enforcement at the resolver layer
(``LocalContext``) plus the display formatter.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from gaia_cli import redaction as R
from gaia_cli import formatting as F
from gaia_cli.localContext import LocalContext
pytestmark = [pytest.mark.integration]



# ── Core predicate ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("level,expected", [
    ("0★", True), ("1★", True), ("2★", False), ("3★", False),
    ("6★", False), (0, True), (1, True), (2, False),
    (None, True), ("", True), ("garbage", True),
])
def test_is_redacted_threshold(level, expected):
    assert R.is_redacted(level) is expected


def test_level_num_parsing():
    assert R.level_num("4★") == 4
    assert R.level_num("4") == 4
    assert R.level_num(5) == 5
    assert R.level_num(None) == 0
    assert R.level_num(True) == 0  # bool guard — never treated as rank 1


def test_redact_handle_styles():
    # Pre-named → placeholder; block form for monospace, bracket for proportional.
    assert R.redact_handle("ruvnet", "1★") == R.REDACTED_HANDLE
    assert R.redact_handle("ruvnet", "1★", block=True) == R.REDACTED_BLOCK
    # Named → passthrough.
    assert R.redact_handle("ruvnet", "4★") == "ruvnet"


def test_anon_segment_is_stable_and_handle_free():
    a = R.anon_segment("ruvnet", "1★")
    assert a.startswith("anon-")
    assert "ruvnet" not in a
    assert a == R.anon_segment("ruvnet", "1★")  # deterministic
    # Named → real handle kept (used in artifact paths).
    assert R.anon_segment("ruvnet", "4★") == "ruvnet"


# ── Display formatter ─────────────────────────────────────────────────────────

def test_format_skill_plain_redacts_below_named():
    assert F.format_skill_plain("agentdb", named_ref="ruvnet/agentdb",
                                level="1★") == f"{R.REDACTED_BLOCK}/agentdb"
    assert F.format_skill_plain("agentdb", named_ref="ruvnet/agentdb",
                                level="4★") == "ruvnet/agentdb"


def test_format_skill_colored_uses_slate_not_honor_red(monkeypatch):
    # Force color on so ANSI codes are emitted regardless of TTY.
    monkeypatch.setenv("FORCE_COLOR", "1")
    out = F.format_skill_colored("agentdb", "1★", named_ref="ruvnet/agentdb")
    assert R.REDACTED_BLOCK in out
    assert "ruvnet" not in out


# ── Resolver-layer enforcement (the choke point) ──────────────────────────────

def _ctx(level: str) -> LocalContext:
    ctx = LocalContext(username="me", named_map={"sk": "ruvnet/agentdb"})
    ctx._skill_map = {"sk": {"id": "sk", "level": level}}
    return ctx


def test_display_name_redacts_other_contributor_below_named():
    # display_name now always adds a leading slash and appends the level star.
    # Below named (<=1★): redacted block replaces contributor handle.
    # Format: "/REDACTED_BLOCK/nickname N★"
    assert _ctx("1★").display_name("sk") == f"/{R.REDACTED_BLOCK}/agentdb 1★"
    # At 3★: full contributor handle shown, with leading slash and star.
    assert _ctx("3★").display_name("sk") == "/ruvnet/agentdb 3★"
    # Verify security semantics: block present below-named, absent above.
    assert R.REDACTED_BLOCK in _ctx("1★").display_name("sk")
    assert "ruvnet" not in _ctx("1★").display_name("sk")
    assert R.REDACTED_BLOCK not in _ctx("3★").display_name("sk")


def test_named_ref_and_contributor_redacted():
    c = _ctx("1★")
    assert c.named_ref("sk") == f"{R.REDACTED_BLOCK}/agentdb"
    assert c.named_contributor("sk") == R.REDACTED_BLOCK
    assert c.is_redacted("sk") is True


def test_owner_sees_own_pre_named_skill():
    # Your own work is never redacted — you can always see it.
    # display_name now returns "/contrib/nick N★" even for own skills:
    # the contributor handle is SHOWN (not replaced by nickname-only).
    # This is the current documented behavior: "Named Slash-Skill with Star"
    # (e.g. karpathy/autoresearch 5★). The leading slash is always present.
    own = LocalContext(username="ruvnet", named_map={"sk": "ruvnet/agentdb"})
    own._skill_map = {"sk": {"id": "sk", "level": "1★"}}
    result = own.display_name("sk")
    # Own skill shows full handle (not redacted); format is /contrib/nick N★
    assert result == "/ruvnet/agentdb 1★"
    # No redaction block for own skill
    assert R.REDACTED_BLOCK not in result
    # Without star
    assert own.display_name("sk", include_star=False) == "/ruvnet/agentdb"


# ── Integration: the invariant validator runs clean on the built tree ─────────

def test_redaction_validator_passes_on_repo():
    repo = Path(__file__).resolve().parent.parent
    script = repo / "scripts" / "validate_redaction.py"
    if not script.exists():
        pytest.skip("validate_redaction.py not present")
    result = subprocess.run([sys.executable, str(script)], cwd=str(repo),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
