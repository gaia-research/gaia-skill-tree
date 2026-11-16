"""Shared bounded semantic contract for active trust and evidence-policy guidance.

The authority map and active trust/evidence-policy surfaces are explicit inputs.
Historical archives, handovers, retrospectives, and unlisted generated/archive
documents are intentionally outside the retired-claim scan; explicitly listed
.claude mirrors and schema/API metadata surfaces are included.
"""

from __future__ import annotations

import json
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

EVIDENCE_POLICY_SURFACES = (
    *TRUST_SURFACES,
    ".agents/skills/ev-scout/SKILL.md",
    ".agents/skills/ev-discovery/SKILL.md",
    ".agents/skills/ev-collection/SKILL.md",
    ".agents/skills/ev-adversarial-audit/SKILL.md",
    ".agents/skills/ev-pipeline/SKILL.md",
    ".agents/skills/gaia-ingest/SKILL.md",
    ".agents/skills/gaia-ingest-batch/SKILL.md",
    ".claude/skills/ev-scout/SKILL.md",
    ".claude/skills/ev-discovery/SKILL.md",
    ".claude/skills/ev-collection/SKILL.md",
    ".claude/skills/ev-adversarial-audit/SKILL.md",
    ".claude/skills/ev-pipeline/SKILL.md",
    ".claude/skills/gaia-ingest/SKILL.md",
    ".claude/skills/gaia-ingest-batch/SKILL.md",
    "docs/agents/curation-principles.md",
    "evidence/README.md",
    "CLAUDE.md",
    "META.md",
    "GOVERNANCE.md",
    "docs/architecture/ecosystem-intelligence.md",
    "founder/steward/routines/trust-evidence-gap.md",
    "docs/en/evidence-classes.html",
    "docs/codex/trust-methodology.html",
    "docs/trust/leaderboard/leaderboard.js",
)

EVIDENCE_POLICY_CLAIM_ONLY_SURFACES = (
    "docs/js/tm-config.js",
)

EVIDENCE_META_JSON_SURFACES = (
    "registry/schema/meta.json",
    "src/gaia_cli/data/registry/schema/meta.json",
    "docs/schema/meta.json",
)

EVIDENCE_TYPES_API_SURFACE = "docs/api/v1/evidence-types.json"
HISTORICAL_G7_RFC = "founder/handovers/done/G7_TRUST_TAXONOMY_RFC.md"
EVIDENCE_POLICY_FIXTURE = "tests/fixtures/evidence_policy_cases.json"
REQUIRED_FIXTURE_CASE_IDS = (
    "eligible-first-party-video",
    "recent-third-party-video",
    "unrelated-first-party-video-rejected-relevance",
    "below-view-floor-video-scores-zero",
    "first-party-proxy-containment-rejected",
    "same-creator-plateau-and-same-type-url-dedup",
    "suite-component-cap-no-synthetic-self-attestation",
)

