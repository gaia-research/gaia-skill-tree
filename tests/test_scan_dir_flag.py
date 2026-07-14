import os
from gaia_cli.scanner import scan_skill_mds

def test_scan_dir_flag(tmp_path, monkeypatch):
    skills_dir = tmp_path / "skills"
    demo_skill_dir = skills_dir / "demo-skill"
    demo_skill_dir.mkdir(parents=True)
    
    skill_md = demo_skill_dir / "SKILL.md"
    skill_md.write_text("---\nid: demo-skill\nname: Demo\ndescription: demo skill for scan --dir test\n---\n")
    
    monkeypatch.chdir(tmp_path)
    
    # scan without --dir
    found_without_dir = scan_skill_mds(".")
    ids_without_dir = [item["id"] for item in found_without_dir]
    assert "/demo-skill" not in ids_without_dir
    
    # scan with --dir
    found_with_dir = scan_skill_mds(".", extra_dirs=["skills"])
    ids_with_dir = [item["id"] for item in found_with_dir]
    assert "/demo-skill" in ids_with_dir
