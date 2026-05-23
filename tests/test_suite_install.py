"""Comprehensive tests for suite skill install, uninstall, and gaia skills CLI.

Tests cover:
- Suite detection and recursive installation
- Actual content verification (real SKILL.md files, not empty dirs)
- Known bugs documented as explicit regression tests
- list_available fast-path (named-skills.json) and fallback-scan behaviour
- Uninstall edge cases

NOTE: The pytest Python environment (/root/.local/share/uv/tools/pytest/bin/python)
does NOT have the `yaml` package, so _parse_frontmatter() falls back to a naive
line-by-line parser that cannot handle nested YAML (links.github, suiteComponents).
All tests that exercise install_skill() must therefore use named-skills.json as
the registry source (pure JSON, no YAML parsing needed).
Only the fallback-scan tests use .md files, with flat scalar-only frontmatter.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.install import (
    install_skill,
    install_suite,
    list_available,
    load_manifest,
    save_manifest,
    uninstall_skill,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_json_registry(tmp_path, entries: list[dict]) -> str:
    """Write registry/named-skills.json from a list of skill meta dicts.

    Returns tmp_path (acts as registry root).
    Buckets are keyed by a generated genericSkillRef if not provided.
    """
    registry = tmp_path / "registry"
    registry.mkdir(exist_ok=True)
    buckets: dict = {}
    for meta in entries:
        # Use the skill slug as the bucket key if no genericSkillRef
        ref = meta.get("genericSkillRef", meta["id"].replace("/", "-"))
        buckets.setdefault(ref, []).append(meta)
    data = {"buckets": buckets, "awaitingClassification": []}
    (registry / "named-skills.json").write_text(json.dumps(data), encoding="utf-8")
    return str(tmp_path)


def _suite_meta(components: list[str], suite_has_link: bool = False) -> dict:
    """Build a suite skill meta dict."""
    meta: dict = {
        "id": "testuser/my-suite",
        "name": "My Suite",
        "level": "5★",
        "status": "named",
        "suiteComponents": [f"testuser/{c}" for c in components],
    }
    if suite_has_link:
        meta["links"] = {
            "github": "https://github.com/testuser/repo/blob/main/suite-root/SKILL.md"
        }
    return meta


def _component_meta(slug: str) -> dict:
    """Build a leaf component skill meta dict with a github link."""
    return {
        "id": f"testuser/{slug}",
        "name": slug.replace("-", " ").title(),
        "level": "3★",
        "status": "named",
        "links": {
            "github": f"https://github.com/testuser/repo/blob/main/{slug}/SKILL.md"
        },
    }


def _make_git_mock(tmp_path, subpath_contents: dict):
    """Return a mock _run_git that seeds real SKILL.md files on 'clone'.

    subpath_contents = {"alpha": "Alpha actual content", ...}
    All component URLs point to github.com/testuser/repo, so the global cache
    for all of them is the same directory.  The clone mock creates every
    subpath at once (as if the full repo were cloned).
    """

    def mock_run_git(args, cwd=None):
        if args[0] == "clone":
            dest = args[-1]
            os.makedirs(dest, exist_ok=True)
            for subpath, content in subpath_contents.items():
                skill_dir = os.path.join(dest, subpath)
                os.makedirs(skill_dir, exist_ok=True)
                with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                    f.write(content)
        # pull is a no-op in tests
        return True

    return mock_run_git


def _setup_install_env(tmp_path, monkeypatch):
    """Common monkeypatching needed by every install_skill test."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "gaia_cli.install.get_global_cache_dir",
        lambda: str(tmp_path / ".gaia" / "skills"),
    )


# ---------------------------------------------------------------------------
# TestSuiteInstallDetection
# ---------------------------------------------------------------------------


