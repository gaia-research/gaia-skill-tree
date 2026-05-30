"""Tests for gaia_cli.scanner — scan_skill_mds and match_skill_to_canonical."""

import os
import pytest

from gaia_cli.scanner import scan_skill_mds, match_skill_to_canonical, _skill_search_dirs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


_CANONICAL_SKILLS = [
    {"id": "web-scraping", "name": "Web Scraping", "description": "Scrape and extract data from websites"},
    {"id": "data-analysis", "name": "Data Analysis", "description": "Analyze and visualize data"},
    {"id": "python-basics", "name": "Python Basics", "description": "Write Python programs and scripts"},
]


# ---------------------------------------------------------------------------
# Tests: scan_skill_mds(root=...)
# ---------------------------------------------------------------------------

class TestScanSkillMds:
    def test_reads_agents_skills_dir(self, tmp_path):
        """Finds skill dirs under .agents/skills/ and reads frontmatter."""
        skill_dir = tmp_path / ".agents" / "skills" / "my-scraper"
        skill_dir.mkdir(parents=True)
        _write(
            str(skill_dir / "skill.md"),
            "---\nname: My Scraper\ndescription: Scrape the web\n---\n\n# My Scraper\n",
        )

        results = scan_skill_mds(root=str(tmp_path))
        assert len(results) == 1
        assert results[0]["id"] == "my-scraper"
        assert results[0]["name"] == "My Scraper"
        assert results[0]["description"] == "Scrape the web"
        assert "source_dir" in results[0]

    def test_reads_claude_skills_dir(self, tmp_path):
        """Finds skill dirs under .claude/skills/."""
        skill_dir = tmp_path / ".claude" / "skills" / "analyst"
        skill_dir.mkdir(parents=True)
        _write(str(skill_dir / "README.md"), "---\nname: Analyst\ndescription: Analyze stuff\n---\n")

        results = scan_skill_mds(root=str(tmp_path))
        assert len(results) == 1
        assert results[0]["id"] == "analyst"

    def test_no_skill_dirs_returns_empty(self, tmp_path):
        """Returns empty list when neither skill dir exists."""
        results = scan_skill_mds(root=str(tmp_path))
        assert results == []

    def test_skips_dotfiles(self, tmp_path):
        """Dirs starting with '.' are ignored."""
        hidden = tmp_path / ".agents" / "skills" / ".hidden-dir"
        hidden.mkdir(parents=True)
        _write(str(hidden / "skill.md"), "---\nname: Hidden\n---\n")

        results = scan_skill_mds(root=str(tmp_path))
        assert results == []

    def test_deduplicates_across_dirs(self, tmp_path):
        """Same dir name in both skill roots only appears once (agents wins)."""
        for base in (".agents/skills", ".claude/skills"):
            d = tmp_path / base / "duplicate"
            d.mkdir(parents=True)
            _write(str(d / "skill.md"), f"---\nname: {base}\n---\n")

        results = scan_skill_mds(root=str(tmp_path))
        assert len(results) == 1
        assert results[0]["id"] == "duplicate"

    def test_fallback_to_body_snippet_when_no_description(self, tmp_path):
        """Uses body text as description when frontmatter has no description."""
        skill_dir = tmp_path / ".agents" / "skills" / "bare"
        skill_dir.mkdir(parents=True)
        _write(str(skill_dir / "skill.md"), "---\nname: Bare\n---\n\nThis is the body.")

        results = scan_skill_mds(root=str(tmp_path))
        assert "This is the body" in results[0]["description"]

    def test_uses_root_not_cwd(self, tmp_path, monkeypatch):
        """Passing root= searches under root, not the CWD."""
        monkeypatch.chdir(str(tmp_path))  # CWD has no skills
        other_root = tmp_path / "other"
        skill_dir = other_root / ".agents" / "skills" / "remote-skill"
        skill_dir.mkdir(parents=True)
        _write(str(skill_dir / "skill.md"), "---\nname: Remote\ndescription: From another root\n---\n")

        assert scan_skill_mds(root=str(tmp_path)) == []
        results = scan_skill_mds(root=str(other_root))
        assert len(results) == 1
        assert results[0]["id"] == "remote-skill"


# ---------------------------------------------------------------------------
# Tests: expanded skill dirs + symlinks + config-driven paths
# ---------------------------------------------------------------------------

