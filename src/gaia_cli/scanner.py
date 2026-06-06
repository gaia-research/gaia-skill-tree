import os
import re

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "vendor",
    "__pycache__",
}

DEFAULT_EXCLUDED_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".pyc",
    ".o",
    ".gexf",
)

_SKILL_PATTERN = re.compile(r'/[a-z][a-z0-9]*(-[a-z0-9]+)*')


def load_config():
    toml_path = '.gaia/config.toml'
    json_path = '.gaia/config.json'
    if os.path.exists(toml_path):
        data = {}
        with open(toml_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "=" not in line or line.strip().startswith("#"):
                    continue
                key, _, raw = line.partition("=")
                value = raw.strip()
                if value.startswith("[") and value.endswith("]"):
                    data[key.strip()] = [
                        item.strip().strip('"')
                        for item in value[1:-1].split(",")
                        if item.strip()
                    ]
                elif value.lower() in ("true", "false"):
                    data[key.strip()] = value.lower() == "true"
                else:
                    data[key.strip()] = value.strip('"')
        if "username" in data and "gaiaUser" not in data:
            data["gaiaUser"] = data["username"]
        return data
    config_path = json_path
    if not os.path.exists(config_path):
        return None
    import json
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def scan_file_for_skills(filepath):
    found_skills = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            for match in _SKILL_PATTERN.finditer(content):
                found_skills.add(match.group(0))
    except Exception:
        pass
    return found_skills


def _should_scan_file(filename):
    return not filename.startswith('.') and not filename.endswith(DEFAULT_EXCLUDED_EXTENSIONS)


def scan_repo_detailed():
    config = load_config()
    empty = {
        "tokens": set(),
        "files_scanned": 0,
        "candidate_count": 0,
        "paths_found": [],
        "paths_missing": [],
    }
    if not config:
        return empty

    scan_paths = config.get('scanPaths', [])
    all_found = set()
    files_scanned = 0
    paths_found = []
    paths_missing = []

    for path in scan_paths:
        if os.path.isfile(path):
            paths_found.append(path)
            all_found.update(scan_file_for_skills(path))
            files_scanned += 1
        elif os.path.isdir(path):
            paths_found.append(path)
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDED_DIRS and not d.startswith('.')]
                for file in files:
                    if _should_scan_file(file):
                        all_found.update(scan_file_for_skills(os.path.join(root, file)))
                        files_scanned += 1
        else:
            paths_missing.append(path)

    return {
        "tokens": all_found,
        "files_scanned": files_scanned,
        "candidate_count": len(all_found),
        "paths_found": paths_found,
        "paths_missing": paths_missing,
    }


def scan_repo():
    return scan_repo_detailed()["tokens"]


# ─── skill .md semantic scan ──────────────────────────────────────────────────

_SKILL_MD_CANDIDATES = ("skill.md", "SKILL.md", "README.md", "readme.md")
_SEMANTIC_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "to", "was", "were", "with", "this", "you", "your",
    "skill", "gaia", "use", "when", "user", "asks", "can", "will", "run", "based",
    "new", "all", "any", "each", "has", "have", "its", "not", "but", "also",
}


