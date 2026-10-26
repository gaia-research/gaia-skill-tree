import json
from pathlib import Path

import pytest

from scripts.publication_context import create_context, stamp_outputs, verify_outputs


def test_context_rejects_source_or_symlink_output(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "META.md").write_text("policy", encoding="utf-8")
    with pytest.raises(ValueError, match="disjoint"):
        create_context(source, source / "inside", "2026-10-25T12:00:00Z")
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="symlink"):
        create_context(source, link, "2026-10-25T12:00:00Z")


def test_snapshot_id_binds_inputs_and_pinned_evaluation_time(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    p = source / "META.md"
    p.write_text("policy v1", encoding="utf-8")
    first = create_context(source, tmp_path / "scratch-a", "2026-10-25T12:00:00Z")
    second = create_context(source, tmp_path / "scratch-b", "2026-10-25T12:00:00Z")
    assert first["snapshotId"] == second["snapshotId"]
    assert first["mode"] == "rehearsal" and first["approval"] == "unavailable"
    p.write_text("policy v2", encoding="utf-8")
    changed = create_context(source, tmp_path / "scratch-c", "2026-10-25T12:00:00Z")
    assert changed["snapshotId"] != first["snapshotId"]


def test_output_manifest_detects_partial_and_tampered_replay(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    context = {"mode": "rehearsal", "approval": "unavailable", "snapshotId": "abc",
               "evaluationAtUTC": "2026-10-25T12:00:00Z"}
    with pytest.raises(ValueError, match="incomplete"):
        stamp_outputs(output, context)
    xml = output / "docs" / "fixture.svg"
    xml.parent.mkdir(parents=True, exist_ok=True)
    xml.write_text('<?xml version="1.0"?>\n<svg></svg>\n', encoding="utf-8")
    required = (
        "registry/named-skills.json", "docs/graph/named/index.json",
        "docs/graph/ledger/data.json", "docs/api/v1/skills/index.json",
        "docs/u/index.html", "docs/badges/registry.json",
    )
    for rel in required:
        path = output / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text(json.dumps({"ok": True}), encoding="utf-8")
        else:
            path.write_text("<html>fixture</html>", encoding="utf-8")
    stamp_outputs(output, context)
    assert verify_outputs(output)
    assert xml.read_text(encoding="utf-8").startswith('<?xml version="1.0"?>\n<!-- publication-context:abc')
    (output / required[0]).write_text('{"ok":false}\n', encoding="utf-8")
    assert not verify_outputs(output)
