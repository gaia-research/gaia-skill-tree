import json
import sys
import os
from pathlib import Path
from gaia_cli.main import main
import pytest

@pytest.fixture(autouse=True)
def no_docs_build(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev._run_docs_build", lambda *a, **kw: None)

def write_fixture_registry(root: Path) -> None:
    registry = root / "registry"
    nodes = registry / "nodes"
    basic = nodes / "basic"
    basic.mkdir(parents=True)
    named = registry / "named" / "alice"
    named.mkdir(parents=True)
    
    # Create some generic skills
    (basic / "skill-a.json").write_text(json.dumps({
        "id": "skill-a", "name": "Skill A", "type": "basic", "level": "1★",
        "rarity": "common", "description": "Description A", "status": "provisional",
        "prerequisites": [], "derivatives": ["skill-b"], "evidence": [],
        "knownAgents": [], "createdAt": "2026-05-20", "updatedAt": "2026-05-20", "version": "0.1.0"
    }), encoding="utf-8")
    
    (basic / "skill-b.json").write_text(json.dumps({
        "id": "skill-b", "name": "Skill B", "type": "basic", "level": "1★",
        "rarity": "common", "description": "Description B", "status": "provisional",
        "prerequisites": ["skill-a"], "derivatives": [], "evidence": [],
        "knownAgents": [], "createdAt": "2026-05-20", "updatedAt": "2026-05-20", "version": "0.1.0"
    }), encoding="utf-8")

    # Create a named skill
    (named / "named-a.md").write_text(
        "---\n"
        "id: alice/named-a\n"
        "name: Named A\n"
        "contributor: alice\n"
        "origin: true\n"
        "genericSkillRef: skill-a\n"
        "status: named\n"
        "level: 2★\n"
        "description: Description A\n"
        "---\n",
        encoding="utf-8"
    )
    
    # Run assemble and index scripts to create gaia.json and named-skills.json
    repo_root = Path(__file__).parent.parent
    assemble_script = repo_root / "scripts" / "assemble_gaia.py"
    index_script = repo_root / "scripts" / "generateNamedIndex.py"
    
    import subprocess
    subprocess.run([sys.executable, str(assemble_script), "--registry", str(root)], check=True)
    subprocess.run([sys.executable, str(index_script), 
                    "--graph", str(registry / "gaia.json"),
                    "--named-dir", str(registry / "named"),
                    "--out", str(registry / "named-skills.json")], check=True)

def test_meta_list_generic(tmp_path, monkeypatch, capsys):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "dev", "list", "--generic"])
    main()
    output = capsys.readouterr().out
    assert "[G] /skill-a - Skill A" in output
    assert "[G] /skill-b - Skill B" in output

def test_meta_list_named(tmp_path, monkeypatch, capsys):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "dev", "list", "--named"])
    main()
    output = capsys.readouterr().out
    assert "[N] /alice/named-a - Named A" in output

def test_meta_add_generic(tmp_path, monkeypatch):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "dev", "add", "Skill C", "--id", "skill-c", "--description", "Skill C Description at least ten chars"])
    main()
    
    nodes_dir = tmp_path / "registry" / "nodes" / "basic"
    assert (nodes_dir / "skill-c.json").exists()
    with open(nodes_dir / "skill-c.json", "r") as f:
        data = json.load(f)
        assert data["name"] == "Skill C"
        assert "timeline" in data
        assert data["timeline"][-1]["action"] == "add"

def test_meta_merge(tmp_path, monkeypatch):
    write_fixture_registry(tmp_path)
    # Merge skill-b into skill-a
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "dev", "merge", "skill-a", "skill-b"])
    main()
    
    basic_dir = tmp_path / "registry" / "nodes" / "basic"
    assert (basic_dir / "skill-a.json").exists()
    assert not (basic_dir / "skill-b.json").exists()
    
    with open(basic_dir / "skill-a.json", "r") as f:
        data = json.load(f)
        assert any(ev["action"] == "merge" for ev in data.get("timeline", []))

def test_meta_evidence(tmp_path, monkeypatch):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "dev", "evidence", "skill-a", "https://example.com/proof", "--class", "B", "--notes", "Verified demo"])
    main()

    with open(tmp_path / "registry" / "nodes" / "basic" / "skill-a.json", "r") as f:
        data = json.load(f)
        assert len(data["evidence"]) == 1
        assert data["evidence"][0]["class"] == "B"
        assert data["evidence"][0]["source"] == "https://example.com/proof"
        assert any(ev["action"] == "evidence_added" for ev in data.get("timeline", []))

def test_meta_add_rejects_short_description(tmp_path, monkeypatch):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "dev", "add", "Short", "--id", "short-skill", "--description", "too short"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code != 0


def test_meta_add_extra_fields_null_stripped(tmp_path, monkeypatch):
    """--extra-fields with null values must not overwrite required string fields."""
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(tmp_path), "dev", "add", "Skill D",
        "--id", "skill-d",
        "--description", "Skill D Description at least ten chars",
        "--extra-fields", '{"name": null, "foo": "bar"}',
    ])
    main()

    dest = tmp_path / "registry" / "nodes" / "basic" / "skill-d.json"
    assert dest.exists()
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["name"] == "Skill D", "null extra-field must not overwrite the required 'name' field"
    assert data.get("foo") == "bar", "non-null extra fields should still be applied"


def test_meta_add_extra_fields_non_dict_warns(tmp_path, monkeypatch, capsys):
    """--extra-fields with a non-object JSON value must warn and be skipped."""
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(tmp_path), "dev", "add", "Skill E",
        "--id", "skill-e",
        "--description", "Skill E Description at least ten chars",
        "--extra-fields", "[1, 2, 3]",
    ])
    main()
    captured = capsys.readouterr()
    assert "Warning" in captured.out or "Warning" in captured.err
