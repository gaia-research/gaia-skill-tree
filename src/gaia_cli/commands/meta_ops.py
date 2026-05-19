"""Meta review operations for the Gaia CLI."""

import json
import os
import sys
import datetime
import subprocess
from pathlib import Path
from typing import Any

from gaia_cli.registry import (
    registry_graph_path,
    named_skills_index_path,
    registry_nodes_dir,
    named_skills_dir,
)
from gaia_cli.scanner import load_config
from gaia_cli.timeline import append_skill_event

def _get_contributor():
    config = load_config() or {}
    return config.get("gaiaUser") or config.get("username") or "unknown"

def meta_list_command(args):
    registry_path = args.registry
    graph_path = registry_graph_path(registry_path)
    named_index_path = named_skills_index_path(registry_path)

    results = []

    if getattr(args, "generic", False) or not getattr(args, "named", False):
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
            for skill in graph_data.get("skills", []):
                item = {"id": skill["id"], "name": skill.get("name"), "kind": "generic"}
                if getattr(args, "description", False):
                    item["description"] = skill.get("description")
                if getattr(args, "extra", None):
                    for field in args.extra:
                        if field in skill:
                            item[field] = skill[field]
                results.append(item)

    if getattr(args, "named", False):
        if os.path.exists(named_index_path):
            with open(named_index_path, "r", encoding="utf-8") as f:
                named_data = json.load(f)
            for bucket_id, bucket_items in named_data.get("buckets", {}).items():
                for skill in bucket_items:
                    item = {"id": skill["id"], "name": skill.get("name"), "kind": "named", "genericSkillRef": bucket_id}
                    if getattr(args, "description", False):
                        item["description"] = skill.get("description")
                    if getattr(args, "extra", None):
                        for field in args.extra:
                            if field in skill:
                                item[field] = skill[field]
                    results.append(item)

    if not results:
        print("No skills found.")
        return

    # Output formatting
    if getattr(args, "json", False):
        print(json.dumps(results, indent=2))
    else:
        for item in results:
            kind_prefix = "[G] " if item["kind"] == "generic" else "[N] "
            line = f"{kind_prefix}/{item['id']} - {item.get('name')}"
            if "description" in item:
                line += f"\n    {item['description']}"
            if getattr(args, "extra", None):
                for field in args.extra:
                    if field in item and field not in ("id", "name", "kind", "description"):
                        line += f"\n    {field}: {item[field]}"
            print(line)

