"""Event-driven Trust Magnitude restamping (founder ruling 2026-11-06, #1642, option 8A).

A named skill's ``trustMagnitude`` / ``overallTrustGrade`` /
``trustMagnitudeInputHash`` frontmatter is a derived, hash-signed cache (see
``docs/agents/curation-authority-map.md`` section 4). When an evidence mutation
changes what that cache is computed from, the cache goes stale. The founder
ruled that the stale stamp is cleared inside the same PR that changes the
evidence, for the affected skills only, when the refresh is a pure
recomputation, and that periodic reconciliation (the Steward
``trust_stamp_stale`` sensor, plus ``calibrate-trust-magnitude --all
--recomputation-only``) stays the backstop.

This module owns the decisions that make the trigger safe:

* **Which skills are affected.** Every named skill is fingerprinted before and
  after the evidence write: computed Trust Magnitude, computed Overall Trust
  Grade (which also moves with evidence-type diversity and the independent
  witness, with TM unchanged) and the own-input hash. A change in any of the
  three makes the skill affected, so a change on a generic node reaches every
  inheriting named skill and a change on a component reaches its suites. The
  skill written directly is always affected.
* **Whether a refresh is recomputation-only.** It is when the computed grade
  still agrees with the stored star level **and** the grade written into the
  stamp is the grade already stored there (:func:`isRecomputationOnly`), the
  one predicate the Steward sensor stamps on every ``trust_stamp_stale``
  finding. Anything else is a governed trust, rank or evidence-policy question:
  the stamp is left stale and held for the desk.
* **Who may write, and how.** The write boundary is
  :func:`restampAfterEvidenceChange`. It enforces ``require_operator`` and the
  canonical transaction lock itself, so a direct call cannot bypass the
  authorization and transaction semantics the CLI dispatcher applies. The write
  is the one existing verb, ``gaia dev calibrate-trust-magnitude``, which never
  writes a star level and keeps its own preflights.
* **That nothing but the intended stamps moved.** :func:`verifyRestamp`
  re-reads everything from disk and compares against a pre-write
  :class:`ProtectedState`: every intended target was written with all three
  stamp fields present and matching, and every skill's level, computed grade and
  frozen state, every bucket's Origin, and every non-target record's bytes are
  unchanged.

Frozen skills are never touched.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

# Overall Trust Grade -> the star level that grade supports. The Steward sensor
# reads this same table, so the sensor's ``recomputationOnly`` and this gate can
# never disagree.
targetLevelByGrade = {"S": "5★", "A": "4★", "B": "3★", "C": "2★", "ungraded": "1★"}

# Stamps are written as round(computeTrustMagnitude(...), 2): a fresh stamp sits
# within the rounding tolerance of the computed value.
roundingTolerance = 0.005
# The Steward sensor reports a stamp as TM-stale beyond this distance.
sensorStampTolerance = 0.02
# Computed TM is deterministic, so any movement above float noise is real.
movementEpsilon = 1e-9

stampFields = ("trustMagnitude", "overallTrustGrade", "trustMagnitudeInputHash")


class RestampVerificationError(RuntimeError):
    """A restamp left something other than a clean, level-preserving refresh."""


def holdReasons(storedLevel: Any, computedGrade: str, storedGrade: Any) -> list[str]:
    """Why a refresh is not a pure recomputation (empty when it is).

    * ``level-disagrees-with-computed-grade``: the computed grade supports a
      different star level than the one stored (a calibration question).
    * ``stored-grade-missing``: the stamp carries no grade, so a refresh would
      introduce one (grade movement from nothing).
    * ``stored-grade-differs-from-computed-grade``: a refresh would rewrite the
      grade the stamp already stores.
    """

    reasons: list[str] = []
    if targetLevelByGrade.get(computedGrade) != storedLevel:
        reasons.append("level-disagrees-with-computed-grade")
    if storedGrade is None:
        reasons.append("stored-grade-missing")
    elif storedGrade != computedGrade:
        reasons.append("stored-grade-differs-from-computed-grade")
    return reasons


def isRecomputationOnly(storedLevel: Any, computedGrade: str, storedGrade: Any) -> bool:
    """True when refreshing the stamp cannot change what the skill is rated.

    The computed grade agrees with the stored star level, **and** the stamp
    already stores exactly that grade. ``storedGrade`` is required and ``None``
    is a hold: a partial stamp must never gain an ``overallTrustGrade`` through a
    "recomputation". The Steward sensor and the verb share this one function.
    """

    return not holdReasons(storedLevel, computedGrade, storedGrade)


def hasStamp(skill: Mapping[str, Any]) -> bool:
    return any(skill.get(name) is not None for name in stampFields)


def _isNumber(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def staleFields(skill: Mapping[str, Any], computedTM: float, computedGrade: str, inputHash: str) -> list[str]:
    """Which existing stamp fields no longer match what the engine computes now.

    Only fields the record carries are judged, so an unstamped skill is never
    stale. The Steward sensor and the restamp gate both use this, so grade-only
    and hash-only staleness is detected, not just a moved Trust Magnitude.
    """

    stale: list[str] = []
    stored = skill.get("trustMagnitude")
    if stored is not None and (not _isNumber(stored) or abs(float(stored) - computedTM) > roundingTolerance):
        stale.append("trustMagnitude")
    if skill.get("overallTrustGrade") is not None and skill.get("overallTrustGrade") != computedGrade:
        stale.append("overallTrustGrade")
    if skill.get("trustMagnitudeInputHash") is not None and skill.get("trustMagnitudeInputHash") != inputHash:
        stale.append("trustMagnitudeInputHash")
    return stale


def stampIsStale(skill: Mapping[str, Any], computedTM: float, computedGrade: str, inputHash: str) -> bool:
    return bool(staleFields(skill, computedTM, computedGrade, inputHash))


def stampProblems(skill: Mapping[str, Any], computedTM: float, computedGrade: str, inputHash: str) -> list[str]:
    """Strict verification of a freshly written stamp: all three fields present and matching."""

    problems = [f"{name} is missing" for name in stampFields if skill.get(name) is None]
    problems += [f"{name} is stale" for name in staleFields(skill, computedTM, computedGrade, inputHash)]
    return problems


@dataclass(frozen=True)
class TrustFingerprint:
    """Everything that decides a skill's stamp: TM, grade and own-input hash."""

    tm: float
    grade: str
    inputHash: str


