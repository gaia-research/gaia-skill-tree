import sys

with open('tests/test_packaging.py', 'r') as f:
    content = f.read()

old_test = """def test_install_cache_honors_gaia_home(tmp_path, monkeypatch):
    from gaia_cli.install import install_skill

    repo = tmp_path / "repo"
    repo.mkdir()
    registry = tmp_path / "registry"
    skill_dir = registry / "registry" / "named" / "alice"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text("content")
    gaia_home = tmp_path / "custom-home"

    monkeypatch.chdir(repo)
    monkeypatch.setenv("GAIA_HOME", str(gaia_home))

    assert install_skill("alice/skill", str(registry)) is True"""

new_test = """def test_install_cache_honors_gaia_home(tmp_path, monkeypatch):
    from gaia_cli.install import install_skill

    repo = tmp_path / "repo"
    repo.mkdir()
    registry = tmp_path / "registry"
    skill_dir = registry / "registry" / "named" / "alice"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text("---\\nid: alice/skill\\nlinks:\\n  github: https://github.com/alice/repo/blob/main/skill/SKILL.md\\n---\\ncontent")
    gaia_home = tmp_path / "custom-home"

    monkeypatch.chdir(repo)
    monkeypatch.setenv("GAIA_HOME", str(gaia_home))
    
    # Mock git execution to succeed and create the mock source dir
    import os
    def mock_run_git(args, cwd=None):
        source_dir = os.path.join(str(gaia_home), "skills", "alice", "repo", "skill")
        os.makedirs(source_dir, exist_ok=True)
        return True
    monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)

    assert install_skill("alice/skill", str(registry)) is True"""

content = content.replace(old_test, new_test)

with open('tests/test_packaging.py', 'w') as f:
    f.write(content)

