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
            try:
                import yaml
                fm = yaml.safe_load(content[4:end]) or {}
            except Exception:
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


def _skill_search_dirs(root: str = ".", global_search: bool = False) -> list[str]:
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

    if global_search:
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


def scan_skill_mds(root: str = ".", global_search: bool = False) -> list:
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
    standard_dirs = [os.path.realpath(d) for d in _skill_search_dirs(root, global_search)]
    # The repo root itself is a mixed container, not a standard depth-1 skill container
    root_real = os.path.realpath(root)
    standard_containers = [d for d in standard_dirs if d != root_real]

    # Gather search roots: in pytest we isolate to root, otherwise walk parent
    if "PYTEST_CURRENT_TEST" in os.environ:
        search_roots = []
    else:
        if global_search:
            search_roots = [os.path.abspath(os.path.join(root, ".."))]
        else:
            search_roots = [os.path.abspath(root)]
    
    for d in _skill_search_dirs(root, global_search):
        if "PYTEST_CURRENT_TEST" in os.environ:
            # Containment check: use the realpath of d's *parent* joined with
            # d's basename so that a symlink *located* under root (but pointing
            # outside root) is correctly included, while global dirs that live
            # entirely outside root stay excluded.
            d_parent_real = os.path.realpath(os.path.dirname(d))
            d_entry = os.path.join(d_parent_real, os.path.basename(d))
            if d_entry.startswith(root_real + os.sep) or d_entry == root_real:
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

            # Check if current directory r is inside a standard skill container (depth 1)
            in_standard = False
            for std_dir in standard_containers:
                if r_real != std_dir and r_real.startswith(std_dir + os.sep):
                    rel = os.path.relpath(r_real, std_dir)
                    if os.sep not in rel:
                        in_standard = True
                        dirs[:] = []  # Stop descending further into this skill
                    else:
                        dirs[:] = []  # Already deeper than 1 layer, stop descending
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
                
                fm = _read_skill_md(md_path)
                if fm is None:
                    fm = {}

                # Enforce visible slashes as priority (linter rule)
                skill_id = fm.get("id", os.path.basename(skill_dir))
                skill_id = f"/{skill_id.lstrip('/')}"

                if not skill_id or skill_id == '/':
                    continue
                
                if skill_id in seen_ids:
                    continue
                
                seen_ids.add(skill_id)
                seen_real_paths.add(real_path)

                name = fm.get("name", skill_id)
                description = fm.get("description", fm.get("_body_snippet", ""))
                found.append({
                    "id": skill_id,
                    "name": name,
                    "description": description,
                    "prerequisites": fm.get("prerequisites", []),
                    "source_dir": os.path.dirname(skill_dir),
                    "location": os.path.relpath(skill_dir, root),
                    "real_path": real_path,
                })
    return found


def _word_set(text):
    words = set(re.findall(r"[a-z]{3,}", text.lower()))
    return words - _SEMANTIC_STOPWORDS


def match_skill_to_canonical(skill_id, skill_name, skill_description, canonical_skills, origin_skills=None, named_skills=None, threshold=0.15):
    """Find the best skill match for a custom skill using sequential priority.
    
    1. Exact or near-exact slash-skill name or name match in ORIGIN skills.
    2. Exact or near-exact slash-skill name or name match in NAMED skills.
    3. Exact or near-exact ID or name match in GENERIC (canonical) skills.
    4. Semantic word overlap against STARLESS (generic) skills (with threshold).

    Returns (matched_id, score, match_type) or None.
    """
    query_id_lower = skill_id.lower().strip()

    def normalize_name(n):
        return n.lower().replace('-', ' ').replace('_', ' ').strip()

    query_name_norm = normalize_name(skill_name)
    query_id_norm = normalize_name(skill_id)

    # ⚡ Bolt Optimization: Cache string normalizations to prevent O(N*M) redundant parsing overhead
    # In exact match checks, we repeatedly evaluate the same canonical skills against different
    # custom skills. Caching their base ID and normalized name speeds up this scan significantly.
    if not hasattr(match_skill_to_canonical, "_norm_cache"):
        match_skill_to_canonical._norm_cache = {}

    def _check_skills(skills_list, match_type):
        if not skills_list:
            return None
        for canon in skills_list:
            canon_id = canon["id"]
            if canon_id not in match_skill_to_canonical._norm_cache:
                canon_base = canon_id.split('/')[-1].lower().strip()
                canon_name_norm = normalize_name(canon.get('name', ''))
                match_skill_to_canonical._norm_cache[canon_id] = (canon_base, canon_name_norm)
            else:
                canon_base, canon_name_norm = match_skill_to_canonical._norm_cache[canon_id]

            # Slash-aware identity check
            if canon_base == query_id_lower or f"/{canon_base}" == query_id_lower or canon_name_norm == query_name_norm or canon_name_norm == query_id_norm:
                return (canon_id, 1.0, match_type)
        return None

    # 1. Exact/base ID or normalized name match in ORIGIN priority
    res = _check_skills(origin_skills, "origin")
    if res:
        return res

    # 2. Exact/base ID or normalized name match in NAMED priority
    res = _check_skills(named_skills, "named")
    if res:
        return res

    # 3. Exact ID or normalized name match in GENERIC (canonical) skills
    res = _check_skills(canonical_skills, "exact_generic")
    if res:
        return res

    # 4. Semantic search ONLY on STARLESS/generic skills
    query_words = _word_set(f"{skill_id} {skill_name} {skill_description}")
    if not query_words:
        return None

    # Check starless (generic) skills with threshold
    best_generic_id = None
    best_generic_score = threshold

    # Define an external cache to avoid mutating canonical_skills (which can cause JSON serialization errors)
    if not hasattr(match_skill_to_canonical, "_word_cache"):
        match_skill_to_canonical._word_cache = {}

    for canon in canonical_skills:
        canon_id = canon["id"]
        if canon_id not in match_skill_to_canonical._word_cache:
            canon_text = f"{canon.get('id', '')} {canon.get('name', '')} {canon.get('description', '')}"
            match_skill_to_canonical._word_cache[canon_id] = _word_set(canon_text)

        target_words = match_skill_to_canonical._word_cache[canon_id]
        if not target_words:
            continue

        # Compute intersection efficiently
        shared_count = len(query_words.intersection(target_words))
        score = shared_count / len(query_words)

        if score > best_generic_score:
            best_generic_score = score
            best_generic_id = canon_id

    if best_generic_id:
        return (best_generic_id, round(best_generic_score, 3), "generic")
    
    return None
