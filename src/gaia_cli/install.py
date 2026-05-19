"""Named skill install, sync, and uninstall logic.

Manages a dual-layer cache:
- Global: $GAIA_HOME/skills/{contributor}/{skill-name}.md (defaults to ~/.gaia)
- Repo:   .gaia/named-skills/{contributor}/{skill-name}.md (symlink on Unix, copy on Windows)
"""

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

from gaia_cli.registry import named_skills_dir, registry_graph_path


def get_gaia_home():
    return os.path.abspath(
        os.path.expanduser(os.environ.get("GAIA_HOME", os.path.join("~", ".gaia")))
    )


def get_global_cache_dir():
    return os.path.join(get_gaia_home(), "skills")


def get_repo_skills_dir():
    return os.path.join(".gaia", "named-skills")


def get_manifest_path():
    return os.path.join(".gaia", "install-manifest.json")


def load_manifest():
    path = get_manifest_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"installed": []}


def save_manifest(manifest):
    path = get_manifest_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)


def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def find_named_skill_source(skill_id, registry_path):
    parts = skill_id.split("/", 1)
    if len(parts) != 2:
        return None
    contributor, skill_name = parts
    source = os.path.join(named_skills_dir(registry_path), contributor, f"{skill_name}.md")
    if os.path.exists(source):
        return source
    return None


def _named_skill_source_for_id(skill_id, registry_path):
    contributor, skill_name = skill_id.split("/", 1)
    return os.path.join(named_skills_dir(registry_path), contributor, f"{skill_name}.md")


def resolve_named_skill_reference(skill_ref, registry_path):
    """Resolve an install reference to (canonical_id, source_path).

    Accepted references, in order:
    - exact named skill ID: contributor/skill-name
    - exact catalogRef frontmatter slug
    - unique bare skill-name slug
    """
    skill_ref = skill_ref.lstrip("/")
    source = find_named_skill_source(skill_ref, registry_path)
    if source:
        return skill_ref, source

    available = list_available(registry_path)
    catalog_matches = [
        (skill_id, _named_skill_source_for_id(skill_id, registry_path))
        for skill_id, meta in available
        if meta.get("catalogRef") == skill_ref
    ]
    if len(catalog_matches) == 1:
        return catalog_matches[0]
    if len(catalog_matches) > 1:
        ids = ", ".join(skill_id for skill_id, _ in catalog_matches)
        raise ValueError(f"ambiguous skill slug '{skill_ref}' matches: {ids}")

    bare_matches = [
        (skill_id, _named_skill_source_for_id(skill_id, registry_path))
        for skill_id, _meta in available
        if skill_id.split("/", 1)[1] == skill_ref
    ]
    if len(bare_matches) == 1:
        return bare_matches[0]
    if len(bare_matches) > 1:
        ids = ", ".join(skill_id for skill_id, _ in bare_matches)
        raise ValueError(f"ambiguous skill slug '{skill_ref}' matches: {ids}")

    return None


