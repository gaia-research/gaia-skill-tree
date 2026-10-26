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
import math
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
    registry, docs, skill-trees, src, .agents/skills, .claude/skills, .github.
    Strictly forbids path traversal, ancestor symlinks, or repo overrides targeting canonical paths.
    """
    resolvedRepo = Path(repoRoot).resolve()
    rawOutput = Path(outputPath)
    resolvedOutput = rawOutput.resolve()

    rootsToCheck = [resolvedRepo]
    cwdResolved = Path.cwd().resolve()
    if cwdResolved not in rootsToCheck:
        rootsToCheck.append(cwdResolved)

    for root in rootsToCheck:
        try:
            rel = resolvedOutput.relative_to(root)
            relStr = str(rel).replace("\\", "/")
            firstSegment = relStr.split("/")[0] if "/" in relStr else relStr

            for forbidden in FORBIDDEN_CANONICAL_DIRS:
                if relStr == forbidden or relStr.startswith(forbidden + "/") or forbidden in rel.parts:
                    raise ValueError(
                        f"Output path rejected: '{relStr}' is inside canonical/public path '{forbidden}'. "
                        f"Shadow evaluation output must be written to an ignored scratch directory "
                        f"({', '.join(sorted(ALLOWED_LOCAL_OUTPUT_DIRS))}) or an external path."
                    )

            if root == resolvedRepo and firstSegment not in ALLOWED_LOCAL_OUTPUT_DIRS:
                raise ValueError(
                    f"Output path rejected: '{relStr}' is not in an allowed scratch directory. "
                    f"Allowed in-repo roots: {', '.join(sorted(ALLOWED_LOCAL_OUTPUT_DIRS))}."
                )
        except ValueError as exc:
            if "is not in the subpath of" in str(exc) or "does not start with" in str(exc):
                pass
            else:
                raise

    # Ancestor symlink traversal verification
    curr = rawOutput
    while curr != curr.parent:
        if curr.is_symlink():
            resolvedCurr = curr.resolve()
            for root in rootsToCheck:
                for forbidden in FORBIDDEN_CANONICAL_DIRS:
                    forbidPath = root / forbidden
                    if resolvedCurr == forbidPath or forbidPath in resolvedCurr.parents:
                        raise ValueError(
                            f"Output path rejected: ancestor symlink '{curr}' resolves to canonical path '{resolvedCurr}'."
                        )
        curr = curr.parent

    return resolvedOutput


def _validateEvidenceRowNumeric(row: dict[str, Any]) -> str | None:
    """Validate that numerical evidence fields are finite numbers and not bool/NaN/Inf."""
    NUMERIC_FIELDS = {
        "commits", "contributors", "stars", "views", "percentile",
        "citations", "reviewers", "skillCountInRepo", "externalStars",
        "verifiers", "score", "trustNumber", "downloads", "likes", "comments"
    }
    for key, value in row.items():
        if key not in NUMERIC_FIELDS or value is None:
            continue
        if isinstance(value, bool):
            return f"boolean value not permitted for numeric field '{key}'"
        try:
            num = float(value)
        except (TypeError, ValueError, OverflowError):
            return f"invalid numeric value for field '{key}': {value!r}"
        if not math.isfinite(num):
            return f"non-finite numeric value for field '{key}': {value!r}"
    return None


def _validateSkillStructural(skill: Any, isNamed: bool = True) -> list[str]:
    """Validate skill structural shape before invoking the evaluator."""
    errors: list[str] = []
    if not isinstance(skill, dict):
        return ["skill content must be a dictionary object"]

    sid = skill.get("id")
    if not sid or not isinstance(sid, str) or not sid.strip():
        errors.append("skill requires a non-empty string 'id'")

    ref = skill.get("genericSkillRef")
    if ref is not None:
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"genericSkillRef must be a non-empty string, got {type(ref).__name__}")

    comps = skill.get("suiteComponents")
    if comps is not None:
        if not isinstance(comps, list):
            errors.append(f"suiteComponents must be a list of strings, got {type(comps).__name__}")
        else:
            for idx, c in enumerate(comps):
                if not isinstance(c, str) or not c.strip():
                    errors.append(f"suiteComponents contains non-string or empty component ID at index {idx}: {c!r}")

    rows = skill.get("evidence")
    if rows is not None:
        if not isinstance(rows, list):
            errors.append(f"evidence must be a list of objects, got {type(rows).__name__}")
        else:
            for rIdx, r in enumerate(rows):
                if not isinstance(r, dict):
                    errors.append(f"evidence row[{rIdx}] must be an object, got {type(r).__name__}")
                else:
                    numErr = _validateEvidenceRowNumeric(r)
                    if numErr:
                        errors.append(f"evidence row[{rIdx}]: {numErr}")

    return errors


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
    missingDates: list[dict[str, Any]] = field(default_factory=list)
    unknownVerifiers: list[dict[str, Any]] = field(default_factory=list)
    trustNumberRows: list[dict[str, Any]] = field(default_factory=list)
    duplicateIds: list[dict[str, Any]] = field(default_factory=list)
    structuralFailures: list[dict[str, Any]] = field(default_factory=list)
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
    if isinstance(pinnedTime, str):
        pinnedTime = datetime.datetime.fromisoformat(pinnedTime.replace("Z", "+00:00"))
    if pinnedTime.tzinfo is None:
        pinnedTime = pinnedTime.replace(tzinfo=datetime.timezone.utc)
    else:
        pinnedTime = pinnedTime.astimezone(datetime.timezone.utc)

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

            structErrors = _validateSkillStructural(nodeData, isNamed=False)
            if structErrors:
                for err in structErrors:
                    census.structuralFailures.append({
                        "path": relPath,
                        "skillId": nodeData.get("id") if isinstance(nodeData, dict) else None,
                        "kind": "generic-json",
                        "error": err,
                    })

            nodeId = nodeData.get("id")
            if not nodeId or not isinstance(nodeId, str) or not nodeId.strip():
                census.missingIds.append(relPath)
            elif nodeId in census.genericNodes:
                census.duplicateIds.append({"id": nodeId, "kind": "generic", "path": relPath,
                                            "firstPath": f"registry/nodes/{nodeId}.json"})
            else:
                census.genericNodes[nodeId] = nodeData

            evidenceRows = nodeData.get("evidence") if isinstance(nodeData.get("evidence"), list) else []
            census.genericEvidenceRowCount += len(evidenceRows)
            for rIndex, row in enumerate(evidenceRows):
                if not isinstance(row, dict):
                    continue
                if row.get("trustNumber") is not None:
                    census.trustNumberRows.append({
                        "skillId": nodeId,
                        "path": relPath,
                        "rowIndex": rIndex,
                        "trustNumber": row["trustNumber"],
                    })
                rType = tm._typeOf(row)
                if rType in ("benchmark-result", "social-signal", "peer-review"):
                    if not row.get("lastVerified"):
                        census.missingDates.append({
                            "skillId": nodeId,
                            "path": relPath,
                            "rowIndex": rIndex,
                            "type": rType,
                        })
                for dField in ("lastVerified", "sourceStartedAt"):
                    rawDate = row.get(dField)
                    if rawDate in (None, ""):
                        continue
                    parsedDate = tm._parseIso(rawDate)
                    if parsedDate is None:
                        census.temporalAnomalies.append({
                            "skillId": nodeId,
                            "path": relPath,
                            "rowIndex": rIndex,
                            "field": dField,
                            "rawValue": rawDate,
                            "anomaly": "malformed-iso-date",
                        })
                    elif (parsedDate.replace(tzinfo=datetime.timezone.utc) if parsedDate.tzinfo is None else parsedDate.astimezone(datetime.timezone.utc)) > pinnedTime:
                        census.temporalAnomalies.append({
                            "skillId": nodeId,
                            "path": relPath,
                            "rowIndex": rIndex,
                            "field": dField,
                            "rawValue": rawDate,
                            "anomaly": "future-date",
                        })

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

            structErrors = _validateSkillStructural(parsedFm, isNamed=True)
            if structErrors:
                for err in structErrors:
                    census.structuralFailures.append({
                        "path": relPath,
                        "skillId": parsedFm.get("id") if isinstance(parsedFm, dict) else None,
                        "kind": "named-md",
                        "error": err,
                    })

            status = parsedFm.get("status")
            statusKey = str(status) if status is not None else "<missing>"
            census.statusCounts[statusKey] = census.statusCounts.get(statusKey, 0) + 1

            skillId = parsedFm.get("id")
            if not skillId or not isinstance(skillId, str) or not skillId.strip():
                census.missingIds.append(relPath)
            elif skillId in census.namedSkills:
                firstSeen = next((r["path"] for r in census.namedSkillRecords if r["id"] == skillId), "registry/named/...")
                census.duplicateIds.append({"id": skillId, "kind": "named", "path": relPath,
                                            "firstPath": firstSeen})
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

            evidenceRows = parsedFm.get("evidence") if isinstance(parsedFm.get("evidence"), list) else []
            census.namedEvidenceRowCount += len(evidenceRows)

            # Audit generic ref resolution
            genericRef = parsedFm.get("genericSkillRef")
            if genericRef and isinstance(genericRef, str):
                if genericRef not in census.genericNodes:
                    census.unresolvedRefs.append({
                        "skillId": skillId,
                        "path": relPath,
                        "genericSkillRef": genericRef,
                    })

            # Audit evidence row dates and trustNumber fallbacks
            for rIndex, row in enumerate(evidenceRows):
                if not isinstance(row, dict):
                    continue
                if row.get("trustNumber") is not None:
                    census.trustNumberRows.append({
                        "skillId": skillId,
                        "path": relPath,
                        "rowIndex": rIndex,
                        "trustNumber": row["trustNumber"],
                    })
                rType = tm._typeOf(row)
                if rType in ("benchmark-result", "social-signal", "peer-review"):
                    if not row.get("lastVerified"):
                        census.missingDates.append({
                            "skillId": skillId,
                            "path": relPath,
                            "rowIndex": rIndex,
                            "type": rType,
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
                    elif (parsedDate.replace(tzinfo=datetime.timezone.utc) if parsedDate.tzinfo is None else parsedDate.astimezone(datetime.timezone.utc)) > pinnedTime:
                        census.temporalAnomalies.append({
                            "skillId": skillId,
                            "path": relPath,
                            "rowIndex": rIndex,
                            "field": dField,
                            "rawValue": rawDate,
                            "anomaly": "future-date",
                        })

    # 3. Detect dependency cycles in suite components using 3-color DFS
    state: dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited

    def _detect_cycle(node: str, path: list[str]) -> None:
        state[node] = 1
        skill = census.namedSkills.get(node)
        if skill and isinstance(skill.get("suiteComponents"), list):
            for comp in skill.get("suiteComponents") or []:
                if isinstance(comp, str) and comp in census.namedSkills:
                    if state.get(comp) == 1:
                        census.dependencyCycles.append({
                            "skillId": node,
                            "cycleParticipant": comp,
                            "path": path + [comp],
                        })
                    elif state.get(comp) != 2:
                        _detect_cycle(comp, path + [comp])
        state[node] = 2

    for sid in sorted(census.namedSkills.keys()):
        if state.get(sid) != 2:
            _detect_cycle(sid, [sid])

    # 4. Audit verifier-attestation rows for unknown verifiers
    knownVerifiers = {"mbtiongson1"}
    for sid, skill in census.namedSkills.items():
        lvl = skill.get("level", "")
        contrib = skill.get("contributor") or (sid.split("/")[0] if "/" in sid else None)
        if contrib and lvl and lvl[0].isdigit() and int(lvl[0]) >= 4:
            knownVerifiers.add(contrib)

    for rec in census.namedSkillRecords:
        s = rec["skill"]
        sid = rec["id"]
        for rIndex, row in enumerate(s.get("evidence") or []):
            if isinstance(row, dict) and tm._typeOf(row) == "verifier-attestation":
                v = row.get("verifierId") or row.get("verifier") or row.get("attestor")
                if not v or v not in knownVerifiers:
                    census.unknownVerifiers.append({
                        "skillId": sid,
                        "path": rec["path"],
                        "rowIndex": rIndex,
                        "verifier": v,
                    })

    for nid, nodeData in census.genericNodes.items():
        for rIndex, row in enumerate(nodeData.get("evidence") or []):
            if isinstance(row, dict) and tm._typeOf(row) == "verifier-attestation":
                v = row.get("verifierId") or row.get("verifier") or row.get("attestor")
                if not v or v not in knownVerifiers:
                    census.unknownVerifiers.append({
                        "skillId": nid,
                        "path": f"registry/nodes/{nid}.json",
                        "rowIndex": rIndex,
                        "verifier": v,
                    })

    # 5. Manifest hashes for schema and benchmark catalog
    catalogFile = root / "registry" / "benchmark-sources.json"
    if catalogFile.is_file():
        rel = str(catalogFile.relative_to(root))
        census.fileHashes[rel] = computeFileHash(catalogFile)

    metaJson = root / "registry" / "schema" / "meta.json"
    if metaJson.is_file():
        rel = str(metaJson.relative_to(root))
        census.fileHashes[rel] = computeFileHash(metaJson)

    census.isValid = not any((census.parseFailures, census.parserDiscrepancies, census.missingIds,
                              census.unresolvedRefs, census.dependencyCycles, census.duplicateIds,
                              census.temporalAnomalies, census.structuralFailures))

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
    repoRoot = here.parents[1]
    engineFiles = [
        here / "trustMagnitude.py",
        here / "shadowEvaluation.py",
        here / "shadowCorpus.py",
        here / "grading.py",
        here / "benchmarkCatalog.py",
        repoRoot / "registry" / "schema" / "meta.json",
        repoRoot / "registry" / "benchmark-sources.json",
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
    Performs caller validation before invoking evaluator to catch malformed structural inputs,
    heterogeneous/nonstring component arrays, duplicate IDs, and invalid evidence shapes.
    """
    # 0. Caller validation: identify defective skills and duplicate IDs before evaluator exposure
    idCounts: dict[str, int] = {}
    for s in skills:
        if isinstance(s, dict) and isinstance(s.get("id"), str) and s.get("id"):
            sid = s["id"]
            idCounts[sid] = idCounts.get(sid, 0) + 1

    validSkills: list[dict[str, Any]] = []
    defectiveAssessments: list[dict[str, Any]] = []

    for idx, s in enumerate(skills):
        if not isinstance(s, dict):
            defectiveAssessments.append({
                "status": "not-evaluated",
                "skillId": None,
                "inputIndex": idx,
                "reason": "skill input must be a dictionary object",
                "scope": "unknown",
                "canonicalStars": None,
            })
            continue

        sid = s.get("id")
        if not sid or not isinstance(sid, str) or not sid.strip():
            defectiveAssessments.append({
                "status": "not-evaluated",
                "skillId": None,
                "inputIndex": idx,
                "reason": "skill input requires a non-empty string id",
                "scope": "suite" if s.get("suiteComponents") is not None else ("effective named" if s.get("genericSkillRef") else "generic"),
                "canonicalStars": s.get("level"),
            })
            continue

        if idCounts.get(sid, 0) > 1:
            defectiveAssessments.append({
                "status": "not-evaluated",
                "skillId": sid,
                "inputIndex": idx,
                "reason": f"duplicate skill id in registry input: {sid}",
                "scope": "suite" if s.get("suiteComponents") is not None else ("effective named" if s.get("genericSkillRef") else "generic"),
                "canonicalStars": s.get("level"),
            })
            continue

        # Structural validation for genericSkillRef, suiteComponents, and evidence shapes
        structErrors = _validateSkillStructural(s, isNamed=True)
        if structErrors:
            defectiveAssessments.append({
                "status": "not-evaluated",
                "skillId": sid,
                "inputIndex": idx,
                "reason": f"structural validation failure: {'; '.join(structErrors)}",
                "scope": "suite" if s.get("suiteComponents") is not None else ("effective named" if s.get("genericSkillRef") else "generic"),
                "canonicalStars": s.get("level"),
            })
            continue

        validSkills.append(s)

    if not validSkills:
        return {
            "status": "not-evaluated",
            "assessments": defectiveAssessments,
            "engineCoverage": {
                "mode": "caller-validation",
                "status": "not-evaluated",
                "expected": len(skills),
                "returned": len(defectiveAssessments),
                "evaluated": 0,
                "notEvaluated": len(defectiveAssessments),
                "structuralValidationFailures": len(defectiveAssessments),
                "registryAttempt": None,
            },
        }

    # 1. Attempt evaluateShadowRegistry on validSkills
    validAssessments: list[dict[str, Any]] = []
    coverageMode = "registry"
    registryFailure = None
    try:
        registryResult = shadow.evaluateShadowRegistry(validSkills, context)
        status = registryResult.get("status")
        returned = registryResult.get("assessments") or []
        if status in ("evaluated", "partial") and len(returned) == len(validSkills):
            validAssessments = returned
        else:
            registryFailure = {"type": "IncompleteRegistryResult", "message":
                               f"status={status!r}, expected={len(validSkills)}, returned={len(returned)}",
                               "fallback": "per-record seam coordinator"}
    except Exception as exc:
        registryFailure = {"type": type(exc).__name__, "message": str(exc)[:500],
                           "fallback": "per-record seam coordinator"}

    # 2. Seam coordinator fallback: topological component-before-suite evaluation on validSkills
    if not validAssessments:
        coverageMode = "per-record-fallback"
        byId = {s["id"]: s for s in validSkills}
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

        validAssessments = [assessmentsById[k] for k in sorted(assessmentsById.keys())]

    allAssessments = validAssessments + defectiveAssessments
    evaluatedCount = sum(1 for a in allAssessments if a.get("status") == "evaluated")
    notEvaluatedCount = len(allAssessments) - evaluatedCount
    overallStatus = "evaluated" if (notEvaluatedCount == 0 and len(allAssessments) > 0) else "partial"

    return {
        "status": overallStatus,
        "assessments": allAssessments,
        "engineCoverage": {
            "mode": coverageMode,
            "status": overallStatus,
            "expected": len(skills),
            "returned": len(allAssessments),
            "evaluated": evaluatedCount,
            "notEvaluated": notEvaluatedCount,
            "structuralValidationFailures": len(defectiveAssessments),
            "registryAttempt": registryFailure,
        },
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
    census = censusRegistry(repoRoot, failClosed=failClosed, evaluationAtUTC=evaluationAtUTC)

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
        "engineCoverage": evaluationResult.get("engineCoverage", {"mode": "unknown", "status": "unreported"}),
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
            "tool": {
                "name": "gaia shadow",
                "module": "gaia_cli.shadowCorpus",
                "version": SHADOW_CORPUS_VERSION,
            },
            "runtime": {
                "pythonVersion": sys.version.split()[0],
                "platform": sys.platform,
            },
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
            "missingDatesCount": len(census.missingDates),
            "missingDates": census.missingDates,
            "unknownVerifiers": census.unknownVerifiers,
            "trustNumberRowsCount": len(census.trustNumberRows),
            "trustNumberRows": [{**row, "disposition": "provenance-only; excluded from current TM scoring"}
                                for row in census.trustNumberRows],
            "duplicateIds": census.duplicateIds,
            "structuralFailuresCount": len(census.structuralFailures),
            "structuralFailures": census.structuralFailures,
            "integrityFindings": {
                "parseFailures": census.parseFailures, "parserDiscrepancies": census.parserDiscrepancies,
                "missingIds": census.missingIds, "unresolvedRefs": census.unresolvedRefs,
                "dependencyCycles": census.dependencyCycles, "duplicateIds": census.duplicateIds,
                "temporalAnomalies": census.temporalAnomalies, "structuralFailures": census.structuralFailures,
            },
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
    toolInfo = meta.get("tool", {})
    runtimeInfo = meta.get("runtime", {})

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
        f"Tool                       : {toolInfo.get('name', 'gaia shadow')} ({toolInfo.get('version', SHADOW_CORPUS_VERSION)})",
        f"Runtime                    : Python {runtimeInfo.get('pythonVersion', sys.version.split()[0])} on {runtimeInfo.get('platform', sys.platform)}",
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
        f"  Structural Failures       : {len(census.get('structuralFailures', []))}",
        f"  Unresolved Generic Refs   : {len(census.get('unresolvedRefs', []))}",
        f"  Dependency Cycles         : {len(census.get('dependencyCycles', []))}",
        f"  Temporal Anomalies        : {len(census.get('temporalAnomalies', []))}",
        f"  Decay Rows Missing Date   : {census.get('missingDatesCount', len(census.get('missingDates', [])))}",
        f"  Unknown Verifiers         : {len(census.get('unknownVerifiers', []))}",
        "--------------------------------------------------------------------------------",
        "SHADOW REPLAY EVALUATION:",
        f"  Overall Status            : {summary.get('overallStatus')}",
        f"  Engine Coverage            : {summary.get('engineCoverage')}",
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

    # Preflight both destinations before creating or replacing either file.
    for target in (jsonPath, summaryPath):
        if target.is_symlink():
            raise ValueError(f"Refusing symlink output file: {target}")
        if target.exists() and not target.is_file():
            raise ValueError(f"Output destination is not a regular file: {target}")

    # Check ancestor symlinks of the output destinations
    rootsToCheck = [Path(repoRoot).resolve()]
    cwdResolved = Path.cwd().resolve()
    if cwdResolved not in rootsToCheck:
        rootsToCheck.append(cwdResolved)

    for target in (jsonPath, summaryPath):
        curr = target.parent
        while curr != curr.parent:
            if curr.is_symlink():
                resolvedCurr = curr.resolve()
                for root in rootsToCheck:
                    for forbidden in FORBIDDEN_CANONICAL_DIRS:
                        forbidPath = root / forbidden
                        if resolvedCurr == forbidPath or forbidPath in resolvedCurr.parents:
                            raise ValueError(
                                f"Refusing output file in symlinked ancestor directory: {curr} (resolves to {resolvedCurr})"
                            )
            curr = curr.parent

    # Stage sibling files, then replace destinations atomically. Replacement never
    # opens a destination, so a raced symlink target is not followed.
    import tempfile
    def atomicWrite(target: Path, content: str) -> None:
        fd, tempName = tempfile.mkstemp(prefix=f".{target.name}.", dir=outPath)
        temp = Path(tempName)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass

    jsonText = json.dumps(reportData, indent=2, sort_keys=True, ensure_ascii=False)
    summaryText = formatImpactSummary(reportData)
    atomicWrite(jsonPath, jsonText)
    atomicWrite(summaryPath, summaryText)

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
    filterStatus = getattr(args, "filter_status", None)

    try:
        reportData = runShadowEvaluation(
            registryPath=registryPath,
            evaluationAtUTC=evaluationAt,
            failClosed=failClosed,
            filterStatus=filterStatus,
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

    integrity = census.get("integrityFindings", {})
    hasIntegrityFailure = any(bool(integrity.get(key)) for key in (
        "parseFailures", "parserDiscrepancies", "missingIds",
        "unresolvedRefs", "dependencyCycles", "duplicateIds",
        "temporalAnomalies", "structuralFailures"
    ))
    if hasIntegrityFailure or (failClosed and summary.get("notEvaluatedCount", 0) > 0) or (
        summary.get("targetSkillsCount", 0) > 0 and summary.get("evaluatedCount", 0) == 0
    ):
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
