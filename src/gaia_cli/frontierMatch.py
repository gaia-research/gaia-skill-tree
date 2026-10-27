"""Advisory registry matching and ledger dedupe for Frontier challenger leads.

Everything here is read-only and non-authoritative. A match is a ranked
suggestion about where a lead might belong, never an admission, approval,
verification, rank, or Trust Magnitude input. The module reads registry bytes
and the committed lead ledger; it never writes either.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from gaia_cli.frontier import FORBIDDEN_AUTHORITY_FIELDS, canonical_source_url, dedupe_key

MATCH_SCHEMA = "frontier-match-v1"
DEDUPE_SCHEMA = "frontier-dedupe-v1"
LEDGER_GLOB = "evidence/frontier-challenges/*/lead.json"
MATCH_METHOD = "lexical-bm25-v1"
MATCH_AUTHORITY = "advisory ranking only; never admission, approval, verification, rank or Trust Magnitude"
MAX_LEAD_BYTES = 1_048_576
MAX_REGISTRY_FILE_BYTES = 2_097_152
FORBIDDEN_CASEFOLDED = frozenset(name.casefold() for name in FORBIDDEN_AUTHORITY_FIELDS)
STOPWORDS = frozenset(
    "a an and are as at be by for from how in into is it its of on or over that the their this to with "
    "via using use used can may not no than then when which who will would one two selected given each".split()
)
K1, B = 1.5, 0.75
FIELD_WEIGHTS = (("id", 3), ("name", 3), ("title", 2), ("tags", 2), ("summary", 1), ("description", 1), ("useCase", 1))


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens with stopwords removed and a light suffix stem."""
    tokens = []
    for raw in re.findall(r"[a-z0-9]+", str(text).casefold()):
        if raw in STOPWORDS or len(raw) < 2:
            continue
        for suffix in ("ing", "es", "ed", "s"):
            if raw.endswith(suffix) and len(raw) - len(suffix) >= 4:
                raw = raw[: -len(suffix)]
                break
        tokens.append(raw)
    return tokens


def _forbiddenAuthorityKeys(value: Any, path: str = "$") -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_CASEFOLDED:
                found.append(f"{path}.{key}")
            found.extend(_forbiddenAuthorityKeys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbiddenAuthorityKeys(child, f"{path}[{index}]"))
    return found


def _requireLeadShape(lead: Any, fields: tuple[tuple[str, ...], ...]) -> None:
    """Partial leads are allowed (a target is what match finds); authority fields never are."""
    if not isinstance(lead, dict):
        raise ValueError("lead must be a JSON object")
    forged = _forbiddenAuthorityKeys(lead)
    if forged:
        raise ValueError("forbidden authority field: " + ", ".join(sorted(forged)))
    for field in fields:
        node: Any = lead
        for part in field:
            node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, str) or not node.strip():
            raise ValueError("lead is missing required field: " + ".".join(field))


def _yamlFrontmatter(raw: bytes) -> dict[str, Any]:
    import yaml
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").lstrip("\ufeff")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    try:
        meta = yaml.load(text[4:end], Loader=loader)
    except yaml.YAMLError:
        return {}
    return meta if isinstance(meta, dict) else {}


