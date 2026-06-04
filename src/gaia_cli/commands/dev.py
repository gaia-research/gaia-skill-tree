"""Meta review operations for the Gaia CLI."""

import copy
import json
import os
import sys
import datetime
import subprocess
from pathlib import Path

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


def _is_verifier(username, registry_path=".") -> bool:
    """Check if the user holds at least one 4★ skill implementation."""
    index_path = named_skills_index_path(registry_path)
    if not os.path.exists(index_path):
        return False
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        for entries in index.get("buckets", {}).values():
            for e in entries:
                if e.get("contributor") == username:
                    level = e.get("level", "2★")
                    if level and level[0].isdigit() and int(level[0]) >= 4:
                        return True
    except Exception:
        pass
    return False


def _confirm_destructive(message: str, args) -> None:
    """Prompt for confirmation before a destructive operation.

    Skipped when ``args.yes`` is True.  In non-interactive contexts (CI, piped
    stdin) ``confirm()`` returns the default value (False), so automation MUST
    pass ``--yes`` explicitly to avoid an implicit abort.
    """
    if getattr(args, "yes", False):
        return
    from gaia_cli.interactive import confirm
    if not confirm(message, default=False):
        print("Aborted.")
        sys.exit(0)


def meta_verify_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    evidence_index = args.index
    is_dispute = getattr(args, "dispute", False)
    notes = getattr(args, "notes", None)
    v_source = getattr(args, "source", None)

    contributor = _get_contributor()
    if not _is_verifier(contributor, registry_path):
        print(f"Error: {contributor} is not a Verifier (no 4★+ skill found).")
        print(
            "Only contributors with at least one 4★ implementation can verify evidence."
        )
        sys.exit(1)

    # 1. Check generic nodes
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

    if node_file:
        evidence = skill_data.get("evidence", [])
        if evidence_index >= len(evidence):
            print(
                f"Error: Evidence index {evidence_index} out of range (total {len(evidence)})."
            )
            sys.exit(1)

        ev = evidence[evidence_index]
        ev["verified"] = not is_dispute
        ev["disputed"] = is_dispute
        if notes:
            ev["notes"] = notes
        if v_source:
            ev["verificationSource"] = v_source

        skill_data["updatedAt"] = datetime.date.today().isoformat()
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(skill_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        action = "disputed" if is_dispute else "verified"
        print(
            f"{action.capitalize()} evidence index {evidence_index} for skill {skill_id}."
        )
        append_skill_event(
            skill_id,
            action,
            contributor,
            f"{action.capitalize()} evidence index {evidence_index} from {ev.get('source')}",
            registry_path=registry_path,
        )
    else:
        # 2. Check named skills
        named_dir = Path(named_skills_dir(registry_path))
        target_file = _find_named_file(named_dir, skill_id)
        if not target_file:
            print(f"Error: Skill '{skill_id}' not found.")
            sys.exit(1)

        meta, body = _parse_md(target_file)
        evidence = meta.get("evidence", [])
        if evidence_index >= len(evidence):
            print(
                f"Error: Evidence index {evidence_index} out of range (total {len(evidence)})."
            )
            sys.exit(1)

        ev = evidence[evidence_index]
        ev["verified"] = not is_dispute
        ev["disputed"] = is_dispute
        if notes:
            ev["notes"] = notes
        if v_source:
            ev["verificationSource"] = v_source

        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(target_file, meta, body)

        action = "disputed" if is_dispute else "verified"
        print(
            f"{action.capitalize()} evidence index {evidence_index} for named skill {skill_id}."
        )
        append_skill_event(
            skill_id,
            action,
            contributor,
            f"{action.capitalize()} evidence index {evidence_index} from {ev.get('source')}",
            registry_path=registry_path,
        )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)


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
                # Generic refs are rank-less — only named skills carry a level.
                if getattr(args, "level", False) and skill.get("level"):
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
                    item = {
                        "id": skill["id"],
                        "name": skill.get("name"),
                        "kind": "named",
                        "genericSkillRef": bucket_id,
                    }
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
                    if field in item and field not in (
                        "id",
                        "name",
                        "kind",
                        "description",
                    ):
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


