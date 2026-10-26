"""Yggdrasil IV Trust Magnitude complete registry census and shadow replay.

This module provides a read-only census and shadow evaluation runner over the
entire Gaia Skill Tree corpus, consuming ``evaluateShadow`` and
``evaluateShadowRegistry`` from ``gaia_cli.shadowEvaluation``.

It guarantees:
- Complete census of all named markdown skills (both 'named' and 'awakened' status)
  and generic JSON nodes with parser reconciliation (yaml.safe_load vs load_yaml_simple).
- Strict output path safeguards: rejects writes into canonical/public directories.
- File digest manifest verification before and after evaluation to detect concurrent mutation.
- Seam coordination: preserves valid coverage when individual records have issues.
- Transparent reporting of cause classifications, contextual row grades,
  trustNumber fallback risks, and star ceiling proposals.
- Zero canonical writes and no numerical publication.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from gaia_cli import shadowEvaluation as shadow
from gaia_cli import trustMagnitude as tm
from gaia_cli.benchmarkCatalog import loadBenchmarkCatalog
from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
from gaia_cli.grading import (
    load_evidence_types_full,
    load_grade_thresholds,
    load_per_row_grade_thresholds,
)

SHADOW_CORPUS_VERSION = "gaia-shadow-corpus-v1"
FORBIDDEN_CANONICAL_DIRS = frozenset({
    "registry",
    "docs",
    "skill-trees",
    "src",
    ".agents/skills",
    ".claude/skills",
    ".github",
})
ALLOWED_LOCAL_OUTPUT_DIRS = frozenset({
    ".gaia",
    "generated-output",
    ".tmp",
})


def canonicalBytes(value: Any) -> bytes:
    """Deterministic UTF-8 JSON serialization for digest computation."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def sha256Digest(value: Any) -> str:
    """Return SHA-256 hex digest for any JSON-serializable structure or bytes."""
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = canonicalBytes(value)
    return hashlib.sha256(payload).hexdigest()


def computeFileHash(filePath: Path) -> str:
    """Return SHA-256 hex digest of file contents."""
    return hashlib.sha256(filePath.read_bytes()).hexdigest()


def buildFileDigestManifest(repoRoot: Path) -> dict[str, str]:
    """Scan and return relative path -> SHA-256 manifest of all canonical registry inputs."""
    manifest: dict[str, str] = {}
    nodesDir = repoRoot / "registry" / "nodes"
    if nodesDir.is_dir():
        for p in sorted(nodesDir.rglob("*.json")):
            rel = str(p.relative_to(repoRoot))
            manifest[rel] = computeFileHash(p)
    namedDir = repoRoot / "registry" / "named"
    if namedDir.is_dir():
        for p in sorted(namedDir.rglob("*.md")):
            rel = str(p.relative_to(repoRoot))
            manifest[rel] = computeFileHash(p)
    benchmarkCatalogFile = repoRoot / "registry" / "benchmark-sources.json"
    if benchmarkCatalogFile.is_file():
        rel = str(benchmarkCatalogFile.relative_to(repoRoot))
        manifest[rel] = computeFileHash(benchmarkCatalogFile)
    metaJson = repoRoot / "registry" / "schema" / "meta.json"
    if metaJson.is_file():
        rel = str(metaJson.relative_to(repoRoot))
        manifest[rel] = computeFileHash(metaJson)
    return manifest


def verifyFileDigestManifest(beforeManifest: dict[str, str], repoRoot: Path) -> tuple[bool, list[str]]:
    """Compare before and current manifest to verify no concurrent mutations occurred."""
    current = buildFileDigestManifest(repoRoot)
    discrepancies: list[str] = []
    beforeKeys = set(beforeManifest.keys())
    currentKeys = set(current.keys())

    for key in sorted(beforeKeys - currentKeys):
        discrepancies.append(f"file-deleted: {key}")
    for key in sorted(currentKeys - beforeKeys):
        discrepancies.append(f"file-added: {key}")
    for key in sorted(beforeKeys & currentKeys):
        if beforeManifest[key] != current[key]:
            discrepancies.append(f"file-modified: {key} (was {beforeManifest[key][:8]}, now {current[key][:8]})")

    return len(discrepancies) == 0, discrepancies


