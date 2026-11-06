"""Parent-owned real full-corpus replay; no production publication or approval."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = Path.home() / '.gaia-worktrees/yggdrasil-iv-publication-last-mile'
SHA = '93fb731ea8842ef07fd703bb0b58dea944a83a0d'
os.chdir(ROOT)
# Bind parent imports and all children to this exact worktree, not caller CWD.
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
os.environ['PYTHONPATH'] = os.pathsep.join((str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')))
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == SHA
BASE = Path(tempfile.mkdtemp(prefix='yggiv-publication-93.', dir=os.environ['TMPDIR']))
print('PUBLICATION_EVIDENCE_ROOT=' + str(BASE), flush=True)

def inventory():
    result = {}
    for raw in subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).split(b'\0'):
        if not raw:
            continue
        name = os.fsdecode(raw)
        p = ROOT / name
        if p.is_symlink():
            data, kind = os.fsencode(os.readlink(p)), 'symlink'
        elif p.is_file():
            data, kind = p.read_bytes(), 'file'
        else:
            data, kind = b'', 'missing-or-directory'
        result[name] = {'kind': kind, 'sha256': hashlib.sha256(data).hexdigest(), 'mode': p.lstat().st_mode if p.exists() or p.is_symlink() else None}
    return result

before = inventory()
(BASE / 'source-before.json').write_text(json.dumps(before, sort_keys=True))
result = {'sha': SHA, 'interpreter': sys.executable, 'evaluation_at': '2026-10-25T12:00:00Z', 'runs': [], 'success': False, 'state': 'running'}
started = time.monotonic()

def save():
    temporary = BASE / 'verification-result.tmp'
    temporary.write_text(json.dumps(result, sort_keys=True, indent=2))
    os.replace(temporary, BASE / 'verification-result.json')

save()
try:
    import cairosvg
    import publication_context as pc
    import gaia_cli
    assert Path(pc.__file__).resolve() == (ROOT / 'scripts/publication_context.py').resolve()
    assert Path(gaia_cli.__file__).resolve().is_relative_to((ROOT / 'src').resolve())
    manifests = []
    for name in ('replay-one', 'replay-two'):
        out = BASE / name
        assert not out.exists()
        begin = time.monotonic()
        command = [sys.executable, 'scripts/build_docs.py', '--publication-rehearsal', str(out), '--evaluation-at-utc', result['evaluation_at']]
        with (BASE / (name + '.log')).open('w') as log:
            proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        entry = {'name': name, 'root': str(out), 'exit': proc.returncode, 'build_seconds': round(time.monotonic() - begin, 2)}
        result['runs'].append(entry)
        save()
        print('BUILD_RESULT=' + json.dumps(entry), flush=True)
        if proc.returncode:
            raise RuntimeError(name + ' strict builder failed; no certification')
        manifest = json.loads((out / 'publication-artifacts.json').read_text())
        entry.update(snapshotId=manifest['snapshotId'], artifact_count=len(manifest['artifacts']))
        begin = time.monotonic()
        entry['independent_verify'] = pc.verify_outputs(out, manifest['snapshotId'])
        entry['verify_seconds'] = round(time.monotonic() - begin, 2)
        save()
        print('VERIFY_RESULT=' + json.dumps(entry), flush=True)
        assert entry['independent_verify'] and manifest['approval'] == 'unavailable'
        manifests.append(manifest)
    a, b = manifests
    for key in ('snapshotId', 'artifacts', 'artifactClasses'):
        assert a[key] == b[key], 'two-root mismatch: ' + key
    for rel in a['artifacts']:
        assert (BASE / 'replay-one' / rel).read_bytes() == (BASE / 'replay-two' / rel).read_bytes(), rel
    result['two_root_byte_equal'] = True
    save()
    tests = ['tests/test_publication_context.py', 'tests/test_publication_og_coverage.py', 'tests/test_build_docs_api_projection_write.py', 'tests/test_api_projection.py', 'tests/test_trust_magnitude.py', 'tests/test_row_grading.py', 'tests/test_curation_authority_map.py', 'tests/test_benchmark_catalog.py', 'tests/test_trust_freshness.py', 'tests/test_calibrate_evidence_grades.py', 'tests/steward/test_trust_calibration_regression.py', 'tests/test_shadow_evaluation.py']
    assert all((ROOT / path).is_file() for path in tests)
    # Include the author's previously timed-out bounded replay; no exclusion or timeout override.
    with (BASE / 'regressions.log').open('w') as log:
        proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'faulthandler_timeout=60', '--show-capture=no', *tests], stdout=log, stderr=subprocess.STDOUT)
    result['tests_exit'] = proc.returncode
    print('REGRESSIONS_EXIT=' + str(proc.returncode), flush=True)
    if proc.returncode:
        raise RuntimeError('publication/production regressions failed; see regressions.log')
    result['success'] = True
except Exception as exc:
    result['error'] = str(exc)
    print('PUBLICATION_FAILURE=' + repr(exc), flush=True)
finally:
    after = inventory()
    (BASE / 'source-after.json').write_text(json.dumps(after, sort_keys=True))
    result['source_changed'] = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
    result['head_after'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if result['source_changed'] or result['head_after'] != SHA:
        result['success'] = False
    result.update(seconds=round(time.monotonic() - started, 2), state='completed' if result['success'] else 'failed')
    save()
    print('PARENT_PUBLICATION_RESULT=' + json.dumps(result, sort_keys=True), flush=True)
raise SystemExit(0 if result['success'] else 1)
