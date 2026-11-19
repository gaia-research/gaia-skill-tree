"""Offline contract/routing proofs for the diagnostic-only permission A/B.

The small evaluator covers only the expressions used here, including GitHub's
loose scalar equality and implicit needs-success gate; not a runner emulator.
No network, token, collector change or live workflow execution is needed.
"""
import ast
import copy
from functools import lru_cache
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace

import yaml


WORKFLOW = Path('.github/workflows/upstream-watcher.yml')
BASE = '1a57a915fe02d45157da9e717fa7149a9f9e35d1'
ARMS = ('permission-ab-control', 'permission-ab-treatment')


@lru_cache(maxsize=1)
def workflow():
    return yaml.safe_load(WORKFLOW.read_text())


def ghEqual(left, right):
    if type(left) is type(right):
        return left == right

    def number(value):
        if value is None or value == '':
            return 0
        if isinstance(value, bool):
            return int(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float('nan')

    return number(left) == number(right)


class Equality(ast.NodeTransformer):
    def visit_Compare(self, node):
        assert len(node.ops) == 1
        call = ast.Call(func=ast.Name(id='ghEqual', ctx=ast.Load()),
                        args=[node.left, node.comparators[0]], keywords=[])
        if isinstance(node.ops[0], ast.NotEq):
            return ast.UnaryOp(op=ast.Not(), operand=call)
        assert isinstance(node.ops[0], ast.Eq)
        return call


def condition(expression, inputs, event='workflow_dispatch', status='success'):
    expression = expression.removeprefix('${{').removesuffix('}}').strip()
    expression = expression.replace('&&', ' and ').replace('||', ' or ')
    expression = re.sub(r'!(?!=)', ' not ', expression)
    expression = re.sub(r'\btrue\b', 'True', expression)
    # Preserve the JSON literal string compared with toJSON(...).
    expression = expression.replace("'True'", "'true'")
    tree = ast.fix_missing_locations(Equality().visit(ast.parse(expression.strip(), mode='eval')))
    return bool(eval(compile(tree, '<workflow-condition>', 'eval'), {'__builtins__': {}}, {
        'ghEqual': ghEqual, 'inputs': SimpleNamespace(**inputs),
        'github': SimpleNamespace(event_name=event, ref='refs/heads/main',
                                  event=SimpleNamespace(repository=SimpleNamespace(default_branch='main'))),
        'vars': SimpleNamespace(GAIA_CHALLENGE_WATCH_ENABLED='true'),
        'format': lambda pattern, value: pattern.format(value),
        'toJSON': lambda value: json.dumps(value, separators=(',', ':')),
        'always': lambda: True, 'success': lambda: status == 'success',
    }))


def selectedJobs(inputs, event='workflow_dispatch', controlStatus='success'):
    jobs = workflow()['jobs']
    selected = {}
    for name, job in jobs.items():
        # No explicit status override is present on challenge-watch. Skipped or
        # failed watcher therefore fails its implicit needs-success prerequisite.
        dependencies = job.get('needs', [])
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        prerequisite = all(selected.get(dep, False) for dep in dependencies)
        if name == 'permission-ab-treatment' and 'permission-ab-control' in dependencies:
            prerequisite = prerequisite and controlStatus == 'success'
        selected[name] = prerequisite and condition(job['if'], inputs, event)
    return selected


def defaults():
    doc = workflow()
    trigger = doc.get('on', doc.get(True))
    return {name: item['default'] for name, item in trigger['workflow_dispatch']['inputs'].items()}


def test_ordinary_bodies_and_trigger_bytes_unchanged_except_authorized_read_scope():
    baselineText = subprocess.check_output(['git', 'show', f'{BASE}:{WORKFLOW}'], text=True)
    currentText = WORKFLOW.read_text()
    baseline = yaml.safe_load(baselineText)
    current = workflow()
    # Byte equality for global permission blob and entire challenge job, which
    # alone has its preexisting contents-write permission override.
    def permissionBlob(text):
        return text[text.index('\npermissions:'):text.index('\njobs:')]
    assert permissionBlob(currentText) == permissionBlob(baselineText)
    def watcherBlob(text):
        return text[text.index('  watcher:'):text.index('  metadata-probe:')]
    pinFetchText = (
        '      - name: Fetch pinned historical authority commit\n'
        '        run: |\n'
        '          set -euo pipefail\n'
        '          COMMIT=$(python3 -c \'import json; print(json.load(open("scripts/upstream_watcher/legacy_plan_policy.json"))["historicalAuthorityCommit"])\')\n'
        '          if ! git cat-file -e "${COMMIT}^{commit}" 2>/dev/null; then\n'
        '            git fetch --depth=1 --no-tags origin "$COMMIT"\n'
        '          fi\n'
        '          git cat-file -e "${COMMIT}^{commit}"\n'
        '\n'
    )
    assert currentText.count(pinFetchText) == 1
    assert watcherBlob(currentText).replace(
        'inputs.metadata_probe != true && !inputs.permission_ab',
        'inputs.metadata_probe != true').replace(
            '    permissions:\n      issues: write\n      contents: read\n      pull-requests: read\n',
            '').replace(pinFetchText, '', 1) == watcherBlob(baselineText)
    assert currentText[currentText.index('  challenge-watch:'):] == baselineText[baselineText.index('  challenge-watch:'):]
    for name in ('watcher', 'challenge-watch', 'metadata-probe'):
        before, after = copy.deepcopy(baseline['jobs'][name]), copy.deepcopy(current['jobs'][name])
        if name != 'challenge-watch':
            before.pop('if')
            after.pop('if')
        if name == 'watcher':
            assert 'permissions' not in before
            assert after.pop('permissions') == {
                'issues': 'write', 'contents': 'read', 'pull-requests': 'read',
            }
            assert after['steps'].pop(4)['name'] == 'Fetch pinned historical authority commit'
        assert before == after
        assert before.get('permissions') == after.get('permissions')
    oldTrigger = baseline.get('on', baseline.get(True))
    newTrigger = copy.deepcopy(current.get('on', current.get(True)))
    ab = newTrigger['workflow_dispatch']['inputs'].pop('permission_ab')
    assert ab['type'] == 'boolean' and ab['default'] is False
    assert newTrigger == oldTrigger
    assert current['concurrency'] == baseline['concurrency'] == 'upstream-watcher'
    assert set(current['jobs']) == set(baseline['jobs']) | set(ARMS)


def test_exact_permission_differential_same_pinned_code_and_isolated_artifacts():
    doc = workflow()
    control, treatment = (copy.deepcopy(doc['jobs'][name]) for name in ARMS)
    assert doc['permissions'] == control['permissions'] == {'issues': 'write', 'contents': 'read'}
    assert treatment['permissions'] == {**control['permissions'], 'pull-requests': 'read'}
    assert treatment['permissions'].pop('pull-requests') == 'read'
    for job, arm in ((control, 'CONTROL'), (treatment, 'TREATMENT')):
        assert 'needs' not in job and 'strategy' not in job and 'continue-on-error' not in job
        assert 'outputs' not in job and 'environment' not in job
        assert job['timeout-minutes'] == 6
        checkout, setup, collect, upload = job['steps']
        assert checkout['with'] == {
            'repository': '${{ github.repository }}', 'ref': '${{ github.sha }}',
            'fetch-depth': 1, 'persist-credentials': False,
        }
        assert checkout['uses'] == 'actions/checkout@v4'
        assert setup['uses'] == 'actions/setup-python@v5'
        assert collect == {
            'name': 'Read diagnostic metadata only',
            'env': {'GH_TOKEN': '${{ secrets.GITHUB_TOKEN }}'},
            'run': 'python -m scripts.upstream_watcher.metadata_probe',
        }
        assert upload['uses'] == 'actions/upload-artifact@v4'
        assert upload['if'] == 'always()'
        assert upload['with'] == {
            'name': f'DIAGNOSTIC-upstream-metadata-permission-ab-{arm}',
            'path': 'generated-output/diagnostic-upstream-metadata.json',
            'if-no-files-found': 'error', 'retention-days': 7,
        }
        # Remove only human-readable arm and isolated artifact labels.
        job.pop('name')
        upload['with'].pop('name')
    assert control == treatment
    # No global/job env, auth fallback, PAT, token minting/sharing, extra step,
    # production command, acceptance/winner job, or permission escalation.
    for job in (control, treatment):
        assert set(job) == {'if', 'runs-on', 'timeout-minutes', 'permissions', 'steps'}


def test_authorized_ordinary_scope_is_only_workflow_delta_from_paired_receipt_head():
    baselineText = subprocess.check_output([
        'git', 'show', f'ef05149256f6091429f4f618bccaade3c3da7ee1:{WORKFLOW}',
    ], text=True)
    currentText = WORKFLOW.read_text()
    baseline = yaml.safe_load(baselineText)
    current = workflow()
    ordinary = current['jobs']['watcher']
    # Explicit maps replace inherited defaults: retain contents/issue access,
    # add only PR READ for mixed issue/PR inventory; metadata read is implicit.
    assert ordinary['permissions'] == {
        'issues': 'write', 'contents': 'read', 'pull-requests': 'read',
    }
    assert 'permissions' not in baseline['jobs']['watcher']
    readJobs = {name for name, job in current['jobs'].items()
                if job.get('permissions', current['permissions']).get('pull-requests') == 'read'}
    assert readJobs == {'watcher', 'permission-ab-treatment'}
    assert current['permissions'] == baseline['permissions'] == {
        'issues': 'write', 'contents': 'read',
    }
    permissionText = ('    permissions:\n      issues: write\n'
                      '      contents: read\n      pull-requests: read\n')
    pinFetchText = (
        '      - name: Fetch pinned historical authority commit\n'
        '        run: |\n'
        '          set -euo pipefail\n'
        '          COMMIT=$(python3 -c \'import json; print(json.load(open("scripts/upstream_watcher/legacy_plan_policy.json"))["historicalAuthorityCommit"])\')\n'
        '          if ! git cat-file -e "${COMMIT}^{commit}" 2>/dev/null; then\n'
        '            git fetch --depth=1 --no-tags origin "$COMMIT"\n'
        '          fi\n'
        '          git cat-file -e "${COMMIT}^{commit}"\n'
        '\n'
    )
    assert currentText.count(permissionText) == 2  # ordinary + existing treatment
    assert currentText.count(pinFetchText) == 1  # ordinary watcher read-only pin fetch only
    # Stronger than parsed equality: ALL routing, commands, other jobs, comments,
    # global permissions and inputs stay byte-identical, except these two exact blocks.
    assert currentText.replace(permissionText, '', 1).replace(pinFetchText, '', 1) == baselineText


def test_normal_acceptance_flags_invoke_existing_batch_dry_run_only(tmp_path):
    inputs = defaults()
    inputs.update(apply=False, metadata_probe=False, permission_ab=False,
                  child_mode='batch', staging='off', staging_bootstrap=False,
                  challenge_watch=False, challenge_shadow=False,
                  skill_id='', challenge_input='', escalate_candidate='')
    assert {name for name, selected in selectedJobs(inputs).items() if selected} == {'watcher'}
    step = next(step for step in workflow()['jobs']['watcher']['steps']
                if step['name'] == 'Run upstream watcher')
    assert step['env']['GH_TOKEN'] == '${{ secrets.GITHUB_TOKEN }}'
    # Execute only the existing argument builder with a shell function stub:
    # NEVER invoke Python/collector/API, or provide a credential. A synthetic
    # weekly repo setting proves explicit staging=off still bypasses staging.
    result = subprocess.run(['bash', '-c',
                             'python() { printf "%s\\n" "$@"; };\n' + step['run']],
                            cwd=tmp_path, env={
                                'PATH': os.environ['PATH'],
                                'INPUT_APPLY': 'false', 'EVENT_NAME': 'workflow_dispatch',
                                'INPUT_CHILD_MODE': 'batch', 'INPUT_STAGING': 'off',
                                'INPUT_STAGING_BOOTSTRAP': 'false', 'INPUT_ESCALATE': '',
                                'INPUT_SKILL_ID': '', 'STAGING_VAR': 'weekly',
                                'STAGING_INITIALIZED': '', 'V2_ENABLED': '',
                            }, text=True, capture_output=True, check=True)
    assert result.stdout.splitlines() == [
        'scripts/upstream_watcher/watcher.py', '--child-mode', 'batch', '--dry-run',
        '--report', 'generated-output/upstream-watcher-report.json',
    ]
    assert result.stderr == ''


def test_ab_true_full_other_input_crossproduct_skips_all_ordinary_paths():
    # All other boolean combinations, choice values, and empty/nonempty filters:
    # even apply/escalation/challenge/staging/repo variable opt-ins cannot write.
    flags = ('metadata_probe', 'apply', 'challenge_watch', 'challenge_shadow', 'staging_bootstrap')
    for booleans, mode, staging, skill, challenge, escalation in itertools.product(
            itertools.product((False, True), repeat=len(flags)),
            ('fanout', 'batch'), ('inherit', 'off', 'weekly'),
            ('', 'owner/suite'), ('', 'input.json'), ('', 'owner/repo:row')):
        inputs = defaults()
        inputs.update(zip(flags, booleans))
        inputs.update(permission_ab=True, child_mode=mode, staging=staging,
                      skill_id=skill, challenge_input=challenge, escalate_candidate=escalation)
        selected = selectedJobs(inputs)
        assert {name for name, value in selected.items() if value} == set(ARMS)


def test_default_schedule_and_standalone_metadata_routing_preserved():
    inputs = defaults()
    assert {name for name, value in selectedJobs(inputs).items() if value} == {'watcher'}
    assert {name for name, value in selectedJobs(inputs, 'schedule').items() if value} == {'watcher', 'challenge-watch'}
    # Scheduled events do not have inputs: absent values resolve to null. Existing
    # configured challenge behavior remains active; diagnostic arms stay off.
    absent = dict.fromkeys(inputs)
    assert {name for name, value in selectedJobs(absent, 'schedule').items() if value} == {'watcher', 'challenge-watch'}
    inputs['metadata_probe'] = True
    for apply, challenge in itertools.product((False, True), repeat=2):
        inputs.update(apply=apply, challenge_watch=challenge)
        assert {name for name, value in selectedJobs(inputs).items() if value} == {'metadata-probe'}
    # Even a synthetic schedule carrying A/B=true is fail-closed, not diagnostic.
    inputs['permission_ab'] = True
    assert not any(selectedJobs(inputs, 'schedule').values())


def test_native_boolean_not_event_string_truthiness_and_malformed_fail_closed():
    inputs = defaults()
    for malformed in ('true', 'false', '1', '0', 'garbage'):
        inputs['permission_ab'] = malformed
        assert not any(selectedJobs(inputs).values())
    inputs['permission_ab'] = True
    assert all(selectedJobs(inputs)[name] for name in ARMS)
    for absent in (False, None, ''):
        inputs['permission_ab'] = absent
        assert selectedJobs(inputs)['watcher']
    assert 'github.event.inputs' not in WORKFLOW.read_text()


def test_exit3_still_uploads_both_and_treatment_has_no_success_dependency():
    inputs = defaults()
    inputs['permission_ab'] = True
    for controlStatus in ('success', 'failure', 'cancelled'):
        selected = selectedJobs(inputs, controlStatus=controlStatus)
        assert selected['permission-ab-treatment']
        for name in ARMS:
            upload = workflow()['jobs'][name]['steps'][-1]
            # A nonzero collector exit (including 3) makes job failure, but the
            # upload step remains selected. Runner/service failure may still
            # prevent delivery; no fixture claims otherwise.
            assert condition(upload['if'], inputs, status='failure')
