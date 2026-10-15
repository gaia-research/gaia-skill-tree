"""Shared bounded semantic contract for active trust guidance.

The authority map and active trust surfaces are explicit inputs. Historical
archives, handovers, retrospectives, and unlisted generated/archive documents
are intentionally outside this semantic scan; explicitly listed .claude mirrors
are included.
"""

from __future__ import annotations

import re
from pathlib import Path

AUTHORITY_MAP = "docs/agents/curation-authority-map.md"
MAP_LINK = "curation-authority-map.md"
MAX_INPUT_BYTES = 1024 * 1024
TRUST_SURFACES = (
    ".agents/skills/trust-appraise-all/SKILL.md",
    ".agents/skills/gaia-tm-inspect/SKILL.md",
    ".agents/skills/trust-appraise/SKILL.md",
    ".agents/skills/trust-methodology-consult/SKILL.md",
    ".claude/skills/trust-appraise-all/SKILL.md",
    ".claude/skills/gaia-tm-inspect/SKILL.md",
    ".claude/skills/trust-appraise/SKILL.md",
    ".claude/skills/trust-methodology-consult/SKILL.md",
    "docs/agents/curation-guidelines.md",
)

# Keep these finite retired-claim predicates aligned with the authority-map
# agreement tests. They are not numeric heuristics over arbitrary repository text.
BANNED_PATTERNS = {
    "skill-count divisor": re.compile(
        r"(?:/\s*(?:min\(\s*)?skill_count_in_repo|"
        r"\bskill_count_in_repo\b.{0,35}\bdivisor\b|"
        r"\bskill_count_in_repo\b.{0,35}\bdivides?\s+(?:the\s+)?(?:score|contribution)\b)",
        re.I,
    ),
    "mothership discount": re.compile(r"mothership\s+discount", re.I),
    "linear stars formula": re.compile(r"stars\s*/\s*1000"),
    "cross-type same-URL collapse": re.compile(
        r"`github-stars-own`\s+and\s+`repo-own`\s+pointing\s+to\s+the\s+same\s+URL\s*→\s*deduped", re.I
    ),
    "4-star at grade B": re.compile(r"(?:≥|>=)\s*B\s*\(\s*TM\s*(?:≥|>=)\s*50\s*\)"),
    "A merely the norm at 4-star": re.compile(r"norm for 4★"),
    "write-back helper usage": re.compile(r"python3?\s+\S*recompute_one_tm\.py"),
    "partial total called final": re.compile(r"inheritance disallowed(?!\")", re.I),
}


def bannedClaims(text: str) -> list[str]:
    """Return names of finite, specifically retired trust claims in text."""
    claims: list[str] = []
    for name, pattern in BANNED_PATTERNS.items():
        matches = pattern.finditer(text)
        if any(
            not _is_retired_warning_context(text, match.start(), match.end())
            for match in matches
        ):
            claims.append(name)
    return claims


def _is_retired_warning_context(text: str, start: int, end: int) -> bool:
    """Ignore an explicit denial or retirement warning in the same clause."""
    boundaries = ("\n", ".", "!", "?", ";")
    clause_start = max(text.rfind(mark, 0, start) for mark in boundaries) + 1
    clause_end = min(
        (position for mark in boundaries if (position := text.find(mark, end)) != -1),
        default=len(text),
    )
    before = text[clause_start:start].rstrip("`'\" \t")
    after = text[end:clause_end].lstrip("`'\" \t")

    # Denials must directly govern the match; quotes and code ticks alone are
    # not evidence. Clause boundaries prevent unrelated prose from exempting it.
    if re.search(r"\b(?:do\s+not|don't|never|no|not|without)\b[^.!?;\n]{0,40}$", before, re.I):
        return True

    return bool(
        re.search(
            r"\b(?:is|was|has been|are|were|have been)\s+(?:explicitly\s+)?(?:retired|obsolete|deprecated)\b",
            after,
            re.I,
        )
    )


def _read_required(repo_root: Path, relative: str) -> str:
    path = repo_root / relative
    try:
        with path.open("rb") as stream:
            content = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise OSError(f"required trust guidance input unavailable: {relative}: {exc}") from exc
    if len(content) > MAX_INPUT_BYTES:
        raise ValueError(f"required trust guidance input exceeds safety limit (possibly truncated): {relative}")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"required trust guidance input is not UTF-8: {relative}") from exc
    if not text.strip():
        raise ValueError(f"required trust guidance input is empty or whitespace-only (possibly truncated): {relative}")
    return text


def check_trust_guidance(repo_root: Path) -> list[dict[str, str]]:
    """Check only the active trust surfaces and map; unavailable inputs raise.

    The authority map's retired-claims section is intentionally excluded from
    matching: it documents the exact obsolete language as a warning. Active
    content before that section and the explicitly listed guidance surfaces are
    checked. No archive traversal or stylistic/numeric inference is performed.
    """
    authority_map = _read_required(repo_root, AUTHORITY_MAP)
    active_map = authority_map.split("## Banned claims", 1)[0]
    inputs = [(AUTHORITY_MAP, active_map)]
    inputs.extend((relative, _read_required(repo_root, relative)) for relative in TRUST_SURFACES)

    violations: list[dict[str, str]] = []
    for relative, text in inputs:
        if relative != AUTHORITY_MAP and MAP_LINK not in text:
            violations.append({
                "source": relative,
                "rule": "trust-authority-map-link",
                "detail": f"active trust guidance must reference {MAP_LINK}",
            })
        for claim in bannedClaims(text):
            violations.append({
                "source": relative,
                "rule": "retired-trust-claim",
                "detail": f"active trust guidance contains retired claim: {claim}",
            })
    return violations
