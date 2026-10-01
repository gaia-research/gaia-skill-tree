"""Semantic search over pre-computed Gaia skill embeddings.

Loads registry/embeddings.json and ranks skills by cosine similarity to a query.
Validates vector dimensions, non-finite values, and model consistency.
"""

from __future__ import annotations

import copy
import json
import math
import os
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
    normalize_pooling_mode,
    semanticFingerprint,
    semantic_fingerprint,
    validateEmbeddingsData,
    validateVector,
    validate_vector,
    verify_model_pooling,
)


def load_embeddings(embeddings_path: str, validate: bool = True) -> dict[str, Any]:
    """Load registry/embeddings.json.

    Returns the full parsed dict:
    {
        "model": str,
        "dimensions": int,
        "generatedAt": str,
        "fingerprint": Optional[str],
        "config": Optional[dict],
        "entries": [{"id": str, "vector": [float, ...]}, ...]
    }

    Legacy artifacts without fingerprints are loadable. If validate=True,
    vector structure, dimensions, and numerical finiteness are validated.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If file content is invalid JSON, dimensions mismatch,
            or vectors contain non-finite numbers.
    """
    if not os.path.exists(embeddings_path):
        raise FileNotFoundError(
            f"Embeddings file not found: {embeddings_path}\n"
            "Run `gaia dev embed` to generate it first."
        )
    with open(embeddings_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if validate:
        validateEmbeddingsData(data)

    return data


def cosine_similarity(a: Sequence[Any], b: Sequence[Any]) -> float:
    """Compute cosine similarity between two vectors.

    Validates that vectors have equal dimensions and contain finite numbers.
    Rejects booleans, empty vectors, and dimension mismatches.
    Uses numpy when available; falls back to pure Python otherwise.

    Raises:
        ValueError: On dimension mismatch, non-finite elements, or boolean values.
    """
    if not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple)):
        raise ValueError("Inputs to cosine_similarity must be lists or tuples")
    if isinstance(a, (str, bytes, bool)) or isinstance(b, (str, bytes, bool)):
        raise ValueError("Inputs to cosine_similarity must be numeric vectors")
    if len(a) == 0 or len(b) == 0:
        raise ValueError("Vectors must not be empty (zero dimensions)")
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} != {len(b)}")

    for idx, x in enumerate(a):
        if isinstance(x, bool):
            raise ValueError(f"Vector 'a' element at index {idx} contains boolean value: {x!r}")
        if not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError(f"Vector 'a' element at index {idx} contains non-finite value: {x!r}")
    for idx, y in enumerate(b):
        if isinstance(y, bool):
            raise ValueError(f"Vector 'b' element at index {idx} contains boolean value: {y!r}")
        if not isinstance(y, (int, float)) or not math.isfinite(y):
            raise ValueError(f"Vector 'b' element at index {idx} contains non-finite value: {y!r}")

    try:
        import numpy as np

        a_arr = np.array(a, dtype=float)
        b_arr = np.array(b, dtype=float)
        norm_a = float(np.linalg.norm(a_arr))
        norm_b = float(np.linalg.norm(b_arr))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
    except ImportError:
        # Pure Python fallback with strict zip
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


