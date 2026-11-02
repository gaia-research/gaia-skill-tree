"""The one definition of a *frozen* named skill.

Founder ruling 2026-10-30 (EPIC #2189, ``CAMPAIGN.md`` r4-frozen-def): a skill
is frozen when it was frozen itself, or when it belongs to a frozen suite
("suites whose upstream is frozen — gaia dev freeze any node").

A skill is **self-frozen** when any of these hold:

- ``frozen: true`` or a ``frozenAt`` stamp in its frontmatter;
- it carries an ``upstream_deprecated`` timeline event (what ``gaia dev freeze``
  writes) **and** it is not an active suite capstone. A suite capstone that only
  logged a component removal (``gaia dev build``) has the same event with
  "(not frozen)" in its details and keeps ``installable`` unset, so it is not
  frozen. A capstone frozen with ``gaia dev freeze`` gets ``installable: false``.

A skill is **frozen** when it is self-frozen, or when a frozen suite contains it
(it is listed in a frozen capstone's ``suiteComponents``, or its ``suiteRef``
names a frozen capstone), applied transitively through nested suites.

Frozen skills keep their **locked** Trust Magnitude and grade: the values cached
in their frontmatter (``trustMagnitude`` / ``overallTrustGrade``) when they were
frozen. Nothing writes to a frozen file afterwards, so the cache is the lock.
Every batch tool that skips frozen skills must call :func:`frozenIds` or
:func:`isFrozen` rather than restating this rule.
"""

from __future__ import annotations

import math
from typing import Iterable, Optional


_VALID_GRADES = frozenset({"S", "A", "B", "C", "ungraded"})


def _hasUpstreamDeprecated(meta: dict) -> bool:
    timeline = meta.get("timeline")
    if not isinstance(timeline, list):
        return False
    return any(isinstance(e, dict) and e.get("action") == "upstream_deprecated" for e in timeline)


def isSelfFrozen(meta: dict) -> bool:
    """True when ``meta`` was frozen itself (see module docstring)."""
    if not isinstance(meta, dict):
        return False
    if meta.get("frozen") is True or meta.get("frozenAt"):
        return True
    if not _hasUpstreamDeprecated(meta):
        return False
    activeCapstone = bool(meta.get("suiteComponents")) and meta.get("installable") is not False
    return not activeCapstone


def frozenIds(metas: Iterable[dict]) -> set[str]:
    """Return the ids of every frozen skill among ``metas`` (self or via a frozen suite)."""
    byId: dict[str, dict] = {}
    for meta in metas:
        if isinstance(meta, dict) and meta.get("id"):
            byId[meta["id"]] = meta
    frozen = {sid for sid, meta in byId.items() if isSelfFrozen(meta)}
    changed = True
    while changed:
        changed = False
        for sid, meta in byId.items():
            if sid in frozen:
                continue
            if meta.get("suiteRef") in frozen:
                frozen.add(sid)
                changed = True
        for sid in list(frozen):
            for component in byId.get(sid, {}).get("suiteComponents") or []:
                if isinstance(component, str) and component in byId and component not in frozen:
                    frozen.add(component)
                    changed = True
    return frozen


def isFrozen(meta: dict, allMetas: Optional[Iterable[dict]] = None) -> bool:
    """True when ``meta`` is frozen. Pass ``allMetas`` to resolve suite inheritance."""
    if isSelfFrozen(meta):
        return True
    if allMetas is None:
        return False
    return meta.get("id") in frozenIds(list(allMetas) + [meta])


def frozenLock(meta: dict) -> Optional[tuple[float, str]]:
    """Return a valid locked ``(trustMagnitude, grade)``, else ``None``.

    Frozen records never fall back to live computation. A lock must contain a
    finite numeric TM and one canonical Overall Trust Grade. Call
    :func:`requireFrozenLocks` at a read or write boundary to fail closed with
    the affected ids rather than silently changing historical standing.
    """
    tm = meta.get("trustMagnitude")
    grade = meta.get("overallTrustGrade")
    if tm is None or grade not in _VALID_GRADES:
        return None
    try:
        value = float(tm)
    except (TypeError, ValueError):
        return None
    return (value, grade) if math.isfinite(value) else None


def missingFrozenLocks(metas: Iterable[dict], frozen: Optional[set[str]] = None) -> list[str]:
    """Return frozen ids lacking a valid historical TM/grade lock."""
    values = [meta for meta in metas if isinstance(meta, dict) and meta.get("id")]
    frozen_ids = frozen if frozen is not None else frozenIds(values)
    return sorted(
        meta["id"] for meta in values
        if meta.get("id") in frozen_ids and frozenLock(meta) is None
    )


def requireFrozenLocks(metas: Iterable[dict], frozen: Optional[set[str]] = None) -> None:
    """Fail closed when a frozen record has no valid historical lock."""
    missing = missingFrozenLocks(metas, frozen)
    if missing:
        raise ValueError(
            "Frozen skill(s) lack a valid trustMagnitude/overallTrustGrade lock: "
            + ", ".join(missing)
            + ". Preserve their bytes and repair through an explicitly authorized historical-lock workflow."
        )
