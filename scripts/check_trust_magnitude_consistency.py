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

# Fields validated by their own sub-schema from namedSkill.schema.json (read, never
# restated), only where the real registry conforms. NOT the whole-record schema: the
# committed schema has drifted from the registry (see the schema-drift issue), so the
# record is deliberately not validated as a whole.
SCHEMA_DERIVED_FIELDS = (
    "status", "genericSkillRef", "trustMagnitude", "overallTrustGrade", "suiteRef", "suiteComponents",
)


class SchemaContext:
    """The named-skill schema's enums and per-field validators, read from the schema file."""

    def __init__(self, path: Path, schema) -> None:
        if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
            raise InputError(f"{path}: not a schema with a 'properties' object")
        self.path = path
        self.properties = schema["properties"]
        self.statuses = self._enum("status")
        self.grades = self._enum("overallTrustGrade")
        if GATED_STATUS not in self.statuses:
            raise InputError(f"{path}: status enum does not contain {GATED_STATUS!r}")
        try:
            import jsonschema
        except ImportError as exc:  # fail closed: a missing validator is not a passing validation
            raise InputError("jsonschema is required to validate named skills against the schema") from exc
        self.validators = {}
        for field in SCHEMA_DERIVED_FIELDS:
            sub = self.properties.get(field)
            if not isinstance(sub, dict):
                raise InputError(f"{path}: schema defines no sub-schema for {field!r}")
            try:
                jsonschema.Draft7Validator.check_schema(sub)
            except jsonschema.SchemaError as exc:
                raise InputError(f"{path}: invalid sub-schema for {field!r}: {exc.message}") from exc
            self.validators[field] = jsonschema.Draft7Validator(sub)
        # Type level only: the item schema rejects fields real files carry (e.g.
        # evidence[].updatedAt), so only "an array of mappings" is enforced.
        for field in ("evidence", "timeline"):
            base = self.properties.get(field)
            if not isinstance(base, dict) or base.get("type") != "array":
                raise InputError(f"{path}: schema does not define {field!r} as an array")
            self.validators[field] = jsonschema.Draft7Validator({"type": "array", "items": {"type": "object"}})

    def _enum(self, field: str) -> frozenset[str]:
        values = (self.properties.get(field) or {}).get("enum") if isinstance(self.properties.get(field), dict) else None
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):
            raise InputError(f"{self.path}: the {field!r} enum must be a non-empty list of non-empty strings (got {values!r})")
        return frozenset(values)


def _loadSchema(registryPath: str) -> SchemaContext:
    path = Path(registryPath) / NAMED_SCHEMA
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"{path}: cannot read the named-skill schema: {exc}") from exc
    return SchemaContext(path, schema)


def _allowedStatuses(registryPath: str) -> frozenset[str]:
    return _loadSchema(registryPath).statuses


def _requireString(path: Path, meta: dict, field: str) -> None:
    value = meta.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{path}: field {field!r} is missing or not a non-empty string (got {value!r})")


def _explicitType(path: Path, meta: dict, field: str, check, expected: str) -> None:
    """For fields ``gaia_cli.frozen`` reads that the schema does not define: typed when present."""
    if field in meta and not check(meta[field]):
        raise InputError(f"{path}: field {field!r} must be {expected} when present (got {meta[field]!r})")


