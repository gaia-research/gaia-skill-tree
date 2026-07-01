"""Dry-run source curation report runner.

This module intentionally performs no network calls and no registry writes. It
emits schema-validated proposal reports for human review only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

BOT_IDENTITY = "nova-gaia"
PIPELINE_PHASE = "discovery"
DEFAULT_CONFIDENCE_FLOOR = 0.3
DEFAULT_MAX_PROPOSALS_PER_SKILL = 5
DEFAULT_BACKENDS = ["fixture-discovery"]


def repoRoot() -> Path:
    return Path(__file__).resolve().parents[2]


def utcNowStamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def todayRunId(nowStamp: str | None = None) -> str:
    stamp = nowStamp or utcNowStamp()
    return stamp[:10].replace("-", "") + "-dry-run"


def loadJson(path: str | os.PathLike[str]) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def writeJson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def schemaStore(schemaDir: Path) -> dict[str, dict[str, Any]]:
    store: dict[str, dict[str, Any]] = {}
    for schemaPath in schemaDir.glob("*.schema.json"):
        schema = loadJson(schemaPath)
        schemaId = schema.get("$id")
        if schemaId:
            store[schemaId] = schema
        store[schemaPath.name] = schema
    return store


def formatChecker() -> jsonschema.FormatChecker:
    checker = jsonschema.FormatChecker()

    if "date-time" not in checker.checkers:
        @checker.checks("date-time", raises=ValueError)
        def isDateTime(value: object) -> bool:
            if not isinstance(value, str):
                return True
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.tzinfo is not None

    return checker


def validateReport(report: dict[str, Any], rootDir: Path | None = None) -> None:
    root = rootDir or repoRoot()
    schemaDir = root / "registry" / "schema"
    schema = loadJson(schemaDir / "sourceProposalReport.schema.json")
    resolver = jsonschema.RefResolver("file://" + str(schemaDir) + "/", {}, store=schemaStore(schemaDir))
    validator = jsonschema.Draft7Validator(schema, resolver=resolver, format_checker=formatChecker())
    validator.validate(report)


def safeId(value: str) -> str:
    value = value.lower().replace("/", "-")
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "proposal"


def proposalId(seed: dict[str, Any], datePart: str) -> str:
    basis = "|".join([seed.get("skillId", ""), seed.get("source", ""), seed.get("evidenceType", "")])
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:8]
    return f"{safeId(seed.get('skillId', 'unknown-skill'))}-{digest}-{datePart}"


def defaultSeeds() -> list[dict[str, Any]]:
    return [
        {
            "skillId": "mattpocock/grill-me",
            "genericSkillRef": "code-review-automation",
            "source": "https://example.com/source-curation/grill-me-demo",
            "evidenceType": "social-signal",
            "numericPayload": {"views": 2400, "likes": 120, "comments": 18},
            "crawlerBackend": "fixture-discovery",
            "confidence": 0.74,
            "rationale": "Deterministic fixture describing a public demonstration relevant to the grill-me named skill.",
            "existingEvidenceCheck": {"checked": True, "duplicate": False},
        },
        {
            "skillId": "karpathy/autoresearch",
            "genericSkillRef": "autonomous-research",
            "source": "https://example.com/source-curation/autoresearch-repo",
            "evidenceType": "repo-own",
            "numericPayload": {"commits": 42, "contributors": 3},
            "crawlerBackend": "fixture-discovery",
            "confidence": 0.81,
            "rationale": "Deterministic fixture describing repository activity relevant to the autoresearch named skill.",
            "existingEvidenceCheck": {"checked": True, "duplicate": False},
        },
    ]


def loadSeeds(inputPath: str | None) -> list[dict[str, Any]]:
    if not inputPath:
        return defaultSeeds()
    payload = loadJson(inputPath)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("proposals"), list):
        return payload["proposals"]
    if isinstance(payload, dict) and isinstance(payload.get("seeds"), list):
        return payload["seeds"]
    raise ValueError("Input seed file must be a JSON array, or an object with proposals/seeds array")


def normalizeProposal(seed: dict[str, Any], generatedAt: str) -> dict[str, Any]:
    proposal = copy.deepcopy(seed)
    datePart = generatedAt[:10].replace("-", "")
    proposal.setdefault("proposalId", proposalId(proposal, datePart))
    proposal.setdefault("discoveredAt", generatedAt)
    proposal["discoveredBy"] = BOT_IDENTITY
    proposal.setdefault("crawlerBackend", "fixture-discovery")
    proposal["dryRun"] = True
    return proposal


def buildReport(
    seeds: list[dict[str, Any]],
    runId: str,
    generatedAt: str,
    confidenceFloor: float = DEFAULT_CONFIDENCE_FLOOR,
    maxProposalsPerSkill: int = DEFAULT_MAX_PROPOSALS_PER_SKILL,
) -> dict[str, Any]:
    countsBySkill: dict[str, int] = {}
    proposals: list[dict[str, Any]] = []
    duplicatesDropped = 0
    belowConfidenceDropped = 0
    skillsTargeted = {seed.get("skillId") for seed in seeds if seed.get("skillId")}

    for seed in seeds:
        if seed.get("existingEvidenceCheck", {}).get("duplicate") is True:
            duplicatesDropped += 1
            continue
        if float(seed.get("confidence", 0)) < confidenceFloor:
            belowConfidenceDropped += 1
            continue
        skillId = seed.get("skillId", "")
        if countsBySkill.get(skillId, 0) >= maxProposalsPerSkill:
            continue
        proposal = normalizeProposal(seed, generatedAt)
        proposals.append(proposal)
        countsBySkill[skillId] = countsBySkill.get(skillId, 0) + 1

    backends = sorted({proposal.get("crawlerBackend", "fixture-discovery") for proposal in proposals}) or DEFAULT_BACKENDS
    return {
        "reportId": runId,
        "generatedAt": generatedAt,
        "generatedBy": BOT_IDENTITY,
        "pipelinePhase": PIPELINE_PHASE,
        "dryRun": True,
        "crawlConfig": {
            "targetGrades": ["C", "ungraded"],
            "maxProposalsPerSkill": maxProposalsPerSkill,
            "confidenceFloor": confidenceFloor,
            "backends": backends,
        },
        "quotaSummary": {
            "totalApiCalls": 0,
            "estimatedTotalCostUsd": 0,
            "perBackend": {backend: {"calls": 0, "costUsd": 0} for backend in backends},
        },
        "proposals": proposals,
        "summary": {
            "skillsTargeted": len(skillsTargeted),
            "proposalsGenerated": len(proposals),
            "duplicatesDropped": duplicatesDropped,
            "belowConfidenceDropped": belowConfidenceDropped,
        },
    }


def defaultOutputPath(rootDir: Path, runId: str) -> Path:
    return rootDir / "generated-output" / "source-curation" / runId / "report.json"


def resolveOutputPath(rootDir: Path, runId: str, outputPath: str | None = None) -> Path:
    allowedDir = (rootDir / "generated-output" / "source-curation").resolve()
    path = Path(outputPath) if outputPath else defaultOutputPath(rootDir, runId)
    if not path.is_absolute():
        path = rootDir / path
    resolved = path.resolve()
    if not resolved.is_relative_to(allowedDir):
        raise ValueError(f"Output path must stay under {allowedDir}")
    return resolved


def runDryRun(
    rootDir: Path | None = None,
    runId: str | None = None,
    generatedAt: str | None = None,
    inputPath: str | None = None,
    outputPath: str | None = None,
    confidenceFloor: float = DEFAULT_CONFIDENCE_FLOOR,
    maxProposalsPerSkill: int = DEFAULT_MAX_PROPOSALS_PER_SKILL,
) -> tuple[dict[str, Any], Path]:
    root = rootDir or repoRoot()
    stamp = generatedAt or utcNowStamp()
    reportId = runId or todayRunId(stamp)
    seeds = loadSeeds(inputPath)
    report = buildReport(seeds, reportId, stamp, confidenceFloor, maxProposalsPerSkill)
    validateReport(report, root)
    path = resolveOutputPath(root, reportId, outputPath)
    writeJson(path, report)
    return report, path


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit a dry-run nova-gaia source-curation proposal report.")
    parser.add_argument("--input", help="Optional JSON seed file. Defaults to deterministic fixture discovery.")
    parser.add_argument("--output", help="Output report path. Defaults to generated-output/source-curation/<run-id>/report.json")
    parser.add_argument("--run-id", help="Deterministic report ID. Defaults to <yyyymmdd>-dry-run")
    parser.add_argument("--generated-at", help="ISO 8601 timestamp for deterministic runs. Defaults to current UTC time.")
    parser.add_argument("--confidence-floor", type=float, default=DEFAULT_CONFIDENCE_FLOOR)
    parser.add_argument("--max-proposals-per-skill", type=int, default=DEFAULT_MAX_PROPOSALS_PER_SKILL)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = buildParser().parse_args(argv)
    report, path = runDryRun(
        runId=args.run_id,
        generatedAt=args.generated_at,
        inputPath=args.input,
        outputPath=args.output,
        confidenceFloor=args.confidence_floor,
        maxProposalsPerSkill=args.max_proposals_per_skill,
    )
    print(f"Wrote dry-run source-curation report: {path}")
    print(f"reportId={report['reportId']} proposals={len(report['proposals'])} generatedBy={report['generatedBy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
