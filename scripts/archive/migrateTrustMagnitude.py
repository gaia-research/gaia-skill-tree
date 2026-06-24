#!/usr/bin/env python3
"""I3 — big-bang Trust Magnitude regrade migration.

For each named skill .md:
  1. Strip phantom (anti-auto-mint) rows.
  2. Compute trustMagnitude.
  3. Compute overallTrustGrade.
  4. Compute apexGateStatus (per-predicate).
  5. Mark provisional if any A/S row lacks sourceStartedAt.
  6. Stamp verification.firstEvidenceAt from earliest evidence_added timeline event
     if missing.
  7. Append a migrate_trust_magnitude timeline event (CLI gap — direct edit).
  8. Skip if input hash unchanged (idempotency).

Writes generated-output/migration_summary.json with per-skill stats.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Make repo root and src/ importable. trustMagnitude imports `gaia_cli.evidence`
# directly, so we need src/ on sys.path (not just repo root).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from gaia_cli.trustMagnitude import (  # noqa: E402
    computeOverallTrustGradeFromSkill,
    computeTrustMagnitude,
    enforceAntiAutoMint,
    passesApexGate,
)

NAMED_DIR = REPO_ROOT / "registry" / "named"
NODES_DIR = REPO_ROOT / "registry" / "nodes"
OUT_DIR = REPO_ROOT / "generated-output"
SUMMARY_PATH = OUT_DIR / "migration_summary.json"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def loadNamedSkill(path: Path) -> tuple[dict | None, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def saveNamedSkill(path: Path, frontmatter: dict, body: str) -> None:
    serialized = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{serialized}---\n{body}", encoding="utf-8")


def buildGenericSkillMap(nodesDir: Path) -> dict[str, dict]:
    gmap: dict[str, dict] = {}
    for p in nodesDir.rglob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        sid = d.get("id")
        if sid:
            gmap[sid] = d
    return gmap


def buildNamedSkillMap(namedDir: Path) -> dict[str, dict]:
    """Walk registry/named/**/*.md and return a dict keyed by skill id.

    Named skills have IDs like ``obra/brainstorming`` (with a slash) so they
    will never collide with generic node IDs.  The returned dicts carry the
    full frontmatter so ``_gradedOriginCount`` can inspect ``overallTrustGrade``
    when resolving fusion-recipe origins.
    """
    nmap: dict[str, dict] = {}
    for p in namedDir.rglob("*.md"):
        try:
            fm, _ = loadNamedSkill(p)
        except Exception:
            continue
        if fm is None:
            continue
        sid = fm.get("id")
        if sid:
            nmap[sid] = fm
    return nmap


def computeInputHash(skill: dict) -> str:
    """Stable hash of (skillId + sorted evidence row keys + suiteComponents).

    Bug fixes vs original:
    1. Uses r.get("source") or r.get("url") — evidence rows use "source", not "url".
    2. Includes numeric payload fields that drive the TM computation per row:
       commits, contributors, stars, views, origins(len if list), percentile,
       citations, reviewers, gradedOriginCount, skillCountInRepo, externalStars, verifiers.
    3. Includes suiteComponents (sorted) — adding suite components auto-derives a
       fusion-recipe row worth hundreds of TM points; the hash must cover it.
    """
    sid = skill.get("id") or ""
    rows = []
    for r in skill.get("evidence") or []:
        if not isinstance(r, dict):
            continue
        # Bug fix 1: use "source" field (evidence rows never use "url")
        source = r.get("source") or r.get("url") or ""
        evType = r.get("type") or ""
        grade = r.get("grade") or ""
        # Bug fix 2: include numeric payload fields that drive TM computation
        commits = str(r.get("commits") or 0)
        contributors = str(r.get("contributors") or 0)
        stars = str(r.get("stars") or 0)
        views = str(r.get("views") or 0)
        originsVal = r.get("origins")
        originsHash = str(len(originsVal)) if isinstance(originsVal, list) else str(originsVal or 0)
        percentile = str(r.get("percentile") or 0)
        citations = str(r.get("citations") or 0)
        reviewers = str(r.get("reviewers") or 0)
        gradedOriginCount = str(r.get("gradedOriginCount") or 0)
        skillCountInRepo = str(r.get("skillCountInRepo") or 0)
        externalStars = str(r.get("externalStars") or 0)
        verifiers = str(r.get("verifiers") or 0)
        rows.append(
            f"{source}|{evType}|{grade}"
            f"|commits={commits}|contributors={contributors}|stars={stars}"
            f"|views={views}|origins={originsHash}|percentile={percentile}"
            f"|citations={citations}|reviewers={reviewers}"
            f"|gradedOriginCount={gradedOriginCount}|skillCountInRepo={skillCountInRepo}"
            f"|externalStars={externalStars}|verifiers={verifiers}"
        )
    rows.sort()
    # Bug fix 3: include suiteComponents — auto-derives fusion-recipe at TM-compute time
    suiteComponents = sorted(skill.get("suiteComponents") or [])
    suitePayload = "suiteComponents=" + ",".join(suiteComponents)
    payload = sid + "::" + "||".join(rows) + "::" + suitePayload
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hasMissingSourceStartedAt(skill: dict) -> bool:
    """True if any A or S graded evidence row is missing sourceStartedAt."""
    for r in skill.get("evidence") or []:
        if not isinstance(r, dict):
            continue
        grade = (r.get("grade") or "").upper()
        if grade in {"A", "S"} and not r.get("sourceStartedAt"):
            return True
    return False


def firstEvidenceAddedTimestamp(skill: dict) -> str | None:
    timeline = skill.get("timeline") or []
    earliest: str | None = None
    for ev in timeline:
        if not isinstance(ev, dict):
            continue
        if ev.get("action") == "evidence_added":
            ts = ev.get("timestamp")
            if ts and (earliest is None or ts < earliest):
                earliest = ts
    return earliest


def nowIso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def migrateSkill(
    path: Path,
    mergedMap: dict[str, dict],
    stats: dict[str, Any],
    dryRun: bool,
) -> None:
    fm, body = loadNamedSkill(path)
    if fm is None:
        print(f"  [skip] {path.relative_to(REPO_ROOT)} — no frontmatter")
        return

    skillId = fm.get("id") or path.stem
    relPath = path.relative_to(REPO_ROOT).as_posix()

    # Idempotency check
    inputHash = computeInputHash(fm)
    if fm.get("trustMagnitudeInputHash") == inputHash:
        stats["skipped"] += 1
        print(f"  [skip] {skillId} — hash unchanged")
        return

    # Snapshot before for delta tracking
    oldTm = fm.get("trustMagnitude")
    oldGrade = fm.get("overallTrustGrade") or "ungraded"

    # Phantom-row removal — capture which rows would be stripped
    originalEvidence = list(fm.get("evidence") or [])
    cleanedEvidence = enforceAntiAutoMint(fm)
    removed = []
    cleanedKeys = {(r.get("url"), r.get("type")) for r in cleanedEvidence if isinstance(r, dict)}
    for r in originalEvidence:
        if not isinstance(r, dict):
            continue
        key = (r.get("url"), r.get("type"))
        if key not in cleanedKeys:
            removed.append({
                "skillId": skillId,
                "url": r.get("url"),
                "type": r.get("type"),
                "grade": r.get("grade"),
            })
    if removed:
        # Strip phantom rows in-place
        fm["evidence"] = cleanedEvidence
        stats["phantomRemovals"].extend(removed)

    # Compute new TM, grade, apex gate
    tmRaw = computeTrustMagnitude(fm, mergedMap)
    tm = round(float(tmRaw), 2) if tmRaw is not None else 0.0
    grade = computeOverallTrustGradeFromSkill(fm, mergedMap) or "ungraded"
    gateResult = passesApexGate(fm, {"genericSkillMap": mergedMap})

    # Provisional check — A/S rows missing sourceStartedAt
    provisional = hasMissingSourceStartedAt(fm)

    # firstEvidenceAt backfill
    verification = fm.get("verification") if isinstance(fm.get("verification"), dict) else {}
    firstEvidenceAt = verification.get("firstEvidenceAt")
    newlySetFirstEvidenceAt = False
    if not firstEvidenceAt:
        backfill = firstEvidenceAddedTimestamp(fm)
        if backfill:
            verification = dict(verification)
            verification["firstEvidenceAt"] = backfill
            newlySetFirstEvidenceAt = True

    # Write back
    fm["trustMagnitude"] = tm
    fm["overallTrustGrade"] = grade
    fm["apexGateStatus"] = gateResult
    fm["trustMagnitudeInputHash"] = inputHash
    if provisional:
        fm["provisional"] = True
    elif "provisional" in fm:
        # Clear stale provisional flag if no longer applicable
        del fm["provisional"]
    if newlySetFirstEvidenceAt:
        fm["verification"] = verification

    # Append timeline event
    timeline = fm.get("timeline")
    if not isinstance(timeline, list):
        timeline = []
    timeline.append({
        "action": "migrate_trust_magnitude",
        "timestamp": nowIso(),
        "details": (
            f"TM {oldTm} -> {tm}, grade {oldGrade} -> {grade} "
            "(direct edit -- CLI gap)"
        ),
    })
    fm["timeline"] = timeline

    # Stats
    stats["processed"] += 1
    stats["tmDeltas"].append({
        "skillId": skillId,
        "path": relPath,
        "oldTm": oldTm,
        "newTm": tm,
        "delta": (tm - float(oldTm)) if isinstance(oldTm, (int, float)) else None,
    })
    transition = f"{oldGrade} -> {grade}"
    stats["gradeTransitions"][transition] = stats["gradeTransitions"].get(transition, 0) + 1
    if provisional:
        stats["provisionalSkills"].append({"skillId": skillId, "path": relPath})

    # Track apex gate status for known apex skills
    if skillId in {"mattpocock/skills", "ruvnet/ruflo"}:
        stats["apexGateInspected"][skillId] = {
            "tm": tm,
            "grade": grade,
            "gate": gateResult,
            "isApex": all(v is True for v in gateResult.values() if v is not None),
        }

    if dryRun:
        print(f"  [dry] {skillId} TM {oldTm} -> {tm}, grade {oldGrade} -> {grade}")
    else:
        saveNamedSkill(path, fm, body)
        print(f"  [ok]  {skillId} TM {oldTm} -> {tm}, grade {oldGrade} -> {grade}")


def main(args: argparse.Namespace) -> int:
    if not NAMED_DIR.exists():
        print(f"ERROR: named dir not found: {NAMED_DIR}", file=sys.stderr)
        return 2

    print(f"Building genericSkillMap from {NODES_DIR}...")
    genericSkillMap = buildGenericSkillMap(NODES_DIR)
    print(f"  loaded {len(genericSkillMap)} generic skills")

    print(f"Building namedSkillMap from {NAMED_DIR}...")
    namedSkillMap = buildNamedSkillMap(NAMED_DIR)
    print(f"  loaded {len(namedSkillMap)} named skills")

    # Merge: named skill IDs use 'owner/name' form — no collision with generic IDs.
    # Named skill grades are initially whatever is on disk (all cleared to 'ungraded'
    # before this run).  As each skill is migrated its updated frontmatter is written
    # back into mergedMap so subsequent skills (esp. suites) see fresh grades.
    mergedMap: dict[str, dict] = {**genericSkillMap, **namedSkillMap}

    paths = sorted(NAMED_DIR.rglob("*.md"))
    print(f"Found {len(paths)} named skill files")

    stats: dict[str, Any] = {
        "startedAt": nowIso(),
        "totalFiles": len(paths),
        "processed": 0,
        "skipped": 0,
        "tmDeltas": [],
        "gradeTransitions": {},
        "phantomRemovals": [],
        "provisionalSkills": [],
        "apexGateInspected": {},
        "dryRun": bool(args.dryRun),
    }

    for p in paths:
        try:
            migrateSkill(p, mergedMap, stats, args.dryRun)
            # Update mergedMap with the newly-migrated frontmatter so later skills
            # (especially suites) see accurate grades for their components.
            fm, _ = loadNamedSkill(p)
            if fm is not None:
                sid = fm.get("id")
                if sid:
                    mergedMap[sid] = fm
        except Exception as exc:
            print(f"  [err] {p.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)
            stats.setdefault("errors", []).append({
                "path": p.relative_to(REPO_ROOT).as_posix(),
                "error": str(exc),
            })

    stats["finishedAt"] = nowIso()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(stats, indent=2, sort_keys=False), encoding="utf-8")
    print()
    print(f"Summary: processed={stats['processed']} skipped={stats['skipped']} "
          f"phantomRemovals={len(stats['phantomRemovals'])} "
          f"provisional={len(stats['provisionalSkills'])}")
    print(f"Summary written to {SUMMARY_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="I3 — big-bang Trust Magnitude regrade")
    parser.add_argument("--dry-run", dest="dryRun", action="store_true",
                        help="Compute fields but don't write files")
    parsed = parser.parse_args()
    sys.exit(main(parsed))
