"""Deterministic, read-only Yggdrasil IV Trust Magnitude shadow evaluation.

This module is an opt-in comparison seam. It never writes registry data and
never changes the default production scoring path.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from gaia_cli import trustMagnitude as tm
from gaia_cli.grading import derive_grade, derive_row_grade

SHADOW_ENGINE_VERSION = "gaia-tm-shadow-v1"


@dataclass(frozen=True)
class ShadowEvaluationContext:
    evaluationAtUTC: datetime.datetime
    policyVersion: str
    policyDigest: str
    benchmarkCatalog: dict[str, Any]
    benchmarkCatalogDigest: str
    registryRevision: str
    canonicalInputDigest: str
    genericSkillMap: dict[str, dict[str, Any]]
    namedSkillMap: dict[str, dict[str, Any]]
    verifierStanding: dict[str, bool]
    perRowGradeThresholds: dict[str, Any]
    gradeCeiling: dict[str, str]
    gradeThresholds: dict[str, float]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _contextProblem(skill: dict, context: ShadowEvaluationContext) -> str | None:
    if not isinstance(context.evaluationAtUTC, datetime.datetime) or context.evaluationAtUTC.tzinfo is None:
        return "evaluationAtUTC must be timezone-aware UTC"
    if context.evaluationAtUTC.utcoffset() != datetime.timedelta(0):
        return "evaluationAtUTC must be UTC"
    for field in ("policyVersion", "policyDigest", "benchmarkCatalogDigest", "registryRevision", "canonicalInputDigest"):
        if not getattr(context, field):
            return f"missing required context: {field}"
    if not isinstance(context.benchmarkCatalog, dict) or not isinstance(context.benchmarkCatalog.get("benchmarks"), list):
        return "benchmark catalog context is missing or malformed"
    ref = skill.get("genericSkillRef")
    if ref and (not context.genericSkillMap or ref not in context.genericSkillMap):
        return f"generic context not resolved for {ref}"
    evidenceRows = list(skill.get("evidence") or [])
    if ref and ref in context.genericSkillMap:
        evidenceRows.extend(context.genericSkillMap[ref].get("evidence") or [])
    for index, row in enumerate(evidenceRows):
        if tm._typeOf(row) != "verifier-attestation":
            continue
        verifier = row.get("verifierId") or row.get("verifier") or row.get("attestor")
        if verifier and verifier not in context.verifierStanding:
            return f"verifier standing not resolved for row[{index}] {verifier}"
        if not verifier and "verifierActiveRank" not in row and "derank" not in row:
            return f"verifier standing not resolved for row[{index}]"
    return None


def _temporalWarnings(
    skill: dict,
    evaluationAtUTC: datetime.datetime,
    genericSkillMap: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[str], str | None]:
    warnings = []
    sources = [("own", skill.get("evidence") or [])]
    ref = skill.get("genericSkillRef")
    generic = (genericSkillMap or {}).get(ref) if ref else None
    if generic is not None:
        sources.append(("generic", generic.get("evidence") or []))
    for sourceName, rows in sources:
        for index, row in enumerate(rows):
            for field in ("lastVerified", "sourceStartedAt"):
                raw = row.get(field)
                if raw in (None, ""):
                    continue
                parsed = tm._parseIso(raw)
                label = f"{sourceName}[{index}].{field}"
                if parsed is None:
                    warnings.append(f"{label}: malformed legacy date; treated as unknown")
                elif parsed > evaluationAtUTC:
                    return warnings, f"{label}: future date after pinned evaluation time"
    return warnings, None


def _cloneWithStanding(skill: dict, standing: dict[str, bool]) -> dict:
    clone = dict(skill)
    rows = []
    for original in skill.get("evidence") or []:
        row = dict(original)
        if tm._typeOf(row) == "verifier-attestation":
            verifier = row.get("verifierId") or row.get("verifier") or row.get("attestor")
            if verifier and verifier in standing:
                row["verifierActiveRank"] = standing[verifier]
        rows.append(row)
    clone["evidence"] = rows
    return clone


def _correctionCauses(
    skill: dict,
    context: ShadowEvaluationContext,
    rowReport: list[dict[str, Any]],
    computedNamed: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify the four RFC implementation-correction families independently."""
    effective = tm._effectivePool(skill, context.genericSkillMap, shadowCorrections=True)
    sourceTypes: dict[str, set[str]] = {}
    for row in effective:
        source = row.get("source")
        if source:
            sourceTypes.setdefault(str(source), set()).add(tm._typeOf(row) or "")
    inheritanceConflict = any(len(types) > 1 for types in sourceTypes.values()) or bool(
        skill.get("genericSkillRef") and any(
            not (row.get("source") or row.get("url") or row.get("sourceUrl"))
            for row in skill.get("evidence") or []
        )
    )

    candidates: dict[tuple[str, str], list[Optional[float]]] = {}
    scoredSkill = _cloneWithStanding(skill, context.verifierStanding)
    for row in effective:
        row = dict(row)
        verifier = row.get("verifierId") or row.get("verifier") or row.get("attestor")
        if verifier in context.verifierStanding:
            row["verifierActiveRank"] = context.verifierStanding[verifier]
        url = tm._canonicalUrl(row.get("source")) or tm._canonicalUrl(row.get("url")) or tm._canonicalUrl(row.get("sourceUrl"))
        if not url:
            continue
        score = tm.computeArtifactScoreOrNone(
            row, context.genericSkillMap, evaluationAtUTC=context.evaluationAtUTC,
            benchmarkCatalog=context.benchmarkCatalog,
        )
        candidates.setdefault((tm._typeOf(row) or "", url), []).append(score)
    eligibilityConflict = any(
        any(score is None for score in scores) and any(score is not None and score > 0 for score in scores)
        for scores in candidates.values()
    )
    componentDrift = any(
        (context.namedSkillMap.get(component) or {}).get("overallTrustGrade")
        != (computedNamed.get(component) or {}).get("overallTrustGrade")
        for component in skill.get("suiteComponents") or []
        if component in computedNamed
    )
    rowGradeDrift = any(
        item["gradeDiffers"] or item["trustNumberFallback"] for item in rowReport
    )
    causes = [
        ("source-only-inheritance-merge", inheritanceConflict,
         "same-source evidence has distinct Evidence Types or row origins"),
        ("eligibility-before-dedup", eligibilityConflict,
         "same-type URL group contains both ineligible and scoring rows"),
        ("component-before-suite-grade", componentDrift,
         "a suite component grade differs from its shadow-recomputed grade"),
        ("named-row-grade-context", rowGradeDrift,
         "stored row grade differs from contextual grade or trustNumber fallback is present"),
    ]
    return [{
        "cause": name,
        "classification": "implementation-correction",
        "status": "triggered" if triggered else "not-triggered",
        "evidence": detail if triggered else None,
    } for name, triggered, detail in causes]