def embed_query(
    query: str,
    model_name: Optional[str] = None,
    revision: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
) -> list[float]:
    """Embed a single query string using sentence-transformers.

    Reuses model objects from cache and applies queryPrefix and normalization
    defined in retrieval configuration.

    Returns:
        list of floats (the embedding vector).
    Raises:
        ImportError: If sentence-transformers is missing.
        ValueError: If query is empty or produces non-finite vector.
    """
    if config is None:
        cfg = loadRetrievalConfig(modelName=model_name)
    else:
        cfg = config

    modelId = cfg.get("modelId") or cfg.get("model") or model_name or cfg.get("defaultModel")
    rev = revision if revision is not None else cfg.get("revision")
    backend = cfg.get("backend", "torch")
    queryPrefix = cfg.get("queryPrefix") or cfg.get("query_prefix", "")
    normalize = bool(cfg.get("normalize", True))
    pooling = cfg.get("pooling")

    model = getSentenceTransformer(modelId, revision=rev, backend=backend, pooling=pooling)
    if pooling:
        verify_model_pooling(model, pooling, model_id=str(modelId))

    formattedQuery = (queryPrefix or "") + query
    try:
        rawVector = model.encode(
            [formattedQuery],
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )[0]
    except TypeError:
        try:
            rawVector = model.encode([formattedQuery], convert_to_numpy=True)[0]
        except TypeError:
            rawVector = model.encode([formattedQuery])[0]

    vectorList = rawVector.tolist() if hasattr(rawVector, "tolist") else list(rawVector)
    if normalize:
        norm = math.sqrt(sum(x * x for x in vectorList))
        if norm > 0.0 and abs(norm - 1.0) > 1e-4:
            vectorList = [x / norm for x in vectorList]

    validateVector(vectorList, label="Query vector")
    return vectorList


