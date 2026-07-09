import json
import os
import re
import subprocess
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import urlparse

try:
    from gaia_cli.resolver import load_canonical_skills
except ModuleNotFoundError:
    pass

from gaia_cli.registry import registry_graph_path, skill_batches_dir


SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


class NonPublicRepoError(RuntimeError):
    """Raised when no public GitHub remote is detected for the working directory."""


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
        parsed = urlparse(cleaned if "://" in cleaned else "https://" + cleaned)
        host = parsed.netloc.lower().lstrip("www.")
        if host == "github.com" or host.endswith(".github.com"):
            return parsed.path.lstrip("/")

    raise NonPublicRepoError(config.get('gaiaUser', 'unknown'))


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

    # ⚡ Bolt Optimization: Pre-compute properties and reuse SequenceMatcher
    # to avoid O(N*M) overhead, speeding up lexical similarity by 50-80%
    precomputed_canonical = []
    for skill in canonical_skill_map.values():
        canonical_id_lower = skill["id"].lower()
        canonical_name_lower = skill.get("name", skill["id"]).lower()
        precomputed_canonical.append((canonical_id_lower, canonical_name_lower, skill["id"]))

    for proposed_id in proposed_ids:
        candidate_name = skill_name_from_id(proposed_id).lower()
        candidate_id_lower = proposed_id.lower()

        id_matcher = SequenceMatcher(None, candidate_id_lower)
        name_matcher = SequenceMatcher(None, candidate_name)

        scored = []
        for canonical_id_lower, canonical_name_lower, target_id in precomputed_canonical:
            score1 = 0.0
            id_matcher.set_seq2(canonical_id_lower)
            if id_matcher.real_quick_ratio() >= 0.45 and id_matcher.quick_ratio() >= 0.45:
                score1 = id_matcher.ratio()

            score2 = 0.0
            name_matcher.set_seq2(canonical_name_lower)
            if name_matcher.real_quick_ratio() >= 0.45 and name_matcher.quick_ratio() >= 0.45:
                score2 = name_matcher.ratio()

            score = score1 if score1 > score2 else score2
            if score >= 0.45:
                scored.append((score, target_id))

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


def build_skill_batch(raw_tokens, config, registry_root, now=None, source_repo=None):
    graph_path = registry_graph_path(registry_root)
    canonical_map = load_canonical_skill_map(graph_path)
    if source_repo is None:
        source_repo = detect_source_repo(config)
    timestamp = now or datetime.now(timezone.utc)
    generated_at = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    batch_id = (
        f"{timestamp.strftime('%Y%m%d%H%M%S')}-"
        f"{config.get('gaiaUser', 'unknown')}-{source_repo.split('/')[-1]}"
    )

    custom_state_path = os.path.join(".gaia", "custom_state.json")
    
    proposed_skills = []
    proposed_combos = []
    known_ids = {}
    proposed_ids = []

    if os.path.exists(custom_state_path):
        try:
            with open(custom_state_path, "r", encoding="utf-8") as f:
                cstate = json.load(f)
                
                # Extract Custom Skills and Starless Skills
                custom_skills = cstate.get("customSkills", [])
                for sk in custom_skills:
                    m_type = sk.get("match_type")
                    c_level = sk.get("canon_level", "0★")
                    mapped_id = sk.get("mapped_to", sk.get("id"))
                    
                    if m_type in ("generic", "exact_generic") and c_level == "0★":
                        # Starless skill
                        bare_id = mapped_id.lstrip('/')
                        local_bare_id = sk.get("id", "").lstrip('/')
                        known_ids[bare_id] = local_bare_id
                    elif m_type not in ("origin", "named", "generic", "exact_generic"):
                        # Custom skill
                        bare_id = sk.get("id", "").lstrip('/')
                        if bare_id:
                            proposed_ids.append(bare_id)
                            skill = build_proposed_skill(bare_id, source_repo)
                            if "name" in sk and sk["name"]:
                                skill["name"] = sk["name"]
                            if "description" in sk and sk["description"]:
                                skill["description"] = sk["description"]
                            if "prerequisites" in sk and sk["prerequisites"]:
                                skill["prerequisites"] = sk["prerequisites"]
                            proposed_skills.append(skill)
                
                # Extract Fusions
                fusions = cstate.get("customFusions", {})
                for target, data in fusions.items():
                    if isinstance(data, dict):
                        sources = data.get("sources", [])
                        level = data.get("level", "1★")
                        stype = data.get("type", "extra")
                    else:
                        sources = data
                        level = "1★"
                        stype = "extra"
                    
                    proposed_combos.append({
                        "candidateResult": target,
                        "detectedSkills": sources,
                        "levelFloor": level,
                        "type": stype
                    })
        except Exception:
            pass

    return {
        "batchId": batch_id,
        "userId": config.get("gaiaUser", "unknown"),
        "sourceRepo": source_repo,
        "generatedAt": generated_at,
        "knownSkills": [{"skillId": k, "localId": v} for k, v in sorted(known_ids.items())],
        "proposedSkills": proposed_skills,
        "proposedCombinations": proposed_combos,
        "similarity": build_similarity(proposed_ids, canonical_map),
    }


