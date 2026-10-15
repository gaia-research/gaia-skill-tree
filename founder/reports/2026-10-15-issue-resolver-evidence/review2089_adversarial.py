"""Historical independent review probe; see adjacent README before running."""
"""Independent synthetic tests; no branch data or remote calls are touched."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from gaia_cli.intakeAdapter import _canonicalDigest, buildIntakeYaml, validateL4Resolution, validateIntakeIdentities
from gaia_cli.commands.pushFromFile import _load_yaml_file, build_from_file_batch
from gaia_cli.prefill import buildGenericSnapshot
from scripts.validate_intake import validate_intake

ROOT = Path(os.environ.get('GAIA_REVIEW_REPO', '.')).resolve()
spec = importlib.util.spec_from_file_location('independent_packet_validator', ROOT / '.agents/skills/gaia-curate/scripts/validate_discovery_packet.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

class Review2089(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='review2089-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'registry').mkdir()
        self.skills = [dict(id=s, name=s.title(), description='Synthetic generic capability for independent review.', type='basic', prerequisites=[]) for s in ('retrieved-skill', 'outside-skill')]
        (self.root / 'registry/gaia.json').write_text(json.dumps({'skills': self.skills}))
        self.trusted = buildGenericSnapshot(str(self.root))['generics']
        opts = [dict(genericId='retrieved-skill', similarity=.99, matchTier='strong', rationale='Synthetic shortlist hint')]
        source = dict(canonicalUrl='https://github.com/example/fixture/blob/main/SKILL.md', sourceLane='source-repository', hostRepository='https://github.com/example/fixture', fetchedAt='2026-10-15T00:00:00Z', contentSha256='a'*64, frontmatter=dict(name='Synthetic Fixture', description='Independent synthetic source.'))
        self.packet = dict(contractVersion='discovery-packet-v2', candidateId='example/fixture', lifecycle=['discovered','fetched','parsed','normalized','deduped','mapped','review-ready'], artifactGate='valid-skill', source=source, normalized=dict(name='Synthetic Fixture', description='Independent synthetic source.'), exactDedupe=dict(matched=False), flags=[], mappingOptions=opts, genericSnapshot=dict(capturedAt='2026-10-15T00:00:00Z', command='gaia dev list --generic --json', generics=self.trusted, contentSha256=_canonicalDigest(self.trusted), mappingOptionsSha256=_canonicalDigest(opts)), decision=dict(value='MAP', reasonCode='L4_RATIFIED_MAP', genericId='outside-skill'))
        self.packet['l4Resolution'] = dict(status='approved', generic=copy.deepcopy(self.skills[1]), named=dict(contributor='example', skillName='fixture'), skillFileUrl=source['canonicalUrl'], humanReview=dict(reviewedBy='forged-human', approvalRef='attacker-invented-reference', reviewedAt='invented-time', rationale='attacker-invented-rationale', humanOverride=True, operatorOverride=False, assessmentPath=str(self.root/'never-existed.json'), assessmentReceiptDigest='b'*64, attestation='attacker claims a human approved'))

    def load(self, packet):
        path = self.root/'packet.json'
        path.write_text(json.dumps(packet))
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            return _load_yaml_file(str(path))
        finally:
            os.chdir(previous)

    def row(self, name='first', generic='new-skill', contributor='example'):
        return dict(id=generic,name='Synthetic Generic',type='basic',description='Independent shared generic definition.',prerequisites=[],candidateId=f'example/{name}',named=dict(contributor=contributor,skill_name=name,links_github=f'https://github.com/example/{name}/blob/main/SKILL.md'),evidence=[dict(grade='C',type='repo',url=f'https://github.com/example/{name}')])

    def test_forged_outside_topk_attestation_is_accepted(self):
        # Repro of a defect, assertions deliberately record actual acceptance.
        self.assertEqual(validateL4Resolution(self.packet, True, self.trusted), [])
        self.assertEqual(validator.validate_packet(self.packet, self.trusted), [])
        adapted, error = self.load(self.packet)
        self.assertIsNone(error)
        self.assertEqual(adapted['skills'][0]['mapsToGeneric'], 'outside-skill')
        batch, errors = build_from_file_batch(adapted['skills'], {'gaiaUser':'agent'}, str(self.root), 'example/fixture', curationHandoff=adapted['curationHandoff'])
        self.assertEqual(errors, [])
        self.assertEqual(batch['proposedSkills'][0]['id'], 'outside-skill')

    def test_forgery_still_accepted_with_fabricated_local_receipt(self):
        receipt = dict(candidateId=self.packet['candidateId'], candidateSourceDigest=self.packet['source']['contentSha256'])
        path = self.root/'fabricated.json'
        path.write_text(json.dumps(receipt))
        self.packet['l4Resolution']['humanReview'].update(assessmentPath=str(path), assessmentReceiptDigest=_canonicalDigest(receipt))
        self.assertEqual(validateL4Resolution(self.packet, True, self.trusted), [])
        self.assertIsNone(self.load(self.packet)[1])

    def test_mixed_case_contributor_survives_push(self):
        self.packet['l4Resolution']['named']['contributor']='Hikari9'
        self.assertEqual(validateL4Resolution(self.packet, True, self.trusted), [])
        adapted,error=self.load(self.packet)
        self.assertIsNone(error)
        batch,errors=build_from_file_batch(adapted['skills'], {'gaiaUser':'agent'},str(self.root),'example/fixture')
        self.assertEqual(errors, [])
        self.assertEqual(batch['proposedSkills'][0]['named']['contributor'],'Hikari9')

    def test_missing_attestation_is_rejected(self):
        del self.packet['l4Resolution']['humanReview']
        self.assertTrue(validateL4Resolution(self.packet, True, self.trusted))
        self.assertTrue(validator.validate_packet(self.packet, self.trusted))

    def test_allow_stale_is_rejected(self):
        self.packet['retrieval']={'allowStale':True}
        self.assertTrue(validateL4Resolution(self.packet, True, self.trusted))
        self.assertIn('UNTRUSTED_RETRIEVAL',validator.validate_packet(self.packet,self.trusted))

    def test_manual_vector_is_rejected(self):
        self.packet['retrieval']={'vectorSource':'attacker'}
        self.assertTrue(validateL4Resolution(self.packet, True, self.trusted))
        self.assertIn('UNTRUSTED_RETRIEVAL',validator.validate_packet(self.packet,self.trusted))

    def test_stale_catalog_is_rejected(self):
        trusted=self.trusted[:-1]
        self.assertTrue(validateL4Resolution(self.packet,True,trusted))
        self.assertIn('INVALID_GENERIC_SNAPSHOT',validator.validate_packet(self.packet,trusted))

    def test_distinct_named_shared_generic_accepted(self):
        self.assertEqual(validateIntakeIdentities([self.row(),self.row('second')]),[])

    def test_same_identity_different_generic_rejected(self):
        self.assertTrue(validateIntakeIdentities([self.row(),self.row(generic='other-generic')]))

    def test_case_variant_named_identity_rejected(self):
        self.assertTrue(validateIntakeIdentities([self.row(),self.row(contributor='EXAMPLE')]))

    def test_conflicting_generic_definition_rejected(self):
        second=self.row('second')
        second['description']='A completely conflicting definition.'
        self.assertTrue(validateIntakeIdentities([self.row(),second]))

    def test_duplicate_candidate_rejected(self):
        second=self.row('second')
        second['candidateId']=self.row()['candidateId']
        self.assertTrue(validateIntakeIdentities([self.row(),second]))

    def test_unaccepted_generic_across_batches_rejected(self):
        directory=self.root/'registry-for-review/skill-batches'
        directory.mkdir(parents=True)
        for i,row in enumerate([self.row(),self.row('second')]):
            batch=dict(batchId=f'batch-{i}',userId='synthetic',sourceRepo='example/fixture',generatedAt='2026-10-15T00:00:00Z',knownSkills=[],proposedSkills=[row],similarity=[])
            (directory/f'{i}.json').write_text(json.dumps(batch))
        errors,_,_=validate_intake(str(directory.parent),str(self.root/'registry/gaia.json'),str(ROOT/'registry/schema/skillBatch.schema.json'))
        self.assertTrue(any('Duplicate proposed skill' in e for e in errors),errors)

if __name__=='__main__':
    unittest.main(verbosity=2)