def _readBounded(path: Path, root: Path) -> bytes | None:
    """Registry bytes for a regular, in-tree, size-bounded file; symlinks and oversize files are skipped."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_REGISTRY_FILE_BYTES:
            return None
        if not path.resolve().is_relative_to(root):
            return None
        return path.read_bytes()
    except OSError:
        return None


def loadRegistryEntries(repo_root: str | Path) -> tuple[list[dict[str, Any]], str, int]:
    """Read generic nodes and named skills; return entries, a registry byte digest and file count."""
    root = Path(repo_root).resolve()
    nodes, named = root / "registry" / "nodes", root / "registry" / "named"
    if not nodes.is_dir() or not named.is_dir():
        raise ValueError(f"no registry/nodes and registry/named under {root}; pass --repo-root <checkout>")
    entries, manifest = [], []
    for path in sorted(nodes.rglob("*.json")):
        raw = _readBounded(path, root)
        if raw is None:
            continue
        manifest.append(f"{path.relative_to(root).as_posix()}\0{_sha(raw)}")
        try:
            node = json.loads(raw)
        except ValueError:
            continue
        if isinstance(node, dict) and node.get("id"):
            entries.append({"kind": "generic", "skillId": node["id"], "genericSkillId": node["id"], "fields": node, "path": path.relative_to(root).as_posix()})
    for path in sorted(named.rglob("*.md")):
        raw = _readBounded(path, root)
        if raw is None:
            continue
        manifest.append(f"{path.relative_to(root).as_posix()}\0{_sha(raw)}")
        meta = _yamlFrontmatter(raw)
        if meta.get("id") and meta.get("genericSkillRef"):
            entries.append({"kind": "named", "skillId": str(meta["id"]), "genericSkillId": str(meta["genericSkillRef"]), "fields": meta, "path": path.relative_to(root).as_posix()})
    similarity = _readBounded(root / "registry" / "similarity.json", root)
    if similarity is not None:
        manifest.append(f"registry/similarity.json\0{_sha(similarity)}")
    return entries, _sha("\n".join(manifest).encode()), len(manifest)


def _docTokens(entry: dict[str, Any]) -> Counter:
    fields, weighted = entry["fields"], Counter()
    for name, weight in FIELD_WEIGHTS:
        value = fields.get(name)
        if isinstance(value, list):
            value = " ".join(str(item) for item in value)
        if not isinstance(value, str):
            continue
        for token in tokenize(value.replace("-", " ").replace("/", " ")):
            weighted[token] += weight
    return weighted


def _repoRef(url: Any) -> tuple[str, tuple[str, ...]] | None:
    """(owner/repo, subpath directory segments) for a GitHub URL; None for anything else."""
    try:
        parts = urlsplit(canonical_source_url(str(url)))
    except ValueError:
        return None
    if parts.hostname not in {"github.com", "raw.githubusercontent.com", "www.github.com"}:
        return None
    segments = [p for p in parts.path.split("/") if p]
    if len(segments) < 2:
        return None
    repo = "/".join(segments[:2]).casefold()
    rest = segments[3:] if parts.hostname == "raw.githubusercontent.com" else segments[4:]
    if segments[2:3] not in (["blob"], ["tree"]) and parts.hostname != "raw.githubusercontent.com":
        rest = []
    if rest and "." in rest[-1]:
        rest = rest[:-1]  # drop the file name (SKILL.md, __init__.py): compare directories
    return repo, tuple(part.casefold() for part in rest)


def findRegisteredChallenger(lead: dict[str, Any], entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Registry skills that are the challenger itself, matched by exact name or by repository plus subpath.

    A bare repository URL matches only when exactly one registry entry lives in that repository;
    otherwise (monorepos such as many skills in one repo) it is reported as ambiguous, not matched.
    """
    name = lead["identity"]["name"].strip().casefold()
    source = lead.get("source") if isinstance(lead.get("source"), dict) else {}
    ref = _repoRef(source.get("url", ""))
    inRepo = []
    if ref:
        for entry in entries:
            links = entry["fields"].get("links") if isinstance(entry["fields"].get("links"), dict) else {}
            other = _repoRef(links.get("github"))
            if other and other[0] == ref[0]:
                inRepo.append((entry, other))
    ambiguous = None
    byRepo: set[str] = set()
    if ref and ref[1]:
        byRepo = {e["skillId"] for e, other in inRepo if other[1] == ref[1]}
    elif ref and len(inRepo) == 1:
        byRepo = {inRepo[0][0]["skillId"]}
    elif ref and len(inRepo) > 1:
        ambiguous = {"repository": ref[0], "entries": len(inRepo), "note": "bare repository URL matches several registry skills; not treated as the challenger itself"}
    found = []
    for entry in entries:
        via = []
        if str(entry["fields"].get("name", "")).strip().casefold() == name:
            via.append("name")
        if entry["skillId"] in byRepo:
            via.append("repository")
        if via:
            found.append({"kind": entry["kind"], "skillId": entry["skillId"], "genericSkillId": entry["genericSkillId"], "via": via, "path": entry["path"]})
    return found, ambiguous


