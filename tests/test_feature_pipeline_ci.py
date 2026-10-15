"""Run the actual CI helper against synthetic gh responses; no network/waits."""
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.agents/skills/fp-iterate/scripts/ci-poll.sh'
TIP = 'a' * 40


def poll(tmp_path, checks, status=0, before=TIP, after=TIP, view_status=0, options=()):
    mock = tmp_path / 'gh'
    # Record argv, use a file counter to distinguish view calls.
    mock.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
p=pathlib.Path(os.environ['MOCK_DIR'])
with (p/'argv').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1:3]==['pr','view']:
    count=p/'count'
    n=int(count.read_text()) if count.exists() else 0
    count.write_text(str(n+1))
    print(os.environ['BEFORE'] if n%2==0 else os.environ['AFTER'])
    sys.exit(int(os.environ['VIEW_STATUS']))
if sys.argv[1:3]==['pr','checks']:
    print(os.environ['CHECKS'])
    sys.exit(int(os.environ['CHECK_STATUS']))
sys.exit(99)
''')
    mock.chmod(0o755)
    env = {**os.environ, 'PATH': str(tmp_path) + os.pathsep + os.environ['PATH'],
           'MOCK_DIR': str(tmp_path), 'CHECKS': json.dumps(checks),
           'CHECK_STATUS': str(status), 'BEFORE': before, 'AFTER': after,
           'VIEW_STATUS': str(view_status)}
    return subprocess.run(['bash', str(SCRIPT), '2098', '--max', '1', '--interval', '0', *options],
                          env=env, text=True, capture_output=True)


def check(bucket, state='SUCCESS'):
    return {'name': 'synthetic-required', 'bucket': bucket, 'state': state}


def test_green_required_checks_are_bound_to_stable_head(tmp_path):
    result = poll(tmp_path, [check('pass'), check('skipping', 'SKIPPED')])
    assert result.returncode == 0, result.stderr
    assert TIP in result.stdout
    calls = [json.loads(line) for line in (tmp_path / 'argv').read_text().splitlines()]
    assert '--required' in calls[1]
    assert calls[0][1] == calls[2][1] == 'view'


@pytest.mark.parametrize(('bucket', 'state'), [('fail', 'FAILURE'), ('cancel', 'CANCELLED')])
def test_gh_failure_exit_is_a_failed_check_not_a_retry(tmp_path, bucket, state):
    result = poll(tmp_path, [check(bucket, state)], status=1)
    assert result.returncode == 2
    assert 'synthetic-required' in result.stdout


@pytest.mark.parametrize(('checks', 'status'), [
    ([], 0), ([check('pending', 'QUEUED')], 8),
    ([check('pending', 'IN_PROGRESS')], 8), ([check('unknown')], 0),
    ([{'name': 'no-bucket', 'state': 'SUCCESS'}], 0),
    ([check('pass')], 1), ([check('pass')], 8), ([check('pass')], 5),
    ({'message': 'api unavailable'}, 1),
])
def test_absent_pending_unknown_or_inconsistent_ci_is_never_green(tmp_path, checks, status):
    assert poll(tmp_path, checks, status=status).returncode == 1


@pytest.mark.parametrize(('before', 'after', 'view_status'), [
    (TIP, 'b' * 40, 0), ('', '', 0), (TIP, TIP, 1),
])
def test_moved_missing_or_unreadable_head_cannot_be_green(tmp_path, before, after, view_status):
    assert poll(tmp_path, [check('pass')], before=before, after=after,
                view_status=view_status).returncode == 1


@pytest.mark.parametrize('options', [('--max', '0'), ('--max', '101'),
                                     ('--interval', '61'), ('--max',), ('--wat', '1')])
def test_poll_bounds_are_validated_before_network_calls(tmp_path, options):
    assert poll(tmp_path, [check('pass')], options=options).returncode == 3
    assert not (tmp_path / 'argv').exists()
