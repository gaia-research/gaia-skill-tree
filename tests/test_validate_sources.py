"""Tests for evidence/scripts/validate_sources.py (#1786).

Covers the three URL-gathering modes (lake scan, --urls file, --manifest)
without hitting the network — validate_url is monkeypatched everywhere.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evidence", "scripts"))

import validate_sources  # noqa: E402


def _fake_validate_url(url):
    return url, {"status": "ok", "statusCode": 200}


def test_collect_urls_from_lake_reads_by_type_and_legacy_tiers(tmp_path):
    lake = tmp_path / "evidence"
    by_type = lake / "by-type"
    by_type.mkdir(parents=True)
    (by_type / "repo-own.md").write_text(
        "## Skill: `alice-skill`\n"
        "- **Source:** [https://github.com/alice/tool](https://github.com/alice/tool)\n",
        encoding="utf-8",
    )
    (lake / "tier_3.md").write_text(
        "## Skill: `legacy-skill`\n"
        "- **Source:** [https://github.com/legacy/tool](https://github.com/legacy/tool)\n",
        encoding="utf-8",
    )

    occurrences = validate_sources.collect_urls_from_lake(str(lake))
    assert "https://github.com/alice/tool" in occurrences
    assert "https://github.com/legacy/tool" in occurrences
    fname, _, skill_id = occurrences["https://github.com/alice/tool"][0]
    assert fname == os.path.join("by-type", "repo-own.md")
    assert skill_id == "alice-skill"


def test_collect_urls_from_file(tmp_path):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("https://example.com/a\n# comment\n\nhttps://example.com/b\n", encoding="utf-8")
    occurrences = validate_sources.collect_urls_from_file(str(urls_file))
    assert set(occurrences.keys()) == {"https://example.com/a", "https://example.com/b"}


def test_collect_urls_from_manifest_json_object_with_candidates_key(tmp_path):
    manifest = tmp_path / "candidates.json"
    manifest.write_text(
        '{"candidates": [{"id": "bob-skill", "url": "https://github.com/bob/tool"}]}',
        encoding="utf-8",
    )
    occurrences = validate_sources.collect_urls_from_manifest(str(manifest))
    assert "https://github.com/bob/tool" in occurrences
    _, _, skill_id = occurrences["https://github.com/bob/tool"][0]
    assert skill_id == "bob-skill"


def test_collect_urls_from_manifest_bare_list_of_strings(tmp_path):
    manifest = tmp_path / "urls.json"
    manifest.write_text('["https://example.com/a", "https://example.com/b"]', encoding="utf-8")
    occurrences = validate_sources.collect_urls_from_manifest(str(manifest))
    assert set(occurrences.keys()) == {"https://example.com/a", "https://example.com/b"}


def test_main_urls_mode_writes_report(tmp_path):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("https://example.com/a\nhttps://example.com/b\n", encoding="utf-8")
    report_path = tmp_path / "report.md"

    with patch.object(validate_sources, "validate_url", side_effect=_fake_validate_url):
        rc = validate_sources.main(["--urls", str(urls_file), "--report", str(report_path)])

    assert rc == 0
    text = report_path.read_text(encoding="utf-8")
    assert "https://example.com/a" in text
    assert "https://example.com/b" in text


def test_main_limit_applies_to_manifest_mode(tmp_path):
    manifest = tmp_path / "candidates.json"
    manifest.write_text(
        '["https://example.com/a", "https://example.com/b", "https://example.com/c"]',
        encoding="utf-8",
    )
    report_path = tmp_path / "report.md"

    with patch.object(validate_sources, "validate_url", side_effect=_fake_validate_url):
        rc = validate_sources.main(["--manifest", str(manifest), "--limit", "1", "--report", str(report_path)])

    assert rc == 0
    text = report_path.read_text(encoding="utf-8")
    # Exactly one of the three URLs should have been validated (order-independent).
    assert sum(1 for u in ("https://example.com/a", "https://example.com/b", "https://example.com/c") if u in text) == 1


def test_urls_and_manifest_mutually_exclusive(tmp_path):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("https://example.com/a\n", encoding="utf-8")
    manifest = tmp_path / "candidates.json"
    manifest.write_text("[]", encoding="utf-8")

    try:
        validate_sources.main(["--urls", str(urls_file), "--manifest", str(manifest)])
        assert False, "expected SystemExit from argparse.error"
    except SystemExit as exc:
        assert exc.code != 0