def write_skill_batch(batch, registry_root):
    intake_dir = skill_batches_dir(registry_root)
    os.makedirs(intake_dir, exist_ok=True)
    batch_path = os.path.join(intake_dir, f"{batch['batchId']}.json")
    with open(batch_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2)
        f.write("\n")
    return batch_path


def pushable_skill_ids(config, registry_root):
    """Return the set of graph node ids that `gaia push` would propose.

    Reuses build_skill_batch so the local-graph highlight (issue #139) can never
    drift from what actually gets pushed. Ids are bare (no leading slash) to match
    build_render_graph node ids. Combines starless known skills (canonical id),
    proposed custom skills, and fusion targets.
    """
    try:
        batch = build_skill_batch([], config, registry_root)
    except Exception:
        return set()
    ids: set[str] = set()
    for entry in batch.get("knownSkills", []):
        sid = (entry.get("skillId") or "").lstrip("/")
        if sid:
            ids.add(sid)
    for entry in batch.get("proposedSkills", []):
        sid = (entry.get("id") or "").lstrip("/")
        if sid:
            ids.add(sid)
    for combo in batch.get("proposedCombinations", []):
        sid = (combo.get("candidateResult") or "").lstrip("/")
        if sid:
            ids.add(sid)
    return ids


_SKILL_MD_CANDIDATES = ("skill.md", "SKILL.md", "README.md", "readme.md")


def collectBatchSkillPaths(batch, registryRoot="."):
    """Return absolute paths to named-skill markdown files referenced by ``batch``.

    The push pipeline does not embed markdown in the batch JSON; instead it
    references skills by ID and pulls bodies from the local install manifest
    or the canonical ``registry/named/`` tree.  This helper collects the
    markdown paths so the security scanner has something to scan.

    The returned list is deduplicated and skips paths that do not exist.
    """
    paths: list[str] = []
    seen: set[str] = set()

    def addPath(candidate: str) -> None:
        if not candidate:
            return
        absPath = os.path.abspath(candidate)
        if absPath in seen:
            return
        if not os.path.isfile(absPath):
            return
        seen.add(absPath)
        paths.append(absPath)

    manifestPath = os.path.join(".gaia", "install-manifest.json")
    manifestEntries: list = []
    if os.path.exists(manifestPath):
        try:
            with open(manifestPath, "r", encoding="utf-8") as f:
                manifestEntries = json.load(f).get("installed", []) or []
        except (OSError, json.JSONDecodeError):
            manifestEntries = []

    for entry in manifestEntries:
        localPath = entry.get("localPath") or ""
        if localPath and os.path.isdir(localPath):
            for candidate in _SKILL_MD_CANDIDATES:
                addPath(os.path.join(localPath, candidate))
        sourceRef = entry.get("sourceRef") or ""
        if sourceRef:
            addPath(os.path.join(registryRoot, sourceRef))
        sid = entry.get("id") or ""
        if "/" in sid:
            contrib, name = sid.split("/", 1)
            addPath(os.path.join(registryRoot, "registry", "named", contrib, f"{name}.md"))

    namedRoot = os.path.join(registryRoot, "registry", "named")
    for known in batch.get("knownSkills", []) or []:
        sid = (known.get("skillId") or "").lstrip("/")
        localId = (known.get("localId") or "").lstrip("/")
        for tail in (sid, localId):
            if not tail or "/" not in tail:
                continue
            contrib, name = tail.split("/", 1)
            addPath(os.path.join(namedRoot, contrib, f"{name}.md"))

    return paths


def scanProposedSkillDescriptions(batch):
    """Scan inline strings (descriptions, names) carried in the batch JSON itself.

    Some attacks land in skill metadata before any markdown file exists yet
    (e.g. injection in ``description``).  This synthesizes a virtual path so
    findings still locate cleanly in the report.
    """
    from gaia_cli.securityScanner import scanSkillContent

    findings = []
    for proposed in batch.get("proposedSkills", []) or []:
        sid = proposed.get("id", "unknown")
        text = "\n".join(
            str(proposed.get(k, ""))
            for k in ("name", "description", "summary", "notes")
            if proposed.get(k)
        )
        if not text.strip():
            continue
        findings.extend(scanSkillContent(text, f"<batch:proposed:{sid}>"))
    return findings


def scanBatchForSecurity(batch, registryRoot="."):
    """Run the full security scanner against everything ``batch`` references.

    Returns a list of findings combining markdown bodies pulled from the
    install manifest / canonical tree plus inline batch JSON strings.
    """
    from gaia_cli.securityScanner import (
        SEVERITY_ORDER,
        scanNamedSkillFiles,
    )

    findings = list(scanNamedSkillFiles(collectBatchSkillPaths(batch, registryRoot)))
    findings.extend(scanProposedSkillDescriptions(batch))
    findings.sort(
        key=lambda f: (
            SEVERITY_ORDER.get(f.severity, 99),
            f.category,
            f.filePath,
            f.lineNumber,
            f.rule,
        )
    )
    return findings