def search(
    query: str,
    embeddings_path: str,
    top_k: int = 10,
    config: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Embed a query string and return the top-K most similar skills.

    Uses full stored artifact config to encode query. Validates that any
    explicit query configuration matches the artifact's semantic configuration.

    Args:
        query: plain-text search query
        embeddings_path: path to registry/embeddings.json
        top_k: number of results to return
        config: optional retrieval configuration dict

    Returns:
        list of {"id": str, "score": float} sorted by score descending
    """
    embeddings = load_embeddings(embeddings_path)
    storedConfig = embeddings.get("config")
    if isinstance(storedConfig, dict):
        effective_config = copy.deepcopy(storedConfig)
    else:
        effective_config = {
            "dimensions": embeddings.get("dimensions"),
            "modelId": embeddings.get("model", "all-MiniLM-L6-v2"),
        }

    if config is not None:
        callerModel = config.get("modelId") or config.get("model")
        artModel = effective_config.get("modelId") or embeddings.get("model")
        if callerModel and artModel and callerModel != artModel:
            raise ValueError(
                f"Model mismatch: query config specifies '{callerModel}', "
                f"but embeddings artifact was built with '{artModel}'"
            )

        callerRev = config.get("revision")
        artRev = effective_config.get("revision")
        if callerRev is not None and artRev is not None and callerRev != artRev:
            raise ValueError(
                f"Semantic configuration mismatch: query config specifies revision '{callerRev}', "
                f"but embeddings artifact was built with revision '{artRev}'"
            )

        callerDim = config.get("dimensions")
        artDim = effective_config.get("dimensions") or embeddings.get("dimensions")
        if callerDim is not None and artDim is not None and callerDim != artDim:
            raise ValueError(
                f"Semantic configuration mismatch: query config specifies dimensions {callerDim}, "
                f"but embeddings artifact was built with dimensions {artDim}"
            )

        callerNorm = config.get("normalize")
        artNorm = effective_config.get("normalize")
        if callerNorm is not None and artNorm is not None and bool(callerNorm) != bool(artNorm):
            raise ValueError(
                f"Semantic configuration mismatch: query config specifies normalize={callerNorm}, "
                f"but embeddings artifact was built with normalize={artNorm}"
            )

        callerPool = config.get("pooling")
        artPool = effective_config.get("pooling")
        if callerPool is not None and artPool is not None:
            if normalize_pooling_mode(callerPool) != normalize_pooling_mode(artPool):
                raise ValueError(
                    f"Semantic configuration mismatch: query config specifies pooling='{callerPool}', "
                    f"but embeddings artifact was built with pooling='{artPool}'"
                )

        callerPrefix = config.get("queryPrefix") or config.get("query_prefix")
        artPrefix = effective_config.get("queryPrefix") or effective_config.get("query_prefix", "")
        if callerPrefix is not None and callerPrefix != artPrefix:
            raise ValueError(
                f"Semantic configuration mismatch: query config specifies queryPrefix='{callerPrefix}', "
                f"but embeddings artifact was built with queryPrefix='{artPrefix}'"
            )

        callerBackend = config.get("backend")
        artBackend = effective_config.get("backend")
        if callerBackend is not None and artBackend is not None and callerBackend != artBackend:
            raise ValueError(
                f"Semantic configuration mismatch: query config specifies backend='{callerBackend}', "
                f"but embeddings artifact was built with backend='{artBackend}'"
            )

    query_vector = embed_query(query, config=effective_config)
    return search_precomputed(query_vector, embeddings, top_k=top_k)


def search_precomputed(
    query_vector: Sequence[Any],
    embeddings: Mapping[str, Any],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Search using a pre-computed query vector against loaded embeddings.

    Validates query vector and every entry vector against non-finite values,
    booleans, zero dimension, and dimension mismatch, preventing pure-Python
    zip truncation.

    Args:
        query_vector: list of floats representing the query embedding
        embeddings: dict loaded from registry/embeddings.json
        top_k: number of results to return

    Returns:
        list of {"id": str, "score": float} sorted by score descending
    """
    validateVector(query_vector, label="Query vector")
    queryDim = len(query_vector)

    declaredDim = embeddings.get("dimensions")
    if declaredDim is not None and queryDim != declaredDim:
        raise ValueError(
            f"Query vector dimension ({queryDim}) does not match "
            f"embeddings declared dimensions ({declaredDim})"
        )

    entries = embeddings.get("entries", [])
    if not entries:
        return []

    for idx, val in enumerate(query_vector):
        if isinstance(val, bool):
            raise ValueError(f"Query vector element at index {idx} contains boolean value: {val!r}")
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            raise ValueError(f"Query vector element at index {idx} contains non-finite value: {val!r}")

    # Validate each entry vector explicitly to prevent pure-Python zip truncation
    for entry in entries:
        vec = entry.get("vector")
        if not isinstance(vec, (list, tuple)) or isinstance(vec, (str, bytes, bool)):
            raise ValueError(f"Embedding entry '{entry.get('id')}' vector must be a list")
        if len(vec) != queryDim:
            raise ValueError(
                f"Embedding vector dimension ({len(vec)}) does not match "
                f"query vector dimension ({queryDim}) for skill '{entry.get('id')}'"
            )
        for idx, val in enumerate(vec):
            if isinstance(val, bool):
                raise ValueError(
                    f"Embedding vector for skill '{entry.get('id')}' contains boolean value at index {idx}: {val!r}"
                )
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(
                    f"Embedding vector for skill '{entry.get('id')}' contains non-finite value at index {idx}: {val!r}"
                )

    results: list[dict[str, Any]] = []

    try:
        import numpy as np

        q_arr = np.array(query_vector, dtype=float)
        norm_q = float(np.linalg.norm(q_arr))
        if norm_q == 0.0:
            return []

        vectors = np.array([e["vector"] for e in entries], dtype=float)
        norms = np.linalg.norm(vectors, axis=1)
        valid_mask = norms > 0.0

        if not np.any(valid_mask):
            return []

        dot_products = np.dot(vectors[valid_mask], q_arr)
        scores = dot_products / (norm_q * norms[valid_mask])

        valid_indices = np.where(valid_mask)[0]
        for i, score in zip(valid_indices, scores):
            results.append({"id": entries[i]["id"], "score": float(score)})

    except ImportError:
        # Pure Python fallback with strict zip preventing truncation
        norm_q = math.sqrt(sum(x * x for x in query_vector))
        if norm_q == 0.0:
            return []

        for entry in entries:
            vector = entry["vector"]
            norm_v = math.sqrt(sum(x * x for x in vector))
            if norm_v == 0.0:
                continue

            dot = sum(x * y for x, y in zip(query_vector, vector, strict=True))
            score = dot / (norm_q * norm_v)
            results.append({"id": entry["id"], "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
