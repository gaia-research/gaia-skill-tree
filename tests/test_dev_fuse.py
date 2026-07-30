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
        prereqs="prereq-a,prereq-b",
    ))

    # Yggdrasil II: `gaia dev fuse` always creates a fusion node under nodes/fusion/.
    node_path = Path(root) / "registry" / "nodes" / "fusion" / "new-fusion.json"
    assert node_path.exists()
    data = json.loads(node_path.read_text(encoding="utf-8"))
    assert data["id"] == "new-fusion"
    assert data["type"] == "fusion"
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


def test_dev_fuse_timeline_behavior(tmp_path, monkeypatch):
    """Proves legacy `note` timeline events from older `gaia dev fuse` are repaired,

    and asserts newly appended events use `fuse` instead of `note`.
    """
    root = _make_registry(tmp_path)
    nodes_dir = Path(root) / "registry" / "nodes"

    # Setup existing generic node with legacy 'note' timeline events
    skill_id = "existing-fusion"
    d = nodes_dir / "fusion"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{skill_id}.json"

    payload = {
        "id": skill_id,
        "name": "Existing Fusion",
        "type": "fusion",
        "description": "An existing fusion node with some legacy timeline events.",
        "prerequisites": ["prereq-a"],
        "derivatives": [],
        "evidence": [],
        "knownAgents": [],
        "status": "provisional",
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
        "version": "0.1.0",
        "timeline": [
            {
                "timestamp": "2026-01-01T12:00:00Z",
                "action": "note",
                "contributor": "legacy-author",
                "details": "Created generic fusion node 'existing-fusion' via `gaia dev fuse`."
            },
            {
                "timestamp": "2026-01-01T12:05:00Z",
                "action": "note",
                "contributor": "legacy-author",
                "details": "Some unrelated note."
            }
        ]
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Also write prereqs to registry so preflight passes
    _write_generic(nodes_dir, "prereq-a")
    _write_generic(nodes_dir, "prereq-b")

    # Trace the calls made to append_skill_event
    captured_events = []
    def mock_append_skill_event(skill_id_val, action, contributor, details, registry_path=None):
        captured_events.append({
            "skill_id": skill_id_val,
            "action": action,
            "contributor": contributor,
            "details": details,
        })
    monkeypatch.setattr("gaia_cli.commands.dev.fuse.append_skill_event", mock_append_skill_event)

    # Call dev fuse, which adds "prereq-b" to prerequisites
    meta_dev_fuse_command(_args(
        root, skill_id,
        prereqs="prereq-a,prereq-b",
    ))

    # Check that the legacy event was repaired on disk
    data = json.loads(path.read_text(encoding="utf-8"))
    timeline = data.get("timeline", [])
    assert len(timeline) == 2
    # The legacy event via `gaia dev fuse` should be repaired to "fuse"
    assert timeline[0]["action"] == "fuse"
    # The unrelated note should NOT be repaired
    assert timeline[1]["action"] == "note"

    # Check that newly appended events use "fuse" and NOT "note"
    assert len(captured_events) > 0
    fuse_events = [e for e in captured_events if e["action"] == "fuse"]
    note_events = [e for e in captured_events if e["action"] == "note"]

    # Assert newly appended events for fusing use action "fuse", not "note"
    assert len(fuse_events) == 1
    assert len(note_events) == 0
    assert fuse_events[0]["skill_id"] == "existing-fusion"
    assert "prereq-b" in fuse_events[0]["details"]
