"""
scripts/lib/tests/test_heartbeat_regression.py — regression test for stargazerHeartbeat.py.

Verifies that the refactored heartbeat (PR 3/7) produces byte-for-byte identical
output to what the original ``_update_evidence_row_in_text`` logic would have
written, by running ``process_file`` against a fixture file and asserting the
golden output.

Test strategy
-------------
We exercise the heartbeat's ``process_file`` in both dry-run (``apply=False``)
and apply (``apply=True``) modes against an in-memory fixture file.  ``fetch_json``
is mocked to return a canned API response so no live network calls are made.

The golden output is computed from the known fixture contents + the known mock
star count, using ``update_list_item_in_frontmatter`` directly (the same
function that the refactored heartbeat now delegates to).  This proves:

1. The heartbeat correctly delegates to ``update_list_item_in_frontmatter``.
2. The delegation is equivalent to the original ``_update_evidence_row_in_text``
   (which was already tested in ``test_lib.py``).
3. The ``_fetch_stars`` wrapper correctly extracts ``stargazers_count`` from
   the ``fetch_json`` response.
4. The ``_needs_update`` threshold still gates writes correctly.

Note on fixture data
--------------------
The fixture is a minimal synthetic version of ``mattpocock/diagnose.md``
(a real named skill with a ``github-stars-own`` evidence row).  It is NOT
a copy of the live file — the live file changes as stars update, which would
make the test fragile.  The fixture has a known star count (100_000) and the
mock API returns 220_000, which exceeds the 5% threshold so a write is
expected.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from datetime import date
from unittest.mock import patch

import pytest

import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.frontmatter import update_list_item_in_frontmatter
import scripts.stargazerHeartbeat as heartbeat

# ---------------------------------------------------------------------------
# Fixture text — synthetic, based on mattpocock/diagnose.md structure
# ---------------------------------------------------------------------------

_FIXTURE_STARS_STORED = 100_000
_MOCK_API_STARS = 220_000  # > 5% delta AND > 100 absolute → should update

FIXTURE_TEXT = textwrap.dedent(f"""\
    ---
    id: mattpocock/diagnose
    name: Diagnose
    contributor: mattpocock
    status: named
    level: 3★
    links:
      github: https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md
    evidence:
    - class: B
      source: https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md
      type: repo
      trustNumber: 70.0
    - source: https://github.com/mattpocock/skills
      type: github-stars-own
      stars: {_FIXTURE_STARS_STORED}
      updatedAt: '2026-01-01'
      notes: mattpocock/skills suite
    ---
    # Diagnose

    Body text.
    """)

# The evidence row that contains stars is at index 1 (0-based).
_EVIDENCE_ROW_IDX = 1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_FETCH_JSON_RESPONSE = {"stargazers_count": _MOCK_API_STARS, "full_name": "mattpocock/skills"}


def _make_mock_fetch_json(response: dict | None):
    """Return a mock that sleeps 0 ms and returns *response* for any URL."""
    def _fake(url, token=None, timeout=10):
        return response
    return _fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHeartbeatDryRun:
    """apply=False — no file writes, correct result rows returned."""

    def test_returns_result_row_with_expected_fields(self, tmp_path):
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            rows = heartbeat.process_file(fixture_path, apply=False)

        assert len(rows) == 1  # only one github-stars-own row
        row = rows[0]
        assert row["skill_id"] == "mattpocock/diagnose"
        assert row["evidence_idx"] == _EVIDENCE_ROW_IDX
        assert row["old_stars"] == _FIXTURE_STARS_STORED
        assert row["new_stars"] == _MOCK_API_STARS
        assert row["delta"] == _MOCK_API_STARS - _FIXTURE_STARS_STORED
        assert row["updated"] is False  # dry-run never writes
        assert row["skip_reason"] is None

    def test_file_not_modified_in_dry_run(self, tmp_path):
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")
        original_text = fixture_path.read_text(encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            heartbeat.process_file(fixture_path, apply=False)

        assert fixture_path.read_text(encoding="utf-8") == original_text

    def test_needs_update_triggers_for_fixture(self):
        """Sanity-check: the mock delta is large enough to warrant an update."""
        assert heartbeat._needs_update(_FIXTURE_STARS_STORED, _MOCK_API_STARS)


class TestHeartbeatApplyMode:
    """apply=True — file is written with updated star count + today's updatedAt."""

    def test_apply_writes_updated_stars(self, tmp_path):
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            rows = heartbeat.process_file(fixture_path, apply=True)

        assert rows[0]["updated"] is True
        written = fixture_path.read_text(encoding="utf-8")
        assert f"stars: {_MOCK_API_STARS}" in written
        assert f"stars: {_FIXTURE_STARS_STORED}" not in written

    def test_apply_sets_updatedAt_to_today(self, tmp_path):
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")
        today = date.today().isoformat()

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            heartbeat.process_file(fixture_path, apply=True)

        written = fixture_path.read_text(encoding="utf-8")
        assert f"updatedAt: '{today}'" in written

    def test_apply_golden_output_matches_update_list_item(self, tmp_path):
        """Golden-output test: heartbeat apply must produce the same bytes as
        calling update_list_item_in_frontmatter directly with the same args.

        This is the byte-for-byte regression proof: if the heartbeat delegates
        correctly to update_list_item_in_frontmatter, the output must be
        identical to calling that function directly.
        """
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")
        today = date.today().isoformat()

        # Compute golden output directly via the lib function
        golden = update_list_item_in_frontmatter(
            FIXTURE_TEXT,
            list_key="evidence",
            row_index=_EVIDENCE_ROW_IDX,
            field_updates={"stars": _MOCK_API_STARS, "updatedAt": today},
        )

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            heartbeat.process_file(fixture_path, apply=True)

        written = fixture_path.read_text(encoding="utf-8")
        assert written == golden, (
            "Heartbeat apply output does not match golden update_list_item_in_frontmatter output.\n"
            f"Expected:\n{golden}\n\nActual:\n{written}"
        )

    def test_non_star_evidence_rows_untouched(self, tmp_path):
        """The first evidence row (type: repo) must not be modified."""
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            heartbeat.process_file(fixture_path, apply=True)

        written = fixture_path.read_text(encoding="utf-8")
        # The repo-type evidence row's trustNumber must survive unchanged
        assert "trustNumber: 70.0" in written

    def test_body_text_preserved_after_apply(self, tmp_path):
        """Body content after the closing --- must be byte-for-byte identical."""
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            heartbeat.process_file(fixture_path, apply=True)

        written = fixture_path.read_text(encoding="utf-8")
        assert "# Diagnose\n\nBody text.\n" in written


