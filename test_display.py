import json
with open("registry/gaia.json") as f:
    graph_data = json.load(f)

skill_map = {s["id"]: s for s in graph_data.get("skills", [])}

custom_nodes = set()
scanned_nodes = set()

with open(".gaia/custom_state.json") as f:
    cstate = json.load(f)

for csk in cstate.get("customSkills", []):
    m_type = csk.get("match_type")
    mapped_to = csk.get("mapped_to")
    node_id = mapped_to if (mapped_to and mapped_to in skill_map) else csk["id"]
    
    scanned_nodes.add(node_id)

unlocked_ids = set()
for cid in scanned_nodes:
    unlocked_ids.add(cid)

display_ids = set()
queue = list(scanned_nodes)
visited = set()
while queue:
    curr = queue.pop(0)
    if curr in visited:
        continue
    visited.add(curr)
    display_ids.add(curr)
    for prereq in skill_map.get(curr, {}).get("prerequisites", []):
        queue.append(prereq)

display_ids = {sid for sid in display_ids if sid in unlocked_ids or sid in scanned_nodes}

all_prereqs = set()
for sid in display_ids:
    for p in skill_map.get(sid, {}).get("prerequisites", []):
        all_prereqs.add(p)

roots = [sid for sid in display_ids if sid not in all_prereqs]
print("Roots:", roots)
print("display_ids has garrytan/gstack?", "garrytan/gstack" in display_ids)
