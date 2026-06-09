import json
with open("registry/gaia.json") as f:
    graph = json.load(f)
for e in graph.get("edges", []):
    if e["targetSkillId"] == "founder-mode-orchestration":
        print("Prereq of founder-mode:", e["sourceSkillId"])
    if e["sourceSkillId"] == "founder-mode-orchestration":
        print("founder-mode is Prereq of:", e["targetSkillId"])
