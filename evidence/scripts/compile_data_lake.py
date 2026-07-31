from __future__ import annotations

import argparse
import os
from typing import Any

from evidence_type_partitions import CANONICAL_EVIDENCE_TYPES, iterTypePartitionPaths


def newSkillRecord(skillId: str) -> dict[str, Any]:
    return {
        "id": skillId,
        "evidenceTypes": [],
        "evidenceRows": [],
        "benchmarks": [],
        "reviews": [],
        "papers": [],
        "blogs": [],
        "videos": [],
        "verifications": [],
    }


def ensureSkill(skillsData: dict[str, dict[str, Any]], skillId: str) -> dict[str, Any]:
    if skillId not in skillsData:
        skillsData[skillId] = newSkillRecord(skillId)
    return skillsData[skillId]


def parseEvidenceRows(block: str, evType: str | None = None) -> list[dict[str, str]]:
    rows = []
    for evBlock in block.split("#### E")[1:]:
        evLines = evBlock.split("\n")
        evHeader = evLines[0].strip()
        evContent = []
        for evLine in evLines[1:]:
            if evLine.strip() == "---" or evLine.startswith("## Skill:"):
                break
            evContent.append(evLine)
        row = {
            "header": f"E{evHeader}",
            "content": "\n".join(evContent).strip(),
        }
        if evType:
            row["type"] = evType
        rows.append(row)
    return rows


def parseSkillBlockMetadata(skill: dict[str, Any], lines: list[str]) -> None:
    for line in lines:
        if line.startswith("- **Name:**"):
            skill["name"] = line.split("- **Name:**", 1)[1].strip()
        elif line.startswith("- **Contributor:**"):
            skill["contributor"] = line.split("- **Contributor:**", 1)[1].strip().replace("`", "")
        elif line.startswith("- **Primary GitHub Repository:**"):
            skill["primaryRepo"] = line.split("- **Primary GitHub Repository:**", 1)[1].strip()


def parseByTypeFiles(byTypeDir: str, skillsData: dict[str, dict[str, Any]]) -> int:
    """Parse type-first partitions from ``byTypeDir`` into ``skillsData``.

    Returns the number of partition files consumed. The primary key is evidence
    type; tier files are intentionally ignored here.
    """
    parsedFiles = 0
    for filePath in iterTypePartitionPaths(byTypeDir):
        if not os.path.exists(filePath):
            continue
        parsedFiles += 1
        evType = os.path.splitext(os.path.basename(filePath))[0]
        with open(filePath, "r", encoding="utf-8") as f:
            content = f.read()
        skillBlocks = content.split("## Skill: ")
        for block in skillBlocks[1:]:
            lines = block.split("\n")
            skillId = lines[0].strip().replace("`", "")
            skill = ensureSkill(skillsData, skillId)
            if evType not in skill["evidenceTypes"]:
                skill["evidenceTypes"].append(evType)
            parseSkillBlockMetadata(skill, lines[1:])
            skill["evidenceRows"].extend(parseEvidenceRows(block, evType=evType))
    return parsedFiles


def parseTierFiles(lakeDir: str, skillsData: dict[str, dict[str, Any]]) -> int:
    # Legacy fallback only: parse tier_1.md to tier_6.md from data lake folder.
    parsedFiles = 0
    for tierNum in range(1, 7):
        filePath = os.path.join(lakeDir, f"tier_{tierNum}.md")
        if not os.path.exists(filePath):
            continue
        parsedFiles += 1
        with open(filePath, "r", encoding="utf-8") as f:
            content = f.read()
        skillBlocks = content.split("## Skill: ")
        for block in skillBlocks[1:]:
            lines = block.split("\n")
            skillId = lines[0].strip().replace("`", "")
            skill = ensureSkill(skillsData, skillId)
            skill["tier"] = f"{tierNum}★"
            parseSkillBlockMetadata(skill, lines[1:])
            skill["evidenceRows"].extend(parseEvidenceRows(block))
    return parsedFiles