def _similarityPairs(repo_root: Path) -> dict[str, dict[str, float]]:
    path = repo_root / "registry" / "similarity.json"
    neighbors: dict[str, dict[str, float]] = {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return neighbors
    for pair in data.get("pairs", []) if isinstance(data, dict) else []:
        if isinstance(pair, dict) and isinstance(pair.get("a"), str) and isinstance(pair.get("b"), str) and isinstance(pair.get("score"), (int, float)):
            neighbors.setdefault(pair["a"], {})[pair["b"]] = float(pair["score"])
            neighbors.setdefault(pair["b"], {})[pair["a"]] = float(pair["score"])
    return neighbors


def match_candidates(lead: dict[str, Any], repo_root: str | Path, *, top: int = 5) -> dict[str, Any]:
    """Rank registry targets for a lead. Output is advisory and `frontier-match-v1` shaped."""
    _requireLeadShape(lead, (("identity", "name"), ("capability", "claim"), ("capability", "task"), ("comparison", "comparator")))
    if not isinstance(top, int) or isinstance(top, bool) or not 1 <= top <= 50:
        raise ValueError("top must be an integer between 1 and 50")
    root = Path(repo_root).resolve()
    entries, registryDigest, fileCount = loadRegistryEntries(root)
    challengers, ambiguousRepository = findRegisteredChallenger(lead, entries)
    challengerIds = {item["skillId"] for item in challengers}
    challengerBuckets = {item["genericSkillId"] for item in challengers}
    queryText = " ".join((lead["identity"]["name"], lead["capability"]["claim"], lead["capability"]["task"], lead["comparison"]["comparator"]))
    query = sorted(set(tokenize(queryText)))
    docs = [(entry, _docTokens(entry)) for entry in entries if entry["skillId"] not in challengerIds]
    docFreq = Counter(token for _, tokens in docs for token in tokens)
    count = max(len(docs), 1)
    avgLen = (sum(sum(tokens.values()) for _, tokens in docs) / count) or 1.0
    idf = {token: math.log(1 + (count - docFreq[token] + 0.5) / (docFreq[token] + 0.5)) for token in query}
    ceiling = sum(idf.values()) * (K1 + 1) or 1.0
    neighbors = _similarityPairs(root)
    scored = []
    for entry, tokens in docs:
        length, raw, matched = sum(tokens.values()), 0.0, []
        for token in query:
            tf = tokens.get(token, 0)
            if tf:
                raw += idf[token] * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * length / avgLen))
                matched.append(token)
        if raw > 0:
            scored.append((round(raw / ceiling, 4), entry, sorted(matched, key=lambda t: (-idf[t], t))))
    scored.sort(key=lambda row: (-row[0], row[1]["kind"], row[1]["skillId"]))
    candidates = []
    for rank, (score, entry, matched) in enumerate(scored[:top], 1):
        signals = [{"signal": "lexical-overlap", "terms": matched[:8]}]
        parts = [f"lexical overlap on {', '.join(matched[:5])}"]
        if entry["kind"] == "named":
            parts.append(f"named implementation of generic {entry['genericSkillId']}")
        if entry["genericSkillId"] in challengerBuckets:
            parts.append("same generic bucket as the registered challenger")
            signals.append({"signal": "challenger-bucket"})
        near = sorted((sid, s) for sid, s in neighbors.get(entry["skillId"], {}).items() if sid in challengerIds | challengerBuckets)
        if near:
            signals.append({"signal": "similarity-index", "with": [sid for sid, _ in near]})
            parts.append("registry similarity index links it to the challenger")
        candidates.append({"rank": rank, "kind": entry["kind"], "skillId": entry["skillId"], "genericSkillId": entry["genericSkillId"], "score": score, "signals": signals, "rationale": "; ".join(parts) + "."})
    declared = lead.get("target") if isinstance(lead.get("target"), dict) else None
    declaredReport = None
    if declared and isinstance(declared.get("skillId"), str):
        position = next((row for row in range(len(scored)) if scored[row][1]["skillId"] == declared["skillId"]), None)
        declaredReport = {"skillId": declared["skillId"], "kind": declared.get("kind"), "exists": any(e["skillId"] == declared["skillId"] for e in entries), "contentRank": None if position is None else position + 1}
    if challengers:
        note = "The challenger is already a registry skill; it is excluded from the ranked targets and its bucket is flagged."
    elif candidates:
        note = "Ranked by lexical overlap between the lead's claim and registry text; a human or Meta audit must still choose any target."
        if ambiguousRepository:
            note += f" The source repository holds {ambiguousRepository['entries']} registry skills, so no single registered challenger was assumed."
    else:
        note = f"No registry text among {len(entries)} entries overlaps the lead's claim; no candidate is suggested. If that is unexpected, confirm --repo-root points at the checkout."
    return {
        "schemaVersion": MATCH_SCHEMA,
        "advisory": True,
        "authority": MATCH_AUTHORITY,
        "leadId": lead.get("leadId"),
        "method": MATCH_METHOD,
        "query": query,
        "registeredElsewhere": bool(challengers),
        "registeredAs": challengers,
        "ambiguousRepository": ambiguousRepository,
        "declaredTarget": declaredReport,
        "candidates": candidates,
        "rationale": note,
        "registry": {"digest": registryDigest, "files": fileCount, "readOnly": True},
    }


