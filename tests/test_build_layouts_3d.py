import importlib.util
import json
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_layouts_3d.py"
SPEC = importlib.util.spec_from_file_location("build_layouts_3d", SCRIPT)
LAYOUTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAYOUTS)


SKILLS = [
    {"id": "alpha", "name": "Alpha", "prerequisites": []},
    {"id": "beta", "name": "Beta", "prerequisites": ["alpha"]},
    {"id": "gamma", "name": "Gamma", "prerequisites": ["beta"]},
    {"id": "delta", "name": "Delta", "prerequisites": []},
    {"id": "epsilon", "name": "Epsilon", "prerequisites": ["delta"]},
    {"id": "zeta", "name": "Zeta", "prerequisites": []},
    {"id": "eta", "name": "Eta", "prerequisites": []},
]


def _write_registry(path, skills):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"skills": skills}), encoding="utf-8")


def _write_previous_graph(path, skills, spectral=None):
    site_skills = []
    for index, skill in enumerate(skills):
        site_skills.append({
            **skill,
            "positions": {"spectral": (spectral or {}).get(skill["id"], [index + 0.1, index + 0.2, index + 0.3, index + 0.4])},
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"skills": site_skills}), encoding="utf-8")


def _generate(tmp_path, monkeypatch, skills):
    registry = tmp_path / "registry.json"
    _write_registry(registry, skills)
    monkeypatch.setattr(LAYOUTS, "REGISTRY", registry)
    monkeypatch.setattr(LAYOUTS, "EMBEDDINGS", tmp_path / "missing-embeddings.json")
    monkeypatch.setattr(LAYOUTS, "ROOT", tmp_path)
    return LAYOUTS.generate_layouts()


def _spectral_by_id(layout):
    return {skill_id: node["positions"]["spectral"] for skill_id, node in layout["nodes"].items()}


def test_prior_spectral_coordinates_are_preserved_for_unchanged_topology(tmp_path, monkeypatch):
    prior = {skill["id"]: [i / 10, i / 20, i / 30, i / 40] for i, skill in enumerate(SKILLS)}
    _write_previous_graph(tmp_path / "docs/graph/gaia.json", SKILLS, prior)

    layout = _generate(tmp_path, monkeypatch, list(reversed(SKILLS)))

    assert _spectral_by_id(layout) == prior


def test_changed_topology_recomputes_instead_of_reusing_prior_coordinates(tmp_path, monkeypatch):
    prior = {skill["id"]: [i / 10, i / 20, i / 30, i / 40] for i, skill in enumerate(SKILLS)}
    _write_previous_graph(tmp_path / "docs/graph/gaia.json", SKILLS, prior)
    changed = [dict(skill) for skill in SKILLS]
    changed[2] = {**changed[2], "prerequisites": ["alpha"]}
    original_eigh = LAYOUTS.linalg.eigh
    calls = []

    def recording_eigh(matrix):
        calls.append(matrix.copy())
        return original_eigh(matrix)

    monkeypatch.setattr(LAYOUTS.linalg, "eigh", recording_eigh)
    layout = _generate(tmp_path, monkeypatch, changed)

    assert len(calls) == 1
    assert _spectral_by_id(layout) != prior


def test_malformed_previous_positions_fall_back_to_recomputation(tmp_path, monkeypatch):
    malformed = [{**skill, "positions": None} for skill in SKILLS]
    previous_path = tmp_path / "docs/graph/gaia.json"
    previous_path.parent.mkdir(parents=True, exist_ok=True)
    previous_path.write_text(json.dumps({"skills": malformed}), encoding="utf-8")
    original_eigh = LAYOUTS.linalg.eigh
    calls = []

    def recording_eigh(matrix):
        calls.append(matrix.copy())
        return original_eigh(matrix)

    monkeypatch.setattr(LAYOUTS.linalg, "eigh", recording_eigh)
    layout = _generate(tmp_path, monkeypatch, SKILLS)

    assert len(calls) == 1
    assert all(len(vector) == 4 for vector in _spectral_by_id(layout).values())


def test_spectral_layout_stays_4d_for_fewer_than_five_nodes(tmp_path, monkeypatch):
    small_graph = [
        {"id": "alpha", "name": "Alpha", "prerequisites": None},
        {"id": "beta", "name": "Beta", "prerequisites": ["alpha"]},
        {"id": "gamma", "name": "Gamma", "prerequisites": []},
    ]
    layout = _generate(tmp_path, monkeypatch, small_graph)
    spectral = _spectral_by_id(layout)
    deterministic = {
        skill_id: node["positions"]["deterministic"]
        for skill_id, node in layout["nodes"].items()
    }

    assert spectral == deterministic
    assert all(len(vector) == 4 for vector in spectral.values())


def test_spectral_layout_is_repeatable_and_independent_of_registry_order(tmp_path, monkeypatch):
    # No matching prior artifact: exercise canonical sorted-ID computation.
    first = _generate(tmp_path, monkeypatch, SKILLS)
    original = _spectral_by_id(first)
    reordered = _spectral_by_id(_generate(tmp_path, monkeypatch, list(reversed(SKILLS))))
    repeated = _spectral_by_id(_generate(tmp_path, monkeypatch, SKILLS))

    for skill_id in original:
        np.testing.assert_allclose(reordered[skill_id], original[skill_id], atol=1e-10, rtol=0)
        np.testing.assert_allclose(repeated[skill_id], original[skill_id], atol=1e-10, rtol=0)
