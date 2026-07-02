import datetime
import json
import sys
from pathlib import Path

from gaia_cli.registry import named_skills_dir, registry_nodes_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _parse_md,
    _update_named_skill_ref,
    _get_contributor,
    _run_docs_build,
    _run_dev_preflights,
    preflightRenameCommand,
)


def meta_rename_command(args):
    _run_dev_preflights([
        lambda: preflightRenameCommand(args),
    ])
    registry_path = args.registry
    old_id = args.old_id.lstrip("/")
    new_id = args.new_id.lstrip("/")

    nodes_dir = Path(registry_nodes_dir(registry_path))
    old_file = None
    skill_data = None

    # ⚡ Bolt: Single pass read of all nodes
    all_nodes = []
    new_id_exists = False

    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        node_id = data.get("id")
        all_nodes.append((p, data))

        if node_id == old_id:
            old_file = p
            skill_data = data
        elif node_id == new_id:
            new_id_exists = True

    if not old_file:
        print(f"Error: Skill '{old_id}' not found.")
        sys.exit(1)

    # Rename the file and update ID
    new_file = old_file.parent / f"{new_id}.json"
    if new_file.exists():
        print(
            f"Error: '{new_id}' already exists on disk at {new_file}. Rename aborted."
        )
        sys.exit(1)

    if new_id_exists:
        print(f"Error: Skill with id '{new_id}' already exists in registry.")
        sys.exit(1)

    skill_data["id"] = new_id
    skill_data["updatedAt"] = datetime.date.today().isoformat()

    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(skill_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    old_file.unlink()
    print(f"Renamed {old_file} to {new_file}")

    # Update references in all other nodes
    # Skip processing old_file as it has been renamed and deleted
    for p, data in all_nodes:
        if p.name == old_file.name and p.parent == old_file.parent:
            continue

        changed = False
        if "prerequisites" in data:
            if old_id in data["prerequisites"]:
                data["prerequisites"] = [
                    new_id if pr == old_id else pr for pr in data["prerequisites"]
                ]
                changed = True

        if "derivatives" in data:
            if old_id in data["derivatives"]:
                data["derivatives"] = [
                    new_id if dr == old_id else dr for dr in data["derivatives"]
                ]
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

    append_skill_event(
        new_id,
        "rename",
        _get_contributor(),
        f"Renamed from {old_id} to {new_id}",
        registry_path=registry_path,
    )

    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
    print(f"Successfully renamed '{old_id}' to '{new_id}'.")
