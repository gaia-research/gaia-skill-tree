"""Filesystem containment tests for curation intake output writers."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from gaia_cli.push import write_skill_batch


def test_skill_batches_directory_symlink_cannot_escape_registry(tmp_path):
    registry = tmp_path / "registry"
    outside = tmp_path / "outside"
    outside.mkdir()
    batches = registry / "registry-for-review" / "skill-batches"
    batches.parent.mkdir(parents=True)
    batches.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes registry root"):
        write_skill_batch({"batchId": "synthetic-batch"}, registry)

    assert list(outside.iterdir()) == []


def test_skill_batch_leaf_symlink_is_refused(tmp_path):
    registry = tmp_path / "registry"
    batches = registry / "registry-for-review" / "skill-batches"
    batches.mkdir(parents=True)
    outside_file = tmp_path / "outside.json"
    outside_file.write_text('{"sentinel": true}', encoding="utf-8")
    (batches / "synthetic-batch.json").symlink_to(outside_file)

    with pytest.raises(ValueError, match="symlinked batch file"):
        write_skill_batch({"batchId": "synthetic-batch"}, registry)

    assert json.loads(outside_file.read_text(encoding="utf-8")) == {"sentinel": True}


def test_normal_skill_batch_write_stays_inside_registry(tmp_path):
    batch = {"batchId": "synthetic-batch", "proposedSkills": []}

    output = write_skill_batch(batch, tmp_path)

    assert output == str(tmp_path / "registry-for-review" / "skill-batches" / "synthetic-batch.json")
    assert json.loads((tmp_path / "registry-for-review" / "skill-batches" / "synthetic-batch.json").read_text(encoding="utf-8")) == batch
