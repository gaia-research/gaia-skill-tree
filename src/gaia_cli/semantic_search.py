"""Semantic search over pre-computed Gaia skill embeddings.

Loads registry/embeddings.json and ranks skills by cosine similarity to a query.
"""

import json
import math
import os


def load_embeddings(embeddings_path):
    """Load registry/embeddings.json.

    Returns the full parsed dict:
    {
        "model": str,
        "dimensions": int,
        "generatedAt": str,
        "entries": [{"id": str, "vector": [float, ...]}, ...]
    }
    Raises FileNotFoundError if the file does not exist.
    """
    if not os.path.exists(embeddings_path):
        raise FileNotFoundError(
            f"Embeddings file not found: {embeddings_path}\n"
            "Run `gaia embed` to generate it first."
        )
    with open(embeddings_path, "r", encoding="utf-8") as f:
        return json.load(f)


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors.

    Uses numpy when available; falls back to pure Python otherwise.
    """
    try:
        import numpy as np
        a_arr = np.array(a, dtype=float)
        b_arr = np.array(b, dtype=float)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
    except ImportError:
        # Pure Python fallback
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


def embed_query(query, model_name="all-MiniLM-L6-v2"):
    """Embed a single query string using sentence-transformers.

    Returns a list of floats (the embedding vector).
    Raises ImportError with a helpful message if sentence-transformers is missing.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        )
    model = SentenceTransformer(model_name)
    vector = model.encode([query], convert_to_numpy=True)[0]
    return vector.tolist()


def search(query, embeddings_path, top_k=10):
    """Embed a query string and return the top-K most similar skills.

    Args:
        query: plain-text search query
        embeddings_path: path to registry/embeddings.json
        top_k: number of results to return

    Returns:
        list of {"id": str, "score": float} sorted by score descending
    """
    embeddings = load_embeddings(embeddings_path)
    model_name = embeddings.get("model", "all-MiniLM-L6-v2")
    query_vector = embed_query(query, model_name=model_name)
    return search_precomputed(query_vector, embeddings, top_k=top_k)


def search_precomputed(query_vector, embeddings, top_k=10):
    """Search using a pre-computed query vector against loaded embeddings.

    Args:
        query_vector: list of floats representing the query embedding
        embeddings: dict loaded from registry/embeddings.json
        top_k: number of results to return

    Returns:
        list of {"id": str, "score": float} sorted by score descending
    """
    entries = embeddings.get("entries", [])
    if not entries:
        return []

    results = []

    try:
        import numpy as np

        q_arr = np.array(query_vector, dtype=float)
        norm_q = np.linalg.norm(q_arr)
        if norm_q == 0.0:
            return []

        # Get all vectors as matrix
        vectors = np.array([e["vector"] for e in entries], dtype=float)

        # Calculate norms of all vectors
        norms = np.linalg.norm(vectors, axis=1)

        # Mask out zero vectors
        valid_mask = norms > 0.0

        # Dot products
        dot_products = np.dot(vectors[valid_mask], q_arr)

        # Cosine similarities
        scores = dot_products / (norm_q * norms[valid_mask])

        # Map back to IDs
        valid_indices = np.where(valid_mask)[0]
        for i, score in zip(valid_indices, scores):
            results.append({"id": entries[i]["id"], "score": float(score)})

    except ImportError:
        # Optimized pure python fallback
        norm_q = math.sqrt(sum(x * x for x in query_vector))
        if norm_q == 0.0:
            return []

        for entry in entries:
            vector = entry["vector"]
            norm_v = math.sqrt(sum(x * x for x in vector))
            if norm_v == 0.0:
                continue

            dot = sum(x * y for x, y in zip(query_vector, vector))
            score = dot / (norm_q * norm_v)
            results.append({"id": entry["id"], "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