def _subjectKey(lead: dict[str, Any]) -> str | None:
    try:
        identity = lead["identity"]
        return hashlib.sha256("\0".join((identity["name"].strip().casefold(), str(identity["version"]).casefold(), canonical_source_url(lead["source"]["url"]))).encode()).hexdigest()
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _leadKey(lead: dict[str, Any]) -> str | None:
    try:
        return dedupe_key(lead)
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def dedupe_against_ledger(lead: dict[str, Any], repo_root: str | Path, *, exclude: str | Path | None = None) -> dict[str, Any]:
    """Compare a lead against committed `evidence/frontier-challenges/*/lead.json` records.

    `duplicates` share the full dedupe key (identity, version, source, task, target
    identity and revision); timestamps and recorded `dedupe` blocks are ignored.
    `related` share only the challenger subject. A ledger record is a prior
    observation, not an assertion that the claim was substantiated.
    """
    _requireLeadShape(lead, (("identity", "name"), ("source", "url")))
    root = Path(repo_root).resolve()
    excluded = Path(exclude).resolve() if exclude else None
    key, subject = _leadKey(lead), _subjectKey(lead)
    duplicates, related, skipped, scanned = [], [], [], 0
    for path in sorted(root.glob(LEDGER_GLOB)):
        relative = path.relative_to(root).as_posix()
        if excluded is not None and path.resolve() == excluded:
            continue
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("ledger lead is a symlink or outside the checkout")
            if path.stat().st_size > MAX_LEAD_BYTES:
                raise ValueError("ledger lead exceeds bounded size")
            existing = json.loads(path.read_bytes())
            if not isinstance(existing, dict):
                raise ValueError("ledger lead is not a JSON object")
        except (OSError, ValueError) as exc:
            skipped.append({"path": relative, "reason": str(exc)})
            continue
        scanned += 1
        item = {"caseId": path.parent.name, "path": relative, "leadId": existing.get("leadId")}
        if key is not None and _leadKey(existing) == key:
            duplicates.append({**item, "match": "dedupe-key"})
        elif subject is not None and _subjectKey(existing) == subject:
            related.append({**item, "match": "same-challenger-subject"})
    return {
        "schemaVersion": DEDUPE_SCHEMA,
        "advisory": True,
        "authority": "advisory duplicate check; a prior ledger record is not verification and does not block Meta review",
        "leadId": lead.get("leadId"),
        "dedupeKey": key,
        "keyBasis": "full" if key else "subject-only (lead has no complete target)",
        "isDuplicate": bool(duplicates),
        "duplicates": duplicates,
        "related": related,
        "ledger": {"glob": LEDGER_GLOB, "present": (root / "evidence" / "frontier-challenges").is_dir(), "scanned": scanned, "skipped": skipped},
    }


def loadLeadFile(path: str | Path) -> dict[str, Any]:
    """Bounded JSON read for CLI use."""
    path = Path(path)
    if path.stat().st_size > MAX_LEAD_BYTES:
        raise ValueError("lead file exceeds bounded size")
    data = json.loads(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError("lead must be a JSON object")
    return data

