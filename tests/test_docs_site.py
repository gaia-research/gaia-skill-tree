import os
from pathlib import Path

import pytest

from scripts import build_docs

REPO_ROOT = Path(__file__).parent.parent


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
