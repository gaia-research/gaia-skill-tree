"""Merged generic + named skill map — canonical input for Trust Magnitude
fusion-recipe origin resolution (Issue #1600).

`computeTrustMagnitude()` and its siblings in `trustMagnitude.py` accept an
optional `genericSkillMap: {id: skillDict}` used to resolve a suite/fusion
skill's `suiteComponents` origins to their actual grade (`_gradedOriginCount`)
and to resolve a named skill's generic-parent evidence (`_effectivePool`).
Every caller needs the SAME map — one keyed by both generic node ids and full
named-skill ids (`contributor/skill-id`) — or the two computations diverge:
without a named id in the map, `_gradedOriginCount` cannot tell whether a
suite-component origin is graded and falls back to an optimistic "assume
graded" guess (see `trustMagnitude.py::_gradedOriginCount`), inflating the
aggregate for any skill with `suiteComponents`.

`scripts/generateNamedIndex.py` builds this map inline from the in-memory
registry it already has loaded while regenerating docs. `scripts/trust_appraise.py`
has no such context — it appraises a single skill standalone — so it needs to
build the same map from disk. This module is the one place that construction
happens, so the two callers can never drift again (mirrors the
`gaia_cli.taxonomy` precedent: one canonical resolver, no consumer forks its
own copy).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
from gaia_cli.registry import named_skills_dir, registry_nodes_dir


def buildMergedSkillMap(registryPath: str | Path = ".") -> dict[str, dict[str, Any]]:
    """Return {id: skillDict} merging generic nodes with every named skill.

    Generic half: every `registry/nodes/**/*.json`, keyed by its `id` field.
    Named half: every `registry/named/**/*.md` whose frontmatter `status` is
    `"named"` (matching the bucket filter `generateNamedIndex.py` applies),
    keyed by its `id` field, with the display-only `role` key stripped (a
    named entry's `role` marks "champion vs variant" within its own bucket —
    leaking it into a shared lookup map previously zeroed out non-champion
    origins' contribution to fusion-recipe grading; see commit `59a87e45d`).

    Named entries win over a generic entry on id collision, mirroring
    `generateNamedIndex.py`'s `{**generic_skills_map, **named_skill_map}`.
    """
    mergedMap: dict[str, dict[str, Any]] = {}

    nodesDir = Path(registry_nodes_dir(registryPath))
    if nodesDir.exists():
        for nodeFile in nodesDir.rglob("*.json"):
            try:
                skill = json.loads(nodeFile.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            skillId = skill.get("id")
            if skillId:
                mergedMap[skillId] = skill

    namedDir = Path(named_skills_dir(registryPath))
    if namedDir.exists():
        for mdFile in namedDir.rglob("*.md"):
            try:
                _, fmText, _ = split_frontmatter(mdFile.read_text(encoding="utf-8"))
                fm = load_yaml_simple(fmText)
            except OSError:
                continue
            if fm.get("status") != "named":
                continue
            skillId = fm.get("id")
            if not skillId:
                continue
            fm = {k: v for k, v in fm.items() if k != "role"}
            mergedMap[skillId] = fm

    return mergedMap
