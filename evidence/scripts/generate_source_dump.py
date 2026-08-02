from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
from datetime import date
from typing import Any

import yaml

from evidence_type_partitions import (
    CANONICAL_EVIDENCE_TYPES,
    byTypeDir as defaultByTypeDir,
    iterTypePartitionPaths,
    normalizeEvidenceType,
    typeOutputPath,
)

STARS_CACHE = {
    "mattpocock/skills": 133210,
    "ruvnet/ruflo": 59957,
    "garrytan/gstack": 110930,
    "obra/superpowers": 230818,
    "ruvnet/agentdb": 66,
    "pbakaus/impeccable": 39158,
    "0xDarkMatter/claude-mods": 22,
    "browser-use/browser-harness": 15008,
    "browser-use/browser-use": 99295,
    "addyosmani/agent-skills": 62101,
}


def getLiveStars(repoPath: str) -> int | None:
    if repoPath in STARS_CACHE:
        return STARS_CACHE[repoPath]
    try:
        out = subprocess.check_output(
            ["gh", "repo", "view", repoPath, "--json", "stargazerCount"], text=True
        )
        data = json.loads(out)
        stars = data.get("stargazerCount", 0)
        STARS_CACHE[repoPath] = stars
        return stars
    except Exception as e:  # pragma: no cover - depends on local gh/network state
        print(f"Warning: Could not fetch stars for {repoPath}: {e}")
        return None


def parseRepoPath(url: str | None) -> str | None:
    if not url or "github.com/" not in url:
        return None
    try:
        path = url.split("github.com/")[1]
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    except Exception:
        pass
    return None


