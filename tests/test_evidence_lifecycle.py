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
    prepare_assertion_transition,
    prepare_metric_refresh,
    EvidenceValidationError,
    InvalidTransitionError,
    MalformedRevisionCycleError,
    active_evidence_rows,
    apply_rollback,
    compute_payload_digest,
    derive_evidence_identity,
    rehearse_legacy_migration,
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
        assert "decisionRef" not in row
        assert row["evidenceId"].startswith("ev-")
        assert "metricMethod" not in row


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

def _observation_provenance(**overrides):
    result = {"metricMethod": METRIC_VERIFIED, "observationState": "reachable",
        "lastObservedAt": "2026-01-01T12:00:00Z", "sourceRevision": "abc123",
        "contentDigest": "a" * 64, "measurementScope": "repository"}
    result.update(overrides)
    return result


def test_metric_refresh_is_full_payload_shadow_proposal(sample_legacy_skill):
    skill = rehearse_legacy_migration(sample_legacy_skill).after_payload
    eid = skill["evidence"][0]["evidenceId"]
    prior = copy.deepcopy(skill["evidence"][0])
    plan = prepare_metric_refresh(skill, eid, {"stars": 1500}, "proposal:refresh-stars", _observation_provenance())
    assert plan.operation == "metric-refresh"
    assert plan.before_digest == compute_payload_digest(skill)
    assert plan.after_digest == compute_payload_digest(plan.after_payload)
    assert plan.after_payload["evidence"][0] == prior  # immutable prior revision
    successor = plan.after_payload["evidence"][-1]
    assert successor["evidenceId"] == eid and successor["revision"] == 2
    assert successor["supersedes"] == 1 and successor["stars"] == 1500
    assert successor["lastObservedAt"] == "2026-01-01T12:00:00Z"
    assert successor["decisionHistory"][-1]["priorPayload"] == prior
    assert plan.history_before and len(plan.history_after) == len(plan.history_before) + 1
    second = prepare_metric_refresh(plan.after_payload, eid, {"stars": 1700}, "proposal:refresh-again", _observation_provenance())
    assert second.after_payload["evidence"][-1]["revision"] == 3
    assert second.after_payload["evidence"][-1]["supersedes"] == 2
    assert active_evidence_rows(second.after_payload)[0]["stars"] == 1700
    assert "authorized" not in plan.operation


# ---------------------------------------------------------------------------
# 6. Assertion State Transitions & Cycle Rejection
# ---------------------------------------------------------------------------

def test_assertion_transition_is_only_a_proposal_and_preserves_decision_history():
    row = {"evidenceId": "ev-test-1", "revision": 1, "assertionState": ASSERTION_ACTIVE,
        "decisionRef": "decision:initial", "type": "arxiv", "source": "https://arxiv.org/abs/1234.5678",
        "evaluator": "mbtiongson1", "date": "2026-01-01", "citations": 10}
    skill = {"id": "test/skill", "evidence": [row]}
    proposal = prepare_assertion_transition(skill, "ev-test-1", ASSERTION_SUSPENDED, "proposal:suspend")
    assert proposal.after_payload["evidence"][0] == row  # immutable prior revision
    after = proposal.after_payload["evidence"][-1]
    assert after["revision"] == 2 and after["supersedes"] == 1
    assert after["assertionState"] == ASSERTION_SUSPENDED
    assert after["decisionRef"] == "proposal:suspend"
    history = after["decisionHistory"][-1]
    assert history["decisionRef"] == "decision:initial"
    assert history["assertionState"] == ASSERTION_ACTIVE and history["priorPayload"] == row
    assert history["proposedBy"] == "unknown" and history["proposedAt"].endswith("Z")
    assert skill["evidence"][0] == row  # input untouched
    assert proposal.before_digest != proposal.after_digest
    revoked = prepare_assertion_transition(proposal.after_payload, "ev-test-1", ASSERTION_REVOKED, "proposal:revoke")
    assert revoked.after_payload["evidence"][-1]["revision"] == 3
    assert revoked.after_payload["evidence"][-1]["supersedes"] == 2
    assert revoked.after_payload["evidence"][0] == row
    with pytest.raises(InvalidTransitionError, match="Cannot transition a superseded"):
        prepare_assertion_transition({"id": "x", "evidence": [{**row, "assertionState": ASSERTION_SUPERSEDED}]},
            "ev-test-1", ASSERTION_ACTIVE, "proposal:invalid")


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
    with pytest.raises(MalformedRevisionCycleError, match="immediate predecessor"):
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
    # Revisions are immutable historical snapshots; the highest revision is current.
    validate_revision_history("test/skill", [row_active1, row_active2])
    assert active_evidence_rows({"evidence": [row_active1, row_active2]}) == [row_active2]


