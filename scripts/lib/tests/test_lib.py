"""
tests/test_scripts_lib.py — unit tests for scripts/lib/*.

Test location rationale: tests/ is NOT in the infra/ branch scope allowlist
(only .github/, scripts/, .claude/skills/, .agents/skills/, *.md, docs/*.html).
This file lives under scripts/lib/tests/ which IS under scripts/ and therefore
in-scope for infra/ branches.

Run with:
    pytest scripts/lib/tests/test_lib.py -v
or via the normal test suite:
    pytest
(pyproject.toml sets testpaths = ["tests"] so this file is also discoverable
there if we add scripts to sys.path; we do so in conftest below.)
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure scripts/ is on the path so ``scripts.lib`` resolves
import sys
import os

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT / "scripts") not in sys.path:
    # Not strictly needed if pyproject testpaths includes ".", but be explicit
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.frontmatter import (
    load_yaml_simple,
    split_frontmatter,
    update_list_item_in_frontmatter,
    upsert_top_level_block,
)
from scripts.lib.github_api import fetch_json, head_check, parse_owner_repo
from scripts.lib.named_iterator import iter_named_skills

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_FM = textwrap.dedent("""\
    ---
    id: test/skill
    name: Test Skill
    evidence:
    - source: https://github.com/example/repo
      type: github-stars-own
      stars: 1000
      updatedAt: '2026-01-01'
    - source: https://example.com/post
      type: social-signal
      views: 5000
    ---
    # Body text

    Some content here.
    """)

SAMPLE_FM_NO_UPSTREAM = textwrap.dedent("""\
    ---
    id: test/skill
    name: Test Skill
    status: named
    level: 2★
    ---
    """)

SAMPLE_FM_WITH_UPSTREAM = textwrap.dedent("""\
    ---
    id: test/skill
    name: Test Skill
    upstream:
      repo: example/repo
      version: v1.0.0
    ---
    """)


# ---------------------------------------------------------------------------
# split_frontmatter
# ---------------------------------------------------------------------------


class TestSplitFrontmatter:
    def test_splits_canonical_file(self):
        pre, fm, body = split_frontmatter(SAMPLE_FM)
        assert pre == "---\n"
        assert "id: test/skill" in fm
        assert "evidence:" in fm
        assert "# Body text" in body

    def test_round_trip_preserves_content(self):
        """Round-trip: reassembling the parts must reproduce the original text."""
        pre, fm, body = split_frontmatter(SAMPLE_FM)
        reassembled = f"{pre}{fm}\n---\n{body}"
        assert reassembled == SAMPLE_FM

    def test_returns_empty_tuple_on_no_frontmatter(self):
        text = "# Just markdown\nNo frontmatter here."
        pre, fm, body = split_frontmatter(text)
        assert pre == ""
        assert fm == ""
        assert body == text

    def test_real_mattpocock_skills_fixture(self):
        """Smoke-test against the canonical mattpocock/skills.md."""
        real_path = _REPO_ROOT / "registry" / "named" / "mattpocock" / "skills.md"
        if not real_path.exists():
            pytest.skip("mattpocock/skills.md not present in this checkout")
        text = real_path.read_text(encoding="utf-8")
        pre, fm, body = split_frontmatter(text)
        assert pre == "---\n"
        assert "id: mattpocock/skills" in fm

    def test_crlf_frontmatter(self):
        crlf_text = "---\r\nid: foo\r\n---\r\n# body\r\n"
        pre, fm, body = split_frontmatter(crlf_text)
        assert pre == "---\n"
        assert "id: foo" in fm


# ---------------------------------------------------------------------------
# load_yaml_simple
# ---------------------------------------------------------------------------


class TestLoadYamlSimple:
    def test_parses_basic_dict(self):
        fm = "id: skill\nname: My Skill\nlevel: 3"
        result = load_yaml_simple(fm)
        assert result["id"] == "skill"
        assert result["name"] == "My Skill"

    def test_returns_empty_dict_on_blank(self):
        assert load_yaml_simple("") == {}
        assert load_yaml_simple("   ") == {}

    def test_parses_nested_keys(self):
        fm = "links:\n  github: https://github.com/owner/repo\n"
        result = load_yaml_simple(fm)
        assert result["links"]["github"] == "https://github.com/owner/repo"


# ---------------------------------------------------------------------------
# update_list_item_in_frontmatter
# ---------------------------------------------------------------------------


class TestUpdateListItemInFrontmatter:
    def test_updates_stars_on_first_evidence_row(self):
        result = update_list_item_in_frontmatter(
            SAMPLE_FM,
            list_key="evidence",
            row_index=0,
            field_updates={"stars": 9999},
        )
        assert "stars: 9999" in result
        # Original star count should be gone
        assert "stars: 1000" not in result

    def test_updates_updatedAt_on_first_evidence_row(self):
        result = update_list_item_in_frontmatter(
            SAMPLE_FM,
            list_key="evidence",
            row_index=0,
            field_updates={"updatedAt": "2026-07-09"},
        )
        assert "updatedAt: '2026-07-09'" in result
        assert "updatedAt: '2026-01-01'" not in result

    def test_heartbeat_use_case_both_fields(self):
        """The heartbeat updates stars + updatedAt simultaneously."""
        result = update_list_item_in_frontmatter(
            SAMPLE_FM,
            list_key="evidence",
            row_index=0,
            field_updates={"stars": 55000, "updatedAt": "2026-07-09"},
        )
        assert "stars: 55000" in result
        assert "updatedAt: '2026-07-09'" in result

    def test_preserves_surrounding_rows(self):
        result = update_list_item_in_frontmatter(
            SAMPLE_FM,
            list_key="evidence",
            row_index=0,
            field_updates={"stars": 42},
        )
        # Second evidence row must be untouched
        assert "views: 5000" in result
        assert "type: social-signal" in result

    def test_inserts_new_field_if_absent(self):
        """A field not present in the item should be inserted."""
        fm_no_updated_at = SAMPLE_FM.replace("      updatedAt: '2026-01-01'\n", "")
        result = update_list_item_in_frontmatter(
            fm_no_updated_at,
            list_key="evidence",
            row_index=0,
            field_updates={"updatedAt": "2026-07-09"},
        )
        assert "updatedAt: '2026-07-09'" in result

    def test_returns_text_unchanged_for_out_of_range_index(self):
        result = update_list_item_in_frontmatter(
            SAMPLE_FM,
            list_key="evidence",
            row_index=99,
            field_updates={"stars": 1},
        )
        assert result == SAMPLE_FM

    def test_returns_text_unchanged_when_no_frontmatter(self):
        plain = "# No frontmatter\nSome text."
        result = update_list_item_in_frontmatter(
            plain, list_key="evidence", row_index=0, field_updates={"stars": 1}
        )
        assert result == plain

    def test_preserves_body_text(self):
        result = update_list_item_in_frontmatter(
            SAMPLE_FM,
            list_key="evidence",
            row_index=0,
            field_updates={"stars": 1},
        )
        assert "# Body text" in result
        assert "Some content here." in result


# ---------------------------------------------------------------------------
# upsert_top_level_block
# ---------------------------------------------------------------------------


class TestUpsertTopLevelBlock:
    def test_inserts_new_block_when_absent(self):
        result = upsert_top_level_block(
            SAMPLE_FM_NO_UPSTREAM,
            block_key="upstream",
            block_value={"repo": "example/repo", "version": "v1.0.0"},
        )
        assert "upstream:" in result
        assert "repo: example/repo" in result
        assert "version: v1.0.0" in result

    def test_updates_existing_block(self):
        result = upsert_top_level_block(
            SAMPLE_FM_WITH_UPSTREAM,
            block_key="upstream",
            block_value={"version": "v2.0.0"},
        )
        assert "version: v2.0.0" in result
        # Original unrelated sub-key should be preserved
        assert "repo: example/repo" in result
        # Old version gone
        assert "version: v1.0.0" not in result

    def test_key_ordering_is_deterministic(self):
        result = upsert_top_level_block(
            SAMPLE_FM_NO_UPSTREAM,
            block_key="upstream",
            block_value={"version": "v1.0.0", "repo": "a/b", "syncedAt": "2026-07-09"},
        )
        # Keys should appear in sorted order: repo, syncedAt, version
        pos_repo = result.index("repo:")
        pos_synced = result.index("syncedAt:")
        pos_version = result.index("version:")
        assert pos_repo < pos_synced < pos_version

    def test_preserves_other_frontmatter_keys(self):
        result = upsert_top_level_block(
            SAMPLE_FM_NO_UPSTREAM,
            block_key="upstream",
            block_value={"version": "v1.0.0"},
        )
        assert "id: test/skill" in result
        assert "status: named" in result

    def test_returns_unchanged_when_no_frontmatter(self):
        plain = "# No frontmatter"
        result = upsert_top_level_block(plain, "upstream", {"version": "v1"})
        assert result == plain

    def test_upsert_twice_is_idempotent(self):
        """Applying the same upsert twice should not duplicate the block."""
        first = upsert_top_level_block(
            SAMPLE_FM_NO_UPSTREAM,
            block_key="upstream",
            block_value={"version": "v1.0.0", "repo": "a/b"},
        )
        second = upsert_top_level_block(
            first,
            block_key="upstream",
            block_value={"version": "v1.0.0", "repo": "a/b"},
        )
        # 'upstream:' should appear exactly once
        assert second.count("upstream:") == 1


# ---------------------------------------------------------------------------
# parse_owner_repo
# ---------------------------------------------------------------------------


class TestParseOwnerRepo:
    def test_bare_repo_url(self):
        assert parse_owner_repo("https://github.com/owner/repo") == ("owner", "repo")

    def test_blob_url(self):
        assert parse_owner_repo(
            "https://github.com/owner/repo/blob/main/skills/foo/SKILL.md"
        ) == ("owner", "repo")

    def test_tree_url(self):
        assert parse_owner_repo(
            "https://github.com/owner/repo/tree/main/src"
        ) == ("owner", "repo")

    def test_releases_tag_url(self):
        assert parse_owner_repo(
            "https://github.com/owner/repo/releases/tag/v1.2.3"
        ) == ("owner", "repo")

    def test_git_suffix_stripped(self):
        assert parse_owner_repo("https://github.com/owner/repo.git") == ("owner", "repo")

    def test_non_github_url_returns_none(self):
        assert parse_owner_repo("https://gitlab.com/owner/repo") is None
        assert parse_owner_repo("https://example.com/owner/repo") is None

    def test_empty_string_returns_none(self):
        assert parse_owner_repo("") is None

    def test_none_like_empty(self):
        assert parse_owner_repo("   ") is None

    def test_stargazers_url(self):
        assert parse_owner_repo(
            "https://github.com/mattpocock/skills/stargazers"
        ) == ("mattpocock", "skills")


# ---------------------------------------------------------------------------
# head_check — mocked (no live network calls in unit tests)
# ---------------------------------------------------------------------------


class TestHeadCheck:
    def test_returns_200_on_success(self):
        class FakeResp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        with patch("urllib.request.urlopen", return_value=FakeResp()):
            assert head_check("https://example.com/path") == 200

    def test_returns_status_code_on_http_error(self):
        import urllib.error

        err = urllib.error.HTTPError(
            "https://example.com/path", 404, "Not Found", {}, None
        )
        with patch("urllib.request.urlopen", side_effect=err):
            assert head_check("https://example.com/path") == 404

    def test_returns_none_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            assert head_check("https://example.com/path") is None

    def test_returns_403_on_forbidden(self):
        import urllib.error

        err = urllib.error.HTTPError(
            "https://raw.githubusercontent.com/x/y/main/SKILL.md",
            403,
            "Forbidden",
            {},
            None,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            assert (
                head_check(
                    "https://raw.githubusercontent.com/x/y/main/SKILL.md"
                )
                == 403
            )


# ---------------------------------------------------------------------------
# fetch_json — mocked (no live GitHub API calls in unit tests)
# ---------------------------------------------------------------------------


class TestFetchJson:
    def test_auto_prefixes_path(self):
        """A bare path like /repos/owner/repo is prefixed to api.github.com."""
        import json as _json

        captured_url: list[str] = []

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                return _json.dumps({"stargazers_count": 42}).encode()

        original_urlopen = __import__("urllib.request", fromlist=["urlopen"]).urlopen

        def fake_urlopen(req, timeout=None):
            captured_url.append(req.full_url)
            return FakeResp()

        # Clear any cached result first
        from scripts.lib import github_api

        github_api._CACHE.clear()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("time.sleep"):  # suppress 100ms throttle in tests
                result = fetch_json("/repos/owner/repo")

        assert any(u.startswith("https://api.github.com/") for u in captured_url)

    def test_caches_result(self):
        import json as _json

        call_count = [0]

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                call_count[0] += 1
                return _json.dumps({"id": 1}).encode()

        from scripts.lib import github_api

        url = "https://api.github.com/repos/cache-test/repo-xyz"
        github_api._CACHE.pop(url, None)

        with patch("urllib.request.urlopen", return_value=FakeResp()):
            with patch("time.sleep"):
                r1 = fetch_json(url)
                r2 = fetch_json(url)

        # urlopen called only once — second call served from cache
        assert call_count[0] == 1
        assert r1 == r2

    def test_returns_none_on_http_error(self):
        import urllib.error
        from scripts.lib import github_api

        url = "https://api.github.com/repos/gone/repo"
        github_api._CACHE.pop(url, None)

        err = urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            with patch("time.sleep"):
                result = fetch_json(url)

        assert result is None


# ---------------------------------------------------------------------------
# iter_named_skills
# ---------------------------------------------------------------------------


class TestIterNamedSkills:
    def test_yields_tuples_of_path_and_dict(self):
        named_root = _REPO_ROOT / "registry" / "named"
        if not named_root.exists():
            pytest.skip("registry/named/ not present in this checkout")

        count = 0
        for path, fm in iter_named_skills(root=named_root):
            assert isinstance(path, Path)
            assert isinstance(fm, dict)
            count += 1
            if count >= 5:
                break

        assert count > 0, "Expected at least one named skill"

    def test_mattpocock_skills_present(self):
        named_root = _REPO_ROOT / "registry" / "named"
        if not named_root.exists():
            pytest.skip("registry/named/ not present in this checkout")

        ids = [fm.get("id") for _, fm in iter_named_skills(root=named_root)]
        assert "mattpocock/skills" in ids, "mattpocock/skills must be in the registry"

    def test_garrytan_gstack_present(self):
        named_root = _REPO_ROOT / "registry" / "named"
        if not named_root.exists():
            pytest.skip("registry/named/ not present in this checkout")

        ids = [fm.get("id") for _, fm in iter_named_skills(root=named_root)]
        assert "garrytan/gstack" in ids, "garrytan/gstack must be in the registry"

    def test_skips_files_without_frontmatter(self, tmp_path):
        """Files with no frontmatter fence are skipped."""
        (tmp_path / "no_fm.md").write_text("# Just markdown\nNo fences.", encoding="utf-8")
        fenced = tmp_path / "has_fm.md"
        fenced.write_text("---\nid: test/x\nname: X\n---\n# body\n", encoding="utf-8")

        results = list(iter_named_skills(root=tmp_path))
        assert len(results) == 1
        assert results[0][1]["id"] == "test/x"

    def test_custom_root_override(self, tmp_path):
        """Passing an explicit root overrides the default registry/named/ path."""
        (tmp_path / "custom.md").write_text(
            "---\nid: custom/skill\nname: Custom\n---\n", encoding="utf-8"
        )
        results = list(iter_named_skills(root=tmp_path))
        assert any(fm.get("id") == "custom/skill" for _, fm in results)
