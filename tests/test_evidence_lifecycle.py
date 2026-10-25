"""Focused tests for Yggdrasil IV Evidence Lifecycle, Identity, Rehearsal, and Rollback.

Validates RFC #2148 §§3, 4, 7, 10 P3 preparation:
- Idempotency of migration rehearsal.
- Row reordering and stable evidence identity.
- Ambiguous collision detection and failure.
- Retained revision history and active-row filtering.
- Assertion state transitions and cycle rejection.
- Stale approval rejection (digest binding).
- Exact rollback proof (byte-for-byte / value-for-value restoration).
- Schema parity across canonical, bundled, and docs mirrors.
- Score neutrality across legacy and migrated representations.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import jsonschema
import pytest

from gaia_cli.evidenceLifecycle import (
    ASSERTION_ACTIVE,
    ASSERTION_REVOKED,
    ASSERTION_SUPERSEDED,
    ASSERTION_SUSPENDED,
    METRIC_REPORTED,
    METRIC_VERIFIED,
    AmbiguousCollisionError,
    ApprovalTransition,
    DigestMismatchError,
    EvidenceValidationError,
    InvalidTransitionError,
    MalformedRevisionCycleError,
    StaleApprovalError,
    active_evidence_rows,
    apply_rollback,
    compute_payload_digest,
    derive_evidence_identity,
    refresh_metric_assertion,
    rehearse_legacy_migration,
    transition_assertion_state,
    validate_evidence_payload,
    validate_revision_history,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_legacy_skill():
    return {
        "id": "agent-skills",
        "name": "Agent Skills",
        "type": "basic",
        "description": "Curated skills for autonomous agents.",
        "prerequisites": [],
        "derivatives": [],
        "knownAgents": ["claude"],
        "status": "validated",
        "createdAt": "2026-07-03",
        "updatedAt": "2026-10-01",
        "version": "1.0.0",
        "evidence": [
            {
                "source": "https://github.com/addyosmani/agent-skills/stargazers",
                "evaluator": "mbtiongson1",
                "date": "2026-07-03",
                "type": "github-stars-own",
                "stars": 1000,
                "skillCountInRepo": 1,
            },
            {
                "source": "https://github.com/addyosmani/agent-skills",
                "evaluator": "mbtiongson1",
                "date": "2026-07-03",
                "type": "repo-own",
                "commits": 260,
                "contributors": 36,
            },
        ],
    }


# ---------------------------------------------------------------------------
# 1. Identity & Row Reordering
# ---------------------------------------------------------------------------

def test_evidence_identity_is_stable_across_row_reordering(sample_legacy_skill):
    """evidenceId derivation is independent of row index in the evidence array."""
    rows = sample_legacy_skill["evidence"]
    id_0_orig = derive_evidence_identity(sample_legacy_skill["id"], rows[0])
    id_1_orig = derive_evidence_identity(sample_legacy_skill["id"], rows[1])

    # Reorder rows
    reordered_rows = [rows[1], rows[0]]
    id_0_reordered = derive_evidence_identity(sample_legacy_skill["id"], reordered_rows[1])
    id_1_reordered = derive_evidence_identity(sample_legacy_skill["id"], reordered_rows[0])

    assert id_0_orig == id_0_reordered
    assert id_1_orig == id_1_reordered
    assert id_0_orig != id_1_orig


def test_cross_type_same_url_rows_have_distinct_identities():
    """Different evidence types pointing at the same URL receive distinct evidenceIds."""
    skill_id = "test/skill"
    row_stars = {"type": "github-stars-own", "source": "https://github.com/org/repo", "stars": 500, "evaluator": "ev", "date": "2026-01-01"}
    row_repo = {"type": "repo-own", "source": "https://github.com/org/repo", "commits": 100, "contributors": 2, "evaluator": "ev", "date": "2026-01-01"}

    id_stars = derive_evidence_identity(skill_id, row_stars)
    id_repo = derive_evidence_identity(skill_id, row_repo)

    assert id_stars != id_repo
    assert "github-stars-own" in id_stars
    assert "repo-own" in id_repo


# ---------------------------------------------------------------------------
# 2. Ambiguous Collision Detection
# ---------------------------------------------------------------------------

def test_ambiguous_duplicate_legacy_collision_fails():
    """Duplicate legacy rows with identical (type, source) within a skill raise AmbiguousCollisionError."""
    skill = {
        "id": "basic/ci-churn-analysis",
        "evidence": [
            {
                "source": "https://arxiv.org/abs/2602.02307",
                "evaluator": "unknown",
                "date": "2026-07-08",
                "type": "arxiv",
                "citations": 0,
            },
            {
                "source": "https://arxiv.org/abs/2602.02307",
                "evaluator": "unknown",
                "date": "2026-07-08",
                "type": "arxiv",
                "citations": 0,
            },
        ],
    }
    with pytest.raises(AmbiguousCollisionError, match="ambiguous duplicate legacy collision"):
        rehearse_legacy_migration(skill)


def test_duplicate_explicit_evidence_id_fails():
    """Duplicate explicit evidenceId across rows raises AmbiguousCollisionError."""
    skill = {
        "id": "basic/test",
        "evidence": [
            {
                "evidenceId": "ev-test-1",
                "source": "https://arxiv.org/abs/1",
                "evaluator": "unknown",
                "date": "2026-07-08",
                "type": "arxiv",
            },
            {
                "evidenceId": "ev-test-1",
                "source": "https://arxiv.org/abs/2",
                "evaluator": "unknown",
                "date": "2026-07-08",
                "type": "arxiv",
            },
        ],
    }
    with pytest.raises(AmbiguousCollisionError, match="ambiguous duplicate evidenceId"):
        rehearse_legacy_migration(skill)


# ---------------------------------------------------------------------------
# 3. Deterministic Migration Rehearsal & Score Neutrality
# ---------------------------------------------------------------------------

def test_migration_rehearsal_is_score_neutral(sample_legacy_skill):
    """In-memory legacy migration rehearsal preserves TM score exactly."""
    result = rehearse_legacy_migration(sample_legacy_skill, decision_ref="migration:yggdrasil-iv@test")

    assert result.score_neutral is True
    assert result.before_score == result.after_score
    assert result.migrated_row_count == 2
    assert result.before_digest != result.after_digest

    # Verify all after rows have active assertionState, revision 1, non-blank evidenceId
    for row in result.after_payload["evidence"]:
        assert row["assertionState"] == ASSERTION_ACTIVE
        assert row["revision"] == 1
        assert row["decisionRef"] == "migration:yggdrasil-iv@test"
        assert row["evidenceId"].startswith("ev-")
        assert row["metricMethod"] == METRIC_REPORTED


def test_migration_rehearsal_idempotency(sample_legacy_skill):
    """Running migration rehearsal on already-migrated skill is a no-op."""
    first_result = rehearse_legacy_migration(sample_legacy_skill)
    second_result = rehearse_legacy_migration(first_result.after_payload)

    assert second_result.migrated_row_count == 0
    assert second_result.before_digest == second_result.after_digest
    assert second_result.score_neutral is True


# ---------------------------------------------------------------------------
# 4. Exact In-Memory Rollback Proof
# ---------------------------------------------------------------------------

def test_exact_rollback_proof(sample_legacy_skill):
    """Applying rollback payload exactly restores pre-migration state byte-for-byte."""
    result = rehearse_legacy_migration(sample_legacy_skill)

    restored = apply_rollback(result.after_payload, result.rollback_payload)
    restored_digest = compute_payload_digest(restored)

    assert restored_digest == result.before_digest
    assert restored == sample_legacy_skill


# ---------------------------------------------------------------------------
# 5. Metric Refresh & Retained History
# ---------------------------------------------------------------------------

def test_metric_refresh_creates_successor_revision_and_retains_history(sample_legacy_skill):
    """Metric refresh increments revision, supersedes previous, and retains old row in history."""
    rehearsal = rehearse_legacy_migration(sample_legacy_skill)
    migrated_skill = rehearsal.after_payload

    # Active row for stars
    active_stars_row = migrated_skill["evidence"][0]
    eid = active_stars_row["evidenceId"]
    old_digest = compute_payload_digest(active_stars_row)

    # Compute expected new row to obtain reviewedNewDigest
    expected_new_row = dict(active_stars_row)
    expected_new_row["stars"] = 1500
    expected_new_row["revision"] = 2
    expected_new_row["supersedes"] = 1
    expected_new_row["decisionRef"] = "decision:refresh-stars-pr#99"
    expected_new_row["reviewedOldDigest"] = old_digest
    expected_new_digest = compute_payload_digest(expected_new_row)

    approval = ApprovalTransition(
        decision_ref="decision:refresh-stars-pr#99",
        reviewed_old_digest=old_digest,
        reviewed_new_digest=expected_new_digest,
        actor="curator",
    )

    updated_skill, new_row = refresh_metric_assertion(
        migrated_skill,
        eid,
        {"stars": 1500},
        approval,
    )

    assert new_row["evidenceId"] == eid
    assert new_row["revision"] == 2
    assert new_row["supersedes"] == 1
    assert new_row["assertionState"] == ASSERTION_ACTIVE
    assert new_row["stars"] == 1500

    # Total rows in updated skill should now be 3 (retained history!)
    all_rows = updated_skill["evidence"]
    assert len(all_rows) == 3

    # Check superseded row is still present
    superseded_rows = [r for r in all_rows if r.get("assertionState") == ASSERTION_SUPERSEDED]
    assert len(superseded_rows) == 1
    assert superseded_rows[0]["evidenceId"] == eid
    assert superseded_rows[0]["revision"] == 1

    # Active evidence rows filter excludes the superseded row
    active_rows = active_evidence_rows(updated_skill)
    assert len(active_rows) == 2
    assert any(r["evidenceId"] == eid and r["revision"] == 2 for r in active_rows)
    assert not any(r["evidenceId"] == eid and r["revision"] == 1 for r in active_rows)


# ---------------------------------------------------------------------------
# 6. Assertion State Transitions & Cycle Rejection
# ---------------------------------------------------------------------------

def test_assertion_transitions_active_suspended_revoked():
    """Assertion state machine permits valid transitions and rejects invalid ones."""
    row = {
        "evidenceId": "ev-test-1",
        "revision": 1,
        "assertionState": ASSERTION_ACTIVE,
        "decisionRef": "decision:initial",
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1234.5678",
        "evaluator": "mbtiongson1",
        "date": "2026-01-01",
        "citations": 10,
    }
    old_digest = compute_payload_digest(row)

    # 1. active -> suspended
    temp_suspended = dict(row)
    temp_suspended["assertionState"] = ASSERTION_SUSPENDED
    temp_suspended["decisionRef"] = "decision:suspend-1"
    temp_suspended["reviewedOldDigest"] = old_digest
    new_dig = compute_payload_digest(temp_suspended)

    approval = ApprovalTransition(
        decision_ref="decision:suspend-1",
        reviewed_old_digest=old_digest,
        reviewed_new_digest=new_dig,
    )
    suspended_row = transition_assertion_state(row, ASSERTION_SUSPENDED, approval)
    assert suspended_row["assertionState"] == ASSERTION_SUSPENDED

    # 2. suspended -> revoked
    old_susp_digest = compute_payload_digest(suspended_row)
    temp_revoked = dict(suspended_row)
    temp_revoked["assertionState"] = ASSERTION_REVOKED
    temp_revoked["decisionRef"] = "decision:revoke-1"
    temp_revoked["reviewedOldDigest"] = old_susp_digest
    new_rev_dig = compute_payload_digest(temp_revoked)

    rev_approval = ApprovalTransition(
        decision_ref="decision:revoke-1",
        reviewed_old_digest=old_susp_digest,
        reviewed_new_digest=new_rev_dig,
    )
    revoked_row = transition_assertion_state(suspended_row, ASSERTION_REVOKED, rev_approval)
    assert revoked_row["assertionState"] == ASSERTION_REVOKED

    # 3. Cannot transition from superseded (terminal)
    superseded_row = dict(row)
    superseded_row["assertionState"] = ASSERTION_SUPERSEDED
    sup_digest = compute_payload_digest(superseded_row)
    dummy_approval = ApprovalTransition(
        decision_ref="decision:invalid",
        reviewed_old_digest=sup_digest,
        reviewed_new_digest=sup_digest,
    )
    with pytest.raises(InvalidTransitionError, match="Cannot transition a superseded"):
        transition_assertion_state(superseded_row, ASSERTION_ACTIVE, dummy_approval)


def test_malformed_revision_cycles_rejected():
    """Self-supersession, forward supersession, and duplicate active revisions fail."""
    # Self-supersession
    row_self = {
        "evidenceId": "ev-cycle",
        "revision": 2,
        "supersedes": 2,
        "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1",
        "evaluator": "ev",
        "date": "2026-01-01",
    }
    with pytest.raises(MalformedRevisionCycleError, match="supersedes itself"):
        validate_revision_history("test/skill", [row_self])

    # Forward supersession
    row_forward = {
        "evidenceId": "ev-cycle",
        "revision": 2,
        "supersedes": 3,
        "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1",
        "evaluator": "ev",
        "date": "2026-01-01",
    }
    with pytest.raises(MalformedRevisionCycleError, match="supersedes future revision"):
        validate_revision_history("test/skill", [row_forward])

    # Multiple active revisions for same evidenceId
    row_active1 = {
        "evidenceId": "ev-multi-active",
        "revision": 1,
        "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1",
        "evaluator": "ev",
        "date": "2026-01-01",
    }
    row_active2 = {
        "evidenceId": "ev-multi-active",
        "revision": 2,
        "supersedes": 1,
        "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1",
        "evaluator": "ev",
        "date": "2026-01-01",
    }
    with pytest.raises(MalformedRevisionCycleError, match="at most 1 allowed"):
        validate_revision_history("test/skill", [row_active1, row_active2])


# ---------------------------------------------------------------------------
# 7. Stale Approval & Digest Mismatch Rejection
# ---------------------------------------------------------------------------

def test_stale_approval_old_digest_mismatch_fails():
    """An approval bound to an outdated old digest fails with StaleApprovalError."""
    row = {
        "evidenceId": "ev-test-1",
        "revision": 1,
        "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1234.5678",
        "evaluator": "mbtiongson1",
        "date": "2026-01-01",
    }
    stale_approval = ApprovalTransition(
        decision_ref="decision:stale",
        reviewed_old_digest="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        reviewed_new_digest="some-new-digest",
    )
    with pytest.raises(StaleApprovalError, match="Approval binding stale"):
        transition_assertion_state(row, ASSERTION_SUSPENDED, stale_approval)


def test_digest_mismatch_fails_on_transition():
    """An approval whose reviewedNewDigest does not match computed digest fails with DigestMismatchError."""
    row = {
        "evidenceId": "ev-test-1",
        "revision": 1,
        "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1234.5678",
        "evaluator": "mbtiongson1",
        "date": "2026-01-01",
    }
    actual_old_digest = compute_payload_digest(row)
    bad_approval = ApprovalTransition(
        decision_ref="decision:test",
        reviewed_old_digest=actual_old_digest,
        reviewed_new_digest="incorrect_new_digest_value",
    )
    with pytest.raises(DigestMismatchError, match="Approval binding mismatch"):
        transition_assertion_state(row, ASSERTION_SUSPENDED, bad_approval)


# ---------------------------------------------------------------------------
# 8. Finite & Raw Metric Validation
# ---------------------------------------------------------------------------

def test_non_finite_numeric_metrics_rejected():
    """NaN, Inf, and -Inf are rejected in evidence payloads."""
    row_nan = {
        "source": "https://github.com/org/repo",
        "evaluator": "ev",
        "date": "2026-01-01",
        "type": "github-stars-own",
        "stars": float("nan"),
    }
    with pytest.raises(EvidenceValidationError, match="non-finite value"):
        validate_evidence_payload(row_nan, allow_legacy=True)

    row_inf = {
        "source": "https://github.com/org/repo",
        "evaluator": "ev",
        "date": "2026-01-01",
        "type": "github-stars-own",
        "stars": float("inf"),
    }
    with pytest.raises(EvidenceValidationError, match="non-finite value"):
        validate_evidence_payload(row_inf, allow_legacy=True)


# ---------------------------------------------------------------------------
# 9. Schema Parity & Draft-7 Validation
# ---------------------------------------------------------------------------

def test_schema_mirrors_are_byte_identical():
    """Canonical, bundled, and docs schema mirrors must be byte-identical."""
    schema_tuples = [
        (
            REPO_ROOT / "registry" / "schema" / "skill.schema.json",
            REPO_ROOT / "docs" / "schema" / "skill.schema.json",
            REPO_ROOT / "src" / "gaia_cli" / "data" / "registry" / "schema" / "skill.schema.json",
        ),
        (
            REPO_ROOT / "registry" / "schema" / "namedSkill.schema.json",
            REPO_ROOT / "docs" / "schema" / "namedSkill.schema.json",
            REPO_ROOT / "src" / "gaia_cli" / "data" / "registry" / "schema" / "namedSkill.schema.json",
        ),
        (
            REPO_ROOT / "registry" / "schema" / "graph.schema.json",
            REPO_ROOT / "docs" / "schema" / "graph.schema.json",
            REPO_ROOT / "src" / "gaia_cli" / "data" / "registry" / "schema" / "graph.schema.json",
        ),
        (
            REPO_ROOT / "registry" / "schema" / "evidence" / "benchmark-result.schema.json",
            REPO_ROOT / "docs" / "schema" / "evidence" / "benchmark-result.schema.json",
            REPO_ROOT / "src" / "gaia_cli" / "data" / "registry" / "schema" / "evidence" / "benchmark-result.schema.json",
        ),
    ]
    for canon, docs, bundled in schema_tuples:
        canon_bytes = canon.read_bytes()
        assert docs.read_bytes() == canon_bytes, f"{docs} drifted from {canon}"
        assert bundled.read_bytes() == canon_bytes, f"{bundled} drifted from {canon}"


def test_proposed_schema_validates_both_legacy_and_migrated_evidence(sample_legacy_skill):
    """The additive schema accepts legacy rows and migrated lifecycle rows cleanly for skills."""
    skill_schema_path = REPO_ROOT / "registry" / "schema" / "skill.schema.json"
    with open(skill_schema_path, "r", encoding="utf-8") as f:
        skill_schema = json.load(f)

    # 1. Validate generic legacy skill
    jsonschema.validate(instance=sample_legacy_skill, schema=skill_schema)

    # 2. Validate migrated generic skill
    rehearsal = rehearse_legacy_migration(sample_legacy_skill)
    jsonschema.validate(instance=rehearsal.after_payload, schema=skill_schema)

    # 3. Validate named skill with proposed schema
    named_schema_path = REPO_ROOT / "registry" / "schema" / "namedSkill.schema.json"
    with open(named_schema_path, "r", encoding="utf-8") as f:
        named_schema = json.load(f)

    named_skill = {
        "id": "fixture/example-named",
        "name": "Example Named",
        "contributor": "fixture",
        "origin": False,
        "genericSkillRef": "agent-skills",
        "status": "named",
        "level": "2★",
        "description": "An example named skill implementation.",
        "createdAt": "2026-07-03",
        "updatedAt": "2026-10-01",
        "timeline": [
            {
                "timestamp": "2026-07-03T00:00:00Z",
                "action": "add",
                "contributor": "fixture",
                "details": "Added skill",
            }
        ],
        "evidence": [
            {
                "source": "https://github.com/fixture/example",
                "evaluator": "fixture",
                "date": "2026-07-03",
                "type": "github-stars-own",
                "stars": 200,
                "evidenceId": "ev-fixture-example-named-github-stars-own-1a2b3c4d",
                "revision": 1,
                "assertionState": "active",
                "decisionRef": "migration:yggdrasil-iv@test",
            }
        ],
    }
    jsonschema.validate(instance=named_skill, schema=named_schema)


def test_restoration_from_revoked_to_active():
    """An assertion can be restored from revoked to active with a new decisionRef."""
    row = {
        "evidenceId": "ev-restore-1",
        "revision": 1,
        "assertionState": ASSERTION_REVOKED,
        "decisionRef": "decision:past-revocation",
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1234.5678",
        "evaluator": "mbtiongson1",
        "date": "2026-01-01",
        "citations": 50,
    }
    old_digest = compute_payload_digest(row)
    proposed_restored = dict(row)
    proposed_restored["assertionState"] = ASSERTION_ACTIVE
    proposed_restored["decisionRef"] = "decision:restored-by-appeal#42"
    proposed_restored["reviewedOldDigest"] = old_digest
    new_digest = compute_payload_digest(proposed_restored)

    approval = ApprovalTransition(
        decision_ref="decision:restored-by-appeal#42",
        reviewed_old_digest=old_digest,
        reviewed_new_digest=new_digest,
        reason="counterevidence successfully rebutted",
    )
    restored_row = transition_assertion_state(row, ASSERTION_ACTIVE, approval)

    assert restored_row["assertionState"] == ASSERTION_ACTIVE
    assert restored_row["decisionRef"] == "decision:restored-by-appeal#42"
    assert restored_row["reviewedOldDigest"] == old_digest
    assert restored_row["reviewedNewDigest"] == new_digest


def test_circular_supersession_chain_length_3_rejected():
    """Circular supersession across multiple hops (3 -> 2 -> 1 -> 3) is rejected."""
    rows = [
        {
            "evidenceId": "ev-tri-cycle",
            "revision": 1,
            "supersedes": 3,  # Invalid: supersedes future revision
            "assertionState": ASSERTION_SUPERSEDED,
            "type": "arxiv",
            "source": "https://arxiv.org/abs/1",
            "evaluator": "ev",
            "date": "2026-01-01",
        },
        {
            "evidenceId": "ev-tri-cycle",
            "revision": 2,
            "supersedes": 1,
            "assertionState": ASSERTION_SUPERSEDED,
            "type": "arxiv",
            "source": "https://arxiv.org/abs/1",
            "evaluator": "ev",
            "date": "2026-01-01",
        },
        {
            "evidenceId": "ev-tri-cycle",
            "revision": 3,
            "supersedes": 2,
            "assertionState": ASSERTION_ACTIVE,
            "type": "arxiv",
            "source": "https://arxiv.org/abs/1",
            "evaluator": "ev",
            "date": "2026-01-01",
        },
    ]
    with pytest.raises(MalformedRevisionCycleError):
        validate_revision_history("test/skill", rows)


def test_blank_decision_ref_rejected():
    """Blank or whitespace-only decisionRef raises EvidenceValidationError."""
    row = {
        "evidenceId": "ev-test",
        "revision": 1,
        "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv",
        "source": "https://arxiv.org/abs/1",
        "evaluator": "ev",
        "date": "2026-01-01",
    }
    old_dig = compute_payload_digest(row)
    approval_blank = ApprovalTransition(
        decision_ref="   ",
        reviewed_old_digest=old_dig,
        reviewed_new_digest="anything",
    )
    with pytest.raises(EvidenceValidationError, match="non-blank"):
        transition_assertion_state(row, ASSERTION_SUSPENDED, approval_blank)


def test_missing_required_core_fields_rejected():
    """Missing or empty source, evaluator, or date is rejected in validate_evidence_payload."""
    row_no_src = {"evaluator": "ev", "date": "2026-01-01", "type": "repo-own"}
    with pytest.raises(EvidenceValidationError, match="missing required non-blank field 'source'"):
        validate_evidence_payload(row_no_src, allow_legacy=True)

    row_no_eval = {"source": "https://github.com", "date": "2026-01-01", "type": "repo-own"}
    with pytest.raises(EvidenceValidationError, match="missing required non-blank field 'evaluator'"):
        validate_evidence_payload(row_no_eval, allow_legacy=True)

    row_no_date = {"source": "https://github.com", "evaluator": "ev", "type": "repo-own"}
    with pytest.raises(EvidenceValidationError, match="missing required non-blank field 'date'"):
        validate_evidence_payload(row_no_date, allow_legacy=True)


def test_real_registry_generic_node_in_memory_rehearsal():
    """Rehearsal on real registry node api-call.json succeeds, is score-neutral, and writes zero files."""
    node_path = REPO_ROOT / "registry" / "nodes" / "basic" / "api-call.json"
    orig_bytes = node_path.read_bytes()

    with open(node_path, "r", encoding="utf-8") as f:
        node = json.load(f)

    result = rehearse_legacy_migration(node, decision_ref="migration:yggdrasil-iv@rehearsal-proof")
    assert result.score_neutral is True
    assert result.migrated_row_count > 0

    # Ensure node file on disk was NOT touched
    assert node_path.read_bytes() == orig_bytes

    # Exact rollback proof
    restored = apply_rollback(result.after_payload, result.rollback_payload)
    assert compute_payload_digest(restored) == result.before_digest


def test_real_registry_named_skill_in_memory_rehearsal():
    """Rehearsal on real named skill addy-osmani/agent-skills.md succeeds, is score-neutral, and writes zero files."""
    import yaml
    named_path = REPO_ROOT / "registry" / "named" / "addy-osmani" / "agent-skills.md"
    orig_bytes = named_path.read_bytes()

    text = orig_bytes.decode("utf-8")
    fm = yaml.safe_load(text.split("---")[1])

    result = rehearse_legacy_migration(fm, decision_ref="migration:yggdrasil-iv@named-rehearsal")
    assert result.score_neutral is True
    assert result.migrated_row_count > 0

    # Ensure named file on disk was NOT touched
    assert named_path.read_bytes() == orig_bytes

    # Exact rollback proof
    restored = apply_rollback(result.after_payload, result.rollback_payload)
    assert compute_payload_digest(restored) == result.before_digest


def test_active_evidence_rows_filtering():
    """active_evidence_rows includes only active assertions, respecting include_legacy."""
    skill = {
        "id": "test-filter",
        "evidence": [
            {
                "evidenceId": "ev-1",
                "revision": 1,
                "assertionState": ASSERTION_SUPERSEDED,
                "source": "https://a.com",
                "evaluator": "e",
                "date": "2026-01-01",
                "type": "repo-own",
            },
            {
                "evidenceId": "ev-1",
                "revision": 2,
                "assertionState": ASSERTION_ACTIVE,
                "source": "https://a.com",
                "evaluator": "e",
                "date": "2026-01-01",
                "type": "repo-own",
            },
            {
                "evidenceId": "ev-2",
                "revision": 1,
                "assertionState": ASSERTION_REVOKED,
                "source": "https://b.com",
                "evaluator": "e",
                "date": "2026-01-01",
                "type": "arxiv",
            },
            {
                "evidenceId": "ev-3",
                "revision": 1,
                "assertionState": ASSERTION_SUSPENDED,
                "source": "https://c.com",
                "evaluator": "e",
                "date": "2026-01-01",
                "type": "arxiv",
            },
            {
                # Legacy unmigrated row
                "source": "https://legacy.com",
                "evaluator": "e",
                "date": "2026-01-01",
                "type": "github-stars-own",
                "stars": 100,
            },
        ],
    }
    # With include_legacy=True (default score-neutral read compatibility)
    active_with_legacy = active_evidence_rows(skill, include_legacy=True)
    assert len(active_with_legacy) == 2
    assert active_with_legacy[0]["evidenceId"] == "ev-1"
    assert active_with_legacy[0]["revision"] == 2
    assert active_with_legacy[1]["source"] == "https://legacy.com"

    # With include_legacy=False
    active_no_legacy = active_evidence_rows(skill, include_legacy=False)
    assert len(active_no_legacy) == 1
    assert active_no_legacy[0]["evidenceId"] == "ev-1"
    assert active_no_legacy[0]["revision"] == 2


def test_preexisting_exclusions_remain_score_neutral():
    """Rejected benchmark rows and deranked verifier rows remain 0 score before and after."""
    skill = {
        "id": "basic/benchmark-test",
        "evidence": [
            {
                "source": "https://example.com/benchmark",
                "evaluator": "test",
                "date": "2026-07-08",
                "type": "benchmark-result",
                "benchmarkId": "swe-bench_verified@1.0",
                "score": 45.0,
                "unit": "pct",
                "provenance": "rejected",  # Preexisting exclusion lane
            }
        ],
    }
    rehearsal = rehearse_legacy_migration(skill)
    assert rehearsal.before_score == 0.0
    assert rehearsal.after_score == 0.0
    assert rehearsal.score_neutral is True