class TestSuiteInstallDetection:
    """install_skill correctly detects suites vs plain skills."""

    def test_install_skill_delegates_to_suite_when_suite_components_present(
        self, tmp_path, monkeypatch
    ):
        """install_skill on a suite skill creates manifest entries for all components."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                _suite_meta(["alpha", "beta"]),
                _component_meta("alpha"),
                _component_meta("beta"),
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(
                tmp_path,
                {"alpha": "Alpha actual skill content", "beta": "Beta actual skill content"},
            ),
        )

        result = install_skill("testuser/my-suite", str(tmp_path))

        assert result is True
        manifest = load_manifest()
        installed_ids = {e["id"] for e in manifest["installed"]}
        assert "testuser/alpha" in installed_ids
        assert "testuser/beta" in installed_ids

    def test_install_skill_on_individual_skill_creates_single_entry(
        self, tmp_path, monkeypatch
    ):
        """install_skill on a plain skill creates exactly one manifest entry."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(tmp_path, [_component_meta("solo")])
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(tmp_path, {"solo": "Solo actual content"}),
        )

        result = install_skill("testuser/solo", str(tmp_path))

        assert result is True
        manifest = load_manifest()
        assert len(manifest["installed"]) == 1
        assert manifest["installed"][0]["id"] == "testuser/solo"


# ---------------------------------------------------------------------------
# TestSuiteInstallFlow
# ---------------------------------------------------------------------------