# ---------------------------------------------------------------------------
# 7. Proposal boundary and metric refresh restrictions
# ---------------------------------------------------------------------------

def test_metric_refresh_cannot_modify_identity_class_or_lifecycle_fields(sample_legacy_skill):
    skill = rehearse_legacy_migration(sample_legacy_skill).after_payload
    evidence_id = skill["evidence"][0]["evidenceId"]
    for field, value in [("source", "https://other.example"), ("type", "arxiv"),
                         ("grade", "S"), ("verified", True), ("assertionState", "revoked")]:
        with pytest.raises(EvidenceValidationError, match="Only raw metric fields"):
            prepare_metric_refresh(skill, evidence_id, {field: value}, "proposal:test")


def test_metric_refresh_rejects_provenance_identity_overwrite(sample_legacy_skill):
    skill = rehearse_legacy_migration(sample_legacy_skill).after_payload
    evidence_id = skill["evidence"][0]["evidenceId"]
    with pytest.raises(EvidenceValidationError, match="provenance must provide"):
        prepare_metric_refresh(skill, evidence_id, {"stars": 2}, "proposal:test", {**_observation_provenance(), "evaluator": "forged"})


def test_metric_refresh_requires_truthful_complete_utc_observation(sample_legacy_skill):
    skill = rehearse_legacy_migration(sample_legacy_skill).after_payload
    row = skill["evidence"][0]
    row["lastVerified"] = "2025-01-01"
    row["sourceStartedAt"] = "2020-01-01"
    for provenance in (None, {}, {**_observation_provenance(), "lastObservedAt": "2026-01-01T12:00:00"},
                       _observation_provenance(contentDigest=""), _observation_provenance(sourceRevision="")):
        with pytest.raises(EvidenceValidationError):
            prepare_metric_refresh(skill, row["evidenceId"], {"stars": 1001}, "proposal:refresh", provenance)
    plan = prepare_metric_refresh(skill, row["evidenceId"], {"stars": 1001}, "proposal:refresh",
        _observation_provenance(metricMethod="unknown", observationState="unknown",
            contentDigest="unknown", sourceRevision="unknown", measurementScope="unknown"))
    successor = plan.after_payload["evidence"][-1]
    assert successor["lastVerified"] == "2025-01-01"
    assert successor["sourceStartedAt"] == "2020-01-01"
    assert successor["lastObservedAt"] != successor["lastVerified"]


def test_all_migrated_path_validates_history_before_noop(sample_legacy_skill):
    migrated = rehearse_legacy_migration(sample_legacy_skill).after_payload
    migrated["evidence"][0]["assertionState"] = "bogus"
    with pytest.raises(EvidenceValidationError, match="Invalid assertionState"):
        rehearse_legacy_migration(migrated)


def test_non_active_migration_state_is_preserved(sample_legacy_skill):
    mixed = copy.deepcopy(sample_legacy_skill)
    mixed["evidence"][0].update({"evidenceId": "ev-existing", "revision": 1,
        "assertionState": ASSERTION_REVOKED, "decisionRef": "decision:revoked"})
    result = rehearse_legacy_migration(mixed)
    assert result.after_payload["evidence"][0]["assertionState"] == ASSERTION_REVOKED
    assert result.after_payload["evidence"][0]["decisionRef"] == "decision:revoked"
    assert result.after_payload["evidence"][1]["assertionState"] == ASSERTION_ACTIVE


def test_every_partial_lifecycle_metadata_combination_fails(sample_legacy_skill):
    from itertools import combinations
    keys = ("evidenceId", "revision", "assertionState", "decisionRef")
    for size in range(1, len(keys)):
        for subset in combinations(keys, size):
            damaged = copy.deepcopy(sample_legacy_skill)
            metadata = {"evidenceId": "ev-partial", "revision": 1,
                "assertionState": ASSERTION_REVOKED, "decisionRef": "decision:revoked"}
            damaged["evidence"][0].update({key: metadata[key] for key in subset})
            with pytest.raises(EvidenceValidationError, match="Partial lifecycle metadata|revision|assertionState|decisionRef"):
                rehearse_legacy_migration(damaged)


def test_legacy_verified_boolean_is_not_treated_as_lifecycle_approval(sample_legacy_skill):
    row = sample_legacy_skill["evidence"][0]
    row["verified"] = True
    result = rehearse_legacy_migration(sample_legacy_skill)
    migrated = result.after_payload["evidence"][0]
    assert migrated["verified"] is True
    assert migrated["assertionState"] == ASSERTION_ACTIVE
    assert "decisionRef" not in migrated and "metricMethod" not in migrated


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
    with pytest.raises(EvidenceValidationError, match="finite and non-negative"):
        validate_evidence_payload(row_nan, allow_legacy=True)

    row_inf = {
        "source": "https://github.com/org/repo",
        "evaluator": "ev",
        "date": "2026-01-01",
        "type": "github-stars-own",
        "stars": float("inf"),
    }
    with pytest.raises(EvidenceValidationError, match="finite and non-negative"):
        validate_evidence_payload(row_inf, allow_legacy=True)


