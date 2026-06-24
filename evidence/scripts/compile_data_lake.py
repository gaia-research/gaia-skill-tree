import os
import argparse

def parseTierFiles(lakeDir, skillsData):
    # Parse tier_1.md to tier_6.md from data lake folder
    for tierNum in range(1, 7):
        filePath = os.path.join(lakeDir, f"tier_{tierNum}.md")
        if not os.path.exists(filePath):
            continue
        
        content = open(filePath, "r").read()
        skillBlocks = content.split("## Skill: ")
        for block in skillBlocks[1:]:
            lines = block.split("\n")
            skillId = lines[0].strip().replace("`", "")
            
            if skillId not in skillsData:
                skillsData[skillId] = {
                    "id": skillId,
                    "tier": f"{tierNum}★",
                    "evidenceRows": [],
                    "benchmarks": [],
                    "reviews": [],
                    "papers": [],
                    "blogs": [],
                    "videos": [],
                    "verifications": []
                }
            
            for line in lines[1:]:
                if line.startswith("- **Name:**"):
                    skillsData[skillId]["name"] = line.split("- **Name:**")[1].strip()
                elif line.startswith("- **Contributor:**"):
                    skillsData[skillId]["contributor"] = line.split("- **Contributor:**")[1].strip().replace("`", "")
                elif line.startswith("- **Primary GitHub Repository:**"):
                    skillsData[skillId]["primaryRepo"] = line.split("- **Primary GitHub Repository:**")[1].strip()

            evSplit = block.split("#### E")
            for evBlock in evSplit[1:]:
                evLines = evBlock.split("\n")
                evHeader = evLines[0].strip()
                evContent = []
                for evLine in evLines[1:]:
                    if evLine.strip() == "---" or evLine.startswith("## Skill:"):
                        break
                    evContent.append(evLine)
                skillsData[skillId]["evidenceRows"].append({
                    "header": f"E{evHeader}",
                    "content": "\n".join(evContent).strip()
                })

