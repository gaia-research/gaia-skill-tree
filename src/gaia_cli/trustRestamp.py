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

This module owns the three decisions that make the trigger safe:

* **Which skills are affected.** Computed Trust Magnitude is compared before and
  after the evidence write across every named skill, so a change on a generic
  node reaches every named implementation that inherits from it, and a change
  on a component reaches the suites that count it. The skill that was written
  directly is always affected.
* **Whether a refresh is recomputation-only.** It is when the computed grade
  still agrees with the star level stored on the skill (:func:`isRecomputationOnly`),
  the same predicate the sensor stamps on every ``trust_stamp_stale`` finding.
  Anything else is a governed trust, rank or evidence-policy question: the stamp
  is left stale and held for the desk.
* **That nothing but the stamp moved.** The refresh itself is written by the one
  existing verb, ``gaia dev calibrate-trust-magnitude``, which never writes a
  star level. :func:`verifyRestamp` re-reads the files from disk afterwards and
  proves the level is byte-for-byte unchanged and every stamp is now fresh.

Frozen skills are never touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Mapping

# Overall Trust Grade -> the star level that grade supports. The Steward sensor
# reads this same table, so the sensor's ``recomputationOnly`` and this gate can
# never disagree.
targetLevelByGrade = {"S": "5★", "A": "4★", "B": "3★", "C": "2★", "ungraded": "1★"}

# Stamps are written as round(computeTrustMagnitude(...), 2): a fresh stamp sits
# within the rounding tolerance of the computed value.
roundingTolerance = 0.005
# The Steward sensor reports a stamp as stale beyond this distance.
sensorStampTolerance = 0.02
# Computed TM is deterministic, so any movement above float noise is real.
movementEpsilon = 1e-9

stampFields = ("trustMagnitude", "overallTrustGrade", "trustMagnitudeInputHash")


class RestampVerificationError(RuntimeError):
    """A restamp left something other than a clean, level-preserving refresh."""


def isRecomputationOnly(storedLevel: Any, computedGrade: str) -> bool:
    """True when refreshing the stamp cannot change what the skill is rated.

    The computed grade still agrees with the stored star level, so the new stamp
    describes the same rating as the old one. A skill whose computed grade
    disagrees with its level is a calibration question (Class C), never a
    refresh.
    """

    return targetLevelByGrade.get(computedGrade) == storedLevel


def hasStamp(skill: Mapping[str, Any]) -> bool:
    return any(skill.get(name) is not None for name in stampFields)


def _isNumber(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def stampIsStale(skill: Mapping[str, Any], computedTM: float, computedGrade: str, inputHash: str) -> bool:
    """Whether an existing stamp no longer matches what the engine computes now."""

    if not hasStamp(skill):
        return False
    stored = skill.get("trustMagnitude")
    if not _isNumber(stored) or abs(float(stored) - computedTM) > roundingTolerance:
        return True
    return (
        skill.get("overallTrustGrade") != computedGrade
        or skill.get("trustMagnitudeInputHash") != inputHash
    )


def _namedSkills(skillMap: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        skillId: skill
        for skillId, skill in skillMap.items()
        if skill.get("status") == "named" and skill.get("contributor")
    }


def _computeAll(skillMap: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, float], list[str]]:
    from gaia_cli.trustMagnitude import computeTrustMagnitude

    values: dict[str, float] = {}
    unevaluable: list[str] = []
    for skillId, skill in sorted(_namedSkills(skillMap).items()):
        try:
            values[skillId] = computeTrustMagnitude(skill, skillMap)
        except (ValueError, TypeError, KeyError, AttributeError):
            unevaluable.append(skillId)
    return values, unevaluable


def namedTrustSnapshot(registryPath: str = ".") -> dict[str, float]:
    """Computed Trust Magnitude of every evaluable named skill, read-only."""

    from gaia_cli.registryMaps import buildMergedSkillMap

    return _computeAll(buildMergedSkillMap(registryPath))[0]


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
    before: Mapping[str, float],
    after: Mapping[str, float],
    targetId: str | None = None,
) -> tuple[str, ...]:
    """Named skills whose computed Trust Magnitude moved, plus the one written directly."""

    ids = {
        skillId
        for skillId, value in after.items()
        if skillId in before and abs(value - before[skillId]) > movementEpsilon
    }
    if targetId and targetId in after:
        ids.add(targetId)
    return tuple(sorted(ids))