# Keep these finite retired-claim predicates aligned with the authority-map
# agreement tests. They are not numeric heuristics over arbitrary repository text.
BANNED_PATTERNS = {
    "skill-count divisor": re.compile(
        r"(?:/\s*(?:min\(\s*)?(?:skill_count_in_repo|skillCountInRepo)|"
        r"\b(?:skill_count_in_repo|skillCountInRepo)\b.{0,35}\bdivisor\b|"
        r"\b(?:skill_count_in_repo|skillCountInRepo)\b.{0,35}\bdivides?\s+(?:the\s+)?(?:score|contribution)\b)",
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
    "social-signal first-party ban": re.compile(r"sameAsAuthor[\"']?\s*(?::|=)\s*0(?!\.)", re.I),
    "social-signal 30-day publish cooldown": re.compile(
        r"(?:publishCooldownDays[\"']?\s*(?::|=)\s*30\b|\b30-day\s+publish(?:ation)?\s+(?:cooldown|hold)\b)",
        re.I,
    ),
    "social-signal external creators only": re.compile(r"from\s+external\s+creators", re.I),
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
    if re.search(r"\b(?:do\s+not|don't|never|no|not|without|retired|superseded)\b[^.!?;\n]{0,60}$", before, re.I):
        return True

    return bool(
        re.search(
            r"\b(?:is|was|has been|are|were|have been)\s+(?:explicitly\s+)?(?:retired|obsolete|deprecated|superseded)\b",
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


def _extract_evidence_types(data: object, relative: str) -> list[dict[str, object]]:
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {relative}")
    if relative == EVIDENCE_TYPES_API_SURFACE:
        types = data.get("types")
    else:
        evidence = data.get("evidence")
        types = evidence.get("types") if isinstance(evidence, dict) else None
    if not isinstance(types, list):
        raise ValueError(f"missing evidence types array in {relative}")
    return [entry for entry in types if isinstance(entry, dict)]


def check_evidence_policy(repo_root: Path) -> list[dict[str, str]]:
    """Verify #2473 evidence-policy agreement across schema/API metadata and active surfaces.

    Historical archives under founder/handovers/done/ are excluded from the
    retired-claim scan; G7_TRUST_TAXONOMY_RFC.md is checked only for its top
    supersession banner while preserving its historical §2.11 body.
    """
    violations = list(check_trust_guidance(repo_root))

    authority_map = _read_required(repo_root, AUTHORITY_MAP)
    for heading in ("## Social versus proxy eligibility", "## Freshness mechanisms"):
        if heading not in authority_map:
            violations.append({
                "source": AUTHORITY_MAP,
                "rule": "authority-map-section",
                "detail": f"authority map missing required section {heading!r}",
            })

    extra_surfaces = [s for s in EVIDENCE_POLICY_SURFACES if s not in TRUST_SURFACES]
    for relative in extra_surfaces:
        text = _read_required(repo_root, relative)
        if MAP_LINK not in text:
            violations.append({
                "source": relative,
                "rule": "trust-authority-map-link",
                "detail": f"active evidence-policy surface must reference {MAP_LINK}",
            })
        for claim in bannedClaims(text):
            violations.append({
                "source": relative,
                "rule": "retired-trust-claim",
                "detail": f"active evidence-policy surface contains retired claim: {claim}",
            })

    for relative in EVIDENCE_POLICY_CLAIM_ONLY_SURFACES:
        text = _read_required(repo_root, relative)
        for claim in bannedClaims(text):
            violations.append({
                "source": relative,
                "rule": "retired-trust-claim",
                "detail": f"active evidence-policy surface contains retired claim: {claim}",
            })

    rfc_text = _read_required(repo_root, HISTORICAL_G7_RFC)
    rfc_banner = rfc_text.split("## The Gate", 1)[0]
    if "#2473" not in rfc_banner or MAP_LINK not in rfc_banner:
        violations.append({
            "source": HISTORICAL_G7_RFC,
            "rule": "historical-rfc-supersession-banner",
            "detail": f"historical RFC must carry a top supersession banner linking #2473 and {MAP_LINK}",
        })

    json_surfaces = (*EVIDENCE_META_JSON_SURFACES, EVIDENCE_TYPES_API_SURFACE)
    canonical_types: list[dict[str, object]] | None = None
    for relative in json_surfaces:
        raw_text = _read_required(repo_root, relative)
        data = json.loads(raw_text)
        types = _extract_evidence_types(data, relative)
        if canonical_types is None:
            canonical_types = types
        elif types != canonical_types:
            violations.append({
                "source": relative,
                "rule": "evidence-types-parity",
                "detail": f"{relative} evidence types differ from {EVIDENCE_META_JSON_SURFACES[0]}",
            })

        by_id = {str(entry.get("id")): entry for entry in types}
        social = by_id.get("social-signal")
        if not isinstance(social, dict):
            violations.append({
                "source": relative,
                "rule": "social-signal-definition",
                "detail": "missing social-signal entry in evidence types",
            })
            continue

        creator_mults = social.get("creatorMultipliers")
        same_as_author = creator_mults.get("sameAsAuthor") if isinstance(creator_mults, dict) else None
        if same_as_author != 1.0:
            violations.append({
                "source": relative,
                "rule": "social-signal-same-as-author",
                "detail": f"expected social-signal creatorMultipliers.sameAsAuthor == 1.0, got {same_as_author!r}",
            })

        cooldown = social.get("publishCooldownDays")
        if cooldown != 0:
            violations.append({
                "source": relative,
                "rule": "social-signal-publish-cooldown",
                "detail": f"expected social-signal publishCooldownDays == 0, got {cooldown!r}",
            })

        for field_name in ("description", "notes"):
            field_val = str(social.get(field_name) or "")
            for claim in bannedClaims(field_val):
                violations.append({
                    "source": relative,
                    "rule": "retired-trust-claim",
                    "detail": f"social-signal.{field_name} contains retired claim: {claim}",
                })

    fixture_path = repo_root / EVIDENCE_POLICY_FIXTURE
    if fixture_path.is_file():
        fixture_data = json.loads(_read_required(repo_root, EVIDENCE_POLICY_FIXTURE))
        cases = fixture_data.get("cases") if isinstance(fixture_data, dict) else None
        case_ids = {
            str(item.get("id"))
            for item in (cases or [])
            if isinstance(item, dict) and item.get("id")
        }
        missing_cases = [cid for cid in REQUIRED_FIXTURE_CASE_IDS if cid not in case_ids]
        if missing_cases:
            violations.append({
                "source": EVIDENCE_POLICY_FIXTURE,
                "rule": "evidence-policy-fixture-coverage",
                "detail": f"missing required evidence policy fixture case(s): {missing_cases}",
            })

    return violations