class TestSuiteInstallFlow:
    """Correct behaviour for suite installation, including content verification."""

    def test_install_suite_creates_manifest_entry_for_each_component(
        self, tmp_path, monkeypatch
    ):
        """After installing a 3-component suite, manifest has exactly 3 entries."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                _suite_meta(["alpha", "beta", "gamma"]),
                _component_meta("alpha"),
                _component_meta("beta"),
                _component_meta("gamma"),
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(
                tmp_path,
                {
                    "alpha": "Alpha actual skill content",
                    "beta": "Beta actual skill content",
                    "gamma": "Gamma actual skill content",
                },
            ),
        )

        result = install_suite("testuser/my-suite", str(tmp_path))

        assert result is True
        manifest = load_manifest()
        installed_ids = {e["id"] for e in manifest["installed"]}
        assert installed_ids == {"testuser/alpha", "testuser/beta", "testuser/gamma"}

    def test_install_suite_components_have_actual_skill_content(
        self, tmp_path, monkeypatch
    ):
        """Installed skill dirs contain actual SKILL.md content, not empty dirs or placeholders."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                _suite_meta(["alpha", "beta"]),
                _component_meta("alpha"),
                _component_meta("beta"),
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(
                tmp_path,
                {
                    "alpha": "# Alpha\n\nThis is the actual skill content for alpha.\n",
                    "beta": "# Beta\n\nThis is the actual skill content for beta.\n",
                },
            ),
        )

        install_suite("testuser/my-suite", str(tmp_path))

        skills_dir = tmp_path / ".agents" / "skills"
        for slug, expected_fragment in [
            ("alpha", "actual skill content for alpha"),
            ("beta", "actual skill content for beta"),
        ]:
            skill_path = skills_dir / slug
            assert skill_path.exists() or skill_path.is_symlink(), (
                f"Skill dir '{slug}' was not created"
            )
            # Resolve symlink so we can read the file
            real_path = skill_path.resolve()
            skill_md = real_path / "SKILL.md"
            assert skill_md.exists(), f"SKILL.md missing inside '{slug}' skill dir"
            content = skill_md.read_text(encoding="utf-8")
            assert expected_fragment in content, (
                f"'{slug}/SKILL.md' does not contain expected content.\nGot: {content!r}"
            )

    def test_install_suite_symlink_resolves_to_correct_cache_dir(
        self, tmp_path, monkeypatch
    ):
        """Installed symlink points into the global cache (~/.gaia/skills)."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [_suite_meta(["alpha"]), _component_meta("alpha")],
        )
        cache_base = str(tmp_path / ".gaia" / "skills")
        monkeypatch.setattr("gaia_cli.install.get_global_cache_dir", lambda: cache_base)
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(tmp_path, {"alpha": "Alpha content"}),
        )

        install_suite("testuser/my-suite", str(tmp_path))

        link = tmp_path / ".agents" / "skills" / "alpha"
        assert link.is_symlink(), "Expected a symlink for installed skill"
        link_target = os.readlink(str(link))
        assert link_target.startswith(cache_base), (
            f"Symlink target {link_target!r} is not inside cache dir {cache_base!r}"
        )

    def test_install_suite_prevents_circular_recursion(
        self, tmp_path, monkeypatch
    ):
        """Suite component referencing back to the suite does not cause infinite recursion."""
        _setup_install_env(tmp_path, monkeypatch)
        # cycle-suite → component-a → cycle-suite (circular)
        _make_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/cycle-suite",
                    "name": "Cycle Suite",
                    "status": "named",
                    "suiteComponents": ["testuser/component-a"],
                },
                {
                    "id": "testuser/component-a",
                    "name": "Component A",
                    "status": "named",
                    "suiteComponents": ["testuser/cycle-suite"],
                },
            ],
        )
        monkeypatch.setattr("gaia_cli.install._run_git", lambda args, cwd=None: True)

        # Must not raise RecursionError
        result = install_skill("testuser/cycle-suite", str(tmp_path))
        assert result is not None  # Completes without infinite loop

    def test_install_suite_nested_suites_all_leaf_skills_installed(
        self, tmp_path, monkeypatch
    ):
        """A suite containing a sub-suite installs all leaf skills recursively."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/top-suite",
                    "name": "Top Suite",
                    "status": "named",
                    "suiteComponents": ["testuser/sub-suite", "testuser/leaf-direct"],
                },
                {
                    "id": "testuser/sub-suite",
                    "name": "Sub Suite",
                    "status": "named",
                    "suiteComponents": ["testuser/leaf-a", "testuser/leaf-b"],
                },
                {
                    "id": "testuser/leaf-a",
                    "name": "Leaf A",
                    "status": "named",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/leaf-a/SKILL.md"
                    },
                },
                {
                    "id": "testuser/leaf-b",
                    "name": "Leaf B",
                    "status": "named",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/leaf-b/SKILL.md"
                    },
                },
                {
                    "id": "testuser/leaf-direct",
                    "name": "Leaf Direct",
                    "status": "named",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/leaf-direct/SKILL.md"
                    },
                },
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(
                tmp_path,
                {
                    "leaf-a": "Leaf A actual content",
                    "leaf-b": "Leaf B actual content",
                    "leaf-direct": "Leaf Direct actual content",
                },
            ),
        )

        install_skill("testuser/top-suite", str(tmp_path))

        manifest = load_manifest()
        installed_ids = {e["id"] for e in manifest["installed"]}
        assert "testuser/leaf-a" in installed_ids
        assert "testuser/leaf-b" in installed_ids
        assert "testuser/leaf-direct" in installed_ids

        # Verify actual content in each leaf
        skills_dir = tmp_path / ".agents" / "skills"
        for slug, fragment in [
            ("leaf-a", "Leaf A actual content"),
            ("leaf-b", "Leaf B actual content"),
            ("leaf-direct", "Leaf Direct actual content"),
        ]:
            real_path = (skills_dir / slug).resolve()
            skill_md = real_path / "SKILL.md"
            assert skill_md.exists(), f"SKILL.md missing for {slug}"
            assert fragment in skill_md.read_text(encoding="utf-8")

    def test_install_suite_updates_existing_entry_not_duplicate(
        self, tmp_path, monkeypatch
    ):
        """Installing the same suite twice does not duplicate manifest entries."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [_suite_meta(["alpha"]), _component_meta("alpha")],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(tmp_path, {"alpha": "Alpha actual content"}),
        )

        install_suite("testuser/my-suite", str(tmp_path))
        install_suite("testuser/my-suite", str(tmp_path))

        manifest = load_manifest()
        alpha_entries = [e for e in manifest["installed"] if e["id"] == "testuser/alpha"]
        assert len(alpha_entries) == 1, (
            f"Expected exactly 1 manifest entry for testuser/alpha, got {len(alpha_entries)}"
        )

    def test_install_suite_shared_repo_cloned_once(self, tmp_path, monkeypatch):
        """Components from the same GitHub repo share one global cache clone."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                _suite_meta(["alpha", "beta", "gamma"]),
                _component_meta("alpha"),
                _component_meta("beta"),
                _component_meta("gamma"),
            ],
        )
        clone_calls = []

        def counting_git_mock(args, cwd=None):
            if args[0] == "clone":
                clone_calls.append(args)
                dest = args[-1]
                os.makedirs(dest, exist_ok=True)
                for slug in ["alpha", "beta", "gamma"]:
                    d = os.path.join(dest, slug)
                    os.makedirs(d, exist_ok=True)
                    with open(os.path.join(d, "SKILL.md"), "w") as f:
                        f.write(f"{slug} content")
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", counting_git_mock)

        install_suite("testuser/my-suite", str(tmp_path))

        # All three components share the same repo URL → only one clone
        assert len(clone_calls) == 1, (
            f"Expected 1 git clone call (shared repo), got {len(clone_calls)}"
        )

    def test_install_suite_visited_set_prevents_duplicate_installations(
        self, tmp_path, monkeypatch
    ):
        """A skill shared between two sub-suites is installed only once."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/parent-suite",
                    "name": "Parent Suite",
                    "status": "named",
                    "suiteComponents": ["testuser/sub-suite-a", "testuser/sub-suite-b"],
                },
                {
                    "id": "testuser/sub-suite-a",
                    "name": "Sub Suite A",
                    "status": "named",
                    "suiteComponents": ["testuser/shared-skill"],
                },
                {
                    "id": "testuser/sub-suite-b",
                    "name": "Sub Suite B",
                    "status": "named",
                    "suiteComponents": ["testuser/shared-skill"],
                },
                {
                    "id": "testuser/shared-skill",
                    "name": "Shared Skill",
                    "status": "named",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/shared-skill/SKILL.md"
                    },
                },
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(tmp_path, {"shared-skill": "Shared skill content"}),
        )

        install_skill("testuser/parent-suite", str(tmp_path))

        manifest = load_manifest()
        shared_entries = [e for e in manifest["installed"] if e["id"] == "testuser/shared-skill"]
        assert len(shared_entries) == 1, (
            f"Expected shared-skill installed exactly once, got {len(shared_entries)} entries"
        )


# ---------------------------------------------------------------------------
# TestSuiteInstallBugs  (regression tests documenting known bugs)
# ---------------------------------------------------------------------------


class TestSuiteInstallBugs:
    """Document existing bugs; tests pass by asserting the current buggy behaviour.

    When the underlying bug is fixed, update the assertion to expect correct
    behaviour and verify the fix.
    """

    def test_install_suite_returns_true_even_when_zero_components_installed(
        self, tmp_path, monkeypatch
    ):
        """BUG (install.py:251): install_suite returns True even when 0/N components install.

        Components lacking links.github cannot be installed. The suite should
        signal failure, but currently always returns True regardless.
        """
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/empty-suite",
                    "name": "Empty Suite",
                    "status": "named",
                    "suiteComponents": ["testuser/no-link"],
                },
                {
                    # No links.github → install_skill will fail for this component
                    "id": "testuser/no-link",
                    "name": "No Link",
                    "status": "named",
                },
            ],
        )

        result = install_suite("testuser/empty-suite", str(tmp_path))

        # BUG: returns True even though nothing was installed
        assert result is True, (
            "BUG still present: install_suite should return False on total failure"
        )
        manifest = load_manifest()
        assert len(manifest["installed"]) == 0, "No components should have been installed"

    def test_install_suite_with_partial_failures_returns_true(
        self, tmp_path, monkeypatch
    ):
        """BUG (install.py:251): install_suite returns True when only 1/3 components succeed."""
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/partial-suite",
                    "name": "Partial Suite",
                    "status": "named",
                    "suiteComponents": [
                        "testuser/ok-skill",
                        "testuser/no-link-1",
                        "testuser/no-link-2",
                    ],
                },
                _component_meta("ok-skill"),
                {"id": "testuser/no-link-1", "name": "No Link 1", "status": "named"},
                {"id": "testuser/no-link-2", "name": "No Link 2", "status": "named"},
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(tmp_path, {"ok-skill": "OK actual content"}),
        )

        result = install_suite("testuser/partial-suite", str(tmp_path))

        # BUG: partial failure still returns True
        assert result is True, (
            "BUG still present: partial suite failure should not unconditionally return True"
        )
        manifest = load_manifest()
        installed_ids = {e["id"] for e in manifest["installed"]}
        assert "testuser/ok-skill" in installed_ids
        assert "testuser/no-link-1" not in installed_ids
        assert "testuser/no-link-2" not in installed_ids

    def test_suite_root_with_github_link_not_installed_due_to_visited_set(
        self, tmp_path, monkeypatch
    ):
        """BUG (install.py:247-248): Suite root is never installed when it has suiteComponents
        AND links.github.

        install_skill adds suite_id to `visited` before delegating to install_suite.
        install_suite then tries to install the root at line 247 via
        install_skill(sid, ..., visited), but sid is already visited → instant True no-op.
        """
        _setup_install_env(tmp_path, monkeypatch)
        _make_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/my-suite",
                    "name": "My Suite",
                    "status": "named",
                    "suiteComponents": ["testuser/alpha"],
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/suite-root/SKILL.md"
                    },
                },
                _component_meta("alpha"),
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install._run_git",
            _make_git_mock(
                tmp_path,
                {"alpha": "Alpha content", "suite-root": "Suite root content"},
            ),
        )

        install_skill("testuser/my-suite", str(tmp_path))

        manifest = load_manifest()
        installed_ids = {e["id"] for e in manifest["installed"]}

        # Component IS installed correctly
        assert "testuser/alpha" in installed_ids

        # BUG: suite root itself is NOT in the manifest (blocked by visited set)
        assert "testuser/my-suite" not in installed_ids, (
            "BUG still present: suite root should be installed when it has its own github link"
        )


# ---------------------------------------------------------------------------
# TestUninstallEdgeCases
# ---------------------------------------------------------------------------


class TestUninstallEdgeCases:
    """Edge-case and bug tests for uninstall_skill."""

    def test_uninstall_nonexistent_skill_incorrectly_returns_true(
        self, tmp_path, monkeypatch
    ):
        """BUG (install.py:299-302): uninstall_skill returns True for skills never installed.

        When skill_id is not in the manifest, the filter is a no-op and the function
        still prints "Uninstalled:" and returns True. Should return False.
        """
        monkeypatch.chdir(tmp_path)
        save_manifest({"installed": []})

        result = uninstall_skill("never/installed")

        # BUG: should be False but is True
        assert result is True, (
            "BUG still present: uninstall of non-existent skill should return False"
        )
        manifest = load_manifest()
        assert manifest["installed"] == []

    def test_uninstall_with_leading_slash_normalizes(self, tmp_path, monkeypatch):
        """uninstall_skill('/testuser/skill') finds the entry stored as 'testuser/skill'."""
        monkeypatch.chdir(tmp_path)

        skill_file = tmp_path / ".agents" / "skills" / "skill"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("mock")

        save_manifest(
            {"installed": [{"id": "testuser/skill", "localPath": str(skill_file)}]}
        )

        result = uninstall_skill("/testuser/skill")

        assert result is True
        assert load_manifest()["installed"] == []
        assert not skill_file.exists()

    def test_uninstall_directory_skill_removed(self, tmp_path, monkeypatch):
        """uninstall_skill removes a directory (not just a symlink or file)."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / ".agents" / "skills" / "my-dir-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("content")

        save_manifest(
            {"installed": [{"id": "testuser/my-dir-skill", "localPath": str(skill_dir)}]}
        )

        uninstall_skill("testuser/my-dir-skill")

        assert not skill_dir.exists()
        assert load_manifest()["installed"] == []

    def test_uninstall_leaves_other_suite_components_intact(
        self, tmp_path, monkeypatch
    ):
        """Uninstalling one suite component does not affect the others."""
        monkeypatch.chdir(tmp_path)

        alpha_dir = tmp_path / ".agents" / "skills" / "alpha"
        beta_dir = tmp_path / ".agents" / "skills" / "beta"
        alpha_dir.mkdir(parents=True)
        beta_dir.mkdir(parents=True)
        (alpha_dir / "SKILL.md").write_text("alpha content")
        (beta_dir / "SKILL.md").write_text("beta content")

        save_manifest({
            "installed": [
                {"id": "testuser/alpha", "localPath": str(alpha_dir)},
                {"id": "testuser/beta", "localPath": str(beta_dir)},
            ]
        })

        uninstall_skill("testuser/alpha")

        assert not alpha_dir.exists()
        assert beta_dir.exists(), "beta skill dir should remain after uninstalling alpha"
        remaining_ids = {e["id"] for e in load_manifest()["installed"]}
        assert "testuser/beta" in remaining_ids
        assert "testuser/alpha" not in remaining_ids


