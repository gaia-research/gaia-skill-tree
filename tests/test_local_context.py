"""Tests for gaia_cli.localContext."""

import json
import os

import pytest

from gaia_cli.localContext import LocalContext, _build_named_map, _build_local_first_map, _build_install_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


MINI_GRAPH = {
    "version": "0.1.0",
    "skills": [
        {
            "id": "python-basics",
            "name": "Python Basics",
            "type": "basic",
            "level": "1★",
            "prerequisites": [],
            "derivatives": ["web-frameworks"],
        },
        {
            "id": "web-frameworks",
            "name": "Web Frameworks",
            "type": "extra",
            "level": "2★",
            "prerequisites": ["python-basics"],
            "derivatives": [],
        },
        {
            "id": "testing",
            "name": "Testing",
            "type": "basic",
            "level": "1★",
            "prerequisites": [],
            "derivatives": [],
        },
    ],
}

MINI_TREE = {
    "userId": "testuser",
    "updatedAt": "2024-01-01T00:00:00Z",
    "unlockedSkills": [
        {"skillId": "python-basics", "level": "3★"},
        {"skillId": "testing", "level": "1★"},
    ],
    "stats": {"totalUnlocked": 2},
}

NAMED_SKILL_MD = """\
---
id: alice/flask-mastery
genericSkillRef: web-frameworks
contributor: alice
---

# Flask Mastery

A named implementation of the web-frameworks skill.
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_registry(tmp_path):
    """Create a minimal registry layout under tmp_path."""
    # registry/gaia.json
    _write_json(tmp_path / "registry" / "gaia.json", MINI_GRAPH)

    # skill-trees/testuser/skill-tree.json
    _write_json(
        tmp_path / "skill-trees" / "testuser" / "skill-tree.json",
        MINI_TREE,
    )

    # registry/named/alice/flask-mastery.md
    _write_text(
        tmp_path / "registry" / "named" / "alice" / "flask-mastery.md",
        NAMED_SKILL_MD,
    )

    return str(tmp_path)


@pytest.fixture
def mock_registry_no_tree(tmp_path):
    """Registry without a user tree."""
    _write_json(tmp_path / "registry" / "gaia.json", MINI_GRAPH)
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Tests: LocalContext.load()
# ---------------------------------------------------------------------------

class TestLocalContextLoad:
    def test_load_basic(self, mock_registry, monkeypatch):
        """Load with a valid registry and user tree."""
        # Disable scan loading (no .gaia/paths.json)
        monkeypatch.chdir(tmp_path := mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)

        assert ctx.username == "testuser"
        assert ctx.owned_ids == {"python-basics", "testing"}
        assert ctx.tree_data is not None
        assert ctx.graph_data is not None
        assert len(ctx._skill_map) == 3

    def test_load_no_user_tree(self, mock_registry_no_tree, monkeypatch):
        """Load when user has no tree yet."""
        monkeypatch.chdir(mock_registry_no_tree)
        ctx = LocalContext.load(mock_registry_no_tree, "newuser", include_scan=False)

        assert ctx.username == "newuser"
        assert ctx.owned_ids == set()
        assert ctx.tree_data is None
        assert ctx.graph_data is not None

    def test_load_with_scan(self, mock_registry, monkeypatch):
        """Load with scan results (paths.json) using new detectedIds format."""
        monkeypatch.chdir(mock_registry)
        # Create .gaia/paths.json in the new format with explicit detectedIds / novelIds.
        # The old `availablePaths[].ownedPrereqs` format is no longer read by the loader.
        paths_data = {
            "nearUnlocks": [],
            "oneAway": [],
            "detectedIds": ["python-basics", "testing", "novel-skill"],
            "novelIds": ["novel-skill"],
            "computedAt": "2024-01-01T00:00:00Z",
        }
        _write_json(os.path.join(mock_registry, ".gaia", "paths.json"), paths_data)

        ctx = LocalContext.load(mock_registry, "testuser", include_scan=True)

        # owned_ids should be in detected_ids (owned implies detected)
        assert "python-basics" in ctx.detected_ids
        assert "testing" in ctx.detected_ids
        # novel-skill is in detectedIds + novelIds → shows up as detected and novel
        assert "novel-skill" in ctx.detected_ids
        assert "novel-skill" in ctx.novel_ids

    def test_load_no_graph(self, tmp_path, monkeypatch):
        """Load when registry/gaia.json does not exist."""
        monkeypatch.chdir(str(tmp_path))
        ctx = LocalContext.load(str(tmp_path), "testuser", include_scan=False)

        assert ctx.graph_data is None
        assert ctx._skill_map == {}


# ---------------------------------------------------------------------------
# Tests: is_named(), named_ref(), named_contributor()
# ---------------------------------------------------------------------------

class TestNamedSkills:
    def test_is_named_true(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.is_named("web-frameworks") is True

    def test_is_named_false(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.is_named("python-basics") is False

    def test_named_ref(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.named_ref("web-frameworks") == "alice/flask-mastery"

    def test_named_ref_none(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.named_ref("python-basics") is None

    def test_named_contributor(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.named_contributor("web-frameworks") == "alice"

    def test_named_contributor_none(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.named_contributor("testing") is None


# ---------------------------------------------------------------------------
# Tests: is_local(), is_owned()
# ---------------------------------------------------------------------------

class TestLocalAndOwned:
    def test_is_owned_true(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.is_owned("python-basics") is True
        assert ctx.is_owned("testing") is True

    def test_is_owned_false(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.is_owned("web-frameworks") is False

    def test_is_local_with_novel(self, mock_registry, monkeypatch):
        """Novel skills (detected but not in canon) should be local."""
        monkeypatch.chdir(mock_registry)
        # Use new paths.json format with detectedIds / novelIds.
        paths_data = {
            "nearUnlocks": [],
            "oneAway": [],
            "detectedIds": ["my-custom-skill"],
            "novelIds": ["my-custom-skill"],
            "computedAt": "2024-01-01T00:00:00Z",
        }
        _write_json(os.path.join(mock_registry, ".gaia", "paths.json"), paths_data)

        ctx = LocalContext.load(mock_registry, "testuser", include_scan=True)
        assert ctx.is_local("my-custom-skill") is True

    def test_is_local_canon_skill(self, mock_registry, monkeypatch):
        """Canon skills are not local."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.is_local("python-basics") is False


