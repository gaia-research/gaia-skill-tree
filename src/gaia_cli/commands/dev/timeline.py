import sys
from gaia_cli.commands.dev.helpers import _get_contributor, _run_docs_build


def meta_timeline_command(args):
    """Append a standalone event to a skill's or user tree's timeline."""
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")
    action = args.action
    notes = args.notes
    user = getattr(args, "user", None)
    timestamp = getattr(args, "timestamp", None)

    if user:
        # Check if skill_id refers to a named skill first; if so write there.
        from gaia_cli.timeline import _named_skill_file
        named_file = _named_skill_file(skill_id, registry_path)
        if named_file:
            from gaia_cli.timeline import append_skill_event
            append_skill_event(skill_id, action, user, notes, registry_path=registry_path)
            print(f"Appended '{action}' event for '{skill_id}' to named skill file.")
        else:
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
