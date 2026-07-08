"""Named skill install, sync, and uninstall logic.

Fetches skills directly from source repositories (GitHub) and installs them
into agent-accessible directories (.agents/skills or .claude/skills).
Supports explicit suite dependencies and recursive installation.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from gaia_cli.registry import named_skills_dir
from gaia_cli.formatting import _fg, _reset, get_harness_color
from gaia_cli.windowsLinks import makeLink, isLinkOrJunction


def get_gaia_home():
    return os.path.abspath(
        os.path.expanduser(os.environ.get("GAIA_HOME", os.path.join("~", ".gaia")))
    )


def get_global_cache_dir():
    return os.path.join(get_gaia_home(), "skills")


def get_repo_skills_dir(location: str = "local") -> str:
    """Return the target agent skills directory.

    Args:
        location: "local" (project-relative .agents/.claude) or "global" (~/.gaia/skills)

    Returns:
        Absolute path to the skills directory.

    Raises:
        ValueError: If location is not "local" or "global"
    """
    if location not in ("local", "global"):
        raise ValueError(f"Invalid location '{location}'; must be 'local' or 'global'")

    if location == "global":
        return os.path.join(get_gaia_home(), "skills")

    # Local: project-relative (.agents/.claude)
    if os.path.isdir(".agents"):
        return os.path.abspath(".agents/skills")
    if os.path.isdir(".claude"):
        return os.path.abspath(".claude/skills")
    # Default to .agents/skills if neither exist (will be created)
    return os.path.abspath(".agents/skills")


def get_manifest_path():
    return os.path.join(".gaia", "install-manifest.json")


def load_manifest():
    path = get_manifest_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"installed": []}


def save_manifest(manifest):
    path = get_manifest_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _parse_github_url(url: str) -> tuple[str, str, str]:
    """Parse a GitHub URL into (repo_url, branch, subpath).

    Examples:
    - https://github.com/owner/repo -> (https://github.com/owner/repo.git, None, "")
    - https://github.com/owner/repo/blob/main/path/to/skill.md -> (https://github.com/owner/repo.git, main, path/to)
    - https://github.com/owner/repo/tree/main/path/to/skill -> (https://github.com/owner/repo.git, main, path/to/skill)
    """
    url = url.rstrip("/")
    # Pattern for blob URLs: https://github.com/owner/repo/blob/branch/path
    blob_match = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)", url)
    if blob_match:
        owner, repo, branch, path = blob_match.groups()
        repo_url = f"https://github.com/{owner}/{repo}.git"
        # If path is to a file, take the directory
        if path.endswith(".md"):
            subpath = os.path.dirname(path)
        else:
            subpath = path
        return repo_url, branch, subpath

    # Pattern for tree URLs: https://github.com/owner/repo/tree/branch[/path]
    # tree/ paths always refer to directories — use the path verbatim (no dirname step).
    # This is a common curator copy-paste mistake; handle it correctly rather than
    # silently falling through to the bare-repo pattern and dropping the subpath.
    tree_match = re.match(r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(.*)", url)
    if tree_match:
        owner, repo, branch, path = tree_match.groups()
        repo_url = f"https://github.com/{owner}/{repo}.git"
        subpath = path.lstrip("/")  # strip leading slash; empty string = repo root
        return repo_url, branch, subpath

    # Pattern for base repo: https://github.com/owner/repo
    repo_match = re.match(r"https://github\.com/([^/]+)/([^/]+)", url)
    if repo_match:
        owner, repo = repo_match.groups()
        repo_url = f"https://github.com/{owner}/{repo}.git"
        return repo_url, None, ""

    return url, None, ""


def _run_git(args: list[str], cwd: str | None = None) -> bool:
    """Run a git command and stream output to stdout."""
    try:
        subprocess.run(["git"] + args, cwd=cwd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}", file=sys.stderr)
        return False


def resolve_named_skill_reference(skill_ref, registry_path):
    """Resolve an install reference to (canonical_id, meta_dict)."""
    skill_ref = skill_ref.lstrip("/")
    available = list_available(registry_path)
    
    # 1. Exact ID match (contributor/skill-name)
    for sid, meta in available:
        if sid == skill_ref:
            return sid, meta

    # 2. catalogRef match
    catalog_matches = [(sid, meta) for sid, meta in available if meta.get("catalogRef") == skill_ref]
    if len(catalog_matches) == 1: return catalog_matches[0]
    if len(catalog_matches) > 1:
        raise ValueError(f"Ambiguous slug '{skill_ref}' matches multiple skills.")

    # 3. Bare skill-name match
    bare_matches = [(sid, meta) for sid, meta in available if sid.split("/", 1)[1] == skill_ref]
    if len(bare_matches) == 1: return bare_matches[0]
    if len(bare_matches) > 1:
        raise ValueError(f"Ambiguous bare name '{skill_ref}' matches multiple skills.")

    return None, None


def _install_single(sid: str, meta: dict, registry_path: str, visited: set[str], location: str = "local") -> bool:
    """Clone/symlink a single skill entry, bypassing suite-component detection.

    Called by both install_skill (for non-suite skills) and install_suite (for
    the optional suite-root artifact that has its own links.github). Using this
    helper in install_suite avoids infinite recursion that would arise if we
    called install_skill(sid) there — install_skill would detect suiteComponents
    and re-enter install_suite.

    Args:
        location: "local" (default, .agents/.claude) or "global" (~/.gaia/skills)
    """
    links = meta.get("links", {}) if isinstance(meta, dict) else {}
    github_url = links.get("github") if isinstance(links, dict) else None
    if not github_url:
        print(f"Error: Skill '{sid}' has no source repository link.", file=sys.stderr)
        return False

    repo_url, branch, subpath = _parse_github_url(github_url)
    owner = sid.split("/", 1)[0]
    repo_name = repo_url.split("/")[-1].replace(".git", "")

    # 1. Clone/Fetch to global cache
    global_cache = os.path.join(get_global_cache_dir(), owner, repo_name)
    if not os.path.exists(global_cache):
        print(f"Cloning {repo_url}...")
        os.makedirs(os.path.dirname(global_cache), exist_ok=True)
        args = ["clone", "--single-branch", "--depth", "1"]
        if branch:
            args += ["-b", branch]
        args += [repo_url, global_cache]
        if not _run_git(args):
            return False
    else:
        print(f"Updating {repo_name}...")
        _run_git(["pull"], cwd=global_cache)

    # 2. Symlink to target agent directory
    target_dir = get_repo_skills_dir(location=location)
    os.makedirs(target_dir, exist_ok=True)

    skill_slug = sid.split("/", 1)[1]
    local_skill_path = os.path.join(target_dir, skill_slug)

    source_skill_path = os.path.join(global_cache, subpath)

    if os.path.exists(local_skill_path) or os.path.islink(local_skill_path) or isLinkOrJunction(local_skill_path):
        if os.path.islink(local_skill_path) or isLinkOrJunction(local_skill_path):
            try:
                os.remove(local_skill_path)
            except OSError:
                # Junction removal on Windows may need rmdir-style handling
                os.rmdir(local_skill_path)
        else:
            shutil.rmtree(local_skill_path)

    h_color = get_harness_color(local_skill_path)
    print(f"Installing {sid} to {_fg(*h_color)}{local_skill_path}{_reset()}...")
    try:
        mechanism = makeLink(source_skill_path, local_skill_path)
        if mechanism != "symlink":
            print(f"  (used {mechanism} fallback on this platform)")
    except OSError as e:
        # Last-resort: copy. Preserves Windows behavior from before this
        # module existed, so a totally locked-down host still installs.
        print(
            f"  Link creation failed ({e}); falling back to copy.",
            file=sys.stderr,
        )
        if os.path.isdir(source_skill_path):
            shutil.copytree(source_skill_path, local_skill_path)
        else:
            shutil.copy2(source_skill_path, local_skill_path)

    # 3. Update manifest and clean up old installation if location changed
    manifest = load_manifest()
    existing = next((s for s in manifest["installed"] if s["id"] == sid), None)
    entry = {
        "id": sid,
        "installedAt": datetime.now(timezone.utc).isoformat(),
        "repoUrl": repo_url,
        "subpath": subpath,
        "localPath": local_skill_path,
        "location": location,
    }
    if existing:
        # If reinstalling with different location, clean up old path
        old_path = existing.get("localPath")
        old_location = existing.get("location", "local")
        if old_path and old_location != location and (os.path.exists(old_path) or os.path.islink(old_path) or isLinkOrJunction(old_path)):
            try:
                if os.path.islink(old_path) or isLinkOrJunction(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        os.rmdir(old_path)
                elif os.path.isdir(old_path):
                    shutil.rmtree(old_path)
                else:
                    os.remove(old_path)
            except Exception as e:
                print(f"Warning: could not remove old installation at {old_path}: {e}", file=sys.stderr)
        existing.update(entry)
    else:
        manifest["installed"].append(entry)
    save_manifest(manifest)

    print(f"✓ Installed: {sid}")
    return True


def install_skill(skill_id: str, registry_path: str, visited: set[str] | None = None, location: str = "local") -> bool:
    """Install a skill by fetching from source and linking to agent directory.

    Args:
        location: "local" (default, .agents/.claude) or "global" (~/.gaia/skills)
    """
    if visited is None:
        visited = set()
    if skill_id in visited:
        return True
    visited.add(skill_id)

    sid, meta = resolve_named_skill_reference(skill_id, registry_path)
    if not sid:
        print(f"Error: Skill '{skill_id}' not found in registry.", file=sys.stderr)
        return False

    # Check for suite components
    suite_components = meta.get("suiteComponents", [])
    # Fallback to prerequisites for Ultimates if suiteComponents is missing
    if not suite_components and meta.get("ultimate"):
        # We'd need to load gaia.json to find generic prerequisites.
        # But per plan, we prefer explicit suiteComponents.
        pass

    if suite_components:
        return install_suite(sid, registry_path, visited, location=location)

    return _install_single(sid, meta, registry_path, visited, location=location)


def install_suite(suite_id: str, registry_path: str, visited: set[str] | None = None, location: str = "local") -> bool:
    """Recursive installation of a skill suite and its components.

    Returns True only when every component (and the suite root, if it has its
    own links.github) installs successfully. Partial or total failures cause
    a False return and a summary listing the failed component IDs.

    Args:
        location: "local" (default, .agents/.claude) or "global" (~/.gaia/skills)
    """
    if visited is None:
        visited = set()

    sid, meta = resolve_named_skill_reference(suite_id, registry_path)
    if not sid:
        return False

    components = meta.get("suiteComponents", [])
    if not components:
        # If no explicit components, treat it as a regular skill
        github_url = meta.get("links", {}).get("github")
        if github_url:
            return install_skill(sid, registry_path, visited, location=location)
        return False

    print(f"\nInstalling suite: {sid} ({len(components)} components)...")
    success_count = 0
    failed: list[str] = []
    has_nested_suite_failure = False
    for comp_id in components:
        # Check if the component is itself a suite so we can annotate failures clearly.
        _, comp_meta = resolve_named_skill_reference(comp_id, registry_path)
        comp_is_suite = bool(
            comp_meta and comp_meta.get("suiteComponents")
        ) if comp_meta else False

        if install_skill(comp_id, registry_path, visited, location=location):
            success_count += 1
        else:
            if comp_is_suite:
                failed.append(f"{comp_id} (nested suite — see above)")
                has_nested_suite_failure = True
            else:
                failed.append(comp_id)

    # Install the suite root itself if it has its own github source.
    # Use _install_single directly to bypass suite-component detection and
    # avoid re-entering install_suite (which would cause infinite recursion).
    root_ok = True
    root_attempted = False
    if meta.get("links", {}).get("github"):
        root_attempted = True
        root_ok = _install_single(sid, meta, registry_path, visited, location=location)
        if not root_ok:
            failed.append(sid)

    total = len(components) + (1 if root_attempted else 0)
    achieved = success_count + (1 if root_attempted and root_ok else 0)

    if failed:
        print(
            f"\n⚠ Suite {sid}: {achieved}/{total} installed. "
            f"Failed: {', '.join(failed)}",
            file=sys.stderr,
        )
        if has_nested_suite_failure:
            print(
                "  (nested-suite failures listed their own component summaries above.)",
                file=sys.stderr,
            )
        return False

    print(f"\n✓ Suite {sid} complete: {achieved}/{total} component(s) installed.")
    return True


def update_skills(registry_path: str):
    """Update all installed skills by pulling from remote sources."""
    manifest = load_manifest()
    if not manifest["installed"]:
        print("No skills installed.")
        return

    # Group by repo to avoid redundant pulls
    repos = {}
    for entry in manifest["installed"]:
        repo_url = entry.get("repoUrl")
        if not repo_url: continue
        
        # Determine global cache path for this repo
        owner = entry["id"].split("/", 1)[0]
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        global_cache = os.path.join(get_global_cache_dir(), owner, repo_name)
        repos[global_cache] = repo_name

    print(f"Checking for updates in {len(repos)} repositories...")
    updated = 0
    for path, name in repos.items():
        if os.path.exists(path):
            print(f"Pulling {name}...")
            if _run_git(["pull"], cwd=path):
                updated += 1
    
    print(f"\nUpdate complete. {updated} repository/repositories checked.")


def uninstall_skill(skill_id):
    skill_id = skill_id.lstrip("/")
    manifest = load_manifest()
    entry = next((s for s in manifest["installed"] if s["id"] == skill_id), None)
    
    if not entry:
        print(f"Skill {skill_id} is not installed.")
        return False

    if "localPath" in entry:
        lp = entry["localPath"]
        if os.path.exists(lp) or os.path.islink(lp) or isLinkOrJunction(lp):
            if os.path.islink(lp) or isLinkOrJunction(lp):
                try:
                    os.remove(lp)
                except OSError:
                    os.rmdir(lp)
            elif os.path.isdir(lp):
                shutil.rmtree(lp)
            else:
                os.remove(lp)

    manifest["installed"] = [s for s in manifest["installed"] if s["id"] != skill_id]
    save_manifest(manifest)
    print(f"Uninstalled: {skill_id}")
    return True


def list_available(registry_path):
    """Return a sorted list of (skill_id, meta_dict) for all named skills."""
    # 1. Try to load from pre-compiled index first (fast path & contains compiled suiteRef/suiteComponents)
    named_index_path = os.path.join(registry_path, "registry", "named-skills.json")
    if os.path.isfile(named_index_path):
        try:
            with open(named_index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            skills = []
            # Merge buckets (named skills)
            for bucket in data.get("buckets", {}).values():
                for entry in bucket:
                    skills.append((entry["id"], entry))
            # Merge awaiting classification (awakened skills)
            for entry in data.get("awaitingClassification", []):
                skills.append((entry["id"], entry))
            # Sort by ID
            skills.sort(key=lambda x: x[0])
            return skills
        except Exception:
            pass  # Fallback to scanning if index is malformed or read fails

    # 2. Scanning fallback (slow path)
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


def _parse_frontmatter(path):
    """Return the YAML frontmatter dict from a .md file, or {}.

    Uses pyyaml when available. The pure-Python fallback handles simple
    key: value pairs and one level of nesting (e.g. links.github), but
    does not support list syntax or deeper nesting — install pyyaml for
    full YAML support.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            return {}
        try:
            import yaml
            loaded = yaml.safe_load(m.group(1))
            return loaded if isinstance(loaded, dict) else {}
        except ImportError:
            res: dict = {}
            current_key: str | None = None
            for line in m.group(1).split('\n'):
                if not line.strip() or line.strip().startswith('#'):
                    continue
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                if ':' not in stripped:
                    continue
                k, _, v = stripped.partition(':')
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if v.lower() == 'true': v = True  # type: ignore[assignment]
                elif v.lower() == 'false': v = False  # type: ignore[assignment]
                if indent == 0:
                    current_key = k
                    res[k] = v if v else {}
                elif current_key and isinstance(res.get(current_key), dict):
                    res[current_key][k] = v
            return res
    except Exception:
        return {}


def list_installed():
    manifest = load_manifest()
    if not manifest["installed"]:
        print("No skills installed.")
        return

    print(f"{'ID':<35} {'Installed':<25} {'Location'}")
    print("-" * 85)
    for entry in manifest["installed"]:
        loc = entry.get("localPath", "unknown")
        # Relative path for display
        try:
            rel_loc = os.path.relpath(loc)
        except Exception:
            rel_loc = loc
        h_color = get_harness_color(rel_loc)
        colored_loc = f"{_fg(*h_color)}{rel_loc}{_reset()}"
        print(f"{entry['id']:<35} {entry['installedAt'][:19]:<25} {colored_loc}")


def interactive_install(registry_path, location: str = "local"):
    """Display all available named skills and let the user pick which to install.

    Args:
        location: "local" (default, .agents/.claude) or "global" (~/.gaia/skills)
    """
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
    loc_hint = "(global)" if location == "global" else "(local)"
    print(f"Enter numbers to install {loc_hint} (space or comma separated), or press Enter to cancel:")
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
        install_skill(sid, registry_path, location=location)
