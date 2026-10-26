from dataclasses import replace

import pytest

from gaia_cli.challengeDomain import (
    ChallengeStatus, ClosureDisposition, NumericProposal, NumericProposalState,
    Observation, ObservationState, TechnicalProof, VerificationReceipt,
    close_technical_challenge, link_reopened_challenge, open_challenge,
    origin_contested, validate_challenge_history, _canonical, _digest,
)


class Resolver:
    def __init__(self):
        self.receipts = {}

    def resolve(self, receipt_id):
        return self.receipts[receipt_id]


def challenge_values(**overrides):
    values = {
        "subject_id": "skill/example", "claim_id": "claim-1",
        "claim": "Behavior X fails under pinned test", "behavior_id": "behavior-x-v1",
        "contributor_id": "author", "contributor_notice_ref": "https://example.org/notices/1",
        "pinned_version": "1.0.0", "pinned_sha": "sha-old",
        "environment": "linux-x86_64; python=3.12", "test_version": "suite-4",
        "baseline": "fixture-set-a", "comparator": "comparator@2.1",
        "verified_at_utc": "2026-10-25T12:00:00Z", "verifier_id": "independent-reviewer",
        "material_to_origin": True,
    }
    values.update(overrides)
    return values


def draft_context(values):
    draft = {"subject_id": values["subject_id"], "claim_id": values["claim_id"],
             "claim": values["claim"], "behavior_id": values["behavior_id"],
             "contributor_id": values["contributor_id"],
             "contributor_notice_ref": values["contributor_notice_ref"],
             "pinned_version": values["pinned_version"], "pinned_sha": values["pinned_sha"],
             "environment": values["environment"], "test_version": values["test_version"],
             "baseline": values["baseline"], "comparator": values["comparator"],
             "material_to_origin": values["material_to_origin"],
             "created_at_utc": values["verified_at_utc"], "linked_challenge_id": values.get("linked_challenge_id")}
    return _digest(_canonical(draft))


def opened(**overrides):
    values = challenge_values(**overrides)
    resolver = Resolver()
    receipt = VerificationReceipt("open-receipt", draft_context(values), "reproduction-transcript",
        values["verifier_id"], "reproducer", values["contributor_id"], "passed",
        "reproducible-test", "2", "PASS: 12/12", "output-sha256", "https://example.org/receipt/open",
        values["contributor_notice_ref"], values["verified_at_utc"])
    resolver.receipts[receipt.receipt_id] = receipt
    challenge = open_challenge(**values, receipt_resolver=resolver,
                               verification_receipt_id=receipt.receipt_id)
    return challenge, resolver


def proof(challenge, **overrides):
    values = {
        "claim_id": challenge.claim_id, "behavior_id": challenge.behavior_id,
        "prior_version": challenge.pinned_version, "prior_sha": challenge.pinned_sha,
        "current_version": "1.1.0", "current_sha": "sha-new",
        "environment": challenge.environment, "test_version": challenge.test_version,
        "baseline": challenge.baseline, "comparator": challenge.comparator,
        "actual_output": "PASS: 12/12 cases", "verifier_id": "independent-reviewer",
        "contributor_id": challenge.contributor_id, "builder_id": "builder",
        "verification_result": "passed", "verification_method": "reproducible-test",
        "public_receipt_ref": "https://example.org/receipts/resolve-1",
        "contributor_notice_ref": "https://example.org/notices/resolved-1",
        "verified_at_utc": "2026-10-26T12:00:00Z", "upstream_improvement": True,
        "challenge_id": challenge.challenge_id, "method_version": "test-runner-3",
        "output_digest": "sha256:actual-output",
    }
    values.update(overrides)
    return TechnicalProof(**values)


def resolve_close(challenge, packet, resolver=None, closed_at="2026-10-27T00:00:00Z", **changes):
    resolver = resolver or Resolver()
    context = _digest(_canonical({"challenge_id": challenge.challenge_id,
        "claim_id": challenge.claim_id, "behavior_id": challenge.behavior_id,
        "pinned_version": challenge.pinned_version, "pinned_sha": challenge.pinned_sha,
        "environment": challenge.environment, "test_version": challenge.test_version,
        "baseline": challenge.baseline, "comparator": challenge.comparator}))
    receipt = VerificationReceipt("close-receipt", context, packet.proof_digest,
        packet.verifier_id, packet.builder_id, packet.contributor_id,
        packet.verification_result, packet.verification_method, packet.method_version,
        packet.actual_output, packet.output_digest, packet.public_receipt_ref,
        packet.contributor_notice_ref, packet.verified_at_utc)
    for key, value in changes.items():
        receipt = replace(receipt, **{key: value})
    resolver.receipts[receipt.receipt_id] = receipt
    return close_technical_challenge(challenge, packet, closed_at_utc=closed_at,
                                     receipt_resolver=resolver,
                                     verification_receipt_id=receipt.receipt_id)


