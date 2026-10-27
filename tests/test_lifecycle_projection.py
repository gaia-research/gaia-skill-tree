"""Synthetic, in-process ports only; these fixtures are not an issuer."""
from dataclasses import replace

from gaia_cli.lifecycleProjection import project_challenges
from test_challenge_domain import opened, proof, resolve_close


class SyntheticChallengeSource:
    def __init__(self, challenges):
        self.challenges = challenges

    def challenges_for(self, subject_id):
        return self.challenges


def test_unavailable_never_becomes_empty_verified_set():
    challenge, resolver = opened()
    source = SyntheticChallengeSource((challenge,))
    assert project_challenges(challenge.subject_id) is None
    assert project_challenges(challenge.subject_id, source) is None
    assert project_challenges(challenge.subject_id, {}, resolver) is None
    assert project_challenges(challenge.subject_id, SyntheticChallengeSource(None), resolver) is None
    empty = project_challenges(challenge.subject_id, SyntheticChallengeSource(()), resolver)
    assert empty is not None and empty.challenges == ()


def test_scoped_and_multiple_material_challenges_preserve_history():
    first, resolver = opened()
    scoped, resolver2 = opened(claim_id='claim-2', behavior_id='behavior-y',
                               claim='Different scoped claim', material_to_origin=False)
    scoped_result = project_challenges(scoped.subject_id, SyntheticChallengeSource((scoped,)), resolver2)
    assert scoped_result is not None and not scoped_result.material_origin_contested
    second, resolver3 = opened(claim_id='claim-3', behavior_id='behavior-z', claim='Another claim')
    # Synthetic resolver IDs are scoped by challenge; rename the second receipt
    # and bind its event using the domain's canonical digest helper.
    from gaia_cli.challengeDomain import _canonical, _digest
    receipt = replace(resolver3.receipts['open-receipt'], receipt_id='second-receipt')
    event = replace(second.history[0], receipt_id=receipt.receipt_id,
                    receipt_digest=_digest(_canonical(receipt)))
    second = replace(second, history=(event,), history_digest='')
    resolver.receipts[receipt.receipt_id] = receipt
    both = project_challenges(first.subject_id, SyntheticChallengeSource((first, second)), resolver)
    assert both is not None and both.material_origin_contested
    closed = resolve_close(first, proof(first), resolver=resolver).challenge
    still_contested = project_challenges(first.subject_id, SyntheticChallengeSource((closed, second)), resolver)
    assert still_contested is not None and still_contested.material_origin_contested
    projected = project_challenges(first.subject_id, SyntheticChallengeSource((closed,)), resolver)
    assert projected is not None and not projected.material_origin_contested
    assert projected.challenges[0].history[0] == first.history[0]
    assert len(projected.challenges[0].history) == 2
    assert not hasattr(projected, 'approved_standing')


def test_foreign_duplicate_malformed_and_forged_receipts_fail_closed():
    challenge, resolver = opened()
    source = lambda entries: SyntheticChallengeSource(entries)
    assert project_challenges('other/skill', source((challenge,)), resolver) is None
    assert project_challenges(challenge.subject_id, source((challenge, challenge)), resolver) is None
    assert project_challenges(challenge.subject_id, source([challenge]), resolver) is None
    assert project_challenges(challenge.subject_id, source(({'challenge_id': challenge.challenge_id},)), resolver) is None
    original = resolver.receipts['open-receipt']
    resolver.receipts['open-receipt'] = replace(original, context_digest='forged')
    assert project_challenges(challenge.subject_id, source((challenge,)), resolver) is None