def install_skill(skill_id, registry_path):
    try:
        resolved = resolve_named_skill_reference(skill_id, registry_path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return False

    if not resolved:
        print(f"Error: Named skill or slug '{skill_id}' not found in registry.", file=sys.stderr)
        return False

    skill_id, source = resolved
    if not source:
        print(f"Error: Named skill or slug '{skill_id}' not found in registry.", file=sys.stderr)
        return False

    parts = skill_id.split("/", 1)
    contributor, skill_name = parts

    global_dir = os.path.join(get_global_cache_dir(), contributor)
    os.makedirs(global_dir, exist_ok=True)
    global_path = os.path.join(global_dir, f"{skill_name}.md")
    shutil.copy2(source, global_path)

    repo_dir = os.path.join(get_repo_skills_dir(), contributor)
    os.makedirs(repo_dir, exist_ok=True)
    repo_path = os.path.join(repo_dir, f"{skill_name}.md")

    if sys.platform != "win32":
        if os.path.exists(repo_path) or os.path.islink(repo_path):
            os.remove(repo_path)
        os.symlink(os.path.abspath(global_path), repo_path)
    else:
        shutil.copy2(global_path, repo_path)

    manifest = load_manifest()
    sha = compute_sha256(global_path)
    existing = next((s for s in manifest["installed"] if s["id"] == skill_id), None)
    if existing:
        existing["sha256"] = sha
        existing["installedAt"] = datetime.now(timezone.utc).isoformat()
    else:
        manifest["installed"].append({
            "id": skill_id,
            "installedAt": datetime.now(timezone.utc).isoformat(),
            "sourceRef": f"registry/named/{contributor}/{skill_name}.md",
            "sha256": sha,
        })
    save_manifest(manifest)
    print(f"Installed: {skill_id}")
    return True


def install_ultimate(named_skill_ref: str, registry_path: str) -> bool:
    """Batch-install all named prerequisite skills for an ultimate fusion chain."""
    result = resolve_named_skill_reference(named_skill_ref, registry_path)
    if not result:
        print(f"Error: could not resolve '{named_skill_ref}'", file=sys.stderr)
        return False
    skill_id, source_path = result

    # Read frontmatter from the named skill file
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"Error reading {source_path}: {e}", file=sys.stderr)
        return False

    # Minimal frontmatter parse: extract key: value lines between --- delimiters
    fm = {}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
        if end:
            for line in lines[1:end]:
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip('"').strip("'")

    generic_ref = fm.get("genericSkillRef", "")
    if not generic_ref:
        print(f"Error: '{skill_id}' has no genericSkillRef.", file=sys.stderr)
        return False

    # Load registry graph
    try:
        graph_file = os.path.join(registry_path, "registry", "gaia.json")
        if not os.path.exists(graph_file):
            graph_file = registry_graph_path(registry_path)
        with open(graph_file, "r", encoding="utf-8") as f:
            import json as _json
            graph = _json.load(f)
    except (OSError, ValueError) as e:
        print(f"Error loading registry: {e}", file=sys.stderr)
        return False

    abstract = next((s for s in graph.get("skills", []) if s.get("id") == generic_ref), None)
    if not abstract:
        print(f"Error: abstract skill '{generic_ref}' not found in registry.", file=sys.stderr)
        return False
    if abstract.get("type") != "ultimate":
        print(f"Error: '{generic_ref}' is not an ultimate skill. Use --ultimate only for ultimate named skills.", file=sys.stderr)
        return False

    prerequisites = abstract.get("prerequisites", [])

    # Build named map: genericSkillRef -> named skill id
    named_map = {}
    nd = named_skills_dir(registry_path)
    import glob as _glob
    for fp in _glob.glob(os.path.join(nd, "**", "*.md"), recursive=True):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                md_text = f.read()
            md_lines = md_text.splitlines()
            if md_lines and md_lines[0].strip() == "---":
                md_end = next((i for i, l in enumerate(md_lines[1:], 1) if l.strip() == "---"), None)
                if md_end:
                    entry_fm = {}
                    for line in md_lines[1:md_end]:
                        if ":" in line:
                            k, _, v = line.partition(":")
                            entry_fm[k.strip()] = v.strip().strip('"').strip("'")
                    ref = entry_fm.get("genericSkillRef", "")
                    eid = entry_fm.get("id", "")
                    if ref and eid:
                        named_map[ref] = eid
        except OSError:
            continue

    # Install prerequisite named skills
    print(f"\nInstalling prerequisites for {skill_id} ({len(prerequisites)} skills)...")
    installed = 0
    for prereq_id in prerequisites:
        named_ref = named_map.get(prereq_id)
        if named_ref:
            print(f"  Installing {named_ref} ({prereq_id})...")
            install_skill(named_ref, registry_path)
            installed += 1
        else:
            print(f"  Skipping {prereq_id} — no named implementation available")

    # Install the ultimate itself
    print(f"\nInstalling ultimate: {skill_id}...")
    install_skill(named_skill_ref, registry_path)

    print(f"\n✓ Installed {installed + 1} skills for the {abstract.get('name', skill_id)} suite.")
    return True


