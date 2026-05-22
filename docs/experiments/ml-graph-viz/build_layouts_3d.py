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
from pathlib import Path
import numpy as np
from scipy import linalg

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "registry" / "gaia.json"
EMBEDDINGS = ROOT / "graph" / "embeddings.json"
OUT = Path(__file__).resolve().parent / "layouts_3d.json"

def normalize_4d(coords: np.ndarray) -> np.ndarray:
    coords = coords - coords.mean(axis=0)
    span = np.abs(coords).max() or 1.0
    return coords / span

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

def main():
    if not REGISTRY.exists(): return
    with open(REGISTRY, "r") as f:
        registry_data = json.load(f)
    
    skills = registry_data["skills"]
    ids = [s["id"] for s in skills]

    # Deterministic 4D (Mock)
    l_deterministic = deterministic_layout_4d(skills)
    
    # Semantic 4D (Embeddings)
    l_semantic = l_deterministic
    clusters = [0] * len(ids)
    centroids_4d = [] # Export centroids for Hyperplane visualization
    
    if EMBEDDINGS.exists():
        with open(EMBEDDINGS, "r") as f:
            emb_data = json.load(f)
        emb_map = {e["id"]: e["vector"] for e in emb_data["entries"]}
        vectors_list = [emb_map[sid] for sid in ids if sid in emb_map]
        
        if vectors_list:
            vectors = np.array(vectors_list)
            # 1. Run K-Means in high-D space
            labels, centroids_highd = run_kmeans(vectors, k=8)
            
            # 2. Project everything to 4D using same PCA
            l_semantic_raw, mean, components = compute_pca_4d(vectors)
            l_semantic = np.zeros((len(ids), 4))
            
            # Project centroids using the SAME PCA mapping
            centroids_4d_raw = np.dot(centroids_highd - mean, components.T)
            # Normalize centroids same as points
            span = np.abs(l_semantic_raw).max() or 1.0
            centroids_4d = (centroids_4d_raw / span).tolist()
            
            v_idx = 0
            for i, sid in enumerate(ids):
                if sid in emb_map:
                    l_semantic[i] = l_semantic_raw[v_idx] / span
                    clusters[i] = int(labels[v_idx])
                    v_idx += 1
                else: l_semantic[i] = l_deterministic[i]
    
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
        l_spectral = normalize_4d(evecs[:, 1:5])
    except: l_spectral = l_deterministic

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

    nodes = []
    for i, s in enumerate(skills):
        nodes.append({
            "id": s["id"], "name": s["name"], "type": s.get("type", "basic"),
            "cluster": clusters[i], "clusterName": cluster_names.get(str(clusters[i]), "Unknown"),
            "positions": {
                "deterministic": l_deterministic[i].tolist(),
                "spectral": l_spectral[i].tolist(),
                "semantic": l_semantic[i].tolist()
            }
        })

    edges = []
    for s in skills:
        for p in s.get("prerequisites", []):
            if p in id_to_idx: edges.append({"source": p, "target": s["id"]})

    payload = {
        "version": registry_data.get("version"),
        "layoutOrder": ["deterministic", "spectral", "semantic"],
        "clusterNames": cluster_names,
        "centroids": centroids_4d, # 4D Hyperplane anchors
        "nodes": nodes,
        "edges": edges
    }
    with open(OUT, "w") as f: json.dump(payload, f, indent=2)
    print(f"Wrote 4D Hyper-Atlas + Decision Centroids to {OUT.name}")


if __name__ == "__main__":
    main()
