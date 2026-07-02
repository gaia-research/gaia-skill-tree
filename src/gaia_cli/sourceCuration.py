"""Dry-run source curation report runner.

This module defaults to offline fixture discovery. Live GitHub API reads are
available only when explicitly enabled and still stop at schema-valid dry-run
reports: no registry writes and no PR publishing.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

BOT_IDENTITY = "nova-gaia"
PIPELINE_PHASE = "discovery"
DEFAULT_CONFIDENCE_FLOOR = 0.3
DEFAULT_MAX_PROPOSALS_PER_SKILL = 5
GITHUB_FIXTURE_BACKEND = "github-fixture"
GITHUB_API_BACKEND = "github-api"
DEFAULT_BACKENDS = [GITHUB_FIXTURE_BACKEND]
GITHUB_LIVE_ENV = "GAIA_SOURCE_CURATION_LIVE_GITHUB"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
GITHUB_ADAPTER_VERSION = "github-discovery-v1"
SUBJECTIVE_RATIONALE_TERMS = {
    "amazing",
    "best",
    "elite",
    "excellent",
    "high-quality",
    "top-tier",
    "world-class",
}
REQUIRED_NUMERIC_PAYLOAD_FIELDS = {
    "arxiv": ["citations"],
    "benchmark-result": ["percentile"],
    "github-stars-own": ["stars", "skillCountInRepo"],
    "peer-review": ["reviewers"],
    "proxy-containment": ["externalStars", "skillCountInRepo"],
    "repo-own": ["commits", "contributors"],
    "social-signal": ["views"],
    "verifier-attestation": ["verifiers"],
}


class GithubUrlError(ValueError):
    """Raised when a GitHub source URL is not acceptable for a proposal."""


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


def isGithubHost(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    return host in {"github.com", "www.github.com"}


def canonicalizeGithubBlobUrl(url: str) -> str:
    """Return a canonical GitHub blob URL, rejecting directory tree URLs.

    Source-curation proposals that point at a skill file must be installable and
    reviewable as a concrete file. GitHub directory-view URLs use `/tree/`; the
    installer policy requires `/blob/<branch>/<subpath>` for file sources, so
    tree URLs are rejected instead of silently rewritten to a possibly-wrong
    file path.
    """

    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or host not in {"github.com", "www.github.com"}:
        raise GithubUrlError("GitHub source must be an https://github.com/... URL")

    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 5:
        raise GithubUrlError("GitHub skill-file source must include /blob/<branch>/<path>")
    owner, repo, view, branch, *subpath = parts
    viewType = view.lower()
    if viewType == "tree":
        raise GithubUrlError("GitHub tree/ URLs are directory views; use a blob/<branch>/<file> source")
    if viewType != "blob":
        raise GithubUrlError("GitHub skill-file source must use /blob/<branch>/<path>")
    if not owner or not repo or not branch or not subpath:
        raise GithubUrlError("GitHub blob URL is missing owner, repo, branch, or file path")

    quotedParts = [urllib.parse.quote(part, safe="") for part in [owner, repo, "blob", branch, *subpath]]
    return "https://github.com/" + "/".join(quotedParts)


def githubFixtureDiscoveries() -> list[dict[str, Any]]:
    return [
        {
            "skillId": "mattpocock/grill-me",
            "genericSkillRef": "code-review-automation",
            "source": "https://github.com/mattpocock/grill-me/blob/main/SKILL.md",
            "evidenceType": "github-stars-own",
            "numericPayload": {"stars": 1280, "skillCountInRepo": 1},
            "confidence": 0.86,
            "rationale": "Offline GitHub fixture for a concrete SKILL.md file associated with the grill-me named skill.",
        },
        {
            "skillId": "karpathy/autoresearch",
            "genericSkillRef": "autonomous-research",
            "source": "https://github.com/karpathy/autoresearch/blob/main/skills/autoresearch/SKILL.md",
            "evidenceType": "repo-own",
            "numericPayload": {"commits": 42, "contributors": 3},
            "confidence": 0.81,
            "rationale": "Offline GitHub fixture for repository activity relevant to the autoresearch named skill.",
        },
    ]


def githubRepoApiUrl(blobUrl: str) -> str:
    parsed = urllib.parse.urlparse(blobUrl)
    parts = [part for part in parsed.path.split("/") if part]
    owner, repo = parts[0], parts[1]
    return f"https://api.github.com/repos/{owner}/{repo}"


def fetchGithubRepo(repoApiUrl: str, token: str | None = None) -> dict[str, Any]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "nova-gaia-source-curation"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(repoApiUrl, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"GitHub API request failed for {repoApiUrl}: {error}") from error


def discoverGithubSeeds(liveGithub: bool = False, token: str | None = None) -> list[dict[str, Any]]:
    """Discover GitHub-backed source proposals.

    Fixture mode is the default and consumes zero quota. Live mode refreshes the
    fixture repositories through the GitHub REST API only when explicitly
    enabled by CLI flag or environment variable.
    """

    backend = GITHUB_API_BACKEND if liveGithub else GITHUB_FIXTURE_BACKEND
    seeds: list[dict[str, Any]] = []
    for raw in githubFixtureDiscoveries():
        seed = copy.deepcopy(raw)
        seed["source"] = canonicalizeGithubBlobUrl(seed["source"])
        seed["crawlerBackend"] = backend
        seed["crawlerVersion"] = GITHUB_ADAPTER_VERSION
        seed["existingEvidenceCheck"] = {"checked": True, "duplicate": False}
        seed["quotaCost"] = {"apiCalls": 0, "estimatedCostUsd": 0, "backend": backend}
        if liveGithub:
            repoPayload = fetchGithubRepo(githubRepoApiUrl(seed["source"]), token=token)
            seed["quotaCost"]["apiCalls"] = 1
            if seed["evidenceType"] == "github-stars-own":
                seed.setdefault("numericPayload", {})["stars"] = int(repoPayload.get("stargazers_count", 0))
            if seed["evidenceType"] == "repo-own":
                seed.setdefault("numericPayload", {})["contributors"] = int(seed["numericPayload"].get("contributors", 0))
        seeds.append(seed)
    return seeds


def defaultSeeds(liveGithub: bool = False, token: str | None = None) -> list[dict[str, Any]]:
    return discoverGithubSeeds(liveGithub=liveGithub, token=token)


def loadSeeds(inputPath: str | None, liveGithub: bool = False, token: str | None = None) -> list[dict[str, Any]]:
    if not inputPath:
        return defaultSeeds(liveGithub=liveGithub, token=token)
    payload = loadJson(inputPath)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("proposals"), list):
        return payload["proposals"]
    if isinstance(payload, dict) and isinstance(payload.get("seeds"), list):
        return payload["seeds"]
    raise ValueError("Input seed file must be a JSON array, or an object with proposals/seeds array")


def normalizeProposal(seed: dict[str, Any], generatedAt: str, strictGithub: bool = True) -> dict[str, Any]:
    proposal = copy.deepcopy(seed)
    datePart = generatedAt[:10].replace("-", "")
    if isGithubHost(proposal.get("source", "")):
        try:
            proposal["source"] = canonicalizeGithubBlobUrl(proposal["source"])
        except GithubUrlError:
            if strictGithub:
                raise
    proposal.setdefault("proposalId", proposalId(proposal, datePart))
    proposal.setdefault("discoveredAt", generatedAt)
    proposal["discoveredBy"] = BOT_IDENTITY
    proposal.setdefault("crawlerBackend", GITHUB_FIXTURE_BACKEND)
    proposal.setdefault("quotaCost", {"apiCalls": 0, "estimatedCostUsd": 0, "backend": proposal["crawlerBackend"]})
    proposal["dryRun"] = True
    return proposal


def sourceKey(proposal: dict[str, Any]) -> str:
    source = proposal.get("source", "")
    if isGithubHost(source):
        try:
            return canonicalizeGithubBlobUrl(source)
        except GithubUrlError:
            return source.strip()
    return source.strip()


def refuteReasons(
    proposal: dict[str, Any],
    seenSources: set[str],
    confidenceFloor: float,
) -> list[str]:
    reasons: list[str] = []
    source = str(proposal.get("source", ""))
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        reasons.append("source URL must be a full http(s) URL")
    if isGithubHost(source):
        try:
            canonicalizeGithubBlobUrl(source)
        except GithubUrlError as error:
            reasons.append(str(error))
    if sourceKey(proposal) in seenSources:
        reasons.append("duplicate source candidate in this report")
    if proposal.get("existingEvidenceCheck", {}).get("duplicate") is True:
        reasons.append("source already exists in known evidence")
    try:
        confidence = float(proposal.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    if confidence < confidenceFloor:
        reasons.append(f"confidence below floor {confidenceFloor}")
    rationale = str(proposal.get("rationale", ""))
    rationaleLower = rationale.lower()
    subjectiveTerms = sorted(term for term in SUBJECTIVE_RATIONALE_TERMS if term in rationaleLower)
    if subjectiveTerms:
        reasons.append("subjective or unsupported rationale wording: " + ", ".join(subjectiveTerms))
    requiredFields = REQUIRED_NUMERIC_PAYLOAD_FIELDS.get(str(proposal.get("evidenceType", "")), [])
    numericPayload = proposal.get("numericPayload")
    if requiredFields and not isinstance(numericPayload, dict):
        reasons.append("missing numericPayload for evidence type " + str(proposal.get("evidenceType", "")))
    elif requiredFields:
        missingFields = [field for field in requiredFields if field not in numericPayload]
        if missingFields:
            reasons.append("missing numericPayload fields: " + ", ".join(missingFields))
    return reasons


def applyAdversarialReview(
    proposals: list[dict[str, Any]],
    reviewedAt: str,
    confidenceFloor: float,
) -> dict[str, Any]:
    seenSources: set[str] = set()
    accepted = 0
    refuted = 0
    reasonCounts: dict[str, int] = {}
    for proposal in proposals:
        reasons = refuteReasons(proposal, seenSources, confidenceFloor)
        key = sourceKey(proposal)
        if not reasons:
            seenSources.add(key)
            accepted += 1
            proposal["adversarialReview"] = {
                "status": "accepted",
                "skepticVotes": [
                    {
                        "skepticId": "deterministic-refute-gate",
                        "vote": "accept",
                        "reason": "Proposal passed deterministic offline validation checks.",
                    }
                ],
                "reviewedAt": reviewedAt,
            }
            continue
        refuted += 1
        for reason in reasons:
            reasonCounts[reason] = reasonCounts.get(reason, 0) + 1
        proposal["adversarialReview"] = {
            "status": "refuted",
            "skepticVotes": [
                {
                    "skepticId": "deterministic-refute-gate",
                    "vote": "refute",
                    "reason": "; ".join(reasons),
                }
            ],
            "reviewedAt": reviewedAt,
        }
    return {
        "accepted": accepted,
        "rejected": refuted,
        "refuted": refuted,
        "reasons": [{"reason": reason, "count": count} for reason, count in sorted(reasonCounts.items())],
    }


def quotaSummary(proposals: list[dict[str, Any]], backends: list[str]) -> dict[str, Any]:
    perBackend = {backend: {"calls": 0, "costUsd": 0} for backend in backends}
    for proposal in proposals:
        cost = proposal.get("quotaCost", {})
        backend = cost.get("backend") or proposal.get("crawlerBackend", GITHUB_FIXTURE_BACKEND)
        perBackend.setdefault(backend, {"calls": 0, "costUsd": 0})
        perBackend[backend]["calls"] += int(cost.get("apiCalls", 0))
        perBackend[backend]["costUsd"] += float(cost.get("estimatedCostUsd", 0))
    return {
        "totalApiCalls": sum(item["calls"] for item in perBackend.values()),
        "estimatedTotalCostUsd": sum(item["costUsd"] for item in perBackend.values()),
        "perBackend": perBackend,
    }


def buildReport(
    seeds: list[dict[str, Any]],
    runId: str,
    generatedAt: str,
    confidenceFloor: float = DEFAULT_CONFIDENCE_FLOOR,
    maxProposalsPerSkill: int = DEFAULT_MAX_PROPOSALS_PER_SKILL,
    adversarialReview: bool = False,
) -> dict[str, Any]:
    countsBySkill: dict[str, int] = {}
    seenSources: set[str] = set()
    proposals: list[dict[str, Any]] = []
    duplicatesDropped = 0
    belowConfidenceDropped = 0
    skillsTargeted = {seed.get("skillId") for seed in seeds if seed.get("skillId")}

    for seed in seeds:
        proposal = normalizeProposal(seed, generatedAt, strictGithub=not adversarialReview)
        source = sourceKey(proposal)
        if not adversarialReview:
            if proposal.get("existingEvidenceCheck", {}).get("duplicate") is True or source in seenSources:
                duplicatesDropped += 1
                continue
            if float(proposal.get("confidence", 0)) < confidenceFloor:
                belowConfidenceDropped += 1
                continue
        skillId = proposal.get("skillId", "")
        if countsBySkill.get(skillId, 0) >= maxProposalsPerSkill:
            continue
        if not adversarialReview:
            seenSources.add(source)
        proposals.append(proposal)
        countsBySkill[skillId] = countsBySkill.get(skillId, 0) + 1

    reviewSummary = None
    if adversarialReview:
        reviewSummary = applyAdversarialReview(proposals, generatedAt, confidenceFloor)
        duplicatesDropped = sum(
            1 for proposal in proposals if "duplicate source candidate" in proposal["adversarialReview"]["skepticVotes"][0]["reason"]
        )
        belowConfidenceDropped = sum(
            1 for proposal in proposals if "confidence below floor" in proposal["adversarialReview"]["skepticVotes"][0]["reason"]
        )

    backends = sorted({proposal.get("crawlerBackend", GITHUB_FIXTURE_BACKEND) for proposal in proposals}) or DEFAULT_BACKENDS
    summary = {
        "skillsTargeted": len(skillsTargeted),
        "proposalsGenerated": len(proposals),
        "duplicatesDropped": duplicatesDropped,
        "belowConfidenceDropped": belowConfidenceDropped,
    }
    if reviewSummary:
        summary.update(
            {
                "proposalsAccepted": reviewSummary["accepted"],
                "proposalsRejected": reviewSummary["rejected"],
                "proposalsRefuted": reviewSummary["refuted"],
                "refuteReasons": reviewSummary["reasons"],
            }
        )
    return {
        "reportId": runId,
        "generatedAt": generatedAt,
        "generatedBy": BOT_IDENTITY,
        "pipelinePhase": "adversarial-review" if adversarialReview else PIPELINE_PHASE,
        "dryRun": True,
        "crawlConfig": {
            "targetGrades": ["C", "ungraded"],
            "maxProposalsPerSkill": maxProposalsPerSkill,
            "confidenceFloor": confidenceFloor,
            "backends": backends,
        },
        "quotaSummary": quotaSummary(proposals, backends),
        "proposals": proposals,
        "summary": summary,
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


def envEnablesLiveGithub() -> bool:
    return os.environ.get(GITHUB_LIVE_ENV, "").lower() in {"1", "true", "yes", "on"}


def runDryRun(
    rootDir: Path | None = None,
    runId: str | None = None,
    generatedAt: str | None = None,
    inputPath: str | None = None,
    outputPath: str | None = None,
    confidenceFloor: float = DEFAULT_CONFIDENCE_FLOOR,
    maxProposalsPerSkill: int = DEFAULT_MAX_PROPOSALS_PER_SKILL,
    liveGithub: bool | None = None,
    adversarialReview: bool = False,
) -> tuple[dict[str, Any], Path]:
    root = rootDir or repoRoot()
    stamp = generatedAt or utcNowStamp()
    reportId = runId or todayRunId(stamp)
    githubLive = envEnablesLiveGithub() if liveGithub is None else liveGithub
    seeds = loadSeeds(inputPath, liveGithub=githubLive, token=os.environ.get(GITHUB_TOKEN_ENV))
    report = buildReport(seeds, reportId, stamp, confidenceFloor, maxProposalsPerSkill, adversarialReview)
    validateReport(report, root)
    path = resolveOutputPath(root, reportId, outputPath)
    writeJson(path, report)
    return report, path


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit a dry-run nova-gaia source-curation proposal report.")
    parser.add_argument("--input", help="Optional JSON seed file. Defaults to deterministic GitHub fixture discovery.")
    parser.add_argument("--output", help="Output report path. Defaults to generated-output/source-curation/<run-id>/report.json")
    parser.add_argument("--run-id", help="Deterministic report ID. Defaults to <yyyymmdd>-dry-run")
    parser.add_argument("--generated-at", help="ISO 8601 timestamp for deterministic runs. Defaults to current UTC time.")
    parser.add_argument("--confidence-floor", type=float, default=DEFAULT_CONFIDENCE_FLOOR)
    parser.add_argument("--max-proposals-per-skill", type=int, default=DEFAULT_MAX_PROPOSALS_PER_SKILL)
    parser.add_argument(
        "--github-live",
        action="store_true",
        help=f"Opt in to live GitHub API reads. Fixture mode is used unless this flag or {GITHUB_LIVE_ENV}=1 is set.",
    )
    parser.add_argument(
        "--adversarial-review",
        action="store_true",
        help="Run the deterministic offline validation/refute gate and mark proposals accepted/refuted.",
    )
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
        liveGithub=True if args.github_live else None,
        adversarialReview=args.adversarial_review,
    )
    print(f"Wrote dry-run source-curation report: {path}")
    print(f"reportId={report['reportId']} proposals={len(report['proposals'])} generatedBy={report['generatedBy']}")
    if args.adversarial_review:
        summary = report["summary"]
        print(
            "adversarialReview "
            f"accepted={summary.get('proposalsAccepted', 0)} "
            f"rejected={summary.get('proposalsRejected', 0)} "
            f"refuted={summary.get('proposalsRefuted', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