def _namedSkills(skillMap: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        skillId: skill
        for skillId, skill in skillMap.items()
        if skill.get("status") == "named" and skill.get("contributor")
    }


def _fingerprints(skillMap: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, TrustFingerprint], list[str]]:
    from gaia_cli.trustMagnitude import (
        computeOverallTrustGradeFromSkill,
        computeTrustMagnitude,
        computeTrustMagnitudeInputHash,
    )

    values: dict[str, TrustFingerprint] = {}
    unevaluable: list[str] = []
    for skillId, skill in sorted(_namedSkills(skillMap).items()):
        try:
            values[skillId] = TrustFingerprint(
                tm=computeTrustMagnitude(skill, skillMap),
                grade=computeOverallTrustGradeFromSkill(skill, skillMap),
                inputHash=computeTrustMagnitudeInputHash(skill),
            )
        except (ValueError, TypeError, KeyError, AttributeError):
            unevaluable.append(skillId)
    return values, unevaluable


class TrustSnapshot(dict):
    """``{skill id: TrustFingerprint}`` plus the named skills whose fingerprint failed.

    A skill that cannot be fingerprinted is never silently dropped: its id is kept
    in ``unevaluable`` so the restamp can hold or report it instead of treating it
    as unaffected.
    """

    unevaluable: tuple[str, ...] = ()


def namedTrustSnapshot(registryPath: str = ".") -> TrustSnapshot:
    """Fingerprint of every named skill, read-only; failures are kept, not dropped."""

    from gaia_cli.registryMaps import buildMergedSkillMap

    values, unevaluable = _fingerprints(buildMergedSkillMap(registryPath))
    snapshot = TrustSnapshot(values)
    snapshot.unevaluable = tuple(unevaluable)
    return snapshot


@dataclass(frozen=True)
class ProtectedState:
    """What a restamp must leave exactly as it found it."""

    levels: Mapping[str, Any]
    storedGrades: Mapping[str, Any]
    computedGrades: Mapping[str, str]
    frozen: frozenset
    origins: Mapping[str, frozenset]
    digests: Mapping[str, str]
    unevaluable: frozenset = frozenset()


