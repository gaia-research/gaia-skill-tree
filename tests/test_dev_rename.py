"""Unit tests for gaia dev rename (#791)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.rename import meta_rename_command
pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(nodes_dir: Path, skill_id: str) -> None:
    nodes_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "id": skill_id,
        "name": skill_id.replace("-", " ").title(),
        "type": "basic",
        "level": "1★",
        "description": f"Description of {skill_id}.",
        "status": "provisional",
        "prerequisites": [],
        "derivatives": [],
        "evidence": [],
        "timeline": [],
        "createdAt": "2026-06-01",
        "updatedAt": "2026-06-01",
        "version": "0.1.0",
    }
    (nodes_dir / f"{skill_id}.json").write_text(json.dumps(data, indent=2))


def _make_registry(tmp_path: Path) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    _write_skill(nodes, "skill-old")
    _write_skill(nodes, "skill-existing")
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    return str(tmp_path)


def _args(root: str, old_id: str = "skill-old", new_id: str = "skill-new",
          **kw) -> SimpleNamespace:
    base = dict(registry=root, old_id=old_id, new_id=new_id, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.rename._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.rename._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.rename.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_rename_creates_new_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_rename_command(_args(root))
    new_file = Path(root) / "registry" / "nodes" / "basic" / "skill-new.json"
    assert new_file.exists()
    with open(new_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data["id"] == "skill-new"


def test_rename_removes_old_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_rename_command(_args(root))
    old_file = Path(root) / "registry" / "nodes" / "basic" / "skill-old.json"
    assert not old_file.exists()


# ---------------------------------------------------------------------------
# Rejection paths
# ---------------------------------------------------------------------------


def test_rename_missing_old_id_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_rename_command(_args(root, old_id="does-not-exist"))
    assert exc.value.code != 0


def test_rename_to_existing_id_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_rename_command(_args(root, new_id="skill-existing"))
    assert exc.value.code != 0


def test_rename_to_self_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    old_file = Path(root) / "registry" / "nodes" / "basic" / "skill-old.json"
    before = old_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_rename_command(_args(root, new_id="skill-old"))

    assert exc.value.code != 0
    assert old_file.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "Cannot rename skill 'skill-old' to itself" in err


def test_rename_invalid_new_id_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    old_file = Path(root) / "registry" / "nodes" / "basic" / "skill-old.json"
    before = old_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_rename_command(_args(root, new_id="Invalid_ID"))

    assert exc.value.code != 0
    assert old_file.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "New skill ID 'Invalid_ID' is invalid" in err


# ---------------------------------------------------------------------------
# Reference surfaces (#1456)
# ---------------------------------------------------------------------------


def _write_named(named_dir: Path, skill_id: str, body: str = "\nBody.\n") -> Path:
    contributor, slug = skill_id.split("/", 1)
    path = named_dir / contributor / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: {skill_id}\n"
        f"name: {slug.replace('-', ' ').title()}\n"
        "status: named\n"
        "---" + body,
        encoding="utf-8",
    )
    return path


def _named_registry(tmp_path: Path) -> Path:
    """Registry with one named skill plus the schema dir the preflight needs."""
    named_dir = tmp_path / "registry" / "named"
    _write_named(named_dir, "acme/old-slug")
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True, exist_ok=True)
    (schema / "meta.json").write_text(json.dumps({}))
    return named_dir


def test_rename_updates_nested_suite_members(tmp_path):
    """suites[].members[] is the surface PR #1452 had to patch by hand."""
    _named_registry(tmp_path)
    suite_path = tmp_path / "registry" / "suites" / "acme" / "bundle.json"
    suite_path.parent.mkdir(parents=True, exist_ok=True)
    suite_path.write_text(json.dumps({
        "id": "acme/bundle",
        "name": "Acme Bundle",
        "contributor": "acme",
        "capstone": "acme/bundle",
        "suites": [
            {
                "id": "core",
                "name": "Core Suite",
                "fusion": "acme/old-slug",
                "members": ["acme/old-slug", "acme/untouched"],
            }
        ],
        "standalones": ["acme/old-slug"],
        "createdAt": "2026-06-01",
    }, indent=2), encoding="utf-8")

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    data = json.loads(suite_path.read_text(encoding="utf-8"))
    assert data["suites"][0]["members"] == ["acme/new-slug", "acme/untouched"]
    assert data["suites"][0]["fusion"] == "acme/new-slug"
    assert data["standalones"] == ["acme/new-slug"]


def test_rename_moves_suite_manifest_when_capstone_renamed(tmp_path):
    _named_registry(tmp_path)
    suites_dir = tmp_path / "registry" / "suites" / "acme"
    suites_dir.mkdir(parents=True, exist_ok=True)
    (suites_dir / "old-slug.json").write_text(json.dumps({
        "id": "acme/old-slug",
        "name": "Acme Suite",
        "contributor": "acme",
        "capstone": "acme/old-slug",
        "suites": [{"id": "core", "name": "Core", "members": ["acme/other"]}],
        "createdAt": "2026-06-01",
    }, indent=2), encoding="utf-8")

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    assert not (suites_dir / "old-slug.json").exists()
    moved = json.loads((suites_dir / "new-slug.json").read_text(encoding="utf-8"))
    assert moved["id"] == "acme/new-slug"
    assert moved["capstone"] == "acme/new-slug"


