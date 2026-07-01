import sys
import datetime
import json
from pathlib import Path

from gaia_cli.registry import named_skills_dir, registry_nodes_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _find_named_file,
    _parse_md,
    _write_md,
    _confirm_destructive,
    _get_contributor,
    _run_docs_build,
    _run_dev_preflights,
    preflightAddCommand,
    preflightLinkCommand,
    parseCommaSeparatedIds,
)


def meta_build_command(args):
    """Explicitly rebuild registry artifacts and documentation."""
    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
    print("Build complete.")


def meta_add_command(args):
    _run_dev_preflights([
        lambda: preflightAddCommand(args),
    ])
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
            print(
                "Error: --description must be at least 10 characters (schema requirement)."
            )
            sys.exit(1)

        meta = {
            "id": f"{contributor}/{skill_id}",
            "name": skill_name,
            "contributor": contributor,
            "origin": False,
            "genericSkillRef": getattr(args, "generic_ref", "unknown"),
            "status": getattr(args, "status", None) or "named",
            "level": getattr(args, "level", None) or "2★",
            "description": desc,
            "createdAt": datetime.date.today().isoformat(),
            "updatedAt": datetime.date.today().isoformat(),
        }

        # Apply --title if provided
        title = getattr(args, "title", None)
        if title:
            meta["title"] = title

        # Apply --extra-fields for named skills (links, tags, catalogRef, origin, etc.)
        if getattr(args, "extra_fields", None):
            try:
                extra = json.loads(args.extra_fields)
                if isinstance(extra, dict):
                    meta.update({k: v for k, v in extra.items() if v is not None})
                else:
                    print("Warning: --extra-fields must be a JSON object. Skipping.")
            except json.JSONDecodeError:
                print("Warning: Could not parse extra-fields JSON. Skipping.")

        body = "\n\n## Installation\nAdd installation instructions here.\n"
        _write_md(dest_file, meta, body)
        print(f"Created named skill: {dest_file}")
        append_skill_event(
            f"{contributor}/{skill_id}",
            "add",
            _get_contributor(),
            f"Added named skill {contributor}/{skill_id}",
            registry_path=registry_path,
        )
    else:
        skill_type = getattr(args, "type", "basic")
        dest_dir = Path(registry_nodes_dir(registry_path)) / skill_type
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{skill_id}.json"

        desc = (getattr(args, "description", None) or "").strip()
        if len(desc) < 10:
            print(
                "Error: --description must be at least 10 characters (schema requirement)."
            )
            sys.exit(1)

        # Generic skill refs are rank-less — no level/demerits. They keep an
        # (optional) evidence pool inherited by their named implementations.
        data = {
            "id": skill_id,
            "name": skill_name,
            "type": skill_type,
            "description": desc,
            "prerequisites": [],
            "derivatives": [],
            "evidence": [],
            "knownAgents": [],
            "status": "provisional",
            "createdAt": datetime.date.today().isoformat(),
            "updatedAt": datetime.date.today().isoformat(),
            "version": "0.1.0",
        }

        # Add any extra fields passed
        if getattr(args, "extra_fields", None):
            try:
                extra = json.loads(args.extra_fields)
                if isinstance(extra, dict):
                    data.update({k: v for k, v in extra.items() if v is not None})
                else:
                    print("Warning: --extra-fields must be a JSON object. Skipping.")
            except json.JSONDecodeError:
                print("Warning: Could not parse extra-fields JSON. Skipping.")

        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Created generic skill: {dest_file}")
        append_skill_event(
            skill_id,
            "add",
            _get_contributor(),
            f"Added generic skill {skill_id}",
            registry_path=registry_path,
        )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")


def meta_remove_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    _confirm_destructive(
        f"Remove skill '{skill_id}' and all references? This cannot be undone.",
        args,
    )

    nodes_dir = Path(registry_nodes_dir(registry_path))
    node_file = None

    # ⚡ Bolt: Single pass read of all nodes
    all_nodes = []

    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        all_nodes.append((p, data))

        if data.get("id") == skill_id:
            node_file = p

    if not node_file:
        print(f"Error: Generic skill '{skill_id}' not found.")
        sys.exit(1)

    node_file.unlink()
    print(f"Removed generic skill file: {node_file}")

    # Remove references in other skills
    for p, data in all_nodes:
        # Skip processing node_file as it has been deleted
        if p.name == node_file.name and p.parent == node_file.parent:
            continue

        changed = False
        if "prerequisites" in data and skill_id in data["prerequisites"]:
            data["prerequisites"].remove(skill_id)
            changed = True
        if "derivatives" in data and skill_id in data["derivatives"]:
            data["derivatives"].remove(skill_id)
            changed = True

        if changed:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"Removed references to {skill_id} in {p}")

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")


def meta_link_command(args):
    _run_dev_preflights([
        lambda: preflightLinkCommand(args),
    ])
    registry_path = args.registry
    target_id = args.target.lstrip("/")
    prereqs = parseCommaSeparatedIds(args.prereqs, "prerequisite")

    nodes_dir = Path(registry_nodes_dir(registry_path))
    target_file = None

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
        print(f"Error: Target skill '{target_id}' not found.")
        sys.exit(1)

    with open(target_file, "r", encoding="utf-8") as f:
        target_data = json.load(f)

    if getattr(args, "reset", False):
        merged = prereqs
    else:
        merged = list(set(target_data.get("prerequisites", []) + prereqs))
    target_data["prerequisites"] = sorted(merged)
    target_data["updatedAt"] = datetime.date.today().isoformat()

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(target_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Updated prerequisites for {target_id}: {target_data['prerequisites']}")

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")


def meta_reclassify_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    new_type = args.new_type

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

    old_type = skill_data.get("type", "basic")
    if old_type == new_type:
        print(f"Skill '{skill_id}' is already of type '{new_type}'.")
        return

    skill_data["type"] = new_type
    skill_data["updatedAt"] = datetime.date.today().isoformat()

    # Move file to the correct type directory
    new_dir = nodes_dir / new_type
    new_dir.mkdir(parents=True, exist_ok=True)
    new_file = new_dir / f"{skill_id}.json"

    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(skill_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    node_file.unlink()
    print(
        f"Reclassified '{skill_id}' from {old_type} to {new_type} and moved to {new_file}"
    )

    append_skill_event(
        skill_id,
        "type_change",
        _get_contributor(),
        f"Reclassified from {old_type} to {new_type}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")
