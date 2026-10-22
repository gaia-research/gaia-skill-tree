"""Describe repository values without echoing them.

A sensor reads text it does not control: timestamps, schema instances, manifest
fields, driver input. Anything it prints lands in ``.gaia/steward/debt.json``,
in receipts and on stdout, so a finding must never carry the offending value.
It carries the value's type, its length and a short ``sha256`` fingerprint
instead: enough to tell two values apart and to find the line in the source,
nothing that can be replayed.

``scrub`` is the second line of defence for text that is echoed on purpose
(identifiers, test node ids, action references): credential-shaped substrings
are replaced by their fingerprint, whatever surrounds them.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

FINGERPRINT_LENGTH = 12

# (pattern name, compiled regex). Each regex is anchored against alphanumeric
# neighbours so a run inside a longer base64 blob does not match.
CREDENTIAL_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("aws-access-key-id", re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])")),
    ("github-token", re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36,255}(?![A-Za-z0-9])")),
    ("github-fine-grained-token", re.compile(r"(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{82,}")),
    ("anthropic-api-key", re.compile(r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-api-key", re.compile(r"(?<![A-Za-z0-9_-])sk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{40,}")),
    ("slack-token", re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private-key-block", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("google-api-key", re.compile(r"(?<![A-Za-z0-9_-])AIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])")),
    # B7 M3: the shapes the round-2 verifier found unscrubbed. Each is fail-closed: over-matching is acceptable.
    ("huggingface-token", re.compile(r"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{30,}(?![A-Za-z0-9])")),
    ("npm-token", re.compile(r"(?<![A-Za-z0-9])npm_[A-Za-z0-9]{30,}(?![A-Za-z0-9])")),
    ("gitlab-token", re.compile(r"(?<![A-Za-z0-9])glpat-[A-Za-z0-9_-]{20,}")),
    ("jwt", re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])")),
    ("bearer-token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")),
    ("credential-assignment", re.compile(
        r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\\?[\"']?\s*[=:]\s*\\?[\"']?"
        r"(?![A-Za-z_][A-Za-z0-9_]*[.\[(])[^\s\\\"',;&\[\]()]{6,}")),
    # A 40-character base64 string next to an aws or secret keyword (the AWS secret access key shape).
    ("aws-secret-access-key", re.compile(
        r"(?i:aws|secret)[^\n]{0,40}?(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])")),
    ("aws-secret-access-key", re.compile(
        r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])[^\n]{0,40}?(?i:aws|secret)")),
)


def fingerprint(value: Any) -> str:
    """Return the first 12 hex digits of the sha256 of ``value``'s text."""

    text = value if isinstance(value, str) else repr(value)
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:FINGERPRINT_LENGTH]


def describe_value(value: Any) -> str:
    """Return ``<type length=N sha256=…>`` for a value, never the value itself."""

    if isinstance(value, (str, bytes, bytearray, list, tuple, dict, set, frozenset)):
        length = len(value)
    else:
        length = len(repr(value))
    return f"<{type(value).__name__} length={length} sha256={fingerprint(value)}>"


def safe_token(value: Any, pattern: "re.Pattern[str]") -> str:
    """Return ``value`` when it is a string fully matching ``pattern``, else its description.

    For fields with a known closed shape (a version, a commit id, an
    advisory id): a conforming value is structure and is shown, anything else
    is a value of unknown content and is only described.
    """

    if isinstance(value, str) and pattern.fullmatch(value):
        return value
    return describe_value(value)


def scrub(text: str) -> str:
    """Replace credential-shaped substrings of ``text`` with their fingerprint."""

    scrubbed = text
    for name, pattern in CREDENTIAL_PATTERNS:
        scrubbed = pattern.sub(
            lambda match, label=name: f"<{label} sha256={fingerprint(match.group(0))}>", scrubbed
        )
    return scrubbed
