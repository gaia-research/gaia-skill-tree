"""Fusion Score — the structural reading, independent of Trust Magnitude.

Yggdrasil III exposes two numeric readings that answer different questions:

| Reading | Question | Inputs |
|---|---|---|
| Trust Magnitude | How much corroborating evidence supports this named implementation? | positive-scoring evidence rows |
| Fusion Score | How much distinct structure does this capability compose? | canonical prerequisite / suite-component / origin structure |

Fusion Score is **not** an Evidence Type, an evidence row, a Trust Grade
ingredient, a Trust Magnitude multiplier, or a substitute for an Apex
predicate.  It is informational in V1 and gates nothing: no star, no Trust
Grade, no promotion decision reads it.

Two independence invariants hold by construction, because this module reads
the structural graph (``structuralGraph.py``) and nothing else:

- changing only evidence, stars, Trust Magnitude, or Trust Grade leaves the
  Fusion Score unchanged;
- changing only canonical structure leaves Trust Magnitude unchanged.

V1 formula (``yggdrasil-iii-v1``)::

    N  = distinct non-variant nodes in the resolved structural closure
    FS = 0                          when N = 0
    FS = 20 x N                     when 1 <= N <= 10
    FS = 200 + 20 x sqrt(N - 10)    when N > 10

The sqrt softening past 10 is inherited from the retired fusion magnitude, so
a large composition cannot run away from the scale.  Every trust-specific
modifier from that former formula — the ``1.5x`` evidence weight, the Trust
Magnitude cap, the freshness factor, the grade filter, the set bonus, the
Trust Grade threshold — is deliberately absent.  Those belonged to evidence
aggregation and would recreate exactly the coupling Yggdrasil III removed.

Persistence boundary: the registry stores the structural *inputs*, never this
derived answer.  Nothing here writes to ``registry/named/`` frontmatter or to
canonical node JSON; the score is computed in this one Python authority and
serialized only into generated projections.  Browser code consumes the
generated value — it must never carry a second copy of the formula.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from gaia_cli.structuralGraph import (
    directStructuralEdges,
    lookupNode,
    suiteComponentIds,
)

# Formula identifier. Bump when the scalar or the breakdown semantics change.
# NOT a package version, and NOT decorative cache-bust metadata — a consumer
# comparing two projections uses this to know whether the numbers are
# comparable at all.
FUSION_SCORE_VERSION = "yggdrasil-iii-v1"

# Score per distinct structural node below the softening knee.
FUSION_NODE_UNIT = 20.0

# Node count at which linear growth gives way to sqrt softening.
FUSION_SOFTENING_KNEE = 10

# Declared traversal limit. The registry is validated as a DAG, so this is a
# fail-closed backstop rather than a load-bearing tuning knob: a malformed
# graph stops at the limit instead of hanging.
FUSION_MAX_DEPTH = 8

# Anyone reading a Fusion Score for the first time is, in practice, someone
# whose Trust Magnitude just went DOWN. Under Yggdrasil II a `fusion-recipe`
# row poured its structure straight into TM; Yggdrasil III fixed that row at
# 0 TM, and the drop landed on exactly the suites and fusions that now show a
# large Fusion Score. Reporting the new number without naming that movement
# invites the one conclusion that is flatly false — that the skill was
# downgraded. Every surface that prints a Fusion Score prints this too.
YGGDRASIL_II_MIGRATION_NOTE = [
    "Why the numbers moved:",
    "  Under Yggdrasil II, fusion-recipe structure was scored INSIDE Trust",
    "  Magnitude. Yggdrasil III fixed that row at 0 TM, which is why TM fell",
    "  for suites and fusions. No evidence, star, or rank was changed. The",
    "  structure did not disappear — it is reported here, on its own.",
    "  This is not a second trust number and not new credit: it is the part",
    "  of the old Trust Magnitude that was never evidence.",
]


def fusionScalar(distinctNodes: int) -> float:
    """Apply the V1 curve to a distinct-node count. Rounded to 2 decimals.

    Rounding happens here, once, so Python, CLI text, and every JSON
    projection serialize byte-identical numbers.
    """
    if distinctNodes <= 0:
        return 0.0
    if distinctNodes <= FUSION_SOFTENING_KNEE:
        return round(FUSION_NODE_UNIT * distinctNodes, 2)
    softened = FUSION_NODE_UNIT * math.sqrt(distinctNodes - FUSION_SOFTENING_KNEE)
    return round(FUSION_NODE_UNIT * FUSION_SOFTENING_KNEE + softened, 2)


def resolveFusionStructure(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> dict[str, Any]:
    """Walk the structural closure below ``skill`` and describe what it found.

    Returns a dict with:

    - ``nodes``      — closure IDs, sorted (deterministic, dedup by ID);
    - ``direct``     — depth-1 IDs, sorted;
    - ``maxDepth``   — deepest level reached (0 when there is no structure);
    - ``nestedSuites`` — closure IDs that themselves declare ``suiteComponents``;
    - ``truncated``  — True when traversal stopped at ``FUSION_MAX_DEPTH``.

    The root's own ID is excluded from the closure. Cycles are guarded by the
    visited set, so a malformed graph terminates instead of hanging.
    """
    rootId = skill.get("id") or skill.get("skillId")

    direct = directStructuralEdges(skill, genericSkillMap, namedSkillMap)

    visited: set[str] = set()
    nested: set[str] = set()
    maxDepth = 0
    truncated = False

    frontier = [cid for cid in direct if cid != rootId]
    depth = 1
    while frontier:
        if depth > FUSION_MAX_DEPTH:
            truncated = True
            break
        nextFrontier: list[str] = []
        advanced = False
        for nodeId in frontier:
            if nodeId in visited or nodeId == rootId:
                continue
            visited.add(nodeId)
            advanced = True
            node = lookupNode(nodeId, genericSkillMap, namedSkillMap)
            if not node:
                continue
            if suiteComponentIds(node):
                nested.add(nodeId)
            for childId in directStructuralEdges(node, genericSkillMap, namedSkillMap):
                if childId == rootId or childId in visited:
                    continue
                nextFrontier.append(childId)
        if advanced:
            maxDepth = depth
        frontier = nextFrontier
        depth += 1

    return {
        "nodes": sorted(visited),
        "direct": sorted(cid for cid in direct if cid != rootId),
        "maxDepth": maxDepth,
        "nestedSuites": sorted(nested),
        "truncated": truncated,
    }


def computeFusionScore(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> float:
    """Return the V1 Fusion Score for ``skill``, rounded to 2 decimals.

    A Basic with no composed structure scores ``0``. A Fusion or Suite scores
    from its resolved structural closure.
    """
    structure = resolveFusionStructure(skill, genericSkillMap, namedSkillMap)
    return fusionScalar(len(structure["nodes"]))


def fusionScoreProjection(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> dict[str, Any]:
    """Return the serializable ``{fusionScore, fusionScoreVersion, fusionBreakdown}``.

    This is the exact shape written into generated projections and read by
    browser code. The breakdown is inspectable, not decorative: every field is
    a count the traversal actually produced.
    """
    structure = resolveFusionStructure(skill, genericSkillMap, namedSkillMap)
    return {
        "fusionScore": fusionScalar(len(structure["nodes"])),
        "fusionScoreVersion": FUSION_SCORE_VERSION,
        "fusionBreakdown": {
            "directCount": len(structure["direct"]),
            "transitiveCount": len(structure["nodes"]),
            "maxDepth": structure["maxDepth"],
            "nestedSuiteCount": len(structure["nestedSuites"]),
        },
    }


def explainFusionScore(
    skill: dict,
    genericSkillMap: Optional[dict] = None,
    namedSkillMap: Optional[dict] = None,
) -> str:
    """Return a plain-text explanation of how the Fusion Score was reached.

    No ANSI, suitable for piping and for test assertions. Deliberately says
    what Fusion Score is *not*, because the failure mode this metric invites
    is a reader treating it as a second trust number.
    """
    structure = resolveFusionStructure(skill, genericSkillMap, namedSkillMap)
    nodes = structure["nodes"]
    direct = structure["direct"]
    count = len(nodes)
    score = fusionScalar(count)

    lines: list[str] = []
    lines.append(f"Fusion Score: {score:.2f} ({FUSION_SCORE_VERSION})")
    lines.append("")
    lines.append("Structural reading only — independent of Trust Magnitude.")
    lines.append("Not an Evidence Type, not a Trust Grade input, gates no rank.")
    lines.append("")

    if count == 0:
        lines.append("No composed structure: this skill scores 0.00.")
        lines.append("")
        lines.extend(YGGDRASIL_II_MIGRATION_NOTE)
        return "\n".join(lines)

    lines.append(f"Direct structure ({len(direct)}):")
    for nodeId in direct:
        marker = " [nested suite]" if nodeId in structure["nestedSuites"] else ""
        lines.append(f"  {nodeId}{marker}")

    transitiveOnly = [nodeId for nodeId in nodes if nodeId not in set(direct)]
    if transitiveOnly:
        lines.append("")
        lines.append(f"Reached transitively ({len(transitiveOnly)}):")
        for nodeId in transitiveOnly:
            marker = " [nested suite]" if nodeId in structure["nestedSuites"] else ""
            lines.append(f"  {nodeId}{marker}")

    lines.append("")
    lines.append(f"Distinct non-variant nodes (N): {count}")
    lines.append(f"Max depth: {structure['maxDepth']}")
    lines.append(f"Nested suites: {len(structure['nestedSuites'])}")
    if structure["truncated"]:
        lines.append(f"Traversal stopped at the declared limit of {FUSION_MAX_DEPTH} levels.")
    lines.append("")
    if count <= FUSION_SOFTENING_KNEE:
        lines.append(f"  FS = 20 x {count} = {score:.2f}")
    else:
        lines.append(
            f"  FS = 200 + 20 x sqrt({count} - {FUSION_SOFTENING_KNEE}) = {score:.2f}"
        )
    lines.append("")
    lines.extend(YGGDRASIL_II_MIGRATION_NOTE)
    return "\n".join(lines)
