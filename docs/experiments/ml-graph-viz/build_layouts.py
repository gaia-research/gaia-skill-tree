"""Compute three candidate layouts for the Gaia skill graph and emit a single
JSON file the HTML sampler can render.

Layouts:
  1. spring     — networkx force-directed (the visual baseline)
  2. spectral   — Laplacian eigenmaps on the prerequisite/derivative graph
                  (structure-aware ML embedding)
  3. semantic   — TF-IDF over skill descriptions + TruncatedSVD to 2D
                  (meaning-aware embedding, ignores edges)

Communities are detected once with the Louvain method on the structural graph
and reused across all three layouts so colors stay comparable.
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import SpectralEmbedding

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "registry" / "gaia.json"
OUT = Path(__file__).resolve().parent / "layouts.json"


def normalize(coords: np.ndarray) -> np.ndarray:
    coords = coords - coords.mean(axis=0)
    span = np.abs(coords).max() or 1.0
    return coords / span


def build_graph(skills: list[dict]) -> nx.Graph:
    g = nx.Graph()
    for s in skills:
        g.add_node(s["id"])
    for s in skills:
        for p in s.get("prerequisites", []) or []:
            if p in g:
                g.add_edge(s["id"], p, kind="prereq")
        for d in s.get("derivatives", []) or []:
            if d in g:
                g.add_edge(s["id"], d, kind="deriv")
    return g


def spring_layout(g: nx.Graph, ids: list[str]) -> np.ndarray:
    pos = nx.spring_layout(g, seed=7, k=1.2 / np.sqrt(len(ids)), iterations=200)
    return normalize(np.array([pos[i] for i in ids]))


def spectral_layout(g: nx.Graph, ids: list[str]) -> np.ndarray:
    # Spectral embedding requires a connected component; fall back to the
    # giant component and place isolates on a ring around the result.
    components = sorted(nx.connected_components(g), key=len, reverse=True)
    giant = g.subgraph(components[0]).copy()
    giant_ids = [i for i in ids if i in giant]
    embed = SpectralEmbedding(n_components=2, affinity="precomputed", random_state=7)
    adj = nx.to_numpy_array(giant, nodelist=giant_ids)
    coords_giant = embed.fit_transform(adj)
    out = np.zeros((len(ids), 2))
    pos = {nid: coords_giant[idx] for idx, nid in enumerate(giant_ids)}
    isolates = [i for i in ids if i not in pos]
    radius = float(np.abs(coords_giant).max()) * 1.25 if len(coords_giant) else 1.0
    for k, nid in enumerate(isolates):
        theta = 2 * np.pi * k / max(len(isolates), 1)
        pos[nid] = np.array([np.cos(theta) * radius, np.sin(theta) * radius])
    for i, nid in enumerate(ids):
        out[i] = pos[nid]
    return normalize(out)


def semantic_layout(skills: list[dict], ids: list[str]) -> np.ndarray:
    by_id = {s["id"]: s for s in skills}
    docs = [
        f"{by_id[i].get('name', '')}. {by_id[i].get('description', '')}"
        for i in ids
    ]
    vec = TfidfVectorizer(stop_words="english", min_df=1, max_features=4096)
    tfidf = vec.fit_transform(docs)
    svd = TruncatedSVD(n_components=2, random_state=7)
    coords = svd.fit_transform(tfidf)
    return normalize(coords)


def detect_communities(g: nx.Graph, ids: list[str]) -> dict[str, int]:
    try:
        from networkx.algorithms.community import louvain_communities

        groups = louvain_communities(g, seed=7)
    except Exception:
        groups = list(nx.connected_components(g))
    cid: dict[str, int] = {}
    for idx, group in enumerate(groups):
        for nid in group:
            cid[nid] = idx
    # any node never reached gets its own bucket
    next_id = len(groups)
    for nid in ids:
        if nid not in cid:
            cid[nid] = next_id
            next_id += 1
    return cid


def main() -> None:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    skills = data["skills"]
    ids = [s["id"] for s in skills]
    g = build_graph(skills)

    layouts = {
        "spring": spring_layout(g, ids).tolist(),
        "spectral": spectral_layout(g, ids).tolist(),
        "semantic": semantic_layout(skills, ids).tolist(),
    }
    communities = detect_communities(g, ids)

    nodes = []
    for i, s in enumerate(skills):
        nodes.append(
            {
                "id": s["id"],
                "name": s["name"],
                "type": s.get("type", "basic"),
                "level": s.get("level", "0★"),
                "description": s.get("description", ""),
                "degree": g.degree(s["id"]),
                "community": communities[s["id"]],
                "positions": {k: layouts[k][i] for k in layouts},
            }
        )

    edges = [
        {"source": u, "target": v, "kind": d.get("kind", "prereq")}
        for u, v, d in g.edges(data=True)
    ]

    payload = {
        "version": data.get("version"),
        "generatedFrom": "registry/gaia.json",
        "layoutOrder": ["spring", "spectral", "semantic"],
        "layoutLabels": {
            "spring": "Force-directed (baseline)",
            "spectral": "Laplacian eigenmaps (graph ML)",
            "semantic": "TF-IDF + SVD (semantic ML)",
        },
        "layoutBlurbs": {
            "spring": "Classic physics simulation. No ML — included as the visual baseline.",
            "spectral": "Eigenvectors of the graph Laplacian. Skills with similar prerequisite/derivative neighborhoods land near each other.",
            "semantic": "TF-IDF over skill descriptions, then SVD to 2D. Edges are ignored — meaning alone drives the layout.",
        },
        "nodes": nodes,
        "edges": edges,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} — {len(nodes)} nodes, {len(edges)} edges")


if __name__ == "__main__":
    main()
