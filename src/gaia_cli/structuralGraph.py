"""Neutral structural graph traversal — the composition edges of the registry.

Yggdrasil III draws a hard line between *trust* (how much corroborating
evidence supports an implementation) and *structure* (how much distinct
capability a node composes).  ``trustMagnitude.py`` owns the first; this
module owns the raw edges the second is derived from, so neither Trust
Magnitude nor the Apex predicates become the de-facto owner of the Fusion
Score graph (``fusionScore.py``).

Nothing in this module reads Evidence Grade, Overall Trust Grade, Trust
Magnitude, repository stars, rank, level, or source freshness.  A structural
edge is an edge whether the node it points at is ungraded or Platinum.

Three edge sources, in canonical precedence order:

1. ``prerequisites`` on the starless generic node — reached through a Named
   Skill's ``genericSkillRef``, or read directly when the node *is* generic.
2. ``suiteComponents`` on the skill itself.
3. ``fusion-recipe`` evidence-row ``origins`` — a compatibility fallback only.
   ``fusion-recipe`` remains structural provenance worth ``0`` Trust
   Magnitude (Yggdrasil III); reading it here neither mints nor implies
   evidence.  Sources 1 and 2 are canonical, so an origin already reachable
   through them contributes nothing extra.

``role: variant`` entries are excluded at every source.  Under RFC §C-2 a
variant is a reclassified or redirected duplicate of another node, so
counting it would double-count the same capability.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

# Evidence-row type that carries structural origins. Kept as a literal here
# rather than imported from trustMagnitude so this module has no dependency
# on the trust lane.
FUSION_RECIPE_TYPE = "fusion-recipe"

def _rowIsFusionRecipe(row: Any) -> bool:
    """Exact-match the canonical row type.

    Deliberately NOT alias-tolerant: ``trustMagnitude._typeOf`` aliases only
    ``repo`` -> ``repo-own``, so a bare ``fusion`` row has never been read as
    structural anywhere. Widening it here would change Trust Magnitude
    behaviour through the shared walkers below.
    """
    if not isinstance(row, dict):
        return False
    return row.get("type") == FUSION_RECIPE_TYPE


def _originIdAndRole(entry: Any) -> tuple[Optional[str], Optional[str]]:
    """Split an origin entry into (id, inline role).

    Entries are either bare id strings or dicts carrying ``id``/``skillId``
    and an optional inline ``role`` hint.
    """
    if isinstance(entry, dict):
        return (entry.get("id") or entry.get("skillId")), entry.get("role")
    if isinstance(entry, str):
        return entry, None
    return None, None


def lookupNode(
    skillId: str,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> dict:
    """Resolve a skill ID against the named map first, then the generic map.

    Named IDs (``contributor/slug``) and generic IDs share one namespace on
    the structural graph: ``suiteComponents`` routinely names the former and
    ``prerequisites`` the latter. Returns ``{}`` when unresolvable — an
    unknown ID is still a countable structural edge, it simply exposes no
    onward edges of its own.
    """
    if namedSkillMap:
        node = namedSkillMap.get(skillId)
        if node:
            return node
    if genericSkillMap:
        node = genericSkillMap.get(skillId)
        if node:
            return node
    return {}


def isVariant(
    skillId: str,
    inlineRole: Optional[str] = None,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> bool:
    """True when the edge points at an RFC §C-2 ``role: variant`` node.

    An inline ``role`` on the origin entry wins; otherwise the role is read
    from the resolved node.
    """
    if inlineRole is not None:
        return inlineRole == "variant"
    node = lookupNode(skillId, genericSkillMap, namedSkillMap)
    return node.get("role") == "variant"


def prerequisiteIds(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
) -> list[str]:
    """Canonical source 1 — the starless generic node's ``prerequisites``.

    A Named Skill inherits its generic recipe through ``genericSkillRef``; a
    generic node reads its own field. Order is preserved.
    """
    genericRef = skill.get("genericSkillRef")
    if genericRef:
        source = (genericSkillMap or {}).get(genericRef) or {}
    else:
        source = skill
    out: list[str] = []
    for entry in source.get("prerequisites") or []:
        originId, _role = _originIdAndRole(entry)
        if originId:
            out.append(originId)
    return out


def suiteComponentIds(skill: dict) -> list[str]:
    """Canonical source 2 — the skill's own ``suiteComponents``. Order preserved."""
    out: list[str] = []
    for entry in skill.get("suiteComponents") or []:
        originId, _role = _originIdAndRole(entry)
        if originId:
            out.append(originId)
    return out


def fusionRecipeOriginIds(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> list[str]:
    """Compatibility source 3 — ``fusion-recipe`` origins, variants excluded.

    Order preserved; duplicates are NOT collapsed, matching the historical
    ``trustMagnitude._fusionOriginIds`` contract that callers rely on.
    """
    out: list[str] = []
    for row in skill.get("evidence") or []:
        if not _rowIsFusionRecipe(row):
            continue
        for entry in row.get("origins") or []:
            originId, inlineRole = _originIdAndRole(entry)
            if not originId:
                continue
            if isVariant(originId, inlineRole, genericSkillMap, namedSkillMap):
                continue
            out.append(originId)
    return out


def dedupePreservingOrder(ids: Iterable[str]) -> list[str]:
    """Collapse repeats while keeping first-seen order (byte-stable output)."""
    seen: set[str] = set()
    out: list[str] = []
    for value in ids:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def directStructuralEdges(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
    includePrerequisites: bool = True,
    includeSuiteComponents: bool = True,
    includeFusionRecipe: bool = True,
) -> list[str]:
    """Return this skill's depth-1 structural edges, deduplicated.

    Sources are unioned in canonical precedence order (prerequisites, then
    suiteComponents, then fusion-recipe origins), so a fusion-recipe origin
    already reachable through a canonical field adds nothing. ``role:
    variant`` targets are dropped from every source, and the skill's own ID
    never appears in its own edge list.

    The three ``include*`` switches exist so a caller that owns a narrower
    contract (the Apex depth walkers, which predate the canonical
    ``prerequisites`` source and must not silently widen) can select exactly
    the sources it has always read.
    """
    skillId = skill.get("id") or skill.get("skillId")
    candidates: list[tuple[str, Optional[str]]] = []

    if includePrerequisites:
        candidates.extend((cid, None) for cid in prerequisiteIds(skill, genericSkillMap))
    if includeSuiteComponents:
        candidates.extend((cid, None) for cid in suiteComponentIds(skill))
    if includeFusionRecipe:
        for row in skill.get("evidence") or []:
            if not _rowIsFusionRecipe(row):
                continue
            for entry in row.get("origins") or []:
                originId, inlineRole = _originIdAndRole(entry)
                if originId:
                    candidates.append((originId, inlineRole))

    out: list[str] = []
    seen: set[str] = set()
    for originId, inlineRole in candidates:
        if originId in seen or (skillId and originId == skillId):
            continue
        if isVariant(originId, inlineRole, genericSkillMap, namedSkillMap):
            continue
        seen.add(originId)
        out.append(originId)
    return out