def validateOutputPath(outputPath: str | Path, repoRoot: str | Path = ".") -> Path:
    """Validate that output path is external or strictly in an allowed ignored directory.

    Rejects output inside canonical or public project paths:
    registry, docs, skill-trees, src, skills, .github.
    """
    resolvedRepo = Path(repoRoot).resolve()
    resolvedOutput = Path(outputPath).resolve()

    try:
        rel = resolvedOutput.relative_to(resolvedRepo)
        relStr = str(rel).replace("\\", "/")
        firstSegment = relStr.split("/")[0] if "/" in relStr else relStr

        for forbidden in FORBIDDEN_CANONICAL_DIRS:
            if relStr == forbidden or relStr.startswith(forbidden + "/"):
                raise ValueError(
                    f"Output path rejected: '{relStr}' is inside canonical/public path '{forbidden}'. "
                    f"Shadow evaluation output must be written to an ignored scratch directory "
                    f"({', '.join(sorted(ALLOWED_LOCAL_OUTPUT_DIRS))}) or an external path."
                )

        if firstSegment not in ALLOWED_LOCAL_OUTPUT_DIRS:
            raise ValueError(
                f"Output path rejected: '{relStr}' is not in an allowed scratch directory. "
                f"Allowed in-repo roots: {', '.join(sorted(ALLOWED_LOCAL_OUTPUT_DIRS))}."
            )
    except ValueError as exc:
        if "is not in the subpath of" in str(exc) or "does not start with" in str(exc):
            # Output path is outside repoRoot — external paths are safe and allowed
            pass
        else:
            raise

    return resolvedOutput


@dataclass
class RegistryCensus:
    """Complete inventory and parser reconciliation of the registry corpus."""
    totalNamedFiles: int = 0
    totalGenericFiles: int = 0
    statusCounts: dict[str, int] = field(default_factory=dict)
    namedSkills: dict[str, dict[str, Any]] = field(default_factory=dict)
    namedSkillRecords: list[dict[str, Any]] = field(default_factory=list)
    genericNodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    namedEvidenceRowCount: int = 0
    genericEvidenceRowCount: int = 0
    cacheHashCount: int = 0
    parseFailures: list[dict[str, Any]] = field(default_factory=list)
    parserDiscrepancies: list[dict[str, Any]] = field(default_factory=list)
    missingIds: list[str] = field(default_factory=list)
    unresolvedRefs: list[dict[str, Any]] = field(default_factory=list)
    dependencyCycles: list[dict[str, Any]] = field(default_factory=list)
    temporalAnomalies: list[dict[str, Any]] = field(default_factory=list)
    unknownVerifiers: list[dict[str, Any]] = field(default_factory=list)
    trustNumberRows: list[dict[str, Any]] = field(default_factory=list)
    fileHashes: dict[str, str] = field(default_factory=dict)
    isValid: bool = True