def _rowGradeReport(skill: dict, genericMap: dict, context: ShadowEvaluationContext) -> list[dict[str, Any]]:
    out = []
    contextualSkill = _cloneWithStanding(skill, context.verifierStanding)
    for index, raw in enumerate(skill.get("evidence") or []):
        row = dict(raw)
        row.setdefault("layer", "named" if skill.get("genericSkillRef") else "generic")
        score = tm._finalRowScore(
            row, contextualSkill, genericMap,
            evaluationAtUTC=context.evaluationAtUTC,
            benchmarkCatalog=context.benchmarkCatalog,
        )
        kind = tm._typeOf(row) or ""
        grade = derive_row_grade(
            0.0 if score is None else score, kind,
            context.perRowGradeThresholds, context.gradeCeiling.get(kind),
        )
        fallbackGrade = None
        if (score is None or score <= 0) and row.get("trustNumber") is not None:
            fallbackGrade = derive_grade(row["trustNumber"], context.gradeThresholds)
        out.append({
            "index": index,
            "type": kind,
            "source": row.get("source") or row.get("url") or row.get("sourceUrl"),
            "storedGrade": row.get("grade") or row.get("class"),
            "contextualGrade": grade,
            "gradeDiffers": (row.get("grade") or row.get("class")) != grade,
            "trustNumberFallback": fallbackGrade is not None,
            "trustNumberFallbackGrade": fallbackGrade,
            "artifactScore": score,
            "gateGradeRisk": fallbackGrade in {"A", "S"} and grade not in {"A", "S"},
        })
    return out