def _validateNamedRecord(path: Path, meta, schema: SchemaContext) -> dict:
    """Validate the fields the gate reads from one named file, or raise ``InputError``.

    Every message names the file and the field. Schema-derived: ``status`` (enum),
    ``genericSkillRef``, ``trustMagnitude`` (number, minimum 0), ``overallTrustGrade``
    (enum), ``suiteRef``, ``suiteComponents``, ``evidence``/``timeline`` (array of
    mappings, type level). Explicit: ``id``, ``frozen``/``frozenAt``/``installable``
    (not in the schema; ``gaia_cli.frozen`` reads them), timeline ``action`` strings,
    and the stricter-than-schema requirements applied for a named record.
    """
    if not isinstance(meta, dict) or not meta:
        raise InputError(f"{path}: missing or malformed frontmatter")
    _requireString(path, meta, "id")  # the schema's id pattern rejects a real file; type-level only
    if "status" not in meta:
        raise InputError(f"{path}: field 'status' is required (one of {sorted(schema.statuses)})")
    for field in (*SCHEMA_DERIVED_FIELDS, "evidence", "timeline"):
        if field in meta:
            for error in schema.validators[field].iter_errors(meta[field]):
                where = "".join(f"[{part!r}]" for part in error.absolute_path)
                raise InputError(f"{path}: field {field!r}{where}: {error.message}")
    if meta["status"] not in schema.statuses:  # defensive: the validator already enforced the enum
        raise InputError(f"{path}: field 'status' must be one of {sorted(schema.statuses)}")
    for field, check, expected in (
        ("frozen", lambda v: isinstance(v, bool), "a bool"),
        ("frozenAt", lambda v: isinstance(v, str) and bool(v.strip()), "a non-empty string"),
        ("installable", lambda v: isinstance(v, bool), "a bool"),
    ):
        _explicitType(path, meta, field, check, expected)
    # Invariants the schema cannot express. ``gaia_cli.frozen`` freezes on an
    # ``upstream_deprecated`` timeline action, so every item needs a usable action
    # (a missing or non-string action would silently read as "not frozen").
    # ``timeline: null`` is rejected (the schema's type is array); frozen.py would read
    # it as no timeline, so the gate may only be stricter, never different.
    for index, item in enumerate(meta.get("timeline") or []):
        action = item.get("action")
        if not isinstance(action, str) or not action.strip():
            raise InputError(f"{path}: field 'timeline'[{index}]['action'] must be a non-empty string (got {action!r})")
    if meta["status"] != GATED_STATUS:
        return meta  # explicitly excluded from the stamp checks; still part of the frozen census
    # Stricter than the schema, because the gate needs them: the schema requires neither the
    # stamp nor its hash, and the cache check is meaningless without both.
    if "genericSkillRef" not in meta:
        raise InputError(f"{path}: field 'genericSkillRef' is required for a named record")
    return meta


def _validateStamps(records: list[dict], paths: dict[str, Path]) -> None:
    """A non-frozen named skill's stamp and hash are what the cache check reads: both required.

    Stricter than the schema (which requires neither). Frozen skills are exempt here:
    their lock is validated by ``frozenLock`` and a bad lock is a violation.
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
    schema = _loadSchema(registryPath)
    paths: dict[str, Path] = {}
    for mdFile in sorted(namedDir.rglob("*.md")):
        try:
            _, fmText, _ = split_frontmatter(mdFile.read_text(encoding="utf-8"))
            fm = load_yaml_simple(fmText)
        except (OSError, ValueError) as exc:
            raise InputError(f"unreadable named skill {mdFile}: {exc}") from exc
        record = _validateNamedRecord(mdFile, fm, schema)
        if record["id"] in paths:
            raise InputError(f"{mdFile}: field 'id' {record['id']!r} duplicates {paths[record['id']]}")
        paths[record["id"]] = mdFile
        records.append(record)
    _validateStamps(records, paths)
    return records


def _loadGeneratedIndex(registryPath: str) -> dict[str, dict] | None:
    """The generated index by id; ``None`` only when it was never built, else fail closed.

    Valid structure is an object whose ``buckets`` is an object of lists of mappings, each
    with a non-empty string ``id``; a duplicate id is an error (never last-wins).
    """
    indexPath = Path(named_skills_index_path(registryPath))
    if not indexPath.exists():
        return None
    try:
        data = json.loads(indexPath.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"unreadable or malformed {indexPath}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("buckets"), dict):
        raise InputError(f"{indexPath}: expected an object with a 'buckets' object")
    byId: dict[str, dict] = {}
    for bucket, entries in data["buckets"].items():
        if not isinstance(entries, list):
            raise InputError(f"{indexPath}: bucket {bucket!r} must be a list")
        for position, entry in enumerate(entries):
            entryId = entry.get("id") if isinstance(entry, dict) else None
            if not isinstance(entryId, str) or not entryId.strip():
                raise InputError(f"{indexPath}: bucket {bucket!r}[{position}] is not a mapping with a non-empty string 'id'")
            if entryId in byId:
                raise InputError(f"{indexPath}: duplicate id {entryId!r} (bucket {bucket!r})")
            byId[entryId] = entry
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