def parseCollectorFiles(collectorsDir, skillsData):
    benchPath = os.path.join(collectorsDir, "technical", "benchmark_results.md")
    if os.path.exists(benchPath):
        content = open(benchPath, "r").read()
        blocks = content.split("### ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["benchmarks"].append(block)

    reviewPath = os.path.join(collectorsDir, "technical", "peer_reviews_audits.md")
    if os.path.exists(reviewPath):
        content = open(reviewPath, "r").read()
        blocks = content.split("## ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["reviews"].append(block)

    academicPath = os.path.join(collectorsDir, "technical", "academic_papers.md")
    if os.path.exists(academicPath):
        content = open(academicPath, "r").read()
        blocks = content.split("### ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["papers"].append(block)

    blogPath = os.path.join(collectorsDir, "social", "blogs_newsletters.md")
    if os.path.exists(blogPath):
        content = open(blogPath, "r").read()
        blocks = content.split("### ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip().replace("`", "")
            for skillId in skillsData.keys():
                if skillId in title or title in skillId:
                    skillsData[skillId]["blogs"].append(block)

    youtubePath = os.path.join(collectorsDir, "social", "youtube_showcases.md")
    if os.path.exists(youtubePath):
        content = open(youtubePath, "r").read()
        blocks = content.split("## ")
        for block in blocks[1:]:
            lines = block.split("\n")
            title = lines[0].strip()
            for skillId in skillsData.keys():
                contributor = skillsData[skillId]["contributor"]
                if contributor in title:
                    skillsData[skillId]["videos"].append(block)

    verifPath = os.path.join(collectorsDir, "verification", "verification_report.md")
    if os.path.exists(verifPath):
        content = open(verifPath, "r").read()
        for skillId in skillsData.keys():
            matches = []
            for line in content.split("\n"):
                if skillId in line:
                    matches.append(line)
            if matches:
                skillsData[skillId]["verifications"].extend(matches)

def writeUnifiedLake(outputPath, skillsData):
    out = open(outputPath, "w")
    out.write("# Gaia Trust Methodology: Unified Evidence Data Lake\n\n")
    out.write("This unified data lake compiles all evidence dumps (Tiers 1★ to 6★) and specialized collector findings into a single source of truth indexed by skill ID.\n\n")
    
    out.write("## Table of Contents\n\n")
    def getTierWeight(tierStr):
        return int(tierStr.replace("★", ""))
    
    sortedSkills = sorted(skillsData.values(), key=lambda x: (-getTierWeight(x["tier"]), x["id"]))
    
    for s in sortedSkills:
        out.write(f"- [{s['id']} (Tier {s['tier']})](#skill-{s['id'].replace('/', '').replace('.', '')})\n")
    out.write("\n---\n\n")
    
    for s in sortedSkills:
        cleanAnchor = s['id'].replace('/', '').replace('.', '')
        out.write(f"## Skill: <a name=\"skill-{cleanAnchor}\"></a>`{s['id']}`\n\n")
        out.write(f"- **Name:** {s.get('name', 'N/A')}\n")
        out.write(f"- **Contributor:** `{s.get('contributor', 'N/A')}`\n")
        out.write(f"- **Tier:** {s['tier']}\n")
        if "primaryRepo" in s:
            out.write(f"- **Primary Repository:** {s['primaryRepo']}\n")
        out.write("\n")
        
        out.write("### Base Evidence Rows\n\n")
        if s["evidenceRows"]:
            for ev in s["evidenceRows"]:
                out.write(f"#### {ev['header']}\n{ev['content']}\n\n")
        else:
            out.write("*No base evidence rows.*\n\n")
            
        if s["benchmarks"]:
            out.write("### Benchmark Evaluations\n\n")
            for b in s["benchmarks"]:
                lines = b.split("\n")
                out.write("\n".join(lines[1:]).strip() + "\n\n")
                
        if s["reviews"]:
            out.write("### Peer Reviews & Audits\n\n")
            for r in s["reviews"]:
                lines = r.split("\n")
                out.write("\n".join(lines[1:]).strip() + "\n\n")
                
        if s["papers"]:
            out.write("### Academic Papers & Preprints\n\n")
            for p in s["papers"]:
                lines = p.split("\n")
                out.write("\n".join(lines[1:]).strip() + "\n\n")
                
        if s["blogs"]:
            out.write("### Blog & Newsletter Signals\n\n")
            for bl in s["blogs"]:
                lines = bl.split("\n")
                out.write("\n".join(lines[1:]).strip() + "\n\n")
                
        if s["videos"]:
            out.write("### YouTube Showcase Videos\n\n")
            for v in s["videos"]:
                lines = v.split("\n")
                out.write("\n".join(lines[1:]).strip() + "\n\n")

        if s["verifications"]:
            out.write("### Verification Audits\n\n")
            out.write("| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |\n")
            out.write("| :--- | :--- | :--- | :--- |\n")
            for ver in s["verifications"]:
                out.write(ver + "\n")
            out.write("\n")
            
        out.write("---\n\n")
        
    out.close()

def main():
    parser = argparse.ArgumentParser(description="Compile unified evidence data lake.")
    parser.add_argument("--sources", dest="sourcesDir", default="evidence", help="Sources directory path")
    parser.add_argument("--collectors", dest="collectorsDir", default="evidence/collectors", help="Collectors directory path")
    parser.add_argument("--lake", dest="lakeDir", default="evidence", help="Data lake directory path")
    
    args = parser.parse_args()
    
    sourcesDir = args.sourcesDir
    collectorsDir = args.collectorsDir
    lakeDir = args.lakeDir
    
    os.makedirs(lakeDir, exist_ok=True)
    
    skillsData = {}
    print(f"Parsing tier dumps from {lakeDir}...")
    parseTierFiles(lakeDir, skillsData)
    print(f"Parsing collector files from {collectorsDir}...")
    parseCollectorFiles(collectorsDir, skillsData)
    
    outputPath = os.path.join(lakeDir, "unified_evidence_lake.md")
    print(f"Writing unified data lake to {outputPath}...")
    writeUnifiedLake(outputPath, skillsData)
    print("Data lake compilation complete.")

if __name__ == "__main__":
    main()
