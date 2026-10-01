"""Embedding generation for Gaia semantic search.

Uses sentence-transformers to embed skill descriptions.
Outputs to registry/embeddings.json for use by search and similarity tools.
Supports bounded retrieval configuration, semantic fingerprinting, and cache validation.
"""

from __future__ import annotations

import json
import math
import os
import re
from datetime import date
from typing import Any, Mapping, Optional, Sequence

from gaia_cli.curation.retrieval import (
    clearModelCache,
    clear_model_cache,
    embeddingStatus,
    embedding_status,
    getSentenceTransformer,
    get_sentence_transformer,
    loadRetrievalConfig,
    load_retrieval_config,
    saveEmbeddingsAtomic,
    save_embeddings_atomic,
    semanticFingerprint,
    semantic_fingerprint,
    validateVector,
    validate_vector,
    verify_model_pooling,
)
from gaia_cli.registry import (
    embeddings_path,
    named_skills_dir,
    registry_graph_path,
    registry_nodes_dir,
)


def loadNamedFrontmatter(mdText: str) -> dict[str, Any]:
    """Parse the YAML frontmatter block of a named-skill .md file.

    Returns a dict of the frontmatter fields, or an empty dict if no
    frontmatter is present. Mirrors the frontmatter-reading pattern used by
    treeManager._iter_manifest_refs: prefer PyYAML, fall back to a small
    pure-Python line parser when PyYAML is unavailable.
    """
    match = re.match(r"^---\n(.*?)\n---", mdText, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    try:
        import yaml
        return yaml.safe_load(block) or {}
    except ImportError:
        pass
    frontmatter: dict[str, Any] = {}
    for line in block.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1] in (" ", "\t", "-"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        frontmatter[key] = value
    return frontmatter


def load_skills(registry_path="."):
    """Load skills preferring canonical registry/nodes/, falling back to gaia.json.

    Canonical nodes under registry/nodes/ (basic/ and fusion/) are loaded first
    to detect fresh edits. Malformed canonical node files fail immediately with
    ValueError rather than being silently omitted.
    If canonical nodes are absent or empty, falls back to registry/gaia.json.
    Named skills from registry/named/ are also loaded.

    Returns a list of dicts with at least 'id', 'name', and 'description'.
    """
    skills: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1. Prefer canonical nodes under registry/nodes/ (basic/ and fusion/)
    nodes_dir = registry_nodes_dir(registry_path)
    canonical_loaded = False
    if os.path.isdir(nodes_dir):
        for dirpath, _dirnames, filenames in sorted(os.walk(nodes_dir)):
            for fname in sorted(filenames):
                if fname.endswith(".json"):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            node = json.load(f)
                    except Exception as exc:
                        raise ValueError(f"Malformed canonical node JSON at {fpath}: {exc}") from exc
                    if not isinstance(node, dict):
                        raise ValueError(f"Malformed canonical node at {fpath}: expected JSON object, got {type(node).__name__}")
                    sid = node.get("id")
                    if not sid or not isinstance(sid, str) or not sid.strip():
                        raise ValueError(f"Malformed canonical node at {fpath}: missing or invalid 'id'")
                    if sid not in seen:
                        seen.add(sid)
                        skills.append({
                            "id": sid,
                            "name": node.get("name", sid),
                            "description": str(node.get("description", "")),
                        })
                        canonical_loaded = True

    # 2. Fall back to gaia.json only when canonical nodes are absent or yielded no skills
    if not canonical_loaded:
        candidates = [
            registry_graph_path(registry_path),
            os.path.join(str(registry_path), "graph", "gaia.json"),
            os.path.join(str(registry_path), "docs", "graph", "gaia.json"),
        ]
        for gaia_path in candidates:
            if os.path.exists(gaia_path):
                try:
                    with open(gaia_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for skill in data.get("skills", []):
                        sid = skill.get("id")
                        if sid and sid not in seen:
                            seen.add(sid)
                            skills.append({
                                "id": sid,
                                "name": skill.get("name", sid),
                                "description": str(skill.get("description", "")),
                            })
                    break
                except Exception as exc:
                    print(f"Warning: could not load {gaia_path}: {exc}")

    # 3. Load named skills from registry/named/**/*.md (YAML frontmatter) and any legacy .json
    named_dir = named_skills_dir(registry_path)
    if os.path.isdir(named_dir):
        for dirpath, _dirnames, filenames in sorted(os.walk(named_dir)):
            for fname in sorted(filenames):
                fpath = os.path.join(dirpath, fname)
                if fname.endswith(".json"):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            skill = json.load(f)
                        sid = skill.get("id")
                        if sid and sid not in seen:
                            seen.add(sid)
                            skills.append({
                                "id": sid,
                                "name": skill.get("name", sid),
                                "description": str(skill.get("description", "")),
                            })
                    except Exception as exc:
                        print(f"Warning: could not load {fpath}: {exc}")
                elif fname.endswith(".md"):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            frontmatter = loadNamedFrontmatter(f.read())
                        sid = frontmatter.get("id")
                        if sid and sid not in seen:
                            seen.add(sid)
                            skills.append({
                                "id": sid,
                                "name": frontmatter.get("name", sid),
                                "description": str(frontmatter.get("description", "")),
                            })
                    except Exception as exc:
                        print(f"Warning: could not load {fpath}: {exc}")

    return skills


def embed_skills(
    skills: Sequence[Mapping[str, Any]],
    model_name: Optional[str] = None,
    revision: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
):
    """Generate embeddings for each skill using configured textTemplate.

    Returns a tuple of (entries, dimensions):
        entries: [{"id": ..., "vector": [...]}, ...]
        dimensions: int
    Reuses model objects from cache.
    Raises ImportError if sentence-transformers is missing.
    """
    if config is None:
        cfg = loadRetrievalConfig(modelName=model_name)
    else:
        cfg = config

    modelId = cfg.get("modelId") or cfg.get("model") or model_name or cfg.get("defaultModel")
    rev = revision if revision is not None else cfg.get("revision")
    backend = cfg.get("backend", "torch")
    template = cfg.get("textTemplate") or cfg.get("text_template", "{name}: {description}")
    normalize = bool(cfg.get("normalize", True))
    pooling = cfg.get("pooling")

    model = getSentenceTransformer(modelId, revision=rev, backend=backend, pooling=pooling)
    if pooling:
        verified_pooling = verify_model_pooling(model, pooling, model_id=str(modelId))
        cfg["pooling"] = verified_pooling

    texts = [
        template.format(
            name=skill.get("name", skill.get("id", "")),
            description=skill.get("description", ""),
        )
        for skill in skills
    ]

    print(f"Encoding {len(texts)} skills with '{modelId}'...", flush=True)
    try:
        vectors = model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
    except TypeError:
        try:
            vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        except TypeError:
            vectors = model.encode(texts)

    entries: list[dict[str, Any]] = []
    for skill, vector in zip(skills, vectors):
        vecList = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        if normalize:
            norm = math.sqrt(sum(x * x for x in vecList))
            if norm > 0.0 and abs(norm - 1.0) > 1e-4:
                vecList = [x / norm for x in vecList]
        validateVector(vecList, label=f"Skill '{skill.get('id')}'")
        entries.append({
            "id": skill["id"],
            "vector": vecList,
        })

    dimensions = len(entries[0]["vector"]) if entries else (cfg.get("dimensions") or 384)
    return entries, dimensions


def save_embeddings(
    entries: list[dict[str, Any]],
    output_path: str,
    model_name: Optional[str] = None,
    dimensions: Optional[int] = None,
    fingerprint: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
) -> None:
    """Write embeddings atomically to output_path.

    Args:
        entries: list of {"id": ..., "vector": [...]}
        output_path: path to write JSON file
        model_name: optional name of the model used to generate embeddings
        dimensions: embedding vector size
        fingerprint: optional semantic fingerprint string
        config: optional retrieval configuration dict
    """
    cfg = config
    if cfg is None and model_name is not None:
        try:
            cfg = loadRetrievalConfig(modelName=model_name)
        except Exception:
            cfg = None
    elif cfg is None and model_name is None:
        try:
            cfg = loadRetrievalConfig()
        except Exception:
            cfg = None

    resolvedModel = model_name or (cfg.get("modelId") or cfg.get("model") if cfg else None) or "all-MiniLM-L6-v2"
    resolvedDim = dimensions or (cfg.get("dimensions") if cfg else None) or (len(entries[0]["vector"]) if entries else 384)

    saveEmbeddingsAtomic(
        entries=entries,
        outputPath=output_path,
        modelName=resolvedModel,
        dimensions=resolvedDim,
        fingerprint=fingerprint,
        config=cfg,
    )
    print(f"Saved {len(entries)} embeddings to {output_path}")


def generate_embeddings(
    registry_path: str = ".",
    model_name: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
    force: bool = False,
    output_path: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Orchestrate the full embedding generation flow with cache reuse.

    Reuses unchanged fresh artifacts when force=False.
    Atomically writes artifact manifest and vectors when regenerating.
    """
    if config is None:
        cfg = loadRetrievalConfig(registry_path, modelName=model_name)
    else:
        cfg = config

    modelId = cfg.get("modelId") or cfg.get("model") or cfg.get("defaultModel")
    targetOutput = output_path or embeddings_path(registry_path)

    # Check existing status: reuse unchanged fresh artifact
    status = embeddingStatus(
        registryPath=registry_path,
        artifactPath=targetOutput,
        config=cfg,
    )
    if not force and status.get("status") == "fresh":
        fp = status.get("fingerprint") or ""
        fpShort = fp[:8] if fp else "unknown"
        print(f"Embeddings artifact is fresh ({fpShort}...). Reusing existing embeddings.")
        return status

    skills = load_skills(registry_path)
    if not skills:
        print("No skills found. Make sure the registry path is correct.")
        return None

    print(f"Loaded {len(skills)} skills from {registry_path}.")

    try:
        entries, dimensions = embed_skills(skills, model_name=modelId, config=cfg)
    except ImportError:
        print(
            "Error: sentence-transformers is not installed.\n"
            "Install it with:  pip install sentence-transformers"
        )
        return None

    fp = semanticFingerprint(skills, cfg)
    save_embeddings(
        entries=entries,
        output_path=targetOutput,
        model_name=modelId,
        dimensions=dimensions,
        fingerprint=fp,
        config=cfg,
    )
    return {
        "status": "fresh",
        "fingerprint": fp,
        "model": modelId,
        "path": targetOutput,
        "entriesCount": len(entries),
    }
