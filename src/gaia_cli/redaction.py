"""Universal redaction gate for pre-named (≤1★) and demoted skills.

Per ``META.md`` § 1: stars live on **named** skills only. A skill at **1★
(Awakened)** or **0★ (Basic)** is *not yet named* — it is a verified candidate
awaiting a reviewer-assigned title (2★ Named). Until that happens its
contributor handle must be withheld behind a "classified" look everywhere it
could surface.

The same rule covers **demotion**: when a skill is demoted (e.g. the §2.4
hard-reset of a 3★+ skill that loses its verified blob link) its stored
``level`` is rewritten down to ``1★``. Because this module keys purely on the
rank parsed from that stored ``level`` string, a demoted skill is redacted
automatically — no separate "demoted" flag is needed. One predicate, applied
at the single choke point below, gives both the pre-named *and* the
classified-on-demotion behaviours for free.

This module is THE single place that decides:
  (a) *whether* a handle is redacted — :func:`is_redacted`
  (b) *how* it renders as visible text — :func:`redact_handle`
  (c) *how* it renders inside a file path / URL — :func:`anon_segment`

Every CLI command, generator script, and template surface routes attribution
through here so redaction can never silently regress in a "nook or cranny".
The browser mirror lives in ``docs/js/atlas-helpers.js`` (``window.isRedacted``
/ ``window.redactHandle``); keep the two in lockstep.
"""

from __future__ import annotations

import hashlib

# ── Threshold ───────────────────────────────────────────────────────────────
# Ranks at or below this value are pre-named (or demoted) → redacted.
REDACT_AT_OR_BELOW = 1

# ── Visible-text placeholders (context-specific) ─────────────────────────────
# Monospace contexts (CLI output, markdown trees) use a solid block bar so the
# redaction reads as "classified", not "missing".
REDACTED_BLOCK = "████████"  # U+2588 × 8
# Proportional contexts (HTML, SVG, badges) use a bracketed token.
REDACTED_HANDLE = "[anonymous]"

# ── Path / URL anonymization ─────────────────────────────────────────────────
# Replaces a handle inside generated artifact paths (badges, OG cards, profile
# dirs) and constructed URLs. We hash the handle so per-contributor grouping is
# preserved (one stable directory per pre-named contributor) without leaking
# the handle itself into the path.
_ANON_PREFIX = "anon-"

# ── Color (slate, never honor-red) ───────────────────────────────────────────
# Mirrors ``--rank-0`` in docs/css/tokens.css. Honor-red (#ef4444) is reserved
# for *named* Origin contributors; a redacted handle must never wear it.
COLOR_REDACTED = (148, 163, 184)  # #94a3b8


def level_num(level) -> int:
    """Return the integer rank (0–6) parsed from a level value.

    Accepts ``"1★"``, ``"1"``, ``1``, ``None`` … anything. Non-numeric input
    floors to ``0`` (treated as pre-named, i.e. redacted) so the gate fails
    *safe* — an unknown level is hidden, never accidentally exposed.
    """
    if level is None:
        return 0
    if isinstance(level, bool):  # guard: bool is a subclass of int
        return 0
    if isinstance(level, (int, float)):
        return int(level)
    digits = "".join(c for c in str(level) if c.isdigit())
    return int(digits) if digits else 0


def is_redacted(level) -> bool:
    """True when a skill at ``level`` must have its handle withheld."""
    return level_num(level) <= REDACT_AT_OR_BELOW


def redact_handle(handle: str, level, *, block: bool = False) -> str:
    """Return the handle, or its redacted placeholder when ``level`` ≤ 1★.

    ``block=True`` selects the monospace block bar (CLI / markdown); the
    default returns the bracketed ``[anonymous]`` token for proportional
    contexts (HTML / SVG).
    """
    if not is_redacted(level):
        return handle
    return REDACTED_BLOCK if block else REDACTED_HANDLE


def anon_segment(handle: str, level) -> str:
    """Return the handle, or a stable anonymized path segment when redacted.

    Used for generated artifact directories and constructed URLs so the raw
    handle never appears in a path for a pre-named/demoted skill. The segment
    is deterministic per handle (``anon-<sha1[:8]>``) so rebuilds are stable
    and a single contributor's redacted artifacts stay grouped.
    """
    if not is_redacted(level):
        return handle
    digest = hashlib.sha1((handle or "").encode("utf-8")).hexdigest()[:8]
    return f"{_ANON_PREFIX}{digest}"
