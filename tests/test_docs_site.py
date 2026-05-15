from pathlib import Path

from scripts import build_docs


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"


def test_how_we_do_things_page_is_linked_from_site_home():
    home = (DOCS_DIR / "index.html").read_text(encoding="utf-8")

    # Phase 5: how-we-do-things.html was renamed to codex.html.
    # The nav now points to codex.html; how-we-do-things.html redirects there.
    assert 'href="codex.html"' in home
    assert "The Codex" in home


def test_how_we_do_things_page_covers_curation_and_review():
    page = DOCS_DIR / "how-we-do-things.html"

    assert page.exists()
    content = page.read_text(encoding="utf-8")
    assert "<h1>How We Work</h1>" in content
    assert "curation" in content.lower()
    assert "automation" in content.lower()
    assert "reviewer" in content.lower()


def test_build_docs_check_message_uses_copyable_python_command(monkeypatch, capsys):
    monkeypatch.setattr(build_docs, "build_readme", lambda check: True)
    monkeypatch.setattr(build_docs, "build_docs_index", lambda check: False)

    assert build_docs.main(["--check"]) == 1

    output = capsys.readouterr().out
    assert "python scripts/build_docs.py --check" in output
    assert "python scripts/build_docs.py" in output
    assert "gaia docs build" not in output


def test_readme_documents_claimed_vs_effective_levels():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "demerit" in readme.lower()


def test_governance_documents_demerit_constraints():
    governance = (DOCS_DIR / "GOVERNANCE.md").read_text(encoding="utf-8")
    assert "Demerits are valid only for 2★+" in governance
    assert "effective level" in governance.lower()