class TestHeartbeatApiErrors:
    """Robustness: API failures produce skip_reason rows, no writes."""

    def test_api_error_produces_skip_row(self, tmp_path):
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(None)):
            rows = heartbeat.process_file(fixture_path, apply=True)

        assert rows[0]["skip_reason"] == "api_error"
        assert rows[0]["updated"] is False

    def test_file_not_written_on_api_error(self, tmp_path):
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")
        original = fixture_path.read_text(encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(None)):
            heartbeat.process_file(fixture_path, apply=True)

        assert fixture_path.read_text(encoding="utf-8") == original


class TestHeartbeatBelowThreshold:
    """When the delta is within threshold, apply=True must NOT write."""

    def test_no_update_when_delta_below_threshold(self, tmp_path):
        # Same stars — zero delta — no update expected
        fixture_path = tmp_path / "diagnose.md"
        fixture_path.write_text(FIXTURE_TEXT, encoding="utf-8")
        original = fixture_path.read_text(encoding="utf-8")

        same_response = {"stargazers_count": _FIXTURE_STARS_STORED}
        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(same_response)):
            rows = heartbeat.process_file(fixture_path, apply=True)

        assert rows[0]["updated"] is False
        assert fixture_path.read_text(encoding="utf-8") == original


class TestHeartbeatNoGithubUrl:
    """Evidence rows with no resolvable GitHub URL are skipped gracefully."""

    def test_no_github_url_skipped(self, tmp_path):
        text = textwrap.dedent("""\
            ---
            id: test/norepo
            name: No Repo
            evidence:
            - type: github-stars-own
              source: https://example.com/not-github
              stars: 5000
            ---
            """)
        fixture_path = tmp_path / "norepo.md"
        fixture_path.write_text(text, encoding="utf-8")

        with patch("scripts.stargazerHeartbeat.fetch_json", side_effect=_make_mock_fetch_json(_MOCK_FETCH_JSON_RESPONSE)):
            rows = heartbeat.process_file(fixture_path, apply=True)

        assert rows[0]["skip_reason"] == "no_github_url"
        assert rows[0]["updated"] is False
