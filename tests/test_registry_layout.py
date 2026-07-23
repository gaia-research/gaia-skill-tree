import json

import pytest

pytestmark = [pytest.mark.integration]

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