def _write_tree(tmp_path: Path, username: str, skill_id: str) -> Path:
    tree_path = tmp_path / "skill-trees" / username / "skill-tree.json"
    tree_path.parent.mkdir(parents=True, exist_ok=True)
    tree_path.write_text(json.dumps({
        "userId": username,
        "updatedAt": "2026-06-01",
        "unlockedSkills": [
            {
                "skillId": skill_id,
                "level": "2★",
                "unlockedAt": "2026-06-01T00:00:00Z",
                "unlockedIn": f"{username}/repo",
                "combinedFrom": [skill_id, "acme/other"],
            }
        ],
        "timeline": [
            {
                "timestamp": "2026-06-01T00:00:00Z",
                "action": "register",
                "skillId": skill_id,
                "details": f"Registered named skill {skill_id}",
            }
        ],
        "stats": {"totalUnlocked": 1},
        "pendingCombinations": [],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return tree_path


def test_rename_updates_user_tree_references(tmp_path):
    _named_registry(tmp_path)
    tree_path = _write_tree(tmp_path, "someuser", "acme/old-slug")

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    assert tree["unlockedSkills"][0]["skillId"] == "acme/new-slug"
    assert tree["unlockedSkills"][0]["combinedFrom"] == ["acme/new-slug", "acme/other"]
    assert tree["timeline"][0]["skillId"] == "acme/new-slug"
    assert tree["timeline"][0]["details"] == "Registered named skill acme/new-slug"


def test_rename_does_not_fabricate_user_tree_timeline_event(tmp_path):
    """skillTree.schema.json's action enum has no `rename` — invent nothing."""
    _named_registry(tmp_path)
    tree_path = _write_tree(tmp_path, "someuser", "acme/old-slug")

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    assert len(tree["timeline"]) == 1
    assert [e["action"] for e in tree["timeline"]] == ["register"]


def test_rename_rewrites_prose_but_not_changelog(tmp_path):
    named_dir = tmp_path / "registry" / "named"
    _write_named(named_dir, "acme/old-slug", body=(
        "\n## Installation\n\n"
        "`gaia skills install acme/old-slug`\n\n"
        "## Evolution Changelog\n\n"
        "- 1.0.0 — shipped as acme/old-slug\n"
    ))
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True, exist_ok=True)
    (schema / "meta.json").write_text(json.dumps({}))

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    text = (named_dir / "acme" / "new-slug.md").read_text(encoding="utf-8")
    assert "gaia skills install acme/new-slug" in text
    assert "shipped as acme/old-slug" in text


def test_rename_no_prose_flag_leaves_prose_alone(tmp_path):
    named_dir = tmp_path / "registry" / "named"
    _write_named(named_dir, "acme/old-slug", body="\n`gaia skills install acme/old-slug`\n")
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True, exist_ok=True)
    (schema / "meta.json").write_text(json.dumps({}))

    meta_rename_command(_args(
        str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug", no_prose=True,
    ))

    text = (named_dir / "acme" / "new-slug.md").read_text(encoding="utf-8")
    assert "gaia skills install acme/old-slug" in text


def test_stale_reference_report_flags_leftover_reference(tmp_path, capsys):
    """A reference the rename intentionally does not rewrite must be reported."""
    _named_registry(tmp_path)
    (tmp_path / "docs" / "js").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "js" / "skill-explorer.js").write_text(
        "const FEATURED = ['acme/old-slug'];\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        "Install with `gaia skills install acme/old-slug`.\n", encoding="utf-8"
    )

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    out = capsys.readouterr().out
    assert "Stale-reference report for 'acme/old-slug'" in out
    assert "docs/js/skill-explorer.js:1" in out
    assert "README.md:1" in out


def test_stale_reference_report_clean_when_nothing_left(tmp_path, capsys):
    _named_registry(tmp_path)
    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))
    out = capsys.readouterr().out
    assert "clean — no remaining references" in out


def test_stale_report_ignores_generated_artifacts(tmp_path, capsys):
    """docs/graph/* is regenerated by `gaia dev docs`, not hand-edited."""
    _named_registry(tmp_path)
    (tmp_path / "docs" / "graph").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "graph" / "gaia.json").write_text(
        json.dumps({"skills": [{"id": "acme/old-slug"}]}), encoding="utf-8"
    )

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    out = capsys.readouterr().out
    assert "clean — no remaining references" in out
    assert "Out of scope (regenerated, not hand-edited)" in out


def test_rename_matching_is_token_bounded(tmp_path, capsys):
    """`acme/old-slug` must not match `acme/old-slug-extended`."""
    _named_registry(tmp_path)
    (tmp_path / "README.md").write_text("acme/old-slug-extended is unrelated.\n", encoding="utf-8")

    meta_rename_command(_args(str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug"))

    out = capsys.readouterr().out
    assert "clean — no remaining references" in out
    assert "acme/old-slug-extended" in (tmp_path / "README.md").read_text(encoding="utf-8")


def test_skip_ref_scan_suppresses_report(tmp_path, capsys):
    _named_registry(tmp_path)
    (tmp_path / "README.md").write_text("acme/old-slug\n", encoding="utf-8")

    meta_rename_command(_args(
        str(tmp_path), old_id="acme/old-slug", new_id="acme/new-slug", skip_ref_scan=True,
    ))

    out = capsys.readouterr().out
    assert "Stale-reference report" not in out


def test_generic_rename_updates_user_tree_and_reports(tmp_path, capsys):
    root = _make_registry(tmp_path)
    tree_path = _write_tree(tmp_path, "someuser", "skill-old")

    meta_rename_command(_args(root))

    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    assert tree["unlockedSkills"][0]["skillId"] == "skill-new"
    assert tree["timeline"][0]["skillId"] == "skill-new"
    assert "Stale-reference report for 'skill-old'" in capsys.readouterr().out
