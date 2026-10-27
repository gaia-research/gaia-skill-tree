"""Synthetic, in-process ports only; these fixtures are not an issuer."""
from dataclasses import replace

from gaia_cli.lifecycleProjection import (CanonicalConsequence, LifecyclePorts,
                                          produce_lifecycle, project_challenges)
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
    tampered = replace(challenge)
    object.__setattr__(tampered, 'history_digest', 'forged')
    assert project_challenges(challenge.subject_id, source((tampered,)), resolver) is None
    original = resolver.receipts['open-receipt']
    resolver.receipts['open-receipt'] = replace(original, context_digest='forged')
    assert project_challenges(challenge.subject_id, source((challenge,)), resolver) is None


class SyntheticConsequenceSource:
    def __init__(self, result):
        self.result = result

    def consequence_for(self, subject):
        return self.result


def test_consequence_port_is_distinct_and_does_not_restore_on_closure():
    challenge, resolver = opened()
    closed = resolve_close(challenge, proof(challenge), resolver=resolver).challenge
    entry = {'id': challenge.subject_id, 'genericSkillRef': 'bucket', 'level': '3★', 'trustMagnitude': 72}
    source = SyntheticChallengeSource((closed,))
    assert produce_lifecycle(entry) is None
    assert produce_lifecycle(entry, {'consequence': {'approved': True}}) is None
    unknown = produce_lifecycle(entry, LifecyclePorts(source, resolver))
    assert unknown['consequence'] == {'kind': 'unavailable'}
    assert len(unknown['challenges'][0]['history']) == 2
    assert unknown['challenges'][0]['history'][0]['event_type'] == 'verified-publication'
    baseline = CanonicalConsequence(entry['id'], 'bucket', 'current-baseline', 3, 72, 'author')
    dto = produce_lifecycle(entry, LifecyclePorts(source, resolver, SyntheticConsequenceSource(baseline)))
    assert dto['consequence']['kind'] == 'current-baseline'
    assert dto['consequence']['stars'] == 3
    decision = replace(baseline, kind='approved-decision', recalibration_pending=True)
    dto = produce_lifecycle(entry, LifecyclePorts(source, resolver, SyntheticConsequenceSource(decision)))
    assert dto['consequence']['recalibrationPending'] is True
    for bad in [replace(baseline, subject_id='foreign/skill'), replace(baseline, generic_ref='other'),
                replace(baseline, kind='forged'), replace(baseline, stars=4),
                replace(baseline, tm=float('nan')), replace(baseline, recalibration_pending='false'),
                {'kind': 'approved-decision'}]:
        assert produce_lifecycle(entry, LifecyclePorts(source, resolver, SyntheticConsequenceSource(bad))) is None


def test_consequence_must_agree_with_every_tm_field_the_explorer_can_show():
    # Explorer hero = trustMagnitude || overallTrustMagnitude || trustNumber.
    challenge, resolver = opened()
    source = SyntheticChallengeSource((challenge,))
    base = {'id': challenge.subject_id, 'genericSkillRef': 'bucket', 'level': '3★'}

    def produce(kind, **display):
        consequence = CanonicalConsequence(base['id'], 'bucket', kind, 3, 72, 'author')
        ports = LifecyclePorts(source, resolver, SyntheticConsequenceSource(consequence))
        return produce_lifecycle({**base, **display}, ports)

    for kind in ('current-baseline', 'approved-decision'):
        assert produce(kind, trustMagnitude=72) is not None
        assert produce(kind, trustMagnitude=72, overallTrustMagnitude=72, trustNumber=72.005) is not None
        assert produce(kind) is not None  # no displayed TM: nothing to contradict
        # Original repro: baseline TM 72 accepted next to overallTrustMagnitude 999.
        assert produce(kind, trustMagnitude=72, overallTrustMagnitude=999) is None
        # Hero falls through to overallTrustMagnitude when trustMagnitude is absent or 0.
        assert produce(kind, overallTrustMagnitude=999) is None
        assert produce(kind, trustMagnitude=0, overallTrustMagnitude=999) is None
        assert produce(kind, trustMagnitude=0, overallTrustMagnitude=72) is None
        assert produce(kind, trustNumber=999) is None
        # Unusable displayed values cannot be reconciled and fail closed.
        for bad in (True, 'abc', float('nan'), float('inf'), [72], {'v': 72}):
            assert produce(kind, trustMagnitude=bad) is None
            assert produce(kind, overallTrustMagnitude=bad) is None
        # Numeric strings are what Number() in the browser would display.
        assert produce(kind, trustMagnitude='72') is not None
        assert produce(kind, trustMagnitude='73') is None


def test_named_index_build_strips_spoof_and_only_injects_producer(tmp_path):
    import json
    from scripts.generateNamedIndex import write_index
    challenge, resolver = opened()
    entry = {'id': challenge.subject_id, 'genericSkillRef': 'bucket', 'level': '3★',
             'trustMagnitude': 72, 'origin': True, 'timeline': [{'historic': 'keep'}],
             'trustLifecycle': {'approvedBy': 'forged', 'approved': True}}
    path = tmp_path / 'index.json'
    write_index({'bucket': [entry]}, [], {}, str(path), '2026-01-01')
    published = json.loads(path.read_text())['buckets']['bucket'][0]
    assert 'trustLifecycle' not in published
    assert published['timeline'] == [{'historic': 'keep'}]
    assert published['origin'] is True and published['level'] == '3★'
    entry['trustLifecycle'] = {'contract': 'gaia-trust-lifecycle/v1', 'forged': True}
    ports = LifecyclePorts(SyntheticChallengeSource((challenge,)), resolver)
    write_index({'bucket': [entry]}, [], {}, str(path), '2026-01-01', lifecycle_ports=ports)
    published = json.loads(path.read_text())['buckets']['bucket'][0]
    assert published['trustLifecycle']['contract'] == 'gaia-trust-lifecycle/v1'
    assert published['trustLifecycle']['consequence'] == {'kind': 'unavailable'}
    assert 'forged' not in published['trustLifecycle']
    assert published['timeline'] == [{'historic': 'keep'}]