def parseCollectorFiles(collectorsDir: str, skillsData: dict[str, dict[str, Any]]) -> None:
    benchPath = os.path.join(collectorsDir, "technical", "benchmark_results.md")
    if os.path.exists(benchPath):
        content = open(benchPath, "r", encoding="utf-8").read()
        blocks = content.split("### ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["benchmarks"].append(block)

    reviewPath = os.path.join(collectorsDir, "technical", "peer_reviews_audits.md")
    if os.path.exists(reviewPath):
        content = open(reviewPath, "r", encoding="utf-8").read()
        blocks = content.split("## ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["reviews"].append(block)

    academicPath = os.path.join(collectorsDir, "technical", "academic_papers.md")
    if os.path.exists(academicPath):
        content = open(academicPath, "r", encoding="utf-8").read()
        blocks = content.split("### ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["papers"].append(block)

    blogPath = os.path.join(collectorsDir, "social", "blogs_newsletters.md")
    if os.path.exists(blogPath):
        content = open(blogPath, "r", encoding="utf-8").read()
        blocks = content.split("### ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["blogs"].append(block)

    youtubePath = os.path.join(collectorsDir, "social", "youtube_showcases.md")
    if os.path.exists(youtubePath):
        content = open(youtubePath, "r", encoding="utf-8").read()
        blocks = content.split("## ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip()
            for skillId in skillsData.keys():
                contributor = skillsData[skillId].get("contributor", "")
                if contributor and contributor in title:
                    skillsData[skillId]["videos"].append(block)

    verifPath = os.path.join(collectorsDir, "verification", "verification_report.md")
    if os.path.exists(verifPath):
        content = open(verifPath, "r", encoding="utf-8").read()
        for skillId in skillsData.keys():
            matches = []
            for line in content.split("\n"):
                if skillId in line:
                    matches.append(line)
            if matches:
                skillsData[skillId]["verifications"].extend(matches)


def canonicalTypeWeight(skill: dict[str, Any]) -> int:
    types = skill.get("evidenceTypes") or []
    if not types:
        return len(CANONICAL_EVIDENCE_TYPES)
    return min(CANONICAL_EVIDENCE_TYPES.index(t) for t in types if t in CANONICAL_EVIDENCE_TYPES)


def writeUnifiedLake(outputPath: str, skillsData: dict[str, dict[str, Any]]) -> None:
    with open(outputPath, "w", encoding="utf-8") as out:
        out.write("# Gaia Trust Methodology: Unified Evidence Data Lake\n\n")
        out.write(
            "This unified data lake compiles type-first evidence partitions "
            "(`evidence/by-type/<canonical-evidence-type>.md`) into a single source "
            "of truth indexed by skill ID. Legacy `tier_*.md` files are coexistence "
            "artifacts only and are ignored unless the legacy fallback flag is used.\n\n"
        )

        out.write("## Table of Contents\n\n")
        sortedSkills = sorted(skillsData.values(), key=lambda x: (canonicalTypeWeight(x), x["id"]))

        for skill in sortedSkills:
            types = ", ".join(skill.get("evidenceTypes") or ["legacy-tier-fallback"])
            out.write(f"- [{skill['id']} ({types})](#skill-{skill['id'].replace('/', '').replace('.', '')})\n")
        out.write("\n---\n\n")

        for skill in sortedSkills:
            cleanAnchor = skill["id"].replace("/", "").replace(".", "")
            out.write(f"## Skill: <a name=\"skill-{cleanAnchor}\"></a>`{skill['id']}`\n\n")
            out.write(f"- **Name:** {skill.get('name', 'N/A')}\n")
            out.write(f"- **Contributor:** `{skill.get('contributor', 'N/A')}`\n")
            out.write(f"- **Evidence Types:** {', '.join(skill.get('evidenceTypes') or ['legacy-tier-fallback'])}\n")
            if "tier" in skill:
                out.write(f"- **Legacy Tier:** {skill['tier']}\n")
            if "primaryRepo" in skill:
                out.write(f"- **Primary Repository:** {skill['primaryRepo']}\n")
            out.write("\n")

            out.write("### Type-First Evidence Rows\n\n")
            if skill["evidenceRows"]:
                for ev in skill["evidenceRows"]:
                    typeLabel = f" ({ev['type']})" if ev.get("type") else ""
                    out.write(f"#### {ev['header']}{typeLabel}\n{ev['content']}\n\n")
            else:
                out.write("*No base evidence rows.*\n\n")

            if skill["benchmarks"]:
                out.write("### Benchmark Evaluations\n\n")
                for b in skill["benchmarks"]:
                    lines = b.split("\n")
                    out.write("\n".join(lines[1:]).strip() + "\n\n")

            if skill["reviews"]:
                out.write("### Peer Reviews & Audits\n\n")
                for r in skill["reviews"]:
                    lines = r.split("\n")
                    out.write("\n".join(lines[1:]).strip() + "\n\n")

            if skill["papers"]:
                out.write("### Academic Papers & Preprints\n\n")
                for p in skill["papers"]:
                    lines = p.split("\n")
                    out.write("\n".join(lines[1:]).strip() + "\n\n")

            if skill["blogs"]:
                out.write("### Blog & Newsletter Signals\n\n")
                for bl in skill["blogs"]:
                    lines = bl.split("\n")
                    out.write("\n".join(lines[1:]).strip() + "\n\n")

            if skill["videos"]:
                out.write("### YouTube Showcase Videos\n\n")
                for v in skill["videos"]:
                    lines = v.split("\n")
                    out.write("\n".join(lines[1:]).strip() + "\n\n")

            if skill["verifications"]:
                out.write("### Verification Audits\n\n")
                out.write("| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |\n")
                out.write("| :--- | :--- | :--- | :--- |\n")
                for ver in skill["verifications"]:
                    out.write(ver + "\n")
                out.write("\n")

            out.write("---\n\n")


def compileDataLake(
    *,
    sourcesDir: str,
    collectorsDir: str,
    lakeDir: str,
    legacyTierFallback: bool = False,
    includeCollectors: bool = False,
) -> dict[str, dict[str, Any]]:
    os.makedirs(lakeDir, exist_ok=True)
    skillsData: dict[str, dict[str, Any]] = {}

    if os.path.isdir(sourcesDir):
        print(f"Parsing type-first evidence partitions from {sourcesDir}...")
        parsedByType = parseByTypeFiles(sourcesDir, skillsData)
        if parsedByType == 0:
            print(f"No canonical by-type partition files found in {sourcesDir}.")
    else:
        print(
            f"Type-first evidence directory not found: {sourcesDir}. "
            "Run generate_source_dump.py to materialize evidence/by-type, "
            "or pass --legacy-tier-fallback to consume tier_*.md coexistence artifacts."
        )
        parsedByType = 0

    if parsedByType == 0 and legacyTierFallback:
        print(f"Parsing legacy tier dumps from {lakeDir}...")
        parseTierFiles(lakeDir, skillsData)
    elif legacyTierFallback:
        print("By-type partitions were found; legacy tier fallback not needed.")

    if includeCollectors:
        print(f"Parsing collector files from {collectorsDir}...")
        parseCollectorFiles(collectorsDir, skillsData)
    else:
        print("Skipping collector files by default; by-type partitions are the primary working set.")

    outputPath = os.path.join(lakeDir, "unified_evidence_lake.md")
    print(f"Writing unified data lake to {outputPath}...")
    writeUnifiedLake(outputPath, skillsData)
    print("Data lake compilation complete.")
    return skillsData


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile unified evidence data lake.")
    parser.add_argument("--sources", dest="sourcesDir", default="evidence/by-type", help="Type-first sources directory path")
    parser.add_argument("--collectors", dest="collectorsDir", default="evidence/collectors", help="Collectors directory path")
    parser.add_argument("--lake", dest="lakeDir", default="evidence", help="Data lake output directory path")
    parser.add_argument("--legacy-tier-fallback", action="store_true", help="Use legacy tier_*.md files only when by-type partitions are absent")
    parser.add_argument("--include-collectors", action="store_true", help="Also parse collector channels after by-type partitions")

    args = parser.parse_args()
    compileDataLake(
        sourcesDir=args.sourcesDir,
        collectorsDir=args.collectorsDir,
        lakeDir=args.lakeDir,
        legacyTierFallback=args.legacy_tier_fallback,
        includeCollectors=args.include_collectors,
    )


if __name__ == "__main__":
    main()
