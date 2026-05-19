import datetime
import json
import os
from pathlib import Path

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
    from gaia_cli.registry import registry_nodes_dir
    nodes_dir = Path(registry_nodes_dir(registry_path))
    
    node_file = None
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("id") == skill_id:
                    node_file = p
                    break
            except json.JSONDecodeError:
                continue
    
    if not node_file:
        return

    with open(node_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "timeline" not in data:
        data["timeline"] = []

    event = {
        "timestamp": get_utc_now_iso(),
        "action": action,
    }
    if contributor:
        event["contributor"] = contributor
    if details:
        event["details"] = details

    data["timeline"].append(event)
    
    with open(node_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def append_registry_event(action, contributor, details, registry_path="."):
    """Appends an event to the global registry timeline (if we decide to have one)."""
    # For now, we mainly care about skill-specific timelines, 
    # but we could have a registry-wide timeline file.
    pass
