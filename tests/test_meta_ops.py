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
        "description": "Description A", "status": "provisional",
        "prerequisites": [], "derivatives": ["skill-b"], "evidence": [],
        "knownAgents": [], "createdAt": "2026-05-20", "updatedAt": "2026-05-20", "version": "0.1.0"
    }), encoding="utf-8")
    
    (basic / "skill-b.json").write_text(json.dumps({
        "id": "skill-b", "name": "Skill B", "type": "basic", "level": "1★",
        "description": "Description B", "status": "provisional",
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
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "dev", "merge", "skill-a", "skill-b", "--yes"])
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


# ---------------------------------------------------------------------------
# update-named tests
# ---------------------------------------------------------------------------

def write_named_skill(named_dir: Path, skill_id: str, extra_body: str = "") -> Path:
    """Write a minimal named skill .md file and return its path."""
    contributor, slug = skill_id.split("/", 1)
    skill_dir = named_dir / contributor
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / f"{slug}.md"
    path.write_text(
        f"---\nid: {skill_id}\nname: Test Skill\ncontributor: {contributor}\n"
        f"origin: true\ngenericSkillRef: skill-a\nstatus: named\nlevel: 2★\n"
        f"description: A test skill for unit tests.\n---\n{extra_body}",
        encoding="utf-8",
    )
    return path


def test_update_named_suite_ref(tmp_path, monkeypatch):
    """--suite-ref writes suiteRef to frontmatter."""
    write_fixture_registry(tmp_path)
    write_named_skill(tmp_path / "registry" / "named", "alice/named-a")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(tmp_path),
        "dev", "update-named", "alice/named-a",
        "--suite-ref", "alice/capstone-suite",
        "--no-build",
    ])
    main()

    import yaml
    content = (tmp_path / "registry" / "named" / "alice" / "named-a.md").read_text(encoding="utf-8")
    _, frontmatter, _ = content.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    assert meta.get("suiteRef") == "alice/capstone-suite"


def test_update_named_installation_file_append(tmp_path, monkeypatch):
    """--installation-file appends ## Installation when not present."""
    write_fixture_registry(tmp_path)
    write_named_skill(tmp_path / "registry" / "named", "alice/named-a")

    install_md = tmp_path / "setup.md"
    install_md.write_text("Run `pip install gaia` to get started.", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(tmp_path),
        "dev", "update-named", "alice/named-a",
        "--installation-file", str(install_md),
        "--no-build",
    ])
    main()

    content = (tmp_path / "registry" / "named" / "alice" / "named-a.md").read_text(encoding="utf-8")
    assert "## Installation" in content
    assert "pip install gaia" in content


def test_update_named_installation_file_replace(tmp_path, monkeypatch):
    """--installation-file replaces an existing ## Installation section."""
    write_fixture_registry(tmp_path)
    write_named_skill(
        tmp_path / "registry" / "named", "alice/named-a",
        extra_body="\n## Installation\n\nOld content here.\n\n## Usage\n\nSome usage.\n",
    )

    install_md = tmp_path / "setup.md"
    install_md.write_text("New installation instructions.", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(tmp_path),
        "dev", "update-named", "alice/named-a",
        "--installation-file", str(install_md),
        "--no-build",
    ])
    main()

    content = (tmp_path / "registry" / "named" / "alice" / "named-a.md").read_text(encoding="utf-8")
    assert "New installation instructions." in content
    assert "Old content here." not in content
    # Sibling section must be preserved
    assert "## Usage" in content


def test_update_named_installation_file_missing(tmp_path, monkeypatch):
    """--installation-file with a non-existent path exits with code 1."""
    write_fixture_registry(tmp_path)
    write_named_skill(tmp_path / "registry" / "named", "alice/named-a")

    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(tmp_path),
        "dev", "update-named", "alice/named-a",
        "--installation-file", str(tmp_path / "does-not-exist.md"),
        "--no-build",
    ])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code != 0


def test_replace_section_unit():
    """_replace_section unit tests covering replace and append paths."""
    from gaia_cli.commands.dev import _replace_section

    # Replace existing section; sibling heading preserved
    body = "\n## Installation\n\nOld text.\n\n## Usage\n\nHello.\n"
    result = _replace_section(body, "Installation", "New text.")
    assert "New text." in result
    assert "Old text." not in result
    assert "## Usage" in result

    # Append when section is absent
    body_no_section = "\n## Usage\n\nHello.\n"
    result2 = _replace_section(body_no_section, "Installation", "Appended.")
    assert "## Installation" in result2
    assert "Appended." in result2
    # Original content intact
    assert "## Usage" in result2

    # Code comment constraint: bare ## inside content is NOT fence-aware
    # (this test documents the known limitation rather than asserting correct behaviour)
    body_with_fence = "\n## Installation\n\n```bash\necho hi\n```\n\n## Next\n\nText.\n"
    result3 = _replace_section(body_with_fence, "Installation", "Replacement.")
    assert "Replacement." in result3
