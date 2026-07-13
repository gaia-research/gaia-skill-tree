"""Registry-level dev fuse — Issue #926.

Creates/updates `registry/suites/<contributor>/<suite>.json` and optionally the
starless generic fusion node that acts as the taxonomic anchor for a named
capstone. Player-facing `gaia fuse` writes user-tree fuse events; this command
touches only registry-level structure and never mutates a user tree.

Usage
-----

    gaia dev fuse <generic-id> \\
      --name "Get Shit Done" \\
      --type ultimate \\
      --prereqs a,b,c,d \\
      --named-capstone gsd-build/get-shit-done \\
      --suite-components gsd-build/discuss-phase,gsd-build/plan-phase,...

The generic id (positional) is the starless anchor skill. Passing
--named-capstone additionally writes a suite manifest at
`registry/suites/<contributor>/<suite>.json` so `gaia dev docs` regeneration
picks up the suiteRef/suiteComponents links without stripping them.
"""

import json
import sys
import datetime
from pathlib import Path

from gaia_cli.registry import (
    registry_nodes_dir,
    named_skills_dir,
)
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _run_dev_preflights,
    _get_contributor,
    _run_docs_build,
    _find_named_file,
    _parse_md,
    _write_md,
    parseCommaSeparatedIds,
    _fail_dev_preflight,
)


VALID_TYPES = ("basic", "extra", "ultimate", "unique")


def _preflight_generic_id(generic_id: str) -> None:
    if not generic_id or "/" in generic_id:
        _fail_dev_preflight(
            f"Generic skill id must be a bare slug (no '/'); got {generic_id!r}.",
            fix="Use the starless anchor id, e.g. 'get-shit-done', not 'contributor/slug'.",
        )


def _preflight_type(skill_type: str) -> None:
    if skill_type not in VALID_TYPES:
        _fail_dev_preflight(
            f"--type must be one of {', '.join(VALID_TYPES)}; got {skill_type!r}.",
            fix="Choose ultimate/extra/unique/basic to fit the taxonomy of the fusion.",
        )


def _preflight_named_capstone(registry_path: str, capstone_id: str | None) -> None:
    if not capstone_id:
        return
    if "/" not in capstone_id:
        _fail_dev_preflight(
            f"--named-capstone must be a contributor/slug id; got {capstone_id!r}.",
            fix="Format the id as '<contributor>/<slug>' matching a named skill file.",
        )
    named_dir = Path(named_skills_dir(registry_path))
    if not _find_named_file(named_dir, capstone_id):
        _fail_dev_preflight(
            f"Named capstone '{capstone_id}' not found under {named_dir}.",
            fix="Create the capstone with `gaia dev add <name> --named --contributor <c>` first, "
                "or point --named-capstone at an existing named skill.",
        )


def _preflight_suite_components(registry_path: str, components: list[str]) -> None:
    if not components:
        return
    named_dir = Path(named_skills_dir(registry_path))
    for comp in components:
        if not _find_named_file(named_dir, comp):
            _fail_dev_preflight(
                f"Suite component '{comp}' does not exist as a named skill.",
                fix="Every entry in --suite-components must reference an existing "
                    "named skill under registry/named/. Add missing skills first.",
            )


