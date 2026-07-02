import sys
from pathlib import Path

from gaia_cli.commands.dev.helpers import (
    _get_contributor,
    _run_docs_build,
    _run_dev_preflights,
    _fail_dev_preflight,
    _preflight_iso_timestamp,
)


def _registry_timeline_target_exists(skill_id: str, registry_path: str) -> bool:
    from gaia_cli.registry import registry_nodes_dir, named_skills_dir
    from gaia_cli.commands.dev.helpers import _find_named_file

    nodes_dir = Path(registry_nodes_dir(registry_path))
    for node_file in nodes_dir.glob("**/*.json"):
        try:
            import json
            data = json.loads(node_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("id") == skill_id:
            return True

    named_dir = Path(named_skills_dir(registry_path))
    return _find_named_file(named_dir, skill_id) is not None


def _preflight_timeline_command(args) -> None:
    skill_id = args.skill_id.lstrip("/")
    user = getattr(args, "user", None)
    timestamp = getattr(args, "timestamp", None)
    _preflight_iso_timestamp(timestamp)

    if user:
        from gaia_cli.treeManager import load_tree
        try:
            tree_data = load_tree(user, args.registry)
        except ValueError as exc:
            _fail_dev_preflight(str(exc))
        if tree_data is None:
            _fail_dev_preflight(
                f"User tree skill-trees/{user}/skill-tree.json does not exist.",
                fix="Run `gaia init` for that user or pass the correct --user value before appending a user-tree timeline event.",
            )
        return

    if timestamp:
        _fail_dev_preflight(
            "--timestamp is only supported with --user skill-tree timeline events.",
            fix="Pass --user <username> for historical user-tree backfills, or omit --timestamp for registry timelines.",
        )
    if not _registry_timeline_target_exists(skill_id, args.registry):
        _fail_dev_preflight(
            f"Timeline target '{skill_id}' was not found in registry nodes or named skills.",
            fix="Use an existing generic or named skill ID, or pass --user when targeting a user skill tree.",
        )


def meta_timeline_command(args):
    """Append a standalone event to a skill's or user tree's timeline."""
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    action = args.action
    notes = args.notes
    user = getattr(args, "user", None)
    timestamp = getattr(args, "timestamp", None)

    _run_dev_preflights([
        lambda: _preflight_timeline_command(args),
    ])

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
