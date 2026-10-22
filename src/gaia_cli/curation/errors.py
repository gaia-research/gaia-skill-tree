"""Public, stable error contract for curation refusals.

Curation refusals reach the operator on stderr. The refusal text is assembled
inside the curation seam: it can embed operator-supplied values, and once a
protected human ceremony exists it can also carry provider, artifact or
protected-environment detail. Rendering it verbatim — even truncated, even
redacted — would put unbounded upstream content on the console, so the console
contract here is deliberately narrow and stable:

    <CATEGORY>: <published summary or published refusal> [<n> withheld]

``CATEGORY`` names the gate that refused. The remainder is either a *published
refusal* — a constant this codebase owns and the operator's contract — or a
sentence published by this module. Refusal text that is not published is
withheld and reported only as a count.

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

import re

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

# --- published refusals --------------------------------------------------------

#: The fail-closed refusal of the protected authorization seam. It is a
#: constant this codebase owns, it is the operator's contract, and it is the
#: only refusal the production verifier can currently emit. It is published
#: here so that it can be echoed without echoing anything upstream.
REFUSAL_L4_PENDING = (
    "independent protected human authorization is not configured; "
    "L4 remains pending"
)

#: Refusals this codebase publishes as constants and may therefore echo.
_PUBLISHED_REFUSALS = (
    REFUSAL_L4_PENDING,
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

# --- console tokens ------------------------------------------------------------

#: A console token: an uppercase identifier and nothing else.
SAFE_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

#: Printed in place of anything that is not a safe console token.
DETAIL_WITHHELD = "DETAIL_WITHHELD"

#: Tokens published for classifying a set of refusals.
TOKEN_L4_PENDING = "AUTHORIZATION_L4_PENDING"
TOKEN_REFUSAL_UNRECOGNISED = "REFUSAL_UNRECOGNISED"


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


def public_refusal_lines(raws, category: str) -> list[str]:
    """Return the console-safe lines describing the refusals reported by a gate.

    A refusal that is exactly a *published* refusal is echoed, because a
    published refusal is this codebase's own constant and is the operator's
    contract. Every other refusal is withheld and reported only as the gate's
    category and a count, because its text can embed unbounded upstream
    content.
    """
    echoed: list[str] = []
    withheld = 0
    for raw in raws:
        published = _published_refusal(raw)
        if published is None:
            withheld += 1
        else:
            echoed.append(f"{CATEGORY_AUTHORIZATION}: {published}")
    lines = list(echoed)
    if withheld:
        lines.append(f"{public_refusal(category)} [{withheld} withheld]")
    return lines


def classify_refusals(raws) -> str:
    """Classify a set of refusals into a published, console-safe token.

    Used by the verification scripts, whose only dynamic console output is a
    token from this vocabulary.
    """
    for raw in raws:
        if raw == REFUSAL_L4_PENDING:
            return TOKEN_L4_PENDING
    return TOKEN_REFUSAL_UNRECOGNISED


def public_reason(message: str) -> str:
    """Classify a refusal message into a published, console-safe reason code.

    The message is *matched*, never rendered. An unrecognised message yields
    :data:`REASON_UNRECOGNISED`; no part of the message reaches the output.
    """
    for marker, code in _REASONS:
        if marker in message:
            return code
    return REASON_UNRECOGNISED


def public_detail(token: str) -> str:
    """Return ``token`` when it is a safe console token, else withhold it.

    A console token is an uppercase identifier. Anything else — a payload, a
    path, an exception rendering — is replaced rather than printed, so a
    verification script cannot leak a payload into its own output.
    """
    if SAFE_TOKEN.fullmatch(token):
        return token
    return DETAIL_WITHHELD


def _published_refusal(raw):
    """Return the published refusal equal to ``raw``, else ``None``."""
    for known in _PUBLISHED_REFUSALS:
        if raw == known:
            return known
    return None