def censusRegistry(
    registryPath: str | Path = ".",
    failClosed: bool = False,
    evaluationAtUTC: Optional[datetime.datetime] = None,
) -> RegistryCensus:
    """Perform a complete, read-only census and reconciliation of every registry record."""
    root = Path(registryPath).resolve()
    census = RegistryCensus()
    pinnedTime = evaluationAtUTC or datetime.datetime(2026, 10, 25, 0, 0, 0, tzinfo=datetime.timezone.utc)

    # 1. Census Generic JSON nodes
    nodesDir = root / "registry" / "nodes"
    if nodesDir.is_dir():
        for jsonFile in sorted(nodesDir.rglob("*.json")):
            relPath = str(jsonFile.relative_to(root))
            try:
                rawText = jsonFile.read_text(encoding="utf-8")
                census.fileHashes[relPath] = hashlib.sha256(rawText.encode("utf-8")).hexdigest()
                nodeData = json.loads(rawText)
                census.totalGenericFiles += 1
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                census.parseFailures.append({
                    "path": relPath,
                    "kind": "generic-json",
                    "error": str(exc),
                })
                continue

            if not isinstance(nodeData, dict):
                census.parseFailures.append({
                    "path": relPath,
                    "kind": "generic-json",
                    "error": "JSON content is not an object",
                })
                continue

            nodeId = nodeData.get("id")
            if not nodeId:
                census.missingIds.append(relPath)
            else:
                census.genericNodes[nodeId] = nodeData

            evidenceRows = nodeData.get("evidence") or []
            census.genericEvidenceRowCount += len(evidenceRows)

    # 2. Census Named Markdown skills + Parser Reconciliation
    namedDir = root / "registry" / "named"
    if namedDir.is_dir():
        for mdFile in sorted(namedDir.rglob("*.md")):
            relPath = str(mdFile.relative_to(root))
            try:
                rawText = mdFile.read_text(encoding="utf-8")
                census.fileHashes[relPath] = hashlib.sha256(rawText.encode("utf-8")).hexdigest()
                census.totalNamedFiles += 1
            except (OSError, UnicodeDecodeError) as exc:
                census.parseFailures.append({
                    "path": relPath,
                    "kind": "named-md",
                    "error": str(exc),
                })
                continue

            # Parser 1: split_frontmatter + load_yaml_simple
            fence, fmText, _ = split_frontmatter(rawText)
            simpleFmData: Optional[dict[str, Any]] = None
            simpleErr: Optional[str] = None
            try:
                if fence:
                    simpleFmData = load_yaml_simple(fmText)
                else:
                    simpleErr = "no frontmatter fence matched"
            except Exception as exc:
                simpleErr = str(exc)

            # Parser 2: split("---", 2) + yaml.safe_load
            safeFmData: Optional[dict[str, Any]] = None
            safeErr: Optional[str] = None
            parts = rawText.split("---", 2)
            try:
                if len(parts) >= 3:
                    safeFmData = yaml.safe_load(parts[1]) or {}
                else:
                    safeErr = "file has fewer than two '---' separators"
            except Exception as exc:
                safeErr = str(exc)

            # Reconcile parser behavior
            if simpleErr != safeErr or simpleFmData != safeFmData:
                census.parserDiscrepancies.append({
                    "path": relPath,
                    "simpleError": simpleErr,
                    "safeError": safeErr,
                    "dataMatches": simpleFmData == safeFmData,
                })

            parsedFm = simpleFmData if isinstance(simpleFmData, dict) else (safeFmData if isinstance(safeFmData, dict) else None)
            if parsedFm is None:
                census.parseFailures.append({
                    "path": relPath,
                    "kind": "named-md",
                    "error": simpleErr or safeErr or "failed to parse frontmatter as dictionary",
                })
                continue

            status = parsedFm.get("status")
            statusKey = str(status) if status is not None else "<missing>"
            census.statusCounts[statusKey] = census.statusCounts.get(statusKey, 0) + 1

            skillId = parsedFm.get("id")
            if not skillId:
                census.missingIds.append(relPath)
            else:
                census.namedSkills[skillId] = parsedFm

            census.namedSkillRecords.append({
                "path": relPath,
                "id": skillId,
                "status": status,
                "skill": parsedFm,
            })

            if parsedFm.get("trustMagnitudeInputHash"):
                census.cacheHashCount += 1

            evidenceRows = parsedFm.get("evidence") or []
            census.namedEvidenceRowCount += len(evidenceRows)

            # Audit generic ref resolution
            genericRef = parsedFm.get("genericSkillRef")
            if genericRef and genericRef not in census.genericNodes:
                census.unresolvedRefs.append({
                    "skillId": skillId,
                    "path": relPath,
                    "genericSkillRef": genericRef,
                })

            # Audit evidence row dates and trustNumber fallbacks
            for rIndex, row in enumerate(evidenceRows):
                if row.get("trustNumber") is not None:
                    census.trustNumberRows.append({
                        "skillId": skillId,
                        "path": relPath,
                        "rowIndex": rIndex,
                        "trustNumber": row["trustNumber"],
                    })
                for dField in ("lastVerified", "sourceStartedAt"):
                    rawDate = row.get(dField)
                    if rawDate in (None, ""):
                        continue
                    parsedDate = tm._parseIso(rawDate)
                    if parsedDate is None:
                        census.temporalAnomalies.append({
                            "skillId": skillId,
                            "path": relPath,
                            "rowIndex": rIndex,
                            "field": dField,
                            "rawValue": rawDate,
                            "anomaly": "malformed-iso-date",
                        })
                    elif parsedDate > pinnedTime:
                        census.temporalAnomalies.append({
                            "skillId": skillId,
                            "path": relPath,
                            "rowIndex": rIndex,
                            "field": dField,
                            "rawValue": rawDate,
                            "anomaly": "future-date",
                        })

    # 3. Detect dependency cycles in suite components
    namedMap = census.namedSkills
    for sid, skill in namedMap.items():
        components = skill.get("suiteComponents") or []
        if not components:
            continue
        visited: set[str] = set()
        stack: list[str] = [sid]
        while stack:
            curr = stack.pop()
            if curr in visited:
                census.dependencyCycles.append({
                    "skillId": sid,
                    "cycleParticipant": curr,
                })
                break
            visited.add(curr)
            currSkill = namedMap.get(curr)
            if currSkill:
                for subComp in currSkill.get("suiteComponents") or []:
                    if subComp in visited:
                        census.dependencyCycles.append({
                            "skillId": sid,
                            "cycleParticipant": subComp,
                        })
                    else:
                        stack.append(subComp)

    if failClosed and census.parseFailures:
        census.isValid = False

    return census


