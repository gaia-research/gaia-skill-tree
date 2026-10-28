"""Synthetic proposal persistence and continuation; no live issues or approvals."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.curation.submission import (
    contentKey, lookupExistingIntake, submissionLock, submitBatch,
)
from gaia_cli.commands.pushFromFile import _load_yaml_file, build_from_file_batch
from gaia_cli.prWriter import build_intake_issue_body


def batch():
    return {"batchId": "original-from-file", "userId": "synthetic", "sourceRepo": "test/repo",
            "proposedSkills": [{"id": "animation-design", "name": "Animation Design", "type": "basic",
                                "prerequisites": [], "description": "Design intentional motion for interfaces.",
                                "evidence": [{"grade": "B", "type": "repo", "url": "https://github.com/test/repo"}]}]}


def fakes(tmp_path):
    calls = {"write": [], "issue": []}
    def write(value, root):
        calls["write"].append(copy.deepcopy(value))
        path = Path(root) / "batch.json"
        path.write_text(json.dumps(value))
        return str(path)
    def issue(*args, **kwargs):
        calls["issue"].append(args)
        return "https://github.com/gaia-research/gaia-skill-tree/issues/99999"
    return calls, write, issue


def test_identical_resubmission_returns_existing_receipt(tmp_path):
    calls, write, issue = fakes(tmp_path)
    first = submitBatch(batch(), tmp_path, writeBatch=write, openIssue=issue)
    modifiedClock = dict(batch(), generatedAt="2099-01-01", batchId="other-clock-from-file")
    second = submitBatch(modifiedClock, tmp_path, writeBatch=write, openIssue=issue)
    assert first == second
    assert len(calls["write"]) == len(calls["issue"]) == 1


def test_payload_change_changes_content_id(tmp_path):
    original = batch()
    changed = copy.deepcopy(original)
    changed["proposedSkills"][0]["description"] += " changed"
    assert contentKey(original) != contentKey(changed)
    now1, errors = build_from_file_batch(original["proposedSkills"], {"gaiaUser": "synthetic"}, str(tmp_path), "test/repo")
    assert not errors
    now2, errors = build_from_file_batch(original["proposedSkills"], {"gaiaUser": "synthetic"}, str(tmp_path), "test/repo")
    assert now1["batchId"] == now2["batchId"]


def test_no_issue_then_submission_reuses_original_batch(tmp_path):
    calls, write, issue = fakes(tmp_path)
    first = submitBatch(batch(), tmp_path, writeBatch=write, openIssue=issue, noIssue=True)
    second = submitBatch(batch(), tmp_path, writeBatch=write, openIssue=issue)
    assert first["batchId"] == second["batchId"]
    assert len(calls["write"]) == len(calls["issue"]) == 1


def test_uncertain_network_window_never_blindly_resubmits(tmp_path):
    calls, write, issue = fakes(tmp_path)
    def failed(*args, **kwargs):
        raise RuntimeError("connection lost after possible creation")
    with pytest.raises(RuntimeError):
        submitBatch(batch(), tmp_path, writeBatch=write, openIssue=failed)
    with pytest.raises(ValueError, match="uncertain"):
        submitBatch(batch(), tmp_path, writeBatch=write, openIssue=issue)
    assert calls["issue"] == []


def test_existing_intake_continuation_preserves_refs_and_handoff(tmp_path):
    calls, write, issue = fakes(tmp_path)
    seen = []
    def lookup(number, value, root):
        seen.append((number, value["batchId"]))
        return "https://github.com/gaia-research/gaia-skill-tree/issues/123"
    receipt = submitBatch(batch(), tmp_path, writeBatch=write, openIssue=issue,
                          existingIntake="123", existingBatchId="old-batch", lookupIssue=lookup)
    assert seen == [("123", "old-batch")]
    assert receipt["batchId"] == "old-batch"
    assert receipt["continued"] is True
    assert receipt["nextPhase"] == "evidence-verification"
    assert calls == {"write": [], "issue": []}


def test_submission_lock_rejects_concurrent_same_content(tmp_path):
    with submissionLock(tmp_path, contentKey(batch())):
        with pytest.raises(ValueError, match="already in progress"):
            with submissionLock(tmp_path, contentKey(batch())):
                pass


def test_existing_intake_checked_not_locally_asserted(tmp_path, monkeypatch):
    value = batch()
    body = build_intake_issue_body(value, repo_root=tmp_path)
    def fakeRun(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({"url": "https://github.com/gaia-research/gaia-skill-tree/issues/123",
            "body": body, "labels": [{"name": "intake"}]}))
    monkeypatch.setattr("gaia_cli.curation.submission.subprocess.run", fakeRun)
    with pytest.raises(ValueError, match="content cannot be verified"):
        lookupExistingIntake("123", value, tmp_path)
    value["submissionKey"] = contentKey(value)
    body = build_intake_issue_body(value, repo_root=tmp_path)
    assert lookupExistingIntake("123", value, tmp_path).endswith("/123")
    body = body.replace("original-from-file", "different-batch")
    with pytest.raises(ValueError, match="exact intake batch"):
        lookupExistingIntake("123", value, tmp_path)


@pytest.mark.parametrize("key", ["humanReview", "l4Resolution", "authorization", "curationHandoff"])
def test_plain_yaml_cannot_impersonate_trusted_l4(tmp_path, key):
    path = tmp_path / "proposal.yml"
    path.write_text(json.dumps({"skills": batch()["proposedSkills"], key: {"status": "approved"}}))
    value, error = _load_yaml_file(path)
    assert value is None and "unreviewed proposal" in error


def test_ordinary_yaml_proposal_remains_available(tmp_path):
    path = tmp_path / "proposal.yml"
    path.write_text(json.dumps({"skills": batch()["proposedSkills"]}))
    value, error = _load_yaml_file(path)
    assert not error and len(value["skills"]) == 1
