"""Unit tests for gaia dev build, gaia dev add, gaia dev rm (#791)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.build import (
    meta_build_command,
    meta_add_command,
    meta_remove_command,
    meta_link_command,
    meta_reclassify_command,
)
pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(tmp_path: Path) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    node = {
        "id": "existing-skill",
        "name": "Existing Skill",
        "type": "basic",
        "level": "1★",
        "description": "An existing skill for build tests.",
        "status": "provisional",
        "prerequisites": [],
        "derivatives": [],
        "evidence": [],
        "timeline": [],
        "createdAt": "2026-06-01",
        "updatedAt": "2026-06-01",
        "version": "0.1.0",
    }
    (nodes / "existing-skill.json").write_text(json.dumps(node, indent=2))
    return str(tmp_path)


def _write_named(tmp_path: Path, slug: str, name: str = "Test Skill", level: str = "2★") -> None:
    contributor, skillId = slug.split("/", 1)
    namedDir = tmp_path / "registry" / "named" / contributor
    namedDir.mkdir(parents=True, exist_ok=True)
    path = namedDir / f"{skillId}.md"
    path.write_text(
        f"---\nid: {slug}\nname: {name}\ncontributor: {contributor}\n"
        f"origin: false\ngenericSkillRef: unknown\nstatus: named\n"
        f"level: {level}\ntitle: Epithet\n"
        f"description: A named skill description here.\n---\n",
        encoding="utf-8"
    )


def _add_args(root: str, name: str = "New Skill",
              description: str = "A brand new skill description here.",
              **kw) -> SimpleNamespace:
    base = dict(
        registry=root,
        name=name,
        id=None,
        type="basic",
        description=description,
        named=False,
        contributor="gaiabot",
        generic_ref=None,
        status=None,
        title=None,
        level=None,
        extra_fields=None,
        no_build=True,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _rm_args(root: str, skill_id: str = "existing-skill", **kw) -> SimpleNamespace:
    base = dict(registry=root, skill_id=skill_id, yes=True, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


def _reclassify_args(root: str, skill_id: str = "existing-skill", new_type: str = "fusion", **kw) -> SimpleNamespace:
    base = dict(registry=root, skill_id=skill_id, new_type=new_type, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


def _link_args(root: str, target: str, prereqs: str, **kw) -> SimpleNamespace:
    base = dict(registry=root, target=target, prereqs=prereqs, reset=False, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.build._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.build._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.build.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# meta_build_command
# ---------------------------------------------------------------------------


def test_build_calls_docs_rebuild(tmp_path, monkeypatch, capsys):
    root = _make_registry(tmp_path)
    called = []
    monkeypatch.setattr("gaia_cli.commands.dev.build._run_docs_build", lambda *a, **kw: called.append(a))
    meta_build_command(SimpleNamespace(registry=root))
    assert len(called) == 1


# ---------------------------------------------------------------------------
# meta_add_command
# ---------------------------------------------------------------------------


def test_add_creates_skill_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root))
    new_file = Path(root) / "registry" / "nodes" / "basic" / "new-skill.json"
    assert new_file.exists()
    data = json.loads(new_file.read_text(encoding="utf-8"))
    assert data["name"] == "New Skill"


def test_add_short_description_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, description="too short"))
    assert exc.value.code != 0


def test_add_writes_timeline_add_event(tmp_path, monkeypatch):
    """add command calls append_skill_event with 'add' action."""
    root = _make_registry(tmp_path)
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.build.append_skill_event",
        lambda *a, **kw: events.append(a),
    )
    meta_add_command(_add_args(root))
    assert any("add" in str(ev) for ev in events)


def test_add_explicit_id(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root, id="custom-id"))
    assert (Path(root) / "registry" / "nodes" / "basic" / "custom-id.json").exists()


# ---------------------------------------------------------------------------
# meta_remove_command
# ---------------------------------------------------------------------------


def test_remove_deletes_skill_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_remove_command(_rm_args(root))
    assert not (Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json").exists()


def test_remove_missing_skill_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_remove_command(_rm_args(root, skill_id="nonexistent"))
    assert exc.value.code != 0


def test_remove_rejects_named_generic_ref_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    _write_named(Path(root), "alice/my-skill")
    named_file = Path(root) / "registry" / "named" / "alice" / "my-skill.md"
    text = named_file.read_text(encoding="utf-8")
    text = text.replace("genericSkillRef: unknown", "genericSkillRef: existing-skill")
    named_file.write_text(text, encoding="utf-8")
    node_file = Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json"
    before = node_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_remove_command(_rm_args(root))

    assert exc.value.code != 0
    assert node_file.exists()
    assert node_file.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "genericSkillRef" in err


def test_remove_rejects_suite_ref_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    _write_named(Path(root), "alice/my-skill")
    named_file = Path(root) / "registry" / "named" / "alice" / "my-skill.md"
    text = named_file.read_text(encoding="utf-8")
    text = text.replace("title: Epithet\n", "title: Epithet\nsuiteRef: existing-skill\n")
    named_file.write_text(text, encoding="utf-8")
    node_file = Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json"
    before = node_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_remove_command(_rm_args(root))

    assert exc.value.code != 0
    assert node_file.exists()
    assert node_file.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "suiteRef" in err


# ---------------------------------------------------------------------------
# meta_reclassify_command
# ---------------------------------------------------------------------------


def test_reclassify_moves_skill_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_reclassify_command(_reclassify_args(root))
    assert not (Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json").exists()
    assert (Path(root) / "registry" / "nodes" / "fusion" / "existing-skill.json").exists()


def test_reclassify_missing_skill_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_reclassify_command(_reclassify_args(root, skill_id="nonexistent"))
    assert exc.value.code != 0


def test_reclassify_destination_collision_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    dest_dir = Path(root) / "registry" / "nodes" / "fusion"
    dest_dir.mkdir(parents=True)
    dest_file = dest_dir / "existing-skill.json"
    dest_file.write_text('{"id":"stale"}\n', encoding="utf-8")
    source_file = Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json"
    before = source_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_reclassify_command(_reclassify_args(root))

    assert exc.value.code != 0
    assert source_file.read_text(encoding="utf-8") == before
    assert dest_file.read_text(encoding="utf-8") == '{"id":"stale"}\n'
    err = capsys.readouterr().err
    assert "destination file already exists" in err


# ---------------------------------------------------------------------------
# Preflight tests for add and link commands
# ---------------------------------------------------------------------------


def test_add_rejects_duplicate_generic_id(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="existing-skill"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Generic skill 'existing-skill' already exists" in err


def test_add_rejects_invalid_generic_id(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="Invalid_ID"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Generic skill ID 'Invalid_ID' is invalid" in err


def test_add_rejects_duplicate_named_id(tmp_path, capsys):
    root = _make_registry(tmp_path)
    _write_named(Path(root), "alice/my-skill")
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="my-skill", named=True, contributor="alice"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Named skill 'alice/my-skill' already exists" in err


def test_add_rejects_invalid_named_id(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="Invalid_ID", named=True, contributor="alice"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Named skill ID 'alice/Invalid_ID' is invalid" in err


def test_add_rejects_invalid_level(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="my-skill", named=True, level="10★"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Level '10★' is invalid" in err


def test_add_rejects_invalid_status(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="my-skill", named=True, status="invalid-status"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Status 'invalid-status' is invalid for named skill" in err


def test_add_rejects_named_status_missing_title(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="my-skill", named=True, status="named"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "status='named' requires 'title' or 'catalogRef'" in err


def test_add_awakened_named_does_not_require_title_and_writes_status(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root, id="my-skill", named=True, status="awakened"))
    new_file = Path(root) / "registry" / "named" / "gaiabot" / "my-skill.md"
    assert new_file.exists()
    md = new_file.read_text(encoding="utf-8")
    assert "status: awakened" in md
    assert "title:" not in md


def test_add_rejects_nonexistent_generic_ref(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, id="my-skill", named=True, generic_ref="nonexistent-skill", title="Epithet"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Referenced generic skill 'nonexistent-skill' does not exist" in err


def test_add_happy_path_named(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root, id="my-skill", named=True, generic_ref="existing-skill", title="Epithet"))
    assert (Path(root) / "registry" / "named" / "gaiabot" / "my-skill.md").exists()


def test_link_rejects_nonexistent_target(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_link_command(_link_args(root, target="nonexistent-target", prereqs="existing-skill"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Target skill 'nonexistent-target' does not exist" in err


def test_link_rejects_nonexistent_prereq(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_link_command(_link_args(root, target="existing-skill", prereqs="nonexistent-prereq"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Prerequisite skill 'nonexistent-prereq' does not exist" in err


def test_link_rejects_self_link(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_link_command(_link_args(root, target="existing-skill", prereqs="existing-skill"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Cannot link skill 'existing-skill' to itself" in err


def test_link_rejects_duplicate_prereqs_in_list(tmp_path, capsys):
    root = _make_registry(tmp_path)
    # create another skill
    meta_add_command(_add_args(root, name="Other Skill", id="other-skill"))
    with pytest.raises(SystemExit) as exc:
        meta_link_command(_link_args(root, target="existing-skill", prereqs="other-skill,other-skill"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Duplicate prerequisite IDs are not allowed in the link list: other-skill" in err


def test_link_rejects_duplicate_relationship(tmp_path, capsys):
    root = _make_registry(tmp_path)
    # create other skill
    meta_add_command(_add_args(root, name="Other Skill", id="other-skill"))
    # link them once (works)
    meta_link_command(_link_args(root, target="existing-skill", prereqs="other-skill"))

    # try linking again, should reject
    with pytest.raises(SystemExit) as exc:
        meta_link_command(_link_args(root, target="existing-skill", prereqs="other-skill"))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "Relationship already exists" in err


def test_link_rejects_empty_prereq_entry_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root, name="Other Skill", id="other-skill"))
    target_file = Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json"
    before = target_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_link_command(_link_args(root, target="existing-skill", prereqs="other-skill,"))

    assert exc.value.code != 0
    assert target_file.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "Empty prerequisite entries are not allowed" in err


def test_link_happy_path(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root, name="Other Skill", id="other-skill"))
    meta_link_command(_link_args(root, target="existing-skill", prereqs="other-skill"))

    newFile = Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json"
    data = json.loads(newFile.read_text(encoding="utf-8"))
    assert "other-skill" in data["prerequisites"]


def test_link_happy_path_with_reset(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root, name="Other Skill", id="other-skill"))
    meta_add_command(_add_args(root, name="Another Skill", id="another-skill"))

    # link once
    meta_link_command(_link_args(root, target="existing-skill", prereqs="other-skill"))
    # link with reset
    meta_link_command(_link_args(root, target="existing-skill", prereqs="another-skill", reset=True))

    newFile = Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json"
    data = json.loads(newFile.read_text(encoding="utf-8"))
    assert data["prerequisites"] == ["another-skill"]
