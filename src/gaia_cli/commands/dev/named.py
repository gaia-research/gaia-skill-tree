import sys
import datetime
from pathlib import Path

from gaia_cli.registry import named_skills_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _find_named_file,
    _parse_md,
    _write_md,
    _replace_section,
    _get_contributor,
    _run_docs_build,
    _run_dev_preflights,
    _preflight_named_status_identity,
    preflightSuiteComponents,
    preflightGithubLink,
    parseCommaSeparatedIds,
)


def _preflight_no_manual_origin(args) -> None:
    """Origin is automatic (founder rulings 2026-10-30); refuse a manual flag."""
    if getattr(args, "origin", None) is None:
        return
    from gaia_cli.commands.dev.helpers import _fail_dev_preflight

    _fail_dev_preflight(
        "--origin is retired: Origin is automatic. Each generic bucket's Origin is its "
        "highest-merit named implementation (published level, then Trust Magnitude); "
        "tied top contenders all hold it, frozen skills compete with their locked TM/grade, "
        "and there is no star floor. Nothing was written.",
        fix=(
            "Change the skill's merit instead (evidence via `gaia dev evidence`, level via "
            "`gaia dev calibrate`), then run `gaia dev docs`; the build derives Origin. "
            "See META.md §4.1 and src/gaia_cli/origin.py."
        ),
    )


def meta_update_named_command(args):
    registry_path = args.registry
    skill_id = args.skill_id.lstrip("/")

    named_dir = Path(named_skills_dir(registry_path))
    target_file = _find_named_file(named_dir, skill_id)

    if not target_file:
        print(f"Error: Named skill '{skill_id}' not found.")
        sys.exit(1)

    meta, body = _parse_md(target_file)
    prior_status = meta.get("status")
    changed = False
    status_promoted_to_named = False

    _run_dev_preflights([
        lambda: _preflight_no_manual_origin(args),
        lambda: _preflight_named_status_identity(skill_id, meta, args),
        lambda: preflightSuiteComponents(registry_path, getattr(args, "suite_components", None)),
        lambda: preflightGithubLink(getattr(args, "github_link", None)),
    ])

    if getattr(args, "status", None):
        new_status = args.status
        if prior_status != "named" and new_status == "named":
            status_promoted_to_named = True
        meta["status"] = new_status
        changed = True

    if getattr(args, "name", None):
        meta["name"] = args.name
        changed = True

    if getattr(args, "title", None):
        meta["title"] = args.title
        changed = True

    if getattr(args, "catalog_ref", None):
        meta["catalogRef"] = args.catalog_ref
        changed = True

    if getattr(args, "generic_ref", None):
        meta["genericSkillRef"] = args.generic_ref
        changed = True

    if getattr(args, "suite_components", None):
        meta["suiteComponents"] = parseCommaSeparatedIds(args.suite_components, "suite component")
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

    if getattr(args, "github_link", None) is not None:
        if args.github_link == "":
            # Empty string is an explicit clear.
            if "links" in meta and "github" in meta["links"]:
                del meta["links"]["github"]
                if not meta["links"]:
                    del meta["links"]
                changed = True
        else:
            meta.setdefault("links", {})["github"] = args.github_link
            changed = True

    installable_val = getattr(args, "installable", None)
    if installable_val is not None:
        target_val = (installable_val.lower() == "true")
        if meta.get("installable") != target_val:
            meta["installable"] = target_val
            changed = True
            if not target_val and "links" in meta:
                meta.pop("links")

    notesText = (getattr(args, "notes", None) or "").strip()
    notesSuffix = f" {notesText}" if notesText else ""

    if changed:
        meta["updatedAt"] = datetime.date.today().isoformat()
        _write_md(target_file, meta, body)
        print(f"Updated named skill frontmatter: {target_file}")

        # Record timeline events for mutations that affect suite topology or content.
        registry_path = args.registry
        contributor = _get_contributor()

        if status_promoted_to_named:
            append_skill_event(
                skill_id,
                "name",
                contributor,
                f"Promoted from {prior_status or 'unknown'} to named." + notesSuffix,
                registry_path=registry_path,
            )
        if getattr(args, "suite_ref", None):
            append_skill_event(
                skill_id,
                "suite_ref_set",
                contributor,
                f"Set suiteRef to {args.suite_ref}" + notesSuffix,
                registry_path=registry_path,
            )
        if getattr(args, "installation_file", None):
            append_skill_event(
                skill_id,
                "installation_updated",
                contributor,
                f"Replaced ## Installation section from {args.installation_file}" + notesSuffix,
                registry_path=registry_path,
            )
        if getattr(args, "github_link", None) is not None:
            if args.github_link == "":
                append_skill_event(
                    skill_id,
                    "note",
                    contributor,
                    "Cleared GitHub link.",
                    registry_path=registry_path,
                )
            else:
                append_skill_event(
                    skill_id,
                    "note",
                    contributor,
                    f"Updated GitHub link to {args.github_link}",
                    registry_path=registry_path,
                )
        if getattr(args, "installable", None) is not None:
            append_skill_event(
                skill_id,
                "note",
                contributor,
                f"Set installable to {args.installable}",
                registry_path=registry_path,
            )

        if not getattr(args, "no_build", False):
            print("Regenerating registry and documentation...")
            _run_docs_build(args.registry)
        else:
            print("Skipping documentation rebuild as requested (--no-build).")
    else:
        print("No changes specified.")