def _recordDigests(registryPath: str) -> dict[str, str]:
    """sha256 of every named record's bytes, keyed by the skill id in its frontmatter."""

    import yaml

    from gaia_cli.registry import named_skills_dir

    digests: dict[str, str] = {}
    root = Path(named_skills_dir(registryPath))
    if not root.exists():
        return digests
    for path in sorted(root.rglob("*.md")):
        raw = path.read_bytes()
        try:
            parts = raw.decode("utf-8").split("---", 2)
            meta = yaml.safe_load(parts[1]) if len(parts) >= 3 else None
        except (UnicodeDecodeError, yaml.YAMLError):
            meta = None
        key = meta.get("id") if isinstance(meta, dict) and meta.get("id") else f"path:{path.name}"
        digests[str(key)] = hashlib.sha256(raw).hexdigest()
    return digests


def protectedState(registryPath: str) -> ProtectedState:
    """Fresh read of level, grades, frozen set, Origin standings and record bytes."""

    from gaia_cli.frozen import frozenIds
    from gaia_cli.origin import contenderPool, registryOrigins
    from gaia_cli.registryMaps import buildMergedSkillMap

    skillMap = buildMergedSkillMap(registryPath)
    named = _namedSkills(skillMap)
    fingerprints, unevaluable = _fingerprints(skillMap)
    try:
        origins = {ref: frozenset(holders) for ref, holders in registryOrigins(contenderPool(registryPath, skillMap)).items()}
    except ValueError as exc:
        raise RestampVerificationError(f"cannot derive Origin standings to protect: {exc}") from exc
    return ProtectedState(
        levels={skillId: skill.get("level") for skillId, skill in named.items()},
        storedGrades={skillId: skill.get("overallTrustGrade") for skillId, skill in named.items()},
        computedGrades={skillId: item.grade for skillId, item in fingerprints.items()},
        frozen=frozenset(frozenIds(named.values())),
        origins=origins,
        digests=_recordDigests(registryPath),
        unevaluable=frozenset(unevaluable),
    )


@dataclass(frozen=True)
class RestampReport:
    trigger: str
    affected: tuple[str, ...] = ()
    restamped: tuple[str, ...] = ()
    current: tuple[str, ...] = ()
    unstamped: tuple[str, ...] = ()
    frozen: tuple[str, ...] = ()
    unevaluable: tuple[str, ...] = ()
    held: tuple[Mapping[str, Any], ...] = ()
    verified: bool = False
    levels: Mapping[str, Any] = field(default_factory=dict)

    def toDict(self) -> dict[str, Any]:
        return {
            "trigger": self.trigger,
            "affected": list(self.affected),
            "restamped": list(self.restamped),
            "current": list(self.current),
            "unstamped": list(self.unstamped),
            "frozen": list(self.frozen),
            "unevaluable": list(self.unevaluable),
            "held": [dict(item) for item in self.held],
            "verified": self.verified,
        }


def affectedSkillIds(
    before: Mapping[str, TrustFingerprint],
    after: Mapping[str, TrustFingerprint],
    targetId: str | None = None,
) -> tuple[str, ...]:
    """Named skills whose TM, grade or own-input hash moved, plus the one written directly."""

    ids = {
        skillId
        for skillId, now in after.items()
        if skillId in before
        and (
            abs(now.tm - before[skillId].tm) > movementEpsilon
            or now.grade != before[skillId].grade
            or now.inputHash != before[skillId].inputHash
        )
    }
    if targetId and targetId in after:
        ids.add(targetId)
    return tuple(sorted(ids))


def restampAfterEvidenceChange(
    registryPath: str,
    before: Mapping[str, TrustFingerprint],
    *,
    trigger: str,
    targetId: str | None = None,
    dryRun: bool = False,
) -> RestampReport:
    """Restamp only the skills an evidence write affected, when that is a pure recomputation.

    This is the shared write boundary. It requires an authorized operator and
    holds the canonical transaction lock for the whole read, write and verify
    sequence (re-entrant under the CLI dispatcher, which already holds it), so a
    direct call cannot bypass either. ``before`` is :func:`namedTrustSnapshot`
    taken before the evidence write.
    """

    return _restampLocked(registryPath, before, trigger=trigger, targetId=targetId, dryRun=dryRun)


