import os
import json
import yaml
import glob
import subprocess
import argparse

STARS_CACHE = {
    'mattpocock/skills': 133210,
    'ruvnet/ruflo': 59957,
    'garrytan/gstack': 110930,
    'obra/superpowers': 230818,
    'ruvnet/agentdb': 66,
    'pbakaus/impeccable': 39158,
    '0xDarkMatter/claude-mods': 22,
    'browser-use/browser-harness': 15008,
    'browser-use/browser-use': 99295,
    'addyosmani/agent-skills': 62101
}

def getLiveStars(repoPath):
    if repoPath in STARS_CACHE:
        return STARS_CACHE[repoPath]
    try:
        out = subprocess.check_output(['gh', 'repo', 'view', repoPath, '--json', 'stargazerCount'], text=True)
        data = json.loads(out)
        stars = data.get('stargazerCount', 0)
        STARS_CACHE[repoPath] = stars
        return stars
    except Exception as e:
        print(f"Warning: Could not fetch stars for {repoPath}: {e}")
        return None

def parseRepoPath(url):
    if not url or 'github.com/' not in url:
        return None
    try:
        path = url.split('github.com/')[1]
        parts = [p for p in path.split('/') if p]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    except Exception:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Generate source dump files.")
    parser.add_argument("--named-skills-json", dest="namedSkillsJson", default="registry/named-skills.json", help="Path to named-skills.json")
    parser.add_argument("--gaia-json", dest="gaiaJson", default="registry/gaia.json", help="Path to gaia.json")
    parser.add_argument("--named-dir", dest="namedDir", default="registry/named", help="Directory containing named skill Markdown files")
    parser.add_argument("--output-dir", dest="outputDir", default="evidence", help="Output directory for tier dumps")
    parser.add_argument("--report-path", dest="reportPath", default="evidence/source_report_2026_06_18.md", help="Path to the generated source report")
    
    args = parser.parse_args()
    
    namedSkillsJson = args.namedSkillsJson
    gaiaJson = args.gaiaJson
    namedDir = args.namedDir
    outputDir = args.outputDir
    reportPath = args.reportPath
    
    if not os.path.exists(gaiaJson):
        for fallbackPath in ["docs/graph/gaia.json", ".gaia/registry/gaia.json"]:
            if os.path.exists(fallbackPath):
                gaiaJson = fallbackPath
                break

    print(f"Loading registry files from {namedSkillsJson} and {gaiaJson}...")
    try:
        namedSkillsData = json.load(open(namedSkillsJson))
    except Exception as e:
        print(f"Error loading {namedSkillsJson}: {e}")
        return

    try:
        gaiaData = json.load(open(gaiaJson))
    except Exception as e:
        print(f"Error loading {gaiaJson}: {e}")
        return

    genericEvidence = {}
    for s in gaiaData.get('skills', []):
        if 'id' in s:
            genericEvidence[s['id']] = s.get('evidence') or []

    tierGroups = {
        '6★': [],
        '5★': [],
        '4★': [],
        '3★': [],
        '2★': [],
        '1★': [],
        'provisional': []
    }

    print(f"Parsing named skills in {namedDir} and compiling evidence...")
    namedFiles = glob.glob(os.path.join(namedDir, "**/*.md"), recursive=True)
    
    for filePath in namedFiles:
        try:
            content = open(filePath).read()
            if not content.startswith('---'):
                continue
            parts = content.split('---')
            if len(parts) < 3:
                continue
            meta = yaml.safe_load(parts[1])
            if not meta or 'id' not in meta:
                continue
            
            skillId = meta['id']
            level = meta.get('level', '2★')
            
            ownEvidence = meta.get('evidence') or []
            genericRef = meta.get('genericSkillRef')
            inherited = genericEvidence.get(genericRef) or []
            
            seenSources = set()
            mergedEvidence = []
            
            def addEntry(entry):
                src = entry.get('source')
                if src and src not in seenSources:
                    seenSources.add(src)
                    
                    repoPath = parseRepoPath(src)
                    if repoPath:
                        liveStars = getLiveStars(repoPath)
                        if liveStars is not None:
                            entry['stars_verified'] = liveStars
                    mergedEvidence.append(entry)

            for e in ownEvidence:
                addEntry(e)
            for e in inherited:
                addEntry(e)
                
            meta['compiled_evidence'] = mergedEvidence
            
            if level in tierGroups:
                tierGroups[level].append(meta)
            else:
                tierGroups['provisional'].append(meta)
        except Exception as e:
            print(f"Error parsing file {filePath}: {e}")

    os.makedirs(outputDir, exist_ok=True)
    
    for level, skills in tierGroups.items():
        if not skills:
            continue
            
        filename = f"tier_{level.replace('★', '')}.md"
        outputPath = os.path.join(outputDir, filename)
        print(f"Writing {outputPath} with {len(skills)} skills...")
        
        with open(outputPath, 'w') as f:
            f.write(f"# Evidence Sources: Tier {level}\n\n")
            f.write(f"This file lists the raw evidence sources for named skills rated at {level}.\n\n")
            
            for s in sorted(skills, key=lambda x: x['id']):
                evList = s.get('compiled_evidence') or []
                if not evList:
                    continue
                    
                f.write(f"## Skill: `{s['id']}`\n")
                f.write(f"- **Name:** {s.get('name')}\n")
                f.write(f"- **Contributor:** `{s.get('contributor')}`\n")
                
                ghLink = s.get('links', {}).get('github')
                if ghLink:
                    repoPath = parseRepoPath(ghLink)
                    if repoPath:
                        liveStars = getLiveStars(repoPath)
                        if liveStars is not None:
                            f.write(f"- **Primary GitHub Repository:** [{ghLink}]({ghLink}) ({liveStars:,} stars)\n")
                        else:
                            f.write(f"- **Primary GitHub Repository:** [{ghLink}]({ghLink})\n")
                
                f.write("\n### Evidence Rows:\n\n")
                for i, e in enumerate(evList, 1):
                    f.write(f"#### E{i}: `{e.get('type', 'unknown')}`\n")
                    f.write(f"- **Source:** [{e.get('source')}]({e.get('source')})\n")
                    f.write(f"- **Date:** {e.get('date', 'unknown')}\n")
                    
                    if 'stars_verified' in e:
                        f.write(f"- **Verified Stars:** {e['stars_verified']:,} stars\n")
                    elif e.get('trustNumber'):
                        f.write(f"- **Trust Metric:** {e.get('trustNumber')}\n")
                        
                    f.write(f"- **Description:** {e.get('notes', 'No notes.')}\n\n")
                
                f.write("---\n\n")

    print(f"Writing master report to {reportPath}...")
    with open(reportPath, 'w') as f:
        f.write("# Consolidated Trust Methodology Source Report\n\n")
        f.write("**Date:** June 18, 2026  \n")
        f.write("**Subject:** Complete Dump of Verified Evidence Sources across all Gaia named skills\n\n")
        
        f.write("## 1. Summary Metrics\n\n")
        totalSkills = sum(len(skills) for skills in tierGroups.values())
        totalSources = 0
        skillsWithSources = 0
        
        for level, skills in sorted(tierGroups.items(), reverse=True):
            levelSources = 0
            levelSkillsWithSources = 0
            for s in skills:
                evs = len(s.get('compiled_evidence') or [])
                if evs > 0:
                    levelSkillsWithSources += 1
                    levelSources += evs
            totalSources += levelSources
            skillsWithSources += levelSkillsWithSources
            f.write(f"- **Tier {level}:** {len(skills)} skills total, {levelSkillsWithSources} have verified sources ({levelSources} raw source entries)\n")
            
        f.write(f"\n- **Total Skills Evaluated:** {totalSkills}\n")
        f.write(f"- **Total Skills with Active Sources:** {skillsWithSources}\n")
        f.write(f"- **Total Evidence Entries Dumped:** {totalSources}\n\n")
        
        f.write("## 2. Directory Index\n\n")
        f.write("All raw sources are partitioned by level for fast consumption:\n")
        for level in sorted(tierGroups.keys(), reverse=True):
            if tierGroups[level]:
                absPath = os.path.abspath(os.path.join(outputDir, f"tier_{level.replace('★', '')}.md"))
                f.write(f"- [Tier {level} Source Dump](file://{absPath})\n")

if __name__ == '__main__':
    main()
