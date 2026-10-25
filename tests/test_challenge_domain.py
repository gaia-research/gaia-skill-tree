from dataclasses import replace

import pytest

from gaia_cli.challengeDomain import (
    ChallengeStatus,
    ClosureDisposition,
    NumericProposal,
    NumericProposalState,
    Observation,
    ObservationState,
    TechnicalProof,
    close_technical_challenge,
    link_reopened_challenge,
    open_challenge,
    origin_contested,
)


def challenge(**overrides):
    values = {
        "subject_id": "skill/example",
        "claim_id": "claim-1",
        "claim": "Behavior X fails under pinned test",
        "behavior_id": "behavior-x-v1",
        "contributor_id": "author",
        "contributor_notice_ref": "https://example.org/notices/1",
        "pinned_version": "1.0.0",
        "pinned_sha": "sha-old",
        "environment": "linux-x86_64; python=3.12",
        "test_version": "suite-4",
        "baseline": "fixture-set-a",
        "comparator": "comparator@2.1",
        "verified_at_utc": "2026-10-25T12:00:00Z",
        "verifier_id": "independent-reviewer",
        "material_to_origin": True,
    }
    values.update(overrides)
    return open_challenge(**values)


def proof(**overrides):
    values = {
        "claim_id": "claim-1",
        "behavior_id": "behavior-x-v1",
        "prior_version": "1.0.0",
        "prior_sha": "sha-old",
        "current_version": "1.1.0",
        "current_sha": "sha-new",
        "environment": "linux-x86_64; python=3.12",
        "test_version": "suite-4",
        "baseline": "fixture-set-a",
        "comparator": "comparator@2.1",
        "actual_output": "PASS: 12/12 cases; output-digest=abc",
        "verifier_id": "independent-reviewer",
        "contributor_id": "author",
        "builder_id": "builder",
        "verification_result": "passed",
        "verification_method": "reproducible-test",
        "public_receipt_ref": "https://example.org/receipts/resolve-1",
        "contributor_notice_ref": "https://example.org/notices/resolved-1",
        "verified_at_utc": "2026-10-26T12:00:00Z",
        "upstream_improvement": True,
    }
    values.update(overrides)
    return TechnicalProof(**values)


def test_observation_and_challenge_ids_are_stable_and_bind_pins():
    one = Observation("repo/a", "2026-10-25T00:00:00Z", ObservationState.TRANSIENT_FAILURE)
    two = Observation("repo/a", "2026-10-25T00:00:00Z", ObservationState.TRANSIENT_FAILURE)
    assert one.observation_id == two.observation_id
    assert one.state is ObservationState.TRANSIENT_FAILURE
    original = challenge()
    assert original.challenge_id == challenge().challenge_id
    assert original.challenge_id != challenge(pinned_sha="different-sha").challenge_id


def test_incomplete_or_conflicting_proofs_escalate_class_c():
    opened = challenge()
    for invalid in (
        proof(actual_output=""),
        proof(verification_result="partial"),
        proof(verification_method="model-only"),
        proof(verifier_id="builder"),
        proof(environment="different environment"),
        proof(baseline="different baseline"),
        proof(comparator="different comparator"),
        proof(prior_sha="conflicting-sha"),
        proof(behavior_id="different behavior"),
        proof(public_receipt_ref="file:///private/receipt"),
    ):
        result = close_technical_challenge(opened, invalid, closed_at_utc="2026-10-27T00:00:00Z")
        assert result.disposition is ClosureDisposition.CLASS_C
        assert result.challenge == opened
        assert result.contested is True


def test_independent_complete_improvement_closes_public_status_only():
    opened = challenge()
    result = close_technical_challenge(opened, proof(), closed_at_utc="2026-10-27T00:00:00Z")
    assert result.disposition is ClosureDisposition.CLOSED
    assert result.challenge.status is ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT
    assert len(result.challenge.history) == len(opened.history) + 1
    assert result.challenge.history[0] == opened.history[0]
    assert result.contested is False
    assert origin_contested((result.challenge,)) is False


def test_rebuttal_closes_technical_challenge_but_numeric_proposal_stays_separate():
    opened = challenge()
    result = close_technical_challenge(
        opened, proof(upstream_improvement=False), closed_at_utc="2026-10-27T00:00:00Z"
    )
    assert result.challenge.status is ChallengeStatus.TECHNICALLY_REBUTTED
    pending = NumericProposal("proposal-1", opened.challenge_id,
                              NumericProposalState.AWAITING_APPROVAL, "opaque-digest",
                              "2026-10-27T00:00:00Z")
    assert pending.state is NumericProposalState.AWAITING_APPROVAL
    assert result.challenge.resolved
    assert not hasattr(result.challenge, "score")


def test_multiple_material_challenges_keep_origin_contested_until_all_resolve():
    first = challenge()
    second = challenge(claim_id="claim-2", behavior_id="behavior-y", claim="Other behavior")
    closed = close_technical_challenge(
        first, proof(), closed_at_utc="2026-10-27T00:00:00Z"
    ).challenge
    assert origin_contested((closed, second)) is True


def test_reopening_requires_new_linked_challenge_and_preserves_old_history():
    previous = close_technical_challenge(
        challenge(), proof(), closed_at_utc="2026-10-27T00:00:00Z"
    ).challenge
    reopened = challenge(claim_id="claim-2", behavior_id="behavior-x-v2",
                         linked_challenge_id=previous.challenge_id,
                         verified_at_utc="2026-11-01T12:00:00Z")
    assert link_reopened_challenge(previous, reopened) == reopened
    assert previous.status is ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT
    assert previous.history[-1].event_type == "technical-resolution"
    with pytest.raises(ValueError, match="link"):
        link_reopened_challenge(previous, replace(reopened, linked_challenge_id=None))


def test_no_timeout_or_numeric_side_effect_is_encoded_in_core():
    opened = challenge()
    assert opened.status is ChallengeStatus.VERIFIED_PENDING
    assert origin_contested((opened,)) is True
    assert not hasattr(opened, "numeric_state")
    assert NumericProposalState.SHADOW.value == "shadow"
