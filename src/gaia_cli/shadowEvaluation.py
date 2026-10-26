"""Deterministic, read-only Yggdrasil IV Trust Magnitude shadow evaluation.

This module is an opt-in comparison seam. It never writes registry data and
never changes the default production scoring path.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import math
from dataclasses import dataclass, replace
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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")


def _canonicalSkill(skill: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize evidence as an unordered set for identity, not scoring."""
    clone = dict(skill)
    rows = clone.get("evidence")
    if isinstance(rows, list):
        clone["evidence"] = sorted(rows, key=_canonical)
    components = clone.get("suiteComponents")
    if isinstance(components, list):
        clone["suiteComponents"] = sorted(components, key=_canonical)
    return clone


def _canonicalMap(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: _canonicalSkill(value) if isinstance(value, dict) else value
            for key, value in sorted(mapping.items())}


def _canonicalRowReport(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop positional indexes and sort row diagnostics for identity hashing."""
    return sorted(({key: value for key, value in row.items() if key != "index"} for row in rows), key=_canonical)


def _invalidNumericInput(skill: dict[str, Any], genericMap: dict[str, dict[str, Any]]) -> str | None:
    """Reject non-finite/non-numeric TM inputs before scoring can leak NaN."""
    sources = [("skill", skill.get("evidence") or [])]
    ref = skill.get("genericSkillRef")
    if ref and ref in genericMap:
        sources.append((f"generic:{ref}", genericMap[ref].get("evidence") or []))
    for source, rows in sources:
        for index, row in enumerate(rows):
            for key, value in row.items():
                if key not in {"commits", "contributors", "stars", "views", "percentile", "citations", "reviewers", "skillCountInRepo", "externalStars", "verifiers", "score", "trustNumber", "downloads", "likes", "comments"} or value is None:
                    continue
                if isinstance(value, bool):
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError, OverflowError):
                    return f"invalid numeric input {source}[{index}].{key}"
                if not math.isfinite(numeric):
                    return f"non-finite numeric input {source}[{index}].{key}"
    return None


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _policyBinding(context: ShadowEvaluationContext) -> dict[str, Any]:
    """Digest the actual scoring configuration separately from declared labels."""
    actualPolicy = {
        "engine": SHADOW_ENGINE_VERSION,
        "trustMagnitudeEngine": "trustMagnitude-v1",
        "perRowGradeThresholds": context.perRowGradeThresholds,
        "gradeCeiling": context.gradeCeiling,
        "gradeThresholds": context.gradeThresholds,
    }
    return {
        "actualPolicyDigest": _digest(actualPolicy),
        "actualCatalogDigest": _digest(context.benchmarkCatalog),
        "engineVersion": SHADOW_ENGINE_VERSION,
        "declaredPolicyVersion": context.policyVersion,
        "declaredPolicyDigest": context.policyDigest,
        "declaredCatalogDigest": context.benchmarkCatalogDigest,
    }


def _snapshotContext(context: ShadowEvaluationContext) -> ShadowEvaluationContext:
    """Freeze mutable caller-owned maps for one deterministic evaluation."""
    return replace(context, benchmarkCatalog=copy.deepcopy(context.benchmarkCatalog),
                   genericSkillMap=copy.deepcopy(context.genericSkillMap),
                   namedSkillMap=copy.deepcopy(context.namedSkillMap),
                   verifierStanding=copy.deepcopy(context.verifierStanding),
                   perRowGradeThresholds=copy.deepcopy(context.perRowGradeThresholds),
                   gradeCeiling=copy.deepcopy(context.gradeCeiling),
                   gradeThresholds=copy.deepcopy(context.gradeThresholds))


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
    if not isinstance(skill, dict):
        return "skill input must be an object"
    ref = skill.get("genericSkillRef")
    if ref and (not context.genericSkillMap or ref not in context.genericSkillMap):
        return f"generic context not resolved for {ref}"
    evidenceRows = list(skill.get("evidence") or [])
    if any(not isinstance(row, dict) for row in evidenceRows):
        return "evidence rows must be objects"
    if ref and ref in context.genericSkillMap:
        genericNode = context.genericSkillMap[ref]
        if not isinstance(genericNode, dict):
            return f"generic context is malformed for {ref}"
        inheritedRows = list(genericNode.get("evidence") or [])
        if any(not isinstance(row, dict) for row in inheritedRows):
            return f"generic evidence rows must be objects for {ref}"
        evidenceRows.extend(inheritedRows)
    numericProblem = _invalidNumericInput(skill, context.genericSkillMap)
    if numericProblem:
        return numericProblem
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
                elif (parsed.replace(tzinfo=datetime.timezone.utc) if parsed.tzinfo is None else parsed.astimezone(datetime.timezone.utc)) > evaluationAtUTC:
                    return warnings, f"{label}: future date after pinned evaluation time"
    return warnings, None


def _cloneWithStanding(skill: dict, standing: dict[str, bool], *, layer: str | None = None) -> dict:
    clone = dict(skill)
    ownLayer = layer or tm._ownLayerOf(skill)
    rows = []
    for original in skill.get("evidence") or []:
        row = dict(original)
        # Trust actual registry placement, never a caller-supplied row label.
        row["layer"] = ownLayer
        if tm._typeOf(row) == "verifier-attestation":
            verifier = row.get("verifierId") or row.get("verifier") or row.get("attestor")
            if verifier and verifier in standing:
                row["verifierActiveRank"] = standing[verifier]
        rows.append(row)
    clone["evidence"] = rows
    return clone


def _shadowSnapshots(skill: dict, context: ShadowEvaluationContext) -> tuple[dict, dict]:
    """Return isolated layer-correct maps with verifier standing applied everywhere."""
    genericMap = {}
    for sid, node in context.genericSkillMap.items():
        genericMap[sid] = _cloneWithStanding(node, context.verifierStanding, layer="generic")
    # Generic evidence is a real inherited context, so its own row grades and
    # verifier standing must be snapshotted under the same contextual rules.
    for sid, node in list(genericMap.items()):
        genericMap[sid], _ = _withContextualGrades(node, genericMap, context)
    scoredSkill = _cloneWithStanding(skill, context.verifierStanding)
    return scoredSkill, genericMap


def _withContextualGrades(skill: dict, genericMap: dict, context: ShadowEvaluationContext) -> tuple[dict, list[dict[str, Any]]]:
    report = _rowGradeReport(skill, genericMap, context)
    clone = dict(skill)
    clone["evidence"] = []
    for index, raw in enumerate(skill.get("evidence") or []):
        row = dict(raw)
        row["layer"] = tm._ownLayerOf(skill)
        row["grade"] = report[index]["contextualGrade"]
        row.pop("class", None)
        clone["evidence"].append(row)
    return clone, report


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
    scoredSkill, genericMap = _shadowSnapshots(skill, context)
    scoredSkill, rowReport = _withContextualGrades(scoredSkill, genericMap, context)
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
    # Expose raw artifact magnitude separately from the actual post-dedup,
    # plateau and suite-component-cap contribution used in total TM.
    scoreByKey = {}
    for actualRow, bounded in rows:
        key = (tm._typeOf(actualRow), tm._canonicalUrl(actualRow.get("source") or actualRow.get("url") or actualRow.get("sourceUrl")))
        scoreByKey.setdefault(key, []).append(bounded)
    for item in rowReport:
        key = (item["type"], tm._canonicalUrl(item["source"]))
        item["rawArtifactScore"] = item["artifactScore"]
        item["boundedArtifactScore"] = next(iter(scoreByKey.get(key, [])), None)
        item["artifactScoreMeaning"] = "raw pre-plateau/pre-suite-cap artifact score"
        item["contextualGradeBasis"] = "raw artifact score before plateau and suite component cap"
    gateSkill = dict(scoredSkill)
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
        "correctionCauses": _correctionCauses(
            scoredSkill, replace(context, genericSkillMap=genericMap), rowReport, computedNamed
        ),
        "namedMapDependencyGrades": {key: value.get("overallTrustGrade") for key, value in computedNamed.items()},
    }


def evaluateShadow(skill: dict, context: ShadowEvaluationContext) -> dict[str, Any]:
    """Evaluate one skill using an explicit immutable context; report proposals only.

    A caller evaluating a registry in dependency order may pass each returned
    assessment into ``computedNamed`` via ``evaluateShadowRegistry`` below.
    """
    context = _snapshotContext(context)
    problem = _contextProblem(skill, context)
    if problem:
        return {"status": "not-evaluated", "reason": problem, "skillId": skill.get("id")}
    warnings, dateProblem = _temporalWarnings(skill, context.evaluationAtUTC, context.genericSkillMap)
    if dateProblem:
        return {"status": "not-evaluated", "reason": dateProblem, "skillId": skill.get("id")}
    assessed = _assessOne(skill, context, {key: dict(value) for key, value in context.namedSkillMap.items()})
    assessed["temporalWarnings"] = warnings
    assessed["contextBinding"] = _policyBinding(context)
    assessed["fingerprint"] = _digest({
        "api": SHADOW_ENGINE_VERSION, "contextBinding": assessed["contextBinding"], "skill": _canonicalSkill(skill),
        "genericSkillMap": _canonicalMap(context.genericSkillMap),
        "namedSkillMap": _canonicalMap(context.namedSkillMap),
        "verifierStanding": context.verifierStanding,
        "policyVersion": context.policyVersion, "policyDigest": context.policyDigest,
        "catalog": context.benchmarkCatalog, "catalogDigest": context.benchmarkCatalogDigest,
        "evaluationAtUTC": context.evaluationAtUTC.isoformat(),
        "registryRevision": context.registryRevision,
        "canonicalInputDigest": context.canonicalInputDigest,
        "perRowGradeThresholds": context.perRowGradeThresholds,
        "gradeCeiling": context.gradeCeiling,
        "gradeThresholds": context.gradeThresholds,
        "engine": "trustMagnitude-v1", "rowGrades": _canonicalRowReport(assessed["rows"]),
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
    """Evaluate a bounded registry; invalid rows and cycles retain partial coverage."""
    context = _snapshotContext(context)
    baseProblem = _contextProblem({"genericSkillRef": None}, context)
    if baseProblem:
        rows = [{"status": "not-evaluated", "skillId": skill.get("id"), "reason": baseProblem} for skill in skills]
        return {"status": "not-evaluated", "reason": baseProblem, "coverage": {"total": len(skills), "evaluated": 0, "notEvaluated": len(rows)}, "assessments": rows}

    byId = {}
    inputFailures = []
    duplicateIds = set()
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict) or not skill.get("id"):
            inputFailures.append({"status": "not-evaluated", "skillId": None, "inputIndex": index,
                                  "reason": "skill input requires an id"})
            continue
        sid = skill["id"]
        if sid in byId:
            duplicateIds.add(sid)
            inputFailures.append({"status": "not-evaluated", "skillId": sid, "inputIndex": index,
                                  "reason": "duplicate skill id in registry input"})
        else:
            byId[sid] = skill
    pending = dict(byId)
    computed = {key: dict(value) for key, value in context.namedSkillMap.items()}
    assessments: dict[str, dict[str, Any]] = {}
    for sid in duplicateIds:
        assessments[sid] = {"status": "not-evaluated", "skillId": sid,
                            "reason": "duplicate skill id in registry input"}
        pending.pop(sid, None)
    temporalById = {}
    for sid, skill in list(pending.items()):
        problem = _contextProblem(skill, context)
        if problem:
            assessments[sid] = {"status": "not-evaluated", "skillId": sid, "reason": problem}
            pending.pop(sid)
            continue
        warnings, dateProblem = _temporalWarnings(skill, context.evaluationAtUTC, context.genericSkillMap)
        if dateProblem:
            assessments[sid] = {"status": "not-evaluated", "skillId": sid, "reason": dateProblem}
            pending.pop(sid)
            continue
        temporalById[sid] = warnings

    while pending:
        ready = sorted(key for key, item in pending.items()
                       if all(component not in pending for component in (item.get("suiteComponents") or [])))
        if not ready:
            for sid in sorted(pending):
                assessments[sid] = {"status": "not-evaluated", "skillId": sid, "reason": "component dependency cycle"}
            pending.clear()
            break
        for sid in ready:
            skill = pending.pop(sid)
            assessment = _assessOne(skill, context, computed)
            assessment["temporalWarnings"] = temporalById.get(sid, [])
            assessment["contextBinding"] = _policyBinding(context)
            assessment["fingerprint"] = _digest({
                "api": SHADOW_ENGINE_VERSION, "contextBinding": assessment["contextBinding"],
                "skill": _canonicalSkill(skill), "computedDependencies": _canonicalMap(computed),
                "context": {"time": context.evaluationAtUTC.isoformat(), "policyVersion": context.policyVersion,
                            "policyDigest": context.policyDigest, "catalog": context.benchmarkCatalog,
                            "catalogDigest": context.benchmarkCatalogDigest, "registry": context.registryRevision,
                            "input": context.canonicalInputDigest,
                            "generic": _canonicalMap(context.genericSkillMap),
                            "named": _canonicalMap(context.namedSkillMap),
                            "verifiers": context.verifierStanding, "engine": SHADOW_ENGINE_VERSION,
                            "perRowGradeThresholds": context.perRowGradeThresholds,
                            "gradeCeiling": context.gradeCeiling, "gradeThresholds": context.gradeThresholds},
            })
            old = tm.computeTrustMagnitude(skill, context.genericSkillMap, evaluationAtUTC=context.evaluationAtUTC,
                                           benchmarkCatalog=context.benchmarkCatalog)
            assessment["correctionDelta"] = {"legacyTM": old, "shadowTM": assessment["tmRaw"], "implementationCorrection": assessment["tmRaw"] - old}
            assessments[sid] = assessment

    ordered = [assessments[key] for key in sorted(assessments)] + inputFailures
    evaluated = sum(item.get("status") == "evaluated" for item in ordered)
    notEvaluated = len(ordered) - evaluated
    return {"status": "evaluated" if not notEvaluated else "partial",
            "coverage": {"total": len(skills), "evaluated": evaluated, "notEvaluated": notEvaluated},
            "assessments": ordered}
