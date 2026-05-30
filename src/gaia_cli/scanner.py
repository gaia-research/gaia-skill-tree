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


def scan_skill_mds():
    """Detect installed custom skills from .agents/skills/ and .claude/skills/.

    Returns a list of dicts: {"id": str, "name": str, "description": str}
    Each entry represents one installed skill directory.
    """
    skill_dirs = [d for d in (".agents/skills", ".claude/skills") if os.path.isdir(d)]
    found = []
    seen_ids = set()

    for skills_root in skill_dirs:
        try:
            entries = sorted(os.listdir(skills_root))
        except OSError:
            continue
        for entry in entries:
            entry_path = os.path.join(skills_root, entry)
            if not os.path.isdir(entry_path) or entry.startswith("."):
                continue
            skill_id = entry
            if skill_id in seen_ids:
                continue
            # Find best .md candidate
            md_path = None
            for candidate in _SKILL_MD_CANDIDATES:
                p = os.path.join(entry_path, candidate)
                if os.path.isfile(p):
                    md_path = p
                    break
            if not md_path:
                for f in sorted(os.listdir(entry_path)):
                    if f.endswith(".md"):
                        md_path = os.path.join(entry_path, f)
                        break
            fm = _read_skill_md(md_path) if md_path else {}
            seen_ids.add(skill_id)
            name = fm.get("name", skill_id)
            description = fm.get("description", fm.get("_body_snippet", ""))
            found.append({"id": skill_id, "name": name, "description": description})

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
