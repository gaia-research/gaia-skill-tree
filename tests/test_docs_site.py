import json
import os
from pathlib import Path

import pytest

from scripts import build_docs

REPO_ROOT = Path(__file__).parent.parent


def test_check_ignores_volatile_release_timestamps():
    """`docs build --check` must not flag date-only drift.

    assemble_gaia.py stamps gaia.json's generatedAt with wall-clock now(), which
    cascades into named-skills.json and docs/tree.md. Auto-Sync re-stamps it on
    every main merge, so a feature PR built a day later would otherwise fail the
    integrity gate on a pure date diff. Both tree.md provenance forms and the
    JSON generatedAt must normalize equal across differing dates.
    """
    header_a = "GAIA SKILL TREE  v4.7.12  ·  generated 2026-06-13"
    header_b = "GAIA SKILL TREE  v4.7.12  ·  generated 2026-06-14"
    footer_a = "*Generated from gaia.json on 2026-06-13. Do not edit directly.*"
    footer_b = "*Generated from gaia.json on 2026-06-14. Do not edit directly.*"
    json_a = '{\n  "generatedAt": "2026-06-13",\n  "x": 1\n}'
    json_b = '{\n  "generatedAt": "2026-06-14",\n  "x": 1\n}'

    assert build_docs._normalize_dates(header_a) == build_docs._normalize_dates(header_b)
    assert build_docs._normalize_dates(footer_a) == build_docs._normalize_dates(footer_b)
    assert build_docs._normalize_dates(json_a) == build_docs._normalize_dates(json_b)

    # Real content drift must still be caught.
    json_c = '{\n  "generatedAt": "2026-06-14",\n  "x": 2\n}'
    assert build_docs._normalize_dates(json_b) != build_docs._normalize_dates(json_c)


def test_badge_registry_generated_at_mirrors_source(tmp_path, monkeypatch):
    """The badge registry must stamp the source date, not wall-clock time.

    Using today's date made docs/badges/registry.json drift every calendar day,
    tripping `build_docs.py --check` on any CI run after the last regeneration.
    The regenerated date must equal registry/named-skills.json's own
    `generatedAt` so the artifact is reproducible regardless of when it runs.
    """
    from scripts import generateBadges

    mock_named_json = tmp_path / "named-skills.json"
    mock_named_json.write_text(json.dumps({
        "generatedAt": "2026-06-20",
        "buckets": {}
    }), encoding="utf-8")

    monkeypatch.setattr(generateBadges, "NAMED_JSON", mock_named_json)

    out_dir = tmp_path / "badges"
    assert generateBadges.main(["--out-dir", str(out_dir)]) == 0

    regenerated = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    assert regenerated["generatedAt"] == "2026-06-20"


def test_build_docs_check_message_uses_copyable_python_command(monkeypatch, capsys):
    monkeypatch.setattr(build_docs, "build_readme", lambda check: True)
    monkeypatch.setattr(build_docs, "build_docs_index", lambda check: False)

    assert build_docs.main(["--check"]) == 1

    output = capsys.readouterr().out
    assert "gaia docs build --check" in output


def test_readme_documents_claimed_vs_effective_levels():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "demerit" in readme.lower()


def test_readme_documents_ultimate_requirements():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "ultimate" in readme.lower()
    assert "class a" in readme.lower()
