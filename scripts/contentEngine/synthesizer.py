#!/usr/bin/env python3
"""L1 → L2 → L3 salvage harness for the Content Engine.

Per `founder/handovers/WORKFLOW_PATTERNS.md` §2 (2026-06-20 lessons):

  L1 — primary synthesizer (Opus). Full context. Best quality.
  L2 — chunked synthesizer (Sonnet). 2-pass, section-halves. Cheaper + faster.
  L3 — mechanical assembly (pure Python). Cannot fail on valid data.

L1 and L2 are gated behind two conditions:
  - GAIA_CONTENT_ENGINE_LLM == '1'
  - ANTHROPIC_API_KEY set

When either is missing, the layer skips silently to the next. The MVP always
falls through to L3, which is a deterministic transform. This keeps the
default path free of network calls, LLM cost, and non-determinism — the
cron/CI path is 100% reproducible.

The wire between run() and this module is `synthesize(report) -> (report, layerFlag)`.
Callers write the returned `layerFlag` into the canonical JSON's `salvageLayer`
field so post-mortems can see which layer produced any given report.
"""

from __future__ import annotations

import os
from typing import Any


def _llmEnabled() -> bool:
    """LLM synthesis requires both an env flag AND an API key."""
    if os.environ.get("GAIA_CONTENT_ENGINE_LLM", "").strip() != "1":
        return False
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return False
    return True


def synthesizeL1(report: dict, model: str = "opus") -> dict | None:
    """Primary synthesizer — Opus, full report context.

    Returns None when the LLM path is disabled (default). When enabled, this
    would call Anthropic's Messages API with the report dict as JSON context
    and ask for a polished narrative overlay (headline, one-paragraph lede,
    per-section summaries) that gets merged back into the report dict.

    Implementation is deferred to a follow-up PR — MVP ships with the L3
    mechanical path only, per Sprint D §Content Engine §Publish gate.
    """
    if not _llmEnabled():
        return None
    # LLM path is not yet wired — reachable only in a controlled follow-up.
    raise NotImplementedError(
        "L1 (Opus) synthesizer path is guarded; wire the Anthropic call in "
        "a follow-up PR before flipping GAIA_CONTENT_ENGINE_LLM=1."
    )


def synthesizeL2(report: dict, model: str = "sonnet") -> dict | None:
    """Chunked synthesizer — Sonnet, per-section 2-pass. See L1 note."""
    if not _llmEnabled():
        return None
    raise NotImplementedError(
        "L2 (Sonnet) synthesizer path is guarded; wire the Anthropic call in "
        "a follow-up PR before flipping GAIA_CONTENT_ENGINE_LLM=1."
    )


def synthesizeL3Mechanical(report: dict) -> dict:
    """Pure-Python mechanical assembly. Deterministic; no LLM.

    Guarantees:
      - Marks the report with `salvageLayer='L3'`.
      - Preserves the input shape exactly (no field drops).
      - Raises ValueError iff EVERY section has zero entries — callers must
        catch this and emit a stub `L3-empty` report rather than shipping a
        vacuous artefact.
    """
    sections = report.get("sections", {}) or {}
    trending = sections.get("trending", {}).get("entries", []) or []
    ascended = sections.get("ascended", {}).get("entries", []) or []
    contested = sections.get("contested", {}).get("entries", []) or []

    if not trending and not ascended and not contested:
        raise ValueError(
            "empty sections — all three of trending, ascended, and contested "
            "are empty. Refusing to emit a report with no content."
        )

    # L3 is a passthrough on valid data; the report dict is already assembled.
    # We tag the layer and return.
    out = dict(report)
    out["salvageLayer"] = "L3"
    return out


def synthesize(report: dict) -> tuple[dict, str]:
    """Run L1 → L2 → L3, returning (report, layerFlag).

    Layer flag is written into the canonical JSON's `salvageLayer` field so
    a post-mortem can identify which layer produced any given report.

    Raises ValueError iff L3 refuses because all sections are empty. Callers
    (generate_weekly_report.run) MUST catch and emit an `L3-empty` stub.
    """
    # L1 first — will return None unless env-gated.
    try:
        result = synthesizeL1(report)
        if result is not None:
            return result, "L1"
    except Exception:  # pragma: no cover — future LLM path
        # Silent fall-through per WORKFLOW_PATTERNS.md §2 L1 catch block.
        pass

    # L2 next.
    try:
        result = synthesizeL2(report)
        if result is not None:
            return result, "L2"
    except Exception:  # pragma: no cover
        pass

    # L3 — mechanical, no network, can only fail with ValueError on empty input.
    result = synthesizeL3Mechanical(report)
    return result, "L3"