class TestSkillSearchDirs:
    def test_finds_antigravity_skills(self, tmp_path):
        """Skills in .antigravity/skills/ are discovered."""
        d = tmp_path / ".antigravity" / "skills" / "my-skill"
        d.mkdir(parents=True)
        _write(str(d / "skill.md"), "---\nname: Antigravity\ndescription: test\n---\n")

        results = scan_skill_mds(root=str(tmp_path))
        assert any(r["id"] == "my-skill" for r in results)

    def test_finds_cursor_rules(self, tmp_path):
        """.cursor/rules/ subdirs are treated as skills."""
        d = tmp_path / ".cursor" / "rules" / "cursor-skill"
        d.mkdir(parents=True)
        _write(str(d / "README.md"), "---\nname: Cursor Rule\ndescription: test\n---\n")

        results = scan_skill_mds(root=str(tmp_path))
        assert any(r["id"] == "cursor-skill" for r in results)

    def test_finds_windsurf_rules(self, tmp_path):
        """.windsurf/rules/ subdirs are treated as skills."""
        d = tmp_path / ".windsurf" / "rules" / "surf-skill"
        d.mkdir(parents=True)
        _write(str(d / "skill.md"), "---\nname: Surf\ndescription: test\n---\n")

        results = scan_skill_mds(root=str(tmp_path))
        assert any(r["id"] == "surf-skill" for r in results)

    def test_source_dir_recorded(self, tmp_path):
        """Each result records which directory it came from."""
        d = tmp_path / ".agents" / "skills" / "tracked"
        d.mkdir(parents=True)
        _write(str(d / "skill.md"), "---\nname: Tracked\ndescription: test\n---\n")

        results = scan_skill_mds(root=str(tmp_path))
        assert results[0]["source_dir"].endswith(os.path.join(".agents", "skills"))

    def test_symlinked_skill_dir_followed(self, tmp_path):
        """A symlink in .agents/skills/ pointing to a real dir outside root is followed."""
        real_skill = tmp_path / "shared-cache" / "my-skill"
        real_skill.mkdir(parents=True)
        _write(str(real_skill / "skill.md"), "---\nname: Shared\ndescription: from cache\n---\n")

        skills_root = tmp_path / ".agents" / "skills"
        skills_root.mkdir(parents=True)
        link = skills_root / "my-skill"
        link.symlink_to(real_skill)

        results = scan_skill_mds(root=str(tmp_path))
        assert len(results) == 1
        assert results[0]["id"] == "my-skill"
        assert results[0]["name"] == "Shared"

    def test_symlink_deduplication(self, tmp_path):
        """The same real skill dir reached via two different symlinks appears only once."""
        real_skill = tmp_path / "cache" / "skill-x"
        real_skill.mkdir(parents=True)
        _write(str(real_skill / "skill.md"), "---\nname: SkillX\ndescription: test\n---\n")

        for base in (".agents/skills", ".claude/skills"):
            d = tmp_path / base
            d.mkdir(parents=True, exist_ok=True)
            (d / "skill-x").symlink_to(real_skill)

        results = scan_skill_mds(root=str(tmp_path))
        assert len([r for r in results if r["id"] == "skill-x"]) == 1

    def test_config_driven_skill_dirs(self, tmp_path, monkeypatch):
        """Paths listed under skillDirs in .gaia/config.toml are scanned."""
        monkeypatch.chdir(str(tmp_path))
        custom = tmp_path / "my-custom-skills"
        skill = custom / "custom-skill"
        skill.mkdir(parents=True)
        _write(str(skill / "skill.md"), "---\nname: Custom\ndescription: from config\n---\n")

        gaia_dir = tmp_path / ".gaia"
        gaia_dir.mkdir()
        _write(str(gaia_dir / "config.toml"), 'skillDirs = ["my-custom-skills"]\n')

        results = scan_skill_mds(root=str(tmp_path))
        assert any(r["id"] == "custom-skill" for r in results)

    def test_skill_search_dirs_deduplicates_real_paths(self, tmp_path):
        """_skill_search_dirs never returns two entries for the same realpath."""
        real = tmp_path / "shared"
        real.mkdir()
        agents = tmp_path / ".agents" / "skills"
        agents.mkdir(parents=True)
        claude = tmp_path / ".claude" / "skills"
        claude.parent.mkdir(parents=True)
        claude.symlink_to(agents)  # .claude/skills → .agents/skills

        dirs = _skill_search_dirs(root=str(tmp_path))
        realpaths = [os.path.realpath(d) for d in dirs]
        assert len(realpaths) == len(set(realpaths))


# ---------------------------------------------------------------------------
# Tests: match_skill_to_canonical
# ---------------------------------------------------------------------------

class TestMatchSkillToCanonical:
    def test_matches_by_word_overlap(self):
        """Returns the best canonical match above threshold."""
        result = match_skill_to_canonical(
            "scraper", "Web Scraper", "scrape extract websites data",
            _CANONICAL_SKILLS,
        )
        assert result is not None
        canonical_id, score = result
        assert canonical_id == "web-scraping"
        assert score > 0.20

    def test_returns_none_below_threshold(self):
        """Returns None when no canonical skill exceeds threshold."""
        result = match_skill_to_canonical(
            "xyz", "Unrelated Thing", "completely different domain topic",
            _CANONICAL_SKILLS,
            threshold=0.90,
        )
        assert result is None

    def test_returns_none_for_empty_query(self):
        """Returns None when skill has no recognizable words."""
        result = match_skill_to_canonical("a", "a", "", _CANONICAL_SKILLS)
        assert result is None

    def test_custom_threshold(self):
        """Threshold parameter gates which matches are returned."""
        low = match_skill_to_canonical(
            "scraper", "Scraper", "scrape websites",
            _CANONICAL_SKILLS,
            threshold=0.01,
        )
        high = match_skill_to_canonical(
            "scraper", "Scraper", "scrape websites",
            _CANONICAL_SKILLS,
            threshold=0.99,
        )
        assert low is not None
        assert high is None

    def test_score_in_result_tuple(self):
        """The returned score is a float in [0, 1]."""
        result = match_skill_to_canonical(
            "python", "Python", "python scripts programs",
            _CANONICAL_SKILLS,
        )
        assert result is not None
        _, score = result
        assert 0.0 < score <= 1.0