def _update_named_skill_ref(md_path: Path, old_ref: str, new_ref: str):
    """Update genericSkillRef in a named skill markdown file."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple regex-less replacement for now, being careful about keys
    old_line = f"genericSkillRef: {old_ref}"
    old_line_quoted = f"genericSkillRef: \"{old_ref}\""
    old_line_single_quoted = f"genericSkillRef: '{old_ref}'"
    
    new_line = f"genericSkillRef: \"{new_ref}\""
    
    changed = False
    if old_line in content:
        content = content.replace(old_line, new_line)
        changed = True
    elif old_line_quoted in content:
        content = content.replace(old_line_quoted, new_line)
        changed = True
    elif old_line_single_quoted in content:
        content = content.replace(old_line_single_quoted, new_line)
        changed = True
        
    if changed:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

def meta_merge_command(args):
    registry_path = args.registry
    target_id = args.target.lstrip("/")
    sources = [s.lstrip("/") for s in args.sources]

    if target_id in sources:
        print(f"Error: Target skill '{target_id}' cannot be one of the source skills.")
        sys.exit(1)

    if "/" in target_id:
        # Named skill merging
        named_dir = Path(named_skills_dir(registry_path))
        target_file = None
        for p in named_dir.glob("**/*.md"):
            with open(p, "r", encoding="utf-8") as f:
                try:
                    content = f.read()
                    if f'id: "{target_id}"' in content or f"id: '{target_id}'" in content or f"id: {target_id}" in content:
                        target_file = p
                        break
                except Exception:
                    continue
        
        if not target_file:
            print(f"Error: Target named skill '{target_id}' not found.")
            sys.exit(1)

        source_files = []
        for source_id in sources:
            for p in named_dir.glob("**/*.md"):
                with open(p, "r", encoding="utf-8") as f:
                    try:
                        content = f.read()
                        if f'id: "{source_id}"' in content or f"id: '{source_id}'" in content or f"id: {source_id}" in content:
                            source_files.append(p)
                            break
                    except Exception:
                        continue
        
        for sf in source_files:
            print(f"Merging content from {sf} into {target_file} (manual review recommended)")
            sf.unlink()
        
        append_skill_event(target_id, "merge", _get_contributor(), f"Merged named skills {', '.join(sources)} into {target_id}", registry_path=registry_path)
    else:
        # Generic skill merging
        nodes_dir = Path(registry_nodes_dir(registry_path))
        target_file = None
        target_data = None
        
        for p in nodes_dir.glob("**/*.json"):
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if data.get("id") == target_id:
                        target_file = p
                        target_data = data
                        break
                except json.JSONDecodeError:
                    continue
        
        if not target_file:
            print(f"Error: Target skill '{target_id}' not found in registry nodes.")
            sys.exit(1)

        merged_evidence = target_data.get("evidence", []) or []
        merged_prereqs = set(target_data.get("prerequisites", []) or [])
        merged_derivatives = set(target_data.get("derivatives", []) or [])
        merged_agents = set(target_data.get("knownAgents", []) or [])
        
        source_files = []
        for source_id in sources:
            source_file = None
            for p in nodes_dir.glob("**/*.json"):
                with open(p, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        if data.get("id") == source_id:
                            source_file = p
                            source_data = data
                            break
                    except json.JSONDecodeError:
                        continue
            
            if not source_file:
                print(f"Warning: Source skill '{source_id}' not found. Skipping.")
                continue
            
            source_files.append(source_file)
            merged_evidence.extend(source_data.get("evidence", []) or [])
            merged_prereqs.update(source_data.get("prerequisites", []) or [])
            merged_derivatives.update(source_data.get("derivatives", []) or [])
            merged_agents.update(source_data.get("knownAgents", []) or [])

        to_remove = set(sources) | {target_id}
        merged_prereqs -= to_remove
        merged_derivatives -= to_remove

        target_data["evidence"] = merged_evidence
        target_data["prerequisites"] = sorted(list(merged_prereqs))
        target_data["derivatives"] = sorted(list(merged_derivatives))
        target_data["knownAgents"] = sorted(list(merged_agents))
        target_data["updatedAt"] = datetime.date.today().isoformat()

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(target_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        for sf in source_files:
            sf.unlink()
            print(f"Deleted source skill file: {sf}")

        for p in nodes_dir.glob("**/*.json"):
            if p == target_file:
                continue
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue
            
            changed = False
            if "prerequisites" in data:
                new_prereqs = []
                for pr in data["prerequisites"]:
                    if pr in sources:
                        if target_id not in new_prereqs and target_id != data["id"]:
                            new_prereqs.append(target_id)
                            changed = True
                    else:
                        new_prereqs.append(pr)
                data["prerequisites"] = new_prereqs
                
            if "derivatives" in data:
                new_derivatives = []
                for dr in data["derivatives"]:
                    if dr in sources:
                        if target_id not in new_derivatives and target_id != data["id"]:
                            new_derivatives.append(target_id)
                            changed = True
                    else:
                        new_derivatives.append(dr)
                data["derivatives"] = new_derivatives
                
            if changed:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                print(f"Updated references in {p}")

        # Update named skill references
        named_dir = Path(named_skills_dir(registry_path))
        for p in named_dir.glob("**/*.md"):
            for source_id in sources:
                if _update_named_skill_ref(p, source_id, target_id):
                    print(f"Updated genericSkillRef in {p}")

        append_skill_event(target_id, "merge", _get_contributor(), f"Merged {', '.join(sources)} into {target_id}", registry_path=registry_path)

    print("Running scripts/assemble_gaia.py...")
    subprocess.run([sys.executable, "scripts/assemble_gaia.py", "--registry", registry_path], check=True)
    print("Running scripts/generateNamedIndex.py...")
    subprocess.run([sys.executable, "scripts/generateNamedIndex.py", "--graph", registry_graph_path(registry_path), "--named-dir", named_skills_dir(registry_path), "--out", named_skills_index_path(registry_path)], check=True)

    print(f"Successfully merged skills into '{target_id}'.")

def meta_split_command(args):
    registry_path = args.registry
    source_id = args.source.lstrip("/")
    targets = [t.lstrip("/") for t in args.targets]

    nodes_dir = Path(registry_nodes_dir(registry_path))
    source_file = None
    source_data = None
    
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("id") == source_id:
                    source_file = p
                    source_data = data
                    break
            except json.JSONDecodeError:
                continue
    
    if not source_file:
        print(f"Error: Source skill '{source_id}' not found.")
        sys.exit(1)

    for target_id in targets:
        target_data = source_data.copy()
        target_data["id"] = target_id
        target_data["name"] = target_id.replace("-", " ").title()
        target_data["createdAt"] = datetime.date.today().isoformat()
        target_data["updatedAt"] = datetime.date.today().isoformat()
        
        target_file = source_file.parent / f"{target_id}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(target_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Created split target: {target_file}")

    # Update references in other files to the FIRST target
    first_target = targets[0]
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        
        changed = False
        if "prerequisites" in data:
            new_prereqs = []
            for pr in data["prerequisites"]:
                if pr == source_id:
                    if first_target not in new_prereqs and first_target != data["id"]:
                        new_prereqs.append(first_target)
                        changed = True
                else:
                    new_prereqs.append(pr)
            data["prerequisites"] = new_prereqs
            
        if "derivatives" in data:
            new_derivatives = []
            for dr in data["derivatives"]:
                if dr == source_id:
                    if first_target not in new_derivatives and first_target != data["id"]:
                        new_derivatives.append(first_target)
                        changed = True
                else:
                    new_derivatives.append(dr)
            data["derivatives"] = new_derivatives
            
        if changed:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"Updated references in {p} to {first_target}")

    # Update named skill references
    named_dir = Path(named_skills_dir(registry_path))
    for p in named_dir.glob("**/*.md"):
        if _update_named_skill_ref(p, source_id, first_target):
            print(f"Updated genericSkillRef in {p} to {first_target}")

    source_file.unlink()
    print(f"Deleted source skill file: {source_file}")
    append_skill_event(first_target, "split", _get_contributor(), f"Split {source_id} into {', '.join(targets)}", registry_path=registry_path)

    print("Running scripts/assemble_gaia.py...")
    subprocess.run([sys.executable, "scripts/assemble_gaia.py", "--registry", registry_path], check=True)
    print("Running scripts/generateNamedIndex.py...")
    subprocess.run([sys.executable, "scripts/generateNamedIndex.py", "--graph", registry_graph_path(registry_path), "--named-dir", named_skills_dir(registry_path), "--out", named_skills_index_path(registry_path)], check=True)

def meta_add_command(args):
    registry_path = args.registry
    skill_name = args.name
    skill_id = args.id or skill_name.lower().replace(" ", "-")
    
    if getattr(args, "named", False):
        contributor = getattr(args, "contributor", "gaiabot")
        dest_dir = Path(named_skills_dir(registry_path)) / contributor
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{skill_id}.md"
        
        content = f"""---
