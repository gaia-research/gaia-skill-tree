"""Shared level math for canonical Gaia skills."""

from __future__ import annotations

import json
import os


def _load_meta() -> dict:
    """Load registry/schema/meta.json from repo root or bundled fallback."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "registry", "schema", "meta.json"),
        os.path.join(os.path.dirname(__file__), "data", "registry", "schema", "meta.json"),
    ]
    for path in candidates:
        resolved = os.path.normpath(path)
        if os.path.isfile(resolved):
            with open(resolved, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("Cannot find registry/schema/meta.json")


_META = _load_meta()
LEVEL_ORDER = tuple(_META["levels"]["order"])
DEMERIT_ORDER = tuple(_META["demerits"]["order"])
DEMERIT_ELIGIBLE_LEVELS = set(_META["demerits"]["eligibleLevels"])
MIN_EFFECTIVE_LEVEL = _META["demerits"]["minimumEffectiveLevel"]


def level_index(level: str) -> int:
    """Return the index for a level string within LEVEL_ORDER."""
    return LEVEL_ORDER.index(level)


def demerit_penalty(skill: dict) -> int:
    """Return demerit penalty count for a skill from known catalog ids."""
    demerits = skill.get("demerits", []) or []
    return sum(1 for item in demerits if item in DEMERIT_ORDER)


def effective_level(skill: dict) -> str:
    """Return the demerit-adjusted effective level for a skill."""
    current = skill.get("level", "1★")
    if current not in DEMERIT_ELIGIBLE_LEVELS:
        return current
    base_idx = level_index(current)
    floor_idx = level_index(MIN_EFFECTIVE_LEVEL)
    penalty = demerit_penalty(skill)
    lowered = max(floor_idx, base_idx - penalty)
    return LEVEL_ORDER[lowered]


def level_summary(skill: dict) -> dict:
    """Return base/effective level summary plus demerits."""
    return {
        "baseLevel": skill.get("level", "1★"),
        "effectiveLevel": effective_level(skill),
        "demerits": list(skill.get("demerits", []) or []),
    }
