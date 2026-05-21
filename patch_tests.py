import sys

with open('tests/test_named_skills_worktree.py', 'r') as f:
    content = f.read()

new_sync = """    @patch("gaia_cli.install._run_git", return_value=True)
    def test_update_skills_pulls_repos(self, mock_run_git):
        \"\"\"update_skills runs git pull on installed repos.\"\"\"
        import io
        import os
        from contextlib import redirect_stdout
        from gaia_cli.install import install_skill, update_skills, get_global_cache_dir
        install_skill("alice/my-skill", self.registry)
        
        # Create the cache dir so update_skills finds it
        os.makedirs(os.path.join(get_global_cache_dir(), "alice", "repo"), exist_ok=True)
        
        buf = io.StringIO()
        with redirect_stdout(buf):
            update_skills(self.registry)
        output = buf.getvalue()
        self.assertIn("Checking for updates", output)
        self.assertIn("Pulling", output)"""

old_sync = """    @patch("gaia_cli.install._run_git", return_value=True)
    def test_update_skills_pulls_repos(self, mock_run_git):
        \"\"\"update_skills runs git pull on installed repos.\"\"\"
        import io
        from contextlib import redirect_stdout
        from gaia_cli.install import install_skill, update_skills
        install_skill("alice/my-skill", self.registry)
        buf = io.StringIO()
        with redirect_stdout(buf):
            update_skills(self.registry)
        output = buf.getvalue()
        self.assertIn("Checking for updates", output)
        self.assertIn("Pulling", output)"""

content = content.replace(old_sync, new_sync)

with open('tests/test_named_skills_worktree.py', 'w') as f:
    f.write(content)

