import datetime
import sys
from pathlib import Path

from gaia_cli.registry import named_skills_dir
from gaia_cli.timeline import append_skill_event
from gaia_cli.commands.dev.helpers import (
    _parse_md,
    _write_md,
    _get_contributor,
    _run_docs_build,
    _run_dev_preflights,
    _fail_dev_preflight,
    _find_named_file,
)

def preflightRenameNamedCommand(args) -> None:
    registryPath = args.registry
    oldId = getattr(args, "old_id", "").strip()
    newId = getattr(args, "new_id", "").strip()

    if oldId == newId:
        _fail_dev_preflight(
            f"Cannot rename named skill '{oldId}' to itself.",
            fix="Choose a distinct new ID.",
        )
    
    if oldId.count("/") != 1 or not all(oldId.split("/")):
        _fail_dev_preflight(
            f"Old skill ID '{oldId}' is invalid.",
            fix="Use a valid contributor/slug format.",
        )
        
    if newId.count("/") != 1 or not all(newId.split("/")):
        _fail_dev_preflight(
            f"New skill ID '{newId}' is invalid.",
            fix="Use a valid contributor/slug format.",
        )
        
    namedDir = Path(named_skills_dir(registryPath))
    
    oldPath = _find_named_file(namedDir, oldId)
    if not oldPath:
        _fail_dev_preflight(f"Named skill '{oldId}' not found.")
        
    newPath = _find_named_file(namedDir, newId)
    if newPath:
        _fail_dev_preflight(
            f"Skill with id '{newId}' already exists in registry.",
            fix="Choose a new ID or remove the stale file before renaming."
        )
        
    new_slug = newId.split("/")[1]
    contributor = newId.split("/")[0]
    expectedPath = namedDir / contributor / f"{new_slug}.md"
    if expectedPath.exists():
        _fail_dev_preflight(
            f"'{newId}' already exists on disk at {expectedPath}.",
            fix="Choose a new ID or remove the stale file before renaming.",
        )

def meta_rename_named_command(args):
    _run_dev_preflights([
        lambda: preflightRenameNamedCommand(args),
    ])
    
    registry_path = args.registry
    old_id = args.old_id.strip()
    new_id = args.new_id.strip()
    
    named_dir = Path(named_skills_dir(registry_path))
    old_file = _find_named_file(named_dir, old_id)
    
    if not old_file:
        print(f"Error: Named skill '{old_id}' not found.")
        sys.exit(1)
        
    new_contributor, new_slug = new_id.split("/")
    new_file = named_dir / new_contributor / f"{new_slug}.md"
    
    if new_file.exists():
        print(f"Error: '{new_id}' already exists on disk at {new_file}. Rename aborted.")
        sys.exit(1)
        
    new_file.parent.mkdir(parents=True, exist_ok=True)
    
    meta, body = _parse_md(old_file)
    meta["id"] = new_id
    meta["catalogRef"] = new_id.replace("/", "-")
    meta["updatedAt"] = datetime.date.today().isoformat()
    
    _write_md(new_file, meta, body)
    old_file.unlink()
    
    print(f"Renamed {old_file} to {new_file}")
    
    # Update references in all other named nodes
    for p in named_dir.glob("**/*.md"):
        if p.resolve() == new_file.resolve():
            continue
            
        m, b = _parse_md(p)
        changed = False
        
        if "suiteComponents" in m and isinstance(m["suiteComponents"], list):
            if old_id in m["suiteComponents"]:
                m["suiteComponents"] = [
                    new_id if c == old_id else c for c in m["suiteComponents"]
                ]
                changed = True
                
        if m.get("suiteRef") == old_id:
            m["suiteRef"] = new_id
            changed = True
            
        if m.get("genericSkillRef") == old_id:
            m["genericSkillRef"] = new_id
            changed = True
            
        if changed:
            _write_md(p, m, b)
            print(f"Updated references in {p}")

    append_skill_event(
        new_id,
        "rename",
        _get_contributor(),
        f"Renamed from {old_id} to {new_id}",
        registry_path=registry_path,
    )
    
    print("Regenerating registry and documentation...")
    _run_docs_build(registry_path)
    print(f"Successfully renamed '{old_id}' to '{new_id}'.")