id: "{contributor}/{skill_id}"
name: "{skill_name}"
contributor: "{contributor}"
origin: false
genericSkillRef: "{getattr(args, 'generic_ref', 'unknown')}"
status: "named"
level: "{getattr(args, 'level', '2★')}"
description: "{getattr(args, 'description', '')}"
createdAt: "{datetime.date.today().isoformat()}"
updatedAt: "{datetime.date.today().isoformat()}"
---

## Installation
Add installation instructions here.
"""
        with open(dest_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created named skill: {dest_file}")
    else:
        skill_type = getattr(args, "type", "basic")
        dest_dir = Path(registry_nodes_dir(registry_path)) / skill_type
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{skill_id}.json"
        
        data = {
            "id": skill_id,
            "name": skill_name,
            "type": skill_type,
            "level": getattr(args, "level", "1★"),
            "rarity": getattr(args, "rarity", "common"),
            "description": getattr(args, "description", ""),
            "prerequisites": [],
            "derivatives": [],
            "evidence": [],
            "status": "provisional",
            "createdAt": datetime.date.today().isoformat(),
            "updatedAt": datetime.date.today().isoformat(),
            "version": "0.1.0"
        }
        
        # Add any extra fields passed
        if getattr(args, "extra_fields", None):
            try:
                extra = json.loads(args.extra_fields)
                data.update(extra)
            except json.JSONDecodeError:
                print("Warning: Could not parse extra-fields JSON. Skipping.")

        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Created generic skill: {dest_file}")
        append_skill_event(skill_id, "add", _get_contributor(), f"Added generic skill {skill_id}", registry_path=registry_path)

    print("Running scripts/assemble_gaia.py...")
    subprocess.run([sys.executable, "scripts/assemble_gaia.py", "--registry", registry_path], check=True)
    print("Running scripts/generateNamedIndex.py...")
    subprocess.run([sys.executable, "scripts/generateNamedIndex.py", "--graph", registry_graph_path(registry_path), "--named-dir", named_skills_dir(registry_path), "--out", named_skills_index_path(registry_path)], check=True)

def meta_evidence_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    
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
        print(f"Error: Skill '{skill_id}' not found.")
        sys.exit(1)

    with open(node_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    evidence = {
        "class": getattr(args, "evidence_class", "C"),
        "source": args.source,
        "evaluator": getattr(args, "evaluator", None) or _get_contributor(),
        "date": getattr(args, "date", None) or datetime.date.today().isoformat(),
    }
    if getattr(args, "notes", None):
        evidence["notes"] = args.notes

    if "evidence" not in data:
        data["evidence"] = []
    
    data["evidence"].append(evidence)
    data["updatedAt"] = datetime.date.today().isoformat()

    with open(node_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    print(f"Added evidence to skill: {skill_id}")
    append_skill_event(skill_id, "evidence_added", _get_contributor(), f"Added {evidence['class']} evidence from {evidence['source']}", registry_path=registry_path)

    print("Running scripts/assemble_gaia.py...")
    subprocess.run([sys.executable, "scripts/assemble_gaia.py", "--registry", registry_path], check=True)
    print("Running scripts/generateNamedIndex.py...")
    subprocess.run([sys.executable, "scripts/generateNamedIndex.py", "--graph", registry_graph_path(registry_path), "--named-dir", named_skills_dir(registry_path), "--out", named_skills_index_path(registry_path)], check=True)