def test_opening_rejects_builder_verifier_overlap_and_future_receipt():
    values = challenge_values()
    resolver = Resolver()
    receipt = VerificationReceipt("open-receipt", draft_context(values), "reproduction-transcript",
        values["verifier_id"], values["verifier_id"], values["contributor_id"], "passed",
        "reproducible-test", "2", "PASS: 12/12", "output-sha256", "https://example.org/receipt/open",
        values["contributor_notice_ref"], values["verified_at_utc"])
    resolver.receipts[receipt.receipt_id] = receipt
    with pytest.raises(ValueError, match="independent of builder"):
        open_challenge(**values, receipt_resolver=resolver,
                       verification_receipt_id=receipt.receipt_id)

    receipt = replace(receipt, builder_id="reproducer", verified_at_utc="2026-10-25T12:00:01Z")
    resolver.receipts[receipt.receipt_id] = receipt
    with pytest.raises(ValueError, match="after asserted event time"):
        open_challenge(**values, receipt_resolver=resolver,
                       verification_receipt_id=receipt.receipt_id)
    object.__setattr__(receipt, "builder_id", "  ")
    resolver.receipts[receipt.receipt_id] = receipt
    with pytest.raises(ValueError, match="builder identity is absent"):
        open_challenge(**values, receipt_resolver=resolver,
                       verification_receipt_id=receipt.receipt_id)


def test_ids_and_receipts_bind_exact_opening_context():
    first, resolver = opened()
    second, _ = opened(claim="different allegation")
    assert first.challenge_id != second.challenge_id
    assert first.history[0].receipt_digest
    validate_challenge_history(first, resolver)
    with pytest.raises(ValueError, match="resolver"):
        open_challenge(**challenge_values())
    bad = Resolver()
    bad.receipts["fake"] = replace(resolver.receipts["open-receipt"], receipt_id="fake",
                                    context_digest="invented")
    with pytest.raises(ValueError, match="different exact context"):
        open_challenge(**challenge_values(), receipt_resolver=bad, verification_receipt_id="fake")


def test_rehydration_rejects_builder_verifier_overlap_and_receipts_after_events():
    challenge, resolver = opened()
    opening = challenge.history[0]
    original = resolver.receipts[opening.receipt_id]
    forged = replace(original, builder_id=original.verifier_id)
    resolver.receipts[forged.receipt_id] = forged
    changed_opening = replace(opening, receipt_digest=_digest(_canonical(forged)))
    tampered = replace(challenge, history=(changed_opening,), history_digest="")
    with pytest.raises(ValueError, match="independent passing"):
        validate_challenge_history(tampered, resolver)

    future = replace(original, verified_at_utc="2026-10-25T12:00:01Z")
    resolver.receipts[future.receipt_id] = future
    changed_opening = replace(opening, receipt_digest=_digest(_canonical(future)))
    tampered = replace(challenge, history=(changed_opening,), history_digest="")
    with pytest.raises(ValueError, match="event cannot predate"):
        validate_challenge_history(tampered, resolver)


def test_untrusted_flags_or_method_aliases_cannot_close():
    opened_challenge, resolver = opened()
    for packet in (proof(opened_challenge, verification_method="model-alias"),
                   proof(opened_challenge, verifier_id="builder"),
                   proof(opened_challenge, challenge_id="other-challenge"),
                   proof(opened_challenge, pinned_sha_known=False),
                   proof(opened_challenge, comparator_known=False)):
        result = resolve_close(opened_challenge, packet)
        assert result.disposition is ClosureDisposition.CLASS_C
        assert result.challenge == opened_challenge
    # The packet alone never authorizes closure; the trusted receipt must exist.
    result = close_technical_challenge(opened_challenge, proof(opened_challenge),
        closed_at_utc="2026-10-27T00:00:00Z", receipt_resolver=resolver,
        verification_receipt_id="missing")
    assert result.disposition is ClosureDisposition.CLASS_C
    failed_receipt = resolve_close(opened_challenge, proof(opened_challenge), result="failed")
    assert failed_receipt.disposition is ClosureDisposition.CLASS_C


