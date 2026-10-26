import json
from pathlib import Path

import pytest

from scripts.publication_context import (
    GENERATED_OUTPUTS, compare_ledger_api, create_context, stamp_outputs, verify_copied_inputs,
    verify_outputs,
)

UTC = "2026-10-25T12:00:00Z"


def _outputs(root: Path):
    for rel in GENERATED_OUTPUTS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n" if path.suffix == ".json" else "<html></html>\n", encoding="utf-8")


def _context(tmp_path):
    source = tmp_path / "context-source"
    source.mkdir(exist_ok=True)
    (source / "input.json").write_text('{"fixed":true}', encoding="utf-8")
    return create_context(source, tmp_path / "context-output", UTC)


def _stages():
    return {name: {"status": "success", "outputs": ["docs/api/v1/skills/index.json"]}
            for name in ("assembly", "named-index", "trust-ledger", "api-projection", "profiles", "badges", "graph-assets")}


def test_context_binds_dirty_and_untracked_copied_bytes(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    omitted = source / "skill-trees" / "untracked" / "skill-tree.json"
    omitted.parent.mkdir(parents=True)
    omitted.write_text('{"level":1}', encoding="utf-8")
    first = create_context(source, tmp_path / "out1", UTC)
    copied = tmp_path / "copy"
    copied.mkdir()
    (copied / "skill-trees").mkdir()
    assert first["snapshotId"]
    omitted.write_text('{"level":2}', encoding="utf-8")
    second = create_context(source, tmp_path / "out2", UTC)
    assert second["snapshotId"] != first["snapshotId"]
    with pytest.raises(ValueError, match="differs"):
        verify_copied_inputs(copied, second)


def test_context_rejects_overlap_symlink_and_foreign_worktree(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError, match="disjoint"):
        create_context(source, source / "inside", UTC)
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        create_context(source, link / "child", UTC)
    # All active worktrees reported by git are protected, not only source_root.
    repo = Path(__file__).resolve().parents[1]
    foreign = next((Path(line[9:]) for line in __import__("subprocess").run(
        ["git", "worktree", "list", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout.splitlines() if line.startswith("worktree ") and Path(line[9:]).resolve() != repo.resolve()), None)
    if foreign:
        with pytest.raises(ValueError, match="every repository worktree"):
            create_context(repo, foreign / "publication-fixture", UTC)


def test_stamping_is_external_and_rejects_skipped_generators(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    source_like = output / "registry" / "nodes" / "fixture.json"
    source_like.parent.mkdir(parents=True)
    source_like.write_text('{"input":true}\n', encoding="utf-8")
    before = source_like.read_bytes()
    context = _context(tmp_path)
    _outputs(output)
    failed = _stages()
    failed["badges"]["status"] = "skipped"
    with pytest.raises(ValueError, match="success"):
        stamp_outputs(output, context, failed)
    stamp_outputs(output, context, _stages())
    assert source_like.read_bytes() == before
    assert verify_outputs(output)
    (output / "publication-context.json").write_text('{"mode":"production"}', encoding="utf-8")
    assert not verify_outputs(output)


def test_manifest_detects_stale_artifact_and_context_mix(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    context = _context(tmp_path)
    _outputs(output)
    stamp_outputs(output, context, _stages())
    assert verify_outputs(output)
    (output / GENERATED_OUTPUTS[0]).write_text('{"stale":true}', encoding="utf-8")
    assert not verify_outputs(output)


def test_semantic_comparator_rejects_star_and_tm_mismatch():
    ledger = {"rows": [{"skillId": "author/skill", "currentStars": "4★", "tm": 90.0}]}
    api = {"skills": [{"id": "author/skill", "level": "3★", "trustMagnitude": 89.5}]}
    assert compare_ledger_api(ledger, api) == [
        "author/skill: canonical stars differ", "author/skill: TM differs"
    ]


def test_replay_context_is_deterministic_at_pinned_time(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "input.json").write_text('{"x":1}', encoding="utf-8")
    a = create_context(source, tmp_path / "a", UTC)
    b = create_context(source, tmp_path / "b", UTC)
    assert a["snapshotId"] == b["snapshotId"]
    assert a["evaluationAtUTC"] == b["evaluationAtUTC"] == UTC
