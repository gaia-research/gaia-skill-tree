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

A missing ``registry/named-skills.json`` is NOT agreement: the gate exits 1 with
"named index not built" unless ``--allow-missing-index`` is passed explicitly.

Exit code 0 = all named skills agree across surfaces; 1 = drift (each printed).
"""

from __future__ import annotations

import argparse
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

INDEX_NOT_BUILT = (
    "named index not built; run scripts/generateNamedIndex.py (gaia dev docs) "
    "before this gate"
)


class InputError(Exception):
    """An input the gate depends on is unreadable or malformed; agreement cannot be claimed."""


NAMED_SCHEMA = Path("registry") / "schema" / "namedSkill.schema.json"
GATED_STATUS = "named"  # every other schema status is excluded explicitly, not skipped by accident


def _allowedStatuses(registryPath: str) -> frozenset[str]:
    """The lifecycle statuses the named-skill schema allows (read, never hard-coded)."""
    path = Path(registryPath) / NAMED_SCHEMA
    try:
        values = json.loads(path.read_text(encoding="utf-8"))["properties"]["status"]["enum"]
        if not values or not all(isinstance(value, str) and value for value in values):
            raise ValueError("status enum must be a non-empty list of strings")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InputError(f"{path}: cannot read the allowed status values: {exc}") from exc
    if GATED_STATUS not in values:
        raise InputError(f"{path}: status enum does not contain {GATED_STATUS!r}")
    return frozenset(values)


def _requireString(path: Path, meta: dict, field: str) -> None:
    value = meta.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{path}: field {field!r} is missing or not a non-empty string (got {value!r})")


def _optionalType(path: Path, meta: dict, field: str, check, expected: str) -> None:
    value = meta.get(field)
    if value is not None and not check(value):
        raise InputError(f"{path}: field {field!r} must be {expected} when present (got {value!r})")


def _validateNamedRecord(path: Path, meta, allowedStatuses: frozenset[str]) -> dict:
    """Validate every field the gate reads from one named file, or raise ``InputError``.

    Every message names the file and the field. Fields read, and why:
      id, status                 identity and census membership (always)
      frozen, frozenAt, timeline, installable, suiteRef, suiteComponents
                                 read by ``gaia_cli.frozen`` to decide who is frozen
      trustMagnitude, overallTrustGrade
                                 the lock of a frozen skill (validated by ``frozenLock``)
      trustMagnitude, trustMagnitudeInputHash
                                 the stamp and its hash for a non-frozen named skill
      genericSkillRef            required by the recomputation (generic evidence resolution)
    """
    if not isinstance(meta, dict) or not meta:
        raise InputError(f"{path}: missing or malformed frontmatter")
    _requireString(path, meta, "id")
    status = meta.get("status")
    if status not in allowedStatuses:
        raise InputError(
            f"{path}: field 'status' must be one of {sorted(allowedStatuses)} (got {status!r})"
        )
    # Fields that decide who is frozen apply to every record, whatever its status.
    _optionalType(path, meta, "frozen", lambda v: isinstance(v, bool), "a bool")
    _optionalType(path, meta, "frozenAt", lambda v: isinstance(v, str) and bool(v.strip()), "a non-empty string")
    _optionalType(path, meta, "installable", lambda v: isinstance(v, bool), "a bool")
    _optionalType(path, meta, "suiteRef", lambda v: isinstance(v, str) and bool(v.strip()), "a non-empty string")
    _optionalType(
        path, meta, "suiteComponents",
        lambda v: isinstance(v, list) and all(isinstance(item, str) and item.strip() for item in v),
        "a list of non-empty strings",
    )
    _optionalType(
        path, meta, "timeline",
        lambda v: isinstance(v, list) and all(isinstance(item, dict) for item in v),
        "a list of mappings",
    )
    if status != GATED_STATUS:
        return meta  # explicitly excluded from the stamp checks; still part of the frozen census
    _requireString(path, meta, "genericSkillRef")
    return meta


def _validateStamps(records: list[dict], paths: dict[str, Path]) -> None:
    """A non-frozen named skill's stamp and hash are what the cache check reads: both required.

    Frozen skills are exempt here: their lock is validated by ``frozenLock`` and a bad
    lock is reported as a violation against the skill.
    """
    frozen = frozenIds(records)
    for meta in records:
        if meta.get("status") != GATED_STATUS or meta["id"] in frozen:
            continue
        path = paths[meta["id"]]
        if not _finiteNumber(meta.get("trustMagnitude")):
            raise InputError(
                f"{path}: field 'trustMagnitude' is missing or not a finite number (got {meta.get('trustMagnitude')!r})"
            )
        digest = meta.get("trustMagnitudeInputHash")
        if not isinstance(digest, str) or not digest.strip():
            raise InputError(f"{path}: field 'trustMagnitudeInputHash' is missing or not a non-empty string (got {digest!r})")


def _loadNamedSkills(registryPath: str) -> list[dict]:
    """Every validated named-skill record (all statuses), for the frozen census."""
    namedDir = Path(named_skills_dir(registryPath))
    records = []
    if not namedDir.exists():
        return records
    allowedStatuses = _allowedStatuses(registryPath)
    paths: dict[str, Path] = {}
    for mdFile in sorted(namedDir.rglob("*.md")):
        try:
            _, fmText, _ = split_frontmatter(mdFile.read_text(encoding="utf-8"))
            fm = load_yaml_simple(fmText)
        except (OSError, ValueError) as exc:
            raise InputError(f"unreadable named skill {mdFile}: {exc}") from exc
        record = _validateNamedRecord(mdFile, fm, allowedStatuses)
        if record["id"] in paths:
            raise InputError(f"{mdFile}: field 'id' {record['id']!r} duplicates {paths[record['id']]}")
        paths[record["id"]] = mdFile
        records.append(record)
    _validateStamps(records, paths)
    return records


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
    namedSkills: list[dict],
    mergedMap: dict,
    generatedIndex: dict[str, dict] | None,
    allowMissingIndex: bool = False,
) -> tuple[list[str], int, int]:
    """Return ``(violations, cacheChecked, indexChecked)`` for the named skills.

    ``generatedIndex`` is ``None`` when the index was never built. A missing
    publication artifact is not agreement: unless ``allowMissingIndex`` is set, every
    frozen skill is reported as unpublished. A built index, even an empty one, must
    contain every frozen skill.
    """
    indexBuilt = generatedIndex is not None
    if generatedIndex is None:
        generatedIndex = {}
    frozen = frozenIds(namedSkills)  # census: every status, plus suite inheritance
    violations: list[str] = []
    cacheChecked = 0
    indexChecked = 0

    for skill in namedSkills:
        if skill.get("status") != GATED_STATUS:
            continue  # explicitly excluded (still part of the frozen census above)
        skillId = skill["id"]
        lock = frozenLock(skill) if skillId in frozen else None
        if skillId in frozen:
            if lock is None:
                violations.append(
                    f"{skillId}: frozen skill lacks a valid trustMagnitude/overallTrustGrade "
                    f"lock (missing, bool, string, NaN or inf); its bytes must be preserved and the lock repaired through an "
                    f"explicitly authorized historical-lock workflow."
                )
                continue
            # The locked stamp IS the expected value; never recompute a frozen skill.
            expectedTm = round(lock[0], 2)
        else:
            expectedTm = round(computeTrustMagnitude(skill, mergedMap), 2)

            storedTm = skill.get("trustMagnitude")
            storedHash = skill.get("trustMagnitudeInputHash")
            if not _finiteNumber(storedTm) or not isinstance(storedHash, str) or not storedHash.strip():
                violations.append(
                    f"{skillId}: frontmatter trustMagnitude={storedTm!r} / trustMagnitudeInputHash="
                    f"{storedHash!r} must be a finite number and a non-empty string."
                )
            else:
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
                if not indexBuilt:
                    if not allowMissingIndex:
                        violations.append(
                            f"{skillId}: frozen skill cannot be checked against its published "
                            f"entry: {INDEX_NOT_BUILT}."
                        )
                else:
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
            indexChecked += 1
            if not _finiteNumber(indexTm):
                violations.append(
                    f"{skillId}: registry/named-skills.json trustMagnitude={indexTm!r} is missing "
                    f"or not a finite number."
                )
            elif abs(float(indexTm) - expectedTm) > TOLERANCE:
                violations.append(
                    f"{skillId}: registry/named-skills.json trustMagnitude={indexTm} "
                    f"disagrees with the dry-run appraiser's {expectedTm}. The generator "
                    f"and trust_appraise.py must feed computeTrustMagnitude the same "
                    f"registry map (gaia_cli.registryMaps.buildMergedSkillMap)."
                )

    return violations, cacheChecked, indexChecked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trust Magnitude consistency gate")
    parser.add_argument(
        "--allow-missing-index",
        action="store_true",
        help="Explicit opt-in for contexts that legitimately run without a built "
        "registry/named-skills.json (e.g. local maintenance): skip the generated-index "
        "cross-check. The default fails closed, because a missing publication artifact "
        "is not agreement.",
    )
    args = parser.parse_args(argv)

    registryPath = str(REPO_ROOT)
    try:
        namedSkills = _loadNamedSkills(registryPath)
        generatedIndex = _loadGeneratedIndex(registryPath)
    except InputError as exc:
        print(f"❌ Trust Magnitude consistency cannot be established: {exc}")
        return 1
    if generatedIndex is None and not args.allow_missing_index:
        print(
            f"❌ Trust Magnitude consistency cannot be established: {INDEX_NOT_BUILT} "
            f"(pass --allow-missing-index only where no index is expected)."
        )
        return 1
    mergedMap = buildMergedSkillMap(registryPath)

    violations, cacheChecked, indexChecked = findViolations(
        namedSkills, mergedMap, generatedIndex, allowMissingIndex=args.allow_missing_index
    )

    if generatedIndex is None:
        print(
            "Note: registry/named-skills.json not found; generated-index cross-check "
            "skipped by --allow-missing-index."
        )

    print(
        f"Trust Magnitude consistency: {sum(s.get('status') == GATED_STATUS for s in namedSkills)} named skills, "
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