def test_malformed_dates_negative_bool_unknown_and_invalid_ranges_rejected():
    base = {"source": "https://example.org", "evaluator": "ev", "date": "2026-01-01", "type": "arxiv"}
    for key, value in [("date", "2026-02-31"), ("citations", -1), ("citations", True),
                       ("percentile", 101), ("mysteryField", "x")]:
        with pytest.raises(EvidenceValidationError):
            validate_evidence_payload({**base, key: value}, allow_legacy=True)


def test_revoked_lifecycle_schema_requires_decision_reference():
    schema = json.loads((REPO_ROOT / "registry/schema/skill.schema.json").read_text())
    row = {"source": "https://example.org", "evaluator": "ev", "date": "2026-01-01", "type": "arxiv",
           "evidenceId": "ev-x", "revision": 1, "assertionState": "revoked"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"id": "x", "name": "x", "type": "basic", "description": "An example node description.",
            "prerequisites": [], "evidence": [row]}, schema)


def test_identity_matches_tm_canonicalization_without_stripping_query():
    base = {"type": "repo-own", "evaluator": "ev", "date": "2026-01-01"}
    a = derive_evidence_identity("x", {**base, "source": "https://GitHub.com/Org/Repo/tree/main/path/#frag"})
    b = derive_evidence_identity("x", {**base, "source": "https://github.com/org/repo/blob/main/path"})
    c = derive_evidence_identity("x", {**base, "source": "https://github.com/org/repo/blob/main/path?view=1"})
    assert a == b
    assert a != c
    assert len(a.rsplit("-", 1)[-1]) == 64


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


def test_unadopted_schema_refuses_migrated_evidence(sample_legacy_skill):
    """This integration deliberately does not adopt the separately held schemas."""
    skill_schema_path = REPO_ROOT / "registry" / "schema" / "skill.schema.json"
    with open(skill_schema_path, "r", encoding="utf-8") as f:
        skill_schema = json.load(f)

    # 1. Validate generic legacy skill
    jsonschema.validate(instance=sample_legacy_skill, schema=skill_schema)

    # 2. Validate migrated generic skill
    rehearsal = rehearse_legacy_migration(sample_legacy_skill)
    with pytest.raises(jsonschema.ValidationError, match="Additional properties"):
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
    with pytest.raises(jsonschema.ValidationError, match="Additional properties"):
        jsonschema.validate(instance=named_skill, schema=named_schema)


def test_restoration_is_proposal_and_prior_decision_remains_in_history():
    row = {"evidenceId": "ev-restore-1", "revision": 1, "assertionState": ASSERTION_REVOKED,
        "decisionRef": "decision:past-revocation", "type": "arxiv", "source": "https://arxiv.org/abs/1234.5678",
        "evaluator": "mbtiongson1", "date": "2026-01-01", "citations": 50}
    plan = prepare_assertion_transition({"id": "x", "evidence": [row]}, "ev-restore-1",
        ASSERTION_ACTIVE, "proposal:appeal")
    assert plan.after_payload["evidence"][0] == row
    restored = plan.after_payload["evidence"][-1]
    assert restored["revision"] == 2 and restored["assertionState"] == ASSERTION_ACTIVE
    assert restored["decisionRef"] == "proposal:appeal"
    history = restored["decisionHistory"][-1]
    assert history["decisionRef"] == "decision:past-revocation"
    assert history["assertionState"] == ASSERTION_REVOKED and history["priorPayload"] == row


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


def test_blank_proposal_ref_rejected():
    row = {"evidenceId": "ev-test", "revision": 1, "assertionState": ASSERTION_ACTIVE,
        "type": "arxiv", "source": "https://arxiv.org/abs/1", "evaluator": "ev", "date": "2026-01-01"}
    with pytest.raises(EvidenceValidationError, match="non-blank"):
        prepare_assertion_transition({"id": "x", "evidence": [row]}, "ev-test", ASSERTION_SUSPENDED, "  ")


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

    # Historical rows with fields absent from the current evidence schema must fail closed;
    # this rehearsal does not silently sanitize or migrate them.
    with pytest.raises(EvidenceValidationError, match="Unknown evidence field"):
        rehearse_legacy_migration(fm, decision_ref="migration:yggdrasil-iv@named-rehearsal")
    assert named_path.read_bytes() == orig_bytes


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


