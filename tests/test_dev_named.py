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
