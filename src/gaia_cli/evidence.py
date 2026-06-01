"""Evidence inheritance for the rank-less generic / named skill model.

Generic skill refs are pure taxonomy and hold capability-level (Class A /
academic) evidence. Every named skill that points at a generic via
``genericSkillRef`` *inherits* that evidence, and may add its own
implementation-specific evidence (e.g. its GitHub repo).

This module is the single place that computes a named skill's effective
evidence pool, used by rendering, the CLI, and validation.
"""

from __future__ import annotations


def merge_evidence(*groups) -> list:
    """Concatenate evidence lists, de-duplicating by ``source`` (first wins)."""
    seen = set()
    merged = []
    for group in groups:
        for entry in group or []:
            src = entry.get("source")
            if src in seen:
                continue
            seen.add(src)
            merged.append(entry)
    return merged


def inherited_evidence(named_skill: dict, generic_node: dict | None) -> list:
    """Return a named skill's effective evidence pool.

    Own evidence first (most specific), then the generic ref's inherited
    capability evidence. De-duplicated by ``source``.
    """
    generic = (generic_node or {}).get("evidence") if generic_node else []
    return merge_evidence(named_skill.get("evidence"), generic)


def build_generic_evidence_map(skills) -> dict:
    """Map generic skill id -> its evidence list, for inheritance lookups."""
    return {s["id"]: (s.get("evidence") or []) for s in skills if "id" in s}
