#!/usr/bin/env python3
"""Trust Magnitude Consistency Gate — prove the dry-run appraiser and the
generated registry projection can't silently diverge again (Issue #1600).

Gaia's Matt Pocock suite once showed three different Trust Magnitude (TM)
readings for the same skill: `scripts/trust_appraise.py`'s dry-run, the
generated `docs/api/v1/skills/**` projection, and the cached frontmatter
`trustMagnitude` field. Two of those three were both computed live from the
canonical `computeTrustMagnitude()` formula but disagreed because they were
fed different registry context — `trust_appraise.py` built no
generic+named skill map at all, so a suite/fusion skill's `suiteComponents`
origins fell back to an optimistic "assume every origin is graded" guess
instead of resolving each origin's real grade.

This gate re-derives, for every named skill, the exact TM
`trust_appraise.py` now computes (`computeTrustMagnitude(skill, mergedMap)`
via the shared `gaia_cli.registryMaps.buildMergedSkillMap` helper both
`trust_appraise.py` and `scripts/generateNamedIndex.py` build from) and
checks two things:

  1. Cache validity: whenever a skill's stored `trustMagnitudeInputHash`
     still matches its current inputs, the stored `trustMagnitude` must
     equal the freshly recomputed value (within 0.02, the same tolerance
     `computeTrustMagnitudeByType`'s proportional-scaling already uses) — a
     valid-hash cache with a wrong number is a different bug class than
     staleness and would otherwise go undetected.
  2. Generated-index agreement: when `registry/named-skills.json` (built by
     `scripts/assemble_gaia.py` + `scripts/generateNamedIndex.py`) is
     present, its stored `trustMagnitude` for each skill must equal the
     dry-run value within the same tolerance — the actual cross-surface
     check the issue asked for.

Frozen skills (``gaia_cli.frozen``) are the exception to both checks: their
stamps are locked and never rewritten, so a later change to the formula (for
example the 49.9 suite cap, #2378) moves the recomputation but not the lock. For
a frozen skill the expected value is its locked ``trustMagnitude`` /
``overallTrustGrade`` (``frozenLock``), never a fresh recomputation: the index
must publish the lock, and the lock itself must be valid. Non-frozen skills are
checked exactly as before.

Exit code 0 = all named skills agree across surfaces; 1 = drift (each printed).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter  # noqa: E402
from gaia_cli.frozen import frozenIds, frozenLock  # noqa: E402
from gaia_cli.registry import named_skills_dir, named_skills_index_path  # noqa: E402
from gaia_cli.registryMaps import buildMergedSkillMap  # noqa: E402
from gaia_cli.trustMagnitude import (  # noqa: E402
    computeTrustMagnitude,
    computeTrustMagnitudeInputHash,
)

TOLERANCE = 0.02


class InputError(Exception):
    """An input the gate depends on is unreadable or malformed; agreement cannot be claimed."""


def _loadNamedSkills(registryPath: str) -> list[dict]:
    namedDir = Path(named_skills_dir(registryPath))
    skills = []
    if not namedDir.exists():
        return skills
    for mdFile in sorted(namedDir.rglob("*.md")):
        try:
            _, fmText, _ = split_frontmatter(mdFile.read_text(encoding="utf-8"))
            fm = load_yaml_simple(fmText)
        except (OSError, ValueError) as exc:
            raise InputError(f"unreadable named skill {mdFile}: {exc}") from exc
        if fm.get("status") == "named" and fm.get("id"):
            skills.append(fm)
    return skills


def _loadGeneratedIndex(registryPath: str) -> dict[str, dict] | None:
    """The generated index by id; ``None`` only when it was never built, else fail closed."""
    indexPath = Path(named_skills_index_path(registryPath))
    if not indexPath.exists():
        return None
    try:
        data = json.loads(indexPath.read_text(encoding="utf-8"))
        buckets = data["buckets"].values()
        byId: dict[str, dict] = {}
        for entries in buckets:
            for entry in entries:
                entryId = entry.get("id")
                if entryId:
                    byId[entryId] = entry
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise InputError(f"unreadable or malformed {indexPath}: {exc}") from exc
    return byId


def _finiteNumber(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def findViolations(
    namedSkills: list[dict], mergedMap: dict, generatedIndex: dict[str, dict] | None
) -> tuple[list[str], int, int]:
    """Return ``(violations, cacheChecked, indexChecked)`` for the named skills.

    ``generatedIndex`` is ``None`` when the index was never built (cross-check skipped);
    a built index, even an empty one, must contain every frozen skill.
    """
    if generatedIndex is None:
        generatedIndex = {}
        indexBuilt = False
    else:
        indexBuilt = True
    frozen = frozenIds(namedSkills)
    violations: list[str] = []
    cacheChecked = 0
    indexChecked = 0

    for skill in namedSkills:
        skillId = skill["id"]
        lock = frozenLock(skill) if skillId in frozen else None
        if skillId in frozen:
            if lock is None:
                violations.append(
                    f"{skillId}: frozen skill lacks a valid trustMagnitude/overallTrustGrade "
                    f"lock; its bytes must be preserved and the lock repaired through an "
                    f"explicitly authorized historical-lock workflow."
                )
                continue
            # The locked stamp IS the expected value; never recompute a frozen skill.
            expectedTm = round(lock[0], 2)
        else:
            expectedTm = round(computeTrustMagnitude(skill, mergedMap), 2)

            storedTm = skill.get("trustMagnitude")
            storedHash = skill.get("trustMagnitudeInputHash")
            if storedTm is not None and storedHash is not None:
                currentHash = computeTrustMagnitudeInputHash(skill)
                if storedHash == currentHash:
                    cacheChecked += 1
                    if abs(float(storedTm) - expectedTm) > TOLERANCE:
                        violations.append(
                            f"{skillId}: frontmatter trustMagnitude={storedTm} claims a valid "
                            f"trustMagnitudeInputHash, but recomputing from the same inputs gives "
                            f"{expectedTm}. Run `gaia dev calibrate-trust-magnitude --skill {skillId}`."
                        )

        indexEntry = generatedIndex.get(skillId)
        if lock is not None:
            # A frozen skill must be published, and published as exactly its lock:
            # a missing entry, missing or non-finite values, or any inequality
            # (however small) is a violation; there is no tolerance on a lock.
            if indexEntry is None:
                if indexBuilt:
                    violations.append(
                        f"{skillId}: frozen skill is missing from registry/named-skills.json; "
                        f"the generator must publish the frozen lock ({lock[0]} / {lock[1]})."
                    )
                continue
            indexChecked += 1
            indexTm = indexEntry.get("trustMagnitude")
            indexGrade = indexEntry.get("overallTrustGrade")
            if not _finiteNumber(indexTm) or float(indexTm) != lock[0]:
                violations.append(
                    f"{skillId}: registry/named-skills.json trustMagnitude={indexTm!r} is not "
                    f"its locked stamp {lock[0]} (frozen). The generator must publish the "
                    f"frozen lock unchanged (gaia_cli.frozen.frozenLock)."
                )
            if indexGrade != lock[1]:
                violations.append(
                    f"{skillId}: registry/named-skills.json overallTrustGrade={indexGrade!r} is "
                    f"not its locked grade {lock[1]} (frozen). The generator must publish the "
                    f"frozen lock unchanged (gaia_cli.frozen.frozenLock)."
                )
            continue
        if indexEntry is not None:
            indexTm = indexEntry.get("trustMagnitude")
            if indexTm is not None:
                indexChecked += 1
                if abs(float(indexTm) - expectedTm) > TOLERANCE:
                    violations.append(
                        f"{skillId}: registry/named-skills.json trustMagnitude={indexTm} "
                        f"disagrees with the dry-run appraiser's {expectedTm}. The generator "
                        f"and trust_appraise.py must feed computeTrustMagnitude the same "
                        f"registry map (gaia_cli.registryMaps.buildMergedSkillMap)."
                    )

    return violations, cacheChecked, indexChecked


def main() -> int:
    registryPath = str(REPO_ROOT)
    try:
        namedSkills = _loadNamedSkills(registryPath)
        generatedIndex = _loadGeneratedIndex(registryPath)
    except InputError as exc:
        print(f"❌ Trust Magnitude consistency cannot be established: {exc}")
        return 1
    mergedMap = buildMergedSkillMap(registryPath)

    violations, cacheChecked, indexChecked = findViolations(namedSkills, mergedMap, generatedIndex)

    if generatedIndex is None:
        print(
            "Note: registry/named-skills.json not found — skipping generated-index "
            "cross-check (run `python scripts/assemble_gaia.py && "
            "python scripts/generateNamedIndex.py` first for full coverage)."
        )

    print(
        f"Trust Magnitude consistency: {len(namedSkills)} named skills, "
        f"{cacheChecked} cache-validity checks, {indexChecked} generated-index checks."
    )

    if violations:
        print(f"\n❌ {len(violations)} Trust Magnitude inconsistency(ies):")
        for idx, violation in enumerate(violations, 1):
            print(f"   {idx}. {violation}")
        return 1

    print("✅ All Trust Magnitude surfaces agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
