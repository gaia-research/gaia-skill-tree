import json
import sys
import os
from pathlib import Path
from gaia_cli.main import main

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
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "list", "--generic"])
    main()
    output = capsys.readouterr().out
    assert "[G] /skill-a - Skill A" in output
    assert "[G] /skill-b - Skill B" in output

def test_meta_list_named(tmp_path, monkeypatch, capsys):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "list", "--named"])
    main()
    output = capsys.readouterr().out
    assert "[N] /alice/named-a - Named A" in output

def test_meta_add_generic(tmp_path, monkeypatch):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "add", "Skill C", "--id", "skill-c", "--description", "Skill C Description at least ten chars"])
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
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "merge", "skill-a", "skill-b"])
    main()
    
    basic_dir = tmp_path / "registry" / "nodes" / "basic"
    assert (basic_dir / "skill-a.json").exists()
    assert not (basic_dir / "skill-b.json").exists()
    
    with open(basic_dir / "skill-a.json", "r") as f:
        data = json.load(f)
        assert any(ev["action"] == "merge" for ev in data.get("timeline", []))

def test_meta_evidence(tmp_path, monkeypatch):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "evidence", "skill-a", "https://example.com/proof", "--class", "B", "--notes", "Verified demo"])
    main()
    
    with open(tmp_path / "registry" / "nodes" / "basic" / "skill-a.json", "r") as f:
        data = json.load(f)
        assert len(data["evidence"]) == 1
        assert data["evidence"][0]["class"] == "B"
        assert data["evidence"][0]["source"] == "https://example.com/proof"
        assert any(ev["action"] == "evidence_added" for ev in data.get("timeline", []))