def _proof_attack_with_existing_receipt(original, target, packet):
    trusted = Resolver()
    context = _digest(_canonical({"challenge_id": original.challenge_id,
        "claim_id": original.claim_id, "behavior_id": original.behavior_id,
        "pinned_version": original.pinned_version, "pinned_sha": original.pinned_sha,
        "environment": original.environment, "test_version": original.test_version,
        "baseline": original.baseline, "comparator": original.comparator}))
    receipt = VerificationReceipt("approved-original", context, packet.proof_digest,
        packet.verifier_id, packet.builder_id, packet.contributor_id, packet.verification_result,
        packet.verification_method, packet.method_version, packet.actual_output, packet.output_digest,
        packet.public_receipt_ref, packet.contributor_notice_ref, packet.verified_at_utc)
    trusted.receipts[receipt.receipt_id] = receipt
    return close_technical_challenge(target, packet, closed_at_utc="2026-10-27T00:00:00Z",
        receipt_resolver=trusted, verification_receipt_id=receipt.receipt_id).disposition


def test_closure_requires_exact_challenge_and_persisted_receipt_binding():
    one, _ = opened()
    two, _ = opened(claim="different allegation")
    packet = proof(one)
    cross = replace(packet, challenge_id=two.challenge_id)
    assert _proof_attack_with_existing_receipt(one, two, packet) is ClosureDisposition.CLASS_C
    result = resolve_close(one, packet)
    assert result.disposition is ClosureDisposition.CLOSED
    event = result.challenge.history[-1]
    assert event.challenge_id == one.challenge_id
    assert event.transcript_digest == packet.proof_digest
    assert event.receipt_digest and event.notice_ref and event.method_version and event.output_digest
    replay = resolve_close(result.challenge, packet, closed_at="2026-10-27T00:00:00Z")
    assert replay.disposition is ClosureDisposition.CLOSED
    assert replay.challenge == result.challenge
    assert "idempotent" in replay.reason
    different = resolve_close(result.challenge, proof(one, actual_output="different output"),
                               closed_at="2026-10-27T00:00:00Z")
    assert different.disposition is ClosureDisposition.CLASS_C
    assert different.challenge == result.challenge


def test_closure_receipt_rejects_builder_verifier_overlap():
    challenge, _ = opened()
    packet = proof(challenge, builder_id="independent-reviewer")
    result = resolve_close(challenge, packet)
    assert result.disposition is ClosureDisposition.CLASS_C
    assert "independent" in result.reason


def test_chronology_and_receipt_digest_tampering_are_rejected():
    opened_challenge, _ = opened()
    packet = proof(opened_challenge)
    early = resolve_close(opened_challenge, packet, closed_at="2026-10-25T11:59:59Z")
    assert early.disposition is ClosureDisposition.CLASS_C
    closed = resolve_close(opened_challenge, packet).challenge
    with pytest.raises(ValueError, match="history digest"):
        replace(closed, history=(closed.history[0], replace(closed.history[-1], receipt_digest="tampered")))
    with pytest.raises(ValueError, match="challenge_id"):
        replace(closed, challenge_id="invented")


def test_rehydration_rejects_closure_receipt_after_event():
    challenge, resolver = opened()
    packet = proof(challenge)
    result = resolve_close(challenge, packet)
    closed = result.challenge
    event = closed.history[-1]
    context = _digest(_canonical({"challenge_id": challenge.challenge_id,
        "claim_id": challenge.claim_id, "behavior_id": challenge.behavior_id,
        "pinned_version": challenge.pinned_version, "pinned_sha": challenge.pinned_sha,
        "environment": challenge.environment, "test_version": challenge.test_version,
        "baseline": challenge.baseline, "comparator": challenge.comparator}))
    receipt = VerificationReceipt(event.receipt_id, context, packet.proof_digest,
        packet.verifier_id, packet.builder_id, packet.contributor_id, packet.verification_result,
        packet.verification_method, packet.method_version, packet.actual_output, packet.output_digest,
        packet.public_receipt_ref, packet.contributor_notice_ref, "2026-10-28T00:00:00Z")
    resolver.receipts[receipt.receipt_id] = receipt
    altered = replace(event, receipt_digest=_digest(_canonical(receipt)))
    tampered = replace(closed, history=(closed.history[0], altered), history_digest="")
    with pytest.raises(ValueError, match="event cannot predate"):
        validate_challenge_history(tampered, resolver)


def test_only_authorized_technical_transition_is_supported_and_reopening_is_linked():
    first, _ = opened()
    closed = resolve_close(first, proof(first)).challenge
    assert closed.status is ChallengeStatus.RESOLVED_BY_UPSTREAM_IMPROVEMENT
    with pytest.raises(ValueError, match="status"):
        replace(first, status=ChallengeStatus.UPHELD)
    reopened_values = challenge_values(claim_id="claim-2", behavior_id="behavior-x-v2",
        claim="New allegation", linked_challenge_id=closed.challenge_id,
        verified_at_utc="2026-11-01T12:00:00Z")
    # Opening receipt must bind the linked proceeding too.
    reopened, _ = opened(**reopened_values)
    assert link_reopened_challenge(closed, reopened) == reopened
    with pytest.raises(ValueError, match="resolved"):
        link_reopened_challenge(first, reopened)