def sync_skills(registry_path):
    manifest = load_manifest()
    if not manifest["installed"]:
        print("No named skills installed.")
        return

    updated = 0
    for entry in manifest["installed"]:
        skill_id = entry["id"]
        source = find_named_skill_source(skill_id, registry_path)
        if not source:
            print(f"  Warning: Source not found for {skill_id}")
            continue

        new_sha = compute_sha256(source)
        if new_sha != entry.get("sha256"):
            install_skill(skill_id, registry_path)
            updated += 1
        else:
            print(f"  Up to date: {skill_id}")

    print(f"\nSync complete. {updated} skill(s) updated.")


def uninstall_skill(skill_id):
    skill_id = skill_id.lstrip("/")
    parts = skill_id.split("/", 1)
    if len(parts) != 2:
        print("Error: Invalid skill ID format. Expected 'contributor/skill-name'.", file=sys.stderr)
        return False
    contributor, skill_name = parts

    repo_path = os.path.join(get_repo_skills_dir(), contributor, f"{skill_name}.md")
    if os.path.exists(repo_path) or os.path.islink(repo_path):
        os.remove(repo_path)

    manifest = load_manifest()
    manifest["installed"] = [s for s in manifest["installed"] if s["id"] != skill_id]
    save_manifest(manifest)
    print(f"Uninstalled: {skill_id}")
    return True


def _parse_frontmatter(path):
    """Return the YAML frontmatter dict from a .md file, or {}."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            return {}
        try:
            import yaml
            return yaml.safe_load(m.group(1)) or {}
        except ImportError:
            # Fallback when PyYAML is not installed
            res = {}
            for line in m.group(1).split('\n'):
                line = line.strip()
                if not line or line.startswith('#'): continue
                if ':' in line:
                    k, v = line.split(':', 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if v.lower() == 'true': v = True
                    elif v.lower() == 'false': v = False
                    res[k] = v
            return res
    except Exception:
        return {}


def list_available(registry_path):
    """Return a sorted list of (skill_id, meta_dict) for all named skills in the registry."""
    named_dir = named_skills_dir(registry_path)
    if not os.path.isdir(named_dir):
        return []
    skills = []
    for contributor in sorted(os.listdir(named_dir)):
        contrib_dir = os.path.join(named_dir, contributor)
        if not os.path.isdir(contrib_dir):
            continue
        for fname in sorted(os.listdir(contrib_dir)):
            if not fname.endswith(".md"):
                continue
            skill_name = fname[:-3]
            skill_id = f"{contributor}/{skill_name}"
            meta = _parse_frontmatter(os.path.join(contrib_dir, fname))
            skills.append((skill_id, meta))
    return skills


def interactive_install(registry_path):
    """Display all available named skills and let the user pick which to install."""
    skills = list_available(registry_path)
    if not skills:
        print("No named skills found in registry.")
        return

    installed_ids = {e["id"] for e in load_manifest()["installed"]}

    print(f"\n{'#':<4} {'ID':<40} {'Name':<30} Lvl")
    print("─" * 85)
    for i, (sid, meta) in enumerate(skills, 1):
        name = meta.get("name") or sid.split("/", 1)[-1]
        level = meta.get("level", "?")
        marker = " ✓" if sid in installed_ids else "  "
        print(f"{i:<4}{marker} {sid:<38} {name:<30} {level}")

    print("\n✓ = already installed")
    print("Enter numbers to install (space or comma separated), or press Enter to cancel:")
    try:
        raw = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if not raw:
        print("Cancelled.")
        return

    tokens = re.split(r"[\s,]+", raw)
    selected = []
    for tok in tokens:
        if not tok:
            continue
        try:
            idx = int(tok) - 1
            if 0 <= idx < len(skills):
                selected.append(skills[idx][0])
            else:
                print(f"  Skipping out-of-range: {tok}")
        except ValueError:
            print(f"  Skipping invalid input: {tok}")

    if not selected:
        print("Nothing selected.")
        return

    print()
    for sid in selected:
        install_skill(sid, registry_path)


def list_installed():
    manifest = load_manifest()
    if not manifest["installed"]:
        print("No named skills installed.")
        return

    print(f"{'ID':<35} {'Installed':<25} {'SHA-256 (short)'}")
    print("-" * 75)
    for entry in manifest["installed"]:
        sha_short = entry.get("sha256", "unknown")[:12]
        print(f"{entry['id']:<35} {entry['installedAt'][:19]:<25} {sha_short}")