def _restampLocked(
    registryPath: str,
    before: Mapping[str, TrustFingerprint],
    *,
    trigger: str,
    targetId: str | None,
    dryRun: bool,
) -> RestampReport:
    """The guarded restamp body: it authorizes and locks itself, so no caller can skip either."""

    from gaia_cli.authz import require_operator
    from gaia_cli.canonicalTransaction import canonicalTransactionLock

    require_operator("dev restamp-trust", registryPath)
    with canonicalTransactionLock(registryPath):
        return _restampBody(registryPath, before, trigger=trigger, targetId=targetId, dryRun=dryRun)


def _restampBody(
    registryPath: str,
    before: Mapping[str, TrustFingerprint],
    *,
    trigger: str,
    targetId: str | None,
    dryRun: bool,
) -> RestampReport:
    from gaia_cli.commands.dev.calibrate import calibrate_trust_magnitude_command
    from gaia_cli.frozen import frozenIds
    from gaia_cli.registryMaps import buildMergedSkillMap

    skillMap = buildMergedSkillMap(registryPath)
    after, unevaluable = _fingerprints(skillMap)
    named = _namedSkills(skillMap)
    frozen = frozenIds(named.values())
    affected = affectedSkillIds(before, after, targetId)
    # A skill whose fingerprint could not be computed before OR after the write
    # cannot be proven unaffected. It is held and reported, never skipped silently.
    unproven = sorted(
        (set(getattr(before, "unevaluable", ())) | set(unevaluable)
         | {skillId for skillId in after if skillId not in before}
         | {skillId for skillId in before if skillId not in after})
        & set(named)
    )

    toRestamp: list[str] = []
    current: list[str] = []
    unstamped: list[str] = []
    frozenSkipped: list[str] = []
    held: list[dict[str, Any]] = []
    levels: dict[str, Any] = {}
    for skillId in unproven:
        if skillId in frozen or not hasStamp(named[skillId]):
            continue
        side = "before" if skillId in getattr(before, "unevaluable", ()) or skillId not in before else "after"
        held.append({
            "skillId": skillId,
            "storedLevel": named[skillId].get("level"),
            "storedGrade": named[skillId].get("overallTrustGrade"),
            "computedGrade": None,
            "reason": f"fingerprint could not be computed {side} the evidence write: affected status is unproven, so the stamp is left unchanged",
        })
    for skillId in affected:
        if skillId in unproven:
            continue
        skill = named[skillId]
        if skillId in frozen:
            frozenSkipped.append(skillId)
            continue
        if not hasStamp(skill):
            unstamped.append(skillId)
            continue
        now = after[skillId]
        if not stampIsStale(skill, now.tm, now.grade, now.inputHash):
            current.append(skillId)
            continue
        reasons = holdReasons(skill.get("level"), now.grade, skill.get("overallTrustGrade"))
        if reasons:
            held.append({
                "skillId": skillId,
                "storedLevel": skill.get("level"),
                "storedGrade": skill.get("overallTrustGrade"),
                "computedGrade": now.grade,
                "holdReasons": reasons,
                "reason": f"not a pure recomputation ({', '.join(reasons)}): a governed trust question",
            })
            continue
        toRestamp.append(skillId)
        levels[skillId] = skill.get("level")

    restamped: list[str] = []
    verified = False
    if toRestamp:
        guarded = protectedState(registryPath)
        result = calibrate_trust_magnitude_command(SimpleNamespace(
            registry=registryPath,
            skill=list(toRestamp),
            all=False,
            dry_run=dryRun,
            yes=True,
            no_build=True,
            refresh_apex=False,
            recomputation_only=True,
            restamp_trigger=trigger,
        ))
        # An omitted or inconsistent writer result is never assumed to mean success.
        if not isinstance(result, Mapping) or not {"changed", "unchanged", "held"} <= set(result):
            raise RestampVerificationError("the restamp writer returned no result; nothing can be assumed written")
        if set(result["changed"]) != set(toRestamp):
            raise RestampVerificationError(
                f"the restamp writer reported {sorted(result['changed'])} but {sorted(toRestamp)} were intended; "
                f"unchanged={sorted(result['unchanged'])} held={[item.get('skillId') for item in result['held']]}"
            )
        restamped = sorted(toRestamp)
        if not dryRun:
            verifyRestamp(registryPath, restamped, guarded)
            verified = True
    return RestampReport(
        trigger=trigger,
        affected=affected,
        restamped=tuple(restamped),
        current=tuple(current),
        unstamped=tuple(unstamped),
        frozen=tuple(frozenSkipped),
        unevaluable=tuple(sorted(set(unevaluable) | set(getattr(before, "unevaluable", ())))),
        held=tuple(held),
        verified=verified,
        levels=levels,
    )


