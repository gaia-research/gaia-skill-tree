import json
with open("registry/gaia.json") as f:
    graph = json.load(f)
print("Is mbtiongson1/gaia-audit in gaia.json skills?", any(s["id"] == "mbtiongson1/gaia-audit" for s in graph["skills"]))
