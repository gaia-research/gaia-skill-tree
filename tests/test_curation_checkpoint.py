"""Resumed-curation checkpoint and claim-status export (#2052 items 6–7), synthetic only."""

from __future__ import annotations

from gaia_cli.curationCheckpoint import activeBlockers, compactCheckpoint, exportClaims

CHECKPOINT = {
    "sourceRevisions": {"gaia-skill-tree": "f00b3606b", "example/tool": "abc1234"},
    "blockers": [
        {"checkId": "worktree-recovery", "status": "resolved",
         "resolutionEvidence": "worktree re-created; `git worktree list` clean at f00b3606b"},
        {"checkId": "batch-3-ingest", "status": "resolved",
         "resolutionEvidence": "re-ran ingest; validate exit 0"},
        {"checkId": "stale-claim", "status": "resolved"},
        {"checkId": "missing-blob-link", "status": "open", "summary": "links.github is a tree/ URL"},
    ],
}


def statuses(entries):
    return {e["checkId"]: e["currentStatus"] for e in entries}


def test_resolved_history_does_not_reappear_without_fresh_failure():
    current = activeBlockers(CHECKPOINT)
    assert statuses(current) == {
        "stale-claim": "unproven-resolution",
        "missing-blob-link": "open",
    }


def test_fresh_failing_check_regresses_a_resolved_blocker():
    fresh = [{"checkId": "batch-3-ingest", "evidence": "validate exit 1 at abc1234"}]
    current = activeBlockers(CHECKPOINT, fresh)
    assert statuses(current)["batch-3-ingest"] == "regressed"
    regressed = next(e for e in current if e["checkId"] == "batch-3-ingest")
    assert regressed["freshEvidence"] == "validate exit 1 at abc1234"
    assert "worktree-recovery" not in statuses(current)


def test_unknown_fresh_failure_is_reported_as_new():
    current = activeBlockers(CHECKPOINT, [{"checkId": "schema-drift", "evidence": "rc=1"}])
    assert statuses(current)["schema-drift"] == "new"


def test_compact_checkpoint_is_current_state_only():
    compact = compactCheckpoint(CHECKPOINT)
    assert [b["checkId"] for b in compact["resolvedBlockers"]] == ["worktree-recovery", "batch-3-ingest"]
    assert statuses(compact["activeBlockers"]) == {
        "stale-claim": "unproven-resolution",
        "missing-blob-link": "open",
    }
    assert compact["sourceRevisions"] == CHECKPOINT["sourceRevisions"]
    # Idempotent: compacting twice from the same inputs is stable.
    assert compactCheckpoint(CHECKPOINT) == compact


def test_unsupported_verified_claim_cannot_export_as_verified():
    exported = exportClaims([
        {"metric": "stars", "value": 1000, "status": "verified", "repro": "gh repo view x"},
        {"metric": "commits", "value": 816, "status": "verified", "source": "README badge"},
        {"metric": "views", "value": 5000, "status": "verified"},
        {"metric": "repo-own.commits", "value": 816, "status": "inferred"},
        {"metric": "citations", "value": 12, "status": "probably"},
    ])
    byMetric = {c["metric"]: c for c in exported}
    assert byMetric["stars"]["status"] == "verified"
    assert byMetric["commits"]["status"] == "reported"
    assert byMetric["commits"]["downgradedFrom"] == "verified"
    assert byMetric["views"]["status"] == "unknown"
    assert byMetric["repo-own.commits"]["status"] == "unknown"
    assert byMetric["citations"]["status"] == "unknown"