def verifyRestamp(
    registryPath: str,
    targets: list[str] | tuple[str, ...],
    guarded: ProtectedState,
) -> None:
    """Independently re-read the registry and prove the restamp wrote exactly its targets.

    ``guarded`` is a :func:`protectedState` taken before the write. Raises
    :class:`RestampVerificationError` listing every violation: a target that was
    not written, a stamp with a missing or stale field, a stored grade that
    changed, any level, computed grade, frozen state or Origin standing that
    moved, or any non-target record whose bytes changed.
    """

    from gaia_cli.registryMaps import buildMergedSkillMap
    from gaia_cli.trustMagnitude import computeTrustMagnitudeInputHash

    skillMap = buildMergedSkillMap(registryPath)
    named = _namedSkills(skillMap)
    fingerprints, _ = _fingerprints(skillMap)
    now = protectedState(registryPath)
    violations: list[str] = []
    targetSet = set(targets)
    for skillId in targets:
        skill = named.get(skillId)
        fingerprint = fingerprints.get(skillId)
        if skill is None or fingerprint is None:
            violations.append(f"{skillId}: record not found or not evaluable after restamp")
            continue
        if skillId in guarded.frozen or skillId in now.frozen:
            violations.append(f"{skillId}: frozen skill was restamped")
        violations += [
            f"{skillId}: {problem}"
            for problem in stampProblems(skill, fingerprint.tm, fingerprint.grade, computeTrustMagnitudeInputHash(skill))
        ]
        previousGrade = guarded.storedGrades.get(skillId)
        if skill.get("overallTrustGrade") != previousGrade:
            violations.append(f"{skillId}: stored grade changed {previousGrade!r} -> {skill.get('overallTrustGrade')!r}")
        reasons = holdReasons(skill.get("level"), fingerprint.grade, previousGrade)
        if reasons:
            violations.append(f"{skillId}: restamp is not a pure recomputation ({', '.join(reasons)})")
        if guarded.digests.get(skillId) == now.digests.get(skillId):
            violations.append(f"{skillId}: record bytes are unchanged, so the intended write did not happen")
    for skillId, level in guarded.levels.items():
        if now.levels.get(skillId) != level:
            violations.append(f"{skillId}: star level moved {level!r} -> {now.levels.get(skillId)!r}")
    for skillId, grade in guarded.computedGrades.items():
        if now.computedGrades.get(skillId) != grade:
            violations.append(f"{skillId}: computed grade moved {grade!r} -> {now.computedGrades.get(skillId)!r}")
    if now.unevaluable != guarded.unevaluable:
        violations.append(f"fingerprint evaluability changed during the restamp: {sorted(now.unevaluable ^ guarded.unevaluable)}")
    if now.frozen != guarded.frozen:
        violations.append(f"frozen set changed: {sorted(now.frozen ^ guarded.frozen)}")
    if now.origins != guarded.origins:
        moved = sorted(ref for ref in set(now.origins) | set(guarded.origins) if now.origins.get(ref) != guarded.origins.get(ref))
        violations.append(f"Origin standing moved in bucket(s) {moved}")
    for skillId, digest in guarded.digests.items():
        if skillId not in targetSet and now.digests.get(skillId) != digest:
            violations.append(f"{skillId}: non-target record was modified")
    for skillId in set(now.digests) - set(guarded.digests):
        violations.append(f"{skillId}: record appeared during restamp")
    if violations:
        raise RestampVerificationError("; ".join(violations))
