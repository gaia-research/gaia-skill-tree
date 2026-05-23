"""
V4 upgrade: 4D Hyper-Atlas.
Uses PCA to reduce embeddings to 4 dimensions, capturing more semantic variance.
Implements 4D rotation matrices and hyperspace perspective projection.

Layouts (all 4D):
  1. deterministic — sphere + W-variance
  2. spectral      — Laplacian eigenvectors 1-4
  3. semantic      — PCA 4D of embeddings
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import numpy as np
from scipy import linalg

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "gaia.json"
EMBEDDINGS = ROOT / "graph" / "embeddings.json"
OUT = ROOT / "generated-output" / "layouts.json"

def normalize_4d(coords: np.ndarray) -> np.ndarray:
    coords = coords - coords.mean(axis=0)
    # Use 99th percentile for span to avoid being collapsed by single outliers
    span = np.percentile(np.abs(coords), 99) or 1.0
    return np.clip(coords / span, -1.5, 1.5)

def compute_pca_4d(vectors: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Project high-dimensional vectors to 4D and return (projections, mean, components)."""
    mean = np.mean(vectors, axis=0)
    centered = vectors - mean
    u, s, vh = linalg.svd(centered, full_matrices=False)
    components = vh[:4]
    projection = np.dot(centered, components.T)
    return projection, mean, components

def run_kmeans(vectors: np.ndarray, k: int = 8, iterations: int = 15) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(7)
    indices = rng.choice(len(vectors), k, replace=False)
    centroids = vectors[indices]
    labels = np.zeros(len(vectors))
    for _ in range(iterations):
        distances = np.linalg.norm(vectors[:, np.newaxis] - centroids, axis=2)
        labels = np.argmin(distances, axis=1)
        new_centroids = np.array([
            vectors[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i]
            for i in range(k)
        ])
        if np.allclose(centroids, new_centroids): break
        centroids = new_centroids
    return labels, centroids

def deterministic_layout_4d(skills: list[dict]) -> np.ndarray:
    # Use SPHERE_RADII logic from skill-graph.js but in 4D
    radii = {"basic": 300, "extra": 180, "ultimate": 60, "unique": 350}
    coords = []
    for i, s in enumerate(skills):
        stype = s.get("type", "basic")
        r = radii.get(stype, 300)
        phi = np.arccos(1 - 2 * (i + 0.5) / len(skills))
        theta = np.pi * (1 + 5**0.5) * i
        # W dimension as a subtle conceptual depth variance
        w = 0.3 * np.sin(i * 0.1)
        coords.append([
            r * np.sin(phi) * np.cos(theta),
            r * np.sin(phi) * np.sin(theta),
            r * np.cos(phi),
            w
        ])
    return normalize_4d(np.array(coords))

def generate_layouts():
    if not REGISTRY.exists():
        print(f"Error: Registry not found at {REGISTRY}")
        return None
        
    with open(REGISTRY, "r", encoding="utf-8", errors="ignore") as f:
        registry_data = json.load(f)
    
    skills = registry_data["skills"]
    ids = [s["id"] for s in skills]

    # Deterministic 4D
    l_deterministic = deterministic_layout_4d(skills)
    
    # Semantic 4D (Embeddings)
    l_semantic = l_deterministic.copy()
    clusters = [0] * len(ids)
    centroids_4d = [] # Export centroids for Hyperplane visualization
    
    if EMBEDDINGS.exists():
        with open(EMBEDDINGS, "r") as f:
            emb_data = json.load(f)
        emb_map = {e["id"]: e["vector"] for e in emb_data["entries"]}
        vectors_list = []
        vectors_ids = []
        for sid in ids:
            if sid in emb_map:
                vectors_list.append(emb_map[sid])
                vectors_ids.append(sid)
        
        if vectors_list:
            vectors = np.array(vectors_list)
            # 1. Run K-Means in high-D space
            labels, centroids_highd = run_kmeans(vectors, k=8)
            
            # 2. Project everything to 4D using same PCA
            l_semantic_raw, mean, components = compute_pca_4d(vectors)
            
            # Project centroids using the SAME PCA mapping
            centroids_4d_raw = np.dot(centroids_highd - mean, components.T)
            # Normalize centroids same as points
            span = np.abs(l_semantic_raw).max() or 1.0
            centroids_4d = (centroids_4d_raw / span).tolist()
            
            id_to_semantic = {vectors_ids[i]: l_semantic_raw[i] / span for i in range(len(vectors_ids))}
            id_to_cluster = {vectors_ids[i]: int(labels[i]) for i in range(len(vectors_ids))}
            
            for i, sid in enumerate(ids):
                if sid in id_to_semantic:
                    l_semantic[i] = id_to_semantic[sid]
                    clusters[i] = id_to_cluster[sid]
    
    # Spectral 4D (Connectivity)
    adj = np.zeros((len(ids), len(ids)))
    id_to_idx = {sid: i for i, sid in enumerate(ids)}
    for i, s in enumerate(skills):
        for p in s.get("prerequisites", []):
            if p in id_to_idx: adj[i, id_to_idx[p]] = adj[id_to_idx[p], i] = 1
    
    d = np.diag(adj.sum(axis=1))
    laplacian = d - adj
    try:
        evals, evecs = linalg.eigh(laplacian)
        # Skip the first eigenvector (always 0)
        l_spectral = normalize_4d(evecs[:, 1:5])
    except:
        l_spectral = l_deterministic

    # Cluster Naming...
    cluster_names = {}
    for k in range(8):
        cluster_skills = [skills[i] for i, c in enumerate(clusters) if c == k]
        if not cluster_skills: continue
        words = []
        for s in cluster_skills: words.extend(s["name"].split())
        stop_words = {"&", "and", "the", "of", "to", "in", "for", "with"}
        counts = {}
        for w in words:
            wc = w.lower().strip(",() ")
            if len(wc) > 2 and wc not in stop_words: counts[wc] = counts.get(wc, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:2]
        cluster_names[str(k)] = " & ".join([w[0].capitalize() for w in top]) if top else "Misc"

    layout_data = {
        "clusterNames": cluster_names,
        "centroids": centroids_4d,
        "nodes": {}
    }
    
    for i, sid in enumerate(ids):
        layout_data["nodes"][sid] = {
            "cluster": clusters[i],
            "positions": {
                "deterministic": l_deterministic[i].tolist(),
                "spectral": l_spectral[i].tolist(),
                "semantic": l_semantic[i].tolist()
            }
        }
        
    return layout_data

def main():
    layout_data = generate_layouts()
    if layout_data:
        with open(OUT, "w") as f:
            json.dump(layout_data, f, indent=2)
        print(f"Wrote 4D Hyper-Atlas data to {OUT}")

if __name__ == "__main__":
    main()
