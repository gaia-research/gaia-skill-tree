import datetime
import json
import os

from gaia_cli.registry import registry_graph_path
from gaia_cli.treeManager import user_tree_path, load_tree, save_tree

def get_utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def append_skill_tree_event(username, skill_id, action, details, registry_path="."):
    tree_data = load_tree(username, registry_path)
    if not tree_data:
        return

    if "timeline" not in tree_data:
        tree_data["timeline"] = []

    event = {
        "timestamp": get_utc_now_iso(),
        "action": action,
        "skillId": skill_id,
    }
    if details:
        event["details"] = details

    tree_data["timeline"].append(event)
    save_tree(username, tree_data, registry_path)

def append_skill_event(skill_id, action, contributor, details, registry_path="."):
    graph_path = registry_graph_path(registry_path)
    if not os.path.exists(graph_path):
        return

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    skill_found = False
    for skill in graph_data.get("skills", []):
        if skill.get("id") == skill_id:
            if "timeline" not in skill:
                skill["timeline"] = []

            event = {
                "timestamp": get_utc_now_iso(),
                "action": action,
            }
            if contributor:
                event["contributor"] = contributor
            if details:
                event["details"] = details

            skill["timeline"].append(event)
            skill_found = True
            break

    if skill_found:
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
