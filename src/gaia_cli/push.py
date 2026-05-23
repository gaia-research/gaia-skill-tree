import json
import os
import re
import subprocess
from datetime import datetime, timezone
from difflib import SequenceMatcher

try:
    from gaia_cli.resolver import load_canonical_skills
except ModuleNotFoundError:
    from gaia_cli.resolver import load_canonical_skills

from gaia_cli.registry import registry_graph_path, skill_batches_dir


SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
MIN_PROPOSED_TOKEN_LENGTH = 3
PROPOSED_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "to", "was", "were", "with", "already",
    "self", "this", "import", "return", "class", "def", "function", "true", "false", "none", "null", "if", "else", "while", "for", "in", "try", "except", 
    "finally", "raise", "with", "as", "lambda", "yield", "await", "async", "print", "type", "object", "list", "dict", "set", "tuple", "str", "int", "float",
    "bool", "bytes", "bytearray", "memoryview", "range", "enumerate", "zip", "reversed", "sorted", "any", "all", "map", "filter", "eval", "exec", 
    "compile", "getattr", "setattr", "hasattr", "delattr", "isinstance", "issubclass", "len", "id", "hash", "abs", "divmod", "pow", "round", 
    "min", "max", "sum", "open", "input", "help", "dir", "vars", "globals", "locals", "property", "staticmethod", "classmethod", "super",
    "gaia", "skill", "registry", "tree", "node", "batch", "intake", "review", "canonical", "local", "remote", "origin", "master", "main", "branch",
}


def load_canonical_skill_map(registry_path):
    if not os.path.exists(registry_path):
        return {}
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    return {skill["id"]: skill for skill in data.get("skills", [])}


def skill_name_from_id(skill_id):
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", skill_id.replace("-", " ")).replace("_", " ")
    return " ".join(w[:1].upper() + w[1:] for w in words.split())


def detect_source_repo(config):
    env_repo = os.environ.get("GITHUB_REPOSITORY")
    if env_repo:
        return env_repo

    try:
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=False,
            cwd=".",
        ).stdout.strip()
    except Exception:
        remote = ""

    if remote:
        cleaned = remote.removesuffix(".git")
        if cleaned.startswith("git@") and ":" in cleaned:
            return cleaned.split(":", 1)[1]
        if "github.com/" in cleaned:
            return cleaned.split("github.com/", 1)[1]

    return f"{config.get('gaiaUser', 'unknown')}/local-repo"


def build_proposed_skill(skill_id, source_repo):
    name = skill_name_from_id(skill_id)
    return {
        "id": skill_id,
        "name": name,
        "type": "basic",
        "description": f"Candidate skill detected from {source_repo} usage: {name}.",
        "sourceRepo": source_repo,
        "lifecycle": "pending",
    }


def similarity_score(candidate_id, canonical_skill):
    candidate_name = skill_name_from_id(candidate_id).lower()
    canonical_id = canonical_skill["id"].lower()
    canonical_name = canonical_skill.get("name", canonical_skill["id"]).lower()
    return max(
        SequenceMatcher(None, candidate_id.lower(), canonical_id).ratio(),
        SequenceMatcher(None, candidate_name, canonical_name).ratio(),
    )


def build_similarity(proposed_ids, canonical_skill_map, limit_per_skill=3):
    links = []
    for proposed_id in proposed_ids:
        scored = []
        for skill in canonical_skill_map.values():
            score = similarity_score(proposed_id, skill)
            if score >= 0.45:
                scored.append((score, skill["id"]))
        for score, target_id in sorted(scored, reverse=True)[:limit_per_skill]:
            links.append(
                {
                    "sourceSkillId": proposed_id,
                    "targetSkillId": target_id,
                    "score": round(score, 3),
                    "reason": "Lexical similarity from Gaia push scan.",
                }
            )
    return links


def filter_proposed_ids(valid_tokens, canonical_ids):
    filtered = []
    for token in valid_tokens:
        if token in canonical_ids:
            continue
        if len(token) < MIN_PROPOSED_TOKEN_LENGTH:
            continue
        if token in PROPOSED_STOPWORDS:
            continue
        filtered.append(token)
    return filtered


def build_skill_batch(raw_tokens, config, registry_root, now=None):
    graph_path = registry_graph_path(registry_root)
    canonical_ids = load_canonical_skills(graph_path)
    canonical_map = load_canonical_skill_map(graph_path)
    source_repo = detect_source_repo(config)
    timestamp = now or datetime.now(timezone.utc)
    generated_at = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # Strip leading slashes from tokens before matching
    clean_tokens = [t.lstrip('/') for t in raw_tokens]
    valid_tokens = sorted(token for token in clean_tokens if SKILL_ID_RE.match(token))
    known_ids = [token for token in valid_tokens if token in canonical_ids]
    proposed_ids = filter_proposed_ids(valid_tokens, canonical_ids)
    batch_id = (
        f"{timestamp.strftime('%Y%m%d%H%M%S')}-"
        f"{config.get('gaiaUser', 'unknown')}-{source_repo.split('/')[-1]}"
    )

    proposed_skills = []
    for skill_id in proposed_ids:
        skill = build_proposed_skill(skill_id, source_repo)
        proposed_skills.append(skill)

    return {
        "batchId": batch_id,
        "userId": config.get("gaiaUser", "unknown"),
        "sourceRepo": source_repo,
        "generatedAt": generated_at,
        "knownSkills": [{"skillId": skill_id} for skill_id in known_ids],
        "proposedSkills": proposed_skills,
        "similarity": build_similarity(proposed_ids, canonical_map),
    }


def write_skill_batch(batch, registry_root):
    intake_dir = skill_batches_dir(registry_root)
    os.makedirs(intake_dir, exist_ok=True)
    batch_path = os.path.join(intake_dir, f"{batch['batchId']}.json")
    with open(batch_path, "w") as f:
        json.dump(batch, f, indent=2)
        f.write("\n")
    return batch_path
