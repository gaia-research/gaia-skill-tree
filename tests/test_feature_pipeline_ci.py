"""Run shipped gh-2.46-compatible CI helper with synthetic API responses."""
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.agents/skills/fp-iterate/scripts/ci-poll.sh'
TIP = 'a' * 40


def poll(tmp_path, checks, status=0, before=TIP, after=TIP, after_status=0, options=()):
    mock = tmp_path / 'gh'
    mock.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
p=pathlib.Path(os.environ['MOCK_DIR'])
with (p/'argv').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1:3]==['pr','view']:
    fields=sys.argv[sys.argv.index('--json')+1]
    if fields=='headRefOid,statusCheckRollup':
        print(json.dumps({'headRefOid':os.environ['BEFORE'],'statusCheckRollup':json.loads(os.environ['CHECKS'])}))
        sys.exit(int(os.environ['STATUS']))
    if fields=='headRefOid':
        print(os.environ['AFTER'])
        sys.exit(int(os.environ['AFTER_STATUS']))
# Reproduce gh 2.46's unsupported checks --json boundary.
print('unknown flag: --json', file=sys.stderr)
sys.exit(1)
''')
    mock.chmod(0o755)
    env = {**os.environ, 'PATH': str(tmp_path) + os.pathsep + os.environ['PATH'],
           'MOCK_DIR': str(tmp_path), 'CHECKS': json.dumps(checks),
           'STATUS': str(status), 'BEFORE': before, 'AFTER': after,
           'AFTER_STATUS': str(after_status)}
    return subprocess.run(['bash', str(SCRIPT), '2098', '--max', '1', '--interval', '0', *options],
                          env=env, text=True, capture_output=True)


def check(conclusion='SUCCESS', status='COMPLETED'):
    return {'__typename': 'CheckRun', 'name': 'synthetic-check',
            'conclusion': conclusion, 'status': status}


def context(state='SUCCESS'):
    return {'__typename': 'StatusContext', 'context': 'synthetic-context', 'state': state}


def test_all_reported_checks_at_stable_head_use_supported_gh_surface(tmp_path):
    result = poll(tmp_path, [check(), check('SKIPPED'), check('NEUTRAL'), context()])
    assert result.returncode == 0, result.stderr
    assert TIP in result.stdout and 'all reported checks' in result.stdout
    calls = [json.loads(line) for line in (tmp_path / 'argv').read_text().splitlines()]
    assert len(calls) == 2
    assert calls[0] == ['pr', 'view', '2098', '--json', 'headRefOid,statusCheckRollup']
    assert calls[1] == ['pr', 'view', '2098', '--json', 'headRefOid', '--jq', '.headRefOid']


@pytest.mark.parametrize('failed', [check(c) for c in [
    'FAILURE', 'CANCELLED', 'TIMED_OUT', 'ACTION_REQUIRED', 'STARTUP_FAILURE', 'STALE',
]] + [context('FAILURE'), context('ERROR')])
def test_real_completed_failures_are_never_hidden_as_api_retries(tmp_path, failed):
    result = poll(tmp_path, [check(), failed])
    assert result.returncode == 2
    assert 'synthetic-' in result.stdout


@pytest.mark.parametrize('checks', [
    [], *[[check('', state)] for state in ['QUEUED', 'REQUESTED', 'EXPECTED', 'IN_PROGRESS', 'WAITING', 'PENDING']],
    [check('SUCCESS', 'IN_PROGRESS')],
    [context('EXPECTED')], [context('PENDING')], [context('UNKNOWN')],
    [check('FUTURE_UNKNOWN')], [{'name': 'missing-type', 'state': 'SUCCESS'}],
    [None], {'message': 'api unavailable'},
])
def test_empty_pending_unknown_or_malformed_ci_is_never_green(tmp_path, checks):
    assert poll(tmp_path, checks).returncode == 1


@pytest.mark.parametrize('status', [1, 4, 8])
def test_unsupported_auth_or_api_errors_are_diagnostic(tmp_path, status):
    result = poll(tmp_path, [check()], status=status)
    assert result.returncode == 1
    assert 'CI inspection error' in result.stderr and f'exited {status}' in result.stderr
    assert 'authentication' in result.stderr


@pytest.mark.parametrize(('before', 'after', 'after_status'), [
    (TIP, 'b' * 40, 0), ('', '', 0), (TIP, TIP, 4),
])
def test_moved_missing_or_unreadable_head_cannot_be_green(tmp_path, before, after, after_status):
    assert poll(tmp_path, [check()], before=before, after=after,
                after_status=after_status).returncode == 1


@pytest.mark.parametrize('options', [('--max', '0'), ('--max', '101'),
                                     ('--interval', '61'), ('--max',), ('--wat', '1')])
def test_poll_bounds_are_validated_before_network_calls(tmp_path, options):
    assert poll(tmp_path, [check()], options=options).returncode == 3
    assert not (tmp_path / 'argv').exists()
