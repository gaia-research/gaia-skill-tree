"""Unit tests for gaia dev update-named (#791)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.named import meta_update_named_command
pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_named(named_dir: Path, slug: str = "alice/test-skill",
                 level: str = "2★", status: str = "named",
                 title: str = "The Test Skill") -> Path:
    contributor, name = slug.split("/", 1)
    skill_dir = named_dir / contributor
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / f"{name}.md"
    path.write_text(
        f"---\nid: {slug}\nname: Test Skill\ncontributor: {contributor}\n"
        f"origin: true\ngenericSkillRef: test-skill\nstatus: {status}\n"
        f"level: {level}\ntitle: {title}\n"
        f"description: A named skill for update-named tests.\n---\n",
        encoding="utf-8",
    )
    return path


def _make_registry(tmp_path: Path, **kwargs) -> str:
    named_dir = tmp_path / "registry" / "named"
    _write_named(named_dir, **kwargs)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    return str(tmp_path)


def _args(root: str, skill_id: str = "alice/test-skill", **kw) -> SimpleNamespace:
    base = dict(
        registry=root,
        skill_id=skill_id,
        status=None,
        title=None,
        catalog_ref=None,
        generic_ref=None,
        suite_components=None,
        suite_ref=None,
        installation_file=None,
        origin=None,
        github_link=None,
        installable=None,
        no_build=True,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.named._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.named._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.named.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_update_named_sets_status(tmp_path):
    root = _make_registry(tmp_path)
    meta_update_named_command(_args(root, status="awakened"))
    md = (Path(root) / "registry" / "named" / "alice" / "test-skill.md").read_text(encoding="utf-8")
    assert "status: awakened" in md


def test_update_named_sets_generic_ref(tmp_path):
    root = _make_registry(tmp_path)
    meta_update_named_command(_args(root, generic_ref="other-skill"))
    md = (Path(root) / "registry" / "named" / "alice" / "test-skill.md").read_text(encoding="utf-8")
    assert "genericSkillRef: other-skill" in md


def test_update_named_sets_installable_false(tmp_path):
    root = _make_registry(tmp_path)
    meta_update_named_command(_args(root, installable="false"))
    md = (Path(root) / "registry" / "named" / "alice" / "test-skill.md").read_text(encoding="utf-8")
    assert "installable: false" in md


# ---------------------------------------------------------------------------
# Rejection paths
# ---------------------------------------------------------------------------


def test_update_named_missing_skill_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, skill_id="alice/nonexistent"))
    assert exc.value.code != 0


def test_update_named_status_named_requires_title(tmp_path, capsys):
    """Setting status=named on a skill without a title/catalogRef must be rejected."""
    root = _make_registry(tmp_path, title="")
    # Remove title from the file
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    content = path.read_text(encoding="utf-8").replace("title: \n", "").replace("title:\n", "")
    path.write_text(content, encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, status="named"))

    assert exc.value.code != 0
    assert path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "status='named' requires 'title' or 'catalogRef'" in err
    assert "--title" in err
    assert "--catalog-ref" in err


def test_update_named_suite_components_rejects_nonexistent(tmp_path, capsys):
    root = _make_registry(tmp_path)
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, suite_components="alice/nonexistent"))
    assert exc.value.code != 0
    assert path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "Suite component 'alice/nonexistent' does not exist in the registry." in err


def test_update_named_suite_components_rejects_duplicates(tmp_path, capsys):
    root = _make_registry(tmp_path)
    _write_named(Path(root) / "registry" / "named", slug="alice/other-skill")
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, suite_components="alice/other-skill,alice/other-skill"))
    assert exc.value.code != 0
    assert path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "Duplicate suite components are not allowed: alice/other-skill." in err


def test_update_named_suite_components_rejects_empty_entry_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    _write_named(Path(root) / "registry" / "named", slug="alice/other-skill")
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, suite_components="alice/other-skill,"))
    assert exc.value.code != 0
    assert path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "Empty suite component entries are not allowed" in err


def test_update_named_suite_components_happy_path(tmp_path):
    root = _make_registry(tmp_path)
    _write_named(Path(root) / "registry" / "named", slug="alice/other-skill")
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    meta_update_named_command(_args(root, suite_components="alice/other-skill"))
    from gaia_cli.commands.dev.helpers import _parse_md
    meta, _ = _parse_md(path)
    assert meta["suiteComponents"] == ["alice/other-skill"]


def test_update_named_github_link_rejects_tree(tmp_path, capsys):
    root = _make_registry(tmp_path)
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, github_link="https://github.com/alice/repo/tree/main/skills/test-skill"))
    assert exc.value.code != 0
    assert path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "uses '/tree/' which is not supported" in err


def test_update_named_github_link_rejects_bare(tmp_path, capsys):
    root = _make_registry(tmp_path)
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, github_link="https://github.com/alice/repo"))
    assert exc.value.code != 0
    assert path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "missing the '/blob/' segment" in err


def test_update_named_github_link_rejects_non_github_url(tmp_path, capsys):
    root = _make_registry(tmp_path)
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        meta_update_named_command(_args(root, github_link="https://example.com/alice/repo/blob/main/skill.md"))
    assert exc.value.code != 0
    assert path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "GitHub link must start with 'https://github.com/'" in err


def test_update_named_github_link_happy_path(tmp_path):
    root = _make_registry(tmp_path)
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    meta_update_named_command(_args(root, github_link="https://github.com/alice/repo/blob/main/skills/test-skill/SKILL.md"))
    from gaia_cli.commands.dev.helpers import _parse_md
    meta, _ = _parse_md(path)
    assert meta["links"]["github"] == "https://github.com/alice/repo/blob/main/skills/test-skill/SKILL.md"


# ---------------------------------------------------------------------------
# Empty-string clear (Issue #936)
# ---------------------------------------------------------------------------


def test_update_named_github_link_empty_clears_existing(tmp_path):
    """Empty string --github-link '' should clear an existing links.github entry."""
    root = _make_registry(tmp_path)
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    # First set a link.
    meta_update_named_command(_args(root, github_link="https://github.com/alice/repo/blob/main/skills/test-skill/SKILL.md"))
    from gaia_cli.commands.dev.helpers import _parse_md
    meta, _ = _parse_md(path)
    assert meta["links"]["github"].endswith("SKILL.md")

    # Now clear it with an empty string.
    meta_update_named_command(_args(root, github_link=""))
    meta, _ = _parse_md(path)
    # links.github should be gone; links dict itself is pruned if empty.
    assert "github" not in meta.get("links", {})


def test_update_named_github_link_empty_no_op_when_absent(tmp_path):
    """Empty string --github-link '' on a skill with no link should be a no-op (still reports)."""
    root = _make_registry(tmp_path)
    path = Path(root) / "registry" / "named" / "alice" / "test-skill.md"
    before = path.read_text(encoding="utf-8")
    # Should not crash; may report "No changes specified." since nothing to remove.
    meta_update_named_command(_args(root, github_link=""))
    # File should be unchanged (no links.github to remove → no write).
    assert path.read_text(encoding="utf-8") == before
