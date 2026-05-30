"""Tests for gaia_cli.scanner — scan_skill_mds and match_skill_to_canonical."""

import os
import pytest

from gaia_cli.scanner import scan_skill_mds, match_skill_to_canonical


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