# ---------------------------------------------------------------------------
# Tests: display_name()
# ---------------------------------------------------------------------------

class TestDisplayName:
    def test_display_named_skill(self, mock_registry, monkeypatch):
        """Named skills by another contributor display as /contrib/nick N★.

        The new display_name format always adds a leading slash and appends the
        level star: "/alice/flask-mastery 2★" (web-frameworks is level 2★ in
        MINI_GRAPH). With include_star=False: "/alice/flask-mastery".
        """
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.display_name("web-frameworks") == "/alice/flask-mastery 2★"
        assert ctx.display_name("web-frameworks", include_star=False) == "/alice/flask-mastery"

    def test_display_novel_skill(self, mock_registry, monkeypatch):
        """Novel/local skills display as /id (no star when level is 0★/unknown)."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        ctx.novel_ids.add("my-experiment")
        # level_of("my-experiment") → "0★" (not in skill_map); star omitted for 0★
        assert ctx.display_name("my-experiment") == "/my-experiment"

    def test_display_canon_skill(self, mock_registry, monkeypatch):
        """Canon skills without named impl display as /skill-id N★."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        # python-basics has level "1★" in MINI_GRAPH
        assert ctx.display_name("python-basics") == "/python-basics 1★"
        assert ctx.display_name("python-basics", include_star=False) == "/python-basics"


# ---------------------------------------------------------------------------
# Tests: all_skills()
# ---------------------------------------------------------------------------