# ---------------------------------------------------------------------------
# TestListAvailable
# ---------------------------------------------------------------------------


class TestListAvailable:
    """Tests for list_available() fast-path (named-skills.json) and fallback scan."""

    def test_list_available_uses_fast_path_named_skills_json(self, tmp_path):
        """list_available reads named-skills.json when it exists."""
        registry = tmp_path / "registry"
        registry.mkdir()
        (registry / "named-skills.json").write_text(
            json.dumps({
                "buckets": {
                    "web-search": [
                        {
                            "id": "alice/search",
                            "name": "Alice Search",
                            "level": "2★",
                            "description": "Fast web search.",
                        }
                    ]
                },
                "awaitingClassification": [],
            }),
            encoding="utf-8",
        )

        results = list_available(str(tmp_path))

        ids = [sid for sid, _ in results]
        assert "alice/search" in ids

    def test_list_available_fast_path_includes_awaiting_classification(self, tmp_path):
        """awaitingClassification entries are merged with bucket entries."""
        registry = tmp_path / "registry"
        registry.mkdir()
        (registry / "named-skills.json").write_text(
            json.dumps({
                "buckets": {
                    "web-search": [
                        {"id": "alice/search", "name": "Alice Search", "level": "2★"}
                    ]
                },
                "awaitingClassification": [
                    {"id": "bob/pending", "name": "Bob Pending", "level": "1★"}
                ],
            }),
            encoding="utf-8",
        )

        results = list_available(str(tmp_path))
        ids = [sid for sid, _ in results]
        assert "alice/search" in ids
        assert "bob/pending" in ids

    def test_list_available_reads_suite_components_from_json_index(self, tmp_path):
        """suiteComponents compiled into named-skills.json are returned in meta."""
        registry = tmp_path / "registry"
        registry.mkdir()
        (registry / "named-skills.json").write_text(
            json.dumps({
                "buckets": {
                    "suite-skill": [
                        {
                            "id": "testuser/my-suite",
                            "name": "My Suite",
                            "level": "5★",
                            "suiteComponents": ["testuser/alpha", "testuser/beta"],
                        }
                    ]
                },
                "awaitingClassification": [],
            }),
            encoding="utf-8",
        )

        results = list_available(str(tmp_path))

        meta_map = {sid: meta for sid, meta in results}
        assert "testuser/my-suite" in meta_map
        components = meta_map["testuser/my-suite"].get("suiteComponents", [])
        assert "testuser/alpha" in components
        assert "testuser/beta" in components

    def test_list_available_fallback_scans_md_files(self, tmp_path):
        """list_available scans registry/named/**/*.md when no JSON index exists.

        Uses flat frontmatter only (no nested YAML) to avoid the pytest-env naive
        parser limitation.
        """
        named_dir = tmp_path / "registry" / "named" / "testuser"
        named_dir.mkdir(parents=True)
        # Flat frontmatter — safe for the naive line-by-line parser
        (named_dir / "fallback-skill.md").write_text(
            "---\nid: testuser/fallback-skill\nname: Fallback Skill\nlevel: 2★\nstatus: named\n---\n\nBody.",
            encoding="utf-8",
        )
        # No named-skills.json → must use fallback scanner

        results = list_available(str(tmp_path))

        ids = [sid for sid, _ in results]
        assert "testuser/fallback-skill" in ids

    def test_list_available_fallback_returns_empty_when_no_md_files(self, tmp_path):
        """list_available returns [] when no named-skills.json and no .md files."""
        (tmp_path / "registry" / "named").mkdir(parents=True)

        results = list_available(str(tmp_path))

        assert results == []


