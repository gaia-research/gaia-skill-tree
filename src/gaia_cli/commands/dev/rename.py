import datetime
import json
import sys
from pathlib import Path

from gaia_cli.registry import named_skills_dir, registry_nodes_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _parse_md,
    _write_md,
    _find_named_file,
    _update_named_skill_ref,
    _get_contributor,
    _run_docs_build,
    _run_dev_preflights,
    preflightRenameCommand,
)
from gaia_cli.commands.dev.renameSurfaces import (
    rewriteProseRefs,
    updateSuiteManifests,
    updateSkillTrees,
    reportStaleReferences,
)


def _rewrite_prose(body: str, old_id: str, new_id: str, args, path_label: str) -> str:
    """Rewrite prose references to the old id, honouring `--no-prose`.

    Prose inside a registry markdown file routinely carries the id as a real
    reference — install commands, badge/explorer URLs, cross-links. Those are
    rewritten; changelog/history sections are not (they record what the skill
    was called at the time).
    """
    if getattr(args, "no_prose", False):
        return body
    rewritten, count, changelog_hits = rewriteProseRefs(body, old_id, new_id)
    if count:
        print(f"Rewrote {count} prose reference(s) in {path_label}")
    if changelog_hits:
        print(
            f"Left {changelog_hits} changelog/history reference(s) in {path_label} "
            "untouched (historical record)"
        )
    return rewritten


def _update_shared_surfaces(args, old_id: str, new_id: str) -> None:
    """Update every non-node reference surface, then report what is left.

    Shared by the generic-node and named-skill rename paths (#1456).
    """
    for message in updateSuiteManifests(args.registry, old_id, new_id):
        print(message)
    for message in updateSkillTrees(args.registry, old_id, new_id):
        print(message)
    if not getattr(args, "skip_ref_scan", False):
        reportStaleReferences(args.registry, old_id, new_id)


def _rename_named_skill(args, old_id: str, new_id: str) -> None:
    """Rename a named skill (contributor/slug): move the .md, update its id and
    display name/title, repoint every suiteComponents/suiteRef reference in other
    named files and suite manifests, and log a timeline event.

    Named skills carry their own evidence and identity in the .md frontmatter;
    the generic-node walk in meta_rename_command does not touch them.
    """
    registry_path = args.registry
    named_dir = Path(named_skills_dir(registry_path))

    old_file = _find_named_file(named_dir, old_id)
    if old_file is None:
        print(f"Error: Named skill '{old_id}' not found.")
        sys.exit(1)

    new_contributor, new_slug = new_id.split("/", 1)
    new_dir = named_dir / new_contributor
    new_dir.mkdir(parents=True, exist_ok=True)
    new_file = new_dir / f"{new_slug}.md"
    if new_file.exists():
        print(f"Error: '{new_id}' already exists on disk at {new_file}. Rename aborted.")
        sys.exit(1)

    meta, body = _parse_md(old_file)
    old_slug = old_id.split("/", 1)[1]

    # Human-readable name/title default to the slug (title-cased) at add time.
    # Only rewrite them when they still mirror the old slug, so a hand-set
    # display name is preserved.
    old_slug_titled = old_slug.replace("-", " ").title()
    new_slug_titled = new_slug.replace("-", " ").title()
    if meta.get("name") in (old_slug, old_slug_titled, None):
        meta["name"] = new_slug_titled
    # Unlike name, title is schema-optional and reviewer-only (valid solely on
    # status: named — see registry/schema). Absent title means "not set", not
    # "mirrors the slug"; only rewrite it when it already exists and mirrors
    # the old slug, never invent one on a skill that never had it.
    if meta.get("title") is not None and meta.get("title") in (old_slug, old_slug_titled):
        meta["title"] = new_slug_titled

    meta["id"] = new_id
    meta["updatedAt"] = datetime.date.today().isoformat()
    body = _rewrite_prose(body, old_id, new_id, args, str(new_file))
    _write_md(new_file, meta, body)
    old_file.unlink()
    print(f"Renamed {old_file} to {new_file}")

    # Repoint suiteComponents / suiteRef references in every other named file.
    for p in named_dir.glob("**/*.md"):
        if p == new_file:
            continue
        pm, pb = _parse_md(p)
        changed = False
        comps = pm.get("suiteComponents")
        if isinstance(comps, list) and old_id in comps:
            pm["suiteComponents"] = [new_id if c == old_id else c for c in comps]
            changed = True
        if pm.get("suiteRef") == old_id:
            pm["suiteRef"] = new_id
            changed = True
        if changed:
            # A file that structurally references the renamed skill almost
            # always names it in prose too (install commands, cross-links).
            pb = _rewrite_prose(pb, old_id, new_id, args, str(p))
            _write_md(p, pm, pb)
            print(f"Updated suite references in {p}")

    # Suite manifests, user skill trees, and the stale-reference report.
    _update_shared_surfaces(args, old_id, new_id)

    append_skill_event(
        new_id,
        "rename",
        _get_contributor(),
        f"Renamed named skill from {old_id} to {new_id}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", True):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    print(f"Successfully renamed '{old_id}' to '{new_id}'.")


def meta_rename_command(args):
    _run_dev_preflights([
        lambda: preflightRenameCommand(args),
    ])
    registry_path = args.registry
    old_id = args.old_id.lstrip("/")
    new_id = args.new_id.lstrip("/")

    # Named-skill rename (contributor/slug) has a separate .md-based path.
    if "/" in old_id:
        _rename_named_skill(args, old_id, new_id)
        return

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
            pm, pb = _parse_md(p)
            rewritten = _rewrite_prose(pb, old_id, new_id, args, str(p))
            if rewritten != pb:
                _write_md(p, pm, rewritten)

    # Suite manifests, user skill trees, and the stale-reference report.
    _update_shared_surfaces(args, old_id, new_id)

    append_skill_event(
        new_id,
        "rename",
        _get_contributor(),
        f"Renamed from {old_id} to {new_id}",
        registry_path=registry_path,
    )

    if not getattr(args, "no_build", True):
        print("Regenerating registry and documentation...")
        _run_docs_build(args.registry)
    print(f"Successfully renamed '{old_id}' to '{new_id}'.")
