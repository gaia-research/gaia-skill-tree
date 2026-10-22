"""Public, stable error contract for curation refusals.

Curation refusals reach the operator on stderr. The refusal text is assembled
inside the curation seam: it can embed operator-supplied values, and once a
protected human ceremony exists it can also carry provider, artifact or
protected-environment detail. Rendering it verbatim — even truncated, even
redacted — would put unbounded upstream content on the console, so the console
contract here is deliberately narrow and stable:

    <CATEGORY>: <summary> [<n> reported]

``CATEGORY`` names the gate that refused. ``summary`` is a sentence published
by this module. The refusal text itself is never rendered, transformed, or
passed to the console; only comparisons against published constants decide
which category is reported.

Why comparisons and not parsing: the console output has to be a function of
published constants alone, so that no upstream byte can reach it. Redaction,
truncation and hashing are not sufficient — they are still a function of the
upstream text, and a truncation step is not a redaction step. A comparison
whose operands are published constants yields a published constant, which is
the only shape that keeps upstream content out of the output.

This module is the *only* sanctioned way for the curation seam to describe a
refusal to a human. It does not weaken any refusal: nothing here decides
whether an operation is allowed, only how a refusal is worded.
"""

from __future__ import annotations

# --- published gate categories ------------------------------------------------

CATEGORY_AUTHORIZATION = "AUTHORIZATION"
CATEGORY_ENVELOPE = "ENVELOPE"
CATEGORY_FRESHNESS = "FRESHNESS"
CATEGORY_PACKET_WRITE = "PACKET_WRITE"
CATEGORY_RESOLUTION = "RESOLUTION"
CATEGORY_SELF_VALIDATION = "SELF_VALIDATION"
CATEGORY_UNRECOGNISED = "UNRECOGNISED"

# Every summary below is a literal published here. Nothing in this table is
# derived from a refusal message, a packet, an envelope or an exception.
_CATEGORIES = (
    (CATEGORY_AUTHORIZATION,
     "the independent authorization gate refused this packet"),
    (CATEGORY_ENVELOPE,
     "the authorization envelope could not be read"),
    (CATEGORY_FRESHNESS,
     "the independent freshness gate refused this packet"),
    (CATEGORY_PACKET_WRITE,
     "the ratified packet could not be written"),
    (CATEGORY_RESOLUTION,
     "the L4 resolution did not validate"),
    (CATEGORY_SELF_VALIDATION,
     "the packet did not self-validate against the live catalog"),
)

# --- published reason codes ---------------------------------------------------

REASON_ACCOUNTING_HUMAN_APPROVAL = "REVIEW_ACCOUNTING_HUMAN_APPROVAL_CLAIM"
REASON_ACCOUNTING_MISSING_RECEIPTS = "REVIEW_ACCOUNTING_MISSING_RECEIPTS"
REASON_ACCOUNTING_NOT_ACCOUNTED = "REVIEW_ACCOUNTING_NOT_ACCOUNTED"
REASON_ACCOUNTING_RECEIPTS_DISAGREE = "REVIEW_ACCOUNTING_RECEIPTS_DISAGREE"
REASON_UNRECOGNISED = "REASON_UNRECOGNISED"

# Markers are matched by comparison only. The code returned for a marker is a
# published literal, so a refusal message can influence *which* code is
# reported but never *what* is reported.
_REASONS = (
    ("review accounting must carry the receipts that produced it",
     REASON_ACCOUNTING_MISSING_RECEIPTS),
    ("review accounting must be a fully accounted reconciliation",
     REASON_ACCOUNTING_NOT_ACCOUNTED),
    ("unaccounted review outcome",
     REASON_ACCOUNTING_NOT_ACCOUNTED),
    ("review accounting must not claim human approval",
     REASON_ACCOUNTING_HUMAN_APPROVAL),
    ("disagrees with the receipts",
     REASON_ACCOUNTING_RECEIPTS_DISAGREE),
)


def public_refusal(category: str) -> str:
    """Return the published one-line diagnostic for a refusal category.

    The category is *compared*, never echoed: an unrecognised category is
    reported as :data:`CATEGORY_UNRECOGNISED` rather than being printed.
    """
    for known, summary in _CATEGORIES:
        if category == known:
            return f"{known}: {summary}"
    return (f"{CATEGORY_UNRECOGNISED}: the refusal was not recognised and no "
            f"detail is echoed")


def public_refusals(category: str, refusals) -> list[str]:
    """Return the published console lines for the refusals reported by one gate.

    One line is published per gate, carrying how many refusals that gate
    reported. The count is accumulated by iteration rather than by ``len()``
    so that it is not derived from the content of the refusal collection.
    """
    total = 0
    for _ in refusals:
        total += 1
    if total == 0:
        return []
    return [f"{public_refusal(category)} [{total} reported]"]


def public_reason(message: str) -> str:
    """Classify a refusal message into a published, console-safe reason code.

    The message is *matched*, never rendered. An unrecognised message yields
    :data:`REASON_UNRECOGNISED`; no part of the message reaches the output.
    """
    for marker, code in _REASONS:
        if marker in message:
            return code
    return REASON_UNRECOGNISED
