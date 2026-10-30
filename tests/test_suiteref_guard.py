"""Direct suiteRef links must survive docs regeneration (Yggdrasil IV, EPIC #2189)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import generateNamedIndex as gni  # noqa: E402
from gaia_cli.trustMagnitude import computeTrustMagnitude  # noqa: E402


def _write(tmp_path, name, suiteRef=None):
    fp = tmp_path / f"{name}.md"
    lines = ["---", f"id: dev/{name}", f"name: {name}", "contributor: dev", "origin: false", "genericSkillRef: gen", "description: a test description", "status: named", 'level: "2★"']
    if suiteRef:
        lines.append(f'suiteRef: "{suiteRef}"')
    lines += ["---", "", "body", ""]
    fp.write_text("\n".join(lines), encoding="utf-8")
    return str(fp)


def _sync(tmp_path, names_to_ref, mapping):
    for name, ref in names_to_ref.items():
        _write(tmp_path, name, ref)
    skills = gni.load_named_skills(str(tmp_path))
    gni.update_markdown_files_with_suite_metadata(skills, mapping, {})
    return {fm["id"]: fm.get("suiteRef") for _fp, fm in gni.load_named_skills(str(tmp_path))}


def test_direct_suiteref_survives_regeneration(tmp_path):
    out = _sync(tmp_path, {"solo": "dev/capstone"}, {})
    assert out["dev/solo"] == "dev/capstone"


def test_manifest_component_still_gets_suiteref(tmp_path):
    out = _sync(tmp_path, {"member": None, "stale": "dev/old"}, {"dev/member": "dev/capstone", "dev/stale": "dev/capstone"})
    assert out["dev/member"] == "dev/capstone"
    assert out["dev/stale"] == "dev/capstone"  # manifest remains authoritative when it lists the skill


def test_unknown_suiteref_is_rejected(tmp_path):
    _write(tmp_path, "orphan", "ghost/nonexistent")
    _write(tmp_path, "ok", "dev/orphan")  # points at an existing named skill
    skills = gni.load_named_skills(str(tmp_path))
    graph = {"skills": [{"id": "gen", "type": "basic"}]}
    errors, _b, _a, _c = gni.validate_and_group(skills, graph, {}, {})
    joined = "\n".join(errors)
    assert "ghost/nonexistent" in joined
    assert "'suiteRef' value 'dev/orphan'" not in joined


def test_tm_cap_treats_direct_link_like_manifest_component():
    def comp(ref):
        return {
            "id": "taste/component",
            "suiteRef": ref,
            "evidence": [
                {"type": "github-stars-own", "stars": 200000, "source": "https://github.com/taste/taste/stargazers"},
            ],
        }

    # The cap reads only the skill's own suiteRef value; manifest membership is not consulted.
    assert computeTrustMagnitude(comp("taste/taste")) == pytest.approx(50.0)
    assert computeTrustMagnitude(comp(None)) > 50.0
