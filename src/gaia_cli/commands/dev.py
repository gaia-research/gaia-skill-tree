"""Meta review operations for the Gaia CLI."""

import copy
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

def _run_docs_build(registry_path) -> None:
    cmd = [sys.executable, "-m", "gaia_cli"]
    if registry_path:
        cmd += ["--registry", str(registry_path)]
    cmd += ["docs", "build"]
    subprocess.run(cmd, check=True)

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
                if getattr(args, "level", False):
                    item["level"] = skill.get("level")
                if getattr(args, "evidence", False):
                    item["evidence_count"] = len(skill.get("evidence", []))
                
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
                    if getattr(args, "level", False):
                        item["level"] = skill.get("level")
                    if getattr(args, "contributor", False):
                        item["contributor"] = skill.get("contributor")
                    
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
            if "level" in item:
                line += f" ({item['level']})"
            if "contributor" in item:
                line += f" by {item['contributor']}"
            if "evidence_count" in item:
                line += f" [{item['evidence_count']} evidence]"
            
            if "description" in item:
                line += f"\n    {item['description']}"
            
            if getattr(args, "extra", None):
                for field in args.extra:
                    if field in item and field not in ("id", "name", "kind", "description"):
                        line += f"\n    {field}: {item[field]}"
            print(line)

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

def _find_named_file(named_dir, skill_id):
    for p in named_dir.glob("**/*.md"):
        meta, _ = _parse_md(p)
        if meta.get("id") == skill_id:
            return p
    return None

def _update_named_skill_ref(md_path: Path, old_ref: str, new_ref: str):
    """Update genericSkillRef in a named skill markdown file."""
    meta, body = _parse_md(md_path)
    if meta.get("genericSkillRef") == old_ref:
        meta["genericSkillRef"] = new_ref
        _write_md(md_path, meta, body)
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
        target_file = _find_named_file(named_dir, target_id)

        if not target_file:
            print(f"Error: Target named skill '{target_id}' not found.")
            sys.exit(1)

        target_meta, target_body = _parse_md(target_file)

        for source_id in sources:
            source_file = _find_named_file(named_dir, source_id)

            if not source_file:
                print(f"Warning: Source named skill '{source_id}' not found. Skipping.")
                continue

            source_meta, source_body = _parse_md(source_file)
            
            # Merge metadata
            if "links" in source_meta:
                target_meta.setdefault("links", {}).update(source_meta["links"])
            if "tags" in source_meta:
                target_meta["tags"] = list(set(target_meta.get("tags", [])) | set(source_meta["tags"]))
            if "knownAgents" in source_meta:
                target_meta["knownAgents"] = list(set(target_meta.get("knownAgents", [])) | set(source_meta["knownAgents"]))
            
            # Append body
            target_body += f"\n\n--- Merged from {source_id} ---\n\n" + source_body
            
            source_file.unlink()
            print(f"Merged and deleted source file: {source_file}")

        target_meta["updatedAt"] = datetime.date.today().isoformat()
        
        with open(target_file, "w", encoding="utf-8") as f:
            import yaml
            f.write("---\n")
            yaml.dump(target_meta, f, sort_keys=False, allow_unicode=True)
            f.write("---\n")
            f.write(target_body)

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
            if data.get("prerequisites"):
                new_prereqs = [
                    target_id if pr in sources and target_id != data["id"] else pr
                    for pr in data["prerequisites"]
                    if pr not in sources or target_id != data["id"]
                ]
                seen = set()
                new_prereqs = [x for x in new_prereqs if not (x in seen or seen.add(x))]
                if new_prereqs != data["prerequisites"]:
                    data["prerequisites"] = new_prereqs
                    changed = True

            if data.get("derivatives"):
                new_derivatives = [
                    target_id if dr in sources and target_id != data["id"] else dr
                    for dr in data["derivatives"]
                    if dr not in sources or target_id != data["id"]
                ]
                seen = set()
                new_derivatives = [x for x in new_derivatives if not (x in seen or seen.add(x))]
                if new_derivatives != data["derivatives"]:
                    data["derivatives"] = new_derivatives
                    changed = True
                
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

    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)

    print(f"Successfully merged skills into '{target_id}'.")

