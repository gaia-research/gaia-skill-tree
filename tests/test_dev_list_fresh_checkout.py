"""The list command reads canonical nodes without generated artifacts."""
import json
import subprocess
import sys
from pathlib import Path


def run_list(root, *flags):
    result = subprocess.run(
        [sys.executable, '-m', 'gaia_cli', '--registry', str(root), 'dev', 'list', *flags],
        text=True, capture_output=True, check=True,
    )
    return json.loads(result.stdout)


def test_fresh_checkout_nodes_and_filters(tmp_path):
    nodes = tmp_path / 'registry' / 'nodes'
    for kind, node in [('basic', {'id': 'alpha', 'name': 'Alpha', 'description': 'desc'}),
                       ('fusion', {'id': 'zeta', 'name': 'Zeta', 'description': 'fusion'})]:
        path = nodes / kind / (node['id'] + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(node), encoding='utf-8')
    assert not (tmp_path / 'registry' / 'gaia.json').exists()
    stale = tmp_path / '.gaia' / 'registry' / 'gaia.json'
    stale.parent.mkdir(parents=True)
    stale.write_text(json.dumps({'skills': [{'id': 'stale', 'name': 'Stale'}]}))
    assert run_list(tmp_path, '--generic', '--json') == [
        {'id': 'alpha', 'name': 'Alpha', 'kind': 'generic'},
        {'id': 'zeta', 'name': 'Zeta', 'kind': 'generic'},
    ]
    assert run_list(tmp_path, '--named', '--json') == []
    assert run_list(tmp_path, '--generic', '--description', '--json')[0]['description'] == 'desc'
    assert not (tmp_path / 'registry' / 'gaia.json').exists()


def test_source_nodes_take_precedence_and_legacy_graph_fallback(tmp_path):
    registry = tmp_path / 'registry'
    registry.mkdir()
    (registry / 'gaia.json').write_text(json.dumps({'skills': [{'id': 'old', 'name': 'Old'}]}))
    assert run_list(tmp_path, '--generic', '--json')[0]['id'] == 'old'
    (registry / 'nodes').mkdir()
    assert run_list(tmp_path, '--generic', '--json') == []
