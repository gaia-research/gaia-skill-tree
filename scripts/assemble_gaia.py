import json
import os
import datetime

def assemble(registry_root="."):
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
            "demeritLabels": meta_src["demerits"]["labels"]
        }
    else:
        meta_mapped = old_data.get("meta", {})

    assembled_data = {
        "$schema": "./schema/skill.schema.json",
        "version": old_data.get("version", "3.2.2"),
        "generatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "meta": meta_mapped,
        "skills": [],
        "edges": []
    }

    # Collect skills
    all_skills = []
    if os.path.isdir(nodes_dir):
        for root, dirs, files in os.walk(nodes_dir):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        skill = json.load(f)
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
