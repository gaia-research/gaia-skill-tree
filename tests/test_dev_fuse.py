"""Unit tests for gaia dev fuse — Issue #926."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.fuse import meta_dev_fuse_command

pytestmark = [pytest.mark.integration]


def _write_named(named_dir: Path, slug: str, level: str = "2★", status: str = "named",
                 title: str = "The Test Skill") -> Path:
    contributor, name = slug.split("/", 1)
    d = named_dir / contributor
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.md"
    path.write_text(
        f"---\nid: {slug}\nname: {name}\ncontributor: {contributor}\n"
        f"origin: true\ngenericSkillRef: unknown\nstatus: {status}\n"
        f"level: {level}\ntitle: {title}\n"
        f"description: A named skill for dev-fuse tests.\n---\n",
        encoding="utf-8",
    )
    return path


def _write_generic(nodes_dir: Path, skill_id: str, skill_type: str = "basic") -> Path:
    d = nodes_dir / skill_type
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{skill_id}.json"
    payload = {
        "id": skill_id, "name": skill_id.replace("-", " ").title(),
        "type": skill_type, "description": f"{skill_id} generic description longer than ten chars.",
        "prerequisites": [], "derivatives": [], "evidence": [], "knownAgents": [],
        "status": "provisional", "createdAt": "2026-01-01", "updatedAt": "2026-01-01",
        "version": "0.1.0",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _make_registry(tmp_path: Path) -> str:
    (tmp_path / "registry" / "schema").mkdir(parents=True)
    (tmp_path / "registry" / "schema" / "meta.json").write_text(json.dumps({}))
    (tmp_path / "registry" / "nodes").mkdir(parents=True)
    (tmp_path / "registry" / "named").mkdir(parents=True)
    (tmp_path / "registry" / "suites").mkdir(parents=True)
    return str(tmp_path)


def _args(root: str, generic_id: str, **kw) -> SimpleNamespace:
    base = dict(
        registry=root,
        generic_id=generic_id,
        name=None,
        description=None,
        type=None,
        prereqs=None,
        named_capstone=None,
        suite_components=None,
        no_build=True,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.fuse._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.fuse._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.fuse.append_skill_event", lambda *a, **kw: None)


def test_dev_fuse_creates_generic_node_when_missing(tmp_path):
    root = _make_registry(tmp_path)
    _write_generic(Path(root) / "registry" / "nodes", "prereq-a")
    _write_generic(Path(root) / "registry" / "nodes", "prereq-b")

    meta_dev_fuse_command(_args(
        root, "new-fusion",
        name="New Fusion", description="A new fusion of tricks — over ten chars long.",
        type="ultimate", prereqs="prereq-a,prereq-b",
    ))

    node_path = Path(root) / "registry" / "nodes" / "ultimate" / "new-fusion.json"
    assert node_path.exists()
    data = json.loads(node_path.read_text(encoding="utf-8"))
    assert data["id"] == "new-fusion"
    assert data["type"] == "ultimate"
    assert set(data["prerequisites"]) == {"prereq-a", "prereq-b"}


def test_dev_fuse_updates_existing_generic_node(tmp_path):
    root = _make_registry(tmp_path)
    nodes_dir = Path(root) / "registry" / "nodes"
    _write_generic(nodes_dir, "existing-fusion", skill_type="ultimate")
    _write_generic(nodes_dir, "new-prereq")

    meta_dev_fuse_command(_args(root, "existing-fusion", prereqs="new-prereq"))

    node_path = nodes_dir / "ultimate" / "existing-fusion.json"
    data = json.loads(node_path.read_text(encoding="utf-8"))
    assert "new-prereq" in data["prerequisites"]


def test_dev_fuse_requires_name_when_creating(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit):
        meta_dev_fuse_command(_args(root, "brand-new-fusion"))
    err = capsys.readouterr().err
    assert "--name is required" in err


def test_dev_fuse_writes_suite_manifest_with_capstone(tmp_path):
    root = _make_registry(tmp_path)
    named_dir = Path(root) / "registry" / "named"
    _write_named(named_dir, "acme/apex")
    _write_named(named_dir, "acme/comp1")
    _write_named(named_dir, "acme/comp2")
    nodes_dir = Path(root) / "registry" / "nodes"
    _write_generic(nodes_dir, "apex-fusion", skill_type="ultimate")

    meta_dev_fuse_command(_args(
        root, "apex-fusion",
        named_capstone="acme/apex",
        suite_components="acme/comp1,acme/comp2",
    ))

    manifest = Path(root) / "registry" / "suites" / "acme" / "apex.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["id"] == "acme/apex"
    assert data["capstone"] == "acme/apex"
    assert data["contributor"] == "acme"
    assert set(data["standalones"]) == {"acme/comp1", "acme/comp2"}

    # Capstone frontmatter should have suiteRef and genericSkillRef set.
    from gaia_cli.commands.dev.helpers import _parse_md
    cap_meta, _ = _parse_md(named_dir / "acme" / "apex.md")
    assert cap_meta["genericSkillRef"] == "apex-fusion"
    assert cap_meta["suiteRef"] == "acme/apex"
    assert cap_meta["suiteComponents"] == ["acme/comp1", "acme/comp2"]


def test_dev_fuse_updates_existing_suite_manifest_preserves_subsuites(tmp_path):
    """Existing manifests with structured sub-suites must not be flattened into standalones."""
    root = _make_registry(tmp_path)
    named_dir = Path(root) / "registry" / "named"
    _write_named(named_dir, "acme/apex")
    _write_named(named_dir, "acme/extra")

    # Seed a manifest that already has sub-suites.
    suites_dir = Path(root) / "registry" / "suites" / "acme"
    suites_dir.mkdir(parents=True)
    (suites_dir / "apex.json").write_text(json.dumps({
        "id": "acme/apex", "name": "Apex", "contributor": "acme",
        "capstone": "acme/apex",
        "suites": [{"id": "core", "name": "Core", "members": ["acme/other"]}],
        "standalones": [], "createdAt": "2026-01-01",
    }, indent=2), encoding="utf-8")

    nodes_dir = Path(root) / "registry" / "nodes"
    _write_generic(nodes_dir, "apex-fusion", skill_type="ultimate")

    meta_dev_fuse_command(_args(
        root, "apex-fusion",
        named_capstone="acme/apex",
        suite_components="acme/extra",
    ))

    data = json.loads((suites_dir / "apex.json").read_text(encoding="utf-8"))
    # Sub-suites preserved.
    assert data["suites"][0]["id"] == "core"
    # New component appended to standalones.
    assert "acme/extra" in data["standalones"]


def test_dev_fuse_rejects_unknown_prereq(tmp_path, capsys):
    root = _make_registry(tmp_path)
    _write_generic(Path(root) / "registry" / "nodes", "known-prereq")
    with pytest.raises(SystemExit):
        meta_dev_fuse_command(_args(
            root, "new-fusion",
            name="X", description="Description longer than ten chars.",
            prereqs="known-prereq,unknown-prereq",
        ))
    err = capsys.readouterr().err
    assert "unknown-prereq" in err


def test_dev_fuse_rejects_unknown_named_capstone(tmp_path, capsys):
    root = _make_registry(tmp_path)
    _write_generic(Path(root) / "registry" / "nodes", "apex-fusion", skill_type="ultimate")
    with pytest.raises(SystemExit):
        meta_dev_fuse_command(_args(
            root, "apex-fusion",
            named_capstone="acme/does-not-exist",
        ))
    err = capsys.readouterr().err
    assert "acme/does-not-exist" in err


def test_dev_fuse_rejects_unknown_suite_component(tmp_path, capsys):
    root = _make_registry(tmp_path)
    named_dir = Path(root) / "registry" / "named"
    _write_named(named_dir, "acme/apex")
    _write_generic(Path(root) / "registry" / "nodes", "apex-fusion", skill_type="ultimate")
    with pytest.raises(SystemExit):
        meta_dev_fuse_command(_args(
            root, "apex-fusion",
            named_capstone="acme/apex",
            suite_components="acme/apex,acme/ghost",
        ))
    err = capsys.readouterr().err
    assert "acme/ghost" in err


def test_dev_fuse_rejects_slash_in_generic_id(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit):
        meta_dev_fuse_command(_args(root, "contributor/slug", name="X",
                                    description="Description more than ten chars."))
    err = capsys.readouterr().err
    assert "bare slug" in err or "no '/'" in err
