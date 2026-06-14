import json
import os
from pathlib import Path

import pytest

from scripts import build_docs

REPO_ROOT = Path(__file__).parent.parent


def test_badge_registry_generated_at_mirrors_source(tmp_path):
    """The badge registry must stamp the source date, not wall-clock time.

    Using today's date made docs/badges/registry.json drift every calendar day,
    tripping `build_docs.py --check` on any CI run after the last regeneration.
    The regenerated date must equal registry/named-skills.json's own
    `generatedAt` so the artifact is reproducible regardless of when it runs.
    """
    from scripts import generateBadges

    source_stamp = json.loads(
        (REPO_ROOT / "registry" / "named-skills.json").read_text(encoding="utf-8")
    ).get("generatedAt")

    out_dir = tmp_path / "badges"
    assert generateBadges.main(["--out-dir", str(out_dir)]) == 0

    regenerated = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    assert regenerated["generatedAt"] == source_stamp


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