def _preflight_prereqs_exist(registry_path: str, prereqs: list[str]) -> None:
    if not prereqs:
        return
    nodes_dir = Path(registry_nodes_dir(registry_path))
    known_ids = set()
    for p in nodes_dir.glob("**/*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        node_id = data.get("id")
        if node_id:
            known_ids.add(node_id)
    for prereq in prereqs:
        if prereq not in known_ids:
            _fail_dev_preflight(
                f"Prerequisite '{prereq}' is not a known generic skill id.",
                fix=f"Add the prerequisite first via `gaia dev add {prereq}`, "
                    "or drop it from --prereqs.",
            )


def _generic_node_exists(nodes_dir: Path, generic_id: str) -> bool:
    for p in nodes_dir.glob("**/*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("id") == generic_id:
            return True
    return False


def _preflight_create_requirements(registry_path: str, generic_id: str,
                                   name: str | None, description: str | None) -> None:
    """If the generic node doesn't exist, --name and valid --description are required."""
    nodes_dir = Path(registry_nodes_dir(registry_path))
    if _generic_node_exists(nodes_dir, generic_id):
        return
    if not name:
        _fail_dev_preflight(
            f"Generic node '{generic_id}' does not exist yet — --name is required to create it.",
            fix="Pass --name \"Human Readable Name\" so the new fusion node has a display label.",
        )
    if not description or len(description.strip()) < 10:
        _fail_dev_preflight(
            f"Generic node '{generic_id}' does not exist yet — --description (>=10 chars) is required to create it.",
            fix="Pass --description \"...\" to seed a schema-valid skill.",
        )


def _load_or_create_generic_node(nodes_dir: Path, generic_id: str, skill_type: str,
                                 name: str | None, description: str | None) -> tuple[Path, dict, bool]:
    """Return (file_path, node_data, created_new). Prefer existing node; else create.

    Preflights guarantee name/description are provided when creating; here we
    trust that contract.
    """
    for p in nodes_dir.glob("**/*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("id") == generic_id:
            return p, data, False

    dest_dir = nodes_dir / skill_type
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / f"{generic_id}.json"
    data = {
        "id": generic_id,
        "name": name,
        "type": skill_type,
        "description": description.strip(),
        "prerequisites": [],
        "derivatives": [],
        "evidence": [],
        "knownAgents": [],
        "status": "provisional",
        "createdAt": datetime.date.today().isoformat(),
        "updatedAt": datetime.date.today().isoformat(),
        "version": "0.1.0",
    }
    return dest_file, data, True


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _upsert_suite_manifest(registry_path: str,
                           capstone_id: str,
                           components: list[str],
                           suite_name: str | None,
                           suite_description: str | None) -> tuple[Path, bool]:
    """Create or update registry/suites/<contributor>/<slug>.json.

    Returns (path, created_new). The manifest 'id' matches the capstone id and
    the file layout mirrors the existing suites we ship (see registry/suites/gsd-build/get-shit-done.json).
    """
    contributor, slug = capstone_id.split("/", 1)
    suites_dir = Path(registry_path) / "registry" / "suites" / contributor
    dest_file = suites_dir / f"{slug}.json"

    today = datetime.date.today().isoformat()

    if dest_file.exists():
        try:
            data = json.loads(dest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"Error: Existing suite manifest {dest_file} is not valid JSON: {exc}.\n"
                f"Fix the malformed JSON by hand, or remove the file and re-run.",
                file=sys.stderr,
            )
            sys.exit(1)
        created_new = False
    else:
        data = {
            "id": capstone_id,
            "name": suite_name or capstone_id.split("/", 1)[1].replace("-", " ").title(),
            "contributor": contributor,
            "description": suite_description or "",
            "version": "1.0.0",
            "capstone": capstone_id,
            "suites": [],
            "standalones": [],
            "createdAt": today,
        }
        created_new = True

    # Overwrite fields that this dev-fuse invocation owns.
    if suite_name:
        data["name"] = suite_name
    if suite_description:
        data["description"] = suite_description
    data["capstone"] = capstone_id
    # For the flat-suite shape (no sub-suites), members go into standalones.
    # Preserve any pre-existing sub-suite structure so mattpocock/skills-style
    # manifests can be augmented without losing their sub-suite grouping.
    if not data.get("suites"):
        data["standalones"] = sorted(set(components))
    else:
        # Manifest already has structured sub-suites — leave 'suites' alone and
        # only merge new components into standalones, preserving order.
        existing = list(data.get("standalones", []))
        for c in components:
            if c not in existing:
                existing.append(c)
        data["standalones"] = existing

    data["updatedAt"] = today
    _write_json(dest_file, data)
    return dest_file, created_new


def meta_dev_fuse_command(args) -> None:
    """Registry-level fusion / suite command. See module docstring."""
    registry_path = args.registry
    generic_id = args.generic_id.lstrip("/")
    skill_type = getattr(args, "type", None) or "ultimate"
    name = getattr(args, "name", None)
    description = getattr(args, "description", None)

    prereqs = parseCommaSeparatedIds(args.prereqs, "prerequisite") if getattr(args, "prereqs", None) else []
    components = parseCommaSeparatedIds(args.suite_components, "suite component") if getattr(args, "suite_components", None) else []
    capstone_id = getattr(args, "named_capstone", None)

    _run_dev_preflights([
        lambda: _preflight_generic_id(generic_id),
        lambda: _preflight_type(skill_type),
        lambda: _preflight_create_requirements(registry_path, generic_id, name, description),
        lambda: _preflight_prereqs_exist(registry_path, prereqs),
        lambda: _preflight_named_capstone(registry_path, capstone_id),
        lambda: _preflight_suite_components(registry_path, components),
    ])

    # ── 1) Upsert the generic fusion node.
    nodes_dir = Path(registry_nodes_dir(registry_path))
    node_file, node_data, created_new_node = _load_or_create_generic_node(
        nodes_dir, generic_id, skill_type, name, description
    )
    # Merge prerequisites (dedup while preserving existing order).
    existing_prereqs = list(node_data.get("prerequisites") or [])
    for p in prereqs:
        if p not in existing_prereqs:
            existing_prereqs.append(p)
    node_data["prerequisites"] = existing_prereqs
    # Repair the invalid legacy action emitted by earlier versions of this
    # command. Timeline actions are schema-constrained; `note` is not valid.
    for event in node_data.get("timeline") or []:
        if (
            event.get("action") == "note"
            and "via `gaia dev fuse`" in str(event.get("details", ""))
        ):
            event["action"] = "fuse"
    if name:
        node_data["name"] = name
    if description:
        node_data["description"] = description.strip()
    # Re-type if this invocation overrides.
    if getattr(args, "type", None):
        node_data["type"] = skill_type
    node_data["updatedAt"] = datetime.date.today().isoformat()
    _write_json(node_file, node_data)
    if created_new_node:
        print(f"Created generic fusion node: {node_file}")
        append_skill_event(
            generic_id, "add", _get_contributor(),
            f"Created generic fusion node '{generic_id}' via `gaia dev fuse`.",
            registry_path=registry_path,
        )
    else:
        print(f"Updated generic fusion node: {node_file}")
    if prereqs:
        append_skill_event(
            generic_id, "fuse", _get_contributor(),
            f"Set prerequisites via `gaia dev fuse`: {', '.join(prereqs)}.",
            registry_path=registry_path,
        )

    # ── 2) If a named capstone is specified, write the suite manifest and
    #       stamp the named-capstone's frontmatter suiteRef / genericSkillRef.
    if capstone_id:
        named_dir = Path(named_skills_dir(registry_path))
        capstone_file = _find_named_file(named_dir, capstone_id)
        if not capstone_file:
            # Preflight should have caught this; guard defensively.
            print(f"Error: Named capstone '{capstone_id}' not found after preflight.", file=sys.stderr)
            sys.exit(1)
        cap_meta, cap_body = _parse_md(capstone_file)
        cap_changed = False
        if cap_meta.get("genericSkillRef") != generic_id:
            cap_meta["genericSkillRef"] = generic_id
            cap_changed = True
        if cap_meta.get("suiteRef") != capstone_id:
            cap_meta["suiteRef"] = capstone_id
            cap_changed = True
        if components:
            existing_comps = list(cap_meta.get("suiteComponents") or [])
            merged = list(existing_comps)
            for c in components:
                if c not in merged:
                    merged.append(c)
            if merged != existing_comps:
                cap_meta["suiteComponents"] = merged
                cap_changed = True
        if cap_changed:
            cap_meta["updatedAt"] = datetime.date.today().isoformat()
            _write_md(capstone_file, cap_meta, cap_body)
            print(f"Updated capstone frontmatter: {capstone_file}")
            append_skill_event(
                capstone_id, "suite_ref_set", _get_contributor(),
                f"Set suiteRef={capstone_id}, genericSkillRef={generic_id} via `gaia dev fuse`.",
                registry_path=registry_path,
            )

        # 3) Write the suite manifest.
        manifest_file, created_new_manifest = _upsert_suite_manifest(
            registry_path, capstone_id, components,
            name, description,
        )
        if created_new_manifest:
            print(f"Created suite manifest: {manifest_file}")
        else:
            print(f"Updated suite manifest: {manifest_file}")

    # ── 4) Regenerate docs unless --no-build.
    if not getattr(args, "no_build", False):
        print("Regenerating registry and documentation...")
        _run_docs_build(registry_path)
    else:
        print("Skipping documentation rebuild as requested (--no-build).")