def _replace_section(body: str, section_heading: str, new_content: str) -> str:
    """Replace (or append) a top-level markdown section in the body text.

    Matches ``## {section_heading}`` through the next ``##``-level heading
    or end-of-string, then substitutes new_content.  If the section is not
    found it is appended.

    .. warning::
        The lookahead ``(?=\\n##\\s|\\Z)`` is not fenced-code-block-aware.
        A ``## Heading`` line *inside* a fenced code block (e.g. a HEREDOC
        example) will be treated as a real section boundary, causing the
        replacement to truncate too early.  This is acceptable for the
        current named-skill corpus (no production file has bare ``## ``
        lines inside Installation fences), but callers should avoid
        embedding bare ``## `` lines inside fenced blocks in the
        ``new_content`` they pass in.
    """
    import re

    pattern = rf"(##\s+{re.escape(section_heading)}\s*\n)(.*?)(?=\n##\s|\Z)"
    replacement = rf"\g<1>{new_content}\n"
    result, n = re.subn(pattern, replacement, body, flags=re.DOTALL)
    if n == 0:
        result = body.rstrip("\n") + f"\n\n## {section_heading}\n\n{new_content}\n"
    return result


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


def meta_rename_command(args):
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


def meta_calibrate_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    level = args.level

    # Stars live only on named skills now. Calibrate operates on a named
    # implementation (contributor/skill), not a rank-less generic ref.
    ALLOWED_LEVELS = ["1★", "2★", "3★", "4★", "5★", "6★"]
    if level not in ALLOWED_LEVELS:
        print(f"Error: Named skill level must be one of: {', '.join(ALLOWED_LEVELS)}")
        sys.exit(1)

    if "/" not in skill_id:
        print(
            f"Error: '{skill_id}' is a generic skill reference, which is rank-less. "
            f"Calibrate a named implementation instead, e.g. "
            f"'gaia dev calibrate contributor/{skill_id} {level}'."
        )
        sys.exit(1)

    named_dir = Path(named_skills_dir(registry_path))
    node_file = _find_named_file(named_dir, skill_id)
    if not node_file:
        print(f"Error: Named skill '{skill_id}' not found.")
        sys.exit(1)

    skill_data, body = _parse_md(node_file)
    old_level = skill_data.get("level", "2★")
    skill_data["level"] = level
    skill_data["updatedAt"] = datetime.date.today().isoformat()
    _write_md(node_file, skill_data, body)

    level_num = ALLOWED_LEVELS.index(level)
    old_level_num = (
        ALLOWED_LEVELS.index(old_level) if old_level in ALLOWED_LEVELS else 0
    )
    action = "rank_up" if level_num > old_level_num else "demote"

    append_skill_event(
        skill_id,
        action,
        _get_contributor(),
        f"Calibrated level from {old_level} to {level}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")
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
                if "A" in classes:
                    best_class = "A"
                elif "B" in classes:
                    best_class = "B"
                elif "C" in classes:
                    best_class = "C"

            # Evidence Floor Checks (from GEMINI.md)
            # 2★ needs Tier C
            if level >= 2 and not evidence:
                issues.append(
                    f"[P1] {skill_id}: Level {level_str} but has NO evidence."
                )

            # 3★ needs Tier B
            if level == 3 and best_class == "C":
                issues.append(
                    f"[P1] {skill_id}: Level {level_str} but only has Class C evidence (needs B)."
                )

            # 4★+ needs Tier B/A
            if level >= 4 and best_class not in ["A", "B"]:
                issues.append(
                    f"[P0] {skill_id}: Level {level_str} but only has Class {best_class} evidence (needs A/B)."
                )

            # Orphan check
            if (
                not data.get("prerequisites")
                and data.get("type") != "basic"
                and data.get("type") != "unique"
            ):
                issues.append(
                    f"[P2] {skill_id}: Orphaned {data.get('type')} skill (no prerequisites)."
                )

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
            "status": "named",
            "level": getattr(args, "level", "2★"),
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
            "rarity": getattr(args, "rarity", "common"),
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


