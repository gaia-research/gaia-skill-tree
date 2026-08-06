"""
Unit tests for scripts/upstream_watcher/*.

Test scope (per PR 6 spec):
1. Mode detection: ``components`` vs ``version-only``.
2. Payload structure: correct JSON shape in the umbrella body.
3. Idempotency: mocked ``gh issue list`` returning a match → no duplicate creation.
4. Link liveness URL conversion: ``blob/main/x/SKILL.md`` → ``raw.githubusercontent.com/…``

All GitHub API calls are mocked.  No network requests are made.

Run with:
    pytest scripts/upstream_watcher/tests/ -v
or via the normal suite:
    pytest -k "upstream_watcher"
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.upstream_watcher.finder import (
    _parse_star_level,
    compute_finding,
    detect_mode,
)
from scripts.upstream_watcher.issuer import (
    _find_existing_issue,
    _payload_block,
    render_bootstrap_body,
    render_child_body,
    render_umbrella_body,
)
from scripts.upstream_watcher.liveness import (
    blob_to_raw,
    check_component_liveness,
    fetch_component_diff,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SUITE_FM = {
    "id": "mattpocock/skills",
    "level": "5★",
    "links": {"github": "https://github.com/mattpocock/skills"},
    "suiteComponents": [
        "mattpocock/caveman",
        "mattpocock/diagnose",
        "mattpocock/grill-me",
    ],
    "watchUpstream": None,
}

_CAVEMAN_FM = {
    "id": "mattpocock/caveman",
    "level": "2★",
    "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills/caveman/SKILL.md"},
}

_DIAGNOSE_FM = {
    "id": "mattpocock/diagnose",
    "level": "2★",
    "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills/diagnose/SKILL.md"},
}

_GRILL_ME_FM = {
    "id": "mattpocock/grill-me",
    "level": "2★",
    "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills/grill-me/SKILL.md"},
}

_REGISTRY_MAP_SAME_REPO = {
    "mattpocock/caveman": _CAVEMAN_FM,
    "mattpocock/diagnose": _DIAGNOSE_FM,
    "mattpocock/grill-me": _GRILL_ME_FM,
}

_RELEASE_DATA = {
    "tag_name": "v1.2.0",
    "published_at": "2026-07-01T00:00:00Z",
    "html_url": "https://github.com/mattpocock/skills/releases/tag/v1.2.0",
}


# ---------------------------------------------------------------------------
# 1. Mode detection
# ---------------------------------------------------------------------------


class TestDetectMode:
    def test_components_mode_all_same_repo(self):
        """All components in same owner/repo → 'components' mode."""
        mode = detect_mode(_SUITE_FM, _REGISTRY_MAP_SAME_REPO)
        assert mode == "components"

    def test_version_only_when_component_in_different_repo(self):
        """A component pointing to a different repo → 'version-only'."""
        different_repo_map = {
            **_REGISTRY_MAP_SAME_REPO,
            "mattpocock/caveman": {
                "id": "mattpocock/caveman",
                "level": "2★",
                "links": {"github": "https://github.com/other-org/other-repo/blob/main/SKILL.md"},
            },
        }
        mode = detect_mode(_SUITE_FM, different_repo_map)
        assert mode == "version-only"

    def test_version_only_when_component_missing_from_registry(self):
        """Component not in registry_map → 'version-only'."""
        sparse_map = {
            "mattpocock/diagnose": _DIAGNOSE_FM,
            # caveman and grill-me missing
        }
        mode = detect_mode(_SUITE_FM, sparse_map)
        assert mode == "version-only"

    def test_version_only_when_suite_has_no_github_link(self):
        """Suite without links.github → 'version-only'."""
        fm_no_link = {**_SUITE_FM, "links": {}}
        mode = detect_mode(fm_no_link, _REGISTRY_MAP_SAME_REPO)
        assert mode == "version-only"

    def test_version_only_when_component_has_no_github_link(self):
        """Component with no links.github → 'version-only'."""
        map_no_link = {
            **_REGISTRY_MAP_SAME_REPO,
            "mattpocock/grill-me": {
                "id": "mattpocock/grill-me",
                "level": "2★",
                "links": {},
            },
        }
        mode = detect_mode(_SUITE_FM, map_no_link)
        assert mode == "version-only"

    def test_version_only_mode_for_different_owner(self):
        """Different owner on component → 'version-only'."""
        map_diff_owner = {
            **_REGISTRY_MAP_SAME_REPO,
            "mattpocock/diagnose": {
                "id": "mattpocock/diagnose",
                "level": "2★",
                "links": {"github": "https://github.com/someone-else/skills/blob/main/diagnose/SKILL.md"},
            },
        }
        mode = detect_mode(_SUITE_FM, map_diff_owner)
        assert mode == "version-only"


# ---------------------------------------------------------------------------
# 2. Payload structure
# ---------------------------------------------------------------------------


class TestPayloadStructure:
    def _extract_payload(self, body: str) -> dict:
        """Extract JSON payload from issue body HTML comment."""
        import re
        m = re.search(r"<!-- gaia-upstream-payload\n(.*?)-->", body, re.DOTALL)
        assert m, "No payload block found in issue body"
        return json.loads(m.group(1))

    def test_umbrella_body_payload_keys(self):
        finding = {
            "finding_type": "update",
            "skillId": "mattpocock/skills",
            "currentVersion": "v1.0.0",
            "newVersion": "v1.2.0",
            "releasedAt": "2026-07-01T00:00:00Z",
            "sourceUrl": "https://github.com/mattpocock/skills/releases/tag/v1.2.0",
        }
        body = render_umbrella_body(
            finding,
            mode="components",
            component_adds=["new-skill"],
            component_removes=["old-skill"],
            link_liveness=[{"skillId": "mattpocock/caveman", "url": "...", "rawUrl": "...", "status": 404}],
        )
        payload = self._extract_payload(body)
        required_keys = {
            "skillId", "previousVersion", "newVersion", "releasedAt",
            "sourceUrl", "mode", "componentAdds", "componentRemoves", "linkLiveness",
        }
        assert required_keys.issubset(set(payload.keys()))
        assert payload["skillId"] == "mattpocock/skills"
        assert payload["previousVersion"] == "v1.0.0"
        assert payload["newVersion"] == "v1.2.0"
        assert payload["mode"] == "components"
        assert payload["componentAdds"] == ["new-skill"]
        assert payload["componentRemoves"] == ["old-skill"]
        assert len(payload["linkLiveness"]) == 1

    def test_bootstrap_body_payload_keys(self):
        finding = {
            "finding_type": "bootstrap",
            "skillId": "mattpocock/skills",
            "currentVersion": None,
            "newVersion": "v1.2.0",
            "releasedAt": "2026-07-01T00:00:00Z",
            "sourceUrl": "https://github.com/mattpocock/skills/releases/tag/v1.2.0",
        }
        body = render_bootstrap_body(finding)
        payload = self._extract_payload(body)
        assert payload["skillId"] == "mattpocock/skills"
        assert payload["previousVersion"] is None
        assert payload["newVersion"] == "v1.2.0"
        assert payload["mode"] == "bootstrap"

    def test_umbrella_body_contains_version_mode_note(self):
        """version-only mode note should be in the body."""
        finding = {
            "finding_type": "update",
            "skillId": "mattpocock/skills",
            "currentVersion": "v1.0.0",
            "newVersion": "v1.2.0",
            "releasedAt": "2026-07-01T00:00:00Z",
            "sourceUrl": "https://github.com/mattpocock/skills/releases/tag/v1.2.0",
        }
        body = render_umbrella_body(finding, "version-only", [], [], [])
        assert "version-only" in body

    def test_child_body_contains_umbrella_ref(self):
        body = render_child_body(
            slug="new-skill",
            contributor="mattpocock",
            umbrella_number=42,
            suite_gh_url="https://github.com/mattpocock/skills",
        )
        assert "#42" in body
        assert "Umbrella: #42" in body

    def test_child_body_contains_suggested_id(self):
        body = render_child_body(
            slug="caveman",
            contributor="mattpocock",
            umbrella_number=99,
            suite_gh_url="https://github.com/mattpocock/skills",
        )
        assert "mattpocock/caveman" in body


# ---------------------------------------------------------------------------
# 3. Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_find_existing_issue_returns_number_on_match(self):
        """Mocked gh returns an existing issue → _find_existing_issue returns its number."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [{"number": 123, "title": "[upstream] mattpocock/skills → v1.2.0"}]
        )

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = _find_existing_issue(
                "mattpocock/skills → v1.2.0", "upstream:release"
            )
        assert result == 123
        mock_run.assert_called_once()

    def test_find_existing_issue_returns_none_on_no_match(self):
        """gh returns empty list → None."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([])

        with patch("subprocess.run", return_value=mock_result):
            result = _find_existing_issue(
                "mattpocock/skills → v2.0.0", "upstream:release"
            )
        assert result is None

    def test_find_existing_issue_returns_none_on_gh_error(self):
        """gh non-zero exit → None (graceful degradation)."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = _find_existing_issue("anything", "upstream:release")
        assert result is None

    def test_find_existing_issue_returns_none_on_subprocess_exception(self):
        """subprocess.run raises → None (does not propagate)."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 30)):
            result = _find_existing_issue("anything", "upstream:release")
        assert result is None


# ---------------------------------------------------------------------------
# 4. Link liveness URL conversion
# ---------------------------------------------------------------------------


class TestBlobToRaw:
    def test_blob_url_converted(self):
        url = "https://github.com/mattpocock/skills/blob/main/skills/caveman/SKILL.md"
        raw = blob_to_raw(url)
        assert raw == "https://raw.githubusercontent.com/mattpocock/skills/main/skills/caveman/SKILL.md"

    def test_non_blob_url_unchanged(self):
        url = "https://github.com/mattpocock/skills"
        assert blob_to_raw(url) == url

    def test_tree_url_unchanged(self):
        url = "https://github.com/mattpocock/skills/tree/main/skills"
        assert blob_to_raw(url) == url

    def test_already_raw_url_unchanged(self):
        url = "https://raw.githubusercontent.com/mattpocock/skills/main/SKILL.md"
        assert blob_to_raw(url) == url

    def test_blob_url_deep_path(self):
        url = "https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md"
        raw = blob_to_raw(url)
        assert raw == "https://raw.githubusercontent.com/garrytan/gstack/main/benchmark/SKILL.md"
        assert "/blob/" not in raw


class TestCheckComponentLiveness:
    def test_healthy_components_not_in_result(self):
        """2xx responses omitted from result."""
        registry_map = {
            "mattpocock/caveman": {
                "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills/caveman/SKILL.md"}
            }
        }
        with patch("scripts.upstream_watcher.liveness.head_check", return_value=200):
            result = check_component_liveness(["mattpocock/caveman"], registry_map)
        assert result == []

    def test_404_component_in_result(self):
        """404 response included in result."""
        registry_map = {
            "mattpocock/caveman": {
                "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills/caveman/SKILL.md"}
            }
        }
        with patch("scripts.upstream_watcher.liveness.head_check", return_value=404):
            result = check_component_liveness(["mattpocock/caveman"], registry_map)
        assert len(result) == 1
        assert result[0]["skillId"] == "mattpocock/caveman"
        assert result[0]["status"] == 404

    def test_network_error_in_result(self):
        """None status (network error) included in result."""
        registry_map = {
            "mattpocock/diagnose": {
                "links": {"github": "https://github.com/mattpocock/skills/blob/main/skills/diagnose/SKILL.md"}
            }
        }
        with patch("scripts.upstream_watcher.liveness.head_check", return_value=None):
            result = check_component_liveness(["mattpocock/diagnose"], registry_map)
        assert len(result) == 1
        assert result[0]["status"] == "network_error"

    def test_components_without_registry_entry_skipped(self):
        """Components not in registry_map are skipped silently."""
        with patch("scripts.upstream_watcher.liveness.head_check", return_value=200):
            result = check_component_liveness(["unknown/skill"], {})
        assert result == []

    def test_raw_url_used_for_head_check(self):
        """blob/ URL is converted to raw URL before calling head_check."""
        blob_url = "https://github.com/mattpocock/skills/blob/main/skills/caveman/SKILL.md"
        expected_raw = "https://raw.githubusercontent.com/mattpocock/skills/main/skills/caveman/SKILL.md"
        registry_map = {"mattpocock/caveman": {"links": {"github": blob_url}}}

        called_with = []

        def mock_head_check(url, **kwargs):
            called_with.append(url)
            return 200

        with patch("scripts.upstream_watcher.liveness.head_check", side_effect=mock_head_check):
            check_component_liveness(["mattpocock/caveman"], registry_map)

        assert called_with == [expected_raw]


# ---------------------------------------------------------------------------
# 4b. Component diff — nested vs flat suite layouts (issue #1455)
# ---------------------------------------------------------------------------


def _tree_item(path: str, item_type: str) -> dict:
    return {"path": path, "type": item_type, "sha": f"sha-{path}"}


# Synthesized `mattpocock/skills`-style nested layout:
#   skills/engineering/<comp>/SKILL.md
#   skills/productivity/<comp>/SKILL.md
#   deprecated/                    (grouping dir, no SKILL.md beneath it)
#   misc/README.md                 (non-skill file, no SKILL.md)
_NESTED_TREE_DATA = {
    "tree": [
        _tree_item("skills", "tree"),
        _tree_item("skills/engineering", "tree"),
        _tree_item("skills/engineering/caveman", "tree"),
        _tree_item("skills/engineering/caveman/SKILL.md", "blob"),
        _tree_item("skills/engineering/diagnose", "tree"),
        _tree_item("skills/engineering/diagnose/SKILL.md", "blob"),
        _tree_item("skills/productivity", "tree"),
        _tree_item("skills/productivity/grill-me", "tree"),
        _tree_item("skills/productivity/grill-me/SKILL.md", "blob"),
        _tree_item("deprecated", "tree"),
        _tree_item("misc", "tree"),
        _tree_item("misc/README.md", "blob"),
    ],
    "truncated": False,
}

# Flat layout, for regression coverage that existing suites are unaffected:
#   skills/<comp>/SKILL.md
_FLAT_TREE_DATA = {
    "tree": [
        _tree_item("skills", "tree"),
        _tree_item("skills/caveman", "tree"),
        _tree_item("skills/caveman/SKILL.md", "blob"),
        _tree_item("skills/diagnose", "tree"),
        _tree_item("skills/diagnose/SKILL.md", "blob"),
        _tree_item("skills/grill-me", "tree"),
        _tree_item("skills/grill-me/SKILL.md", "blob"),
    ],
    "truncated": False,
}


class TestFetchComponentDiffNestedLayout:
    def test_nested_components_produce_no_false_diff(self):
        """Nested SKILL.md leaves under category dirs are discovered; no
        false adds/removes when the current component list already matches
        upstream."""
        current_components = [
            "mattpocock/caveman",
            "mattpocock/diagnose",
            "mattpocock/grill-me",
        ]
        with patch(
            "scripts.upstream_watcher.liveness.fetch_json",
            return_value=_NESTED_TREE_DATA,
        ):
            adds, removes = fetch_component_diff(
                "mattpocock", "skills", "v1.1.0", "skills", current_components
            )
        assert adds == []
        assert removes == []

    def test_grouping_directories_not_reported_as_additions(self):
        """`deprecated/` (no SKILL.md beneath it) and `misc/` (README only,
        no SKILL.md) must never surface as component additions, even
        starting from an empty current-component list."""
        with patch(
            "scripts.upstream_watcher.liveness.fetch_json",
            return_value=_NESTED_TREE_DATA,
        ):
            adds, removes = fetch_component_diff(
                "mattpocock", "skills", "v1.1.0", "skills", []
            )
        assert "deprecated" not in adds
        assert "misc" not in adds
        assert "engineering" not in adds
        assert "productivity" not in adds
        assert set(adds) == {"caveman", "diagnose", "grill-me"}

    def test_new_nested_component_detected_as_add(self):
        """A genuinely new nested component is reported as an add, not
        confused with its category directory."""
        current_components = ["mattpocock/caveman", "mattpocock/diagnose"]
        with patch(
            "scripts.upstream_watcher.liveness.fetch_json",
            return_value=_NESTED_TREE_DATA,
        ):
            adds, removes = fetch_component_diff(
                "mattpocock", "skills", "v1.1.0", "skills", current_components
            )
        assert adds == ["grill-me"]
        assert removes == []

    def test_removed_nested_component_detected_as_remove(self):
        """A component no longer present anywhere in the nested tree is
        reported as a removal."""
        current_components = [
            "mattpocock/caveman",
            "mattpocock/diagnose",
            "mattpocock/grill-me",
            "mattpocock/retired-tool",
        ]
        with patch(
            "scripts.upstream_watcher.liveness.fetch_json",
            return_value=_NESTED_TREE_DATA,
        ):
            adds, removes = fetch_component_diff(
                "mattpocock", "skills", "v1.1.0", "skills", current_components
            )
        assert adds == []
        assert removes == ["retired-tool"]

    def test_flat_layout_still_works_unchanged(self):
        """Existing flat-suite layouts (component directly under
        component_root) are unaffected by the nested-discovery rewrite."""
        current_components = [
            "mattpocock/caveman",
            "mattpocock/diagnose",
            "mattpocock/grill-me",
        ]
        with patch(
            "scripts.upstream_watcher.liveness.fetch_json",
            return_value=_FLAT_TREE_DATA,
        ):
            adds, removes = fetch_component_diff(
                "mattpocock", "skills", "v1.1.0", "skills", current_components
            )
        assert adds == []
        assert removes == []

    def test_missing_component_root_falls_back_version_only(self):
        """component_root absent from the tree entirely → ([], []) fallback."""
        tree_data = {"tree": [_tree_item("README.md", "blob")], "truncated": False}
        with patch(
            "scripts.upstream_watcher.liveness.fetch_json", return_value=tree_data
        ):
            adds, removes = fetch_component_diff(
                "mattpocock", "skills", "v1.1.0", "skills", ["mattpocock/caveman"]
            )
        assert adds == []
        assert removes == []

    def test_tree_fetch_failure_returns_empty_diff(self):
        """fetch_json returning None (API error) → ([], []) gracefully."""
        with patch(
            "scripts.upstream_watcher.liveness.fetch_json", return_value=None
        ):
            adds, removes = fetch_component_diff(
                "mattpocock", "skills", "v1.1.0", "skills", ["mattpocock/caveman"]
            )
        assert adds == []
        assert removes == []


# ---------------------------------------------------------------------------
# 5. Star-level parsing
# ---------------------------------------------------------------------------


class TestParseStarLevel:
    def test_star_unicode(self):
        assert _parse_star_level("2★") == 2
        assert _parse_star_level("5★") == 5

    def test_star_ascii(self):
        assert _parse_star_level("3*") == 3

    def test_none_returns_zero(self):
        assert _parse_star_level(None) == 0

    def test_empty_returns_zero(self):
        assert _parse_star_level("") == 0


# ---------------------------------------------------------------------------
# 6. compute_finding
# ---------------------------------------------------------------------------


class TestComputeFinding:
    def test_bootstrap_when_no_upstream_block(self):
        fm = {"id": "mattpocock/skills", "level": "5★"}
        finding = compute_finding(fm, _RELEASE_DATA)
        assert finding is not None
        assert finding["finding_type"] == "bootstrap"
        assert finding["newVersion"] == "v1.2.0"
        assert finding["currentVersion"] is None

    def test_up_to_date_returns_none(self):
        fm = {
            "id": "mattpocock/skills",
            "level": "5★",
            "upstream": {"version": "v1.2.0"},
        }
        finding = compute_finding(fm, _RELEASE_DATA)
        assert finding is None

    def test_update_when_version_differs(self):
        fm = {
            "id": "mattpocock/skills",
            "level": "5★",
            "upstream": {"version": "v1.0.0"},
        }
        finding = compute_finding(fm, _RELEASE_DATA)
        assert finding is not None
        assert finding["finding_type"] == "update"
        assert finding["currentVersion"] == "v1.0.0"
        assert finding["newVersion"] == "v1.2.0"
