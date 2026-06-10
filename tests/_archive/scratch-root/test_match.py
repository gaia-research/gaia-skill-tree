import json
from gaia_cli.registry import registry_graph_path
graph_path = registry_graph_path('.')
with open(graph_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
for s in data.get('skills', []):
    if 'feature' in s['id']:
        print(s['id'])