def loadJson(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolveGaiaJson(path: str) -> str:
    if os.path.exists(path):
        return path
    for fallbackPath in ["docs/graph/gaia.json", ".gaia/registry/gaia.json"]:
        if os.path.exists(fallbackPath):
            return fallbackPath
    return path


def resolveNamedSkillsJson(path: str) -> str:
    if os.path.exists(path):
        return path
    for fallbackPath in ["docs/graph/named/index.json", ".gaia/registry/named-skills.json"]:
        if os.path.exists(fallbackPath):
            return fallbackPath
    return path


def loadGenericEvidence(gaiaData: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    genericEvidence: dict[str, list[dict[str, Any]]] = {}
    for skill in gaiaData.get("skills", []):
        if "id" in skill:
            genericEvidence[skill["id"]] = skill.get("evidence") or []
    return genericEvidence


def iterNamedSkillMeta(namedDir: str):
    for filePath in sorted(glob.glob(os.path.join(namedDir, "**/*.md"), recursive=True)):
        try:
            with open(filePath, encoding="utf-8") as f:
                content = f.read()
            if not content.startswith("---"):
                continue
            parts = content.split("---")
            if len(parts) < 3:
                continue
            meta = yaml.safe_load(parts[1])
            if meta and "id" in meta:
                yield filePath, meta
        except Exception as e:
            print(f"Error parsing file {filePath}: {e}")


def dedupeKey(entry: dict[str, Any]) -> tuple[str | None, str, str]:
    normalizedType = normalizeEvidenceType(entry.get("type", "self-attestation"))
    scope = entry.get("scope") or entry.get("layer") or entry.get("attributionScope") or "standalone"
    return (entry.get("source"), normalizedType, str(scope))


def normalizeEvidenceRow(
    entry: dict[str, Any], *, skipLiveStars: bool = False
) -> dict[str, Any]:
    row = dict(entry)
    originalType = row.get("type", "self-attestation")
    normalizedType = normalizeEvidenceType(originalType)
    row["normalized_type"] = normalizedType
    if str(originalType).strip() != normalizedType:
        row["original_type"] = originalType
    # Keep the author-supplied type field for traceability when it was an alias;
    # consumers should use normalized_type for routing.
    row.setdefault("type", originalType)

    src = row.get("source")
    repoPath = parseRepoPath(src)
    if repoPath and not skipLiveStars:
        liveStars = getLiveStars(repoPath)
        if liveStars is not None:
            row["stars_verified"] = liveStars
    return row


def compileNamedSkills(
    namedDir: str,
    genericEvidence: dict[str, list[dict[str, Any]]],
    *,
    skipLiveStars: bool = False,
) -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    for _, meta in iterNamedSkillMeta(namedDir):
        skillMeta = dict(meta)
        ownEvidence = skillMeta.get("evidence") or []
        inherited = genericEvidence.get(skillMeta.get("genericSkillRef")) or []

        seen: set[tuple[str | None, str, str]] = set()
        mergedEvidence: list[dict[str, Any]] = []
        for entry in [*ownEvidence, *inherited]:
            try:
                key = dedupeKey(entry)
            except ValueError as e:
                print(f"Warning: skipping {skillMeta.get('id')} evidence row: {e}")
                continue
            if key in seen:
                continue
            seen.add(key)
            mergedEvidence.append(normalizeEvidenceRow(entry, skipLiveStars=skipLiveStars))

        skillMeta["compiled_evidence"] = mergedEvidence
        skills.append(skillMeta)
    return skills


def groupSkillsByTier(skills: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    tierGroups = {
        "6★": [],
        "5★": [],
        "4★": [],
        "3★": [],
        "2★": [],
        "1★": [],
        "provisional": [],
    }
    for skill in skills:
        level = skill.get("level", "2★")
        tierGroups[level if level in tierGroups else "provisional"].append(skill)
    return tierGroups


def groupSkillsByEvidenceType(skills: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {evType: [] for evType in CANONICAL_EVIDENCE_TYPES}
    for skill in skills:
        rowsByType: dict[str, list[dict[str, Any]]] = {evType: [] for evType in CANONICAL_EVIDENCE_TYPES}
        for row in skill.get("compiled_evidence") or []:
            rowsByType[row["normalized_type"]].append(row)
        for evType, rows in rowsByType.items():
            if rows:
                typeSkill = dict(skill)
                typeSkill["compiled_evidence"] = rows
                groups[evType].append(typeSkill)
    return groups


def writeEvidenceRows(f, evList: list[dict[str, Any]]) -> None:
    for i, row in enumerate(evList, 1):
        normalizedType = row.get("normalized_type") or normalizeEvidenceType(row.get("type", "self-attestation"))
        f.write(f"#### E{i}: `{normalizedType}`\n")
        if row.get("original_type"):
            f.write(f"- **Original Type:** `{row.get('original_type')}`\n")
        f.write(f"- **Source:** [{row.get('source')}]({row.get('source')})\n")
        f.write(f"- **Date:** {row.get('date', 'unknown')}\n")
        if row.get("scope") or row.get("layer") or row.get("attributionScope"):
            scope = row.get("scope") or row.get("layer") or row.get("attributionScope")
            f.write(f"- **Scope:** {scope}\n")
        if "stars_verified" in row:
            f.write(f"- **Verified Stars:** {row['stars_verified']:,} stars\n")
        elif row.get("trustNumber"):
            f.write(f"- **Trust Metric:** {row.get('trustNumber')}\n")
        f.write(f"- **Description:** {row.get('notes', 'No notes.')}\n\n")


def writeSkillBlock(f, skill: dict[str, Any]) -> None:
    f.write(f"## Skill: `{skill['id']}`\n")
    f.write(f"- **Name:** {skill.get('name')}\n")
    f.write(f"- **Contributor:** `{skill.get('contributor')}`\n")

    ghLink = skill.get("links", {}).get("github")
    if ghLink:
        repoPath = parseRepoPath(ghLink)
        if repoPath:
            liveStars = STARS_CACHE.get(repoPath)
            if liveStars is not None:
                f.write(
                    f"- **Primary GitHub Repository:** [{ghLink}]({ghLink}) "
                    f"({liveStars:,} stars)\n"
                )
            else:
                f.write(f"- **Primary GitHub Repository:** [{ghLink}]({ghLink})\n")

    f.write("\n### Evidence Rows:\n\n")
    writeEvidenceRows(f, skill.get("compiled_evidence") or [])
    f.write("---\n\n")


def writeByTypePartitions(byTypeDirectory: str, typeGroups: dict[str, list[dict[str, Any]]]) -> None:
    os.makedirs(byTypeDirectory, exist_ok=True)
    for path in iterTypePartitionPaths(byTypeDirectory):
        evType = os.path.splitext(os.path.basename(path))[0]
        skills = sorted(typeGroups.get(evType, []), key=lambda s: s["id"])
        print(f"Writing {path} with {len(skills)} skills...")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Evidence Sources: {evType}\n\n")
            f.write(
                "This type-first partition lists raw evidence rows whose "
                f"canonical evidence type is `{evType}`. Legacy tier files may "
                "also exist as coexistence artifacts, but they are not the "
                "semantic routing key.\n\n"
            )
            for skill in skills:
                writeSkillBlock(f, skill)


def writeLegacyTierPartitions(outputDir: str, tierGroups: dict[str, list[dict[str, Any]]]) -> None:
    os.makedirs(outputDir, exist_ok=True)
    for level, skills in tierGroups.items():
        if not skills:
            continue
        filename = f"tier_{level.replace('★', '')}.md"
        outputPath = os.path.join(outputDir, filename)
        print(f"Writing legacy {outputPath} with {len(skills)} skills...")
        with open(outputPath, "w", encoding="utf-8") as f:
            f.write(f"# Evidence Sources: Tier {level}\n\n")
            f.write(
                f"This coexistence file lists raw evidence sources for named skills rated at {level}. "
                "The primary semantic partitions are evidence/by-type/<type>.md.\n\n"
            )
            for skill in sorted(skills, key=lambda s: s["id"]):
                if skill.get("compiled_evidence"):
                    writeSkillBlock(f, skill)


def writeSourceReport(
    reportPath: str,
    *,
    reportDate: str,
    skills: list[dict[str, Any]],
    typeGroups: dict[str, list[dict[str, Any]]],
    byTypeDirectory: str,
    legacyTiersEnabled: bool,
) -> None:
    os.makedirs(os.path.dirname(reportPath) or ".", exist_ok=True)
    print(f"Writing master report to {reportPath}...")
    with open(reportPath, "w", encoding="utf-8") as f:
        f.write("# Consolidated Trust Methodology Source Report\n\n")
        f.write(f"**Date:** {reportDate}  \n")
        f.write("**Subject:** Type-first dump of verified evidence sources across Gaia named skills\n\n")
        f.write(
            "The evidence lake is now type-first: `evidence/by-type/<canonical-evidence-type>.md` "
            "is the primary working set. Legacy `tier_*.md` files may still be emitted for "
            "coexistence, but they are no longer the semantic routing key.\n\n"
        )

        f.write("## 1. Summary Metrics\n\n")
        totalSources = sum(len(skill.get("compiled_evidence") or []) for skill in skills)
        skillsWithSources = sum(1 for skill in skills if skill.get("compiled_evidence"))
        f.write(f"- **Total Skills Evaluated:** {len(skills)}\n")
        f.write(f"- **Total Skills with Active Sources:** {skillsWithSources}\n")
        f.write(f"- **Total Evidence Entries Dumped:** {totalSources}\n\n")

        for evType in CANONICAL_EVIDENCE_TYPES:
            typeSkills = typeGroups.get(evType, [])
            typeRows = sum(len(skill.get("compiled_evidence") or []) for skill in typeSkills)
            f.write(
                f"- **{evType}:** {len(typeSkills)} skills with sources "
                f"({typeRows} raw source entries)\n"
            )

        f.write("\n## 2. Type-First Directory Index\n\n")
        f.write("All raw sources are partitioned by canonical evidence type for fast consumption:\n")
        for evType in CANONICAL_EVIDENCE_TYPES:
            absPath = os.path.abspath(typeOutputPath(byTypeDirectory, evType))
            f.write(f"- [{evType} Source Dump](file://{absPath})\n")

        f.write("\n## 3. Coexistence Note\n\n")
        if legacyTiersEnabled:
            f.write(
                "Legacy `tier_*.md` files were also emitted for compatibility. Treat them as "
                "coexistence artifacts only; route new pipeline work through `evidence/by-type/`.\n"
            )
        else:
            f.write("Legacy `tier_*.md` emission was disabled for this run.\n")


def buildSourceDump(
    *,
    namedSkillsJson: str,
    gaiaJson: str,
    namedDir: str,
    outputDir: str,
    byTypeDirectory: str,
    reportPath: str,
    skipLiveStars: bool = False,
    noLegacyTiers: bool = False,
    reportDate: str | None = None,
) -> dict[str, Any] | None:
    gaiaJson = resolveGaiaJson(gaiaJson)
    namedSkillsJson = resolveNamedSkillsJson(namedSkillsJson)
    print(f"Loading registry files from {namedSkillsJson} and {gaiaJson}...")
    try:
        loadJson(namedSkillsJson)  # kept as a preflight; named markdown is source of rows.
    except Exception as e:
        print(f"Error loading {namedSkillsJson}: {e}")
        return None
    try:
        gaiaData = loadJson(gaiaJson)
    except Exception as e:
        print(f"Error loading {gaiaJson}: {e}")
        return None

    print(f"Parsing named skills in {namedDir} and compiling evidence...")
    skills = compileNamedSkills(
        namedDir,
        loadGenericEvidence(gaiaData),
        skipLiveStars=skipLiveStars,
    )
    typeGroups = groupSkillsByEvidenceType(skills)
    tierGroups = groupSkillsByTier(skills)

    os.makedirs(outputDir, exist_ok=True)
    writeByTypePartitions(byTypeDirectory, typeGroups)
    if not noLegacyTiers:
        writeLegacyTierPartitions(outputDir, tierGroups)
    writeSourceReport(
        reportPath,
        reportDate=reportDate or date.today().isoformat(),
        skills=skills,
        typeGroups=typeGroups,
        byTypeDirectory=byTypeDirectory,
        legacyTiersEnabled=not noLegacyTiers,
    )
    return {"skills": skills, "typeGroups": typeGroups, "tierGroups": tierGroups}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate source dump files.")
    parser.add_argument("--named-skills-json", dest="namedSkillsJson", default="registry/named-skills.json", help="Path to named-skills.json")
    parser.add_argument("--gaia-json", dest="gaiaJson", default="registry/gaia.json", help="Path to gaia.json")
    parser.add_argument("--named-dir", dest="namedDir", default="registry/named", help="Directory containing named skill Markdown files")
    parser.add_argument("--output-dir", dest="outputDir", default="evidence", help="Output directory for evidence dumps")
    parser.add_argument("--by-type-dir", dest="byTypeDir", default=None, help="Directory for type-first dumps (default: <output-dir>/by-type)")
    parser.add_argument("--report-path", dest="reportPath", default=None, help="Path to the generated source report")
    parser.add_argument("--no-legacy-tiers", action="store_true", help="Do not emit coexistence tier_*.md dumps")
    parser.add_argument("--skip-live-stars", action="store_true", help="Skip GitHub live star lookups for deterministic runs")
    parser.add_argument("--report-date", default=None, help="Date string to write into the source report")

    args = parser.parse_args()
    outputDir = args.outputDir
    byTypeDirectory = args.byTypeDir or defaultByTypeDir(outputDir)
    reportPath = args.reportPath or os.path.join(outputDir, f"source_report_{date.today().strftime('%Y_%m_%d')}.md")

    buildSourceDump(
        namedSkillsJson=args.namedSkillsJson,
        gaiaJson=args.gaiaJson,
        namedDir=args.namedDir,
        outputDir=outputDir,
        byTypeDirectory=byTypeDirectory,
        reportPath=reportPath,
        skipLiveStars=args.skip_live_stars,
        noLegacyTiers=args.no_legacy_tiers,
        reportDate=args.report_date,
    )


if __name__ == "__main__":
    main()