def _assessOne(skill: dict, context: ShadowEvaluationContext, computedNamed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    genericMap = context.genericSkillMap
    scoredSkill = _cloneWithStanding(skill, context.verifierStanding)
    namedMap = {key: dict(value) for key, value in computedNamed.items()}
    sid = scoredSkill.get("id")
    tmRaw = tm.computeTrustMagnitude(
        scoredSkill, genericMap, namedMap,
        evaluationAtUTC=context.evaluationAtUTC,
        benchmarkCatalog=context.benchmarkCatalog,
        shadowCorrections=True,
    )
    rows = tm._scoredEvidenceRows(
        scoredSkill, genericMap, evaluationAtUTC=context.evaluationAtUTC,
        benchmarkCatalog=context.benchmarkCatalog, shadowCorrections=True,
    )
    positive = [(row, score) for row, score in rows if score is not None and score > 0]
    distinct = len({tm._typeOf(row) for row, _ in positive})
    witness = any(tm._isEligibleWitnessRow(row, score, scoredSkill) for row, score in rows)
    grade = tm.computeOverallTrustGrade(tmRaw, distinct, witness)
    rowReport = _rowGradeReport(scoredSkill, genericMap, context)
    gateSkill = dict(scoredSkill)
    gateRows = []
    for index, row in enumerate(scoredSkill.get("evidence") or []):
        contextualRow = {**row, "grade": rowReport[index]["contextualGrade"]}
        contextualRow.pop("class", None)
        gateRows.append(contextualRow)
    gateSkill["evidence"] = gateRows
    gradeRow = {**scoredSkill, "overallTrustGrade": grade, "overallGrade": grade, "grade": grade, "_shadowAssessed": True}
    if sid:
        computedNamed[sid] = gradeRow
    state = {"genericSkillMap": genericMap, "namedSkillMap": computedNamed}
    branch = "suite" if scoredSkill.get("suiteComponents") is not None else "unique"
    gates = (
        tm.passesSuiteApexGate(
            gateSkill, state, evaluationAtUTC=context.evaluationAtUTC,
            benchmarkCatalog=context.benchmarkCatalog, shadowCorrections=True,
        )
        if branch == "suite"
        else tm.checkUniqueImpossibleGate(
            gateSkill, state, evaluationAtUTC=context.evaluationAtUTC,
            benchmarkCatalog=context.benchmarkCatalog, shadowCorrections=True,
        )
    ) if grade == "S" else None
    ceiling = {"ungraded": 1, "C": 2, "B": 3, "A": 4, "S": 5}.get(grade, 1)
    gateFailures = None
    if gates is not None:
        if branch == "suite":
            for component in scoredSkill.get("suiteComponents") or []:
                if component not in genericMap and not (computedNamed.get(component) or {}).get("_shadowAssessed"):
                    gates["aGradedOriginsGte5"] = None
                    break
        gateFailures = {key: value for key, value in gates.items() if value is False}
        requiredPredicates = {
            key: value for key, value in gates.items()
            if key not in {"crossOrgVerifier", "systemWideCap"}
        }
        if not gateFailures and all(value is True for value in requiredPredicates.values()):
            ceiling = 6
    return {
        "status": "evaluated",
        "skillId": sid,
        "scope": "effective named" if scoredSkill.get("genericSkillRef") else "generic",
        "tmRaw": tmRaw,
        "tmRounded": round(tmRaw, 2),
        "grade": grade,
        "canonicalStars": scoredSkill.get("level"),
        "gradeCeilingProposal": ceiling,
        "gateFailures": gateFailures,
        "gatePredicates": gates,
        "rows": rowReport,
        "correctionCauses": _correctionCauses(scoredSkill, context, rowReport, computedNamed),
        "namedMapDependencyGrades": {key: value.get("overallTrustGrade") for key, value in computedNamed.items()},
    }


def evaluateShadow(skill: dict, context: ShadowEvaluationContext) -> dict[str, Any]:
    """Evaluate one skill using an explicit immutable context; report proposals only.

    A caller evaluating a registry in dependency order may pass each returned
    assessment into ``computedNamed`` via ``evaluateShadowRegistry`` below.
    """
    problem = _contextProblem(skill, context)
    if problem:
        return {"status": "not-evaluated", "reason": problem, "skillId": skill.get("id")}
    warnings, dateProblem = _temporalWarnings(skill, context.evaluationAtUTC, context.genericSkillMap)
    if dateProblem:
        return {"status": "not-evaluated", "reason": dateProblem, "skillId": skill.get("id")}
    assessed = _assessOne(skill, context, {key: dict(value) for key, value in context.namedSkillMap.items()})
    assessed["temporalWarnings"] = warnings
    assessed["fingerprint"] = _digest({
        "api": SHADOW_ENGINE_VERSION, "skill": skill,
        "genericSkillMap": context.genericSkillMap,
        "namedSkillMap": context.namedSkillMap,
        "verifierStanding": context.verifierStanding,
        "policyVersion": context.policyVersion, "policyDigest": context.policyDigest,
        "catalog": context.benchmarkCatalog, "catalogDigest": context.benchmarkCatalogDigest,
        "evaluationAtUTC": context.evaluationAtUTC.isoformat(),
        "registryRevision": context.registryRevision,
        "canonicalInputDigest": context.canonicalInputDigest,
        "perRowGradeThresholds": context.perRowGradeThresholds,
        "gradeCeiling": context.gradeCeiling,
        "gradeThresholds": context.gradeThresholds,
        "engine": "trustMagnitude-v1", "rowGrades": assessed["rows"],
    })
    assessed["correctionDelta"] = {
        "legacyTM": tm.computeTrustMagnitude(
            skill, context.genericSkillMap, evaluationAtUTC=context.evaluationAtUTC,
            benchmarkCatalog=context.benchmarkCatalog,
        ),
        "shadowTM": assessed["tmRaw"],
        "implementationCorrection": assessed["tmRaw"] - tm.computeTrustMagnitude(
            skill, context.genericSkillMap, evaluationAtUTC=context.evaluationAtUTC,
            benchmarkCatalog=context.benchmarkCatalog,
        ),
    }
    return assessed


def evaluateShadowRegistry(skills: list[dict], context: ShadowEvaluationContext) -> dict[str, Any]:
    """Evaluate a bounded registry in component-before-suite dependency order."""
    problem = _contextProblem({"genericSkillRef": None}, context)
    if problem:
        return {"status": "not-evaluated", "reason": problem, "assessments": []}
    temporalById = {}
    for skill in skills:
        problem = _contextProblem(skill, context)
        if problem:
            return {"status": "not-evaluated", "reason": problem, "skillId": skill.get("id"), "assessments": []}
        warnings, dateProblem = _temporalWarnings(skill, context.evaluationAtUTC, context.genericSkillMap)
        if dateProblem:
            return {"status": "not-evaluated", "reason": dateProblem, "skillId": skill.get("id"), "assessments": []}
        temporalById[skill.get("id")] = warnings
    byId = {skill.get("id"): skill for skill in skills if skill.get("id")}
    pending = dict(byId)
    computed = {key: dict(value) for key, value in context.namedSkillMap.items()}
    assessments = {}
    while pending:
        ready = sorted(
            (key for key, item in pending.items()
             if all(component not in pending for component in (item.get("suiteComponents") or []))),
        )
        if not ready:
            return {"status": "not-evaluated", "reason": "component dependency cycle", "assessments": list(assessments.values())}
        for sid in ready:
            skill = pending.pop(sid)
            assessment = _assessOne(skill, context, computed)
            assessment["temporalWarnings"] = temporalById.get(sid, [])
            assessment["fingerprint"] = _digest({
                "api": SHADOW_ENGINE_VERSION, "skill": skill, "computedDependencies": computed,
                "context": {"time": context.evaluationAtUTC.isoformat(), "policyVersion": context.policyVersion,
                            "policyDigest": context.policyDigest, "catalog": context.benchmarkCatalog,
                            "catalogDigest": context.benchmarkCatalogDigest, "registry": context.registryRevision,
                            "input": context.canonicalInputDigest, "generic": context.genericSkillMap,
                            "named": context.namedSkillMap, "verifiers": context.verifierStanding,
                            "perRowGradeThresholds": context.perRowGradeThresholds,
                            "gradeCeiling": context.gradeCeiling, "gradeThresholds": context.gradeThresholds},
            })
            old = tm.computeTrustMagnitude(
                skill, context.genericSkillMap, evaluationAtUTC=context.evaluationAtUTC,
                benchmarkCatalog=context.benchmarkCatalog,
            )
            assessment["correctionDelta"] = {"legacyTM": old, "shadowTM": assessment["tmRaw"], "implementationCorrection": assessment["tmRaw"] - old}
            assessments[sid] = assessment
    return {"status": "evaluated", "assessments": [assessments[key] for key in sorted(assessments)]}