def restampAfterEvidenceChange(
    registryPath: str,
    before: Mapping[str, float],
    *,
    trigger: str,
    targetId: str | None = None,
    dryRun: bool = False,
) -> RestampReport:
    """Restamp only the skills an evidence write affected, when that is a pure recomputation.

    ``before`` is :func:`namedTrustSnapshot` taken before the evidence write.
    The write itself is ``gaia dev calibrate-trust-magnitude`` with
    ``recomputationOnly`` set, so the verb refuses to refresh a stamp the gate
    holds even if this function were wrong about it.
    """

    from gaia_cli.commands.dev.calibrate import calibrate_trust_magnitude_command
    from gaia_cli.frozen import frozenIds
    from gaia_cli.registryMaps import buildMergedSkillMap
    from gaia_cli.trustMagnitude import computeOverallTrustGradeFromSkill, computeTrustMagnitudeInputHash

    skillMap = buildMergedSkillMap(registryPath)
    after, unevaluable = _computeAll(skillMap)
    named = _namedSkills(skillMap)
    frozen = frozenIds(named.values())
    affected = affectedSkillIds(before, after, targetId)

    toRestamp: list[str] = []
    current: list[str] = []
    unstamped: list[str] = []
    frozenSkipped: list[str] = []
    held: list[dict[str, Any]] = []
    levels: dict[str, Any] = {}
    for skillId in affected:
        skill = named[skillId]
        if skillId in frozen:
            frozenSkipped.append(skillId)
            continue
        if not hasStamp(skill):
            unstamped.append(skillId)
            continue
        grade = computeOverallTrustGradeFromSkill(skill, skillMap)
        if not stampIsStale(skill, after[skillId], grade, computeTrustMagnitudeInputHash(skill)):
            current.append(skillId)
            continue
        if not isRecomputationOnly(skill.get("level"), grade):
            held.append({
                "skillId": skillId,
                "storedLevel": skill.get("level"),
                "computedGrade": grade,
                "reason": "computed grade disagrees with the stored level: a governed trust question, not a recomputation",
            })
            continue
        toRestamp.append(skillId)
        levels[skillId] = skill.get("level")

    restamped: list[str] = []
    if toRestamp:
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
        restamped = sorted((result or {}).get("changed", toRestamp))
        held.extend((result or {}).get("held", ()))
    verified = False
    if restamped and not dryRun:
        verifyRestamp(registryPath, restamped, levels)
        verified = True
    return RestampReport(
        trigger=trigger,
        affected=affected,
        restamped=tuple(restamped),
        current=tuple(current),
        unstamped=tuple(unstamped),
        frozen=tuple(frozenSkipped),
        unevaluable=tuple(unevaluable),
        held=tuple(held),
        verified=verified,
        levels=levels,
    )


def verifyRestamp(
    registryPath: str,
    skillIds: list[str] | tuple[str, ...],
    levelsBefore: Mapping[str, Any],
) -> None:
    """Independently re-read the registry and prove the restamp moved only stamps.

    Reads every record fresh from disk (no state shared with the writer) and
    raises :class:`RestampVerificationError` listing every violation: a star
    level that changed, a grade that no longer agrees with the level, a stamp
    that is still stale, or a skill that is frozen.
    """

    from gaia_cli.frozen import frozenIds
    from gaia_cli.registryMaps import buildMergedSkillMap
    from gaia_cli.trustMagnitude import (
        computeOverallTrustGradeFromSkill,
        computeTrustMagnitude,
        computeTrustMagnitudeInputHash,
    )

    skillMap = buildMergedSkillMap(registryPath)
    named = _namedSkills(skillMap)
    frozen = frozenIds(named.values())
    violations: list[str] = []
    for skillId in skillIds:
        skill = named.get(skillId)
        if skill is None:
            violations.append(f"{skillId}: record not found after restamp")
            continue
        if skillId in frozen:
            violations.append(f"{skillId}: frozen skill was restamped")
        if skill.get("level") != levelsBefore.get(skillId):
            violations.append(f"{skillId}: star level moved {levelsBefore.get(skillId)!r} -> {skill.get('level')!r}")
        grade = computeOverallTrustGradeFromSkill(skill, skillMap)
        if not isRecomputationOnly(skill.get("level"), grade):
            violations.append(f"{skillId}: computed grade {grade} no longer agrees with level {skill.get('level')!r}")
        tm = computeTrustMagnitude(skill, skillMap)
        if stampIsStale(skill, tm, grade, computeTrustMagnitudeInputHash(skill)):
            violations.append(f"{skillId}: stamp is still stale after restamp")
    if violations:
        raise RestampVerificationError("; ".join(violations))
