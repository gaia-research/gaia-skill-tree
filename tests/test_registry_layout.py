import json
from datetime import datetime, timedelta, timezone

import pytest

from gaia_cli.promotion import (
    load_promotion_candidates,
    promote_from_candidates,
    write_promotion_candidates,
)
from gaia_cli.push import write_skill_batch
from gaia_cli.registry import (
    generated_output_dir,
    named_skills_dir,
    registry_for_review_dir,
    registry_graph_path,
    user_tree_path,
)
from gaia_cli.treeManager import load_tree, save_tree


@pytest.mark.smoke
def test_registry_paths_use_new_layout(tmp_path):
    assert registry_graph_path(tmp_path) == str(tmp_path / "registry" / "gaia.json")
    assert named_skills_dir(tmp_path) == str(tmp_path / "registry" / "named")
    assert registry_for_review_dir(tmp_path) == str(tmp_path / "registry-for-review")
    assert generated_output_dir(tmp_path) == str(tmp_path / "generated-output")
    assert user_tree_path(tmp_path, "alice") == str(tmp_path / "skill-trees" / "alice" / "skill-tree.json")


@pytest.mark.smoke
def test_tree_manager_reads_and_writes_skill_trees(tmp_path):
    save_tree("alice", {"userId": "alice", "unlockedSkills": []}, registry_path=str(tmp_path))

    assert (tmp_path / "skill-trees" / "alice" / "skill-tree.json").exists()
    assert not (tmp_path / "users" / "alice" / "skill-tree.json").exists()
    assert load_tree("alice", registry_path=str(tmp_path))["userId"] == "alice"


def test_write_skill_batch_uses_registry_for_review(tmp_path):
    batch = {
        "batchId": "batch-1",
        "userId": "alice",
        "sourceRepo": "alice/repo",
        "generatedAt": "2026-05-01T00:00:00Z",
        "knownSkills": [],
        "proposedSkills": [],
        "similarity": [],
    }

    batch_path = write_skill_batch(batch, str(tmp_path))

    assert batch_path == str(tmp_path / "registry-for-review" / "skill-batches" / "batch-1.json")
    assert json.loads((tmp_path / "registry-for-review" / "skill-batches" / "batch-1.json").read_text()) == batch


def test_promotion_candidates_round_trip(tmp_path):
    candidates = [
        {
            "skillId": "web-search",
            "currentLevel": "2★",
            "suggestedLevel": "3★",
            "evidence": [{"source": "scan"}],
        }
    ]

    path = write_promotion_candidates(str(tmp_path), "alice", candidates)
    loaded = load_promotion_candidates(str(tmp_path), max_age_hours=24)

    assert path == str(tmp_path / "generated-output" / "promotion-candidates.json")
    assert loaded["username"] == "alice"
    assert loaded["candidates"] == candidates


def test_promotion_refuses_missing_or_stale_candidates(tmp_path):
    with pytest.raises(ValueError, match="Run `gaia scan` first"):
        load_promotion_candidates(str(tmp_path), max_age_hours=24)

    out_dir = tmp_path / "generated-output"
    out_dir.mkdir()
    stale = {
        "scannedAt": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat().replace("+00:00", "Z"),
        "username": "alice",
        "candidates": [],
    }
    (out_dir / "promotion-candidates.json").write_text(json.dumps(stale), encoding="utf-8")

    with pytest.raises(ValueError, match="Run `gaia scan` again"):
        load_promotion_candidates(str(tmp_path), max_age_hours=24)


def test_promote_from_candidates_uses_scan_suggested_level(tmp_path):
    save_tree(
        "alice",
        {
            "userId": "alice",
            "updatedAt": "2026-05-01",
            "unlockedSkills": [
                {"skillId": "web-search", "level": "2★", "unlockedAt": "2026-05-01", "unlockedIn": "test"},
                {"skillId": "parse-html", "level": "2★", "unlockedAt": "2026-05-01", "unlockedIn": "test"},
            ],
        },
        registry_path=str(tmp_path),
    )
    write_promotion_candidates(
        str(tmp_path),
        "alice",
        [{"skillId": "web-search", "currentLevel": "2★", "suggestedLevel": "3★", "evidence": []}],
    )

    result = promote_from_candidates("alice", "web-search", str(tmp_path))
    assert result["newLevel"] == "3★"

    with pytest.raises(ValueError, match="Only skills listed as promotion candidates can be promoted"):
        promote_from_candidates("alice", "parse-html", str(tmp_path))