# ---------------------------------------------------------------------------
# TestRealRegistryIntegrity — cross-checks against the live registry on disk
# ---------------------------------------------------------------------------


class TestRealRegistryIntegrity:
    """Smoke tests against the actual registry/named-skills.json in this repo."""

    @pytest.fixture
    def real_index(self):
        index_path = os.path.join(REPO_ROOT, "registry", "named-skills.json")
        if not os.path.exists(index_path):
            pytest.skip("registry/named-skills.json not found")
        with open(index_path, encoding="utf-8") as f:
            return json.load(f)

    def test_garrytan_gstack_has_components_in_index(self, real_index):
        """garrytan/gstack suite has suiteComponents in the compiled index."""
        all_entries = {
            entry["id"]: entry
            for bucket in real_index.get("buckets", {}).values()
            for entry in bucket
        }
        assert "garrytan/gstack" in all_entries, "garrytan/gstack missing from index"
        gstack = all_entries["garrytan/gstack"]
        components = gstack.get("suiteComponents", [])
        assert len(components) > 0, "garrytan/gstack has no suiteComponents in index"

    def test_garrytan_gstack_components_all_have_github_links(self, real_index):
        """All garrytan/gstack component skills have a links.github entry."""
        all_entries = {
            entry["id"]: entry
            for bucket in real_index.get("buckets", {}).values()
            for entry in bucket
        }
        gstack = all_entries.get("garrytan/gstack", {})
        components = gstack.get("suiteComponents", [])
        missing_links = [
            cid
            for cid in components
            if cid in all_entries and not all_entries[cid].get("links", {}).get("github")
        ]
        assert missing_links == [], (
            f"These garrytan/gstack components lack links.github: {missing_links}"
        )

    def test_garrytan_gstack_components_exist_in_index(self, real_index):
        """All garrytan/gstack suiteComponents resolve to known entries in the index."""
        all_entries = {
            entry["id"]: entry
            for bucket in real_index.get("buckets", {}).values()
            for entry in bucket
        }
        gstack = all_entries.get("garrytan/gstack", {})
        components = gstack.get("suiteComponents", [])
        unknown = [cid for cid in components if cid not in all_entries]
        assert unknown == [], (
            f"These garrytan/gstack components are missing from the index: {unknown}"
        )

    def test_mattpocock_skills_suite_exists_in_index(self, real_index):
        """mattpocock/skills suite has suiteComponents in the compiled index."""
        all_entries = {
            entry["id"]: entry
            for bucket in real_index.get("buckets", {}).values()
            for entry in bucket
        }
        assert "mattpocock/skills" in all_entries, "mattpocock/skills missing from index"
        suite = all_entries["mattpocock/skills"]
        components = suite.get("suiteComponents", [])
        assert len(components) > 0, "mattpocock/skills has no suiteComponents"

    def test_mattpocock_skills_some_components_lack_github_link(self, real_index):
        """Some mattpocock/skills components have no links.github (sub-suites / stubs).

        This verifies the real registry exposes the partial-failure scenario that
        TestSuiteInstallBugs documents.
        """
        all_entries = {
            entry["id"]: entry
            for bucket in real_index.get("buckets", {}).values()
            for entry in bucket
        }
        suite = all_entries.get("mattpocock/skills", {})
        components = suite.get("suiteComponents", [])
        no_link = [
            cid
            for cid in components
            if cid in all_entries and not all_entries[cid].get("links", {}).get("github")
        ]
        assert len(no_link) > 0, (
            "Expected at least one mattpocock/skills component to lack a github link "
            "(this validates the partial-failure test scenario is realistic)"
        )
