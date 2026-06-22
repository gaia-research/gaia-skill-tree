import copy
import datetime
import json
import sys
from pathlib import Path

from gaia_cli.registry import named_skills_dir, registry_nodes_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _find_named_file,
    _parse_md,
    _write_md,
    _confirm_destructive,
    _get_contributor,
    _update_named_skill_ref,
    _run_docs_build,
)


def meta_merge_command(args):
    registry_path = args.registry
    target_id = args.target.lstrip("/")
    sources = [s.lstrip("/") for s in args.sources]

    _confirm_destructive(
        f"Merge {sources} into '{target_id}'? Source skills will be deleted. This cannot be undone.",
        args,
    )

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
                target_meta["tags"] = list(
                    set(target_meta.get("tags", [])) | set(source_meta["tags"])
                )
            if "knownAgents" in source_meta:
                target_meta["knownAgents"] = list(
                    set(target_meta.get("knownAgents", []))
                    | set(source_meta["knownAgents"])
                )

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

        append_skill_event(
            target_id,
            "merge",
            _get_contributor(),
            f"Merged named skills {', '.join(sources)} into {target_id}",
            registry_path=registry_path,
        )
    else:
        # Generic skill merging
        nodes_dir = Path(registry_nodes_dir(registry_path))

        # ⚡ Bolt: Single pass read of all nodes
        all_nodes = []
        target_file = None
        target_data = None
        source_data_map = {}
        source_file_map = {}

        for p in nodes_dir.glob("**/*.json"):
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue

            node_id = data.get("id")
            all_nodes.append((p, data))

            if node_id == target_id:
                target_file = p
                target_data = data
            elif node_id in sources:
                source_file_map[node_id] = p
                source_data_map[node_id] = data

        if not target_file:
            print(f"Error: Target skill '{target_id}' not found in registry nodes.")
            sys.exit(1)

        merged_evidence = target_data.get("evidence", []) or []
        merged_prereqs = set(target_data.get("prerequisites", []) or [])
        merged_derivatives = set(target_data.get("derivatives", []) or [])
        merged_agents = set(target_data.get("knownAgents", []) or [])

        source_files = []
        for source_id in sources:
            source_file = source_file_map.get(source_id)
            source_data = source_data_map.get(source_id)

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

        sources_set = set(sources)
        for p, data in all_nodes:
            if p == target_file or p in source_files:
                continue

            changed = False
            if data.get("prerequisites"):
                new_prereqs = [
                    target_id if pr in sources_set and target_id != data["id"] else pr
                    for pr in data["prerequisites"]
                    if pr not in sources_set or target_id != data["id"]
                ]
                seen = set()
                new_prereqs = [x for x in new_prereqs if not (x in seen or seen.add(x))]
                if new_prereqs != data["prerequisites"]:
                    data["prerequisites"] = new_prereqs
                    changed = True

            if data.get("derivatives"):
                new_derivatives = [
                    target_id if dr in sources_set and target_id != data["id"] else dr
                    for dr in data["derivatives"]
                    if dr not in sources_set or target_id != data["id"]
                ]
                seen = set()
                new_derivatives = [
                    x for x in new_derivatives if not (x in seen or seen.add(x))
                ]
                if new_derivatives != data["derivatives"]:
                    data["derivatives"] = new_derivatives
                    changed = True

            if changed:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                print(f"Updated references in {p}")

        # ⚡ Bolt: Update named skill references O(N) optimized pass
        named_dir = Path(named_skills_dir(registry_path))
        sources_set = set(sources)
        for p in named_dir.glob("**/*.md"):
            meta, body = _parse_md(p)
            current_ref = meta.get("genericSkillRef")
            if current_ref in sources_set:
                meta["genericSkillRef"] = target_id
                _write_md(p, meta, body)
                print(f"Updated genericSkillRef in {p}")

        append_skill_event(
            target_id,
            "merge",
            _get_contributor(),
            f"Merged {', '.join(sources)} into {target_id}",
            registry_path=registry_path,
        )

    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
    print(f"Successfully merged skills into '{target_id}'.")


def meta_split_command(args):
    registry_path = args.registry
    source_id = args.source.lstrip("/")
    targets = [t.lstrip("/") for t in args.targets]

    _confirm_destructive(
        f"Split '{source_id}' into {targets}? The source skill will be deleted. This cannot be undone.",
        args,
    )

    nodes_dir = Path(registry_nodes_dir(registry_path))
    source_file = None
    source_data = None

    # ⚡ Bolt: Single pass read of all nodes
    all_nodes = []
    existing_ids = set()

    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        node_id = data.get("id")
        if node_id:
            existing_ids.add(node_id)

        all_nodes.append((p, data))

        if node_id == source_id:
            source_file = p
            source_data = data

    if not source_file:
        print(f"Error: Source skill '{source_id}' not found.")
        sys.exit(1)

    for target_id in targets:
        target_file = source_file.parent / f"{target_id}.json"
        if target_file.exists():
            print(f"Error: split target '{target_id}' already exists on disk.")
            sys.exit(1)

        if target_id in existing_ids:
            print(f"Error: split target '{target_id}' already exists in registry.")
            sys.exit(1)

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
    for p, data in all_nodes:
        # Skip the source file that is about to be deleted
        if p.name == source_file.name and p.parent == source_file.parent:
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
                    if (
                        first_target not in new_derivatives
                        and first_target != data["id"]
                    ):
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
    append_skill_event(
        first_target,
        "split",
        _get_contributor(),
        f"Split {source_id} into {', '.join(targets)}",
        registry_path=registry_path,
    )

    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