def _read_skill_md(filepath):
    """Extract frontmatter + first body paragraph from a skill .md file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    fm = {}
    if content.startswith("---\n"):
        end = content.find("\n---", 4)
        if end != -1:
            for line in content[4:end].splitlines():
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                fm[key.strip()] = value.strip().strip('"').strip("'")
            body = content[end + 4:].strip()
        else:
            body = content
    else:
        body = content
    # Take up to first 300 chars of body as description supplement
    fm["_body_snippet"] = body[:300]
    return fm


def _skill_search_dirs(root: str = ".") -> list[str]:
    """Return all directories to search for skill subdirectories, deduplicated by real path.

    Priority order:
      1. Project-local dirs (under root) — checked first so project installs win
      2. Global user dirs (~/.agents/skills, ~/.claude/skills, XDG)
      3. Config-driven dirs from .gaia/config.toml skillDirs key
    """
    candidates: list[str] = []

    # 1. Project-local — every known agent/tool convention that uses subdir-per-skill
    for rel in (
        os.path.join(".agents", "skills"),       # primary (gaia, agent-agnostic)
        os.path.join(".claude", "skills"),       # Claude Code legacy
        os.path.join(".antigravity", "skills"),  # Antigravity legacy
        os.path.join(".cursor", "rules"),        # Cursor IDE
        os.path.join(".windsurf", "rules"),      # Windsurf IDE
        os.path.join(".copilot", "skills"),      # GitHub Copilot (speculative)
        os.path.join(".zed", "skills"),          # Zed editor (speculative)
    ):
        candidates.append(os.path.join(root, rel))

    # 2. Global user dirs — skills installed outside any single project
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, ".agents", "skills"))   # global agent-agnostic
    candidates.append(os.path.join(home, ".claude", "skills"))   # Claude Code global skills
    # XDG_DATA_HOME (Linux/macOS standard; ignored on Windows where it's usually unset)
    xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    candidates.append(os.path.join(xdg_data, "gaia", "skills"))

    # 3. Config-driven custom dirs
    config = load_config()
    if config:
        for d in config.get("skillDirs", []):
            expanded = os.path.expanduser(d)
            if not os.path.isabs(expanded):
                expanded = os.path.join(root, expanded)
            candidates.append(expanded)

    # Deduplicate by real path while preserving priority order; skip missing dirs
    seen_real: set[str] = set()
    result: list[str] = []
    for d in candidates:
        if not os.path.isdir(d):
            continue
        real = os.path.realpath(d)
        if real in seen_real:
            continue
        seen_real.add(real)
        result.append(d)
    return result


def _should_prune_dir(d: str) -> bool:
    if d in DEFAULT_EXCLUDED_DIRS:
        return True
    if d.startswith('.'):
        allowed_prefixes = (
            ".agent",
            ".agents",
            ".claude",
            ".antigravity",
            ".cursor",
            ".windsurf",
            ".copilot",
            ".zed",
            ".local",
            ".gaia",
        )
        if not d.startswith(allowed_prefixes):
            return True
    return False


def scan_skill_mds(root: str = ".") -> list:
    """Detect installed custom skills recursively from all known search paths.

    Checks project's parent directory (..) and all standard/configured skill search directories.
    Prunes standard excluded paths for speed.

    Returns a list of dicts: {"id": str, "name": str, "description": str,
    "source_dir": str, "location": str, "real_path": str}
    """
    found = []
    seen_ids = set()
    seen_real_paths = set()
    visited_real_paths = set()

    # Determine standard skill directories
    standard_dirs = [os.path.realpath(d) for d in _skill_search_dirs(root)]

    # Gather search roots: in pytest we isolate to root, otherwise walk parent
    if "PYTEST_CURRENT_TEST" in os.environ:
        search_roots = []
    else:
        search_roots = [os.path.abspath(os.path.join(root, ".."))]
    
    for d in _skill_search_dirs(root):
        if "PYTEST_CURRENT_TEST" in os.environ:
            if os.path.abspath(d).startswith(os.path.abspath(root)):
                search_roots.append(os.path.abspath(d))
        else:
            search_roots.append(os.path.abspath(d))

    # Deduplicate search roots by their real paths, keeping priority order
    deduped_roots = []
    seen_roots = set()
    for sr in search_roots:
        real_sr = os.path.realpath(sr)
        if real_sr not in seen_roots and os.path.isdir(sr):
            seen_roots.add(real_sr)
            deduped_roots.append(sr)

    for search_root in deduped_roots:
        for r, dirs, files in os.walk(search_root, followlinks=True):
            r_real = os.path.realpath(r)
            if r_real in visited_real_paths:
                dirs[:] = []
                continue
            visited_real_paths.add(r_real)

            # Prune directories
            dirs[:] = [d for d in dirs if not _should_prune_dir(d)]

            # Check if current directory r is inside a standard skill directory
            in_standard = False
            for std_dir in standard_dirs:
                if r_real != std_dir and r_real.startswith(std_dir + os.sep):
                    in_standard = True
                    break

            # Find best candidate file in this directory
            skill_md_file = None
            if in_standard:
                # Inside standard skill directory, look for any best .md candidate
                # First check exact candidates
                for candidate in ("skill.md", "SKILL.md", "README.md", "readme.md"):
                    if candidate in files:
                        skill_md_file = candidate
                        break
                if not skill_md_file:
                    # Fallback to any .md file
                    for f in sorted(files):
                        if f.lower().endswith(".md"):
                            skill_md_file = f
                            break
            else:
                # Outside standard directories, we ONLY accept skill.md / SKILL.md
                for f in files:
                    if f.lower() == "skill.md":
                        skill_md_file = f
                        break

            if skill_md_file:
                md_path = os.path.join(r, skill_md_file)
                skill_dir = r
                real_path = os.path.realpath(skill_dir)
                if real_path in seen_real_paths:
                    continue
                
                skill_id = os.path.basename(skill_dir)
                if not skill_id or skill_id.startswith('.'):
                    continue
                
                if skill_id in seen_ids:
                    continue

                fm = _read_skill_md(md_path)
                if fm is None:
                    fm = {}
                
                seen_ids.add(skill_id)
                seen_real_paths.add(real_path)

                name = fm.get("name", skill_id)
                description = fm.get("description", fm.get("_body_snippet", ""))
                found.append({
                    "id": skill_id,
                    "name": name,
                    "description": description,
                    "source_dir": os.path.dirname(skill_dir),
                    "location": os.path.relpath(skill_dir, root),
                    "real_path": real_path,
                })
    return found


def _word_set(text):
    words = set(re.findall(r"[a-z]{3,}", text.lower()))
    return words - _SEMANTIC_STOPWORDS


def match_skill_to_canonical(skill_id, skill_name, skill_description, canonical_skills, threshold=0.20):
    """Find the best canonical skill match for a custom skill using word overlap.

    Returns (canonical_id, score) or None.
    """
    query_words = _word_set(f"{skill_id} {skill_name} {skill_description}")
    if not query_words:
        return None

    best_id = None
    best_score = threshold

    for canon in canonical_skills:
        canon_text = f"{canon.get('id', '')} {canon.get('name', '')} {canon.get('description', '')}"
        target_words = _word_set(canon_text)
        if not target_words:
            continue
        shared = query_words & target_words
        score = len(shared) / len(query_words)
        if score > best_score:
            best_score = score
            best_id = canon["id"]

    return (best_id, round(best_score, 3)) if best_id else None