class TestAllSkills:
    def test_includes_canon_skills(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        skills = ctx.all_skills()
        ids = {s["id"] for s in skills}
        assert "python-basics" in ids
        assert "web-frameworks" in ids
        assert "testing" in ids

    def test_includes_novel_skills(self, mock_registry, monkeypatch):
        """Novel skills appear in all_skills with local=True."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        ctx.novel_ids.add("my-novel-skill")

        skills = ctx.all_skills()
        ids = {s["id"] for s in skills}
        assert "my-novel-skill" in ids

        novel_entry = next(s for s in skills if s["id"] == "my-novel-skill")
        assert novel_entry["local"] is True
        assert novel_entry["type"] == "basic"
        assert novel_entry["level"] == "0★"

    def test_no_duplicate_for_canon_novel_overlap(self, mock_registry, monkeypatch):
        """If a novel_id also exists in canon (edge case), it should not duplicate."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        # Simulate edge case: novel_ids contains a canon skill
        ctx.novel_ids.add("testing")

        skills = ctx.all_skills()
        testing_entries = [s for s in skills if s["id"] == "testing"]
        # Should not duplicate - the canon entry exists in _skill_map
        assert len(testing_entries) == 1


# ---------------------------------------------------------------------------
# Tests: skill_level(), skill_type()
# ---------------------------------------------------------------------------

class TestSkillLevelAndType:
    def test_skill_level_from_tree(self, mock_registry, monkeypatch):
        """User's tree level takes priority."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.skill_level("python-basics") == "3★"

    def test_skill_level_from_canon(self, mock_registry, monkeypatch):
        """Falls back to canon level when not in user tree."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.skill_level("web-frameworks") == "2★"

    def test_skill_level_unknown(self, mock_registry, monkeypatch):
        """Returns '0★' for unknown skills."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.skill_level("nonexistent") == "0★"

    def test_skill_type(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.skill_type("python-basics") == "basic"
        assert ctx.skill_type("web-frameworks") == "extra"

    def test_skill_type_unknown(self, mock_registry, monkeypatch):
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        assert ctx.skill_type("nonexistent") == "basic"


# ---------------------------------------------------------------------------
# Tests: _build_named_map()
# ---------------------------------------------------------------------------

class TestBuildNamedMap:
    def test_parses_frontmatter(self, tmp_path):
        """Correctly extracts genericSkillRef -> id mapping."""
        named_dir = tmp_path / "registry" / "named" / "bob"
        named_dir.mkdir(parents=True)
        (named_dir / "my-skill.md").write_text(
            "---\n"
            "id: bob/my-skill\n"
            "genericSkillRef: some-generic-ref\n"
            "contributor: bob\n"
            "---\n\n"
            "# My Skill\n",
            encoding="utf-8",
        )

        result = _build_named_map(str(tmp_path))
        assert result == {"some-generic-ref": "bob/my-skill"}

    def test_ignores_files_without_frontmatter(self, tmp_path):
        """Files without YAML frontmatter are skipped."""
        named_dir = tmp_path / "registry" / "named" / "bob"
        named_dir.mkdir(parents=True)
        (named_dir / "no-frontmatter.md").write_text(
            "# Just a regular markdown file\n",
            encoding="utf-8",
        )

        result = _build_named_map(str(tmp_path))
        assert result == {}

    def test_ignores_incomplete_frontmatter(self, tmp_path):
        """Files missing genericSkillRef or id are skipped."""
        named_dir = tmp_path / "registry" / "named" / "carol"
        named_dir.mkdir(parents=True)
        # Missing genericSkillRef
        (named_dir / "missing-ref.md").write_text(
            "---\n"
            "id: carol/missing-ref\n"
            "contributor: carol\n"
            "---\n\n"
            "# Missing Ref\n",
            encoding="utf-8",
        )

        result = _build_named_map(str(tmp_path))
        assert result == {}

    def test_handles_quoted_values(self, tmp_path):
        """Quoted frontmatter values are stripped correctly."""
        named_dir = tmp_path / "registry" / "named" / "dave"
        named_dir.mkdir(parents=True)
        (named_dir / "quoted.md").write_text(
            '---\n'
            'id: "dave/quoted-skill"\n'
            "genericSkillRef: 'quoted-ref'\n"
            '---\n\n'
            '# Quoted\n',
            encoding="utf-8",
        )

        result = _build_named_map(str(tmp_path))
        assert result == {"quoted-ref": "dave/quoted-skill"}

    def test_empty_named_dir(self, tmp_path):
        """Returns empty dict when named dir is empty."""
        (tmp_path / "registry" / "named").mkdir(parents=True)
        result = _build_named_map(str(tmp_path))
        assert result == {}

    def test_missing_named_dir(self, tmp_path):
        """Returns empty dict when named dir does not exist."""
        result = _build_named_map(str(tmp_path))
        assert result == {}

    def test_multiple_skills(self, tmp_path):
        """Multiple named skills from different contributors."""
        for contrib, skill_name, ref in [
            ("alice", "flask-pro", "web-frameworks"),
            ("bob", "pytest-guru", "testing"),
        ]:
            named_dir = tmp_path / "registry" / "named" / contrib
            named_dir.mkdir(parents=True, exist_ok=True)
            (named_dir / f"{skill_name}.md").write_text(
                f"---\n"
                f"id: {contrib}/{skill_name}\n"
                f"genericSkillRef: {ref}\n"
                f"---\n\n"
                f"# {skill_name}\n",
                encoding="utf-8",
            )

        result = _build_named_map(str(tmp_path))
        assert result == {
            "web-frameworks": "alice/flask-pro",
            "testing": "bob/pytest-guru",
        }


# ---------------------------------------------------------------------------
# Tests: local-first map (install manifest + agent dirs + registry)
# ---------------------------------------------------------------------------

INSTALL_MANIFEST = {
    "installed": [
        {
            "id": "marco/gaia-curate",
            "installedAt": "2026-01-01T00:00:00Z",
            "repoUrl": "https://example.com/repo",
            "subpath": "registry/named/marco/gaia-curate",
            "localPath": ".agents/skills/gaia-curate",
        }
    ]
}

INSTALLED_SKILL_MD = """\
---
id: marco/gaia-curate
genericSkillRef: web-frameworks
contributor: marco
---

# Gaia Curate
"""


class TestLocalFirstMap:
    def test_manifest_entry_beats_registry(self, tmp_path, monkeypatch):
        """Install manifest takes priority over registry named-skills."""
        monkeypatch.chdir(str(tmp_path))
        # Registry has alice's version
        _write_text(
            tmp_path / "registry" / "named" / "alice" / "flask-mastery.md",
            NAMED_SKILL_MD,
        )
        # Manifest has marco's local install that also maps web-frameworks
        skills_dir = tmp_path / ".agents" / "skills" / "gaia-curate"
        skills_dir.mkdir(parents=True)
        _write_text(skills_dir / "skill.md", INSTALLED_SKILL_MD)
        _write_json(tmp_path / ".gaia" / "install-manifest.json", INSTALL_MANIFEST)

        result = _build_local_first_map(str(tmp_path), [], "marco")
        assert result["web-frameworks"] == "marco/gaia-curate"

    def test_install_map_extracts_from_local_path(self, tmp_path, monkeypatch):
        """_build_install_map reads genericSkillRef from localPath skill dir.

        _iter_manifest_refs now also yields a self-mapping for each manifest
        entry's named-skill ID (e.g. "marco/gaia-curate" → "marco/gaia-curate"),
        enabling local-first lookup by named ID. The result is a superset of
        the old {genericRef: namedId} mapping.
        """
        monkeypatch.chdir(str(tmp_path))
        skills_dir = tmp_path / ".agents" / "skills" / "gaia-curate"
        skills_dir.mkdir(parents=True)
        _write_text(skills_dir / "skill.md", INSTALLED_SKILL_MD)
        _write_json(tmp_path / ".gaia" / "install-manifest.json", INSTALL_MANIFEST)

        result = _build_install_map(str(tmp_path))
        # Primary mapping: genericSkillRef → named skill id
        assert result["web-frameworks"] == "marco/gaia-curate"
        # Self-mapping: named skill id → itself (local-first behavior)
        assert result.get("marco/gaia-curate") == "marco/gaia-curate"

    def test_install_map_falls_back_to_registry(self, tmp_path, monkeypatch):
        """_build_install_map falls back to registry/named/ when localPath missing."""
        monkeypatch.chdir(str(tmp_path))
        # No localPath dir, but registry has the file
        _write_text(
            tmp_path / "registry" / "named" / "marco" / "gaia-curate.md",
            INSTALLED_SKILL_MD,
        )
        # Manifest points to non-existent localPath
        manifest = {
            "installed": [
                {
                    "id": "marco/gaia-curate",
                    "installedAt": "2026-01-01T00:00:00Z",
                    "localPath": ".agents/skills/gaia-curate",  # does not exist
                }
            ]
        }
        _write_json(tmp_path / ".gaia" / "install-manifest.json", manifest)

        result = _build_install_map(str(tmp_path))
        # Primary mapping: genericSkillRef → named skill id
        assert result["web-frameworks"] == "marco/gaia-curate"
        # Self-mapping also present
        assert result.get("marco/gaia-curate") == "marco/gaia-curate"

    def test_empty_username_skips_agent_dirs(self, tmp_path, monkeypatch):
        """An empty username must not produce broken contributor/ prefixes."""
        monkeypatch.chdir(str(tmp_path))
        result = _build_local_first_map(str(tmp_path), [], "")
        assert result == {}

    def test_display_name_uses_manifest(self, mock_registry, monkeypatch):
        """display_name returns /contrib/nick N★ for the user's own installed skill.

        The new display_name format shows the full /contrib/nick with leading slash
        and star even for own skills. For marco viewing their own web-frameworks
        implementation (gaia-curate at web-frameworks' 2★ level), the result is
        "/marco/gaia-curate 2★". With include_star=False: "/marco/gaia-curate".
        """
        monkeypatch.chdir(mock_registry)
        # Install marco's version of web-frameworks
        skills_dir = os.path.join(mock_registry, ".agents", "skills", "gaia-curate")
        os.makedirs(skills_dir, exist_ok=True)
        _write_text(
            os.path.join(mock_registry, ".agents", "skills", "gaia-curate", "skill.md"),
            INSTALLED_SKILL_MD,
        )
        manifest = {
            "installed": [
                {
                    "id": "marco/gaia-curate",
                    "installedAt": "2026-01-01T00:00:00Z",
                    "localPath": os.path.join(mock_registry, ".agents", "skills", "gaia-curate"),
                }
            ]
        }
        _write_json(os.path.join(mock_registry, ".gaia", "install-manifest.json"), manifest)

        ctx = LocalContext.load(mock_registry, "marco", include_scan=False)
        # web-frameworks level = 2★ from MINI_GRAPH; marco == username → not redacted;
        # format is /contrib/nick N★ (own skills show full handle, not nickname-only)
        assert ctx.display_name("web-frameworks") == "/marco/gaia-curate 2★"
        assert ctx.display_name("web-frameworks", include_star=False) == "/marco/gaia-curate"

    def test_no_manifest_falls_back_gracefully(self, mock_registry, monkeypatch):
        """Without a manifest, local-first map behaves like registry-only named map."""
        monkeypatch.chdir(mock_registry)
        ctx = LocalContext.load(mock_registry, "testuser", include_scan=False)
        # alice/flask-mastery from the registry; web-frameworks is 2★ → "/alice/flask-mastery 2★"
        assert ctx.display_name("web-frameworks") == "/alice/flask-mastery 2★"
        assert ctx.display_name("web-frameworks", include_star=False) == "/alice/flask-mastery"