def resolveRegistryRevision(registryPath: Path) -> str:
    """Resolve current git commit SHA or return 'unknown'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(registryPath),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def computeEngineDigest() -> str:
    """Compute combined SHA-256 digest of engine implementation files."""
    here = Path(__file__).resolve().parent
    engineFiles = [
        here / "trustMagnitude.py",
        here / "shadowEvaluation.py",
        here / "shadowCorpus.py",
    ]
    hasher = hashlib.sha256()
    for f in engineFiles:
        if f.is_file():
            hasher.update(f.read_bytes())
    return hasher.hexdigest()


def buildShadowContext(
    census: RegistryCensus,
    registryPath: str | Path = ".",
    evaluationAtUTC: Optional[datetime.datetime | str] = None,
    policyVersion: str = "g7-v1",
    registryRevision: Optional[str] = None,
    verifierStanding: Optional[dict[str, bool]] = None,
) -> tuple[shadow.ShadowEvaluationContext, dict[str, str]]:
    """Build the explicit immutable evaluation context covering all canonical inputs."""
    repoRoot = Path(registryPath).resolve()

    # Pinned UTC evaluation datetime
    if evaluationAtUTC is None:
        evalTime = datetime.datetime(2026, 10, 25, 0, 0, 0, tzinfo=datetime.timezone.utc)
    elif isinstance(evaluationAtUTC, str):
        isoClean = evaluationAtUTC.replace("Z", "+00:00")
        evalTime = datetime.datetime.fromisoformat(isoClean)
        if evalTime.tzinfo is None:
            evalTime = evalTime.replace(tzinfo=datetime.timezone.utc)
        elif evalTime.utcoffset() != datetime.timedelta(0):
            evalTime = evalTime.astimezone(datetime.timezone.utc)
    elif isinstance(evaluationAtUTC, datetime.datetime):
        evalTime = evaluationAtUTC
        if evalTime.tzinfo is None:
            evalTime = evalTime.replace(tzinfo=datetime.timezone.utc)
        elif evalTime.utcoffset() != datetime.timedelta(0):
            evalTime = evalTime.astimezone(datetime.timezone.utc)
    else:
        raise ValueError(f"Invalid evaluationAtUTC: {evaluationAtUTC}")

    # Benchmark catalog
    catalog = loadBenchmarkCatalog(repoRoot)
    catalogDigest = sha256Digest(catalog)

    # Policy digest from meta.json
    metaJsonPath = repoRoot / "registry" / "schema" / "meta.json"
    if metaJsonPath.is_file():
        policyDigest = computeFileHash(metaJsonPath)
    else:
        policyDigest = sha256Digest(policyVersion)

    # Revision
    rev = registryRevision or resolveRegistryRevision(repoRoot)

    # Canonical input digest: SHA-256 of sorted (path:hash) lines
    manifestLines = [f"{path}:{hashVal}" for path, hashVal in sorted(census.fileHashes.items())]
    canonicalInputDigest = sha256Digest("\n".join(manifestLines))

    # Thresholds
    perRowThresholds = load_per_row_grade_thresholds(repoRoot)
    evTypes = load_evidence_types_full(repoRoot)
    gradeCeilings = {t["id"]: t["gradeCeiling"] for t in evTypes if t.get("gradeCeiling")}
    gradeThresholds = load_grade_thresholds(repoRoot)

    # Verifier standing resolution
    if verifierStanding is not None:
        standing = dict(verifierStanding)
    else:
        standing = {}
        # Known verifiers: mbtiongson1 + any contributor with 4★+ named skill
        standing["mbtiongson1"] = True
        for sid, skill in census.namedSkills.items():
            level = skill.get("level", "")
            contributor = skill.get("contributor") or (sid.split("/")[0] if "/" in sid else None)
            if contributor and level and level[0].isdigit() and int(level[0]) >= 4:
                standing[contributor] = True

        # Check all verifier-attestation evidence rows in named and generic
        allSkills = list(census.namedSkills.values()) + list(census.genericNodes.values())
        for s in allSkills:
            for row in s.get("evidence") or []:
                if tm._typeOf(row) == "verifier-attestation":
                    verifier = row.get("verifierId") or row.get("verifier") or row.get("attestor")
                    if verifier and verifier not in standing:
                        standing[verifier] = False

    context = shadow.ShadowEvaluationContext(
        evaluationAtUTC=evalTime,
        policyVersion=policyVersion,
        policyDigest=policyDigest,
        benchmarkCatalog=catalog,
        benchmarkCatalogDigest=catalogDigest,
        registryRevision=rev,
        canonicalInputDigest=canonicalInputDigest,
        genericSkillMap=census.genericNodes,
        namedSkillMap=census.namedSkills,
        verifierStanding=standing,
        perRowGradeThresholds=perRowThresholds,
        gradeCeiling=gradeCeilings,
        gradeThresholds=gradeThresholds,
    )

    metadata = {
        "engineVersion": shadow.SHADOW_ENGINE_VERSION,
        "engineDigest": computeEngineDigest(),
        "shadowCorpusVersion": SHADOW_CORPUS_VERSION,
    }

    return context, metadata


def evaluateRegistryWithSeam(
    skills: list[dict[str, Any]],
    context: shadow.ShadowEvaluationContext,
) -> dict[str, Any]:
    """Evaluate registry skills consuming evaluateShadow/evaluateShadowRegistry with seam coordination.

    Coordinates gracefully if evaluateShadowRegistry aborts on a single invalid input:
    preserves valid coverage and reports honest per-record unknowns and dependencies.
    """
    # 1. First attempt evaluateShadowRegistry
    try:
        registryResult = shadow.evaluateShadowRegistry(skills, context)
        status = registryResult.get("status")
        assessments = registryResult.get("assessments") or []
        if status in ("evaluated", "partial") and len(assessments) == len(skills):
            return registryResult
    except Exception:
        # Fall through to coordinated per-record evaluation
        pass

    # 2. Seam coordinator: topological component-before-suite evaluation
    byId = {s.get("id"): s for s in skills if s.get("id")}
    pending = dict(byId)
    computedNamed = {k: dict(v) for k, v in context.namedSkillMap.items()}
    assessmentsById: dict[str, dict[str, Any]] = {}

    while pending:
        ready = sorted(
            key for key, item in pending.items()
            if all(component not in pending for component in (item.get("suiteComponents") or []))
        )
        if not ready:
            # Component dependency cycle detected among remaining pending skills
            cycleReason = f"component dependency cycle among remaining: {sorted(pending.keys())}"
            for sid in sorted(pending.keys()):
                skill = pending.pop(sid)
                assessmentsById[sid] = {
                    "status": "not-evaluated",
                    "reason": cycleReason,
                    "skillId": sid,
                    "scope": "suite" if skill.get("suiteComponents") is not None else "unique",
                    "canonicalStars": skill.get("level"),
                }
            break

        for sid in ready:
            skill = pending.pop(sid)
            # Evaluate using context with dynamically accumulated computedNamed
            iterContext = dataclasses.replace(context, namedSkillMap=computedNamed)
            assessment = shadow.evaluateShadow(skill, iterContext)
            assessmentsById[sid] = assessment

            if assessment.get("status") == "evaluated":
                grade = assessment.get("grade")
                computedNamed[sid] = {
                    **skill,
                    "overallTrustGrade": grade,
                    "overallGrade": grade,
                    "grade": grade,
                    "_shadowAssessed": True,
                }

    orderedAssessments = [assessmentsById[k] for k in sorted(assessmentsById.keys())]
    allEvaluated = all(a.get("status") == "evaluated" for a in orderedAssessments)
    overallStatus = "evaluated" if allEvaluated else ("partial" if any(a.get("status") == "evaluated" for a in orderedAssessments) else "not-evaluated")

    return {
        "status": overallStatus,
        "assessments": orderedAssessments,
    }


def runShadowEvaluation(
    registryPath: str | Path = ".",
    evaluationAtUTC: Optional[datetime.datetime | str] = None,
    failClosed: bool = False,
    verifierStanding: Optional[dict[str, bool]] = None,
    filterStatus: Optional[str] = None,
) -> dict[str, Any]:
    """Execute complete read-only shadow evaluation pass over the entire corpus."""
    repoRoot = Path(registryPath).resolve()

    # Step 1: Record pre-evaluation file digest manifest
    beforeManifest = buildFileDigestManifest(repoRoot)

    # Step 2: Census registry corpus with parser reconciliation
    census = censusRegistry(repoRoot, failClosed=failClosed, evaluationAtUTC=None)

    # Step 3: Build explicit immutable evaluation context
    context, engineMeta = buildShadowContext(
        census=census,
        registryPath=repoRoot,
        evaluationAtUTC=evaluationAtUTC,
        verifierStanding=verifierStanding,
    )

    # Filter skills if requested (e.g. status == "named")
    targetSkills: list[dict[str, Any]] = []
    for rec in census.namedSkillRecords:
        skill = rec["skill"]
        if filterStatus is None or rec.get("status") == filterStatus:
            targetSkills.append(skill)

    # Step 4: Run shadow evaluation with seam coordination
    evaluationResult = evaluateRegistryWithSeam(targetSkills, context)

    # Step 5: Verify post-evaluation manifest (concurrent mutation detection)
    manifestMatches, manifestDiscrepancies = verifyFileDigestManifest(beforeManifest, repoRoot)

    # Step 6: Assemble per-record reports and impact aggregation
    enrichedAssessments: list[dict[str, Any]] = []
    tmCorrectionsCount = 0
    gradeChangesCount = 0
    starCeilingDemotionsCount = 0
    starCeilingPromotionsCount = 0
    starCeilingNeutralCount = 0
    causeCounts: dict[str, int] = {
        "source-only-inheritance-merge": 0,
        "eligibility-before-dedup": 0,
        "component-before-suite-grade": 0,
        "named-row-grade-context": 0,
    }
    gateGradeRiskCount = 0
    temporalWarningsCount = 0
    evaluatedCount = 0
    notEvaluatedCount = 0

    for assessment in evaluationResult.get("assessments", []):
        sid = assessment.get("skillId")
        skillFm = census.namedSkills.get(sid, {})
        status = assessment.get("status")

        if status == "evaluated":
            evaluatedCount += 1
            storedStars = skillFm.get("level")
            storedTM = skillFm.get("trustMagnitude")
            storedGrade = skillFm.get("overallTrustGrade")
            storedHash = skillFm.get("trustMagnitudeInputHash")

            shadowTM = assessment.get("tmRaw")
            shadowGrade = assessment.get("grade")
            gradeCeiling = assessment.get("gradeCeilingProposal")

            correctionDelta = assessment.get("correctionDelta") or {}
            legacyTM = correctionDelta.get("legacyTM")
            implCorrection = correctionDelta.get("implementationCorrection", 0.0)

            if abs(implCorrection) > 0.0001:
                tmCorrectionsCount += 1

            gradeChanged = (storedGrade != shadowGrade) if (storedGrade and shadowGrade) else False
            if gradeChanged:
                gradeChangesCount += 1

            # Star ceiling comparison
            ceilingDelta: Optional[str] = None
            if storedStars and isinstance(storedStars, str) and storedStars[0].isdigit() and gradeCeiling is not None:
                numericStars = int(storedStars[0])
                if gradeCeiling < numericStars:
                    starCeilingDemotionsCount += 1
                    ceilingDelta = "demotion-risk"
                elif gradeCeiling > numericStars:
                    starCeilingPromotionsCount += 1
                    ceilingDelta = "promotion-headroom"
                else:
                    starCeilingNeutralCount += 1
                    ceilingDelta = "neutral"

            # Causes tally
            for causeItem in assessment.get("correctionCauses", []):
                cName = causeItem.get("cause")
                if causeItem.get("status") == "triggered" and cName in causeCounts:
                    causeCounts[cName] += 1

            # Rows risk audit
            hasGateRisk = any(r.get("gateGradeRisk") for r in assessment.get("rows", []))
            if hasGateRisk:
                gateGradeRiskCount += 1

            warnings = assessment.get("temporalWarnings") or []
            if warnings:
                temporalWarningsCount += len(warnings)

            enriched = {
                **assessment,
                "storedStars": storedStars,
                "storedTM": storedTM,
                "storedGrade": storedGrade,
                "storedHash": storedHash,
                "ceilingDelta": ceilingDelta,
                "gradeChanged": gradeChanged,
            }
        else:
            notEvaluatedCount += 1
            enriched = {
                **assessment,
                "storedStars": skillFm.get("level"),
                "storedTM": skillFm.get("trustMagnitude"),
                "storedGrade": skillFm.get("overallTrustGrade"),
            }

        enrichedAssessments.append(enriched)

    summary = {
        "totalSkillsCensused": census.totalNamedFiles,
        "targetSkillsCount": len(targetSkills),
        "evaluatedCount": evaluatedCount,
        "notEvaluatedCount": notEvaluatedCount,
        "overallStatus": evaluationResult.get("status"),
        "tmCorrectionsCount": tmCorrectionsCount,
        "gradeChangesCount": gradeChangesCount,
        "starCeilingImpact": {
            "demotionRiskCount": starCeilingDemotionsCount,
            "promotionHeadroomCount": starCeilingPromotionsCount,
            "neutralCount": starCeilingNeutralCount,
        },
        "causeBreakdown": causeCounts,
        "gateGradeRiskCount": gateGradeRiskCount,
        "temporalWarningsCount": temporalWarningsCount,
        "manifestVerification": {
            "clean": manifestMatches,
            "discrepancies": manifestDiscrepancies,
        },
    }

    reportData = {
        "metadata": {
            **engineMeta,
            "policyVersion": context.policyVersion,
            "policyDigest": context.policyDigest,
            "benchmarkCatalogDigest": context.benchmarkCatalogDigest,
            "registryRevision": context.registryRevision,
            "canonicalInputDigest": context.canonicalInputDigest,
            "evaluationAtUTC": context.evaluationAtUTC.isoformat(),
            "publicationAuthorized": False,
            "shadowNotice": "Read-only shadow evaluation diagnostic. Zero canonical writes performed.",
        },
        "census": {
            "totalNamedFiles": census.totalNamedFiles,
            "totalGenericFiles": census.totalGenericFiles,
            "statusCounts": census.statusCounts,
            "namedEvidenceRowCount": census.namedEvidenceRowCount,
            "genericEvidenceRowCount": census.genericEvidenceRowCount,
            "cacheHashCount": census.cacheHashCount,
            "parseFailures": census.parseFailures,
            "parserDiscrepancies": census.parserDiscrepancies,
            "missingIds": census.missingIds,
            "unresolvedRefs": census.unresolvedRefs,
            "dependencyCycles": census.dependencyCycles,
            "temporalAnomalies": census.temporalAnomalies,
            "trustNumberRowsCount": len(census.trustNumberRows),
        },
        "summary": summary,
        "assessments": enrichedAssessments,
    }

    return reportData


def formatImpactSummary(reportData: dict[str, Any]) -> str:
    """Format a clean, readable human impact summary for terminal output or report text."""
    meta = reportData.get("metadata", {})
    census = reportData.get("census", {})
    summary = reportData.get("summary", {})
    causes = summary.get("causeBreakdown", {})
    starImpact = summary.get("starCeilingImpact", {})
    manifest = summary.get("manifestVerification", {})

    lines = [
        "================================================================================",
        "GAIA YGGDRASIL IV TRUST MAGNITUDE — SHADOW REPLAY & REGISTRY CENSUS",
        "================================================================================",
        "NOTICE: Read-only shadow diagnostic output. Zero canonical writes performed.",
        "Core engine under independent review; results are provisional, not authoritative.",
        "--------------------------------------------------------------------------------",
        f"Pinned UTC Evaluation Time : {meta.get('evaluationAtUTC')}",
        f"Registry Revision          : {meta.get('registryRevision')}",
        f"Engine Version             : {meta.get('engineVersion')}",
        f"Policy Version             : {meta.get('policyVersion')} (digest: {meta.get('policyDigest', '')[:12]}...)",
        f"Benchmark Catalog Digest   : {meta.get('benchmarkCatalogDigest', '')[:12]}...",
        f"Canonical Input Digest     : {meta.get('canonicalInputDigest', '')[:12]}...",
        "--------------------------------------------------------------------------------",
        "REGISTRY CENSUS OVERVIEW:",
        f"  Total Named Records       : {census.get('totalNamedFiles')}",
        f"  Status Subsets            : {dict(census.get('statusCounts', {}))}",
        f"  Total Generic Nodes       : {census.get('totalGenericFiles')}",
        f"  Named Evidence Rows       : {census.get('namedEvidenceRowCount')}",
        f"  Generic Evidence Rows     : {census.get('genericEvidenceRowCount')}",
        f"  Frontmatter Cache Hashes  : {census.get('cacheHashCount')}",
        f"  Parse Failures            : {len(census.get('parseFailures', []))}",
        f"  Parser Discrepancies      : {len(census.get('parserDiscrepancies', []))}",
        f"  Unresolved Generic Refs   : {len(census.get('unresolvedRefs', []))}",
        f"  Dependency Cycles         : {len(census.get('dependencyCycles', []))}",
        f"  Temporal Anomalies        : {len(census.get('temporalAnomalies', []))}",
        "--------------------------------------------------------------------------------",
        "SHADOW REPLAY EVALUATION:",
        f"  Overall Status            : {summary.get('overallStatus')}",
        f"  Evaluated Skills          : {summary.get('evaluatedCount')} / {summary.get('targetSkillsCount')}",
        f"  Not-Evaluated Skills      : {summary.get('notEvaluatedCount')}",
        f"  Implementation TM Deltas  : {summary.get('tmCorrectionsCount')} skills with TM delta != 0",
        f"  Grade Changes             : {summary.get('gradeChangesCount')} skills change Overall Trust Grade",
        "--------------------------------------------------------------------------------",
        "STAR CEILING PROPOSALS VS STORED CANONICAL STARS:",
        f"  Ceiling < Stored Stars    : {starImpact.get('demotionRiskCount')} (provisional demotion risk)",
        f"  Ceiling == Stored Stars   : {starImpact.get('neutralCount')} (neutral)",
        f"  Ceiling > Stored Stars    : {starImpact.get('promotionHeadroomCount')} (provisional promotion headroom)",
        "--------------------------------------------------------------------------------",
        "RFC §10/§11 IMPLEMENTATION CORRECTION CAUSES TRIGGERED:",
        f"  1. source-only-inheritance-merge : {causes.get('source-only-inheritance-merge', 0)} skills",
        f"  2. eligibility-before-dedup      : {causes.get('eligibility-before-dedup', 0)} skills",
        f"  3. component-before-suite-grade  : {causes.get('component-before-suite-grade', 0)} skills",
        f"  4. named-row-grade-context       : {causes.get('named-row-grade-context', 0)} skills",
        "--------------------------------------------------------------------------------",
        "RISK & INTEGRITY AUDIT:",
        f"  Gate Grade Risks (trustNum fallbacks) : {summary.get('gateGradeRiskCount')} skills",
        f"  Temporal Date Warnings                : {summary.get('temporalWarningsCount')}",
        f"  Input Manifest Verification           : {'CLEAN (no concurrent mutation)' if manifest.get('clean') else 'MUTATION DETECTED'}",
        "================================================================================",
    ]
    return "\n".join(lines)


def writeShadowReport(
    reportData: dict[str, Any],
    outputDir: str | Path,
    repoRoot: str | Path = ".",
) -> dict[str, Path]:
    """Write machine-readable JSON and human-readable summary to validated output directory."""
    outPath = validateOutputPath(outputDir, repoRoot=repoRoot)
    outPath.mkdir(parents=True, exist_ok=True)

    jsonPath = outPath / "shadow-report.json"
    summaryPath = outPath / "shadow-summary.txt"

    # Write deterministic machine JSON (sorted keys, 2-space indentation)
    jsonText = json.dumps(reportData, indent=2, sort_keys=True, ensure_ascii=False)
    jsonPath.write_text(jsonText, encoding="utf-8")

    # Write human summary
    summaryText = formatImpactSummary(reportData)
    summaryPath.write_text(summaryText, encoding="utf-8")

    return {
        "json": jsonPath,
        "summary": summaryPath,
    }


def run_shadow_corpus_cli(args: argparse.Namespace) -> int:
    """CLI execution entrypoint for gaia shadow command."""
    registryPath = getattr(args, "registry", ".") or "."
    evaluationAt = getattr(args, "evaluation_at", "2026-10-25T00:00:00Z")
    outputDir = getattr(args, "output_dir", None)
    toStdout = getattr(args, "stdout", False)
    asJson = getattr(args, "json", False)
    failClosed = getattr(args, "fail_closed", False)

    try:
        reportData = runShadowEvaluation(
            registryPath=registryPath,
            evaluationAtUTC=evaluationAt,
            failClosed=failClosed,
        )
    except Exception as exc:
        print(f"Error running shadow evaluation: {exc}", file=sys.stderr)
        return 1

    summary = reportData.get("summary", {})
    census = reportData.get("census", {})

    # Handle output files if requested or default to .gaia/shadow when neither stdout nor output_dir is specified
    if outputDir:
        try:
            paths = writeShadowReport(reportData, outputDir, repoRoot=registryPath)
            print(f"Shadow report written to: {paths['json']}")
            print(f"Shadow summary written to: {paths['summary']}")
        except ValueError as exc:
            print(f"Security error: {exc}", file=sys.stderr)
            return 1
    elif not toStdout and not asJson:
        # Default output location in ignored .gaia/shadow
        defaultOut = Path(registryPath) / ".gaia" / "shadow"
        try:
            paths = writeShadowReport(reportData, defaultOut, repoRoot=registryPath)
            print(f"Shadow report written to: {paths['json']}")
            print(f"Shadow summary written to: {paths['summary']}")
        except ValueError as exc:
            print(f"Security error: {exc}", file=sys.stderr)
            return 1

    if asJson:
        print(json.dumps(reportData, indent=2, sort_keys=True, ensure_ascii=False))
    elif toStdout or not outputDir:
        print(formatImpactSummary(reportData))

    if failClosed and (census.get("parseFailures") or summary.get("notEvaluatedCount", 0) > 0):
        return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gaia Registry Census and Shadow Evaluation")
    parser.add_argument("--registry", default=".", help="Path to registry root")
    parser.add_argument("--at", "--evaluation-at", dest="evaluation_at", default="2026-10-25T00:00:00Z", help="Pinned evaluation datetime UTC")
    parser.add_argument("--output-dir", default=None, help="Output directory for machine JSON and summary")
    parser.add_argument("--stdout", action="store_true", help="Print summary to stdout")
    parser.add_argument("--json", action="store_true", help="Print machine JSON to stdout")
    parser.add_argument("--fail-closed", action="store_true", help="Exit non-zero on parse failures or unknowns")
    cliArgs = parser.parse_args()
    sys.exit(run_shadow_corpus_cli(cliArgs))