def test_independent_rebuttal_and_numeric_proposal_remain_separate():
    original, _ = opened()
    result = resolve_close(original, proof(original, upstream_improvement=False))
    assert result.challenge.status is ChallengeStatus.TECHNICALLY_REBUTTED
    pending = NumericProposal("proposal-1", original.challenge_id,
        NumericProposalState.AWAITING_APPROVAL, "opaque-digest", "2026-10-27T00:00:00Z")
    assert pending.state is NumericProposalState.AWAITING_APPROVAL
    assert origin_contested((result.challenge,)) is False
    assert not hasattr(result.challenge, "score")


def test_multiple_material_challenges_and_observation_idempotence():
    first, _ = opened()
    second, _ = opened(claim_id="claim-2", behavior_id="behavior-y", claim="Other behavior")
    closed = resolve_close(first, proof(first)).challenge
    assert origin_contested((closed, second))
    one = Observation("repo/a", "2026-10-25T00:00:00Z", ObservationState.TRANSIENT_FAILURE)
    assert one.observation_id == Observation("repo/a", "2026-10-25T00:00:00Z",
                                             ObservationState.TRANSIENT_FAILURE).observation_id


def test_publication_time_with_earlier_receipt_and_closure_chronology():
    # Earlier receipt / later publication rounds through trusted resolver
    values = challenge_values(verified_at_utc="2026-10-25T12:00:00Z")
    resolver = Resolver()
    receipt = VerificationReceipt(
        "open-receipt-early", draft_context(values), "reproduction-transcript",
        values["verifier_id"], "reproducer", values["contributor_id"], "passed",
        "reproducible-test", "2", "PASS: 12/12", "output-sha256", "https://example.org/receipt/open",
        values["contributor_notice_ref"], "2026-10-25T11:00:00Z"
    )
    resolver.receipts[receipt.receipt_id] = receipt
    challenge = open_challenge(**values, receipt_resolver=resolver,
                               verification_receipt_id=receipt.receipt_id)
    assert challenge.created_at_utc == "2026-10-25T12:00:00Z"
    assert challenge.history[0].at_utc == "2026-10-25T12:00:00Z"
    assert resolver.receipts[receipt.receipt_id].verified_at_utc == "2026-10-25T11:00:00Z"
    validate_challenge_history(challenge, resolver)

    # Equal-time valid
    values_eq = challenge_values(verified_at_utc="2026-10-25T12:00:00Z")
    receipt_eq = replace(receipt, receipt_id="open-receipt-equal",
                         context_digest=draft_context(values_eq),
                         verified_at_utc="2026-10-25T12:00:00Z")
    resolver.receipts[receipt_eq.receipt_id] = receipt_eq
    challenge_eq = open_challenge(**values_eq, receipt_resolver=resolver,
                                  verification_receipt_id=receipt_eq.receipt_id)
    assert challenge_eq.created_at_utc == "2026-10-25T12:00:00Z"
    assert challenge_eq.history[0].at_utc == "2026-10-25T12:00:00Z"
    validate_challenge_history(challenge_eq, resolver)

    # Future-receipt rejected
    values_fut = challenge_values(verified_at_utc="2026-10-25T12:00:00Z")
    receipt_fut = replace(receipt, receipt_id="open-receipt-future",
                          context_digest=draft_context(values_fut),
                          verified_at_utc="2026-10-25T12:00:01Z")
    resolver.receipts[receipt_fut.receipt_id] = receipt_fut
    with pytest.raises(ValueError, match="after asserted event time"):
        open_challenge(**values_fut, receipt_resolver=resolver,
                       verification_receipt_id=receipt_fut.receipt_id)

    # Closure chronology unchanged
    early = resolve_close(challenge, proof(challenge), resolver=resolver,
                          closed_at="2026-10-25T11:30:00Z")
    assert early.disposition is ClosureDisposition.CLASS_C
    assert "closure cannot predate opening or proof verification" in early.reason

    closed = resolve_close(challenge, proof(challenge), resolver=resolver,
                           closed_at="2026-10-27T00:00:00Z")
    assert closed.disposition is ClosureDisposition.CLOSED
    validate_challenge_history(closed.challenge, resolver)

