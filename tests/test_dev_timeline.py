"""Unit tests for gaia dev timeline (#791)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.timeline import meta_timeline_command
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
        "id": "demo-skill",
        "name": "Demo Skill",
        "type": "basic",
        "description": "A demo skill for timeline tests.",
        "evidence": [],
        "timeline": [],
    }
    (nodes / "demo-skill.json").write_text(json.dumps(node, indent=2))
    return str(tmp_path)


def _write_tree(root: str, user: str = "alice") -> None:
    tree_dir = Path(root) / "skill-trees" / user
    tree_dir.mkdir(parents=True, exist_ok=True)
    (tree_dir / "skill-tree.json").write_text(
        json.dumps({"userId": user, "unlockedSkills": [], "timeline": []}),
        encoding="utf-8",
    )


def _args(root: str, skill_id: str = "demo-skill", action: str = "note",
          notes: str = "Test note.", **kw) -> SimpleNamespace:
    base = dict(registry=root, skill_id=skill_id, action=action, notes=notes,
                user=None, timestamp=None, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.timeline._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.timeline._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.timeline.append_skill_event", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.timeline.append_skill_tree_event", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.timeline._named_skill_file", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path — registry node timeline
# ---------------------------------------------------------------------------


def test_timeline_appends_event_to_registry_node(tmp_path, monkeypatch):
    """Without --user, the event goes to the registry node via append_skill_event."""
    root = _make_registry(tmp_path)
    events = []
    monkeypatch.setattr(
        "gaia_cli.timeline.append_skill_event",
        lambda *a, **kw: events.append({"a": a, "kw": kw}),
    )
    meta_timeline_command(_args(root))
    assert len(events) == 1
    assert events[0]["a"][1] == "note"


def test_timeline_capsys_shows_completion(tmp_path, capsys):
    root = _make_registry(tmp_path)
    meta_timeline_command(_args(root))
    # No crash, build skipped message printed (autouse patches append_skill_event)
    out = capsys.readouterr().out
    assert "Skipping" in out or "Appended" in out or out == ""


# ---------------------------------------------------------------------------
# User tree routing
# ---------------------------------------------------------------------------


def test_timeline_with_user_routes_to_tree(tmp_path, monkeypatch):
    """With --user, event is routed to the user skill-tree."""
    root = _make_registry(tmp_path)
    _write_tree(root, "alice")
    tree_events = []
    monkeypatch.setattr(
        "gaia_cli.timeline.append_skill_tree_event",
        lambda *a, **kw: tree_events.append(a),
    )
    # _named_skill_file must return None so user-tree path is taken
    monkeypatch.setattr(
        "gaia_cli.timeline._named_skill_file",
        lambda *a, **kw: None,
    )
    monkeypatch.setattr("gaia_cli.timeline.append_skill_event", lambda *a, **kw: None)
    meta_timeline_command(_args(root, user="alice"))
    assert len(tree_events) == 1
    assert tree_events[0][0] == "alice"


# ---------------------------------------------------------------------------
# Timestamp forwarding
# ---------------------------------------------------------------------------


def test_timestamp_forwarded_to_tree_event(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    _write_tree(root, "alice")
    timestamps = []
    monkeypatch.setattr(
        "gaia_cli.timeline.append_skill_tree_event",
        lambda *a, **kw: timestamps.append(kw.get("timestamp")),
    )
    monkeypatch.setattr(
        "gaia_cli.timeline._named_skill_file", lambda *a, **kw: None
    )
    monkeypatch.setattr("gaia_cli.timeline.append_skill_event", lambda *a, **kw: None)
    meta_timeline_command(_args(root, user="alice", timestamp="2026-01-01T00:00:00Z"))
    assert timestamps[0] == "2026-01-01T00:00:00Z"


def test_invalid_timestamp_exits_before_tree_write(tmp_path, monkeypatch, capsys):
    root = _make_registry(tmp_path)
    _write_tree(root, "alice")
    tree_events = []
    monkeypatch.setattr(
        "gaia_cli.timeline.append_skill_tree_event",
        lambda *a, **kw: tree_events.append(a),
    )

    with pytest.raises(SystemExit) as exc:
        meta_timeline_command(_args(root, user="alice", timestamp="not-a-date"))

    assert exc.value.code != 0
    assert tree_events == []
    assert "--timestamp must be ISO 8601" in capsys.readouterr().err


def test_timestamp_without_user_rejected_before_registry_write(tmp_path, monkeypatch, capsys):
    root = _make_registry(tmp_path)
    events = []
    monkeypatch.setattr(
        "gaia_cli.timeline.append_skill_event",
        lambda *a, **kw: events.append(a),
    )

    with pytest.raises(SystemExit) as exc:
        meta_timeline_command(_args(root, timestamp="2026-01-01T00:00:00Z"))

    assert exc.value.code != 0
    assert events == []
    assert "--timestamp is only supported with --user" in capsys.readouterr().err


def test_missing_user_tree_rejected_before_write(tmp_path, monkeypatch, capsys):
    root = _make_registry(tmp_path)
    tree_events = []
    monkeypatch.setattr(
        "gaia_cli.timeline.append_skill_tree_event",
        lambda *a, **kw: tree_events.append(a),
    )

    with pytest.raises(SystemExit) as exc:
        meta_timeline_command(_args(root, user="missing"))

    assert exc.value.code != 0
    assert tree_events == []
    assert "skill-trees/missing/skill-tree.json does not exist" in capsys.readouterr().err
