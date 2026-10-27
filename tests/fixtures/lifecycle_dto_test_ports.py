"""Disposable synthetic in-process ports; never installed in production."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'src'))
sys.path.insert(0, str(root / 'tests'))
from test_challenge_domain import opened, proof, resolve_close
from gaia_cli.lifecycleProjection import CanonicalConsequence, LifecyclePorts, produce_lifecycle


class SyntheticSource:
    def __init__(self, values):
        self.values = values

    def challenges_for(self, subject):
        return self.values


class SyntheticConsequenceSource:
    def __init__(self, consequence):
        self.consequence = consequence

    def consequence_for(self, subject):
        return self.consequence


def make(material=True, closed=False, kind=None, pending=False):
    challenge, resolver = opened(material_to_origin=material)
    if closed:
        challenge = resolve_close(challenge, proof(challenge), resolver=resolver).challenge
    entry = {'id': challenge.subject_id, 'genericSkillRef': 'synthetic-bucket',
             'level': '3★', 'trustMagnitude': 72}
    consequence = CanonicalConsequence(entry['id'], entry['genericSkillRef'], kind, 3, 72,
                                       'author', pending) if kind else None
    ports = LifecyclePorts(SyntheticSource((challenge,)), resolver,
                           SyntheticConsequenceSource(consequence) if consequence else None)
    entry['trustLifecycle'] = produce_lifecycle(entry, ports)
    return entry


if __name__ == '__main__':
    print(json.dumps({'scoped': make(False, kind='current-baseline'),
                      'material': make(True, kind='approved-decision'),
                      'resolved': make(True, True, 'approved-decision', True),
                      'unknown': make(True)}))