def meta_evidence_command(args):
    """Attach evidence to a generic ref (capability, inherited) or a named skill.

    A bare id (``research``) targets the generic skill ref — capability-level
    evidence that every named implementation inherits. A ``contributor/skill``
    id targets that specific named implementation (e.g. its GitHub repo demo).
    """
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    evidence = {
        "class": getattr(args, "evidence_class", "C"),
        "source": args.source,
        "evaluator": getattr(args, "evaluator", None) or _get_contributor(),
        "date": getattr(args, "date", None) or datetime.date.today().isoformat(),
    }
    if getattr(args, "notes", None):
        evidence["notes"] = args.notes

    if "/" in skill_id:
        # Named implementation → write into the named .md frontmatter.
        named_dir = Path(named_skills_dir(registry_path))
        named_file = _find_named_file(named_dir, skill_id)
        if not named_file:
            print(f"Error: Named skill '{skill_id}' not found.")
            sys.exit(1)
        meta, body = _parse_md(named_file)
        meta.setdefault("evidence", []).append(evidence)
        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(named_file, meta, body)
    else:
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
        data.setdefault("evidence", []).append(evidence)
        data["updatedAt"] = datetime.date.today().isoformat()
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print(f"Added evidence to skill: {skill_id}")
    append_skill_event(
        skill_id,
        "evidence_added",
        _get_contributor(),
        f"Added {evidence['class']} evidence from {evidence['source']}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")


