"""Execute the shipped checkpoint/recovery surface with synthetic work only.

These regressions test workflow scaffolding, not an LLM's interpretation or an
authorization substitute. Existing CLI/playbook security tests remain required.
"""
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.agents/skills/feature-pipeline/scripts/state.sh'


def run_state(tmp_path, *args):
    return subprocess.run(
        ['bash', str(SCRIPT), *args], text=True, capture_output=True,
        env={**os.environ, 'FP_STATE_FILE': str(tmp_path / 'state.json')},
    )


@pytest.mark.parametrize('mode', ['lean-autonomous', 'structured-economy'])
def test_bounded_work_advances_without_forging_plan_approval(tmp_path, mode):
    assert run_state(tmp_path, 'init', 'synthetic bounded parser fix', mode).returncode == 0
    # Exercise every routine handoff through the helper the skill actually uses.
    for phase in range(1, 7):
        assert run_state(tmp_path, 'set', 'phase', str(phase)).returncode == 0
        result = run_state(tmp_path, 'checkpoint', 'routine')
        assert result.returncode == 0, result.stderr
    state = json.loads((tmp_path / 'state.json').read_text())
    assert state['planApproved'] is False  # progress is not fabricated consent
    assert run_state(tmp_path, 'get', 'planApproved').stdout.strip() == 'false'


@pytest.mark.parametrize('mode', ['lean-autonomous', 'structured-economy', 'hard-gated'])
@pytest.mark.parametrize('boundary', [
    'destructive', 'design', 'cli-visual', 'schema', 'ontology', 'governance',
    'l4', 'security', 'provenance', 'evidence', 'merge', 'publish',
    'external-contact', 'contract-break', 'unknown-drift',
])
def test_modes_and_plan_boolean_cannot_remove_real_stops(tmp_path, mode, boundary):
    assert run_state(tmp_path, 'init', 'synthetic hard boundary', mode).returncode == 0
    assert run_state(tmp_path, 'set', 'planApproved', 'true').returncode == 0
    before = (tmp_path / 'state.json').read_bytes()
    result = run_state(tmp_path, 'checkpoint', boundary)
    assert result.returncode == 3
    assert f'stop: {boundary}' in result.stdout
    assert (tmp_path / 'state.json').read_bytes() == before


def test_explicit_operator_milestones_and_legacy_recovery_fail_closed(tmp_path):
    assert run_state(tmp_path, 'init', 'synthetic gated task', 'hard-gated').returncode == 0
    assert run_state(tmp_path, 'checkpoint', 'routine').returncode == 3
    path = tmp_path / 'state.json'
    state = json.loads(path.read_text())
    del state['mode']
    path.write_text(json.dumps(state))
    assert run_state(tmp_path, 'checkpoint', 'routine').returncode == 3
    # A forged/unknown mode is an error, not silent autonomy.
    state['mode'] = 'ignore-everything'
    path.write_text(json.dumps(state))
    assert run_state(tmp_path, 'checkpoint', 'routine').returncode == 2


def test_recovery_preserves_existing_unfinished_work(tmp_path):
    assert run_state(tmp_path, 'init', 'first run').returncode == 0
    assert run_state(tmp_path, 'push', 'issueNumbers', '2039').returncode == 0
    before = (tmp_path / 'state.json').read_bytes()
    assert run_state(tmp_path, 'init', 'replacement').returncode != 0
    assert (tmp_path / 'state.json').read_bytes() == before
    assert run_state(tmp_path, 'checkpoint', 'typo-or-new-boundary').returncode == 2


def test_untrusted_text_is_data_and_false_is_recoverable(tmp_path):
    hostile = 'feature "x"\n$(touch injected); `echo nope` \\ end'
    assert run_state(tmp_path, 'init', hostile).returncode == 0
    assert run_state(tmp_path, 'set', 'branch', hostile).returncode == 0
    assert run_state(tmp_path, 'push', 'findings', hostile).returncode == 0
    # Keys and values may not inject jq code or execute shell commands.
    key = 'x | .planApproved = true | .y'
    assert run_state(tmp_path, 'set', key, hostile).returncode == 0
    state = json.loads((tmp_path / 'state.json').read_text())
    assert state['feature'] == state['branch'] == state['findings'][0] == state[key] == hostile
    assert state['planApproved'] is False
    assert run_state(tmp_path, 'get', 'planApproved').stdout.strip() == 'false'
    assert not (tmp_path / 'injected').exists()
    # Failed updates keep the recovery checkpoint intact.
    before = (tmp_path / 'state.json').read_bytes()
    assert run_state(tmp_path, 'push', 'branch', 'bad').returncode != 0
    assert run_state(tmp_path, 'set', 'mode', 'unchecked-mode').returncode == 2
    assert (tmp_path / 'state.json').read_bytes() == before