def meta_rename_command(args):
    registry_path = args.registry
    old_id = args.old_id.lstrip("/")
    new_id = args.new_id.lstrip("/")

    nodes_dir = Path(registry_nodes_dir(registry_path))
    old_file = None
    skill_data = None
    
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("id") == old_id:
                    old_file = p
                    skill_data = data
                    break
            except json.JSONDecodeError:
                continue
    
    if not old_file:
        print(f"Error: Skill '{old_id}' not found.")
        sys.exit(1)

    # Rename the file and update ID
    new_file = old_file.parent / f"{new_id}.json"
    if new_file.exists():
        print(f"Error: '{new_id}' already exists on disk at {new_file}. Rename aborted.")
        sys.exit(1)
    for p in nodes_dir.glob("**/*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("id") == new_id:
                print(f"Error: Skill with id '{new_id}' already exists in registry.")
                sys.exit(1)
        except Exception:
            continue
    skill_data["id"] = new_id
    skill_data["updatedAt"] = datetime.date.today().isoformat()

    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(skill_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    old_file.unlink()
    print(f"Renamed {old_file} to {new_file}")

    # Update references in all other nodes
    for p in nodes_dir.glob("**/*.json"):
        if p == new_file:
            continue
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        
        changed = False
        if "prerequisites" in data:
            if old_id in data["prerequisites"]:
                data["prerequisites"] = [new_id if pr == old_id else pr for pr in data["prerequisites"]]
                changed = True
        
        if "derivatives" in data:
            if old_id in data["derivatives"]:
                data["derivatives"] = [new_id if dr == old_id else dr for dr in data["derivatives"]]
                changed = True
        
        if changed:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"Updated references in {p}")

    # Update named skill references
    named_dir = Path(named_skills_dir(registry_path))
    for p in named_dir.glob("**/*.md"):
        if _update_named_skill_ref(p, old_id, new_id):
            print(f"Updated genericSkillRef in {p}")

    append_skill_event(new_id, "rename", _get_contributor(), f"Renamed from {old_id} to {new_id}", registry_path=registry_path)
    
    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
    print(f"Successfully renamed '{old_id}' to '{new_id}'.")

def meta_calibrate_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    level = args.level
    
    # Validation
    ALLOWED_LEVELS = ["0★", "1★", "2★", "3★", "4★", "5★", "6★"]
    if level not in ALLOWED_LEVELS:
        print(f"Error: Level must be one of: {', '.join(ALLOWED_LEVELS)}")
        sys.exit(1)

    nodes_dir = Path(registry_nodes_dir(registry_path))
    node_file = None
    skill_data = None
    
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("id") == skill_id:
                    node_file = p
                    skill_data = data
                    break
            except json.JSONDecodeError:
                continue
    
    if not node_file:
        print(f"Error: Skill '{skill_id}' not found.")
        sys.exit(1)

    old_level = skill_data.get("level", "0★")
    skill_data["level"] = level
    skill_data["updatedAt"] = datetime.date.today().isoformat()

    with open(node_file, "w", encoding="utf-8") as f:
        json.dump(skill_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    ALLOWED_LEVELS = ["0★", "1★", "2★", "3★", "4★", "5★", "6★"]
    level_num = ALLOWED_LEVELS.index(level)
    old_level_num = ALLOWED_LEVELS.index(old_level) if old_level in ALLOWED_LEVELS else 0
    action = "rank_up" if level_num > old_level_num else "demote"

    append_skill_event(skill_id, action, _get_contributor(), f"Calibrated level from {old_level} to {level}", registry_path=registry_path)
    
    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
    print(f"Successfully calibrated '{skill_id}' to {level}.")

def meta_audit_command(args):
    """Registry linter for maintenance issues."""
    registry_path = args.registry
    nodes_dir = Path(registry_nodes_dir(registry_path))
    threshold = getattr(args, "level", 0)
    
    issues = []
    
    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
            
            skill_id = data.get("id")
            level_str = data.get("level") or "0★"
            try:
                level = int(level_str[0])
            except (ValueError, IndexError):
                issues.append(f"[P0] {skill_id}: Malformed level {level_str!r}")
                continue
            
            if threshold and level < threshold:
                continue

            evidence = data.get("evidence", [])
            best_class = "D"
            if evidence:
                classes = [e.get("class", "C") for e in evidence]
                if "A" in classes: best_class = "A"
                elif "B" in classes: best_class = "B"
                elif "C" in classes: best_class = "C"
            
            # Evidence Floor Checks (from GEMINI.md)
            # 2★ needs Tier C
            if level >= 2 and not evidence:
                issues.append(f"[P1] {skill_id}: Level {level_str} but has NO evidence.")
            
            # 3★ needs Tier B
            if level == 3 and best_class == "C":
                issues.append(f"[P1] {skill_id}: Level {level_str} but only has Class C evidence (needs B).")
            
            # 4★+ needs Tier B/A
            if level >= 4 and best_class not in ["A", "B"]:
                issues.append(f"[P0] {skill_id}: Level {level_str} but only has Class {best_class} evidence (needs A/B).")

            # Orphan check
            if not data.get("prerequisites") and data.get("type") != "basic" and data.get("type") != "unique":
                issues.append(f"[P2] {skill_id}: Orphaned {data.get('type')} skill (no prerequisites).")

            # Missing description
            if not data.get("description") or len(data.get("description")) < 10:
                issues.append(f"[P3] {skill_id}: Missing or too short description.")

    if not issues:
        print("✅ No registry maintenance issues found.")
    else:
        print(f"Found {len(issues)} potential issues:")
        for issue in sorted(issues):
            print(f"  {issue}")

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
        target_file = source_file.parent / f"{target_id}.json"
        if target_file.exists():
            print(f"Error: split target '{target_id}' already exists on disk.")
            sys.exit(1)
        for p in nodes_dir.glob("**/*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("id") == target_id:
                    print(f"Error: split target '{target_id}' already exists in registry.")
                    sys.exit(1)
            except Exception:
                continue
        target_data = copy.deepcopy(source_data)
        target_data["id"] = target_id
        target_data["name"] = target_id.replace("-", " ").title()
        target_data["evidence"] = []
        target_data["timeline"] = []
        target_data["createdAt"] = datetime.date.today().isoformat()
        target_data["updatedAt"] = datetime.date.today().isoformat()
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

    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)

def meta_add_command(args):
    registry_path = args.registry
    skill_name = args.name
    skill_id = args.id or skill_name.lower().replace(" ", "-")
    
    if getattr(args, "named", False):
        contributor = getattr(args, "contributor", "gaiabot")
        dest_dir = Path(named_skills_dir(registry_path)) / contributor
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{skill_id}.md"

        desc = (getattr(args, "description", None) or "").strip()
        if len(desc) < 10:
            print("Error: --description must be at least 10 characters (schema requirement).")
            sys.exit(1)

        meta = {
            "id": f"{contributor}/{skill_id}",
            "name": skill_name,
            "contributor": contributor,
            "origin": False,
            "genericSkillRef": getattr(args, "generic_ref", "unknown"),
            "status": "named",
            "level": getattr(args, "level", "2★"),
            "description": desc,
            "createdAt": datetime.date.today().isoformat(),
            "updatedAt": datetime.date.today().isoformat(),
        }
        body = "\n\n## Installation\nAdd installation instructions here.\n"
        _write_md(dest_file, meta, body)
        print(f"Created named skill: {dest_file}")
        append_skill_event(f"{contributor}/{skill_id}", "add", _get_contributor(), f"Added named skill {contributor}/{skill_id}", registry_path=registry_path)
    else:
        skill_type = getattr(args, "type", "basic")
        dest_dir = Path(registry_nodes_dir(registry_path)) / skill_type
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{skill_id}.json"

        desc = (getattr(args, "description", None) or "").strip()
        if len(desc) < 10:
            print("Error: --description must be at least 10 characters (schema requirement).")
            sys.exit(1)

        data = {
            "id": skill_id,
            "name": skill_name,
            "type": skill_type,
            "level": getattr(args, "level", "1★"),
            "rarity": getattr(args, "rarity", "common"),
            "description": desc,
            "prerequisites": [],
            "derivatives": [],
            "evidence": [],
            "knownAgents": [],
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

    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)

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

    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