def meta_rm_evidence_command(args):
    """Remove an evidence entry from a generic ref or a named skill.

    Identify the entry by ``--index N`` (its position in the evidence array) or
    by ``--source URL`` (exact match; removes every entry with that source).
    Use this to strip dead / broken evidence links flagged by the liveness
    checker. A bare id targets the generic node; ``contributor/skill`` targets
    the named markdown frontmatter.
    """
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    _confirm_destructive(
        f"Remove evidence from '{skill_id}'? This cannot be undone.",
        args,
    )
    index = getattr(args, "index", None)
    source = getattr(args, "source", None)
    if index is None and not source:
        print("Error: provide --index N or --source URL to identify the evidence entry.")
        sys.exit(1)

    def _filter(evlist):
        evlist = evlist or []
        if index is not None:
            if index < 0 or index >= len(evlist):
                print(f"Error: evidence index {index} out of range (0..{len(evlist) - 1}).")
                sys.exit(1)
            removed = [evlist[index]]
            kept = [e for i, e in enumerate(evlist) if i != index]
        else:
            removed = [e for e in evlist if e.get("source") == source]
            kept = [e for e in evlist if e.get("source") != source]
        return kept, removed

    if "/" in skill_id:
        named_dir = Path(named_skills_dir(registry_path))
        named_file = _find_named_file(named_dir, skill_id)
        if not named_file:
            print(f"Error: Named skill '{skill_id}' not found.")
            sys.exit(1)
        meta, body = _parse_md(named_file)
        kept, removed = _filter(meta.get("evidence", []))
        if not removed:
            print(f"No matching evidence on '{skill_id}'.")
            return
        meta["evidence"] = kept
        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(named_file, meta, body)
    else:
        nodes_dir = Path(registry_nodes_dir(registry_path))
        node_file = None
        for p in nodes_dir.glob("**/*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                continue
            if data.get("id") == skill_id:
                node_file = p
                break
        if not node_file:
            print(f"Error: Skill '{skill_id}' not found.")
            sys.exit(1)
        with open(node_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        kept, removed = _filter(data.get("evidence", []))
        if not removed:
            print(f"No matching evidence on '{skill_id}'.")
            return
        data["evidence"] = kept
        data["updatedAt"] = datetime.date.today().isoformat()
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    srcs = ", ".join(e.get("source", "?") for e in removed)
    plural = "entry" if len(removed) == 1 else "entries"
    print(f"Removed {len(removed)} evidence {plural} from {skill_id}: {srcs}")
    append_skill_event(
        skill_id,
        "evidence_removed",
        _get_contributor(),
        f"Removed dead/invalid evidence: {srcs}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")


def meta_build_command(args):
    """Explicitly rebuild registry artifacts and documentation."""
    print("Regenerating registry and documentation...")
    _run_docs_build(args.registry)
    print("Build complete.")


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
    registry_path = args.registry
    target_id = args.target.lstrip("/")
    prereqs = [p.strip() for p in args.prereqs.split(",")]

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


def meta_update_named_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    named_dir = Path(named_skills_dir(registry_path))
    target_file = _find_named_file(named_dir, skill_id)

    if not target_file:
        print(f"Error: Named skill '{skill_id}' not found.")
        sys.exit(1)

    meta, body = _parse_md(target_file)
    changed = False

    if getattr(args, "status", None):
        meta["status"] = args.status
        changed = True

    if getattr(args, "generic_ref", None):
        meta["genericSkillRef"] = args.generic_ref
        changed = True

    if getattr(args, "suite_components", None):
        meta["suiteComponents"] = [s.strip() for s in args.suite_components.split(",")]
        changed = True

    if getattr(args, "suite_ref", None):
        meta["suiteRef"] = args.suite_ref
        changed = True

    if getattr(args, "installation_file", None):
        install_path = Path(args.installation_file)
        if not install_path.exists():
            print(f"Error: Installation file '{install_path}' not found.")
            sys.exit(1)
        new_content = install_path.read_text(encoding="utf-8").strip()
        body = _replace_section(body, "Installation", new_content)
        changed = True

    origin_val = getattr(args, "origin", None)
    origin_changed = False
    if origin_val is not None:
        target_val = (origin_val.lower() == "true")
        if meta.get("origin") != target_val:
            meta["origin"] = target_val
            changed = True
            origin_changed = True
            
            # Uniqueness constraint: if we're setting origin=True, strip it from others in the same bucket
            if target_val and meta.get("genericSkillRef"):
                bucket_ref = meta["genericSkillRef"]
                for other_file in named_dir.rglob("*.md"):
                    if other_file == target_file:
                        continue
                    o_meta, o_body = _parse_md(other_file)
                    if o_meta.get("genericSkillRef") == bucket_ref and o_meta.get("origin") is True:
                        o_meta["origin"] = False
                        o_meta["updatedAt"] = datetime.date.today().isoformat()
                        _write_md(other_file, o_meta, o_body)
                        append_skill_event(
                            o_meta["id"],
                            "demote",
                            _get_contributor(),
                            f"Origin status removed. Transferred to {skill_id}.",
                            registry_path=registry_path
                        )
                        print(f"Removed origin from competing skill: {o_meta['id']}")

    if changed:
        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(target_file, meta, body)
        print(f"Updated named skill frontmatter: {target_file}")

        # Record timeline events for mutations that affect suite topology or content.
        registry_path = args.registry
        contributor = _get_contributor()

        if origin_changed:
            append_skill_event(
                skill_id,
                "rank_up" if target_val else "demote",
                contributor,
                f"Origin status set to {'true' if target_val else 'false'}.",
                registry_path=registry_path
            )
        if getattr(args, "suite_ref", None):
            append_skill_event(
                skill_id,
                "suite_ref_set",
                contributor,
                f"Set suiteRef to {args.suite_ref}",
                registry_path=registry_path,
            )
        if getattr(args, "installation_file", None):
            append_skill_event(
                skill_id,
                "installation_updated",
                contributor,
                f"Replaced ## Installation section from {args.installation_file}",
                registry_path=registry_path,
            )

        if not getattr(args, "no_build", False):
            print("Regenerating registry and documentation...")
            _run_docs_build(args.registry)
        else:
            print("Skipping documentation rebuild as requested (--no-build).")
    else:
        print("No changes specified.")


# ---------------------------------------------------------------------------
# Paths treated as generated noise (always skipped by dev diff)
# ---------------------------------------------------------------------------
_GENERATED_PREFIXES = (
    "docs/",
    "skill-trees/",
    "registry/gaia.gexf",
    "registry/gaia.svg",
    "registry/named-skills.json",
    "registry/combinations.md",
    "registry/registry.md",
    "registry/skill-sources.md",
)
_GENERATED_SUFFIXES = (
    ".gexf",
    ".svg",
    ".html",
)
_GENERATED_EXACT = {
    "uv.lock",
    "docs/css/tokens.css",
    "docs/tree.md",
}
_VERSION_FILES = {
    "pyproject.toml",
    "packages/cli-npm/package.json",
    "packages/mcp/package.json",
    "registry/gaia.json",
    "docs/graph/gaia.json",
}


def _is_generated(path):
    if path in _GENERATED_EXACT:
        return True
    for prefix in _GENERATED_PREFIXES:
        if path.startswith(prefix):
            return True
    for suffix in _GENERATED_SUFFIXES:
        if path.endswith(suffix):
            return True
    return False


def _parse_named_frontmatter(content):
    """Extract key/value pairs from YAML frontmatter in a named skill file."""
    if not content.startswith("---"):
        return {}
    lines = content.split("\n")
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    meta = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip("'\"")
    return meta


def meta_diff_command(args):
    """Show substantive registry additions in a branch vs main, stripping generated noise."""
    ref = getattr(args, "ref", None)
    base = getattr(args, "base", "origin/main")

    if ref:
        compare_ref = (
            ref if ref.startswith(("origin/", "HEAD", "refs/")) else f"origin/{ref}"
        )
    else:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
        current = r.stdout.strip()
        if not current or current in ("HEAD", "main"):
            print("Error: specify a branch, e.g.  gaia dev diff review/meta/my-branch")
            sys.exit(1)
        compare_ref = current

    print(f"\n  Comparing {base}...{compare_ref}\n")

    def _git_json(git_ref, path):
        r = subprocess.run(
            ["git", "show", f"{git_ref}:{path}"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return None
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return None

    def _git_text(git_ref, path):
        r = subprocess.run(
            ["git", "show", f"{git_ref}:{path}"],
            capture_output=True,
            text=True,
        )
        return r.stdout if r.returncode == 0 else ""

    # Gather changed files, separate generated noise from substantive paths
    r = subprocess.run(
        ["git", "diff", "--name-status", f"{base}...{compare_ref}"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"Error running git diff: {r.stderr.strip()}")
        sys.exit(1)

    skipped = 0
    substantive = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, path = parts[0].rstrip(), parts[1]
        if _is_generated(path):
            skipped += 1
        else:
            substantive.append((status, path))

    # Diff registry/gaia.json as structured JSON (most reliable approach)
    base_graph = _git_json(base, "registry/gaia.json") or {"skills": [], "edges": []}
    branch_graph = _git_json(compare_ref, "registry/gaia.json") or {
        "skills": [],
        "edges": [],
    }

    base_ids = {s["id"] for s in base_graph.get("skills", [])}
    branch_ids = {s["id"] for s in branch_graph.get("skills", [])}

    new_skill_ids = branch_ids - base_ids
    removed_skill_ids = base_ids - branch_ids
    new_skills = sorted(
        [s for s in branch_graph.get("skills", []) if s["id"] in new_skill_ids],
        key=lambda s: s["id"],
    )

    def _edge_key(e):
        return (e["sourceSkillId"], e["targetSkillId"], e.get("edgeType", ""))

    base_edges = {_edge_key(e) for e in base_graph.get("edges", [])}
    branch_edges = {_edge_key(e) for e in branch_graph.get("edges", [])}
    new_edges = sorted(branch_edges - base_edges)
    removed_edges = sorted(base_edges - branch_edges)

    base_version = base_graph.get("version", "?")
    branch_version = branch_graph.get("version", "?")

    # Categorise substantive paths
    new_named = sorted(
        (s, p) for s, p in substantive if s == "A" and p.startswith("registry/named/")
    )
    mod_named = sorted(
        (s, p) for s, p in substantive if s == "M" and p.startswith("registry/named/")
    )
    new_node_files = sorted(
        (s, p) for s, p in substantive if s == "A" and p.startswith("registry/nodes/")
    )
    version_paths = [(s, p) for s, p in substantive if p in _VERSION_FILES]
    other = [
        (s, p)
        for s, p in substantive
        if not p.startswith("registry/named/")
        and not p.startswith("registry/nodes/")
        and p not in _VERSION_FILES
        and p != "registry/gaia.json"
    ]

    W = 68

    # ── New generic skills ────────────────────────────────────────────
    if new_skills:
        print(f"  ── NEW GENERIC SKILLS ({len(new_skills)}) {'─' * max(0, W - 24)}")
        for s in new_skills:
            stype = s.get("type", "?")
            level = s.get("level", "?")
            status = s.get("status", "?")
            desc = s.get("description", "")
            if len(desc) > 65:
                desc = desc[:62] + "..."
            prereqs = s.get("prerequisites", [])
            evidence = s.get("evidence", [])
            ev_str = (
                f"{len(evidence)}× ({', '.join(e['class'] for e in evidence)})"
                if evidence
                else "none"
            )
            print(f"  + {s['id']}  [{stype} · {level} · {status}]")
            print(f'    "{desc}"')
            if prereqs:
                print(f"    Prerequisites: {', '.join(prereqs)}")
            print(f"    Evidence: {ev_str}")
        print()

    # ── Removed generic skills (danger) ──────────────────────────────
    if removed_skill_ids:
        print(
            f"  ── ⛔  REMOVED SKILLS ({len(removed_skill_ids)}) {'─' * max(0, W - 24)}"
        )
        for sid in sorted(removed_skill_ids):
            print(f"  - {sid}")
        print()

    # ── New named skill files ─────────────────────────────────────────
    if new_named:
        print(f"  ── NEW NAMED SKILLS ({len(new_named)}) {'─' * max(0, W - 22)}")
        for _, path in new_named:
            content = _git_text(compare_ref, path)
            meta = _parse_named_frontmatter(content)
            skill_id = meta.get(
                "id", path.replace("registry/named/", "").replace(".md", "")
            )
            generic = meta.get("genericSkillRef", "—")
            level = meta.get("level", "?")
            print(f"  + {skill_id}  → {generic}  [{level}]")
        print()

    if mod_named:
        print(f"  ── MODIFIED NAMED SKILLS ({len(mod_named)}) {'─' * max(0, W - 27)}")
        for _, path in mod_named:
            print(f"  ~ {path.replace('registry/named/', '')}")
        print()

    # ── New edges ────────────────────────────────────────────────────
    if new_edges:
        print(f"  ── NEW EDGES ({len(new_edges)}) {'─' * max(0, W - 15)}")
        for src, tgt, etype in new_edges:
            print(f"  + {src} → {tgt}  ({etype})")
        print()

    if removed_edges:
        print(f"  ── ⛔  REMOVED EDGES ({len(removed_edges)}) {'─' * max(0, W - 23)}")
        for src, tgt, etype in removed_edges:
            print(f"  - {src} → {tgt}  ({etype})")
        print()

    # ── Version bump ─────────────────────────────────────────────────
    if base_version != branch_version:
        print(f"  ── VERSION BUMP {'─' * max(0, W - 17)}")
        print(f"  {base_version} → {branch_version}  (will conflict if main has moved)")
        print()

    # ── Other substantive changes ─────────────────────────────────────
    if other:
        print(f"  ── OTHER CHANGES ({len(other)}) {'─' * max(0, W - 19)}")
        for status, path in other:
            label = {"A": "new", "M": "mod", "D": "del"}.get(status, status)
            print(f"  {label}  {path}")
        print()

    # ── Quality flags ─────────────────────────────────────────────────
    flags = []
    for sid in sorted(removed_skill_ids):
        flags.append(("⛔", f"{sid} — skill removed (verify intentional!)"))

    for _, path in new_named:
        content = _git_text(compare_ref, path)
        meta = _parse_named_frontmatter(content)
        skill_id = meta.get(
            "id", path.replace("registry/named/", "").replace(".md", "")
        )
        if "Add installation instructions here" in content:
            flags.append(("⚠", f"{skill_id} — empty ## Installation body"))
        if not meta.get("genericSkillRef"):
            flags.append(("⚠", f"{skill_id} — missing genericSkillRef"))

    for s in new_skills:
        ev = s.get("evidence", [])
        if not ev:
            flags.append(("⚠", f"{s['id']} — no evidence attached"))
        elif all(e["class"] == "C" for e in ev):
            flags.append(("⚠", f"{s['id']} — only Class C evidence"))
        if s.get("rarity"):
            flags.append(
                (
                    "·",
                    f"{s['id']} — rarity field present (deprecated auto-default, harmless)",
                )
            )

    if flags:
        print(f"  ── QUALITY FLAGS {'─' * max(0, W - 18)}")
        for icon, msg in flags:
            print(f"  {icon}  {msg}")
        print()

    # ── Summary ───────────────────────────────────────────────────────
    if (
        not new_skills
        and not removed_skill_ids
        and not new_named
        and not new_edges
        and not other
    ):
        print(
            "  No substantive changes — branch is all generated noise or already merged."
        )

    print(f"  Skipped {skipped} generated files (SVG, HTML, GEXF, timestamps).")
    print()


def meta_timeline_command(args):
    """Append a standalone event to a skill's or user tree's timeline."""
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    action = args.action
    notes = args.notes
    user = getattr(args, "user", None)
    timestamp = getattr(args, "timestamp", None)

    if user:
        from gaia_cli.timeline import append_skill_tree_event
        append_skill_tree_event(
            user,
            skill_id,
            action,
            notes,
            registry_path=registry_path,
            timestamp=timestamp,
        )
        marker = f" (at {timestamp})" if timestamp else ""
        print(f"Appended '{action}' event for '{skill_id}' to skill-trees/{user}/skill-tree.json{marker}.")
    else:
        from gaia_cli.timeline import append_skill_event
        append_skill_event(
            skill_id,
            action,
            _get_contributor(),
            notes,
            registry_path=registry_path,
        )

    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")

