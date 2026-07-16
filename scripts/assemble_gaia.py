import json
import os
import datetime

def getMaxLevelsForNamed(registryRoot):
    import glob
    import yaml
    namedDir = os.path.join(registryRoot, "registry", "named")
    maxLevels = {}
    if not os.path.isdir(namedDir):
        return maxLevels

    pattern = os.path.join(namedDir, "**", "*.md")
    for fp in glob.glob(pattern, recursive=True):
        if fp.endswith("index.json"):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
            if not text.startswith("---"):
                continue
            parts = text.split("---", 2)
            if len(parts) < 3:
                continue
            fm = yaml.safe_load(parts[1]) or {}
            ref = fm.get("genericSkillRef")
            levelStr = fm.get("level", "")
            if ref and levelStr:
                lvlNum = int("".join(c for c in levelStr if c.isdigit()))
                if ref not in maxLevels or lvlNum > maxLevels[ref]:
                    maxLevels[ref] = lvlNum
        except Exception:
            continue
    return maxLevels

def _read_version(root_path) -> str:
    import os
    pyproject = os.path.join(root_path, "pyproject.toml")
    if os.path.exists(pyproject):
        with open(pyproject, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("version = "):
                    return line.split("=", 1)[1].strip().strip('"')
    return "3.2.2"

def assemble(registry_root="."):
    import sys
    from pathlib import Path
    repoRoot = Path(registry_root).resolve()
    sys.path.insert(0, str(repoRoot))
    sys.path.insert(0, str(repoRoot / "src"))
    from gaia_cli.timeline import get_utc_now_iso

    registry_dir = os.path.join(registry_root, "registry")
    nodes_dir = os.path.join(registry_dir, "nodes")
    gaia_json_path = os.path.join(registry_dir, "gaia.json")
    
    # Load metadata from gaia.json if it exists, otherwise use defaults
    if os.path.exists(gaia_json_path):
        with open(gaia_json_path, "r", encoding="utf-8") as f:
            old_data = json.load(f)
    else:
        old_data = {}

    meta_schema_path = os.path.join(registry_dir, "schema", "meta.json")
    if os.path.exists(meta_schema_path):
        with open(meta_schema_path, "r", encoding="utf-8") as f:
            meta_src = json.load(f)
        meta_mapped = {
            "typeLabels": meta_src["types"]["labels"],
            "levelLabels": meta_src["levels"]["labels"],
            "levelColors": meta_src["levels"]["colors"],
            "typeColors": meta_src["types"]["colors"],
            "typeSymbols": meta_src["types"]["symbols"],
            "demeritLabels": meta_src["demerits"]["labels"],
            "metaEpochs": meta_src.get("metaEpochs", {})
        }
    else:
        meta_mapped = old_data.get("meta", {})

    assembled_data = {
        "$schema": "./schema/skill.schema.json",
        "version": old_data.get("version") or _read_version(registry_root),
        "generatedAt": get_utc_now_iso(),
        "meta": meta_mapped,
        "skills": [],
        "edges": []
    }

    maxLevels = getMaxLevelsForNamed(registry_root)

    # Collect skills
    all_skills = []
    if os.path.isdir(nodes_dir):
        for root, dirs, files in os.walk(nodes_dir):
            for file in files:
                if file.endswith(".json"):
                    filePath = os.path.join(root, file)
                    with open(filePath, "r", encoding="utf-8") as f:
                        skill = json.load(f)

                    # Auto-demote unique skill if max level is < 4
                    if skill.get("type") == "unique":
                        maxLvl = maxLevels.get(skill["id"], 0)
                        if maxLvl < 4:
                            print(f"Auto-demoting unique skill '{skill['id']}' to extra (max named level is {maxLvl}★)")
                            timestamp = get_utc_now_iso()
                            
                            # Add timeline entry
                            timelineEntry = {
                                "timestamp": timestamp,
                                "action": "type_change",
                                "contributor": "system",
                                "details": f"Auto-demoted unique skill to extra (max named level is {maxLvl}★)",
                                "previousValue": "unique",
                                "newValue": "extra"
                            }
                            if "timeline" not in skill:
                                skill["timeline"] = []
                            skill["timeline"].append(timelineEntry)
                            skill["type"] = "extra"
                            skill["updatedAt"] = timestamp.split("T")[0]
                            
                            with open(filePath, "w", encoding="utf-8") as f:
                                json.dump(skill, f, indent=2, ensure_ascii=False)
                                f.write("\n")

                    all_skills.append(skill)

    # Sort skills by ID for deterministic output
    all_skills.sort(key=lambda x: x["id"])
    assembled_data["skills"] = all_skills

    # Generate edges for backward compatibility
    edges = []
    for skill in all_skills:
        target_id = skill["id"]
        prereqs = skill.get("prerequisites", [])
        for source_id in prereqs:
            edges.append({
                "sourceSkillId": source_id,
                "targetSkillId": target_id,
                "edgeType": "prerequisite"
            })
    
    # Sort edges for determinism
    edges.sort(key=lambda x: (x["sourceSkillId"], x["targetSkillId"]))
    assembled_data["edges"] = edges

    os.makedirs(os.path.dirname(gaia_json_path), exist_ok=True)
    with open(gaia_json_path, "w", encoding="utf-8") as f:
        json.dump(assembled_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    print(f"Assembled {len(all_skills)} skills and {len(edges)} edges into {gaia_json_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default=".")
    args = parser.parse_args()
    assemble(args.registry)
