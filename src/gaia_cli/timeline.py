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

def _parse_md(path):
    import yaml
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content
    _, frontmatter, body = content.split("---", 2)
    return (yaml.safe_load(frontmatter) or {}), body

def _write_md(path, meta, body) -> None:
    import yaml
    path.write_text(
        "---\n" + yaml.dump(meta, sort_keys=False, allow_unicode=True) + "---" + body,
        encoding="utf-8",
    )

def append_skill_event(skill_id, action, contributor, details, registry_path="."):
    from gaia_cli.registry import registry_nodes_dir, named_skills_dir
    nodes_dir = Path(registry_nodes_dir(registry_path))
    
    node_file = None
    # 1. Search in generic nodes (JSON)
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("id") == skill_id:
                    node_file = p
                    break
            except json.JSONDecodeError:
                continue
    
    if node_file:
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
        return

    # 2. Search in named skills (Markdown)
    named_base = Path(named_skills_dir(registry_path))
    target_file = None
    if "/" in skill_id:
        # Direct path guess
        guess = named_base / f"{skill_id}.md"
        if guess.exists():
            target_file = guess
    
    if not target_file:
        # Fallback recursive search
        for p in named_base.glob("**/*.md"):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple ID match in frontmatter
                if f"id: {skill_id}" in content or f'id: "{skill_id}"' in content:
                    target_file = p
                    break
    
    if target_file:
        meta, body = _parse_md(target_file)
        
        if "timeline" not in meta:
            meta["timeline"] = []
            
        event = {
            "timestamp": get_utc_now_iso(),
            "action": action,
        }
        if contributor:
            event["contributor"] = contributor
        if details:
            event["details"] = details
            
        meta["timeline"].append(event)
        _write_md(target_file, meta, body)

def append_registry_event(action, contributor, details, registry_path="."):
    """Appends an event to the global registry timeline (if we decide to have one)."""
    # For now, we mainly care about skill-specific timelines, 
    # but we could have a registry-wide timeline file.
    pass
